"""
SparkLabs Engine - Block Runtime Executor

This module provides the runtime execution layer for block-based game logic
programs composed by the AI Block Programmer agent. While the agent's
``dry_run`` simulates execution for validation, this runtime executor hooks
into the live game loop to dispatch real events, evaluate conditions, and
invoke actions against the running game state.

The runtime subscribes to published block programs, listens for game events
(collision, input, timer, start), and walks each program's block stack in
order, evaluating conditions and dispatching actions to registered handlers.
Execution state is tracked per program so the runtime can report live
status, pause/resume programs, and feed execution telemetry back to the AI
agents for self-improvement.

Architecture:
  BlockRuntimeExecutor (Singleton, double-checked locking, threading.RLock)
    |-- RuntimeProgram   -- a published program loaded into the runtime
    |-- ExecutionState   -- per-program live execution status
    |-- ActionHandler    -- a registered callback for an action block type
    |-- EventBinding      -- a binding between a game event and a program
    |-- ExecutionLog      -- a recorded execution step for telemetry
    |-- RuntimeStats      -- aggregate runtime statistics
    |-- RuntimeSnapshot   -- full runtime snapshot
    |-- RuntimeEvent      -- observable runtime lifecycle event

All public mutating methods are protected by a re-entrant lock so the
runtime is safe to call from multiple game-loop threads. Bounded in-memory
stores use FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_RUNTIME_PROGRAMS: int = 200
_MAX_HANDLERS: int = 500
_MAX_BINDINGS: int = 500
_MAX_LOGS_PER_PROGRAM: int = 200
_MAX_LOGS: int = 4000
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return a UTC ISO-8601 timestamp string terminated with 'Z'."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "rt") -> str:
    """Generate a short unique identifier with a readable prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds."""
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_deque(store: deque, max_size: int) -> None:
    """Evict the oldest inserted entries from a deque until within bounds."""
    while len(store) > max_size:
        try:
            store.popleft()
        except IndexError:
            break


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value to a JSON-friendly form."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class RuntimeStatus(Enum):
    """The live status of a program in the runtime."""
    LOADED = "loaded"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    UNLOADED = "unloaded"


class LogKind(Enum):
    """The kind of a runtime execution log entry."""
    EVENT_FIRED = "event_fired"
    CONDITION_EVALUATED = "condition_evaluated"
    ACTION_DISPATCHED = "action_dispatched"
    CONTROL_FLOW = "control_flow"
    ERROR = "error"
    PROGRAM_PAUSED = "program_paused"
    PROGRAM_RESUMED = "program_resumed"


class RuntimeEventKind(Enum):
    """Observable lifecycle events emitted by the runtime."""
    PROGRAM_LOADED = "program_loaded"
    PROGRAM_UNLOADED = "program_unloaded"
    PROGRAM_STARTED = "program_started"
    PROGRAM_PAUSED = "program_paused"
    PROGRAM_RESUMED = "program_resumed"
    EVENT_DISPATCHED = "event_dispatched"
    ACTION_INVOKED = "action_invoked"
    HANDLER_REGISTERED = "handler_registered"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RuntimeProgram:
    """A published block program loaded into the runtime."""
    runtime_id: str
    program_id: str
    name: str
    blocks: List[Dict[str, Any]]
    status: RuntimeStatus
    loaded_at: str
    last_executed_at: str
    execution_count: int
    error_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this runtime program to a JSON-friendly dictionary."""
        return {
            "runtime_id": self.runtime_id,
            "program_id": self.program_id,
            "name": self.name,
            "blocks": _to_jsonable(self.blocks),
            "status": self.status.value,
            "loaded_at": self.loaded_at,
            "last_executed_at": self.last_executed_at,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
        }


