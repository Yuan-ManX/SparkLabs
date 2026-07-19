"""
SparkLabs Engine - Kernel Integration Layer

Binds the unified AgentKernel with the SparkLabs engine runtime, creating a
single coherent surface where cognitive cycles and engine ticks advance in
lockstep. Higher-level game agents (director, conductor, brain) use this
layer to perceive live engine state, reason about it, and dispatch actions
without touching engine internals directly.

Architecture:
  KernelEngineIntegrator (Singleton)
    |-- TickCoupler       -> synchronizes kernel cycles with engine ticks
    |-- PerceptionPipeline -> converts engine events into kernel perceptions
    |-- ActionPipeline    -> converts kernel task results into engine commands
    |-- StateProjector    -> snapshots engine state into kernel memory
    |-- FeedbackBus       -> routes engine telemetry back into kernel reflection
    |-- SessionRegistry   -> tracks agent-engine sessions and their lifecycle

Data Flow (per tick):
  Engine emits events -> PerceptionPipeline encodes -> Kernel.perceive()
  Kernel.cycle() advances -> ActionPipeline drains tasks -> Engine dispatch
  StateProjector snapshots -> Kernel.memory.write(EPISODIC)
  FeedbackBus aggregates -> Kernel.reflection.reflect()

Original SparkLabs design - cognitive-engine integration substrate.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Integration Enums
# =============================================================================


class IntegrationPhase(Enum):
    """Phases of the integration pipeline within a single tick."""
    COLLECT = "collect"      # Gather engine events and state
    ENCODE = "encode"        # Translate to kernel perceptions
    CYCLE = "cycle"          # Run kernel cognitive cycle
    DISPATCH = "dispatch"    # Drain kernel outputs into engine commands
    FEEDBACK = "feedback"    # Route execution results into reflection


class EngineEventType(Enum):
    """Categories of engine events the integrator recognizes."""
    TICK = "tick"
    SCENE_LOADED = "scene_loaded"
    ENTITY_SPAWNED = "entity_spawned"
    ENTITY_DESTROYED = "entity_destroyed"
    PLAYER_INPUT = "player_input"
    COLLISION = "collision"
    GAME_STATE_CHANGE = "game_state_change"
    PERFORMANCE = "performance"
    ERROR = "error"
    CUSTOM = "custom"


class EngineCommandKind(Enum):
    """Categories of commands the integrator can dispatch to the engine."""
    SPAWN_ENTITY = "spawn_entity"
    DESPAWN_ENTITY = "despawn_entity"
    SET_PROPERTY = "set_property"
    INVOKE_SCRIPT = "invoke_script"
    LOAD_SCENE = "load_scene"
    TRIGGER_EVENT = "trigger_event"
    ADJUST_PARAMETER = "adjust_parameter"
    SEND_INPUT = "send_input"
    CUSTOM = "custom"


class SessionStatus(Enum):
    """Lifecycle state of an integration session."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class EngineEvent:
    """A raw event emitted by the engine."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    kind: EngineEventType = EngineEventType.TICK
    source: str = "engine"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    tick: int = 0


@dataclass
class EngineCommand:
    """A command destined for the engine runtime."""
    command_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    kind: EngineCommandKind = EngineCommandKind.CUSTOM
    target: str = ""                # entity id, scene name, system name
    args: Dict[str, Any] = field(default_factory=dict)
    issued_by: str = "kernel"
    priority: int = 0               # higher = sooner
    timestamp: float = field(default_factory=time.time)


@dataclass
class EngineStateSnapshot:
    """A point-in-time snapshot of engine state for kernel memory."""
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    tick: int = 0
    scene: str = ""
    entity_count: int = 0
    player_state: Dict[str, Any] = field(default_factory=dict)
    key_entities: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class IntegrationSession:
    """Tracks one agent's integration session with the engine."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_name: str = "anonymous"
    status: SessionStatus = SessionStatus.INITIALIZING
    started_at: float = field(default_factory=time.time)
    last_tick: int = 0
    events_collected: int = 0
    commands_dispatched: int = 0
    cycles_run: int = 0
    last_snapshot: Optional[EngineStateSnapshot] = None


@dataclass
class IntegrationTickResult:
    """Result of one integration tick for observability."""
    tick: int = 0
    phase: IntegrationPhase = IntegrationPhase.COLLECT
    events_collected: int = 0
    perceptions_encoded: int = 0
    kernel_cycle_ran: bool = False
    commands_dispatched: int = 0
    snapshot_written: bool = False
    feedback_records: int = 0
    duration_s: float = 0.0


