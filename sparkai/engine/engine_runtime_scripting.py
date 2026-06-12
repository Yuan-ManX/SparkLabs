from __future__ import annotations

import ast
import heapq
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

# Module-level time alias to allow deterministic testing via monkey-patching
_time_module = time


# =============================================================================
# Enums
# =============================================================================


class ScriptLanguage(Enum):
    """Supported scripting languages within the runtime."""

    PYTHON = "python"
    LUA = "lua"
    VISUAL_BLOCK = "visual_block"
    EXPRESSION = "expression"
    STATE_MACHINE = "state_machine"


class ScriptScope(Enum):
    """Visibility / ownership scope for a script definition or instance."""

    GLOBAL = "global"
    SCENE = "scene"
    ENTITY = "entity"
    COMPONENT = "component"
    SYSTEM = "system"
    UI = "ui"


class ExecutionMode(Enum):
    """How a script execution is dispatched."""

    IMMEDIATE = "immediate"
    DEFERRED = "deferred"
    COROUTINE = "coroutine"
    EVENT_DRIVEN = "event_driven"
    SCHEDULED = "scheduled"


class ScriptState(Enum):
    """Lifecycle state of a running script instance."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    TERMINATED = "terminated"
    RELOADING = "reloading"


class ScriptEventType(Enum):
    """Built-in event hooks that a script may subscribe to."""

    ON_START = "on_start"
    ON_UPDATE = "on_update"
    ON_COLLISION = "on_collision"
    ON_INPUT = "on_input"
    ON_TIMER = "on_timer"
    ON_TRIGGER = "on_trigger"
    ON_DESTROY = "on_destroy"
    ON_CUSTOM = "on_custom"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class ScriptDefinition:
    """Immutable-ish descriptor for a registered script."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    language: ScriptLanguage = ScriptLanguage.PYTHON
    scope: ScriptScope = ScriptScope.GLOBAL
    source_code: str = ""
    compiled: bool = False
    dependencies: List[str] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "language": self.language.value,
            "scope": self.scope.value,
            "source_code": self.source_code,
            "compiled": self.compiled,
            "dependencies": list(self.dependencies),
            "events": list(self.events),
            "metadata": dict(self.metadata),
            "version": self.version,
            "created_at": self.created_at,
        }


@dataclass
class ScriptInstance:
    """A live instance of a ScriptDefinition bound to an optional entity."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    script_id: str = ""
    target_entity_id: Optional[str] = None
    state: ScriptState = ScriptState.IDLE
    scope: ScriptScope = ScriptScope.GLOBAL
    variables: Dict[str, Any] = field(default_factory=dict)
    execution_count: int = 0
    last_executed: float = 0.0
    total_runtime_us: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "script_id": self.script_id,
            "target_entity_id": self.target_entity_id,
            "state": self.state.value,
            "scope": self.scope.value,
            "variables": dict(self.variables),
            "execution_count": self.execution_count,
            "last_executed": self.last_executed,
            "total_runtime_us": self.total_runtime_us,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }


@dataclass
class ScriptExecutionContext:
    """Per-frame execution context passed to a script instance."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    script_instance_id: str = ""
    mode: ExecutionMode = ExecutionMode.IMMEDIATE
    trigger_event: Optional[ScriptEventType] = None
    event_data: Dict[str, Any] = field(default_factory=dict)
    delta_time: float = 0.0
    frame_number: int = 0
    sandbox_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "script_instance_id": self.script_instance_id,
            "mode": self.mode.value,
            "trigger_event": self.trigger_event.value if self.trigger_event else None,
            "event_data": dict(self.event_data),
            "delta_time": self.delta_time,
            "frame_number": self.frame_number,
            "sandbox_id": self.sandbox_id,
        }


