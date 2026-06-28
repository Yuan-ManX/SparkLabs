"""
Agent-Engine Communication Protocol

This module defines the standardized bidirectional communication interface between
the Agent layer and the Engine layer of the SparkLabs AI-native game engine. It enables
AI agents to send commands, query engine state, receive events, and synchronize data
with the game engine in real-time.

Architecture:
    Agent Layer  <─── commands / queries ───>  Engine Layer
    Agent Layer  <─── events / sync ─────────>  Engine Layer

The protocol is implemented as a thread-safe singleton to ensure consistent state
across all agent-engine interactions within a single process.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CommandType(Enum):
    """Types of commands an agent can send to the engine."""

    SPAWN_ENTITY = auto()
    DESTROY_ENTITY = auto()
    MODIFY_COMPONENT = auto()
    LOAD_SCENE = auto()
    UNLOAD_SCENE = auto()
    SET_PROPERTY = auto()
    TRIGGER_EVENT = auto()
    START_GAME = auto()
    PAUSE_GAME = auto()
    RESUME_GAME = auto()
    STOP_GAME = auto()
    APPLY_PHYSICS = auto()
    PLAY_AUDIO = auto()
    PLAY_ANIMATION = auto()
    SET_CAMERA = auto()
    EXECUTE_SCRIPT = auto()
    MODIFY_TERRAIN = auto()
    SPAWN_PARTICLES = auto()
    SET_UI_STATE = auto()
    SAVE_STATE = auto()
    LOAD_STATE = auto()


class QueryType(Enum):
    """Types of queries an agent can send to the engine."""

    GET_ENTITY = auto()
    GET_SCENE = auto()
    GET_COMPONENT = auto()
    GET_PROPERTY = auto()
    GET_STATE = auto()
    GET_PERFORMANCE = auto()
    GET_PHYSICS = auto()
    GET_RENDER_STATS = auto()
    GET_AUDIO_STATE = auto()
    GET_INPUT_STATE = auto()
    GET_MEMORY_USAGE = auto()
    GET_FRAME_DATA = auto()
    GET_ENTITY_COUNT = auto()
    GET_ACTIVE_SCENES = auto()


class EventType(Enum):
    """Types of events the engine can emit to registered agent listeners."""

    ENTITY_CREATED = auto()
    ENTITY_DESTROYED = auto()
    COLLISION_OCCURRED = auto()
    SCENE_LOADED = auto()
    SCENE_UNLOADED = auto()
    FRAME_RENDERED = auto()
    GAME_STARTED = auto()
    GAME_PAUSED = auto()
    GAME_RESUMED = auto()
    GAME_STOPPED = auto()
    PERFORMANCE_ALERT = auto()
    ERROR_OCCURRED = auto()
    STATE_CHANGED = auto()
    INPUT_RECEIVED = auto()
    ANIMATION_COMPLETED = auto()
    AUDIO_FINISHED = auto()


class ProtocolState(Enum):
    """Possible states of the communication protocol connection."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    SYNCING = auto()
    ERROR = auto()
    RECONNECTING = auto()


