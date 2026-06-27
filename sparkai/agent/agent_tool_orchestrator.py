"""
SparkLabs Agent - Tool Orchestrator

Comprehensive tool orchestration system that enables AI agents to discover,
compose, and execute tools in structured workflows. Provides a unified interface
for tool registration, validation, execution, and result aggregation. Designed
for autonomous game development agents that need to chain multiple operations
across the engine, editor, and content pipeline.

Architecture:
  AgentToolOrchestrator (Singleton)
    |-- ToolRegistry (discoverable tool catalog with metadata)
    |-- ToolExecutor (validated execution with retry and timeout)
    |-- ToolComposer (sequence and parallel tool composition)
    |-- ToolAuditor (execution trace and observability)
    |-- ToolCache (result caching for idempotent operations)
    |-- ToolSchema (structured input/output type definitions)

Tool Categories:
  - ENGINE: game engine operations (scene, physics, rendering)
  - EDITOR: editor-level operations (selection, undo, layout)
  - CONTENT: asset creation and manipulation
  - AGENT: agent introspection and configuration
  - EXTERNAL: API calls, file system, network

Usage:
    ot = AgentToolOrchestrator.get_instance()
    ot.initialize()

    ot.register_tool("create_scene", create_scene_fn, category="ENGINE")
    result = ot.execute("create_scene", {"name": "Level1", "width": 1920})

    pipeline = ot.compose([
        ToolStep("load_assets", {"path": "assets/"}),
        ToolStep("create_scene", {"name": "Level1"}),
        ToolStep("validate_scene", {}),
    ])
    results = ot.execute_pipeline(pipeline)
    ot.shutdown()
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import threading
import time
import traceback
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# =============================================================================
# Enums
# =============================================================================


class ToolCategory(Enum):
    """Categories for tool classification."""
    ENGINE = "engine"          # Game engine operations
    EDITOR = "editor"          # Editor-level operations
    CONTENT = "content"        # Asset creation and manipulation
    AGENT = "agent"            # Agent introspection
    EXTERNAL = "external"      # External API and file system
    UTILITY = "utility"        # General utilities


class ToolExecutionMode(Enum):
    """Execution modes for tools."""
    SYNCHRONOUS = "synchronous"      # Blocking execution
    ASYNCHRONOUS = "asynchronous"    # Non-blocking execution
    STREAMING = "streaming"          # Progressive result streaming
    BATCHED = "batched"              # Bulk execution


class ToolExecutionStatus(Enum):
    """Status of a tool execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    CACHED = "cached"


class CompositionStrategy(Enum):
    """Strategies for composing tool executions."""
    SEQUENTIAL = "sequential"       # Execute one after another
    PARALLEL = "parallel"           # Execute all simultaneously
    CONDITIONAL = "conditional"     # Execute based on previous results
    RETRY_ON_FAILURE = "retry"      # Retry failed steps
    BEST_EFFORT = "best_effort"     # Continue on failure


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    param_type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None
    enum_values: Optional[List[str]] = None
    validation: Optional[Callable[[Any], bool]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "type": self.param_type,
            "description": self.description,
            "required": self.required,
        }
        if self.default is not None:
            result["default"] = self.default
        if self.enum_values:
            result["enum"] = self.enum_values
        return result


@dataclass
class ToolDefinition:
    """Complete definition of a registered tool."""
    tool_id: str
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter] = field(default_factory=list)
    output_type: str = "any"
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    is_idempotent: bool = False
    timeout_seconds: float = 30.0
    max_retries: int = 0
    requires_confirmation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": [p.to_dict() for p in self.parameters],
            "output_type": self.output_type,
            "tags": self.tags,
            "version": self.version,
            "is_idempotent": self.is_idempotent,
            "timeout_seconds": self.timeout_seconds,
            "requires_confirmation": self.requires_confirmation,
            "metadata": self.metadata,
        }

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        properties = {}
        required = []
        for param in self.parameters:
            properties[param.name] = {
                "type": param.param_type,
                "description": param.description,
            }
            if param.enum_values:
                properties[param.name]["enum"] = param.enum_values
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


