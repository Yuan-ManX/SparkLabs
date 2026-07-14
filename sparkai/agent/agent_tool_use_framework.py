"""
SparkLabs Agent - Tool Use Framework

A unified framework that lets AI agents discover, call, and chain tools
(functions) inside the SparkLabs AI-native game engine. Pairs a typed tool
registry with a multi-step reasoning pipeline so agents can move fluidly
between deliberation and concrete game-world actions.

Architecture:
  ToolUseFramework
    |-- ToolRegistry      (register / unregister / list / search tools)
    |-- ToolExecutor      (sync / async / batch execution, timeout, retry)
    |-- ToolChainer       (sequential, conditional, parallel, retry chains)
    |-- FunctionCaller    (parse LLM function-call requests, batch calls)
    |-- PipelineBuilder   (mix tool calls with reasoning steps)
    |-- ToolDiscovery / HistoryTracker / VersionManager / PermissionGate / SchemaValidator
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Tuple


def _uid(prefix: str = "id") -> str:
    """Generate a short unique identifier with a descriptive prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _now_ts() -> float:
    """Return the current time as a POSIX timestamp."""
    return time.time()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value to the [low, high] interval."""
    return low if value < low else high if value > high else value


def _to_namespace(obj: Any) -> Any:
    """Recursively convert dict / list structures into attribute-accessible objects."""
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_to_namespace(item) for item in obj]
    return obj


class ToolCategory(Enum):
    """Coarse classification used for grouping and discovery."""
    ENTITY = "entity"
    ANIMATION = "animation"
    MATERIAL = "material"
    EVENT = "event"
    SCENE = "scene"
    AUDIO = "audio"
    PHYSICS = "physics"
    AI = "ai"
    UI = "ui"
    UTILITY = "utility"


class ExecutionStatus(Enum):
    """Lifecycle status for a single tool execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class PermissionLevel(Enum):
    """Access tier for a tool."""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


class PipelineState(Enum):
    """Lifecycle state for a reasoning pipeline."""
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepKind(Enum):
    """Discriminator for pipeline steps."""
    TOOL = "tool"
    REASONING = "reasoning"


@dataclass
class ToolParameter:
    """A single declared parameter for a tool."""
    name: str
    type: str = "any"
    required: bool = False
    default: Any = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "type": self.type, "required": self.required,
                "default": self.default, "description": self.description}


@dataclass
class ToolDefinition:
    """Full declaration of a callable tool."""
    tool_id: str = field(default_factory=lambda: _uid("tool"))
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.UTILITY
    parameters: List[ToolParameter] = field(default_factory=list)
    handler: str = ""
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    created_ts: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {"tool_id": self.tool_id, "name": self.name, "description": self.description, "category": self.category.value,
                "parameters": [p.to_dict() for p in self.parameters], "handler": self.handler, "version": self.version,
                "tags": list(self.tags), "enabled": self.enabled, "created_ts": self.created_ts}


@dataclass
class ToolResult:
    """Outcome of a single tool invocation."""
    success: bool = False
    output: Any = None
    error: str = ""
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"success": self.success, "output": self.output, "error": self.error,
                "duration": self.duration, "metadata": dict(self.metadata)}


@dataclass
class ToolExecution:
    """A recorded execution event for history and statistics."""
    execution_id: str = field(default_factory=lambda: _uid("exec"))
    tool_id: str = ""
    tool_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: ToolResult = field(default_factory=ToolResult)
    start_ts: float = field(default_factory=_now_ts)
    end_ts: float = 0.0
    duration: float = 0.0
    error: str = ""
    attempt: int = 1
    caller_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"execution_id": self.execution_id, "tool_id": self.tool_id, "tool_name": self.tool_name,
                "parameters": dict(self.parameters), "status": self.status.value, "result": self.result.to_dict(),
                "start_ts": self.start_ts, "end_ts": self.end_ts, "duration": self.duration,
                "error": self.error, "attempt": self.attempt, "caller_id": self.caller_id}


@dataclass
class ChainStep:
    """One step inside a tool chain."""
    step_id: str = field(default_factory=lambda: _uid("step"))
    tool_id: str = ""
    input_mapping: Dict[str, str] = field(default_factory=dict)
    condition: str = ""
    timeout: float = 30.0
    retry_count: int = 0
    parallel_group: str = ""
    on_fail: str = "continue"
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"step_id": self.step_id, "tool_id": self.tool_id, "input_mapping": dict(self.input_mapping),
                "condition": self.condition, "timeout": self.timeout, "retry_count": self.retry_count,
                "parallel_group": self.parallel_group, "on_fail": self.on_fail, "parameters": dict(self.parameters)}


@dataclass
class ToolChain:
    """An ordered collection of chain steps."""
    chain_id: str = field(default_factory=lambda: _uid("chain"))
    name: str = ""
    description: str = ""
    steps: List[ChainStep] = field(default_factory=list)
    created_ts: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {"chain_id": self.chain_id, "name": self.name, "description": self.description,
                "steps": [s.to_dict() for s in self.steps], "created_ts": self.created_ts}


@dataclass
class ChainExecution:
    """Recorded run of a tool chain."""
    chain_execution_id: str = field(default_factory=lambda: _uid("chainexec"))
    chain_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    step_results: Dict[str, ToolResult] = field(default_factory=dict)
    start_ts: float = field(default_factory=_now_ts)
    end_ts: float = 0.0
    duration: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"chain_execution_id": self.chain_execution_id, "chain_id": self.chain_id, "status": self.status.value,
                "step_results": {k: v.to_dict() for k, v in self.step_results.items()},
                "start_ts": self.start_ts, "end_ts": self.end_ts, "duration": self.duration, "error": self.error}


@dataclass
class PipelineStep:
    """A single step in a reasoning pipeline (tool call or deliberation)."""
    step_id: str = field(default_factory=lambda: _uid("pstep"))
    kind: StepKind = StepKind.TOOL
    tool_id: str = ""
    input_mapping: Dict[str, str] = field(default_factory=dict)
    condition: str = ""
    reasoning_prompt: str = ""
    timeout: float = 30.0
    retry_count: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"step_id": self.step_id, "kind": self.kind.value, "tool_id": self.tool_id, "input_mapping": dict(self.input_mapping),
                "condition": self.condition, "reasoning_prompt": self.reasoning_prompt, "timeout": self.timeout,
                "retry_count": self.retry_count, "parameters": dict(self.parameters)}


