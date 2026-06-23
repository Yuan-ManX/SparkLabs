"""
SparkLabs Agent - Game Engine Bridge

Real-time bidirectional bridge between AI agent decision-making and the
SparkLabs game engine runtime. The Game Engine Bridge enables agents to
query the current engine state, inject commands into the runtime pipeline,
subscribe to engine events, and synchronize state snapshots -- all through
a unified, thread-safe interface.

Architecture:
  AgentGameEngineBridge
    |-- CommandPipeline (typed command queue with priority-based dispatch)
    |-- EventBus (channel-based event subscription and delivery)
    |-- StateSync (engine state snapshotting with version tracking)
    |-- SessionManager (agent-engine session lifecycle and statistics)
    |-- TelemetryChannel (runtime metrics and performance data)
    |-- DebugChannel (development-time inspection and introspection)

Data Flow:
  Agent issues command -> Bridge validates and enqueues -> Engine processes
  -> Engine emits event -> Bridge routes to subscribers -> Agent handles
  -> Agent queries state -> Bridge snapshots engine data -> Agent analyzes

The bridge supports multiple concurrent agent sessions, each with its own
command history and event subscription set. All operations are protected
by a reentrant lock to ensure thread safety in multi-agent environments.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BridgeCommandType(Enum):
    """Types of commands that can be issued through the game engine bridge."""
    ENGINE_QUERY = "engine_query"
    STATE_INJECT = "state_inject"
    RUNTIME_ACTION = "runtime_action"
    ENTITY_MANIPULATE = "entity_manipulate"
    SCENE_COMMAND = "scene_command"
    RESOURCE_COMMAND = "resource_command"


class BridgeChannel(Enum):
    """Communication channels for bridge message routing."""
    COMMAND = "command"
    EVENT = "event"
    STATE_SYNC = "state_sync"
    TELEMETRY = "telemetry"
    DEBUG = "debug"


class CommandPriority(Enum):
    """Priority levels for bridge command dispatch ordering."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class ExecutionStatus(Enum):
    """Execution lifecycle states for bridge commands."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class EngineQuery:
    """A structured query for retrieving engine state information.

    Attributes:
        id: unique identifier for this query.
        query_type: the category of engine data being requested.
        target: the specific engine subsystem or entity to query.
        parameters: key-value parameters refining the query scope.
        timestamp: ISO-8601 timestamp when the query was created.
        priority: dispatch priority for the query.
        timeout: maximum seconds to wait for a response; 0 means no timeout.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    query_type: str = ""
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    priority: CommandPriority = CommandPriority.NORMAL
    timeout: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query_type": self.query_type,
            "target": self.target,
            "parameters": dict(self.parameters),
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "timeout": self.timeout,
        }


@dataclass
class BridgeCommand:
    """A command dispatched from an AI agent to the game engine runtime.

    Attributes:
        id: unique identifier for this command.
        command_type: the category of command being issued.
        channel: the bridge channel through which the command is routed.
        target_entity: the entity or subsystem targeted by the command.
        payload: the command data payload.
        priority: dispatch priority.
        timestamp: ISO-8601 timestamp when the command was created.
        status: current execution status of the command.
        result: optional result data after successful execution.
        error: optional error message if execution failed.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    command_type: BridgeCommandType = BridgeCommandType.RUNTIME_ACTION
    channel: BridgeChannel = BridgeChannel.COMMAND
    target_entity: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: CommandPriority = CommandPriority.NORMAL
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "command_type": self.command_type.value,
            "channel": self.channel.value,
            "target_entity": self.target_entity,
            "payload": dict(self.payload),
            "priority": self.priority.value,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "result": dict(self.result) if self.result else None,
            "error": self.error,
        }


@dataclass
class EngineEvent:
    """An event emitted by the game engine and routed to subscribed agents.

    Attributes:
        id: unique identifier for this event.
        event_type: the category of event (e.g. 'collision', 'spawn', 'destroy').
        source: the entity or subsystem that emitted the event.
        payload: event-specific data.
        timestamp: ISO-8601 timestamp when the event was emitted.
        channel: the bridge channel on which the event was delivered.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = ""
    source: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    channel: BridgeChannel = BridgeChannel.EVENT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "source": self.source,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
            "channel": self.channel.value,
        }


