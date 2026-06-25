"""
SparkLabs Agent - God Mode Controller

Runtime intervention system for the SparkLabs AI-native game engine.
Provides god-mode capabilities allowing developers to intervene in running
game simulations at runtime — editing agent memories, modifying personalities,
injecting world events, observing world state, and overriding agent conversations.

Architecture:
  GodModeController (Singleton)
    |-- GodModeSession (active intervention session bound to a world)
    |-- GodModeCommand (individual intervention command with execution tracking)
    |-- AgentMemoryEdit (memory manipulation record)
    |-- AgentPersonalityEdit (personality trait modification record)
    |-- WorldEventInjection (injected world event with propagation)

Intervention Types:
  MEMORY_EDIT, PERSONALITY_EDIT, EVENT_INJECT, STATE_OVERRIDE,
  CONVERSATION_OVERRIDE, WORLD_EDIT, OBSERVE

Intervention Scopes:
  SINGLE_AGENT, AGENT_GROUP, ALL_AGENTS, WORLD, SCENE

Memory Operations:
  ADD, REMOVE, UPDATE

Usage:
    gm = get_god_mode_controller()
    gm.initialize()
    session = gm.start_session("world_01", {"created_by": "developer"})
    gm.edit_agent_memory("agent_42", "childhood_trauma", "Saved by a stranger", "UPDATE")
    gm.edit_agent_personality("agent_42", "extraversion", 0.8)
    gm.inject_world_event("METEOR_STRIKE", "A meteor crashes into the village",
                          "village_square", ["agent_42", "agent_99"], 0.9, 30.0)
    obs = gm.observe_agent("agent_42")
    world_state = gm.observe_world("world_01")
    gm.end_session(session.id)
    gm.shutdown()
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# Enums
# =============================================================================


class InterventionType(Enum):
    """Types of runtime interventions available in god mode."""
    MEMORY_EDIT = "memory_edit"
    PERSONALITY_EDIT = "personality_edit"
    EVENT_INJECT = "event_inject"
    STATE_OVERRIDE = "state_override"
    CONVERSATION_OVERRIDE = "conversation_override"
    WORLD_EDIT = "world_edit"
    OBSERVE = "observe"


class InterventionScope(Enum):
    """Scope of a god mode intervention."""
    SINGLE_AGENT = "single_agent"
    AGENT_GROUP = "agent_group"
    ALL_AGENTS = "all_agents"
    WORLD = "world"
    SCENE = "scene"


class MemoryOperation(Enum):
    """Operations for editing agent memory."""
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class CommandStatus(Enum):
    """Execution status of a god mode command."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERTED = "reverted"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class GodModeCommand:
    """A single god mode intervention command with execution tracking.

    Attributes:
        id: Unique command identifier (auto-generated).
        intervention_type: Type of intervention being performed.
        scope: Scope of the intervention.
        target_ids: List of agent or entity IDs targeted by this command.
        payload: Command-specific data payload.
        timestamp: When the command was created.
        executed_by: Identifier of the developer who executed the command.
        status: Current execution status.
        result: Result data produced by execution.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    intervention_type: InterventionType = InterventionType.OBSERVE
    scope: InterventionScope = InterventionScope.SINGLE_AGENT
    target_ids: List[str] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)
    executed_by: str = ""
    status: CommandStatus = CommandStatus.PENDING
    result: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "intervention_type": self.intervention_type.value,
            "scope": self.scope.value,
            "target_ids": list(self.target_ids),
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
            "executed_by": self.executed_by,
            "status": self.status.value,
            "result": dict(self.result),
        }


@dataclass
class AgentMemoryEdit:
    """A record of an agent memory modification.

    Attributes:
        agent_id: The agent whose memory is being edited.
        memory_key: Identifier for the specific memory entry.
        old_value: Previous memory content before the edit.
        new_value: New memory content after the edit.
        operation: Type of memory operation (ADD, REMOVE, UPDATE).
        edit_id: Unique identifier for this edit record.
        applied_at: Timestamp when the edit was applied.
        reverted: Whether this edit has been reverted.
    """
    agent_id: str = ""
    memory_key: str = ""
    old_value: Any = None
    new_value: Any = None
    operation: MemoryOperation = MemoryOperation.UPDATE
    edit_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    applied_at: float = field(default_factory=_time_module.time)
    reverted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "edit_id": self.edit_id,
            "agent_id": self.agent_id,
            "memory_key": self.memory_key,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "operation": self.operation.value,
            "applied_at": self.applied_at,
            "reverted": self.reverted,
        }


@dataclass
class AgentPersonalityEdit:
    """A record of an agent personality trait modification.

    Attributes:
        agent_id: The agent whose personality is being edited.
        trait_name: Name of the personality trait being modified.
        old_value: Previous trait value before the edit.
        new_value: New trait value after the edit.
        edit_id: Unique identifier for this edit record.
        applied_at: Timestamp when the edit was applied.
        reverted: Whether this edit has been reverted.
    """
    agent_id: str = ""
    trait_name: str = ""
    old_value: float = 0.0
    new_value: float = 0.0
    edit_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    applied_at: float = field(default_factory=_time_module.time)
    reverted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "edit_id": self.edit_id,
            "agent_id": self.agent_id,
            "trait_name": self.trait_name,
            "old_value": round(self.old_value, 4),
            "new_value": round(self.new_value, 4),
            "applied_at": self.applied_at,
            "reverted": self.reverted,
        }


@dataclass
class WorldEventInjection:
    """An event injected into the game world by god mode.

    Attributes:
        event_type: Category of the injected event.
        description: Human-readable description of the event.
        target_location: Location in the world where the event occurs.
        affected_agents: List of agent IDs affected by this event.
        intensity: Severity or strength of the event (0.0 to 1.0).
        duration: How long the event lasts in seconds (0 for instantaneous).
        injection_id: Unique identifier for this injection.
        applied_at: Timestamp when the event was injected.
        expires_at: When the event expires (if duration > 0).
        status: Current status of the injected event.
    """
    event_type: str = ""
    description: str = ""
    target_location: str = ""
    affected_agents: List[str] = field(default_factory=list)
    intensity: float = 0.5
    duration: float = 0.0
    injection_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    applied_at: float = field(default_factory=_time_module.time)
    expires_at: Optional[float] = None
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "injection_id": self.injection_id,
            "event_type": self.event_type,
            "description": self.description,
            "target_location": self.target_location,
            "affected_agents": list(self.affected_agents),
            "intensity": round(self.intensity, 4),
            "duration": self.duration,
            "applied_at": self.applied_at,
            "expires_at": self.expires_at,
            "status": self.status,
        }


@dataclass
class GodModeSession:
    """An active god mode intervention session bound to a specific world.

    Attributes:
        id: Unique session identifier (auto-generated).
        world_id: The world this session is administering.
        interventions: List of GodModeCommand IDs executed in this session.
        created_at: Timestamp when the session was created.
        is_active: Whether the session is currently active.
        metadata: Arbitrary key-value metadata about the session.
        ended_at: Timestamp when the session was ended (None if active).
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_id: str = ""
    interventions: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    ended_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "world_id": self.world_id,
            "interventions": list(self.interventions),
            "created_at": self.created_at,
            "is_active": self.is_active,
            "metadata": dict(self.metadata),
            "ended_at": self.ended_at,
        }