@dataclass
class ScriptSandbox:
    """Security policy that constrains a script execution environment."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    script_language: ScriptLanguage = ScriptLanguage.PYTHON
    max_memory_bytes: int = 16 * 1024 * 1024  # 16 MiB
    max_execution_time_ms: float = 50.0       # 50 ms hard cap
    allowed_modules: List[str] = field(default_factory=list)
    denied_modules: List[str] = field(default_factory=list)
    file_access: bool = False
    network_access: bool = False
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "script_language": self.script_language.value,
            "max_memory_bytes": self.max_memory_bytes,
            "max_execution_time_ms": self.max_execution_time_ms,
            "allowed_modules": list(self.allowed_modules),
            "denied_modules": list(self.denied_modules),
            "file_access": self.file_access,
            "network_access": self.network_access,
            "active": self.active,
        }


# =============================================================================
# Scheduled-task wrapper (internal)
# =============================================================================


@dataclass(order=True)
class _ScheduledTask:
    """Heap-friendly scheduled execution wrapper."""

    fire_at: float
    script_id: str = field(compare=False)
    context: ScriptExecutionContext = field(compare=False)
    repeat_interval_ms: float = field(default=0.0, compare=False)
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex, compare=False)


# =============================================================================
# EngineRuntimeScripting  (Singleton)
# =============================================================================


class EngineRuntimeScripting:
    """
    Sandboxed hot-reload runtime scripting for dynamic game logic.

    Provides registration, compilation, instantiation, execution,
    hot-reloading, event dispatch, variable management, and sandbox policies.
    """

    _instance: Optional[EngineRuntimeScripting] = None
    _lock = threading.RLock()

    def __new__(cls) -> EngineRuntimeScripting:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> EngineRuntimeScripting:
        """Return the global singleton; create it if necessary."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # Prevent re-initialisation when the singleton already exists
        if hasattr(self, "_initialised"):
            return
        self._initialised = True

        # ----- storage -----
        self._scripts: Dict[str, ScriptDefinition] = {}
        self._instances: Dict[str, ScriptInstance] = {}
        self._sandboxes: Dict[str, ScriptSandbox] = {}

        # ----- event system -----
        # script_id -> { event_type: List[handler_code] }
        self._event_listeners: Dict[str, Dict[str, List[str]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # ----- scheduler (min-heap of _ScheduledTask) -----
        self._scheduler: List[_ScheduledTask] = []

        # ----- global variable store (shared across instances) -----
        self._variable_store: Dict[str, Dict[str, Any]] = defaultdict(dict)

        # ----- statistics -----
        self._stats: Dict[str, Any] = {
            "total_executions": 0,
            "total_errors": 0,
            "hot_reloads": 0,
            "event_dispatches": 0,
        }

    # ------------------------------------------------------------------
    # Registration & Compilation
    # ------------------------------------------------------------------

    def register_script(
        self,
        name: str,
        language: ScriptLanguage,
        scope: ScriptScope,
        source_code: str,
        events: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> ScriptDefinition:
        """Register a new script definition in the runtime."""
        definition = ScriptDefinition(
            name=name,
            language=language,
            scope=scope,
            source_code=source_code,
            events=events or [],
            dependencies=dependencies or [],
        )
        self._scripts[definition.id] = definition
        return definition

    def compile_script(self, script_id: str) -> ScriptDefinition:
        """Validate script syntax and mark it as compiled.

        Raises ValueError on syntax errors.
        """
        definition = self._scripts.get(script_id)
        if definition is None:
            raise ValueError(f"ScriptDefinition '{script_id}' not found")

        if definition.language == ScriptLanguage.PYTHON:
            try:
                ast.parse(definition.source_code)
            except SyntaxError as exc:
                definition.compiled = False
                raise ValueError(
                    f"Python syntax error in '{definition.name}': {exc}"
                ) from exc

        # For non-Python languages we perform a lightweight structure check.
        elif definition.language == ScriptLanguage.LUA:
            _validate_lua_syntax(definition.source_code, definition.name)

        elif definition.language == ScriptLanguage.EXPRESSION:
            _validate_expression_syntax(definition.source_code, definition.name)

        definition.compiled = True
        definition.version += 1
        return definition

    # ------------------------------------------------------------------
    # Instantiation
    # ------------------------------------------------------------------

    def instantiate_script(
        self,
        script_id: str,
        target_entity_id: Optional[str] = None,
        initial_variables: Optional[Dict[str, Any]] = None,
    ) -> ScriptInstance:
        """Create a new runnable instance of a registered script."""
        definition = self._scripts.get(script_id)
        if definition is None:
            raise ValueError(f"ScriptDefinition '{script_id}' not found")

        if not definition.compiled:
            raise RuntimeError(
                f"Script '{definition.name}' is not compiled. "
                f"Call compile_script() first."
            )

        instance = ScriptInstance(
            script_id=script_id,
            target_entity_id=target_entity_id,
            scope=definition.scope,
            variables=dict(initial_variables or {}),
        )
        self._instances[instance.id] = instance
        return instance

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_script(
        self, instance_id: str, context: ScriptExecutionContext
    ) -> Dict[str, Any]:
        """Execute a script instance within the supplied context.

        Returns a result dictionary containing at minimum:
            success (bool), error (str|None), output (Any), runtime_us (float)
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            return {"success": False, "error": "Instance not found", "output": None, "runtime_us": 0.0}

        if instance.state in (ScriptState.PAUSED, ScriptState.TERMINATED, ScriptState.ERROR):
            return {"success": False, "error": f"Instance is {instance.state.value}", "output": None, "runtime_us": 0.0}

        definition = self._scripts.get(instance.script_id)
        if definition is None:
            return {"success": False, "error": "Parent script definition vanished", "output": None, "runtime_us": 0.0}

        sandbox = None
        if context.sandbox_id:
            sandbox = self._sandboxes.get(context.sandbox_id)

        start_ns = _time_module.perf_counter_ns()

        try:
            instance.state = ScriptState.RUNNING

            if definition.language == ScriptLanguage.PYTHON:
                output = _execute_python_script(
                    definition.source_code,
                    instance.variables,
                    context,
                )
            elif definition.language == ScriptLanguage.EXPRESSION:
                output = _evaluate_expression(
                    definition.source_code,
                    instance.variables,
                    context,
                )
            elif definition.language == ScriptLanguage.VISUAL_BLOCK:
                output = _execute_visual_block(
                    definition.events,
                    instance.variables,
                    context,
                )
            elif definition.language == ScriptLanguage.STATE_MACHINE:
                output = _execute_state_machine(
                    definition.source_code,
                    instance.variables,
                    context,
                )
            elif definition.language == ScriptLanguage.LUA:
                output = _execute_lua_script(
                    definition.source_code,
                    instance.variables,
                    context,
                )
            else:
                output = None

            # Enforce sandbox time cap (soft check — best effort).
            if sandbox and sandbox.active:
                elapsed_ns = _time_module.perf_counter_ns() - start_ns
                elapsed_ms = elapsed_ns / 1_000_000.0
                if elapsed_ms > sandbox.max_execution_time_ms:
                    instance.state = ScriptState.ERROR
                    instance.last_error = (
                        f"Sandbox time cap exceeded: {elapsed_ms:.2f} ms "
                        f"(limit {sandbox.max_execution_time_ms} ms)"
                    )
                    instance.error_count += 1
                    self._stats["total_errors"] += 1
                    return {
                        "success": False,
                        "error": instance.last_error,
                        "output": None,
                        "runtime_us": elapsed_ms * 1_000.0,
                    }

            end_ns = _time_module.perf_counter_ns()
            runtime_us = (end_ns - start_ns) / 1_000.0

            instance.execution_count += 1
            instance.last_executed = _time_module.time()
            instance.total_runtime_us += runtime_us
            instance.state = ScriptState.IDLE
            self._stats["total_executions"] += 1

            return {"success": True, "error": None, "output": output, "runtime_us": runtime_us}

        except Exception as exc:
            end_ns = _time_module.perf_counter_ns()
            runtime_us = (end_ns - start_ns) / 1_000.0
            instance.state = ScriptState.ERROR
            instance.last_error = str(exc)
            instance.error_count += 1
            instance.total_runtime_us += runtime_us
            self._stats["total_errors"] += 1
            return {"success": False, "error": str(exc), "output": None, "runtime_us": runtime_us}

    # ------------------------------------------------------------------
    # Hot-reload
    # ------------------------------------------------------------------

    def hot_reload(self, script_id: str, new_source: str) -> ScriptDefinition:
        """Replace a script's source at runtime without destroying its instances.

        Existing instances are placed into RELOADING state while the new source
        is validated; they are reset to IDLE afterwards.
        """
        definition = self._scripts.get(script_id)
        if definition is None:
            raise ValueError(f"ScriptDefinition '{script_id}' not found")

        # Mark all related instances as reloading
        affected_instances: List[str] = []
        for iid, inst in self._instances.items():
            if inst.script_id == script_id:
                inst.state = ScriptState.RELOADING
                affected_instances.append(iid)

        # Swap source and re-compile
        definition.source_code = new_source
        definition.compiled = False
        try:
            self.compile_script(script_id)
        except ValueError:
            # Compilation failed — keep instances in ERROR state
            for iid in affected_instances:
                self._instances[iid].state = ScriptState.ERROR
                self._instances[iid].last_error = "Hot-reload compilation failed"
            raise

        # compile_script already bumped version — only bump once more for the reload
        definition.version += 1
        self._stats["hot_reloads"] += 1

        # Restore instances to IDLE
        for iid in affected_instances:
            self._instances[iid].state = ScriptState.IDLE

        return definition

    # ------------------------------------------------------------------
    # Event System
    # ------------------------------------------------------------------

    def trigger_event(
        self,
        script_id: str,
        event_type: ScriptEventType,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Fire an event on a script, running all registered handlers.

        Returns a list of result dictionaries, one per handler.
        """
        self._stats["event_dispatches"] += 1
        results: List[Dict[str, Any]] = []
        data = event_data or {}

        definition = self._scripts.get(script_id)
        if definition is None:
            return results

        event_key = event_type.value
        handlers = self._event_listeners.get(script_id, {}).get(event_key, [])

        # Also execute any matching events declared on the definition itself.
        for evt in definition.events:
            if evt.get("type") == event_key:
                handlers.append(evt.get("code", ""))

        for handler_code in handlers:
            if not handler_code:
                continue
            # Create a temporary execution context for each handler.
            ctx = ScriptExecutionContext(
                mode=ExecutionMode.EVENT_DRIVEN,
                trigger_event=event_type,
                event_data=data,
            )
            # Find or create a lightweight instance for this handler.
            for inst in self._instances.values():
                if inst.script_id == script_id:
                    result = self.execute_script(inst.id, ctx)
                    results.append(result)
                    break

        return results

    def register_event_handler(
        self, script_id: str, event_type: ScriptEventType, handler_code: str
    ) -> bool:
        """Register a code snippet as a handler for a specific event type."""
        definition = self._scripts.get(script_id)
        if definition is None:
            return False

        event_key = event_type.value
        self._event_listeners[script_id][event_key].append(handler_code)
        return True

    # ------------------------------------------------------------------
    # Pause / Resume
    # ------------------------------------------------------------------

    def pause_instance(self, instance_id: str) -> bool:
        """Pause a running or idle script instance."""
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        if instance.state == ScriptState.IDLE or instance.state == ScriptState.RUNNING:
            instance.state = ScriptState.PAUSED
            return True
        return False

    def resume_instance(self, instance_id: str) -> bool:
        """Resume a paused script instance."""
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        if instance.state == ScriptState.PAUSED:
            instance.state = ScriptState.IDLE
            return True
        return False

    # ------------------------------------------------------------------
    # Variable Management
    # ------------------------------------------------------------------

    def set_variable(self, instance_id: str, name: str, value: Any) -> bool:
        """Set a variable on a specific script instance."""
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.variables[name] = value
        return True

    def get_variable(self, instance_id: str, name: str) -> Any:
        """Retrieve a variable from a specific script instance.

        Returns None when the instance or variable does not exist.
        """
        instance = self._instances.get(instance_id)
        if instance is None:
            return None
        return instance.variables.get(name)

    # ------------------------------------------------------------------
    # Sandbox Management
    # ------------------------------------------------------------------

    def create_sandbox(
        self,
        language: ScriptLanguage,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> ScriptSandbox:
        """Create an execution sandbox with optional custom constraints."""
        constraints = constraints or {}
        sandbox = ScriptSandbox(
            script_language=language,
            max_memory_bytes=constraints.get("max_memory_bytes", 16 * 1024 * 1024),
            max_execution_time_ms=constraints.get("max_execution_time_ms", 50.0),
            allowed_modules=constraints.get("allowed_modules", []),
            denied_modules=constraints.get("denied_modules", []),
            file_access=constraints.get("file_access", False),
            network_access=constraints.get("network_access", False),
            active=True,
        )
        self._sandboxes[sandbox.id] = sandbox
        return sandbox

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------

    def schedule_execution(
        self,
        script_id: str,
        delay_ms: float,
        repeat: bool = False,
        context: Optional[ScriptExecutionContext] = None,
    ) -> str:
        """Schedule a future or repeating execution for a script.

        Returns a task_id that can be used to cancel later.
        """
        if script_id not in self._scripts:
            raise ValueError(f"ScriptDefinition '{script_id}' not found")

        ctx = context or ScriptExecutionContext(
            mode=ExecutionMode.SCHEDULED,
        )

        fire_at = _time_module.time() + delay_ms / 1_000.0
        repeat_interval = delay_ms if repeat else 0.0

        task = _ScheduledTask(
            fire_at=fire_at,
            script_id=script_id,
            context=ctx,
            repeat_interval_ms=repeat_interval,
        )
        heapq.heappush(self._scheduler, task)
        return task.task_id

    def tick_scheduler(self) -> int:
        """Process all overdue scheduled tasks. Call once per frame.

        Returns the number of tasks that fired.
        """
        now = _time_module.time()
        fired = 0

        # Collect tasks that are due
        due: List[_ScheduledTask] = []
        while self._scheduler and self._scheduler[0].fire_at <= now:
            due.append(heapq.heappop(self._scheduler))

        for task in due:
            # Execute via any existing instance
            executed = False
            for inst in self._instances.values():
                if inst.script_id == task.script_id:
                    self.execute_script(inst.id, task.context)
                    executed = True
                    fired += 1
                    break

            if not executed and task.script_id in self._scripts:
                # No instance yet — create a transient one.
                try:
                    inst = self.instantiate_script(task.script_id)
                    self.execute_script(inst.id, task.context)
                    fired += 1
                except RuntimeError:
                    pass  # script not compiled

            # Re-schedule repeaters
            if task.repeat_interval_ms > 0:
                task.fire_at = now + task.repeat_interval_ms / 1_000.0
                heapq.heappush(self._scheduler, task)

        return fired

    # ------------------------------------------------------------------
    # Query / Status
    # ------------------------------------------------------------------

    def list_scripts(
        self,
        scope: Optional[ScriptScope] = None,
        language: Optional[ScriptLanguage] = None,
    ) -> List[Dict[str, Any]]:
        """Return a filtered list of registered script summaries."""
        result: List[Dict[str, Any]] = []
        for definition in self._scripts.values():
            if scope is not None and definition.scope != scope:
                continue
            if language is not None and definition.language != language:
                continue
            result.append(definition.to_dict())
        return result

    def get_status(self) -> Dict[str, Any]:
        """Return an aggregate status snapshot suitable for debug overlays."""
        running = sum(
            1 for i in self._instances.values() if i.state == ScriptState.RUNNING
        )
        paused = sum(
            1 for i in self._instances.values() if i.state == ScriptState.PAUSED
        )
        errors = sum(
            1 for i in self._instances.values() if i.state == ScriptState.ERROR
        )
        variable_count = sum(
            len(i.variables) for i in self._instances.values()
        )
        # Count unique event keys across all listeners
        event_keys: set = set()
        for listeners in self._event_listeners.values():
            event_keys.update(listeners.keys())

        return {
            "scripts": len(self._scripts),
            "instances": len(self._instances),
            "running": running,
            "paused": paused,
            "errors": errors,
            "sandboxes": len(self._sandboxes),
            "events_registered": len(event_keys),
            "scheduled_count": len(self._scheduler),
            "variable_count": variable_count,
            "total_executions": self._stats["total_executions"],
            "total_errors": self._stats["total_errors"],
            "hot_reloads": self._stats["hot_reloads"],
            "event_dispatches": self._stats["event_dispatches"],
        }

    def reset(self) -> None:
        """Clear all state. Useful for editor teardown / testing."""
        self._scripts.clear()
        self._instances.clear()
        self._sandboxes.clear()
        self._event_listeners.clear()
        self._scheduler.clear()
        self._variable_store.clear()
        self._stats = {
            "total_executions": 0,
            "total_errors": 0,
            "hot_reloads": 0,
            "event_dispatches": 0,
        }


# =============================================================================
# Module-level accessor
# =============================================================================


def get_runtime_scripting() -> EngineRuntimeScripting:
    """Return the global EngineRuntimeScripting singleton."""
    return EngineRuntimeScripting.get_instance()


# =============================================================================
# Internal execution helpers
# =============================================================================


def _validate_lua_syntax(source: str, name: str) -> None:
    """Rudimentary Lua syntax check.

    Real implementation would shell out to `luac -p` or embed a Lua parser.
    """
    if not isinstance(source, str):
        raise ValueError(f"Lua source for '{name}' must be a string")
    # Basic structural validation: balanced keywords
    keywords = {"function": "end", "if": "end", "do": "end", "while": "end",
                "for": "end", "repeat": "until"}
    stack: List[str] = []
    tokens = source.split()
    for token in tokens:
        stripped = token.strip("(),;\t\n\r")
        if stripped in keywords:
            stack.append(stripped)
        elif stripped in keywords.values():
            if not stack:
                raise ValueError(
                    f"Lua syntax error in '{name}': unexpected '{stripped}'"
                )
            expected_keyword = stack.pop()
            expected_close = keywords.get(expected_keyword)
            if stripped != expected_close:
                raise ValueError(
                    f"Lua syntax error in '{name}': expected '{expected_close}' "
                    f"but got '{stripped}'"
                )
    if stack:
        raise ValueError(
            f"Lua syntax error in '{name}': unclosed block(s): {stack}"
        )


def _validate_expression_syntax(source: str, name: str) -> None:
    """Validate an expression (simple arithmetic / logic check)."""
    if not source.strip():
        raise ValueError(f"Expression for '{name}' is empty")
    # Attempt to parse as a Python expression for validation
    try:
        ast.parse(source.strip(), mode="eval")
    except SyntaxError as exc:
        raise ValueError(
            f"Expression syntax error in '{name}': {exc}"
        ) from exc


def _execute_python_script(
    source: str,
    variables: Dict[str, Any],
    context: ScriptExecutionContext,
) -> Any:
    """Execute a Python script inside a restricted namespace."""
    local_ns: Dict[str, Any] = {
        "variables": variables,
        "context": context,
        "delta": context.delta_time,
        "frame": context.frame_number,
    }
    try:
        exec(source, {"__builtins__": _restricted_builtins()}, local_ns)
    except Exception:
        raise
    return local_ns.get("result", None)


def _evaluate_expression(
    source: str,
    variables: Dict[str, Any],
    context: ScriptExecutionContext,
) -> Any:
    """Evaluate a mathematical / logical expression."""
    local_ns: Dict[str, Any] = {
        "variables": variables,
        "context": context,
        "delta": context.delta_time,
    }
    try:
        tree = ast.parse(source.strip(), mode="eval")
        compiled = compile(tree, "<expression>", "eval")
        return eval(compiled, {"__builtins__": _restricted_builtins()}, local_ns)
    except Exception:
        raise


def _execute_visual_block(
    events: List[Dict[str, Any]],
    variables: Dict[str, Any],
    context: ScriptExecutionContext,
) -> Any:
    """Execute a visual-block event sheet.

    Each block is a dict with keys: 'condition', 'action', 'params'.
    """
    last_result: Any = None
    for block in events:
        cond = block.get("condition", "")
        action = block.get("action", "")
        params = block.get("params", {})

        # Evaluate condition (empty condition always passes)
        if cond:
            try:
                tree = ast.parse(cond.strip(), mode="eval")
                compiled = compile(tree, "<block_condition>", "eval")
                cond_pass = eval(
                    compiled,
                    {"__builtins__": _restricted_builtins()},
                    {"variables": variables, **params},
                )
            except Exception:
                cond_pass = False
            if not cond_pass:
                continue

        # Execute action snippet
        if action:
            try:
                local_ns = {"variables": variables, "context": context, **params}
                exec(action, {"__builtins__": _restricted_builtins()}, local_ns)
                last_result = local_ns.get("result", None)
            except Exception:
                raise
    return last_result


def _execute_state_machine(
    source: str,
    variables: Dict[str, Any],
    context: ScriptExecutionContext,
) -> Any:
    """Execute a state-machine definition.

    The source is expected to be a JSON / dict-like string defining states and
    transitions.  The runtime looks up the current state in `variables` and
    evaluates transition conditions.
    """
    import json as _json

    try:
        sm_def = _json.loads(source)
    except _json.JSONDecodeError as exc:
        raise ValueError(f"State-machine JSON parse error: {exc}") from exc

    current_state = variables.get("_sm_state", sm_def.get("initial", "default"))
    states = sm_def.get("states", {})

    if current_state not in states:
        return None

    state_cfg = states[current_state]
    # Check transitions in order
    for transition in state_cfg.get("transitions", []):
        target = transition.get("target")
        cond_expr = transition.get("condition", "")
        if not target:
            continue
        if cond_expr:
            try:
                tree = ast.parse(cond_expr.strip(), mode="eval")
                compiled = compile(tree, "<transition_condition>", "eval")
                should_transition = eval(
                    compiled,
                    {"__builtins__": _restricted_builtins()},
                    {"variables": variables, "context": context},
                )
            except Exception:
                should_transition = False
            if not should_transition:
                continue
        # Execute transition actions
        for action_code in transition.get("actions", []):
            local_ns: Dict[str, Any] = {"variables": variables, "context": context}
            exec(action_code, {"__builtins__": _restricted_builtins()}, local_ns)
        variables["_sm_state"] = target
        return target

    # Execute current state's on_update
    for action_code in state_cfg.get("on_update", []):
        local_ns: Dict[str, Any] = {"variables": variables, "context": context}
        exec(action_code, {"__builtins__": _restricted_builtins()}, local_ns)

    return current_state


def _execute_lua_script(
    source: str,
    variables: Dict[str, Any],
    context: ScriptExecutionContext,
) -> Any:
    """Execute a Lua script stub.

    In a full engine this would embed Lua via lupa or a similar binding.
    For now we store the intent and return a no-op marker.
    """
    # Placeholder — a real implementation would invoke an embedded Lua runtime.
    return {"_lua_pending": True, "source_length": len(source)}


def _restricted_builtins() -> Dict[str, Any]:
    """Return a restricted set of builtins available to scripts."""
    import builtins

    safe: Dict[str, Any] = {
        # Types
        "bool": builtins.bool,
        "int": builtins.int,
        "float": builtins.float,
        "str": builtins.str,
        "list": builtins.list,
        "dict": builtins.dict,
        "tuple": builtins.tuple,
        "set": builtins.set,
        "range": builtins.range,
        "len": builtins.len,
        "enumerate": builtins.enumerate,
        "zip": builtins.zip,
        "map": builtins.map,
        "filter": builtins.filter,
        "sorted": builtins.sorted,
        "min": builtins.min,
        "max": builtins.max,
        "sum": builtins.sum,
        "abs": builtins.abs,
        "round": builtins.round,
        "any": builtins.any,
        "all": builtins.all,
        "isinstance": builtins.isinstance,
        "type": builtins.type,
        "print": builtins.print,
        # Math helpers
        "pow": builtins.pow,
        "divmod": builtins.divmod,
    }
    return safe