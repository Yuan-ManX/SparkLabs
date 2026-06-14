"""
SparkLabs Engine - AI Bridge

A bidirectional communication bridge connecting the Agent intelligence layer
with the Engine runtime layer. The AI Bridge enables real-time agent decisions
to influence game state, and game events to trigger agent reasoning.

Architecture:
  AIBridge
    |-- AgentCommandChannel (agent-to-engine command dispatch)
    |-- EngineEventChannel (engine-to-agent event notification)
    |-- StateSynchronizer (bidirectional state mirroring)
    |-- DecisionDispatcher (routes agent decisions to engine systems)
    |-- FeedbackCollector (gathers game metrics for agent analysis)

Capabilities:
  - Real-time agent command injection into running game scenes
  - Game event streaming to agent intelligence systems
  - Bidirectional state synchronization between agent world model and engine
  - Decision routing from agents to specific engine subsystems
  - Gameplay metrics collection for agent feedback loops
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CommandType(Enum):
    SPAWN_ENTITY = "spawn_entity"
    REMOVE_ENTITY = "remove_entity"
    MODIFY_PROPERTY = "modify_property"
    TRIGGER_EVENT = "trigger_event"
    SET_CAMERA = "set_camera"
    PLAY_AUDIO = "play_audio"
    DISPLAY_DIALOGUE = "display_dialogue"
    CHANGE_SCENE = "change_scene"
    PAUSE_GAME = "pause_game"
    RESUME_GAME = "resume_game"
    SET_DIFFICULTY = "set_difficulty"
    MODIFY_PHYSICS = "modify_physics"
    SPAWN_PARTICLE = "spawn_particle"
    EXECUTE_SCRIPT = "execute_script"


class EventType(Enum):
    ENTITY_CREATED = "entity_created"
    ENTITY_DESTROYED = "entity_destroyed"
    COLLISION_OCCURRED = "collision_occurred"
    SCENE_LOADED = "scene_loaded"
    PLAYER_ACTION = "player_action"
    QUEST_PROGRESS = "quest_progress"
    DIALOGUE_STARTED = "dialogue_started"
    DIALOGUE_ENDED = "dialogue_ended"
    ITEM_COLLECTED = "item_collected"
    ENEMY_DEFEATED = "enemy_defeated"
    PLAYER_DIED = "player_died"
    LEVEL_COMPLETE = "level_complete"
    GAME_OVER = "game_over"


class BridgeDirection(Enum):
    AGENT_TO_ENGINE = "agent_to_engine"
    ENGINE_TO_AGENT = "engine_to_agent"


class CommandPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentCommand:
    """A command from an agent to the engine."""
    command_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    command_type: CommandType = CommandType.SPAWN_ENTITY
    agent_id: str = ""
    priority: CommandPriority = CommandPriority.NORMAL
    parameters: Dict[str, Any] = field(default_factory=dict)
    target_entity: str = ""
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None


@dataclass
class EngineEvent:
    """An event from the engine to an agent."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: EventType = EventType.ENTITY_CREATED
    source_entity: str = ""
    target_entity: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    scene_id: str = ""


@dataclass
class SyncedState:
    """Synchronized state between agent world model and engine."""
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    scene_state: Dict[str, Any] = field(default_factory=dict)
    global_state: Dict[str, Any] = field(default_factory=dict)
    last_sync: float = field(default_factory=time.time)
    version: int = 0


@dataclass
class FeedbackMetric:
    """A gameplay metric collected for agent feedback."""
    metric_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    value: float = 0.0
    category: str = ""
    source: str = ""
    timestamp: float = field(default_factory=time.time)