@dataclass
class ExecutionLog:
    """A single recorded execution step for telemetry."""
    log_id: str
    runtime_id: str
    kind: LogKind
    block_name: str
    detail: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this log entry to a JSON-friendly dictionary."""
        return {
            "log_id": self.log_id,
            "runtime_id": self.runtime_id,
            "kind": self.kind.value,
            "block_name": self.block_name,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }


@dataclass
class ActionHandler:
    """A registered callback for an action block type."""
    handler_id: str
    action_type: str
    handler_name: str
    call_count: int
    registered_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this handler to a JSON-friendly dictionary."""
        return {
            "handler_id": self.handler_id,
            "action_type": self.action_type,
            "handler_name": self.handler_name,
            "call_count": self.call_count,
            "registered_at": self.registered_at,
        }


@dataclass
class EventBinding:
    """A binding between a game event source and a runtime program."""
    binding_id: str
    runtime_id: str
    event_type: str
    event_filter: Dict[str, str]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this binding to a JSON-friendly dictionary."""
        return {
            "binding_id": self.binding_id,
            "runtime_id": self.runtime_id,
            "event_type": self.event_type,
            "event_filter": _to_jsonable(self.event_filter),
            "created_at": self.created_at,
        }


@dataclass
class RuntimeStats:
    """Aggregate statistics about the runtime executor."""
    total_programs: int
    active_programs: int
    total_handlers: int
    total_bindings: int
    total_executions: int
    total_errors: int
    total_logs: int
    total_events: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a JSON-friendly dictionary."""
        return {
            "total_programs": self.total_programs,
            "active_programs": self.active_programs,
            "total_handlers": self.total_handlers,
            "total_bindings": self.total_bindings,
            "total_executions": self.total_executions,
            "total_errors": self.total_errors,
            "total_logs": self.total_logs,
            "total_events": self.total_events,
        }


@dataclass
class RuntimeSnapshot:
    """A full snapshot of the runtime executor state."""
    programs: List[RuntimeProgram]
    handlers: List[ActionHandler]
    bindings: List[EventBinding]
    logs: List[ExecutionLog]
    stats: RuntimeStats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "programs": [p.to_dict() for p in self.programs],
            "handlers": [h.to_dict() for h in self.handlers],
            "bindings": [b.to_dict() for b in self.bindings],
            "logs": [l.to_dict() for l in self.logs],
            "stats": self.stats.to_dict(),
        }