# =============================================================================
# Perception Pipeline
# =============================================================================


class PerceptionPipeline:
    """
    Converts raw engine events into kernel perceptions. Applies salience
    scoring and optional filtering so the kernel is not flooded with noise.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._salience_map: Dict[EngineEventType, float] = {
            EngineEventType.ERROR: 0.95,
            EngineEventType.PLAYER_INPUT: 0.8,
            EngineEventType.GAME_STATE_CHANGE: 0.75,
            EngineEventType.COLLISION: 0.6,
            EngineEventType.ENTITY_SPAWNED: 0.5,
            EngineEventType.ENTITY_DESTROYED: 0.5,
            EngineEventType.SCENE_LOADED: 0.7,
            EngineEventType.PERFORMANCE: 0.4,
            EngineEventType.TICK: 0.2,
            EngineEventType.CUSTOM: 0.5,
        }
        self._filters: List[Callable[[EngineEvent], bool]] = []

    def register_filter(self, predicate: Callable[[EngineEvent], bool]) -> None:
        """Register a filter; events where predicate returns False are dropped."""
        with self._lock:
            self._filters.append(predicate)

    def encode(self, event: EngineEvent) -> Optional[Dict[str, Any]]:
        """Translate an engine event into a kernel perception payload."""
        for predicate in list(self._filters):
            try:
                if not predicate(event):
                    return None
            except Exception as exc:
                logger.warning("Perception filter raised: %s", exc)

        salience = self._salience_map.get(event.kind, 0.4)
        return {
            "source": f"engine:{event.source}",
            "channel": event.kind.value,
            "payload": {
                "event_id": event.event_id,
                "kind": event.kind.value,
                "tick": event.tick,
                "data": dict(event.payload),
            },
            "salience": salience,
            "timestamp": event.timestamp,
        }


# =============================================================================
# Action Pipeline
# =============================================================================


class ActionPipeline:
    """
    Drains kernel task outputs and converts them into engine commands.
    Maintains a priority queue so critical commands are dispatched first.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._pending: Deque[EngineCommand] = deque()
        self._dispatched: Deque[EngineCommand] = deque(maxlen=200)
        self._handlers: Dict[EngineCommandKind, Callable[[EngineCommand], Dict[str, Any]]] = {}
        self._default_handler: Optional[Callable[[EngineCommand], Dict[str, Any]]] = None

    def register_handler(
        self,
        kind: EngineCommandKind,
        handler: Callable[[EngineCommand], Dict[str, Any]],
    ) -> None:
        with self._lock:
            self._handlers[kind] = handler

    def set_default_handler(self, handler: Callable[[EngineCommand], Dict[str, Any]]) -> None:
        with self._lock:
            self._default_handler = handler

    def enqueue(self, command: EngineCommand) -> None:
        with self._lock:
            self._pending.append(command)
            # Keep queue sorted by priority (stable for equal priorities)
            items = sorted(self._pending, key=lambda c: -c.priority)
            self._pending = deque(items)

    def enqueue_many(self, commands: List[EngineCommand]) -> None:
        for cmd in commands:
            self.enqueue(cmd)

    def drain(self, max_per_tick: int = 16) -> List[Tuple[EngineCommand, Dict[str, Any]]]:
        """Dispatch up to `max_per_tick` commands, returning results."""
        results: List[Tuple[EngineCommand, Dict[str, Any]]] = []
        with self._lock:
            pending = list(self._pending)[:max_per_tick]
            self._pending = deque(list(self._pending)[max_per_tick:])

        for cmd in pending:
            handler = self._handlers.get(cmd.kind) or self._default_handler
            if handler is None:
                results.append((cmd, {"status": "no_handler", "command_id": cmd.command_id}))
                continue
            try:
                result = handler(cmd)
            except Exception as exc:
                logger.warning("Command handler failed for %s: %s", cmd.kind.value, exc)
                result = {"status": "error", "error": str(exc), "command_id": cmd.command_id}
            with self._lock:
                self._dispatched.append(cmd)
            results.append((cmd, result))
        return results

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def dispatched_count(self) -> int:
        with self._lock:
            return len(self._dispatched)


# =============================================================================
# State Projector
# =============================================================================