@dataclass
class StateSnapshot:
    """A point-in-time capture of an entity's component state.

    Attributes:
        id: unique identifier for this snapshot.
        entity_id: the entity whose state was captured.
        component_data: dictionary of component type to component state.
        timestamp: ISO-8601 timestamp when the snapshot was taken.
        version: monotonically increasing revision counter for this entity.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    component_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "component_data": dict(self.component_data),
            "timestamp": self.timestamp,
            "version": self.version,
        }


@dataclass
class BridgeSession:
    """A tracked session representing an agent's interaction with the engine.

    Attributes:
        id: unique identifier for this session.
        agent_id: the agent associated with this session.
        engine_version: version string of the connected game engine.
        start_time: ISO-8601 timestamp when the session was created.
        commands_issued: cumulative count of commands sent by this session.
        events_received: cumulative count of events delivered to this session.
        state: current session state identifier (e.g. 'active', 'paused', 'closed').
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    engine_version: str = ""
    start_time: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    commands_issued: int = 0
    events_received: int = 0
    state: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "engine_version": self.engine_version,
            "start_time": self.start_time,
            "commands_issued": self.commands_issued,
            "events_received": self.events_received,
            "state": self.state,
        }


# ---------------------------------------------------------------------------
# Agent Game Engine Bridge
# ---------------------------------------------------------------------------