class AIBridge:
    """Bidirectional bridge between agent intelligence and engine runtime."""

    def __init__(self):
        self._lock = threading.RLock()
        self._command_queue: deque = deque(maxlen=500)
        self._event_queue: deque = deque(maxlen=500)
        self._command_history: List[AgentCommand] = []
        self._event_history: List[EngineEvent] = []
        self._synced_state = SyncedState()
        self._feedback_metrics: List[FeedbackMetric] = []
        self._command_handlers: Dict[CommandType, List[Callable]] = {}
        self._event_handlers: Dict[EventType, List[Callable]] = {}
        self._total_commands = 0
        self._total_events = 0
        self._active = True

    # ---- Agent-to-Engine Commands ----

    def send_command(self, command_type: CommandType, agent_id: str = "",
                     parameters: Dict[str, Any] = None,
                     priority: CommandPriority = None,
                     target_entity: str = "") -> AgentCommand:
        cmd = AgentCommand(
            command_type=command_type,
            agent_id=agent_id,
            priority=priority or CommandPriority.NORMAL,
            parameters=parameters or {},
            target_entity=target_entity,
        )
        with self._lock:
            if priority == CommandPriority.CRITICAL:
                self._command_queue.appendleft(cmd)
            else:
                self._command_queue.append(cmd)
            self._total_commands += 1

        self._dispatch_command(cmd)
        return cmd

    def _dispatch_command(self, cmd: AgentCommand):
        handlers = self._command_handlers.get(cmd.command_type, [])
        for handler in handlers:
            try:
                result = handler(cmd)
                if result:
                    cmd.result = result
            except Exception:
                pass
        cmd.status = "dispatched"
        with self._lock:
            self._command_history.append(cmd)

    def on_command(self, command_type: CommandType, handler: Callable):
        with self._lock:
            if command_type not in self._command_handlers:
                self._command_handlers[command_type] = []
            self._command_handlers[command_type].append(handler)

    def process_next_command(self) -> Optional[AgentCommand]:
        with self._lock:
            if self._command_queue:
                cmd = self._command_queue.popleft()
                self._dispatch_command(cmd)
                return cmd
        return None

    def process_all_commands(self) -> int:
        count = 0
        while True:
            cmd = self.process_next_command()
            if cmd is None:
                break
            count += 1
        return count

    # ---- Engine-to-Agent Events ----

    def send_event(self, event_type: EventType, source_entity: str = "",
                   target_entity: str = "", data: Dict[str, Any] = None,
                   scene_id: str = "") -> EngineEvent:
        event = EngineEvent(
            event_type=event_type,
            source_entity=source_entity,
            target_entity=target_entity,
            data=data or {},
            scene_id=scene_id,
        )
        with self._lock:
            self._event_queue.append(event)
            self._total_events += 1

        self._dispatch_event(event)
        return event

    def _dispatch_event(self, event: EngineEvent):
        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass
        with self._lock:
            self._event_history.append(event)

    def on_event(self, event_type: EventType, handler: Callable):
        with self._lock:
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
            self._event_handlers[event_type].append(handler)

    def process_next_event(self) -> Optional[EngineEvent]:
        with self._lock:
            if self._event_queue:
                event = self._event_queue.popleft()
                self._dispatch_event(event)
                return event
        return None

    # ---- State Synchronization ----

    def sync_entity_state(self, entity_id: str, state: Dict[str, Any]):
        with self._lock:
            self._synced_state.entities[entity_id] = state
            self._synced_state.version += 1
            self._synced_state.last_sync = time.time()

    def sync_scene_state(self, scene_state: Dict[str, Any]):
        with self._lock:
            self._synced_state.scene_state = scene_state
            self._synced_state.version += 1
            self._synced_state.last_sync = time.time()

    def sync_global_state(self, global_state: Dict[str, Any]):
        with self._lock:
            self._synced_state.global_state = global_state
            self._synced_state.version += 1
            self._synced_state.last_sync = time.time()

    def get_synced_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "state_id": self._synced_state.state_id,
                "entities": dict(self._synced_state.entities),
                "scene_state": dict(self._synced_state.scene_state),
                "global_state": dict(self._synced_state.global_state),
                "last_sync": self._synced_state.last_sync,
                "version": self._synced_state.version,
            }

    # ---- Feedback Collection ----

    def record_metric(self, name: str, value: float, category: str = "",
                      source: str = "") -> FeedbackMetric:
        metric = FeedbackMetric(
            name=name,
            value=value,
            category=category,
            source=source,
        )
        with self._lock:
            self._feedback_metrics.append(metric)
            if len(self._feedback_metrics) > 1000:
                self._feedback_metrics = self._feedback_metrics[-500:]
        return metric

    def get_metrics(self, category: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            metrics = self._feedback_metrics
            if category:
                metrics = [m for m in metrics if m.category == category]
            return [
                {
                    "metric_id": m.metric_id,
                    "name": m.name,
                    "value": m.value,
                    "category": m.category,
                    "source": m.source,
                    "timestamp": m.timestamp,
                }
                for m in metrics[-limit:]
            ]

    def get_metric_summary(self) -> Dict[str, Any]:
        with self._lock:
            if not self._feedback_metrics:
                return {}
            by_name = {}
            for m in self._feedback_metrics:
                if m.name not in by_name:
                    by_name[m.name] = []
                by_name[m.name].append(m.value)
            return {
                name: {
                    "avg": sum(vals) / len(vals),
                    "min": min(vals),
                    "max": max(vals),
                    "count": len(vals),
                }
                for name, vals in by_name.items()
            }

    # ---- Stats ----

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": self._active,
                "total_commands": self._total_commands,
                "total_events": self._total_events,
                "pending_commands": len(self._command_queue),
                "pending_events": len(self._event_queue),
                "registered_command_handlers": sum(len(h) for h in self._command_handlers.values()),
                "registered_event_handlers": sum(len(h) for h in self._event_handlers.values()),
                "synced_entities": len(self._synced_state.entities),
                "state_version": self._synced_state.version,
                "feedback_metrics": len(self._feedback_metrics),
            }

    def get_command_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "command_id": c.command_id,
                    "command_type": c.command_type.value,
                    "agent_id": c.agent_id,
                    "priority": c.priority.value,
                    "status": c.status,
                    "timestamp": c.timestamp,
                }
                for c in self._command_history[-limit:]
            ]

    def get_event_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type.value,
                    "source_entity": e.source_entity,
                    "target_entity": e.target_entity,
                    "timestamp": e.timestamp,
                }
                for e in self._event_history[-limit:]
            ]


# Singleton instance
_ai_bridge: Optional[AIBridge] = None
_bridge_lock = threading.RLock()


def get_ai_bridge() -> AIBridge:
    global _ai_bridge
    with _bridge_lock:
        if _ai_bridge is None:
            _ai_bridge = AIBridge()
        return _ai_bridge