class StateProjector:
    """
    Captures engine state snapshots at a configurable cadence and writes
    them into the kernel's episodic memory so the agent can recall recent
    game state without re-querying the engine.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._snapshot_interval: int = 8  # ticks between snapshots
        self._last_snapshot_tick: int = -1
        self._snapshots: Deque[EngineStateSnapshot] = deque(maxlen=64)
        self._snapshot_provider: Optional[Callable[[], EngineStateSnapshot]] = None

    def set_provider(self, provider: Callable[[], EngineStateSnapshot]) -> None:
        with self._lock:
            self._snapshot_provider = provider

    def set_interval(self, interval: int) -> None:
        with self._lock:
            self._snapshot_interval = max(1, interval)

    def maybe_snapshot(self, tick: int) -> Optional[EngineStateSnapshot]:
        """Capture a snapshot if the cadence interval has elapsed."""
        with self._lock:
            if tick - self._last_snapshot_tick < self._snapshot_interval:
                return None
            if self._snapshot_provider is None:
                return None
            self._last_snapshot_tick = tick

        try:
            snapshot = self._snapshot_provider()
        except Exception as exc:
            logger.warning("State snapshot provider failed: %s", exc)
            return None
        with self._lock:
            self._snapshots.append(snapshot)
        return snapshot

    def recent_snapshots(self, limit: int = 5) -> List[EngineStateSnapshot]:
        with self._lock:
            return list(self._snapshots)[-limit:]

    def latest(self) -> Optional[EngineStateSnapshot]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None


# =============================================================================
# Feedback Bus
# =============================================================================


class FeedbackBus:
    """
    Aggregates execution results and engine telemetry into structured
    feedback records suitable for the kernel's reflection loop.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: Deque[Dict[str, Any]] = deque(maxlen=128)
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def publish(self, record: Dict[str, Any]) -> None:
        with self._lock:
            self._records.append(record)
            subscribers = list(self._subscribers)
        for sub in subscribers:
            try:
                sub(record)
            except Exception as exc:
                logger.warning("Feedback subscriber raised: %s", exc)

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            self._subscribers.append(callback)

    def recent(self, limit: int = 16) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._records)[-limit:]

    def aggregate_stats(self) -> Dict[str, Any]:
        with self._lock:
            records = list(self._records)
        if not records:
            return {"count": 0}
        successes = sum(1 for r in records if r.get("status") == "success")
        return {
            "count": len(records),
            "successes": successes,
            "failures": len(records) - successes,
            "success_rate": round(successes / len(records), 3),
        }


# =============================================================================
# Session Registry
# =============================================================================


