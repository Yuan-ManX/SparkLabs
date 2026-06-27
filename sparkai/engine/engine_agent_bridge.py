"""
SparkLabs Bridge - Agent-Engine Deep Integration Bridge

The bidirectional communication bridge between the AI Agent layer and the
Game Engine layer. This module enables real-time, synchronized interaction
between the cognitive agent brain and the game runtime, allowing agents to
perceive, reason about, and control game worlds programmatically.

The bridge implements:
- Command dispatch from agents to the engine
- State query from agents to the engine
- Event streaming from the engine to agents
- Real-time perception data streaming
- Synchronized action execution with feedback
- Performance monitoring and optimization bridging

Architecture:
  AgentEngineBridge (Singleton)
    |-- CommandChannel (agent -> engine commands)
    |-- QueryChannel (agent -> engine state queries)
    |-- EventChannel (engine -> agent event streaming)
    |-- PerceptionChannel (engine -> agent sensory data)
    |-- ActionChannel (agent -> engine action execution)
    |-- SyncManager (synchronization between agent and engine)
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ── Bridge Enums ──

class BridgeChannel(Enum):
    """Communication channels between agent and engine."""
    COMMAND = "command"
    QUERY = "query"
    EVENT = "event"
    PERCEPTION = "perception"
    ACTION = "action"
    STATE_SYNC = "state_sync"


class CommandType(Enum):
    """Types of commands agents can send to the engine."""
    CREATE_SCENE = "create_scene"
    LOAD_SCENE = "load_scene"
    UNLOAD_SCENE = "unload_scene"
    SPAWN_ENTITY = "spawn_entity"
    DESTROY_ENTITY = "destroy_entity"
    SET_COMPONENT = "set_component"
    EXECUTE_SCRIPT = "execute_script"
    APPLY_CONFIG = "apply_config"
    START_PROFILING = "start_profiling"
    STOP_PROFILING = "stop_profiling"
    CAPTURE_FRAME = "capture_frame"
    SAVE_STATE = "save_state"
    LOAD_STATE = "load_state"
    PAUSE = "pause"
    RESUME = "resume"
    RESET = "reset"
    SIMULATE_INPUT = "simulate_input"


class CommandStatus(Enum):
    """Status of command execution."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    REJECTED = "rejected"


class QueryType(Enum):
    """Types of queries agents can make to the engine."""
    GET_STATE = "get_state"
    GET_ENTITY = "get_entity"
    GET_SCENE = "get_scene"
    GET_COMPONENT = "get_component"
    GET_PERFORMANCE = "get_performance"
    GET_FRAME_HISTORY = "get_frame_history"
    GET_ENTITIES_BY_TAG = "get_entities_by_tag"
    LIST_SCENES = "list_scenes"


class SyncMode(Enum):
    """Synchronization modes between agent and engine."""
    REAL_TIME = "real_time"
    STEP_BY_STEP = "step_by_step"
    BATCH = "batch"
    ASYNC = "async"


# ── Data Classes ──

@dataclass
class BridgeCommand:
    """A command from agent to engine."""
    command_id: str
    command_type: CommandType
    parameters: Dict[str, Any]
    agent_id: str = "default"
    status: CommandStatus = CommandStatus.PENDING
    timestamp: float = field(default_factory=time.time)
    timeout_ms: float = 30000.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "command_type": self.command_type.value,
            "parameters": self.parameters,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "timeout_ms": self.timeout_ms,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class BridgeQuery:
    """A query from agent to engine."""
    query_id: str
    query_type: QueryType
    parameters: Dict[str, Any]
    agent_id: str = "default"
    timestamp: float = field(default_factory=time.time)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "query_type": self.query_type.value,
            "parameters": self.parameters,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class BridgeEvent:
    """An event from engine to agent."""
    event_id: str
    event_type: str
    data: Dict[str, Any]
    source: str = "engine"
    timestamp: float = field(default_factory=time.time)
    priority: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
            "priority": self.priority,
            "metadata": self.metadata,
        }