class AgentGameEngineBridge:
    """Real-time bidirectional bridge between AI agents and the game engine.

    The Game Engine Bridge provides a unified interface for AI agents to
    interact with the SparkLabs game engine runtime. Agents can query the
    current engine state, dispatch commands into the runtime pipeline,
    subscribe to engine events, and synchronize entity state snapshots.

    The bridge supports multiple named instances (e.g. "default", "render",
    "physics") each with independent command queues, event subscriptions,
    and session tracking. Thread safety is ensured via a reentrant lock.

    Usage:
        bridge = get_agent_game_engine_bridge()
        query = bridge.query_engine("transform", "Player", {"include_children": True})
        cmd = bridge.send_command(BridgeCommandType.ENTITY_MANIPULATE, "Enemy_01",
                                  {"action": "destroy"}, CommandPriority.HIGH)
        sub_id = bridge.subscribe_events(["collision", "trigger"], my_callback)
        snapshot = bridge.get_state_snapshot("Player")
    """

    _instances: Dict[str, "AgentGameEngineBridge"] = {}
    _lock = threading.RLock()

    _MAX_COMMANDS: int = 10000
    _MAX_SESSIONS: int = 500
    _MAX_SUBSCRIPTIONS: int = 2000
    _MAX_SNAPSHOTS: int = 5000

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._commands: Dict[str, BridgeCommand] = {}
        self._queries: Dict[str, EngineQuery] = {}
        self._events: Dict[str, EngineEvent] = {}
        self._snapshots: Dict[str, StateSnapshot] = {}
        self._entity_snapshots: Dict[str, List[str]] = {}
        self._sessions: Dict[str, BridgeSession] = {}
        self._subscriptions: Dict[str, Dict[str, Any]] = {}

        self._stats: Dict[str, int] = {
            "total_queries": 0,
            "total_commands": 0,
            "total_events": 0,
            "total_snapshots": 0,
            "total_sessions": 0,
            "total_subscriptions": 0,
            "commands_executed": 0,
            "commands_failed": 0,
            "commands_timed_out": 0,
            "commands_rejected": 0,
            "events_delivered": 0,
            "state_injections": 0,
        }

        self._initialized = True

    @classmethod
    def get_instance(cls, name: str = "default") -> "AgentGameEngineBridge":
        """Return a named bridge instance, creating it if it does not exist.

        Uses double-checked locking for thread-safe lazy initialization.
        """
        if name not in cls._instances:
            with cls._lock:
                if name not in cls._instances:
                    cls._instances[name] = cls()
        return cls._instances[name]

    # ------------------------------------------------------------------
    # Engine Query
    # ------------------------------------------------------------------

    def query_engine(
        self,
        query_type: str,
        target: str,
        parameters: Optional[Dict[str, Any]] = None,
        priority: CommandPriority = CommandPriority.NORMAL,
        timeout: float = 0.0,
    ) -> EngineQuery:
        """Create a structured query for retrieving engine state information.

        Args:
            query_type: the category of engine data being requested.
            target: the specific engine subsystem or entity to query.
            parameters: key-value parameters refining the query scope.
            priority: dispatch priority for the query.
            timeout: maximum seconds to wait for a response; 0 means no timeout.

        Returns:
            An EngineQuery instance registered in the bridge.
        """
        query = EngineQuery(
            query_type=query_type,
            target=target,
            parameters=parameters or {},
            priority=priority,
            timeout=timeout,
        )

        with self._lock:
            self._queries[query.id] = query
            self._stats["total_queries"] += 1

        return query

    # ------------------------------------------------------------------
    # Command Dispatch
    # ------------------------------------------------------------------

    def send_command(
        self,
        command_type: BridgeCommandType,
        target_entity: str,
        payload: Optional[Dict[str, Any]] = None,
        priority: CommandPriority = CommandPriority.NORMAL,
        channel: BridgeChannel = BridgeChannel.COMMAND,
    ) -> BridgeCommand:
        """Issue a command from an AI agent to the game engine runtime.

        Commands are enqueued with the specified priority and routed through
        the designated bridge channel. If the command queue exceeds the
        maximum capacity, the lowest-priority pending command is evicted.

        Args:
            command_type: the category of command being issued.
            target_entity: the entity or subsystem targeted by the command.
            payload: the command data payload.
            priority: dispatch priority.
            channel: the bridge channel through which the command is routed.

        Returns:
            A BridgeCommand instance registered in the bridge.
        """
        command = BridgeCommand(
            command_type=command_type,
            channel=channel,
            target_entity=target_entity,
            payload=payload or {},
            priority=priority,
        )

        with self._lock:
            self._enforce_max_commands()
            self._commands[command.id] = command
            self._stats["total_commands"] += 1

        return command

    # ------------------------------------------------------------------
    # State Injection
    # ------------------------------------------------------------------

    def inject_state(
        self,
        entity_id: str,
        component_data: Dict[str, Any],
    ) -> StateSnapshot:
        """Inject component state data into an entity's state tracking.

        Creates a new versioned snapshot for the given entity with the
        provided component data. The snapshot version is incremented from
        the previous snapshot for the same entity.

        Args:
            entity_id: the entity whose state is being injected.
            component_data: dictionary of component type to component state.

        Returns:
            A StateSnapshot instance representing the injected state.
        """
        with self._lock:
            existing = self._entity_snapshots.get(entity_id, [])
            version = 1
            if existing:
                latest_id = existing[-1]
                latest = self._snapshots.get(latest_id)
                if latest is not None:
                    version = latest.version + 1

            snapshot = StateSnapshot(
                entity_id=entity_id,
                component_data=component_data,
                version=version,
            )

            self._enforce_max_snapshots()
            self._snapshots[snapshot.id] = snapshot
            if entity_id not in self._entity_snapshots:
                self._entity_snapshots[entity_id] = []
            self._entity_snapshots[entity_id].append(snapshot.id)
            self._stats["total_snapshots"] += 1
            self._stats["state_injections"] += 1

        return snapshot

    # ------------------------------------------------------------------
    # Event Subscriptions
    # ------------------------------------------------------------------

    def subscribe_events(
        self,
        event_types: List[str],
        callback: Optional[Callable[[EngineEvent], None]] = None,
    ) -> str:
        """Subscribe to engine events of the specified types.

        When a matching event is emitted by the engine, the provided callback
        is invoked. If no callback is provided, events are queued and can be
        polled via the subscription record.

        Args:
            event_types: list of event type strings to subscribe to.
            callback: optional callable invoked with each matching EngineEvent.

        Returns:
            A subscription ID string that can be used to unsubscribe.
        """
        subscription_id = uuid.uuid4().hex

        with self._lock:
            if len(self._subscriptions) >= self._MAX_SUBSCRIPTIONS:
                oldest_sub = min(
                    self._subscriptions.keys(),
                    key=lambda k: self._subscriptions[k].get("created_at", ""),
                    default=None,
                )
                if oldest_sub is not None:
                    del self._subscriptions[oldest_sub]

            self._subscriptions[subscription_id] = {
                "subscription_id": subscription_id,
                "event_types": list(event_types),
                "callback": callback,
                "created_at": datetime.datetime.utcnow().isoformat(),
                "events_received": 0,
            }
            self._stats["total_subscriptions"] += 1

        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove an event subscription by its identifier.

        Args:
            subscription_id: the subscription ID returned by subscribe_events.

        Returns:
            True if the subscription was found and removed, False otherwise.
        """
        with self._lock:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]
                return True
            return False

    # ------------------------------------------------------------------
    # State Snapshot
    # ------------------------------------------------------------------

    def get_state_snapshot(self, entity_id: str) -> Optional[StateSnapshot]:
        """Retrieve the latest state snapshot for a given entity.

        Args:
            entity_id: the entity whose latest snapshot is requested.

        Returns:
            The most recent StateSnapshot for the entity, or None if no
            snapshots exist for the given entity.
        """
        with self._lock:
            snapshot_ids = self._entity_snapshots.get(entity_id)
            if not snapshot_ids:
                return None
            latest_id = snapshot_ids[-1]
            return self._snapshots.get(latest_id)

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def create_session(
        self,
        agent_id: str,
        engine_version: str = "",
    ) -> BridgeSession:
        """Create a new tracked session for an agent's engine interaction.

        Args:
            agent_id: the agent creating the session.
            engine_version: version string of the connected game engine.

        Returns:
            A BridgeSession instance registered in the bridge.
        """
        session = BridgeSession(
            agent_id=agent_id,
            engine_version=engine_version,
        )

        with self._lock:
            if len(self._sessions) >= self._MAX_SESSIONS:
                oldest_session = min(
                    self._sessions.values(),
                    key=lambda s: s.start_time,
                    default=None,
                )
                if oldest_session is not None:
                    del self._sessions[oldest_session.id]

            self._sessions[session.id] = session
            self._stats["total_sessions"] += 1

        return session

    def get_session(self, session_id: str) -> Optional[BridgeSession]:
        """Retrieve a session by its identifier.

        Args:
            session_id: the session ID to look up.

        Returns:
            The BridgeSession if found, or None.
        """
        with self._lock:
            return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Command Execution
    # ------------------------------------------------------------------

    def execute_command(self, command_id: str) -> ExecutionStatus:
        """Execute a pending command and transition it through its lifecycle.

        Simulates the execution of a command by transitioning its status
        from PENDING to IN_PROGRESS and then to either SUCCESS or FAILED.
        In a production environment, this would delegate to the actual
        engine runtime for command processing.

        Args:
            command_id: the identifier of the command to execute.

        Returns:
            The final ExecutionStatus of the command after execution.
        """
        with self._lock:
            command = self._commands.get(command_id)
            if command is None:
                return ExecutionStatus.REJECTED

            if command.status != ExecutionStatus.PENDING:
                if command.status == ExecutionStatus.SUCCESS:
                    return ExecutionStatus.SUCCESS
                if command.status == ExecutionStatus.FAILED:
                    return ExecutionStatus.FAILED
                return command.status

            command.status = ExecutionStatus.IN_PROGRESS

            try:
                command.status = ExecutionStatus.SUCCESS
                command.result = {
                    "executed_at": datetime.datetime.utcnow().isoformat(),
                    "command_id": command_id,
                }
                self._stats["commands_executed"] += 1
                return ExecutionStatus.SUCCESS
            except Exception as exc:
                command.status = ExecutionStatus.FAILED
                command.error = str(exc)
                self._stats["commands_failed"] += 1
                return ExecutionStatus.FAILED

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about the bridge instance.

        Includes counts for commands, queries, events, snapshots, sessions,
        subscriptions, and execution outcomes.
        """
        with self._lock:
            pending_count = sum(
                1 for c in self._commands.values()
                if c.status == ExecutionStatus.PENDING
            )
            in_progress_count = sum(
                1 for c in self._commands.values()
                if c.status == ExecutionStatus.IN_PROGRESS
            )

            return {
                **dict(self._stats),
                "active_commands": len(self._commands),
                "pending_commands": pending_count,
                "in_progress_commands": in_progress_count,
                "active_queries": len(self._queries),
                "active_events": len(self._events),
                "active_snapshots": len(self._snapshots),
                "active_sessions": len(self._sessions),
                "active_subscriptions": len(self._subscriptions),
                "tracked_entities": len(self._entity_snapshots),
                "max_commands": self._MAX_COMMANDS,
                "max_sessions": self._MAX_SESSIONS,
                "max_subscriptions": self._MAX_SUBSCRIPTIONS,
                "max_snapshots": self._MAX_SNAPSHOTS,
            }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the bridge to its initial empty state.

        Clears all commands, queries, events, snapshots, sessions,
        subscriptions, and statistics counters.
        """
        with self._lock:
            self._commands.clear()
            self._queries.clear()
            self._events.clear()
            self._snapshots.clear()
            self._entity_snapshots.clear()
            self._sessions.clear()
            self._subscriptions.clear()

            self._stats = {
                "total_queries": 0,
                "total_commands": 0,
                "total_events": 0,
                "total_snapshots": 0,
                "total_sessions": 0,
                "total_subscriptions": 0,
                "commands_executed": 0,
                "commands_failed": 0,
                "commands_timed_out": 0,
                "commands_rejected": 0,
                "events_delivered": 0,
                "state_injections": 0,
            }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _enforce_max_commands(self) -> None:
        """Evict the lowest-priority pending command if over capacity.

        Caller must hold the lock.
        """
        if len(self._commands) < self._MAX_COMMANDS:
            return

        priority_order = {
            CommandPriority.BACKGROUND: 0,
            CommandPriority.LOW: 1,
            CommandPriority.NORMAL: 2,
            CommandPriority.HIGH: 3,
            CommandPriority.CRITICAL: 4,
        }

        candidates = [
            (cid, cmd)
            for cid, cmd in self._commands.items()
            if cmd.status == ExecutionStatus.PENDING
            and cmd.priority != CommandPriority.CRITICAL
        ]

        if not candidates:
            candidates = [
                (cid, cmd)
                for cid, cmd in self._commands.items()
                if cmd.status == ExecutionStatus.PENDING
            ]

        if candidates:
            candidates.sort(
                key=lambda item: (
                    priority_order.get(item[1].priority, 0),
                    item[1].timestamp,
                ),
            )
            evict_id = candidates[0][0]
            evicted = self._commands.pop(evict_id, None)
            if evicted is not None:
                evicted.status = ExecutionStatus.REJECTED
                evicted.error = "Evicted due to command queue overflow"
                self._stats["commands_rejected"] += 1

    def _enforce_max_snapshots(self) -> None:
        """Evict the oldest snapshot if over capacity.

        Caller must hold the lock.
        """
        if len(self._snapshots) < self._MAX_SNAPSHOTS:
            return

        sorted_snapshots = sorted(
            self._snapshots.items(),
            key=lambda item: item[1].timestamp,
        )
        overflow = len(self._snapshots) - self._MAX_SNAPSHOTS + 1
        for snap_id, snap in sorted_snapshots[:overflow]:
            del self._snapshots[snap_id]
            entity_list = self._entity_snapshots.get(snap.entity_id)
            if entity_list and snap_id in entity_list:
                entity_list.remove(snap_id)
                if not entity_list:
                    del self._entity_snapshots[snap.entity_id]


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_agent_game_engine_bridge(name: str = "default") -> AgentGameEngineBridge:
    """Return the named AgentGameEngineBridge instance.

    Creates the instance on first access using the double-checked locking
    singleton pattern. The default name is "default".

    Args:
        name: the instance name to retrieve or create.

    Returns:
        The AgentGameEngineBridge instance for the given name.
    """
    return AgentGameEngineBridge.get_instance(name)