class SessionRegistry:
    """Tracks all integration sessions and provides aggregate statistics."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: Dict[str, IntegrationSession] = {}

    def open(self, agent_name: str) -> IntegrationSession:
        session = IntegrationSession(agent_name=agent_name)
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def close(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.status = SessionStatus.TERMINATED

    def get(self, session_id: str) -> Optional[IntegrationSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_active(self) -> List[IntegrationSession]:
        with self._lock:
            return [s for s in self._sessions.values() if s.status == SessionStatus.ACTIVE]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            sessions = list(self._sessions.values())
        return {
            "total": len(sessions),
            "active": sum(1 for s in sessions if s.status == SessionStatus.ACTIVE),
            "terminated": sum(1 for s in sessions if s.status == SessionStatus.TERMINATED),
            "total_cycles": sum(s.cycles_run for s in sessions),
            "total_commands": sum(s.commands_dispatched for s in sessions),
        }


# =============================================================================
# Kernel-Engine Integrator
# =============================================================================


class KernelEngineIntegrator:
    """
    Singleton integrator that binds the AgentKernel with the engine runtime.
    Provides a single `tick()` entry point that advances both the kernel and
    the engine by one step, with perception flow, action dispatch, state
    snapshotting, and feedback aggregation.
    """

    _instance: Optional["KernelEngineIntegrator"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if KernelEngineIntegrator._instance is not None:
            raise RuntimeError("Use KernelEngineIntegrator.get_instance()")
        self._initialized: bool = False
        self._lock = threading.RLock()

        # Pipelines
        self.perception_pipeline: PerceptionPipeline = PerceptionPipeline()
        self.action_pipeline: ActionPipeline = ActionPipeline()
        self.state_projector: StateProjector = StateProjector()
        self.feedback_bus: FeedbackBus = FeedbackBus()
        self.sessions: SessionRegistry = SessionRegistry()

        # Tick state
        self._tick: int = 0
        self._last_result: Optional[IntegrationTickResult] = None
        self._results_history: Deque[IntegrationTickResult] = deque(maxlen=64)

        # Wiring
        self._kernel: Any = None  # AgentKernel instance (lazy)
        self._event_subscribers: List[Callable[[EngineEvent], None]] = []
        self._engine_event_source: Optional[Callable[[], List[EngineEvent]]] = None
        self._default_command_handler_set: bool = False

    @classmethod
    def get_instance(cls) -> "KernelEngineIntegrator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def initialize(self, kernel: Optional[Any] = None) -> None:
        """Initialize the integrator, optionally injecting a kernel."""
        with self._lock:
            if self._initialized:
                return
            if kernel is not None:
                self._kernel = kernel
            else:
                # Lazy import to avoid circular dependencies
                try:
                    from sparkai.agent.agent_unified_kernel import AgentKernel
                    self._kernel = AgentKernel.get_instance()
                except Exception as exc:
                    logger.warning("AgentKernel acquisition failed: %s", exc)
                    self._kernel = None

            # Register a default no-op command handler so dispatch always succeeds
            if not self._default_command_handler_set:
                self.action_pipeline.set_default_handler(self._default_command_handler)
                self._default_command_handler_set = True

            self._initialized = True
            logger.info("KernelEngineIntegrator initialized")

    def _default_command_handler(self, command: EngineCommand) -> Dict[str, Any]:
        """Default handler acknowledges commands without side effects."""
        return {
            "status": "acknowledged",
            "command_id": command.command_id,
            "kind": command.kind.value,
            "target": command.target,
        }

    # -------------------------------------------------------------------------
    # Event Source Wiring
    # -------------------------------------------------------------------------

    def set_engine_event_source(
        self, source: Callable[[], List[EngineEvent]]
    ) -> None:
        """Register a callable that yields engine events on demand."""
        with self._lock:
            self._engine_event_source = source

    def subscribe_to_events(
        self, callback: Callable[[EngineEvent], None]
    ) -> None:
        """Subscribe to engine events as they are collected."""
        with self._lock:
            self._event_subscribers.append(callback)

    def emit_event(self, event: EngineEvent) -> None:
        """Manually emit an engine event into the integrator."""
        with self._lock:
            subscribers = list(self._event_subscribers)
        for sub in subscribers:
            try:
                sub(event)
            except Exception as exc:
                logger.warning("Event subscriber raised: %s", exc)

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    def open_session(self, agent_name: str) -> IntegrationSession:
        return self.sessions.open(agent_name)

    def close_session(self, session_id: str) -> None:
        self.sessions.close(session_id)

    # -------------------------------------------------------------------------
    # Tick Pipeline
    # -------------------------------------------------------------------------

    def tick(self) -> IntegrationTickResult:
        """
        Advance the integrator by one tick. Runs the full pipeline:
        collect -> encode -> cycle -> dispatch -> feedback.
        """
        if not self._initialized:
            self.initialize()

        start = time.time()
        self._tick += 1
        result = IntegrationTickResult(tick=self._tick, phase=IntegrationPhase.COLLECT)

        # Phase 1: Collect engine events
        events: List[EngineEvent] = []
        if self._engine_event_source is not None:
            try:
                events = list(self._engine_event_source() or [])
            except Exception as exc:
                logger.warning("Engine event source failed: %s", exc)
                events = []
        result.events_collected = len(events)

        # Notify subscribers and update active sessions
        for event in events:
            self.emit_event(event)
        for session in self.sessions.list_active():
            session.events_collected += len(events)
            session.last_tick = self._tick

        # Phase 2: Encode perceptions into kernel
        result.phase = IntegrationPhase.ENCODE
        perceptions_encoded = 0
        if self._kernel is not None:
            for event in events:
                perception = self.perception_pipeline.encode(event)
                if perception is None:
                    continue
                try:
                    self._kernel.perceive(
                        source=perception["source"],
                        channel=perception["channel"],
                        payload=perception["payload"],
                        salience=perception["salience"],
                    )
                    perceptions_encoded += 1
                except Exception as exc:
                    logger.warning("Kernel perceive failed: %s", exc)
        result.perceptions_encoded = perceptions_encoded

        # Phase 3: Run kernel cognitive cycle
        result.phase = IntegrationPhase.CYCLE
        if self._kernel is not None:
            try:
                self._kernel.cycle()
                result.kernel_cycle_ran = True
                for session in self.sessions.list_active():
                    session.cycles_run += 1
            except Exception as exc:
                logger.warning("Kernel cycle failed: %s", exc)

        # Phase 4: Dispatch pending commands to engine
        result.phase = IntegrationPhase.DISPATCH
        dispatch_results = self.action_pipeline.drain(max_per_tick=16)
        result.commands_dispatched = len(dispatch_results)
        for session in self.sessions.list_active():
            session.commands_dispatched += len(dispatch_results)

        # Phase 5: Feedback aggregation
        result.phase = IntegrationPhase.FEEDBACK
        for cmd, cmd_result in dispatch_results:
            self.feedback_bus.publish({
                "tick": self._tick,
                "command_id": cmd.command_id,
                "kind": cmd.kind.value,
                "target": cmd.target,
                "status": cmd_result.get("status", "unknown"),
                "result": cmd_result,
            })
        result.feedback_records = len(dispatch_results)

        # Phase 6: Snapshot engine state into kernel memory
        snapshot = self.state_projector.maybe_snapshot(self._tick)
        if snapshot is not None and self._kernel is not None:
            try:
                # Write snapshot to kernel's episodic memory directly
                from sparkai.agent.agent_unified_kernel import MemoryEntry, MemoryLayer
                self._kernel.memory.write(MemoryEntry(
                    layer=MemoryLayer.EPISODIC,
                    namespace="engine_state",
                    content={
                        "snapshot_id": snapshot.snapshot_id,
                        "tick": snapshot.tick,
                        "scene": snapshot.scene,
                        "entity_count": snapshot.entity_count,
                        "player_state": snapshot.player_state,
                        "metrics": snapshot.metrics,
                    },
                    tags=["engine_state", "snapshot"],
                    salience=0.6,
                ))
                result.snapshot_written = True
                for session in self.sessions.list_active():
                    session.last_snapshot = snapshot
            except Exception as exc:
                logger.warning("Kernel memory write failed: %s", exc)

        result.phase = IntegrationPhase.FEEDBACK
        result.duration_s = time.time() - start

        with self._lock:
            self._last_result = result
            self._results_history.append(result)
        return result

    # -------------------------------------------------------------------------
    # Action Submission API
    # -------------------------------------------------------------------------

    def submit_action(
        self,
        kind: EngineCommandKind,
        target: str = "",
        args: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        issued_by: str = "kernel",
    ) -> EngineCommand:
        """Convenience method to enqueue a single engine command."""
        command = EngineCommand(
            kind=kind,
            target=target,
            args=args or {},
            priority=priority,
            issued_by=issued_by,
        )
        self.action_pipeline.enqueue(command)
        return command

    def submit_actions(self, commands: List[EngineCommand]) -> None:
        self.action_pipeline.enqueue_many(commands)

    # -------------------------------------------------------------------------
    # Observability
    # -------------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "tick": self._tick,
            "kernel_attached": self._kernel is not None,
            "pending_commands": self.action_pipeline.pending_count(),
            "dispatched_commands": self.action_pipeline.dispatched_count(),
            "feedback_stats": self.feedback_bus.aggregate_stats(),
            "sessions": self.sessions.stats(),
            "latest_snapshot": (
                self.state_projector.latest().__dict__
                if self.state_projector.latest() else None
            ),
            "last_tick": {
                "phase": self._last_result.phase.value if self._last_result else None,
                "events": self._last_result.events_collected if self._last_result else 0,
                "perceptions": self._last_result.perceptions_encoded if self._last_result else 0,
                "kernel_cycle": self._last_result.kernel_cycle_ran if self._last_result else False,
                "commands": self._last_result.commands_dispatched if self._last_result else 0,
                "duration_s": self._last_result.duration_s if self._last_result else 0,
            } if self._last_result else None,
        }

    def history(self, limit: int = 16) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._results_history)[-limit:]
        return [
            {
                "tick": r.tick,
                "phase": r.phase.value,
                "events": r.events_collected,
                "perceptions": r.perceptions_encoded,
                "kernel_cycle": r.kernel_cycle_ran,
                "commands": r.commands_dispatched,
                "snapshot": r.snapshot_written,
                "duration_s": r.duration_s,
            }
            for r in items
        ]

    def reset(self) -> None:
        """Reset tick state (preserves handlers and wiring)."""
        with self._lock:
            self._tick = 0
            self._last_result = None
            self._results_history.clear()


# =============================================================================
# Module-level Convenience
# =============================================================================


def get_integrator() -> KernelEngineIntegrator:
    """Return the singleton KernelEngineIntegrator instance."""
    return KernelEngineIntegrator.get_instance()


def quick_status() -> Dict[str, Any]:
    """Return a quick status snapshot of the integrator."""
    return get_integrator().status()