@dataclass
class BridgeStats:
    """Statistics for the bridge."""
    commands_sent: int = 0
    commands_completed: int = 0
    commands_failed: int = 0
    queries_made: int = 0
    events_emitted: int = 0
    perceptions_streamed: int = 0
    actions_executed: int = 0
    total_bytes_transferred: int = 0
    average_command_latency_ms: float = 0.0
    average_query_latency_ms: float = 0.0
    uptime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commands_sent": self.commands_sent,
            "commands_completed": self.commands_completed,
            "commands_failed": self.commands_failed,
            "queries_made": self.queries_made,
            "events_emitted": self.events_emitted,
            "perceptions_streamed": self.perceptions_streamed,
            "actions_executed": self.actions_executed,
            "total_bytes_transferred": self.total_bytes_transferred,
            "average_command_latency_ms": self.average_command_latency_ms,
            "average_query_latency_ms": self.average_query_latency_ms,
            "uptime_seconds": self.uptime_seconds,
        }


# ── AgentEngineBridge ──

class AgentEngineBridge:
    """
    The bidirectional bridge between AI agents and the game engine.

    Provides a complete communication layer that enables agents to:
    - Send commands to control the game engine
    - Query engine state and entity information
    - Receive real-time events from the engine
    - Stream perception data from the game world
    - Execute actions with synchronized feedback
    - Monitor performance across both systems

    Uses double-checked locking singleton pattern for thread safety.
    """

    _instance: Optional["AgentEngineBridge"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if AgentEngineBridge._instance is not None:
            raise RuntimeError("Use AgentEngineBridge.get_instance()")
        self._initialized: bool = False
        self._sync_mode: SyncMode = SyncMode.REAL_TIME

        # Command handling
        self._command_queue: deque = deque()
        self._command_history: deque = deque(maxlen=500)
        self._command_handlers: Dict[CommandType, Callable] = {}

        # Query handling
        self._query_handlers: Dict[QueryType, Callable] = {}

        # Event streaming
        self._event_buffer: deque = deque(maxlen=1000)
        self._event_subscriptions: Dict[str, List[Callable]] = {}

        # Perception streaming
        self._perception_buffer: deque = deque(maxlen=100)
        self._perception_rate: float = 30.0  # Hz

        # Action execution
        self._pending_actions: Dict[str, Dict[str, Any]] = {}
        self._action_results: Dict[str, Dict[str, Any]] = {}

        # Statistics
        self._stats: BridgeStats = BridgeStats()
        self._start_time: float = time.time()

        self._lock = threading.RLock()
        self._callbacks: Dict[str, List[Callable]] = {}

    @classmethod
    def get_instance(cls) -> "AgentEngineBridge":
        """Get the singleton instance with thread-safe double-checked locking."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Initialization ──

    def initialize(self, sync_mode: SyncMode = SyncMode.REAL_TIME) -> None:
        """Initialize the bridge with synchronization mode."""
        with self._lock:
            if self._initialized:
                return
            self._initialized = True
            self._sync_mode = sync_mode
            self._start_time = time.time()
            self._setup_default_handlers()

    def _setup_default_handlers(self) -> None:
        """Register default command and query handlers."""
        # Default no-op handlers that get replaced by the engine
        for cmd_type in CommandType:
            self._command_handlers[cmd_type] = self._default_command_handler

        for query_type in QueryType:
            self._query_handlers[query_type] = self._default_query_handler

    def _default_command_handler(self, command: BridgeCommand) -> Dict[str, Any]:
        """Default command handler (no-op)."""
        return {"status": "not_implemented", "command_type": command.command_type.value}

    def _default_query_handler(self, query: BridgeQuery) -> Dict[str, Any]:
        """Default query handler (no-op)."""
        return {"status": "not_implemented", "query_type": query.query_type.value}

    # ── Command Dispatch ──

    def register_command_handler(
        self, command_type: CommandType, handler: Callable
    ) -> None:
        """Register a handler for a specific command type."""
        self._command_handlers[command_type] = handler

    def send_command(
        self,
        command_type: CommandType,
        parameters: Dict[str, Any],
        agent_id: str = "default",
        timeout_ms: float = 30000.0,
    ) -> BridgeCommand:
        """Send a command from agent to engine."""
        command = BridgeCommand(
            command_id=f"cmd_{uuid.uuid4().hex[:12]}",
            command_type=command_type,
            parameters=parameters,
            agent_id=agent_id,
            timeout_ms=timeout_ms,
        )

        self._command_queue.append(command)
        self._stats.commands_sent += 1

        # Execute immediately in sync mode
        if self._sync_mode in (SyncMode.REAL_TIME, SyncMode.STEP_BY_STEP):
            self._execute_command(command)

        return command

    def send_command_batch(
        self, commands: List[Tuple[CommandType, Dict[str, Any]]], agent_id: str = "default"
    ) -> List[BridgeCommand]:
        """Send a batch of commands."""
        results = []
        for cmd_type, params in commands:
            result = self.send_command(cmd_type, params, agent_id)
            results.append(result)
        return results

    def _execute_command(self, command: BridgeCommand) -> None:
        """Execute a single command through the registered handler."""
        command.status = CommandStatus.EXECUTING
        t0 = time.time()

        handler = self._command_handlers.get(command.command_type, self._default_command_handler)

        try:
            result = handler(command)
            command.status = CommandStatus.COMPLETED
            command.result = result
            self._stats.commands_completed += 1
        except Exception as e:
            command.status = CommandStatus.FAILED
            command.error = str(e)
            self._stats.commands_failed += 1

        latency = (time.time() - t0) * 1000
        n = self._stats.commands_sent
        old_avg = self._stats.average_command_latency_ms
        self._stats.average_command_latency_ms = (old_avg * (n - 1) + latency) / n

        self._command_history.append(command)

    def process_command_queue(self) -> int:
        """Process all pending commands in the queue."""
        processed = 0
        while self._command_queue:
            command = self._command_queue.popleft()
            self._execute_command(command)
            processed += 1
        return processed

    def get_command_result(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a previously sent command."""
        for cmd in self._command_history:
            if cmd.command_id == command_id:
                return {
                    "status": cmd.status.value,
                    "result": cmd.result,
                    "error": cmd.error,
                }
        return None

    # ── Query Interface ──

    def register_query_handler(
        self, query_type: QueryType, handler: Callable
    ) -> None:
        """Register a handler for a specific query type."""
        self._query_handlers[query_type] = handler

    def query(
        self,
        query_type: QueryType,
        parameters: Optional[Dict[str, Any]] = None,
        agent_id: str = "default",
    ) -> BridgeQuery:
        """Query the engine for state information."""
        query = BridgeQuery(
            query_id=f"query_{uuid.uuid4().hex[:12]}",
            query_type=query_type,
            parameters=parameters or {},
            agent_id=agent_id,
        )

        self._stats.queries_made += 1
        t0 = time.time()

        handler = self._query_handlers.get(query_type, self._default_query_handler)

        try:
            query.result = handler(query)
        except Exception as e:
            query.error = str(e)

        latency = (time.time() - t0) * 1000
        n = self._stats.queries_made
        old_avg = self._stats.average_query_latency_ms
        self._stats.average_query_latency_ms = (old_avg * (n - 1) + latency) / n

        return query

    def query_engine_state(self) -> Dict[str, Any]:
        """Quick query for the full engine state."""
        result = self.query(QueryType.GET_STATE)
        return result.result or {}

    # ── Event Streaming ──

    def subscribe_to_events(
        self, event_type: str, callback: Callable
    ) -> None:
        """Subscribe to engine events of a specific type."""
        if event_type not in self._event_subscriptions:
            self._event_subscriptions[event_type] = []
        self._event_subscriptions[event_type].append(callback)

    def emit_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        priority: float = 0.5,
    ) -> BridgeEvent:
        """Emit an event from engine to subscribed agents."""
        event = BridgeEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            data=data,
            priority=priority,
        )

        self._event_buffer.append(event)
        self._stats.events_emitted += 1

        # Notify subscribers
        callbacks = self._event_subscriptions.get(event_type, [])
        for cb in callbacks:
            try:
                cb(event.to_dict())
            except Exception:
                pass

        # Also notify wildcard subscribers
        for cb in self._event_subscriptions.get("*", []):
            try:
                cb(event.to_dict())
            except Exception:
                pass

        return event

    def get_recent_events(self, count: int = 50) -> List[Dict[str, Any]]:
        """Get recent events from the buffer."""
        events = list(self._event_buffer)[-count:]
        return [e.to_dict() for e in events]

    # ── Perception Streaming ──

    def stream_perception(
        self, perception_data: Dict[str, Any]
    ) -> None:
        """Stream perception data from engine to agent."""
        self._perception_buffer.append({
            "data": perception_data,
            "timestamp": time.time(),
        })
        self._stats.perceptions_streamed += 1

    def get_latest_perception(self) -> Optional[Dict[str, Any]]:
        """Get the latest perception data."""
        if self._perception_buffer:
            return self._perception_buffer[-1]
        return None

    # ── Action Execution ──

    def execute_action(
        self,
        action_type: str,
        parameters: Dict[str, Any],
        wait_for_result: bool = True,
        timeout_ms: float = 30000.0,
    ) -> Dict[str, Any]:
        """Execute an action through the engine and get feedback."""
        action_id = f"action_{uuid.uuid4().hex[:12]}"

        action_data = {
            "action_id": action_id,
            "action_type": action_type,
            "parameters": parameters,
            "timestamp": time.time(),
            "status": "pending",
        }

        self._pending_actions[action_id] = action_data
        self._stats.actions_executed += 1

        # Execute via command
        cmd_type = self._action_to_command_type(action_type)
        if cmd_type:
            command = self.send_command(cmd_type, parameters)
            action_data["status"] = command.status.value
            action_data["result"] = command.result
            action_data["error"] = command.error
        else:
            action_data["status"] = "failed"
            action_data["error"] = f"Unknown action type: {action_type}"

        self._action_results[action_id] = action_data
        return action_data

    def _action_to_command_type(self, action_type: str) -> Optional[CommandType]:
        """Map an action type to a command type."""
        mapping = {
            "create_scene": CommandType.CREATE_SCENE,
            "load_scene": CommandType.LOAD_SCENE,
            "unload_scene": CommandType.UNLOAD_SCENE,
            "spawn_entity": CommandType.SPAWN_ENTITY,
            "destroy_entity": CommandType.DESTROY_ENTITY,
            "set_component": CommandType.SET_COMPONENT,
            "execute_script": CommandType.EXECUTE_SCRIPT,
            "apply_config": CommandType.APPLY_CONFIG,
            "start_profiling": CommandType.START_PROFILING,
            "stop_profiling": CommandType.STOP_PROFILING,
            "capture_frame": CommandType.CAPTURE_FRAME,
            "save_state": CommandType.SAVE_STATE,
            "load_state": CommandType.LOAD_STATE,
            "pause": CommandType.PAUSE,
            "resume": CommandType.RESUME,
            "reset": CommandType.RESET,
            "simulate_input": CommandType.SIMULATE_INPUT,
        }
        return mapping.get(action_type)

    def get_action_result(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a previously executed action."""
        return self._action_results.get(action_id)

    # ── Synchronization ──

    def sync_state(self) -> Dict[str, Any]:
        """Synchronize state between agent and engine."""
        engine_state = self.query_engine_state()
        return {
            "sync_id": f"sync_{uuid.uuid4().hex[:12]}",
            "timestamp": time.time(),
            "engine_state": engine_state,
            "pending_commands": len(self._command_queue),
            "pending_actions": len(self._pending_actions),
            "sync_mode": self._sync_mode.value,
        }

    def set_sync_mode(self, mode: SyncMode) -> None:
        """Change the synchronization mode."""
        self._sync_mode = mode

    # ── Status & Statistics ──

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive bridge status."""
        self._stats.uptime_seconds = time.time() - self._start_time
        return {
            "initialized": self._initialized,
            "sync_mode": self._sync_mode.value,
            "stats": self._stats.to_dict(),
            "pending_commands": len(self._command_queue),
            "pending_actions": len(self._pending_actions),
            "event_buffer_size": len(self._event_buffer),
            "perception_buffer_size": len(self._perception_buffer),
            "registered_handlers": {
                "commands": len(self._command_handlers),
                "queries": len(self._query_handlers),
            },
            "event_subscriptions": {
                k: len(v) for k, v in self._event_subscriptions.items()
            },
        }

    def reset(self) -> None:
        """Reset the bridge to its initial state."""
        with self._lock:
            self._initialized = False
            self._command_queue.clear()
            self._command_history.clear()
            self._event_buffer.clear()
            self._perception_buffer.clear()
            self._pending_actions.clear()
            self._action_results.clear()
            self._stats = BridgeStats()
            self._start_time = time.time()


# ── Module-level convenience ──

def get_agent_engine_bridge() -> AgentEngineBridge:
    """Get the singleton AgentEngineBridge instance."""
    bridge = AgentEngineBridge.get_instance()
    if not bridge._initialized:
        bridge.initialize()
    return bridge