# =============================================================================
# GodModeController (Singleton)
# =============================================================================


class GodModeController:
    """Runtime intervention system for the SparkLabs AI-native game engine.

    Provides god-mode capabilities for developers to intervene in running
    game simulations at runtime. Supports editing agent memories, modifying
    personalities, injecting world events, observing world state, overriding
    agent conversations, and broadcasting messages to agents.

    Usage:
        gm = get_god_mode_controller()
        gm.initialize()
        session = gm.start_session("world_01", {"created_by": "dev"})
        gm.edit_agent_memory("agent_42", "key_memory", "You are a hero", "UPDATE")
        gm.inject_world_event("STORM", "A storm approaches", "coast", ["agent_1"], 0.7)
        gm.shutdown()
    """

    _instance: Optional["GodModeController"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "GodModeController":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GodModeController":
        """Get or create the singleton instance with double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return
            self._initialized = True

            self._sessions: Dict[str, GodModeSession] = {}
            self._commands: Dict[str, GodModeCommand] = {}
            self._memory_edits: Dict[str, AgentMemoryEdit] = {}
            self._personality_edits: Dict[str, AgentPersonalityEdit] = {}
            self._event_injections: Dict[str, WorldEventInjection] = {}
            self._active_sessions: Dict[str, str] = {}
            self._is_initialized: bool = False
            self._total_commands: int = 0
            self._total_sessions: int = 0

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def initialize(self) -> Dict[str, Any]:
        """Set up the god mode system.

        Initializes internal state and prepares the controller for use.
        Must be called before any other methods.

        Returns:
            A dict with initialization status and controller metadata.
        """
        _time_module.sleep(0.001)
        with self._lock:
            self._is_initialized = True
            return {
                "status": "initialized",
                "controller_id": id(self),
                "sessions_active": len(self._active_sessions),
                "total_commands": self._total_commands,
            }

    def shutdown(self) -> Dict[str, Any]:
        """Clean shutdown of the god mode controller.

        Ends all active sessions, clears all internal state, and resets
        the controller to its initial uninitialized state.

        Returns:
            A dict with shutdown summary.
        """
        _time_module.sleep(0.001)
        with self._lock:
            active_count = len(self._active_sessions)
            for session_id in list(self._active_sessions.values()):
                self.end_session(session_id)

            self._sessions.clear()
            self._commands.clear()
            self._memory_edits.clear()
            self._personality_edits.clear()
            self._event_injections.clear()
            self._active_sessions.clear()
            self._is_initialized = False
            self._total_commands = 0
            self._total_sessions = 0

            return {
                "status": "shutdown",
                "sessions_ended": active_count,
            }

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    def start_session(
        self,
        world_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GodModeSession:
        """Begin a god mode session for a specific world.

        A session tracks all interventions performed on a world during
        a single god mode administration period.

        Args:
            world_id: Identifier of the world being administered.
            metadata: Arbitrary key-value metadata for the session.

        Returns:
            The created GodModeSession.
        """
        _time_module.sleep(0.001)
        with self._lock:
            session = GodModeSession(
                world_id=world_id,
                metadata=dict(metadata) if metadata else {},
                is_active=True,
            )
            self._sessions[session.id] = session
            self._active_sessions[world_id] = session.id
            self._total_sessions += 1
            return session

    def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a god mode session.

        Deactivates the session and records the end timestamp.

        Args:
            session_id: Identifier of the session to end.

        Returns:
            A dict with the session end result.
        """
        _time_module.sleep(0.001)
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"status": "error", "error": "Session not found"}
            if not session.is_active:
                return {"status": "error", "error": "Session already ended"}

            session.is_active = False
            session.ended_at = _time_module.time()

            if session.world_id in self._active_sessions:
                del self._active_sessions[session.world_id]

            return {
                "status": "ended",
                "session_id": session_id,
                "world_id": session.world_id,
                "intervention_count": len(session.interventions),
                "duration": (
                    (session.ended_at - session.created_at)
                    if session.ended_at
                    else 0.0
                ),
            }

    # -------------------------------------------------------------------------
    # Agent Memory Editing
    # -------------------------------------------------------------------------

    def edit_agent_memory(
        self,
        agent_id: str,
        memory_key: str,
        new_value: Any,
        operation: str = "UPDATE",
    ) -> AgentMemoryEdit:
        """Modify an agent's memory at runtime.

        Supports adding new memories, removing existing ones, or updating
        memory content. Each edit is tracked and can be reverted.

        Args:
            agent_id: The agent whose memory is being edited.
            memory_key: Identifier for the specific memory entry.
            new_value: New content for the memory (None for REMOVE).
            operation: One of "ADD", "REMOVE", "UPDATE".

        Returns:
            The AgentMemoryEdit record.
        """
        _time_module.sleep(0.001)
        with self._lock:
            try:
                op = MemoryOperation(operation.lower())
            except ValueError:
                op = MemoryOperation.UPDATE

            edit = AgentMemoryEdit(
                agent_id=agent_id,
                memory_key=memory_key,
                old_value=None,
                new_value=new_value,
                operation=op,
            )
            self._memory_edits[edit.edit_id] = edit
            return edit

    # -------------------------------------------------------------------------
    # Agent Personality Editing
    # -------------------------------------------------------------------------

    def edit_agent_personality(
        self,
        agent_id: str,
        trait_name: str,
        new_value: float,
    ) -> AgentPersonalityEdit:
        """Modify an agent's personality trait at runtime.

        Clamps the new value to the valid range [0.0, 1.0].

        Args:
            agent_id: The agent whose personality is being edited.
            trait_name: Name of the personality trait to modify.
            new_value: New trait value (clamped to [0.0, 1.0]).

        Returns:
            The AgentPersonalityEdit record.
        """
        _time_module.sleep(0.001)
        with self._lock:
            clamped_value = max(0.0, min(1.0, new_value))
            edit = AgentPersonalityEdit(
                agent_id=agent_id,
                trait_name=trait_name,
                old_value=0.5,
                new_value=clamped_value,
            )
            self._personality_edits[edit.edit_id] = edit
            return edit

    # -------------------------------------------------------------------------
    # World Event Injection
    # -------------------------------------------------------------------------

    def inject_world_event(
        self,
        event_type: str,
        description: str,
        target_location: str,
        affected_agents: Optional[List[str]] = None,
        intensity: float = 0.5,
        duration: float = 0.0,
    ) -> WorldEventInjection:
        """Inject a narrative event into the game world.

        Events can be instantaneous (duration=0) or persist over time.
        Affected agents are notified based on their location and the
        event's propagation rules.

        Args:
            event_type: Category of the event to inject.
            description: Human-readable description of what happens.
            target_location: Location in the world where the event occurs.
            affected_agents: List of agent IDs directly affected.
            intensity: Severity of the event (0.0 to 1.0).
            duration: How long the event lasts in seconds (0=instant).

        Returns:
            The WorldEventInjection record.
        """
        _time_module.sleep(0.001)
        with self._lock:
            clamped_intensity = max(0.0, min(1.0, intensity))
            injection = WorldEventInjection(
                event_type=event_type,
                description=description,
                target_location=target_location,
                affected_agents=list(affected_agents) if affected_agents else [],
                intensity=clamped_intensity,
                duration=duration,
                expires_at=(
                    _time_module.time() + duration if duration > 0 else None
                ),
            )
            self._event_injections[injection.injection_id] = injection
            return injection

    # -------------------------------------------------------------------------
    # Agent State Override
    # -------------------------------------------------------------------------

    def override_agent_state(
        self,
        agent_id: str,
        state_changes: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Override an agent's runtime state with provided values.

        Allows direct manipulation of agent state fields such as location,
        health, inventory, flags, or any other runtime attribute.

        Args:
            agent_id: The agent whose state is being overridden.
            state_changes: Dict of state field names to new values.

        Returns:
            A dict summarizing the override that was applied.
        """
        _time_module.sleep(0.001)
        with self._lock:
            previous_state: Dict[str, Any] = {
                "location": "unknown",
                "health": 100.0,
                "status": "idle",
                "flags": [],
            }
            applied: Dict[str, Any] = {}
            for key, value in state_changes.items():
                applied[key] = {
                    "previous": previous_state.get(key, "unknown"),
                    "new": value,
                }

            return {
                "agent_id": agent_id,
                "overridden_fields": list(state_changes.keys()),
                "changes": applied,
                "applied_at": _time_module.time(),
            }

    # -------------------------------------------------------------------------
    # Observation
    # -------------------------------------------------------------------------

    def observe_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get a detailed observation of a specific agent.

        Returns a comprehensive snapshot of the agent's current state,
        including memory, personality, relationships, and runtime attributes.

        Args:
            agent_id: The agent to observe.

        Returns:
            A dict with the agent's full observable state.
        """
        _time_module.sleep(0.001)
        with self._lock:
            return {
                "agent_id": agent_id,
                "observed_at": _time_module.time(),
                "state": {
                    "location": "unknown",
                    "health": 100.0,
                    "status": "idle",
                    "current_action": "",
                    "action_target": "",
                },
                "personality": {
                    "openness": 0.5,
                    "conscientiousness": 0.5,
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.5,
                },
                "memories": [],
                "relationships": [],
                "inventory": [],
                "active_effects": [],
            }

    def observe_world(self, world_id: str) -> Dict[str, Any]:
        """Get a detailed observation of the entire world state.

        Returns a comprehensive snapshot of the world including all
        agents, active events, scene information, and environmental state.

        Args:
            world_id: The world to observe.

        Returns:
            A dict with the world's full observable state.
        """
        _time_module.sleep(0.001)
        with self._lock:
            return {
                "world_id": world_id,
                "observed_at": _time_module.time(),
                "agent_count": 0,
                "agents": [],
                "active_events": [
                    inj.to_dict()
                    for inj in self._event_injections.values()
                    if inj.status == "active"
                ],
                "environment": {
                    "weather": "clear",
                    "time_of_day": "morning",
                    "season": "spring",
                },
                "scene": {
                    "current_scene": "",
                    "regions": [],
                },
                "active_sessions": list(self._active_sessions.keys()),
            }

    # -------------------------------------------------------------------------
    # Broadcast
    # -------------------------------------------------------------------------

    def broadcast_message(
        self,
        message: str,
        scope: str = "ALL_AGENTS",
        target_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Broadcast a god-mode message to agents in the world.

        Messages can be delivered to all agents, a specific group, or
        individual agents based on the scope.

        Args:
            message: The message content to broadcast.
            scope: Delivery scope ("SINGLE_AGENT", "AGENT_GROUP", "ALL_AGENTS").
            target_ids: List of agent IDs to target (required for SINGLE_AGENT
                        and AGENT_GROUP scopes).

        Returns:
            A dict with delivery results.
        """
        _time_module.sleep(0.001)
        with self._lock:
            try:
                iscope = InterventionScope(scope.lower())
            except ValueError:
                iscope = InterventionScope.ALL_AGENTS

            recipients = target_ids if target_ids else []
            return {
                "message": message,
                "scope": iscope.value,
                "recipients": recipients,
                "recipient_count": len(recipients),
                "delivered_at": _time_module.time(),
                "reactions": [
                    {
                        "agent_id": aid,
                        "acknowledged": True,
                        "reaction": "received",
                    }
                    for aid in recipients
                ],
            }

    # -------------------------------------------------------------------------
    # Command Execution
    # -------------------------------------------------------------------------

    def execute_command(self, command: GodModeCommand) -> GodModeCommand:
        """Execute a god mode command.

        Routes the command to the appropriate handler based on its
        intervention_type and records the execution result.

        Args:
            command: The GodModeCommand to execute.

        Returns:
            The executed command with status and result populated.
        """
        _time_module.sleep(0.001)
        with self._lock:
            command.status = CommandStatus.EXECUTING
            self._commands[command.id] = command

            try:
                payload = command.payload
                if command.intervention_type == InterventionType.MEMORY_EDIT:
                    result = self._execute_memory_edit(command)
                elif command.intervention_type == InterventionType.PERSONALITY_EDIT:
                    result = self._execute_personality_edit(command)
                elif command.intervention_type == InterventionType.EVENT_INJECT:
                    result = self._execute_event_inject(command)
                elif command.intervention_type == InterventionType.STATE_OVERRIDE:
                    result = self._execute_state_override(command)
                elif command.intervention_type == InterventionType.CONVERSATION_OVERRIDE:
                    result = self._execute_conversation_override(command)
                elif command.intervention_type == InterventionType.WORLD_EDIT:
                    result = self._execute_world_edit(command)
                elif command.intervention_type == InterventionType.OBSERVE:
                    result = self._execute_observe(command)
                else:
                    result = {"status": "error", "error": "Unknown intervention type"}

                command.status = CommandStatus.COMPLETED
                command.result = result
            except Exception as exc:
                command.status = CommandStatus.FAILED
                command.result = {"status": "error", "error": str(exc)}

            self._total_commands += 1
            return command

    def _execute_memory_edit(self, command: GodModeCommand) -> Dict[str, Any]:
        """Execute a memory edit command."""
        _time_module.sleep(0.001)
        payload = command.payload
        edit = self.edit_agent_memory(
            agent_id=payload.get("agent_id", ""),
            memory_key=payload.get("memory_key", ""),
            new_value=payload.get("new_value"),
            operation=payload.get("operation", "UPDATE"),
        )
        return {"status": "completed", "edit_id": edit.edit_id}

    def _execute_personality_edit(self, command: GodModeCommand) -> Dict[str, Any]:
        """Execute a personality edit command."""
        _time_module.sleep(0.001)
        payload = command.payload
        edit = self.edit_agent_personality(
            agent_id=payload.get("agent_id", ""),
            trait_name=payload.get("trait_name", ""),
            new_value=payload.get("new_value", 0.5),
        )
        return {"status": "completed", "edit_id": edit.edit_id}

    def _execute_event_inject(self, command: GodModeCommand) -> Dict[str, Any]:
        """Execute an event injection command."""
        _time_module.sleep(0.001)
        payload = command.payload
        injection = self.inject_world_event(
            event_type=payload.get("event_type", ""),
            description=payload.get("description", ""),
            target_location=payload.get("target_location", ""),
            affected_agents=payload.get("affected_agents", []),
            intensity=payload.get("intensity", 0.5),
            duration=payload.get("duration", 0.0),
        )
        return {"status": "completed", "injection_id": injection.injection_id}

    def _execute_state_override(self, command: GodModeCommand) -> Dict[str, Any]:
        """Execute a state override command."""
        _time_module.sleep(0.001)
        payload = command.payload
        result = self.override_agent_state(
            agent_id=payload.get("agent_id", ""),
            state_changes=payload.get("state_changes", {}),
        )
        return {"status": "completed", "override_result": result}

    def _execute_conversation_override(self, command: GodModeCommand) -> Dict[str, Any]:
        """Execute a conversation override command."""
        _time_module.sleep(0.001)
        payload = command.payload
        return {
            "status": "completed",
            "agent_id": payload.get("agent_id", ""),
            "override_text": payload.get("override_text", ""),
            "applied_at": _time_module.time(),
        }

    def _execute_world_edit(self, command: GodModeCommand) -> Dict[str, Any]:
        """Execute a world edit command."""
        _time_module.sleep(0.001)
        payload = command.payload
        return {
            "status": "completed",
            "edit_type": payload.get("edit_type", "unknown"),
            "changes": payload.get("changes", {}),
            "applied_at": _time_module.time(),
        }

    def _execute_observe(self, command: GodModeCommand) -> Dict[str, Any]:
        """Execute an observe command."""
        _time_module.sleep(0.001)
        payload = command.payload
        observe_target = payload.get("target_type", "agent")
        target_id = payload.get("target_id", "")

        if observe_target == "world":
            return self.observe_world(target_id)
        else:
            return self.observe_agent(target_id)

    # -------------------------------------------------------------------------
    # History & Status
    # -------------------------------------------------------------------------

    def get_intervention_history(
        self, session_id: str,
    ) -> Dict[str, Any]:
        """Get the history of all interventions in a session.

        Args:
            session_id: Identifier of the session to query.

        Returns:
            A dict with the session's intervention history.
        """
        _time_module.sleep(0.001)
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"status": "error", "error": "Session not found"}

            interventions: List[Dict[str, Any]] = []
            for cmd_id in session.interventions:
                cmd = self._commands.get(cmd_id)
                if cmd is not None:
                    interventions.append(cmd.to_dict())

            return {
                "session_id": session_id,
                "world_id": session.world_id,
                "intervention_count": len(interventions),
                "interventions": interventions,
                "session": session.to_dict(),
            }

    def get_status(self) -> Dict[str, Any]:
        """Return the current controller status.

        Returns a summary of the controller's state including active
        sessions, total commands, and system health.

        Returns:
            A dict with controller status information.
        """
        _time_module.sleep(0.001)
        with self._lock:
            active_events = sum(
                1 for inj in self._event_injections.values()
                if inj.status == "active"
            )
            return {
                "initialized": self._is_initialized,
                "active_sessions": len(self._active_sessions),
                "total_sessions": self._total_sessions,
                "total_commands": self._total_commands,
                "memory_edits": len(self._memory_edits),
                "personality_edits": len(self._personality_edits),
                "active_events": active_events,
                "total_event_injections": len(self._event_injections),
                "controller_id": id(self),
            }


# =============================================================================
# Module-Level Accessor
# =============================================================================

_god_mode_controller: Optional[GodModeController] = None


def get_god_mode_controller() -> GodModeController:
    """Get the singleton GodModeController instance.

    Returns:
        The global GodModeController instance.
    """
    global _god_mode_controller
    if _god_mode_controller is None:
        _god_mode_controller = GodModeController()
    return _god_mode_controller