@dataclass
class ToolExecution:
    """Record of a single tool execution."""
    execution_id: str
    tool_id: str
    parameters: Dict[str, Any]
    status: ToolExecutionStatus = ToolExecutionStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    cached_result: bool = False
    traceback_info: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_successful(self) -> bool:
        return self.status in (ToolExecutionStatus.COMPLETED, ToolExecutionStatus.CACHED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "tool_id": self.tool_id,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
            "cached_result": self.cached_result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class ToolStep:
    """A single step in a tool composition pipeline."""
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    step_id: str = ""
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    on_failure: str = "stop"  # stop, skip, retry
    output_key: Optional[str] = None  # Key to store result for downstream steps

    def __post_init__(self):
        if not self.step_id:
            self.step_id = uuid.uuid4().hex[:8]


@dataclass
class PipelineResult:
    """Result of executing a tool pipeline."""
    pipeline_id: str
    steps: List[ToolExecution]
    overall_status: ToolExecutionStatus = ToolExecutionStatus.PENDING
    total_duration_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    cached_count: int = 0

    @property
    def is_successful(self) -> bool:
        return self.overall_status == ToolExecutionStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "overall_status": self.overall_status.value,
            "total_duration_ms": self.total_duration_ms,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "cached_count": self.cached_count,
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class ToolAuditEntry:
    """Audit trail entry for a tool operation."""
    entry_id: str
    tool_id: str
    action: str  # register, execute, update, remove
    parameters_hash: str = ""
    result_hash: str = ""
    user_id: str = "system"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "tool_id": self.tool_id,
            "action": self.action,
            "parameters_hash": self.parameters_hash,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


# =============================================================================
# Agent Tool Orchestrator
# =============================================================================


class AgentToolOrchestrator:
    """
    Central tool orchestration system for AI game development agents.
    Manages tool registration, discovery, validation, execution, and composition.
    """

    _instance: Optional["AgentToolOrchestrator"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if AgentToolOrchestrator._instance is not None:
            raise RuntimeError("Use AgentToolOrchestrator.get_instance()")
        self._initialized: bool = False
        self._tools: Dict[str, ToolDefinition] = {}
        self._callables: Dict[str, Callable] = {}
        self._executions: Dict[str, ToolExecution] = {}
        self._execution_history: deque = deque(maxlen=500)
        self._audit_trail: List[ToolAuditEntry] = []
        self._cache: Dict[str, Any] = {}
        self._categories: Dict[ToolCategory, List[str]] = defaultdict(list)
        self._tags_index: Dict[str, List[str]] = defaultdict(list)
        self._pending_executions: Dict[str, asyncio.Task] = {}
        self._stats: Dict[str, Any] = {
            "total_tools": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "cached_executions": 0,
            "avg_execution_ms": 0.0,
            "total_pipelines": 0,
        }
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "AgentToolOrchestrator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, cache_enabled: bool = True,
                   default_timeout: float = 30.0,
                   max_concurrent: int = 10) -> None:
        """Initialize the tool orchestrator."""
        with self._lock:
            if self._initialized:
                return
            self._cache_enabled = cache_enabled
            self._default_timeout = default_timeout
            self._max_concurrent = max_concurrent
            self._initialized = True

    # -------------------------------------------------------------------------
    # Tool Registration
    # -------------------------------------------------------------------------

    def register_tool(self, name: str, func: Callable,
                      description: str = "",
                      category: Union[ToolCategory, str] = ToolCategory.UTILITY,
                      parameters: Optional[List[ToolParameter]] = None,
                      output_type: str = "any",
                      tags: Optional[List[str]] = None,
                      is_idempotent: bool = False,
                      timeout_seconds: float = 30.0,
                      max_retries: int = 0,
                      requires_confirmation: bool = False,
                      metadata: Optional[Dict[str, Any]] = None) -> ToolDefinition:
        """Register a new tool with the orchestrator."""
        with self._lock:
            tool_id = uuid.uuid4().hex[:12]

            if isinstance(category, str):
                try:
                    category = ToolCategory(category)
                except ValueError:
                    category = ToolCategory.UTILITY

            # Auto-extract parameters from function signature if not provided
            if parameters is None:
                parameters = self._extract_parameters(func)

            definition = ToolDefinition(
                tool_id=tool_id,
                name=name,
                description=description or func.__doc__ or "",
                category=category,
                parameters=parameters,
                output_type=output_type,
                tags=tags or [],
                is_idempotent=is_idempotent,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                requires_confirmation=requires_confirmation,
                metadata=metadata or {},
            )

            self._tools[tool_id] = definition
            self._callables[tool_id] = func
            self._categories[category].append(tool_id)
            for tag in definition.tags:
                self._tags_index[tag].append(tool_id)
            self._stats["total_tools"] += 1

            self._audit("register", tool_id)
            return definition

    def unregister_tool(self, tool_id: str) -> bool:
        """Remove a tool from the registry."""
        with self._lock:
            definition = self._tools.pop(tool_id, None)
            if definition is None:
                return False
            self._callables.pop(tool_id, None)
            self._categories[definition.category].remove(tool_id)
            for tag in definition.tags:
                if tool_id in self._tags_index[tag]:
                    self._tags_index[tag].remove(tool_id)
            self._audit("remove", tool_id)
            return True

    def _extract_parameters(self, func: Callable) -> List[ToolParameter]:
        """Extract parameter definitions from a function signature."""
        parameters = []
        try:
            sig = inspect.signature(func)
            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                param_type = "string"
                if param.annotation != inspect.Parameter.empty:
                    type_name = getattr(param.annotation, "__name__", str(param.annotation))
                    type_map = {
                        "str": "string", "int": "integer", "float": "number",
                        "bool": "boolean", "list": "array", "dict": "object",
                    }
                    param_type = type_map.get(type_name, "string")

                required = param.default == inspect.Parameter.empty
                default = None if required else param.default

                parameters.append(ToolParameter(
                    name=param_name,
                    param_type=param_type,
                    description=f"Parameter: {param_name}",
                    required=required,
                    default=default,
                ))
        except (ValueError, TypeError):
            pass
        return parameters

    # -------------------------------------------------------------------------
    # Tool Discovery
    # -------------------------------------------------------------------------

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get a tool definition by ID."""
        return self._tools.get(tool_id)

    def find_tool_by_name(self, name: str) -> Optional[ToolDefinition]:
        """Find a tool by its name."""
        for tool in self._tools.values():
            if tool.name == name:
                return tool
        return None

    def list_tools(self, category: Optional[ToolCategory] = None,
                   tags: Optional[List[str]] = None) -> List[ToolDefinition]:
        """List tools, optionally filtered by category or tags."""
        with self._lock:
            if category:
                tool_ids = self._categories.get(category, [])
                tools = [self._tools[tid] for tid in tool_ids if tid in self._tools]
            else:
                tools = list(self._tools.values())

            if tags:
                matching_ids: Set[str] = set()
                for tag in tags:
                    matching_ids.update(self._tags_index.get(tag, []))
                tools = [t for t in tools if t.tool_id in matching_ids]

            return tools

    def search_tools(self, query: str) -> List[ToolDefinition]:
        """Search tools by name, description, or tags."""
        query_lower = query.lower()
        results = []
        for tool in self._tools.values():
            if (query_lower in tool.name.lower() or
                    query_lower in tool.description.lower() or
                    any(query_lower in tag.lower() for tag in tool.tags)):
                results.append(tool)
        return results

    def get_openai_tools(self, category: Optional[ToolCategory] = None) -> List[Dict[str, Any]]:
        """Get all tools as OpenAI function calling schema."""
        tools = self.list_tools(category=category)
        return [t.to_openai_schema() for t in tools]

    # -------------------------------------------------------------------------
    # Tool Execution
    # -------------------------------------------------------------------------

    def execute(self, tool_name_or_id: str, parameters: Dict[str, Any],
                timeout: Optional[float] = None,
                force_refresh: bool = False) -> ToolExecution:
        """Execute a tool with the given parameters."""
        with self._lock:
            # Resolve tool
            tool = self.find_tool_by_name(tool_name_or_id)
            if not tool:
                tool = self._tools.get(tool_name_or_id)
            if not tool:
                return ToolExecution(
                    execution_id=uuid.uuid4().hex[:8],
                    tool_id=tool_name_or_id,
                    parameters=parameters,
                    status=ToolExecutionStatus.FAILED,
                    error=f"Tool not found: {tool_name_or_id}",
                )

            execution_id = uuid.uuid4().hex[:12]
            execution = ToolExecution(
                execution_id=execution_id,
                tool_id=tool.tool_id,
                parameters=parameters,
                status=ToolExecutionStatus.RUNNING,
                started_at=time.time(),
            )

            # Check cache for idempotent tools
            if tool.is_idempotent and self._cache_enabled and not force_refresh:
                cache_key = self._compute_cache_key(tool.tool_id, parameters)
                cached = self._cache.get(cache_key)
                if cached is not None:
                    execution.status = ToolExecutionStatus.CACHED
                    execution.result = cached
                    execution.cached_result = True
                    execution.completed_at = time.time()
                    self._stats["cached_executions"] += 1
                    return execution

            # Execute the tool
            try:
                func = self._callables.get(tool.tool_id)
                if not func:
                    raise ValueError(f"No callable for tool: {tool.tool_id}")

                result = func(**parameters)
                execution.status = ToolExecutionStatus.COMPLETED
                execution.result = result
                execution.completed_at = time.time()
                execution.duration_ms = (execution.completed_at - execution.started_at) * 1000
                self._stats["successful_executions"] += 1

                # Cache idempotent results
                if tool.is_idempotent and self._cache_enabled:
                    cache_key = self._compute_cache_key(tool.tool_id, parameters)
                    self._cache[cache_key] = result

            except Exception as e:
                execution.status = ToolExecutionStatus.FAILED
                execution.error = str(e)
                execution.traceback_info = traceback.format_exc()
                execution.completed_at = time.time()
                execution.duration_ms = (execution.completed_at - execution.started_at) * 1000
                self._stats["failed_executions"] += 1

            self._executions[execution_id] = execution
            self._execution_history.append(execution)
            self._stats["total_executions"] += 1
            self._update_avg_execution_time(execution.duration_ms)
            self._audit("execute", tool.tool_id, execution_id)

            return execution

    def execute_with_retry(self, tool_name_or_id: str, parameters: Dict[str, Any],
                           max_retries: int = 3) -> ToolExecution:
        """Execute a tool with automatic retry on failure."""
        for attempt in range(max_retries + 1):
            execution = self.execute(tool_name_or_id, parameters)
            if execution.is_successful:
                return execution
            execution.retry_count = attempt
            if attempt < max_retries:
                time.sleep(0.5 * (attempt + 1))
        return execution

    # -------------------------------------------------------------------------
    # Pipeline Composition
    # -------------------------------------------------------------------------

    def compose(self, steps: List[ToolStep],
                strategy: CompositionStrategy = CompositionStrategy.SEQUENTIAL) -> PipelineResult:
        """Compose and execute a pipeline of tool steps."""
        pipeline_id = uuid.uuid4().hex[:12]
        executions: List[ToolExecution] = []
        step_outputs: Dict[str, Any] = {}

        if strategy == CompositionStrategy.PARALLEL:
            executions = self._execute_parallel(steps)
        else:
            executions = self._execute_sequential(steps, step_outputs, strategy)

        success_count = sum(1 for e in executions if e.is_successful)
        failure_count = sum(1 for e in executions if e.status == ToolExecutionStatus.FAILED)
        cached_count = sum(1 for e in executions if e.status == ToolExecutionStatus.CACHED)
        total_duration = sum(e.duration_ms for e in executions)

        result = PipelineResult(
            pipeline_id=pipeline_id,
            steps=executions,
            overall_status=ToolExecutionStatus.COMPLETED if failure_count == 0 else ToolExecutionStatus.FAILED,
            total_duration_ms=total_duration,
            success_count=success_count,
            failure_count=failure_count,
            cached_count=cached_count,
        )

        self._stats["total_pipelines"] += 1
        return result

    def _execute_sequential(self, steps: List[ToolStep],
                            step_outputs: Dict[str, Any],
                            strategy: CompositionStrategy) -> List[ToolExecution]:
        """Execute steps sequentially with output passing."""
        executions = []
        for step in steps:
            # Check condition
            if step.condition and not step.condition(step_outputs):
                continue

            # Resolve parameters from previous outputs
            resolved_params = self._resolve_parameters(step.parameters, step_outputs)

            execution = self.execute(step.tool_name, resolved_params)

            if step.output_key:
                step_outputs[step.output_key] = execution.result

            executions.append(execution)

            if not execution.is_successful:
                if strategy == CompositionStrategy.BEST_EFFORT:
                    continue
                elif step.on_failure == "retry":
                    execution = self.execute_with_retry(step.tool_name, resolved_params)
                    if step.output_key:
                        step_outputs[step.output_key] = execution.result
                    if not execution.is_successful:
                        break
                else:
                    break

        return executions

    def _execute_parallel(self, steps: List[ToolStep]) -> List[ToolExecution]:
        """Execute steps in parallel using threads."""
        import concurrent.futures
        executions = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(steps), self._max_concurrent)) as executor:
            futures = {
                executor.submit(self.execute, step.tool_name, step.parameters): step
                for step in steps
            }
            for future in concurrent.futures.as_completed(futures):
                executions.append(future.result())
        return executions

    def _resolve_parameters(self, parameters: Dict[str, Any],
                            step_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve parameter references to previous step outputs."""
        resolved = {}
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("${{") and value.endswith("}}"):
                ref = value[3:-2].strip()
                resolved[key] = step_outputs.get(ref, value)
            else:
                resolved[key] = value
        return resolved

    # -------------------------------------------------------------------------
    # Cache Management
    # -------------------------------------------------------------------------

    def _compute_cache_key(self, tool_id: str, parameters: Dict[str, Any]) -> str:
        """Compute a cache key from tool ID and parameters."""
        param_str = json.dumps(parameters, sort_keys=True, default=str)
        raw = f"{tool_id}:{param_str}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def invalidate_cache(self, tool_id: Optional[str] = None) -> int:
        """Invalidate cache entries, optionally filtered by tool."""
        with self._lock:
            if tool_id is None:
                count = len(self._cache)
                self._cache.clear()
                return count
            count = 0
            keys_to_remove = [k for k in self._cache if k.startswith(tool_id)]
            for k in keys_to_remove:
                del self._cache[k]
                count += 1
            return count

    # -------------------------------------------------------------------------
    # Audit and Observability
    # -------------------------------------------------------------------------

    def _audit(self, action: str, tool_id: str,
               execution_id: Optional[str] = None) -> None:
        """Record an audit trail entry."""
        entry = ToolAuditEntry(
            entry_id=uuid.uuid4().hex[:8],
            tool_id=tool_id,
            action=action,
            metadata={"execution_id": execution_id} if execution_id else {},
        )
        self._audit_trail.append(entry)

    def get_execution(self, execution_id: str) -> Optional[ToolExecution]:
        """Get a specific execution record."""
        return self._executions.get(execution_id)

    def get_execution_history(self, limit: int = 50) -> List[ToolExecution]:
        """Get recent execution history."""
        return list(self._execution_history)[-limit:]

    def get_audit_trail(self, limit: int = 100) -> List[ToolAuditEntry]:
        """Get audit trail entries."""
        return self._audit_trail[-limit:]

    def _update_avg_execution_time(self, duration_ms: float) -> None:
        """Update the rolling average execution time."""
        total = self._stats["total_executions"]
        if total > 0:
            self._stats["avg_execution_ms"] = (
                (self._stats["avg_execution_ms"] * (total - 1) + duration_ms) / total
            )

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status and statistics."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "tools": self._stats["total_tools"],
                "tools_by_category": {k.value: len(v) for k, v in self._categories.items()},
                "executions": self._stats["total_executions"],
                "successful": self._stats["successful_executions"],
                "failed": self._stats["failed_executions"],
                "cached": self._stats["cached_executions"],
                "avg_execution_ms": round(self._stats["avg_execution_ms"], 2),
                "pipelines": self._stats["total_pipelines"],
                "cache_size": len(self._cache),
                "audit_entries": len(self._audit_trail),
            }

    def shutdown(self) -> None:
        """Shutdown the orchestrator and clean up resources."""
        with self._lock:
            self._cache.clear()
            self._pending_executions.clear()
            self._initialized = False


def get_tool_orchestrator() -> AgentToolOrchestrator:
    """Get the singleton tool orchestrator instance."""
    return AgentToolOrchestrator.get_instance()