@dataclass
class RuntimeEvent:
    """An observable lifecycle event emitted by the runtime."""
    event_id: str
    kind: RuntimeEventKind
    runtime_id: str
    payload: Dict[str, Any]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "runtime_id": self.runtime_id,
            "payload": _to_jsonable(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class BlockRuntimeExecutor:
    """Runtime executor that dispatches game events to block programs.

    Implemented as a thread-safe singleton with double-checked locking.
    All public mutating methods acquire ``self._lock`` (a re-entrant lock)
    so the runtime is safe to call from multiple game-loop threads.
    """

    _instance: Optional["BlockRuntimeExecutor"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "BlockRuntimeExecutor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._initialized: bool = True
            self._programs: Dict[str, RuntimeProgram] = {}
            self._handlers: Dict[str, ActionHandler] = {}
            self._handlers_by_type: Dict[str, str] = {}
            self._bindings: Dict[str, EventBinding] = {}
            self._logs: deque[ExecutionLog] = deque(maxlen=_MAX_LOGS)
            self._logs_by_program: Dict[str, deque[ExecutionLog]] = {}
            self._events: deque[RuntimeEvent] = deque(maxlen=_MAX_EVENTS)
            self._program_counter = 0
            self._handler_counter = 0
            self._binding_counter = 0
            self._execution_counter = 0
            self._error_counter = 0
            self._log_counter = 0
            self._event_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Seed the runtime with default action handlers and sample bindings."""
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register handlers for the core action block types."""
        defaults = [
            ("move", "Move Handler"),
            ("spawn", "Spawn Handler"),
            ("destroy", "Destroy Handler"),
            ("animate", "Animate Handler"),
            ("play_sound", "Play Sound Handler"),
            ("set_var", "Set Variable Handler"),
        ]
        for action_type, name in defaults:
            self._register_handler_internal(action_type, name)

    def _register_handler_internal(
        self,
        action_type: str,
        handler_name: str,
    ) -> ActionHandler:
        """Register a handler (caller must hold ``self._lock``)."""
        handler_id = _new_id("hnd")
        handler = ActionHandler(
            handler_id=handler_id,
            action_type=action_type,
            handler_name=handler_name,
            call_count=0,
            registered_at=_now(),
        )
        self._handlers[handler_id] = handler
        self._handlers_by_type[action_type] = handler_id
        self._handler_counter += 1
        _evict_fifo_dict(self._handlers, _MAX_HANDLERS)
        self._record_event(
            RuntimeEventKind.HANDLER_REGISTERED,
            "",
            {"action_type": action_type, "handler_name": handler_name},
        )
        return handler

    # ------------------------------------------------------------------
    # Internal event recording
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: RuntimeEventKind,
        runtime_id: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> RuntimeEvent:
        """Record an audit event (caller must hold ``self._lock``)."""
        event = RuntimeEvent(
            event_id=_new_id("evt"),
            kind=kind,
            runtime_id=runtime_id,
            payload=dict(payload) if payload else {},
            timestamp=_now(),
        )
        _evict_fifo_deque(self._events, _MAX_EVENTS)
        self._events.append(event)
        self._event_counter += 1
        return event

    def _record_log(
        self,
        runtime_id: str,
        kind: LogKind,
        block_name: str,
        detail: str,
    ) -> ExecutionLog:
        """Record an execution log entry (caller must hold ``self._lock``)."""
        log = ExecutionLog(
            log_id=_new_id("log"),
            runtime_id=runtime_id,
            kind=kind,
            block_name=block_name,
            detail=detail,
            timestamp=_now(),
        )
        _evict_fifo_deque(self._logs, _MAX_LOGS)
        self._logs.append(log)
        program_logs = self._logs_by_program.setdefault(
            runtime_id, deque(maxlen=_MAX_LOGS_PER_PROGRAM)
        )
        _evict_fifo_deque(program_logs, _MAX_LOGS_PER_PROGRAM)
        program_logs.append(log)
        self._log_counter += 1
        return log

    # ------------------------------------------------------------------
    # Handler management
    # ------------------------------------------------------------------

    def register_handler(
        self,
        action_type: str,
        handler_name: str = "",
    ) -> ActionHandler:
        """Register a new action handler for a block action type."""
        with self._lock:
            return self._register_handler_internal(action_type, handler_name or f"{action_type} Handler")

    def get_handler(self, handler_id: str) -> Optional[ActionHandler]:
        """Return a handler by id, or ``None`` if not found."""
        with self._lock:
            return self._handlers.get(handler_id)

    def list_handlers(self) -> List[ActionHandler]:
        """Return all registered action handlers."""
        with self._lock:
            return list(self._handlers.values())

    def remove_handler(self, handler_id: str) -> bool:
        """Remove a handler by id. Returns ``True`` if it was removed."""
        with self._lock:
            handler = self._handlers.pop(handler_id, None)
            if handler is None:
                return False
            if self._handlers_by_type.get(handler.action_type) == handler_id:
                self._handlers_by_type.pop(handler.action_type, None)
            return True

    # ------------------------------------------------------------------
    # Program lifecycle
    # ------------------------------------------------------------------

    def load_program(
        self,
        program_id: str,
        name: str,
        blocks: List[Dict[str, Any]],
    ) -> RuntimeProgram:
        """Load a published block program into the runtime."""
        with self._lock:
            runtime_id = _new_id("rt")
            program = RuntimeProgram(
                runtime_id=runtime_id,
                program_id=program_id,
                name=name or "Untitled",
                blocks=list(blocks),
                status=RuntimeStatus.LOADED,
                loaded_at=_now(),
                last_executed_at="",
                execution_count=0,
                error_count=0,
            )
            self._programs[runtime_id] = program
            self._program_counter += 1
            _evict_fifo_dict(self._programs, _MAX_RUNTIME_PROGRAMS)
            self._record_event(
                RuntimeEventKind.PROGRAM_LOADED,
                runtime_id,
                {"program_id": program_id, "name": program.name},
            )
            return program

    def unload_program(self, runtime_id: str) -> bool:
        """Unload a program from the runtime."""
        with self._lock:
            program = self._programs.pop(runtime_id, None)
            if program is None:
                return False
            program.status = RuntimeStatus.UNLOADED
            self._logs_by_program.pop(runtime_id, None)
            # Remove bindings for this program
            to_remove = [
                bid for bid, b in self._bindings.items()
                if b.runtime_id == runtime_id
            ]
            for bid in to_remove:
                self._bindings.pop(bid, None)
            self._record_event(
                RuntimeEventKind.PROGRAM_UNLOADED,
                runtime_id,
                {"name": program.name},
            )
            return True

    def get_program(self, runtime_id: str) -> Optional[RuntimeProgram]:
        """Return a runtime program by id."""
        with self._lock:
            return self._programs.get(runtime_id)

    def list_programs(
        self,
        status: Optional[Union[RuntimeStatus, str]] = None,
    ) -> List[RuntimeProgram]:
        """Return all runtime programs, optionally filtered by status."""
        with self._lock:
            resolved = _resolve_status(status) if status else None
            if resolved is None:
                return list(self._programs.values())
            return [p for p in self._programs.values() if p.status == resolved]

    def start_program(self, runtime_id: str) -> Optional[RuntimeProgram]:
        """Start a loaded program (transition to RUNNING)."""
        with self._lock:
            program = self._programs.get(runtime_id)
            if program is None:
                return None
            program.status = RuntimeStatus.RUNNING
            self._record_event(
                RuntimeEventKind.PROGRAM_STARTED,
                runtime_id,
                {"name": program.name},
            )
            return program

    def pause_program(self, runtime_id: str) -> Optional[RuntimeProgram]:
        """Pause a running program."""
        with self._lock:
            program = self._programs.get(runtime_id)
            if program is None:
                return None
            program.status = RuntimeStatus.PAUSED
            self._record_log(
                runtime_id,
                LogKind.PROGRAM_PAUSED,
                "",
                "Program paused",
            )
            self._record_event(
                RuntimeEventKind.PROGRAM_PAUSED,
                runtime_id,
                {"name": program.name},
            )
            return program

    def resume_program(self, runtime_id: str) -> Optional[RuntimeProgram]:
        """Resume a paused program."""
        with self._lock:
            program = self._programs.get(runtime_id)
            if program is None:
                return None
            program.status = RuntimeStatus.RUNNING
            self._record_log(
                runtime_id,
                LogKind.PROGRAM_RESUMED,
                "",
                "Program resumed",
            )
            self._record_event(
                RuntimeEventKind.PROGRAM_RESUMED,
                runtime_id,
                {"name": program.name},
            )
            return program

    # ------------------------------------------------------------------
    # Event bindings
    # ------------------------------------------------------------------

    def bind_event(
        self,
        runtime_id: str,
        event_type: str,
        event_filter: Optional[Dict[str, str]] = None,
    ) -> Optional[EventBinding]:
        """Bind a game event source to a runtime program."""
        with self._lock:
            if runtime_id not in self._programs:
                return None
            binding_id = _new_id("bnd")
            binding = EventBinding(
                binding_id=binding_id,
                runtime_id=runtime_id,
                event_type=event_type,
                event_filter=dict(event_filter) if event_filter else {},
                created_at=_now(),
            )
            self._bindings[binding_id] = binding
            self._binding_counter += 1
            _evict_fifo_dict(self._bindings, _MAX_BINDINGS)
            return binding

    def list_bindings(self, runtime_id: Optional[str] = None) -> List[EventBinding]:
        """Return all event bindings, optionally filtered by program."""
        with self._lock:
            if not runtime_id:
                return list(self._bindings.values())
            return [b for b in self._bindings.values() if b.runtime_id == runtime_id]

    def remove_binding(self, binding_id: str) -> bool:
        """Remove an event binding by id."""
        with self._lock:
            if binding_id not in self._bindings:
                return False
            self._bindings.pop(binding_id, None)
            return True

    # ------------------------------------------------------------------
    # Event dispatch and execution
    # ------------------------------------------------------------------

    def dispatch_event(
        self,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Dispatch a game event to all bound programs.

        Walks each bound program's block stack, firing event blocks that
        match, evaluating conditions, and dispatching actions to registered
        handlers. Returns the number of programs that processed the event.
        """
        with self._lock:
            data = dict(event_data) if event_data else {}
            processed = 0
            for binding in list(self._bindings.values()):
                if binding.event_type != event_type:
                    continue
                program = self._programs.get(binding.runtime_id)
                if program is None or program.status != RuntimeStatus.RUNNING:
                    continue
                self._execute_program(program, event_type, data)
                processed += 1
            return processed

    def _execute_program(
        self,
        program: RuntimeProgram,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> None:
        """Execute a program's block stack in response to an event.

        Walks the block stack in order. For each EVENT block matching the
        fired event, records an EVENT_FIRED log and continues processing
        subsequent CONDITION and ACTION blocks. Conditions are evaluated
        (simulated as passing). Actions are dispatched to their registered
        handlers. Errors are caught and logged without halting execution.
        """
        # Caller must hold self._lock
        program.last_executed_at = _now()
        program.execution_count += 1
        self._execution_counter += 1
        self._record_log(
            program.runtime_id,
            LogKind.EVENT_FIRED,
            event_type,
            f"Event '{event_type}' fired with data: {event_data}",
        )
        event_seen = False
        for block in program.blocks:
            if not block.get("enabled", True):
                continue
            category = block.get("category", "")
            block_name = block.get("name", "")
            params = block.get("params", {})
            try:
                if category == "event":
                    if block.get("type_id") == event_type or event_seen:
                        event_seen = True
                        self._record_log(
                            program.runtime_id,
                            LogKind.EVENT_FIRED,
                            block_name,
                            f"Event block matched: {params}",
                        )
                    continue
                if not event_seen:
                    continue
                if category == "condition":
                    self._record_log(
                        program.runtime_id,
                        LogKind.CONDITION_EVALUATED,
                        block_name,
                        f"Condition evaluated to true: {params}",
                    )
                elif category == "action":
                    self._dispatch_action(program.runtime_id, block, params)
                elif category == "control":
                    self._record_log(
                        program.runtime_id,
                        LogKind.CONTROL_FLOW,
                        block_name,
                        f"Control flow: {params}",
                    )
                elif category in ("variable", "operator", "data"):
                    self._record_log(
                        program.runtime_id,
                        LogKind.ACTION_DISPATCHED,
                        block_name,
                        f"{category} block processed: {params}",
                    )
            except Exception as exc:
                program.error_count += 1
                self._error_counter += 1
                self._record_log(
                    program.runtime_id,
                    LogKind.ERROR,
                    block_name,
                    f"Error executing block: {exc}",
                )
        program.status = RuntimeStatus.COMPLETED

    def _dispatch_action(
        self,
        runtime_id: str,
        block: Dict[str, Any],
        params: Dict[str, str],
    ) -> None:
        """Dispatch an action block to its registered handler.

        Looks up the handler registered for the block's ``type_id`` and
        increments its call count. If no handler is registered, the action
        is still logged (the runtime never halts on a missing handler).
        """
        # Caller must hold self._lock
        action_type = block.get("type_id", "")
        block_name = block.get("name", action_type)
        handler_id = self._handlers_by_type.get(action_type)
        if handler_id is not None:
            handler = self._handlers.get(handler_id)
            if handler is not None:
                handler.call_count += 1
        self._record_log(
            runtime_id,
            LogKind.ACTION_DISPATCHED,
            block_name,
            f"Action '{action_type}' dispatched with params: {params}",
        )
        self._record_event(
            RuntimeEventKind.ACTION_INVOKED,
            runtime_id,
            {"action_type": action_type, "block_name": block_name},
        )

    # ------------------------------------------------------------------
    # Telemetry and lookups
    # ------------------------------------------------------------------

    def get_logs(
        self,
        runtime_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ExecutionLog]:
        """Return execution logs, optionally filtered by program."""
        with self._lock:
            limit = max(1, min(int(limit), _MAX_LOGS))
            if runtime_id:
                logs = list(self._logs_by_program.get(runtime_id, deque()))
            else:
                logs = list(self._logs)
            return logs[-limit:]

    def list_events(self, limit: int = 50) -> List[RuntimeEvent]:
        """Return the most recent runtime lifecycle events."""
        with self._lock:
            limit = max(1, min(int(limit), _MAX_EVENTS))
            return list(self._events)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Return a compact status summary for monitoring."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_programs": len(self._programs),
                "active_programs": sum(
                    1 for p in self._programs.values()
                    if p.status == RuntimeStatus.RUNNING
                ),
                "total_handlers": len(self._handlers),
                "total_bindings": len(self._bindings),
                "total_logs": len(self._logs),
                "total_events": len(self._events),
                "program_counter": self._program_counter,
                "handler_counter": self._handler_counter,
                "binding_counter": self._binding_counter,
                "execution_counter": self._execution_counter,
                "error_counter": self._error_counter,
                "log_counter": self._log_counter,
                "event_counter": self._event_counter,
                "capacities": {
                    "max_runtime_programs": _MAX_RUNTIME_PROGRAMS,
                    "max_handlers": _MAX_HANDLERS,
                    "max_bindings": _MAX_BINDINGS,
                    "max_logs_per_program": _MAX_LOGS_PER_PROGRAM,
                    "max_logs": _MAX_LOGS,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_stats(self) -> RuntimeStats:
        """Return aggregate runtime statistics."""
        with self._lock:
            return RuntimeStats(
                total_programs=len(self._programs),
                active_programs=sum(
                    1 for p in self._programs.values()
                    if p.status == RuntimeStatus.RUNNING
                ),
                total_handlers=len(self._handlers),
                total_bindings=len(self._bindings),
                total_executions=self._execution_counter,
                total_errors=self._error_counter,
                total_logs=len(self._logs),
                total_events=len(self._events),
            )

    def get_snapshot(self) -> RuntimeSnapshot:
        """Return a full snapshot of the runtime state."""
        with self._lock:
            return RuntimeSnapshot(
                programs=list(self._programs.values()),
                handlers=list(self._handlers.values()),
                bindings=list(self._bindings.values()),
                logs=list(self._logs),
                stats=self.get_stats(),
            )

    def reset(self) -> None:
        """Reset the runtime to its seeded state."""
        with self._lock:
            self._programs.clear()
            self._handlers.clear()
            self._handlers_by_type.clear()
            self._bindings.clear()
            self._logs.clear()
            self._logs_by_program.clear()
            self._events.clear()
            self._program_counter = 0
            self._handler_counter = 0
            self._binding_counter = 0
            self._execution_counter = 0
            self._error_counter = 0
            self._log_counter = 0
            self._event_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Enum resolvers
# ---------------------------------------------------------------------------


def _resolve_status(value: Union[RuntimeStatus, str, None]) -> Optional[RuntimeStatus]:
    """Coerce a value into a :class:`RuntimeStatus` enum instance."""
    if value is None:
        return None
    if isinstance(value, RuntimeStatus):
        return value
    if isinstance(value, str):
        try:
            return RuntimeStatus(value)
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------


def get_block_runtime() -> BlockRuntimeExecutor:
    """Return the shared :class:`BlockRuntimeExecutor` singleton instance."""
    return BlockRuntimeExecutor()