@dataclass
class ReasoningPipeline:
    """A multi-step pipeline interleaving tool calls and reasoning."""
    pipeline_id: str = field(default_factory=lambda: _uid("pipe"))
    name: str = ""
    description: str = ""
    steps: List[PipelineStep] = field(default_factory=list)
    state: PipelineState = PipelineState.DRAFT
    created_ts: float = field(default_factory=_now_ts)
    started_ts: float = 0.0
    completed_ts: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"pipeline_id": self.pipeline_id, "name": self.name, "description": self.description,
                "steps": [s.to_dict() for s in self.steps], "state": self.state.value, "created_ts": self.created_ts,
                "started_ts": self.started_ts, "completed_ts": self.completed_ts}


@dataclass
class PipelineExecution:
    """Recorded run of a reasoning pipeline."""
    pipeline_execution_id: str = field(default_factory=lambda: _uid("pipeexec"))
    pipeline_id: str = ""
    state: PipelineState = PipelineState.DRAFT
    step_results: Dict[str, ToolResult] = field(default_factory=dict)
    start_ts: float = field(default_factory=_now_ts)
    end_ts: float = 0.0
    duration: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"pipeline_execution_id": self.pipeline_execution_id, "pipeline_id": self.pipeline_id, "state": self.state.value,
                "step_results": {k: v.to_dict() for k, v in self.step_results.items()},
                "start_ts": self.start_ts, "end_ts": self.end_ts, "duration": self.duration, "error": self.error}


@dataclass
class ToolPermission:
    """Permission entry binding a caller to a tool at a given level."""
    permission_id: str = field(default_factory=lambda: _uid("perm"))
    tool_id: str = ""
    tool_name: str = ""
    level: PermissionLevel = PermissionLevel.PUBLIC
    caller_id: str = "*"
    granted_ts: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {"permission_id": self.permission_id, "tool_id": self.tool_id, "tool_name": self.tool_name,
                "level": self.level.value, "caller_id": self.caller_id, "granted_ts": self.granted_ts}


@dataclass
class ToolVersion:
    """A snapshotted version of a tool definition."""
    version_id: str = field(default_factory=lambda: _uid("ver"))
    tool_id: str = ""
    version: str = "1.0.0"
    snapshot: Dict[str, Any] = field(default_factory=dict)
    created_ts: float = field(default_factory=_now_ts)
    active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"version_id": self.version_id, "tool_id": self.tool_id, "version": self.version,
                "snapshot": dict(self.snapshot), "created_ts": self.created_ts, "active": self.active}