class SyncMode(Enum):
    """Strategies for synchronizing state between agent and engine."""

    FULL = auto()
    DELTA = auto()
    LAZY = auto()
    EVENT_DRIVEN = auto()
    PERIODIC = auto()


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class AgentCommand:
    """A command issued by an agent to be executed by the engine.

    Attributes:
        command_id: Unique identifier for this command.
        command_type: The type of command to execute.
        target_entity_id: Optional entity this command targets.
        parameters: Key-value payload for the command.
        priority: Execution priority (lower = higher priority).
        timestamp: Unix timestamp when the command was created.
        source_agent: Identifier of the originating agent.
        correlation_id: Optional correlation ID for tracking related commands.
        timeout_ms: Maximum time in milliseconds to wait for execution.
        metadata: Arbitrary key-value metadata.
    """

    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    command_type: CommandType = CommandType.SET_PROPERTY
    target_entity_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timestamp: float = field(default_factory=time.time)
    source_agent: str = ""
    correlation_id: Optional[str] = None
    timeout_ms: int = 5000
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandResult:
    """The result of executing an AgentCommand.

    Attributes:
        command_id: The ID of the command that produced this result.
        success: Whether the command executed successfully.
        data: Optional payload returned by the engine.
        error_message: Description of the error if success is False.
        execution_time_ms: How long the command took to execute.
        engine_timestamp: Timestamp from the engine side when execution finished.
        status_code: Optional numeric status code from the engine.
        warnings: List of non-fatal warnings generated during execution.
    """

    command_id: str = ""
    success: bool = False
    data: Optional[Any] = None
    error_message: str = ""
    execution_time_ms: float = 0.0
    engine_timestamp: float = field(default_factory=time.time)
    status_code: Optional[int] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class EngineQuery:
    """A query sent by an agent to retrieve state from the engine.

    Attributes:
        query_id: Unique identifier for this query.
        query_type: The type of query to perform.
        target: Optional target specifier (entity ID, scene name, etc.).
        filters: Optional filtering criteria.
        fields: Specific fields to return (empty means all).
        timestamp: Unix timestamp when the query was created.
        source_agent: Identifier of the originating agent.
        timeout_ms: Maximum time in milliseconds to wait for a response.
        metadata: Arbitrary key-value metadata.
    """

    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_type: QueryType = QueryType.GET_STATE
    target: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    fields: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    source_agent: str = ""
    timeout_ms: int = 3000
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResult:
    """The result of executing an EngineQuery.

    Attributes:
        query_id: The ID of the query that produced this result.
        success: Whether the query was fulfilled successfully.
        data: The payload returned by the engine.
        error_message: Description of the error if success is False.
        execution_time_ms: How long the query took to execute.
        engine_timestamp: Timestamp from the engine side when the query completed.
        total_results: Total number of matching results (may exceed data size).
        has_more: Whether there are additional results beyond what was returned.
        metadata: Engine-provided metadata about the result.
    """

    query_id: str = ""
    success: bool = False
    data: Optional[Any] = None
    error_message: str = ""
    execution_time_ms: float = 0.0
    engine_timestamp: float = field(default_factory=time.time)
    total_results: int = 0
    has_more: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineEvent:
    """An event emitted by the engine to notify agents of state changes.

    Attributes:
        event_id: Unique identifier for this event.
        event_type: The type of event.
        source_entity_id: Optional entity that originated the event.
        data: Event payload.
        timestamp: Unix timestamp when the event was emitted.
        session_id: Identifier of the game session.
        severity: Event severity level (info, warning, error, critical).
        propagation: Whether the event should be propagated to sub-listeners.
        metadata: Arbitrary key-value metadata.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.STATE_CHANGED
    source_entity_id: Optional[str] = None
    data: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""
    severity: str = "info"
    propagation: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateSync:
    """A synchronization payload exchanged between agent and engine.

    Attributes:
        sync_id: Unique identifier for this synchronization operation.
        mode: The synchronization mode used.
        data: The synchronized state data.
        timestamp: Unix timestamp of the sync.
        version: Monotonic version number for change tracking.
        checksum: Optional checksum for integrity verification.
        previous_sync_id: ID of the preceding sync for delta reconstruction.
        metadata: Arbitrary key-value metadata.
    """

    sync_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mode: SyncMode = SyncMode.FULL
    data: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)
    version: int = 0
    checksum: Optional[str] = None
    previous_sync_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProtocolStats:
    """Aggregated statistics and metrics for the communication protocol.

    Attributes:
        total_commands_sent: Cumulative number of commands sent.
        total_commands_completed: Cumulative number of commands that completed.
        total_commands_failed: Cumulative number of commands that failed.
        total_queries_sent: Cumulative number of queries performed.
        total_queries_completed: Cumulative number of queries that completed.
        total_queries_failed: Cumulative number of queries that failed.
        total_events_emitted: Cumulative number of events emitted.
        total_events_received: Cumulative number of events received.
        total_syncs_performed: Cumulative number of state synchronizations.
        average_command_latency_ms: Rolling average command execution time.
        average_query_latency_ms: Rolling average query execution time.
        uptime_seconds: How long the protocol has been active.
        last_activity: Timestamp of the last protocol activity.
        bytes_sent: Total bytes sent over the protocol.
        bytes_received: Total bytes received over the protocol.
    """

    total_commands_sent: int = 0
    total_commands_completed: int = 0
    total_commands_failed: int = 0
    total_queries_sent: int = 0
    total_queries_completed: int = 0
    total_queries_failed: int = 0
    total_events_emitted: int = 0
    total_events_received: int = 0
    total_syncs_performed: int = 0
    average_command_latency_ms: float = 0.0
    average_query_latency_ms: float = 0.0
    uptime_seconds: float = 0.0
    last_activity: float = field(default_factory=time.time)
    bytes_sent: int = 0
    bytes_received: int = 0


@dataclass
class ProtocolSnapshot:
    """A complete snapshot of the protocol's state at a point in time.

    Attributes:
        snapshot_id: Unique identifier for this snapshot.
        state: The current protocol connection state.
        pending_commands: Number of commands awaiting execution.
        command_history: Recent command execution records.
        event_listener_count: Number of registered event listeners.
        session_id: Identifier of the active session.
        stats: Current protocol statistics.
        timestamp: Unix timestamp when the snapshot was taken.
        metadata: Arbitrary key-value metadata.
    """

    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: ProtocolState = ProtocolState.DISCONNECTED
    pending_commands: int = 0
    command_history: List[Tuple[str, CommandType, str]] = field(default_factory=list)
    event_listener_count: int = 0
    session_id: str = ""
    stats: ProtocolStats = field(default_factory=ProtocolStats)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# AgentEngineCommunicationProtocol (Singleton)
# ---------------------------------------------------------------------------


class AgentEngineCommunicationProtocol:
    """Bidirectional communication protocol between Agent and Engine layers.

    This class implements a thread-safe singleton that manages the full lifecycle
    of agent-engine communication: command dispatch, engine querying, event
    emission, and state synchronization. It maintains a command queue, event
    listener registry, execution history, and protocol statistics.

    Usage::

        protocol = AgentEngineCommunicationProtocol.get_instance()
        protocol.initialize()

        cmd = AgentCommand(command_type=CommandType.SPAWN_ENTITY,
                           parameters={"prefab": "Player"})
        result = protocol.execute_command(cmd)

        protocol.shutdown()
    """

    _instance: Optional[AgentEngineCommunicationProtocol] = None
    _instance_lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> AgentEngineCommunicationProtocol:
        """Return the singleton instance, creating it if necessary.

        Uses double-checked locking to ensure thread safety while
        avoiding the overhead of acquiring the lock on every call.

        Returns:
            The single AgentEngineCommunicationProtocol instance.
        """
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        """Initialize the communication protocol with default state.

        This constructor is called only once due to the singleton pattern.
        Internal structures (command queue, event listeners, etc.) are set
        up but the protocol is not yet active until ``initialize()`` is called.
        """
        if self._instance is not None:
            raise RuntimeError(
                "Use AgentEngineCommunicationProtocol.get_instance() "
                "to obtain the singleton instance."
            )

        # Connection state
        self._state: ProtocolState = ProtocolState.DISCONNECTED
        self._session_id: str = ""
        self._started_at: float = 0.0

        # Command queue and history
        self._command_queue: deque[AgentCommand] = deque()
        self._command_history: deque[Tuple[str, CommandType, str]] = deque(
            maxlen=1000
        )
        self._pending_results: Dict[str, CommandResult] = {}

        # Query history
        self._query_history: deque[Tuple[str, QueryType, str]] = deque(maxlen=1000)

        # Event listeners: EventType -> list of callbacks
        self._event_listeners: Dict[EventType, List[Callable[[EngineEvent], None]]] = {}
        self._global_listeners: List[Callable[[EngineEvent], None]] = []

        # Sync state
        self._sync_version: int = 0
        self._last_sync_id: Optional[str] = None
        self._sync_history: deque[StateSync] = deque(maxlen=100)

        # Statistics
        self._stats: ProtocolStats = ProtocolStats()

        # Thread safety
        self._lock: threading.RLock = threading.RLock()
        self._active: bool = False

        logger.debug("AgentEngineCommunicationProtocol instance created (not yet initialized).")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self, session_id: Optional[str] = None) -> None:
        """Set up the communication protocol and transition to CONNECTED state.

        This method must be called before any commands, queries, or events
        can be sent. It transitions the protocol through CONNECTING to
        CONNECTED, registers the session, and resets internal statistics.

        Args:
            session_id: Optional identifier for the game session. A UUID
                is generated if none is provided.

        Raises:
            RuntimeError: If the protocol is already initialized and active.
        """
        with self._lock:
            if self._active:
                raise RuntimeError(
                    "Communication protocol is already initialized. "
                    "Call shutdown() before re-initializing."
                )

            self._state = ProtocolState.CONNECTING
            logger.info("Agent-Engine communication protocol connecting...")

            self._session_id = session_id or str(uuid.uuid4())
            self._started_at = time.time()
            self._active = True

            # Reset transient state
            self._command_queue.clear()
            self._command_history.clear()
            self._pending_results.clear()
            self._query_history.clear()
            self._event_listeners.clear()
            self._global_listeners.clear()
            self._sync_version = 0
            self._last_sync_id = None
            self._sync_history.clear()
            self._stats = ProtocolStats()

            self._state = ProtocolState.CONNECTED
            self._stats.last_activity = time.time()

            logger.info(
                "Agent-Engine communication protocol initialized (session=%s).",
                self._session_id,
            )

    def shutdown(self) -> None:
        """Gracefully shut down the communication protocol.

        Flushes the command queue, clears all listeners, resets statistics,
        and transitions the state to DISCONNECTED. After shutdown the
        protocol can be re-initialized.
        """
        with self._lock:
            if not self._active:
                logger.warning("shutdown() called but protocol is not active.")
                return

            logger.info("Shutting down Agent-Engine communication protocol...")

            self._state = ProtocolState.DISCONNECTED
            self._active = False

            self._command_queue.clear()
            self._pending_results.clear()
            self._event_listeners.clear()
            self._global_listeners.clear()

            self._stats.uptime_seconds = time.time() - self._started_at

            logger.info(
                "Agent-Engine communication protocol shut down. "
                "Uptime: %.2fs, Commands: %d sent / %d completed / %d failed.",
                self._stats.uptime_seconds,
                self._stats.total_commands_sent,
                self._stats.total_commands_completed,
                self._stats.total_commands_failed,
            )

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def send_command(self, command: AgentCommand) -> str:
        """Enqueue a command for asynchronous execution by the engine.

        The command is placed in the pending queue and will be picked up
        by the engine on the next processing cycle. This method returns
        immediately without waiting for execution.

        Args:
            command: The AgentCommand to send.

        Returns:
            The command_id of the enqueued command.

        Raises:
            RuntimeError: If the protocol has not been initialized.
        """
        with self._lock:
            self._ensure_active()

            if not command.command_id:
                command.command_id = str(uuid.uuid4())
            if command.timestamp <= 0:
                command.timestamp = time.time()

            self._command_queue.append(command)
            self._stats.total_commands_sent += 1
            self._stats.last_activity = time.time()

            self._command_history.append(
                (command.command_id, command.command_type, "pending")
            )

            logger.debug(
                "Command enqueued: id=%s type=%s priority=%d",
                command.command_id,
                command.command_type.name,
                command.priority,
            )

            return command.command_id

    def execute_command(self, command: AgentCommand) -> CommandResult:
        """Send a command and block until the engine returns a result.

        This is a synchronous wrapper around ``send_command``. It enqueues
        the command and then waits for the engine to produce a result
        (up to the command's timeout). In a real implementation this would
        use a future/promise or condition variable; here we simulate the
        execution path.

        Args:
            command: The AgentCommand to execute.

        Returns:
            A CommandResult indicating success or failure.

        Raises:
            RuntimeError: If the protocol has not been initialized.
        """
        with self._lock:
            self._ensure_active()

            command_id = self.send_command(command)

            # In a full implementation this would block on a future or
            # condition variable. We simulate immediate execution.
            start_time = time.time()
            result = self._simulate_command_execution(command)
            elapsed = (time.time() - start_time) * 1000.0

            result.command_id = command_id
            result.execution_time_ms = elapsed
            result.engine_timestamp = time.time()

            self._stats.total_commands_completed += 1
            self._stats.last_activity = time.time()

            # Update rolling average
            prev = self._stats.average_command_latency_ms
            n = self._stats.total_commands_completed
            self._stats.average_command_latency_ms = (
                prev * (n - 1) + elapsed
            ) / n

            # Update history entry
            status = "completed" if result.success else "failed"
            if not result.success:
                self._stats.total_commands_failed += 1

            self._command_history.append(
                (command_id, command.command_type, status)
            )

            logger.debug(
                "Command executed: id=%s type=%s success=%s time=%.2fms",
                command_id,
                command.command_type.name,
                result.success,
                elapsed,
            )

            return result

    def _simulate_command_execution(self, command: AgentCommand) -> CommandResult:
        """Simulate engine-side command execution.

        In a production system this would be replaced by actual engine
        integration. Currently it returns a success result for all
        command types except those marked with a 'fail' parameter.

        Args:
            command: The command to simulate.

        Returns:
            A CommandResult with simulated execution data.
        """
        if command.parameters.get("_simulate_failure"):
            return CommandResult(
                command_id=command.command_id,
                success=False,
                error_message=f"Simulated failure for command type {command.command_type.name}",
                status_code=500,
                warnings=["Simulated failure mode enabled"],
            )

        return CommandResult(
            command_id=command.command_id,
            success=True,
            data={"acknowledged": True, "command_type": command.command_type.name},
            status_code=200,
        )

    # ------------------------------------------------------------------
    # Pending commands
    # ------------------------------------------------------------------

    def get_pending_commands(self) -> List[AgentCommand]:
        """Return a snapshot of all commands currently awaiting execution.

        Returns:
            A list of AgentCommand instances in FIFO order.
        """
        with self._lock:
            return list(self._command_queue)

    def get_command_history(
        self, limit: Optional[int] = None
    ) -> List[Tuple[str, CommandType, str]]:
        """Return the command execution history.

        Each entry is a tuple of (command_id, CommandType, status) where
        status is one of 'pending', 'completed', or 'failed'.

        Args:
            limit: Maximum number of entries to return. Returns all if None.

        Returns:
            A list of command history tuples, most recent first.
        """
        with self._lock:
            history = list(self._command_history)
            if limit is not None:
                history = history[-limit:]
            return history

    # ------------------------------------------------------------------
    # Engine querying
    # ------------------------------------------------------------------

    def query_engine(self, query: EngineQuery) -> QueryResult:
        """Send a query to the engine and block until a response is received.

        Args:
            query: The EngineQuery to send.

        Returns:
            A QueryResult containing the engine's response.

        Raises:
            RuntimeError: If the protocol has not been initialized.
        """
        with self._lock:
            self._ensure_active()

            if not query.query_id:
                query.query_id = str(uuid.uuid4())
            if query.timestamp <= 0:
                query.timestamp = time.time()

            self._stats.total_queries_sent += 1
            self._stats.last_activity = time.time()

            start_time = time.time()
            result = self._simulate_query_execution(query)
            elapsed = (time.time() - start_time) * 1000.0

            result.query_id = query.query_id
            result.execution_time_ms = elapsed
            result.engine_timestamp = time.time()

            self._stats.total_queries_completed += 1
            if not result.success:
                self._stats.total_queries_failed += 1

            status = "completed" if result.success else "failed"
            self._query_history.append((query.query_id, query.query_type, status))

            # Update rolling average
            prev = self._stats.average_query_latency_ms
            n = self._stats.total_queries_completed
            self._stats.average_query_latency_ms = (
                prev * (n - 1) + elapsed
            ) / n

            logger.debug(
                "Query executed: id=%s type=%s success=%s time=%.2fms",
                query.query_id,
                query.query_type.name,
                result.success,
                elapsed,
            )

            return result

    def _simulate_query_execution(self, query: EngineQuery) -> QueryResult:
        """Simulate engine-side query execution.

        Args:
            query: The query to simulate.

        Returns:
            A QueryResult with simulated data.
        """
        if query.filters.get("_simulate_failure"):
            return QueryResult(
                query_id=query.query_id,
                success=False,
                error_message=f"Simulated failure for query type {query.query_type.name}",
                metadata={"simulated": True},
            )

        return QueryResult(
            query_id=query.query_id,
            success=True,
            data={
                "query_type": query.query_type.name,
                "target": query.target,
                "result": {"simulated": True},
            },
            total_results=1,
            has_more=False,
            metadata={"simulated": True},
        )

    # ------------------------------------------------------------------
    # Event system
    # ------------------------------------------------------------------

    def register_event_listener(
        self,
        event_type: EventType,
        callback: Callable[[EngineEvent], None],
    ) -> None:
        """Register a callback to be invoked when the specified event type occurs.

        Multiple listeners can be registered for the same event type; they
        are invoked in registration order.

        Args:
            event_type: The EventType to listen for.
            callback: A callable that accepts a single EngineEvent argument.

        Raises:
            ValueError: If callback is not callable.
        """
        if not callable(callback):
            raise ValueError("callback must be callable.")

        with self._lock:
            if event_type not in self._event_listeners:
                self._event_listeners[event_type] = []
            self._event_listeners[event_type].append(callback)
            logger.debug(
                "Event listener registered for %s (total: %d).",
                event_type.name,
                len(self._event_listeners[event_type]),
            )

    def unregister_event_listener(
        self,
        event_type: EventType,
        callback: Callable[[EngineEvent], None],
    ) -> bool:
        """Remove a previously registered event listener.

        Args:
            event_type: The EventType the callback was registered for.
            callback: The callback to remove.

        Returns:
            True if the listener was found and removed, False otherwise.
        """
        with self._lock:
            listeners = self._event_listeners.get(event_type, [])
            if callback in listeners:
                listeners.remove(callback)
                if not listeners:
                    del self._event_listeners[event_type]
                logger.debug(
                    "Event listener unregistered for %s.",
                    event_type.name,
                )
                return True
            return False

    def register_global_listener(
        self, callback: Callable[[EngineEvent], None]
    ) -> None:
        """Register a callback that receives all events regardless of type.

        Args:
            callback: A callable that accepts a single EngineEvent argument.

        Raises:
            ValueError: If callback is not callable.
        """
        if not callable(callback):
            raise ValueError("callback must be callable.")

        with self._lock:
            self._global_listeners.append(callback)
            logger.debug(
                "Global event listener registered (total: %d).",
                len(self._global_listeners),
            )

    def emit_event(self, event: EngineEvent) -> None:
        """Emit an event from the engine to all registered agent listeners.

        Notifies type-specific listeners first, then global listeners.
        Errors in individual listeners are caught and logged but do not
        prevent other listeners from receiving the event.

        Args:
            event: The EngineEvent to emit.
        """
        with self._lock:
            if not event.event_id:
                event.event_id = str(uuid.uuid4())
            if event.timestamp <= 0:
                event.timestamp = time.time()
            if not event.session_id:
                event.session_id = self._session_id

            self._stats.total_events_emitted += 1
            self._stats.last_activity = time.time()

            # Notify type-specific listeners
            type_listeners = self._event_listeners.get(event.event_type, [])
            for listener in type_listeners:
                try:
                    listener(event)
                except Exception:
                    logger.exception(
                        "Error in event listener for %s (event_id=%s).",
                        event.event_type.name,
                        event.event_id,
                    )

            # Notify global listeners
            for listener in self._global_listeners:
                try:
                    listener(event)
                except Exception:
                    logger.exception(
                        "Error in global event listener (event_id=%s).",
                        event.event_id,
                    )

            logger.debug(
                "Event emitted: id=%s type=%s listeners=%d global=%d",
                event.event_id,
                event.event_type.name,
                len(type_listeners),
                len(self._global_listeners),
            )

    def get_event_listener_count(self) -> Dict[str, int]:
        """Return the number of registered listeners per event type.

        Returns:
            A dict mapping event type names to listener counts.
        """
        with self._lock:
            return {
                et.name: len(listeners)
                for et, listeners in self._event_listeners.items()
            }

    # ------------------------------------------------------------------
    # State synchronization
    # ------------------------------------------------------------------

    def sync_state(self, mode: SyncMode = SyncMode.FULL) -> StateSync:
        """Perform a state synchronization between agent and engine.

        In a full implementation this would exchange state data with the
        engine runtime. Currently it creates a simulated sync payload.

        Args:
            mode: The synchronization strategy to use.

        Returns:
            A StateSync object containing the synchronized data.

        Raises:
            RuntimeError: If the protocol has not been initialized.
        """
        with self._lock:
            self._ensure_active()

            previous_state = self._state
            self._state = ProtocolState.SYNCING

            self._sync_version += 1

            sync = StateSync(
                sync_id=str(uuid.uuid4()),
                mode=mode,
                data={
                    "sync_version": self._sync_version,
                    "session_id": self._session_id,
                    "mode": mode.name,
                    "simulated": True,
                },
                timestamp=time.time(),
                version=self._sync_version,
                previous_sync_id=self._last_sync_id,
            )

            self._last_sync_id = sync.sync_id
            self._sync_history.append(sync)
            self._stats.total_syncs_performed += 1
            self._stats.last_activity = time.time()

            self._state = previous_state

            logger.info(
                "State sync completed: mode=%s version=%d",
                mode.name,
                self._sync_version,
            )

            return sync

    def get_sync_history(self, limit: Optional[int] = None) -> List[StateSync]:
        """Return the history of state synchronizations.

        Args:
            limit: Maximum number of entries to return. Returns all if None.

        Returns:
            A list of StateSync objects, most recent first.
        """
        with self._lock:
            history = list(self._sync_history)
            if limit is not None:
                history = history[-limit:]
            return history

    # ------------------------------------------------------------------
    # Status and statistics
    # ------------------------------------------------------------------

    def get_status(self) -> ProtocolSnapshot:
        """Return a complete snapshot of the current protocol state.

        This includes the connection state, pending command count,
        command history, event listener counts, session ID, and
        aggregated statistics.

        Returns:
            A ProtocolSnapshot describing the current state.
        """
        with self._lock:
            history_summary: List[Tuple[str, CommandType, str]] = list(
                self._command_history
            )[-50:]

            return ProtocolSnapshot(
                snapshot_id=str(uuid.uuid4()),
                state=self._state,
                pending_commands=len(self._command_queue),
                command_history=history_summary,
                event_listener_count=sum(
                    len(v) for v in self._event_listeners.values()
                )
                + len(self._global_listeners),
                session_id=self._session_id,
                stats=self._get_stats_copy(),
                timestamp=time.time(),
            )

    def get_stats(self) -> ProtocolStats:
        """Return a copy of the current protocol statistics.

        Returns:
            A ProtocolStats object with current metrics.
        """
        with self._lock:
            return self._get_stats_copy()

    def _get_stats_copy(self) -> ProtocolStats:
        """Return a snapshot copy of the current statistics.

        Returns:
            A ProtocolStats copy with up-to-date uptime.
        """
        stats = ProtocolStats(
            total_commands_sent=self._stats.total_commands_sent,
            total_commands_completed=self._stats.total_commands_completed,
            total_commands_failed=self._stats.total_commands_failed,
            total_queries_sent=self._stats.total_queries_sent,
            total_queries_completed=self._stats.total_queries_completed,
            total_queries_failed=self._stats.total_queries_failed,
            total_events_emitted=self._stats.total_events_emitted,
            total_events_received=self._stats.total_events_received,
            total_syncs_performed=self._stats.total_syncs_performed,
            average_command_latency_ms=self._stats.average_command_latency_ms,
            average_query_latency_ms=self._stats.average_query_latency_ms,
            uptime_seconds=(
                time.time() - self._started_at
                if self._started_at > 0
                else 0.0
            ),
            last_activity=self._stats.last_activity,
            bytes_sent=self._stats.bytes_sent,
            bytes_received=self._stats.bytes_received,
        )
        return stats

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_active(self) -> None:
        """Raise RuntimeError if the protocol is not initialized."""
        if not self._active:
            raise RuntimeError(
                "Communication protocol is not initialized. "
                "Call initialize() first."
            )

    def is_active(self) -> bool:
        """Return whether the protocol is currently active.

        Returns:
            True if the protocol has been initialized and not shut down.
        """
        with self._lock:
            return self._active

    def get_session_id(self) -> str:
        """Return the current session identifier.

        Returns:
            The session ID string, or an empty string if not initialized.
        """
        with self._lock:
            return self._session_id

    def get_state(self) -> ProtocolState:
        """Return the current protocol connection state.

        Returns:
            The current ProtocolState enum value.
        """
        with self._lock:
            return self._state

    def get_version(self) -> int:
        """Return the current synchronization version number.

        Returns:
            The monotonic sync version counter.
        """
        with self._lock:
            return self._sync_version


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_communication_protocol() -> AgentEngineCommunicationProtocol:
    """Get the AgentEngineCommunicationProtocol singleton instance."""
    return AgentEngineCommunicationProtocol.get_instance()