class ToolUseFramework:
    """Unified registry, executor, chainer, and pipeline builder for agent tool use."""

    DEFAULT_TIMEOUT = 30.0
    MAX_HISTORY = 1000
    _instance: Optional["ToolUseFramework"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "ToolUseFramework":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._lock = threading.RLock()
        self._tools: Dict[str, ToolDefinition] = {}
        self._tools_by_name: Dict[str, str] = {}
        self._versions: Dict[str, List[ToolVersion]] = {}
        self._executions: deque = deque(maxlen=self.MAX_HISTORY)
        self._executions_by_id: Dict[str, ToolExecution] = {}
        self._chains: Dict[str, ToolChain] = {}
        self._chain_executions: Dict[str, ChainExecution] = {}
        self._pipelines: Dict[str, ReasoningPipeline] = {}
        self._pipeline_executions: Dict[str, PipelineExecution] = {}
        self._permissions: Dict[str, ToolPermission] = {}
        self._permissions_by_tool: Dict[str, List[str]] = defaultdict(list)
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._config: Dict[str, Any] = {
            "default_timeout": self.DEFAULT_TIMEOUT, "max_history": self.MAX_HISTORY,
            "default_retry": 0, "strict_permissions": False, "auto_seed": True}
        if config:
            self._config.update(config)
        self._initialized = False
        self._default_handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {
            "spawn_entity": self._h_spawn_entity, "play_animation": self._h_play_animation, "set_material": self._h_set_material,
            "trigger_event": self._h_trigger_event, "teleport_entity": self._h_teleport_entity, "apply_damage": self._h_apply_damage,
            "spawn_particle": self._h_spawn_particle, "play_sound": self._h_play_sound, "set_light": self._h_set_light,
            "attach_component": self._h_attach_component, "set_ai_state": self._h_set_ai_state, "show_ui": self._h_show_ui,
            "save_state": self._h_save_state}

    # -- Lifecycle -------------------------------------------------------

    def initialize(self) -> Dict[str, Any]:
        """Initialize the framework; idempotent and seeds default tools."""
        with self._lock:
            if self._initialized:
                return {"initialized": True, "tools": len(self._tools)}
            self._initialized = True
            if self._config.get("auto_seed", True):
                self._seed_default_tools()
            return {"initialized": True, "tools": len(self._tools),
                    "handlers": len(self._default_handlers)}

    def reset(self) -> Dict[str, Any]:
        """Clear all runtime state, keep config, and re-seed default tools."""
        with self._lock:
            for store in (self._tools, self._tools_by_name, self._versions, self._executions,
                          self._executions_by_id, self._chains, self._chain_executions, self._pipelines,
                          self._pipeline_executions, self._permissions, self._handlers):
                store.clear()
            self._permissions_by_tool.clear()
            self._initialized = False
            self.initialize()
            return {"reset": True, "tools": len(self._tools)}

    def get_config(self) -> Dict[str, Any]:
        """Return a copy of the current configuration."""
        with self._lock:
            return dict(self._config)

    def set_config(self, key: str, value: Any) -> Dict[str, Any]:
        """Set a single configuration key and return the updated config."""
        with self._lock:
            self._config[key] = value
            if key == "max_history":
                self._executions = deque(self._executions, maxlen=int(value))
            return dict(self._config)

    def get_status(self) -> Dict[str, Any]:
        """Return a compact status snapshot of the framework."""
        with self._lock:
            success_count = sum(
                1 for e in self._executions if e.status == ExecutionStatus.SUCCESS)
            return {"initialized": self._initialized, "tools": len(self._tools),
                    "enabled_tools": sum(1 for t in self._tools.values() if t.enabled),
                    "executions": len(self._executions),
                    "successful_executions": success_count, "chains": len(self._chains),
                    "pipelines": len(self._pipelines),
                    "permissions": len(self._permissions),
                    "handlers": len(self._default_handlers) + len(self._handlers)}

    # -- Tool registry ---------------------------------------------------

    def register_tool(self, tool: ToolDefinition) -> ToolDefinition:
        """Register a new tool; a duplicate name snapshots the old one as a version."""
        with self._lock:
            if not tool.name:
                raise ValueError("Tool name is required")
            if not tool.tool_id:
                tool.tool_id = _uid("tool")
            existing_id = self._tools_by_name.get(tool.name)
            if existing_id and existing_id != tool.tool_id:
                self._snapshot_version(self._tools[existing_id])
            self._tools[tool.tool_id] = tool
            self._tools_by_name[tool.name] = tool.tool_id
            if tool.tool_id not in self._versions:
                self._snapshot_version(tool)
            return tool

    def unregister_tool(self, tool_id: str) -> bool:
        """Remove a tool from the registry. Returns True if removed."""
        with self._lock:
            tool = self._tools.get(tool_id)
            if not tool:
                return False
            del self._tools[tool_id]
            if self._tools_by_name.get(tool.name) == tool_id:
                del self._tools_by_name[tool.name]
            self._versions.pop(tool_id, None)
            for perm_id in list(self._permissions_by_tool.get(tool_id, [])):
                self._permissions.pop(perm_id, None)
            self._permissions_by_tool.pop(tool_id, None)
            return True

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """Fetch a tool by its identifier or by name."""
        with self._lock:
            if tool_id in self._tools:
                return self._tools[tool_id]
            mapped = self._tools_by_name.get(tool_id)
            return self._tools.get(mapped) if mapped else None

    def list_tools(self, include_disabled: bool = False) -> List[ToolDefinition]:
        """List all registered tools, optionally including disabled ones."""
        with self._lock:
            tools = list(self._tools.values())
            if not include_disabled:
                tools = [t for t in tools if t.enabled]
            return sorted(tools, key=lambda t: (t.category.value, t.name))

    def list_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """List all enabled tools that belong to a given category."""
        with self._lock:
            return [t for t in self._tools.values()
                    if t.category == category and t.enabled]

    def search_tools(self, query: str, limit: int = 20) -> List[ToolDefinition]:
        """Search tools by name, description, category, and tags via keyword scoring."""
        with self._lock:
            tokens = [t for t in (query or "").lower().split() if t]
            if not tokens:
                return []
            scored: List[Tuple[float, ToolDefinition]] = []
            for tool in self._tools.values():
                if not tool.enabled:
                    continue
                name_l, desc_l = tool.name.lower(), tool.description.lower()
                cat_l = tool.category.value.lower()
                tags_l = " ".join(tool.tags).lower()
                score = sum(3.0 if tok in name_l else 0.0 for tok in tokens) + \
                    sum(2.0 if tok in cat_l else 0.0 for tok in tokens) + \
                    sum(2.0 if tok in tags_l else 0.0 for tok in tokens) + \
                    sum(1.0 if tok in desc_l else 0.0 for tok in tokens)
                if score > 0:
                    scored.append((score, tool))
            scored.sort(key=lambda pair: pair[0], reverse=True)
            return [t for _, t in scored[:limit]]

    def suggest_tools(self, task_description: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Suggest tools likely useful for a natural-language task description."""
        with self._lock:
            results = self.search_tools(task_description, limit=limit * 3)
            return [{"tool_id": t.tool_id, "name": t.name, "description": t.description,
                     "category": t.category.value, "handler": t.handler,
                     "match_score": _clamp(len(task_description) / 100.0)}
                    for t in results[:limit]]

    def register_handler(self, name: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """Register a custom callable handler identified by name."""
        with self._lock:
            self._handlers[name] = handler

    # -- Tool execution --------------------------------------------------

    def execute_tool(self, tool_id: str, parameters: Optional[Dict[str, Any]] = None,
                     caller_id: str = "", timeout: Optional[float] = None, retry_count: Optional[int] = None) -> ToolResult:
        """Execute a tool synchronously by id or name with validation and permissions."""
        with self._lock:
            tool = self.get_tool(tool_id)
            if not tool:
                return ToolResult(success=False, error=f"Tool not found: {tool_id}")
            if not tool.enabled:
                return ToolResult(success=False, error=f"Tool is disabled: {tool.name}")
            if not self.check_permission(tool.tool_id, caller_id):
                return ToolResult(success=False, error=f"Permission denied for {tool.name} (caller={caller_id})")
            ok, errors, coerced = self.validate_parameters(tool, parameters or {})
            if not ok:
                return ToolResult(success=False, error="Parameter validation failed: " + "; ".join(errors))
            execution = ToolExecution(tool_id=tool.tool_id, tool_name=tool.name, parameters=coerced,
                                      status=ExecutionStatus.RUNNING, caller_id=caller_id, start_ts=_now_ts())
            self._executions.append(execution)
            self._executions_by_id[execution.execution_id] = execution
        return self._execute_internal(tool, coerced, execution, timeout, retry_count)

    def execute_batch(self, calls: List[Tuple[str, Dict[str, Any]]],
                      caller_id: str = "", timeout: Optional[float] = None) -> List[ToolResult]:
        """Execute a sequence of tool calls; a failure does not stop the rest."""
        return [self.execute_tool(tid, params, caller_id, timeout) for tid, params in calls]

    def execute_async(self, tool_id: str, parameters: Optional[Dict[str, Any]] = None,
                      caller_id: str = "", timeout: Optional[float] = None) -> str:
        """Start a tool execution on a background thread; return the execution id."""
        with self._lock:
            tool = self.get_tool(tool_id)
            if not tool:
                raise ValueError(f"Tool not found: {tool_id}")
            ok, errors, coerced = self.validate_parameters(tool, parameters or {})
            if not ok:
                raise ValueError("Parameter validation failed: " + "; ".join(errors))
            execution = ToolExecution(tool_id=tool.tool_id, tool_name=tool.name, parameters=coerced,
                                      status=ExecutionStatus.RUNNING, caller_id=caller_id, start_ts=_now_ts())
            self._executions.append(execution)
            self._executions_by_id[execution.execution_id] = execution

        def _runner() -> None:
            self._execute_internal(tool, coerced, execution, timeout, None)

        threading.Thread(target=_runner, daemon=True).start()
        return execution.execution_id

    def get_execution(self, execution_id: str) -> Optional[ToolExecution]:
        """Fetch an execution record by identifier."""
        with self._lock:
            return self._executions_by_id.get(execution_id)

    def list_executions(self, tool_id: Optional[str] = None, limit: int = 100) -> List[ToolExecution]:
        """List recent executions, optionally filtered by tool id or name."""
        with self._lock:
            items = list(self._executions)
        if tool_id:
            target = self.get_tool(tool_id)
            target_id = target.tool_id if target else tool_id
            items = [e for e in items if e.tool_id == target_id]
        return list(reversed(items))[:limit]

    # -- Function calling (LLM integration) ------------------------------

    def parse_function_call(self, request: Any) -> Tuple[str, Dict[str, Any]]:
        """Parse an LLM function-call request into a (tool_name, parameters) tuple."""
        if isinstance(request, str):
            text = request.strip()
            name = ""
            args: Dict[str, Any] = {}
            if "(" in text and text.endswith(")"):
                name = text.split("(", 1)[0].strip()
                arg_str = text[len(name) + 1:-1].strip()
                if arg_str:
                    try:
                        import json as _json
                        args = _json.loads("{" + arg_str + "}")
                    except Exception:
                        for pair in arg_str.split(","):
                            if "=" in pair:
                                k, v = pair.split("=", 1)
                                v = v.strip().strip("'\"")
                                args[k.strip()] = v
            return name, args
        if not isinstance(request, dict):
            return "", {}
        name = request.get("name") or request.get("tool") or ""
        args = request.get("arguments")
        if args is None:
            args = request.get("args") or request.get("parameters") or {}
        if isinstance(args, str):
            try:
                import json
                args = json.loads(args)
            except Exception:
                args = {}
        if not isinstance(args, dict):
            args = {}
        return name, args

    def execute_function_call(self, request: Dict[str, Any], caller_id: str = "") -> ToolResult:
        """Parse and execute a single function-call request."""
        name, args = self.parse_function_call(request)
        if not name:
            return ToolResult(success=False, error="Function call missing tool name")
        return self.execute_tool(name, args, caller_id=caller_id)

    def execute_function_calls(self, requests: List[Dict[str, Any]],
                               caller_id: str = "") -> List[ToolResult]:
        """Execute a batch of function-call requests sequentially."""
        return [self.execute_function_call(req, caller_id=caller_id) for req in requests]

    def format_result_for_llm(self, result: ToolResult, tool_name: str = "") -> Dict[str, Any]:
        """Format a ToolResult into a compact dict for feeding back to an LLM."""
        if isinstance(result, dict):
            success = result.get("success", False)
            output = result.get("output", result.get("data"))
            error = result.get("error", "")
            duration = float(result.get("duration", 0.0) or 0.0)
        else:
            success = result.success
            output = result.output
            error = result.error
            duration = result.duration
        return {"tool": tool_name, "success": success, "output": output,
                "error": error, "duration_ms": round(duration * 1000.0, 2)}

    # -- Tool chaining ---------------------------------------------------

    def create_chain(self, name: str, steps: List[ChainStep],
                     description: str = "") -> ToolChain:
        """Create and register a new tool chain."""
        with self._lock:
            chain = ToolChain(name=name, description=description, steps=list(steps))
            self._chains[chain.chain_id] = chain
            return chain

    def get_chain(self, chain_id: str) -> Optional[ToolChain]:
        """Fetch a chain by identifier."""
        with self._lock:
            return self._chains.get(chain_id)

    def execute_chain(self, chain_id: str, initial_inputs: Optional[Dict[str, Any]] = None,
                      caller_id: str = "") -> ChainExecution:
        """Execute a registered chain with conditional, parallel, retry, and abort support."""
        with self._lock:
            chain = self._chains.get(chain_id)
            if not chain:
                return ChainExecution(chain_id=chain_id, status=ExecutionStatus.FAILED, error="Chain not found")
            execution = ChainExecution(chain_id=chain_id, status=ExecutionStatus.RUNNING, start_ts=_now_ts())
            self._chain_executions[execution.chain_execution_id] = execution
        context: Dict[str, ToolResult] = {"__init__": ToolResult(success=True, output=dict(initial_inputs or {}))}
        i = 0
        while i < len(chain.steps):
            step = chain.steps[i]
            group = step.parallel_group
            if group:
                siblings, j = [], i
                while j < len(chain.steps) and chain.steps[j].parallel_group == group:
                    siblings.append(chain.steps[j])
                    j += 1
                self._run_parallel_steps(siblings, context, caller_id, execution)
                i = j
                continue
            self._run_chain_step(step, context, caller_id, execution)
            if step.on_fail == "abort":
                res = context.get(step.step_id)
                if res and not res.success:
                    execution.status = ExecutionStatus.FAILED
                    execution.error = f"Step {step.step_id} failed; chain aborted"
                    break
            i += 1
        with self._lock:
            execution.end_ts = _now_ts()
            execution.duration = execution.end_ts - execution.start_ts
            if execution.status == ExecutionStatus.RUNNING:
                execution.status = ExecutionStatus.SUCCESS
        return execution

    def get_chain_execution(self, chain_execution_id: str) -> Optional[ChainExecution]:
        """Fetch a chain execution record by identifier."""
        with self._lock:
            return self._chain_executions.get(chain_execution_id)

    # -- Pipeline builder ------------------------------------------------

    def create_pipeline(self, name: str, steps: List[PipelineStep],
                        description: str = "") -> ReasoningPipeline:
        """Create and register a reasoning pipeline."""
        with self._lock:
            pipeline = ReasoningPipeline(name=name, description=description, steps=list(steps))
            self._pipelines[pipeline.pipeline_id] = pipeline
            return pipeline

    def get_pipeline(self, pipeline_id: str) -> Optional[ReasoningPipeline]:
        """Fetch a pipeline by identifier."""
        with self._lock:
            return self._pipelines.get(pipeline_id)

    def execute_pipeline(self, pipeline_id: str, initial_inputs: Optional[Dict[str, Any]] = None,
                         caller_id: str = "") -> PipelineExecution:
        """Execute a reasoning pipeline; tool steps invoke tools, reasoning steps deliberate."""
        with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if not pipeline:
                return PipelineExecution(pipeline_id=pipeline_id, state=PipelineState.FAILED, error="Pipeline not found")
            pipeline.state = PipelineState.RUNNING
            pipeline.started_ts = _now_ts()
            execution = PipelineExecution(pipeline_id=pipeline_id, state=PipelineState.RUNNING, start_ts=_now_ts())
            self._pipeline_executions[execution.pipeline_execution_id] = execution
        context: Dict[str, ToolResult] = {"__init__": ToolResult(success=True, output=dict(initial_inputs or {}))}
        for step in pipeline.steps:
            if step.condition and not self._evaluate_condition(step.condition, context):
                skipped = ToolResult(success=True, output={"skipped": True}, metadata={"reason": "condition false"})
                execution.step_results[step.step_id] = skipped
                context[step.step_id] = skipped
                continue
            params = self._apply_input_mapping(step.input_mapping, context, step.parameters)
            if step.kind == StepKind.TOOL:
                result = self.execute_tool(step.tool_id, params, caller_id=caller_id,
                                           timeout=step.timeout, retry_count=step.retry_count)
            else:
                result = self._run_reasoning_step(step, context)
            execution.step_results[step.step_id] = result
            context[step.step_id] = result
            if not result.success:
                execution.state = PipelineState.FAILED
                execution.error = f"Step {step.step_id} failed: {result.error}"
                break
        with self._lock:
            execution.end_ts = _now_ts()
            execution.duration = execution.end_ts - execution.start_ts
            if execution.state == PipelineState.RUNNING:
                execution.state = PipelineState.COMPLETED
                pipeline.state = PipelineState.COMPLETED
            else:
                pipeline.state = execution.state
            pipeline.completed_ts = _now_ts()
        return execution

    def get_pipeline_execution(self, pipeline_execution_id: str) -> Optional[PipelineExecution]:
        """Fetch a pipeline execution record by identifier."""
        with self._lock:
            return self._pipeline_executions.get(pipeline_execution_id)

    # -- Schema validation -----------------------------------------------

    def validate_parameters(self, tool: ToolDefinition,
                            parameters: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Validate parameters against the tool schema; returns (ok, errors, coerced)."""
        errors: List[str] = []
        coerced: Dict[str, Any] = {}
        schema_by_name = {p.name: p for p in tool.parameters}
        for name, param in schema_by_name.items():
            if name not in parameters:
                if param.required:
                    if param.default is not None:
                        coerced[name] = param.default
                    else:
                        errors.append(f"Missing required parameter '{name}'")
                else:
                    coerced[name] = param.default
                continue
            value = parameters[name]
            ok, msg = self._check_type(value, param.type)
            if not ok:
                errors.append(f"Parameter '{name}' {msg}")
            else:
                coerced[name] = value
        for name, value in parameters.items():
            if name not in schema_by_name:
                errors.append(f"Unknown parameter '{name}' for tool '{tool.name}'")
                coerced[name] = value
        return (len(errors) == 0, errors, coerced)

    # -- Versioning ------------------------------------------------------

    def set_active_version(self, tool_id: str, version: str) -> bool:
        """Activate a previously snapshotted version of a tool."""
        with self._lock:
            tool = self.get_tool(tool_id)
            if not tool:
                return False
            versions = self._versions.get(tool.tool_id, [])
            target = next((v for v in versions if v.version == version), None)
            if not target:
                return False
            self._snapshot_version(tool)
            snap = target.snapshot
            tool.version = target.version
            tool.parameters = [ToolParameter(p.get("name", ""), p.get("type", "any"), p.get("required", False),
                                             p.get("default"), p.get("description", "")) for p in snap.get("parameters", [])]
            tool.handler = snap.get("handler", tool.handler)
            tool.tags = list(snap.get("tags", []))
            tool.description = snap.get("description", tool.description)
            for v in versions:
                v.active = (v.version == target.version)
            return True

    def get_versions(self, tool_id: str) -> List[ToolVersion]:
        """List all stored versions for a tool, newest first."""
        with self._lock:
            tool = self.get_tool(tool_id)
            key = tool.tool_id if tool else tool_id
            versions = list(self._versions.get(key, []))
            versions.sort(key=lambda v: v.created_ts, reverse=True)
            return versions

    def rollback_version(self, tool_id: str) -> bool:
        """Roll a tool back to the version prior to the currently active one."""
        with self._lock:
            tool = self.get_tool(tool_id)
            if not tool:
                return False
            versions = self._versions.get(tool.tool_id, [])
            if len(versions) < 2:
                return False
            active_index = next((i for i, v in enumerate(versions) if v.active), None)
            if active_index is None or active_index == len(versions) - 1:
                return False
            return self.set_active_version(tool_id, versions[active_index + 1].version)

    # -- Permissions -----------------------------------------------------

    def set_permission(self, tool_id: str, level: PermissionLevel,
                       caller_id: str = "*") -> Optional[ToolPermission]:
        """Create or replace a permission entry for a tool and caller."""
        if isinstance(level, str):
            try:
                level = PermissionLevel(level)
            except ValueError:
                level = PermissionLevel[level.upper()] if level.upper() in PermissionLevel.__members__ else PermissionLevel.PUBLIC
        with self._lock:
            tool = self.get_tool(tool_id)
            if not tool:
                return None
            for perm_id in self._permissions_by_tool.get(tool.tool_id, []):
                perm = self._permissions.get(perm_id)
                if perm and perm.caller_id == caller_id:
                    perm.level = level
                    return perm
            perm = ToolPermission(tool_id=tool.tool_id, tool_name=tool.name,
                                  level=level, caller_id=caller_id)
            self._permissions[perm.permission_id] = perm
            self._permissions_by_tool[tool.tool_id].append(perm.permission_id)
            return perm

    def check_permission(self, tool_id: str, caller_id: str = "") -> bool:
        """Check whether a caller may invoke a tool; public unless strict mode is on."""
        with self._lock:
            tool = self.get_tool(tool_id)
            if not tool:
                return False
            entries = self._permissions_by_tool.get(tool.tool_id, [])
            if not entries:
                # No explicit permission means public access unless strict mode.
                return not self._config.get("strict_permissions", False)
            for perm_id in entries:
                perm = self._permissions.get(perm_id)
                if perm and (perm.caller_id == "*" or perm.caller_id == caller_id):
                    return True
            return False

    # -- History and statistics ------------------------------------------

    def get_history(self, tool_id: Optional[str] = None, start_ts: Optional[float] = None,
                    end_ts: Optional[float] = None, success: Optional[bool] = None, limit: int = 100) -> List[ToolExecution]:
        """Query execution history by tool, time range, and success status."""
        with self._lock:
            items = list(self._executions)
        if tool_id:
            target = self.get_tool(tool_id)
            target_id = target.tool_id if target else tool_id
            items = [e for e in items if e.tool_id == target_id]
        if start_ts is not None:
            items = [e for e in items if e.start_ts >= start_ts]
        if end_ts is not None:
            items = [e for e in items if e.start_ts <= end_ts]
        if success is not None:
            items = [e for e in items if e.status == ExecutionStatus.SUCCESS] if success else [e for e in items if e.status != ExecutionStatus.SUCCESS]
        return list(reversed(items))[:limit]

    def clear_history(self) -> int:
        """Clear all execution history. Returns the number of records removed."""
        with self._lock:
            count = len(self._executions)
            self._executions.clear()
            self._executions_by_id.clear()
            return count

    def get_statistics(self, tool_id: Optional[str] = None) -> Dict[str, Any]:
        """Compute execution statistics across all tools or a single tool."""
        with self._lock:
            items = list(self._executions)
        if tool_id:
            target = self.get_tool(tool_id)
            target_id = target.tool_id if target else tool_id
            items = [e for e in items if e.tool_id == target_id]
        total = len(items)
        if total == 0:
            return {"total": 0, "success_rate": 0.0, "avg_duration": 0.0, "by_tool": {}}
        success_count = sum(1 for e in items if e.status == ExecutionStatus.SUCCESS)
        durations = [e.duration for e in items if e.duration > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        per_tool: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"total": 0, "success": 0, "duration_sum": 0.0})
        for e in items:
            entry = per_tool[e.tool_name]
            entry["total"] += 1
            if e.status == ExecutionStatus.SUCCESS:
                entry["success"] += 1
            entry["duration_sum"] += e.duration
        by_tool = {name: {"total": e["total"], "success_rate": _clamp(e["success"] / e["total"]),
                          "avg_duration": e["duration_sum"] / e["total"]} for name, e in per_tool.items()}
        return {"total": total, "success_rate": _clamp(success_count / total), "avg_duration": avg_duration, "by_tool": by_tool}

    # -- AI-driven optimization ------------------------------------------

    def ai_optimize_tools(self) -> List[Dict[str, Any]]:
        """Analyze execution history and produce improvement suggestions for tools."""
        stats = self.get_statistics()
        by_tool = stats.get("by_tool", {})
        with self._lock:
            tools_by_name = {t.name: t for t in self._tools.values()}
        suggestions: List[Dict[str, Any]] = []
        for name, entry in by_tool.items():
            tool = tools_by_name.get(name)
            if not tool:
                continue
            if entry["success_rate"] < 0.5 and entry["total"] >= 3:
                suggestions.append({"tool": name, "issue": "low_success_rate", "severity": "high",
                                    "detail": f"Success rate {entry['success_rate']:.2f} over {entry['total']} calls; "
                                              "consider adding retries or tightening parameter validation"})
            if entry["avg_duration"] > 1.0:
                suggestions.append({"tool": name, "issue": "slow_execution", "severity": "medium",
                                    "detail": f"Average duration {entry['avg_duration']:.3f}s; consider caching outputs or splitting the work"})
        for name, tool in tools_by_name.items():
            if name not in by_tool and tool.enabled:
                suggestions.append({"tool": name, "issue": "unused", "severity": "low",
                                    "detail": "Tool has no recorded executions; confirm it is still needed or disable it"})
        for name, tool in tools_by_name.items():
            if tool.enabled and len(tool.description.strip()) < 10:
                suggestions.append({"tool": name, "issue": "weak_description", "severity": "low",
                                    "detail": "Description is too short; supply a clearer summary so discovery can match it reliably"})
        if not suggestions:
            suggestions.append({"tool": "*", "issue": "none", "severity": "info",
                                "detail": "No improvement opportunities detected from current history"})
        return suggestions

    # -- Snapshot and serialization --------------------------------------

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a lightweight snapshot of the current state."""
        with self._lock:
            return {"status": self.get_status(),
                    "tools": [t.to_dict() for t in self.list_tools()],
                    "recent_executions": [e.to_dict() for e in list(self._executions)[-10:]],
                    "chains": [c.to_dict() for c in self._chains.values()],
                    "pipelines": [p.to_dict() for p in self._pipelines.values()]}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the entire framework state to a JSON-compatible dict."""
        with self._lock:
            return {"config": dict(self._config), "initialized": self._initialized,
                    "tools": [t.to_dict() for t in self._tools.values()],
                    "versions": {tid: [v.to_dict() for v in vs]
                                 for tid, vs in self._versions.items()},
                    "executions": [e.to_dict() for e in self._executions],
                    "chains": [c.to_dict() for c in self._chains.values()],
                    "chain_executions": [ce.to_dict() for ce in self._chain_executions.values()],
                    "pipelines": [p.to_dict() for p in self._pipelines.values()],
                    "pipeline_executions": [pe.to_dict() for pe in self._pipeline_executions.values()],
                    "permissions": [p.to_dict() for p in self._permissions.values()]}

    # -- Internal helpers ------------------------------------------------

    def _snapshot_version(self, tool: ToolDefinition) -> None:
        """Capture the current tool definition as a version snapshot."""
        version = ToolVersion(tool_id=tool.tool_id, version=tool.version,
                              snapshot=tool.to_dict(), active=True)
        versions = self._versions.setdefault(tool.tool_id, [])
        for v in versions:
            v.active = False
        versions.append(version)

    def _execute_internal(self, tool: ToolDefinition, parameters: Dict[str, Any],
                          execution: ToolExecution, timeout: Optional[float], retry_count: Optional[int]) -> ToolResult:
        """Run the resolved handler with timeout and retry, then finalize the record."""
        effective_timeout = timeout if timeout is not None else self._config.get("default_timeout", self.DEFAULT_TIMEOUT)
        effective_retry = retry_count if retry_count is not None else self._config.get("default_retry", 0)
        attempts = max(1, int(effective_retry) + 1)
        last_error, output, success = "", None, False
        start = _now_ts()
        for attempt in range(1, attempts + 1):
            execution.attempt = attempt
            try:
                output, err = self._invoke_handler(tool, parameters, effective_timeout)
                if err is not None:
                    raise err
                success, last_error = True, ""
                break
            except TimeoutError as e:
                last_error = f"Timeout after {effective_timeout}s: {e}"
            except Exception as e:  # noqa: BLE001 - intentional broad capture
                last_error = f"{type(e).__name__}: {e}"
            if attempt < attempts:
                time.sleep(0.01 * attempt)
        duration = _now_ts() - start
        result = ToolResult(success=success, output=output if success else None, error=last_error,
                            duration=duration, metadata={"tool": tool.name, "attempt": execution.attempt, "timeout": effective_timeout})
        with self._lock:
            execution.result = result
            execution.duration = duration
            execution.end_ts = _now_ts()
            execution.error = last_error
            if success:
                execution.status = ExecutionStatus.SUCCESS
            elif last_error.startswith("Timeout"):
                execution.status = ExecutionStatus.TIMEOUT
            else:
                execution.status = ExecutionStatus.FAILED
        return result

    def _invoke_handler(self, tool: ToolDefinition, parameters: Dict[str, Any],
                        timeout: float) -> Tuple[Any, Optional[Exception]]:
        """Resolve and invoke the handler inside a worker thread bounded by timeout."""
        handler = self._handlers.get(tool.handler) or self._default_handlers.get(tool.handler)
        if handler is None:
            return None, ValueError(f"No handler registered for '{tool.handler}'")
        holder: Dict[str, Any] = {}

        def _worker() -> None:
            try:
                holder["result"] = handler(parameters)
            except Exception as e:  # noqa: BLE001
                holder["error"] = e

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            return None, TimeoutError(f"handler '{tool.handler}' exceeded timeout")
        if "error" in holder:
            return None, holder["error"]
        return holder.get("result"), None

    def _run_chain_step(self, step: ChainStep, context: Dict[str, ToolResult],
                        caller_id: str, execution: ChainExecution) -> None:
        """Run a single chain step, honoring its condition and input mapping."""
        if step.condition and not self._evaluate_condition(step.condition, context):
            skipped = ToolResult(success=True, output={"skipped": True}, metadata={"reason": "condition false"})
            execution.step_results[step.step_id] = skipped
            context[step.step_id] = skipped
            return
        params = self._apply_input_mapping(step.input_mapping, context, step.parameters)
        result = self.execute_tool(step.tool_id, params, caller_id=caller_id,
                                   timeout=step.timeout, retry_count=step.retry_count)
        execution.step_results[step.step_id] = result
        context[step.step_id] = result

    def _run_parallel_steps(self, steps: List[ChainStep], context: Dict[str, ToolResult],
                            caller_id: str, execution: ChainExecution) -> None:
        """Run a group of chain steps concurrently on separate threads."""
        threads: List[threading.Thread] = []
        results_lock = threading.Lock()
        local_context = dict(context)

        def _work(step: ChainStep) -> None:
            if step.condition and not self._evaluate_condition(step.condition, local_context):
                res = ToolResult(success=True, output={"skipped": True})
            else:
                params = self._apply_input_mapping(step.input_mapping, local_context, step.parameters)
                res = self.execute_tool(step.tool_id, params, caller_id=caller_id,
                                        timeout=step.timeout, retry_count=step.retry_count)
            with results_lock:
                execution.step_results[step.step_id] = res
                context[step.step_id] = res

        for step in steps:
            t = threading.Thread(target=_work, args=(step,), daemon=True)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    def _run_reasoning_step(self, step: PipelineStep, context: Dict[str, ToolResult]) -> ToolResult:
        """Produce a deliberation output synthesized from prior step results."""
        prior_summary = [{"step": sid, "success": res.success, "output": res.output}
                         for sid, res in context.items() if sid != "__init__"]
        deliberation = {"prompt": step.reasoning_prompt, "inputs": prior_summary,
                        "conclusion": f"Synthesized {len(prior_summary)} prior result(s) for: {step.reasoning_prompt[:80]}",
                        "confidence": _clamp(0.5 + 0.1 * len(prior_summary))}
        return ToolResult(success=True, output=deliberation, duration=0.0,
                          metadata={"kind": "reasoning"})

    def _apply_input_mapping(self, mapping: Dict[str, str], context: Dict[str, ToolResult],
                             base_params: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for a step by resolving 'step_id.field' input mappings."""
        params: Dict[str, Any] = dict(base_params)
        for param_name, expr in mapping.items():
            value = self._resolve_mapping_expr(expr, context)
            if value is not None:
                params[param_name] = value
        return params

    def _resolve_mapping_expr(self, expr: str, context: Dict[str, ToolResult]) -> Any:
        """Resolve a mapping expression like 'spawn_entity.output.entity_id'."""
        parts = expr.split(".")
        if not parts:
            return None
        result = context.get(parts[0])
        if result is None:
            return None
        current: Any = {"success": result.success, "output": result.output,
                        "error": result.error}
        for part in parts[1:]:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, SimpleNamespace):
                current = getattr(current, part, None)
            else:
                current = None
            if current is None:
                return None
        return current

    def _evaluate_condition(self, condition: str, context: Dict[str, ToolResult]) -> bool:
        """Evaluate a condition expression against prior step results in a restricted namespace."""
        if not condition or not condition.strip():
            return True
        namespace: Dict[str, Any] = {"true": True, "false": False, "none": None,
                                     "True": True, "False": False, "None": None}
        for step_id, result in context.items():
            namespace[step_id.replace("-", "_")] = SimpleNamespace(
                success=result.success, error=result.error,
                output=_to_namespace(result.output))
        try:
            return bool(eval(condition, {"__builtins__": {}}, namespace))  # noqa: S307
        except Exception:
            return False

    def _check_type(self, value: Any, expected: str) -> Tuple[bool, str]:
        """Check that a value matches the declared type; returns (ok, error_message)."""
        if expected == "any":
            return True, ""
        type_map = {"string": (str,), "integer": (int,), "number": (int, float),
                    "boolean": (bool,), "array": (list,), "object": (dict,)}
        if expected not in type_map:
            return True, ""
        # Booleans are a subclass of int; exclude them for integer/number.
        if expected in ("integer", "number") and isinstance(value, bool):
            return False, f"expected {expected}, got bool"
        if not isinstance(value, type_map[expected]):
            return False, f"expected {expected}, got {type(value).__name__}"
        return True, ""

    # -- Default seed tools and handlers (game engine simulations) ------

    def _seed_default_tools(self) -> None:
        """Register a baseline set of game-engine tools. Each spec is a compact tuple:
        (name, description, category, handler, tags, [params])."""
        specs = [
            ("spawn_entity", "Instantiate a prefab entity at a world position", ToolCategory.ENTITY, "spawn_entity", ["entity", "spawn", "create"], [("prefab", "string", True, None, "Prefab asset name"), ("position", "array", True, [0, 0, 0], "World position [x,y,z]"), ("rotation", "array", False, [0, 0, 0], "Euler rotation"), ("scale", "number", False, 1.0, "Uniform scale factor")]),
            ("play_animation", "Play an animation clip on a target entity", ToolCategory.ANIMATION, "play_animation", ["animation", "entity"], [("entity_id", "string", True, None, "Target entity id"), ("animation_name", "string", True, None, "Animation clip name"), ("loop", "boolean", False, False, "Loop the animation"), ("speed", "number", False, 1.0, "Playback speed multiplier")]),
            ("set_material", "Assign a material asset to an entity", ToolCategory.MATERIAL, "set_material", ["material", "render"], [("entity_id", "string", True, None, "Target entity id"), ("material_name", "string", True, None, "Material asset name"), ("color", "string", False, "#ffffff", "Base color hex")]),
            ("trigger_event", "Fire a named game event with an optional payload", ToolCategory.EVENT, "trigger_event", ["event", "signal"], [("event_name", "string", True, None, "Game event name"), ("payload", "object", False, {}, "Event payload data"), ("target", "string", False, "global", "Event target scope")]),
            ("teleport_entity", "Move an entity instantly to a target position", ToolCategory.ENTITY, "teleport_entity", ["entity", "move"], [("entity_id", "string", True, None, "Target entity id"), ("position", "array", True, [0, 0, 0], "Target position [x,y,z]")]),
            ("apply_damage", "Apply damage to a target entity and return remaining hp", ToolCategory.ENTITY, "apply_damage", ["combat", "damage"], [("target_id", "string", True, None, "Target entity id"), ("amount", "number", True, None, "Damage amount"), ("damage_type", "string", False, "physical", "Damage type")]),
            ("spawn_particle", "Spawn a particle effect at a position for a duration", ToolCategory.ENTITY, "spawn_particle", ["fx", "particle"], [("effect_name", "string", True, None, "Particle effect asset"), ("position", "array", True, [0, 0, 0], "Spawn position"), ("duration", "number", False, 2.0, "Effect duration in seconds")]),
            ("play_sound", "Play a sound asset with volume and optional spatial position", ToolCategory.AUDIO, "play_sound", ["audio", "sound"], [("sound_name", "string", True, None, "Sound asset name"), ("volume", "number", False, 1.0, "Playback volume 0..1"), ("loop", "boolean", False, False, "Loop the sound"), ("position", "array", False, [], "Spatial position")]),
            ("set_light", "Configure intensity, color, and range of a light entity", ToolCategory.SCENE, "set_light", ["light", "scene"], [("light_id", "string", True, None, "Light entity id"), ("intensity", "number", False, 1.0, "Light intensity"), ("color", "string", False, "#ffffff", "Light color hex"), ("range", "number", False, 10.0, "Effective range")]),
            ("attach_component", "Attach a typed component to an entity with init properties", ToolCategory.ENTITY, "attach_component", ["component", "entity"], [("entity_id", "string", True, None, "Target entity id"), ("component_type", "string", True, None, "Component class name"), ("properties", "object", False, {}, "Init properties")]),
            ("set_ai_state", "Switch an AI-controlled entity to a new behavioral state", ToolCategory.AI, "set_ai_state", ["ai", "behavior"], [("entity_id", "string", True, None, "Target entity id"), ("state", "string", True, None, "New AI state name"), ("priority", "integer", False, 0, "State priority")]),
            ("show_ui", "Display a UI panel with parameters for a duration", ToolCategory.UI, "show_ui", ["ui", "hud"], [("panel_name", "string", True, None, "UI panel name"), ("params", "object", False, {}, "Panel parameters"), ("duration", "number", False, 0.0, "Display duration in seconds")]),
            ("save_state", "Persist current game state to a named save slot", ToolCategory.UTILITY, "save_state", ["save", "persistence"], [("slot_name", "string", True, None, "Save slot name"), ("overwrite", "boolean", False, True, "Overwrite existing slot")]),
        ]
        for name, desc, cat, handler, tags, params in specs:
            if name not in self._tools_by_name:
                self.register_tool(ToolDefinition(name=name, description=desc, category=cat,
                    handler=handler, tags=list(tags),
                    parameters=[ToolParameter(p[0], p[1], p[2], p[3], p[4]) for p in params]))

    def _h_spawn_entity(self, p: Dict[str, Any]) -> Dict[str, Any]:
        prefab = str(p.get("prefab", "default"))
        return {"entity_id": f"ent_{prefab}_{uuid.uuid4().hex[:6]}", "prefab": prefab, "position": p.get("position", [0, 0, 0]), "rotation": p.get("rotation", [0, 0, 0]), "scale": p.get("scale", 1.0)}

    def _h_play_animation(self, p: Dict[str, Any]) -> Dict[str, Any]:
        return {"entity_id": p.get("entity_id"), "animation": p.get("animation_name"), "loop": bool(p.get("loop", False)), "speed": float(p.get("speed", 1.0)), "started": True}

    def _h_set_material(self, p: Dict[str, Any]) -> Dict[str, Any]:
        return {"entity_id": p.get("entity_id"), "material": p.get("material_name"), "color": p.get("color", "#ffffff"), "applied": True}

    def _h_trigger_event(self, p: Dict[str, Any]) -> Dict[str, Any]:
        return {"event": p.get("event_name"), "target": p.get("target", "global"), "payload": p.get("payload", {}), "dispatched": True}

    def _h_teleport_entity(self, p: Dict[str, Any]) -> Dict[str, Any]:
        return {"entity_id": p.get("entity_id"), "position": p.get("position", [0, 0, 0]), "teleported": True}

    def _h_apply_damage(self, p: Dict[str, Any]) -> Dict[str, Any]:
        amount = float(p.get("amount", 0))
        return {"target_id": p.get("target_id"), "damage": amount, "damage_type": p.get("damage_type", "physical"), "remaining_hp": max(0.0, 100.0 - amount)}

    def _h_spawn_particle(self, p: Dict[str, Any]) -> Dict[str, Any]:
        effect = str(p.get("effect_name", "default"))
        return {"particle_id": f"fx_{effect}_{uuid.uuid4().hex[:6]}", "effect": effect, "position": p.get("position", [0, 0, 0]), "duration": float(p.get("duration", 2.0))}

    def _h_play_sound(self, p: Dict[str, Any]) -> Dict[str, Any]:
        sound = str(p.get("sound_name", "default"))
        return {"source_id": f"snd_{sound}_{uuid.uuid4().hex[:6]}", "sound": sound, "volume": _clamp(float(p.get("volume", 1.0))), "loop": bool(p.get("loop", False)), "position": p.get("position", [])}

    def _h_set_light(self, p: Dict[str, Any]) -> Dict[str, Any]:
        return {"light_id": p.get("light_id"), "intensity": float(p.get("intensity", 1.0)), "color": p.get("color", "#ffffff"), "range": float(p.get("range", 10.0)), "updated": True}

    def _h_attach_component(self, p: Dict[str, Any]) -> Dict[str, Any]:
        comp = str(p.get("component_type", "Component"))
        return {"component_id": f"comp_{comp}_{uuid.uuid4().hex[:6]}", "entity_id": p.get("entity_id"), "component_type": comp, "properties": p.get("properties", {}), "attached": True}

    def _h_set_ai_state(self, p: Dict[str, Any]) -> Dict[str, Any]:
        return {"entity_id": p.get("entity_id"), "state": p.get("state"), "priority": int(p.get("priority", 0)), "transitioned": True}

    def _h_show_ui(self, p: Dict[str, Any]) -> Dict[str, Any]:
        panel = str(p.get("panel_name", "default"))
        return {"panel_id": f"ui_{panel}_{uuid.uuid4().hex[:6]}", "panel": panel, "params": p.get("params", {}), "duration": float(p.get("duration", 0.0)), "shown": True}

    def _h_save_state(self, p: Dict[str, Any]) -> Dict[str, Any]:
        return {"slot": str(p.get("slot_name", "default")), "overwrite": bool(p.get("overwrite", True)), "saved": True, "timestamp": _now_ts()}


def get_tool_use_framework() -> ToolUseFramework:
    """Return the shared ToolUseFramework singleton instance."""
    return ToolUseFramework.get_instance()


__all__ = [
    "ToolUseFramework", "get_tool_use_framework",
    "ToolCategory", "ExecutionStatus", "PermissionLevel", "PipelineState", "StepKind",
    "ToolParameter", "ToolDefinition", "ToolResult", "ToolExecution",
    "ChainStep", "ToolChain", "ChainExecution",
    "PipelineStep", "ReasoningPipeline", "PipelineExecution",
    "ToolPermission", "ToolVersion",
]
