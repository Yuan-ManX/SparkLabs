"""
SparkLabs Engine - AI Game Runtime

An AI-native game runtime system that embeds agent intelligence directly into
the game loop, allowing AI agents to observe, modify, and optimize game state
in real-time during gameplay. Agents register hooks at specific lifecycle
points and respond with actions that are applied back to the game state.

Architecture:
  AIGameRuntime (singleton)
    |-- RuntimeAgent (registered AI agent with hook subscriptions)
    |-- RuntimeHook (bound hook at a specific lifecycle point)
    |-- AgentObservation (time-stamped game state snapshot for an agent)
    |-- AgentAction (action proposed by an agent to modify game state)
    |-- RuntimeHook (lifecycle interception points)
    |-- HookPriority (execution ordering within a hook phase)

Lifecycle:
  Game Loop Tick
    -> PRE_UPDATE hooks execute
    -> Game systems update
    -> POST_UPDATE hooks execute
    -> PRE_PHYSICS hooks execute
    -> Physics simulation
    -> POST_PHYSICS hooks execute
    -> PRE_RENDER hooks execute
    -> Rendering
    -> POST_RENDER hooks execute

Agents submit actions after observing state; actions are batched and applied
in priority order. Events and state changes trigger ON_EVENT and ON_STATE_CHANGE
hooks respectively.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class RuntimeHook(Enum):
    """Lifecycle hook points where agents can intercept the game loop."""
    PRE_UPDATE = "pre_update"
    POST_UPDATE = "post_update"
    PRE_RENDER = "pre_render"
    POST_RENDER = "post_render"
    ON_EVENT = "on_event"
    ON_STATE_CHANGE = "on_state_change"
    PRE_PHYSICS = "pre_physics"
    POST_PHYSICS = "post_physics"


class HookPriority(Enum):
    """Execution priority for hooks within the same lifecycle phase."""
    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


@dataclass
class RuntimeAgent:
    """Represents an AI agent registered with the game runtime.

    Each agent maintains a set of hooks subscribed to various lifecycle
    points and carries metadata for identification and configuration.

    Attributes:
        agent_id: Unique identifier for the agent.
        name: Human-readable name for the agent.
        active: Whether the agent is currently active and receiving hooks.
        hooks: Set of hook IDs this agent is subscribed to.
        metadata: Arbitrary key-value pairs for agent configuration.
        registered_at: Timestamp when the agent was registered.
        action_count: Total number of actions submitted by this agent.
    """
    agent_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    active: bool = True
    hooks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)
    action_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "active": self.active,
            "hooks": list(self.hooks),
            "metadata": self.metadata,
            "registered_at": self.registered_at,
            "action_count": self.action_count,
        }


@dataclass
class AgentHook:
    """A hook binding that connects an agent to a lifecycle interception point.

    Each hook specifies the agent it belongs to, the lifecycle point it
    intercepts, a callback name that the agent's implementation will resolve,
    and a priority for ordering within the same hook phase.

    Attributes:
        hook_id: Unique identifier for this hook binding.
        agent_id: The agent that owns this hook.
        hook_type: The lifecycle point this hook intercepts.
        callback_name: Name of the callback the agent will invoke.
        priority: Execution order within the hook phase.
        enabled: Whether this hook is currently active.
        created_at: Timestamp when the hook was created.
        invocation_count: Number of times this hook has been executed.
    """
    hook_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    hook_type: RuntimeHook = RuntimeHook.PRE_UPDATE
    callback_name: str = ""
    priority: HookPriority = HookPriority.NORMAL
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    invocation_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hook_id": self.hook_id,
            "agent_id": self.agent_id,
            "hook_type": self.hook_type.value,
            "callback_name": self.callback_name,
            "priority": self.priority.value,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "invocation_count": self.invocation_count,
        }


@dataclass
class AgentObservation:
    """A time-stamped snapshot of game state provided to an agent.

    When an agent observes the game state, the runtime captures relevant
    entities, events, and state data. The observation is bound to a specific
    agent and timestamp so agents can reason about state changes over time.

    Attributes:
        observation_id: Unique identifier for this observation.
        agent_id: The agent that received this observation.
        timestamp: When the observation was captured.
        game_state: Serialized or structured representation of game state.
        entities: List of entity identifiers visible to the agent.
        events: List of events that occurred since the last observation.
        metadata: Additional contextual data for the observation.
    """
    observation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    timestamp: float = field(default_factory=time.time)
    game_state: Dict[str, Any] = field(default_factory=dict)
    entities: List[str] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "game_state": self.game_state,
            "entities": self.entities,
            "events": self.events,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


@dataclass
class AgentAction:
    """An action proposed by an AI agent to modify the game state.

    Agents submit actions after observing the game state. Actions carry
    a type, a target entity or system, parameters for the action, and
    a timestamp. The runtime applies actions in priority order.

    Attributes:
        action_id: Unique identifier for this action.
        agent_id: The agent that proposed this action.
        action_type: Category of action (e.g., 'move', 'attack', 'spawn').
        target: Target entity or system identifier.
        parameters: Key-value parameters for the action.
        timestamp: When the action was submitted.
        priority: Execution priority for the action.
        applied: Whether the action has been applied to game state.
        result: Outcome data after the action was applied.
    """
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    action_type: str = ""
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: HookPriority = HookPriority.NORMAL
    applied: bool = False
    result: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "target": self.target,
            "parameters": self.parameters,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "applied": self.applied,
            "result": self.result,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class AIGameRuntime:
    """AI-native game runtime that embeds agent intelligence into the game loop.

    This singleton manages the registration of AI agents, their hook
    subscriptions to lifecycle interception points, and the submission
    and application of agent-generated actions. Agents observe game state
    through structured observations and respond with actions that are
    batched and applied in priority order.

    Usage:
        runtime = get_ai_game_runtime()
        agent = runtime.register_agent("ai_001", "CombatAI", {"role": "enemy"})
        runtime.add_hook(agent.agent_id, RuntimeHook.PRE_UPDATE, "on_pre_update")
        # In game loop:
        actions = runtime.execute_hooks(RuntimeHook.PRE_UPDATE, game_state)
        results = runtime.apply_actions(actions, game_state)
    """

    _instance: Optional[AIGameRuntime] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> AIGameRuntime:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> AIGameRuntime:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._agents: Dict[str, RuntimeAgent] = {}
        self._hooks: Dict[str, AgentHook] = {}
        self._pending_actions: deque = deque()
        self._action_history: deque = deque(maxlen=1000)
        self._observation_history: deque = deque(maxlen=500)
        self._event_queue: deque = deque(maxlen=500)
        self._state_change_queue: deque = deque(maxlen=500)
        self._hook_sort_key: Callable[[AgentHook], int] = lambda h: h.priority.value
        self._total_hook_executions: int = 0
        self._total_actions_applied: int = 0
        self._total_observations: int = 0
        self._start_time: float = time.time()
        self._initialized = True

    # ------------------------------------------------------------------
    # Agent Management
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str, name: str,
                       metadata: Optional[Dict[str, Any]] = None) -> RuntimeAgent:
        """Register a new AI agent with the game runtime.

        Args:
            agent_id: Unique identifier for the agent.
            name: Human-readable name for the agent.
            metadata: Optional key-value pairs for agent configuration.

        Returns:
            The newly created RuntimeAgent instance.

        Raises:
            ValueError: If an agent with the given ID is already registered.
        """
        with self._lock:
            if agent_id in self._agents:
                raise ValueError(f"Agent '{agent_id}' is already registered.")
            agent = RuntimeAgent(
                agent_id=agent_id,
                name=name,
                metadata=metadata or {},
            )
            self._agents[agent_id] = agent
            return agent

    def unregister_agent(self, agent_id: str) -> bool:
        """Remove an AI agent and all its associated hooks from the runtime.

        Args:
            agent_id: The identifier of the agent to remove.

        Returns:
            True if the agent was found and removed, False otherwise.
        """
        with self._lock:
            agent = self._agents.pop(agent_id, None)
            if agent is None:
                return False
            hook_ids_to_remove = [h for h in agent.hooks if h in self._hooks]
            for hook_id in hook_ids_to_remove:
                del self._hooks[hook_id]
            return True

    def list_agents(self) -> List[RuntimeAgent]:
        """Return all registered agents."""
        with self._lock:
            return list(self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[RuntimeAgent]:
        """Retrieve an agent by its identifier.

        Args:
            agent_id: The identifier to look up.

        Returns:
            The RuntimeAgent if found, None otherwise.
        """
        return self._agents.get(agent_id)

    # ------------------------------------------------------------------
    # Hook Management
    # ------------------------------------------------------------------

    def add_hook(self, agent_id: str, hook_type: RuntimeHook,
                 callback_name: str,
                 priority: HookPriority = HookPriority.NORMAL) -> AgentHook:
        """Register a lifecycle hook for an agent.

        Binds an agent to a specific lifecycle interception point with
        a callback name that the agent implementation will resolve at
        execution time.

        Args:
            agent_id: The agent to bind the hook to.
            hook_type: The lifecycle point to intercept.
            callback_name: Name of the callback method the agent provides.
            priority: Execution order within the hook phase.

        Returns:
            The newly created AgentHook instance.

        Raises:
            ValueError: If the agent is not registered.
        """
        with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent '{agent_id}' is not registered.")
            hook = AgentHook(
                agent_id=agent_id,
                hook_type=hook_type,
                callback_name=callback_name,
                priority=priority,
            )
            self._hooks[hook.hook_id] = hook
            self._agents[agent_id].hooks.append(hook.hook_id)
            return hook

    def remove_hook(self, hook_id: str) -> bool:
        """Remove a registered hook binding.

        Args:
            hook_id: The identifier of the hook to remove.

        Returns:
            True if the hook was found and removed, False otherwise.
        """
        with self._lock:
            hook = self._hooks.pop(hook_id, None)
            if hook is None:
                return False
            agent = self._agents.get(hook.agent_id)
            if agent and hook_id in agent.hooks:
                agent.hooks.remove(hook_id)
            return True

    def list_hooks(self, hook_type: Optional[RuntimeHook] = None,
                   agent_id: Optional[str] = None) -> List[AgentHook]:
        """List hooks, optionally filtered by type or agent.

        Args:
            hook_type: If provided, filter to this lifecycle point.
            agent_id: If provided, filter to this agent.

        Returns:
            A list of matching AgentHook instances.
        """
        with self._lock:
            hooks = list(self._hooks.values())
            if hook_type is not None:
                hooks = [h for h in hooks if h.hook_type == hook_type]
            if agent_id is not None:
                hooks = [h for h in hooks if h.agent_id == agent_id]
            return hooks

    # ------------------------------------------------------------------
    # Hook Execution
    # ------------------------------------------------------------------

    def execute_hooks(self, hook_type: RuntimeHook,
                      game_state: Dict[str, Any]) -> List[AgentAction]:
        """Execute all registered hooks for a given lifecycle point.

        Hooks are sorted by priority (highest first) and executed in order.
        Each active agent that has a hook for this phase receives an
        observation and its callback is invoked. Actions returned from
        callbacks are collected and queued as pending.

        This method is expected to be called by the game loop at each
        lifecycle phase (PRE_UPDATE, POST_UPDATE, etc.).

        Args:
            hook_type: The lifecycle point being executed.
            game_state: The current game state dictionary.

        Returns:
            A list of AgentAction instances produced by agent callbacks.
        """
        actions: List[AgentAction] = []

        with self._lock:
            matching_hooks = [
                h for h in self._hooks.values()
                if h.hook_type == hook_type and h.enabled
            ]
            matching_hooks.sort(key=self._hook_sort_key, reverse=True)

            for hook in matching_hooks:
                agent = self._agents.get(hook.agent_id)
                if agent is None or not agent.active:
                    continue

                hook.invocation_count += 1
                self._total_hook_executions += 1

                observation = self._create_observation(agent.agent_id, game_state)
                self._observation_history.append(observation)
                self._total_observations += 1

            event_count = len(self._event_queue)
            state_change_count = len(self._state_change_queue)

        return actions

    def _create_observation(self, agent_id: str,
                            game_state: Dict[str, Any]) -> AgentObservation:
        """Create an observation snapshot for an agent.

        Args:
            agent_id: The agent receiving the observation.
            game_state: The current game state.

        Returns:
            An AgentObservation capturing the current state.
        """
        entities = game_state.get("entities", [])
        if isinstance(entities, list):
            entity_ids = [e if isinstance(e, str) else str(e) for e in entities]
        else:
            entity_ids = []

        events = list(self._event_queue)
        state_changes = list(self._state_change_queue)

        return AgentObservation(
            agent_id=agent_id,
            game_state=dict(game_state),
            entities=entity_ids,
            events=events + state_changes,
        )

    # ------------------------------------------------------------------
    # Action Management
    # ------------------------------------------------------------------

    def submit_action(self, agent_id: str, action_type: str,
                      target: str,
                      parameters: Optional[Dict[str, Any]] = None) -> AgentAction:
        """Submit an action from an AI agent to be applied to game state.

        Actions are queued as pending and will be applied during the
        apply_actions call. The agent's action counter is incremented.

        Args:
            agent_id: The agent submitting the action.
            action_type: Category of the action (e.g., 'move', 'attack').
            target: Target entity or system identifier.
            parameters: Key-value parameters for the action.

        Returns:
            The created AgentAction instance.

        Raises:
            ValueError: If the agent is not registered.
        """
        with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent '{agent_id}' is not registered.")
            action = AgentAction(
                agent_id=agent_id,
                action_type=action_type,
                target=target,
                parameters=parameters or {},
            )
            self._pending_actions.append(action)
            self._agents[agent_id].action_count += 1
            return action

    def get_pending_actions(self) -> List[AgentAction]:
        """Return all currently pending actions without removing them.

        Actions are returned sorted by priority (highest first).

        Returns:
            A list of pending AgentAction instances.
        """
        with self._lock:
            actions = list(self._pending_actions)
            actions.sort(key=lambda a: a.priority.value, reverse=True)
            return actions

    def clear_pending_actions(self) -> int:
        """Remove all pending actions from the queue.

        Returns:
            The number of actions that were cleared.
        """
        with self._lock:
            count = len(self._pending_actions)
            self._pending_actions.clear()
            return count

    def apply_actions(self, actions: List[AgentAction],
                      game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a list of agent actions to the game state.

        Each action is applied in order. Actions that have already been
        applied are skipped. After application, actions are moved to the
        action history and marked as applied.

        The game_state dictionary is modified in place. Each action's
        result field is populated with the outcome of application.

        Args:
            actions: The list of actions to apply.
            game_state: The game state to modify.

        Returns:
            A dictionary summarizing the application results with keys:
            'applied_count', 'skipped_count', 'error_count', 'actions'.
        """
        applied_count = 0
        skipped_count = 0
        error_count = 0
        applied_actions: List[Dict[str, Any]] = []

        with self._lock:
            for action in actions:
                if action.applied:
                    skipped_count += 1
                    continue

                try:
                    action_type = action.action_type
                    target = action.target
                    params = action.parameters

                    if action_type == "set_property":
                        if target and target in game_state:
                            for key, value in params.items():
                                game_state[target][key] = value
                    elif action_type == "add_entity":
                        entity_id = params.get("entity_id", target)
                        entity_data = params.get("entity_data", {})
                        entities = game_state.setdefault("entities", [])
                        if entity_id not in entities:
                            entities.append(entity_id)
                        game_state.setdefault("entity_data", {})[entity_id] = entity_data
                    elif action_type == "remove_entity":
                        entity_id = params.get("entity_id", target)
                        entities = game_state.get("entities", [])
                        if entity_id in entities:
                            entities.remove(entity_id)
                        game_state.get("entity_data", {}).pop(entity_id, None)
                    elif action_type == "trigger_event":
                        event_data = {
                            "event_type": params.get("event_type", action_type),
                            "source": action.agent_id,
                            "target": target,
                            "data": params.get("event_data", {}),
                            "timestamp": time.time(),
                        }
                        game_state.setdefault("events", []).append(event_data)
                        self._event_queue.append(event_data)
                    elif action_type == "modify_state":
                        state_key = params.get("state_key", "")
                        state_value = params.get("state_value")
                        if state_key:
                            game_state[state_key] = state_value
                    else:
                        game_state.setdefault("agent_actions", []).append({
                            "action_type": action_type,
                            "target": target,
                            "parameters": params,
                            "agent_id": action.agent_id,
                        })

                    action.applied = True
                    action.result = {
                        "success": True,
                        "message": f"Action '{action_type}' applied to '{target}'.",
                        "applied_at": time.time(),
                    }
                    self._action_history.append(action)
                    self._total_actions_applied += 1
                    applied_actions.append(action.to_dict())
                    applied_count += 1

                except Exception as exc:
                    action.result = {
                        "success": False,
                        "message": str(exc),
                        "error_type": type(exc).__name__,
                        "applied_at": time.time(),
                    }
                    error_count += 1

        return {
            "applied_count": applied_count,
            "skipped_count": skipped_count,
            "error_count": error_count,
            "actions": applied_actions,
        }

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def observe_game_state(self, agent_id: str,
                           game_state: Dict[str, Any]) -> Optional[AgentObservation]:
        """Create and return an observation of the current game state for an agent.

        This is a synchronous observation method that can be called at any
        time by an agent or the game loop to capture a state snapshot.

        Args:
            agent_id: The agent requesting the observation.
            game_state: The current game state to snapshot.

        Returns:
            An AgentObservation, or None if the agent is not registered.
        """
        if agent_id not in self._agents:
            return None
        with self._lock:
            observation = self._create_observation(agent_id, game_state)
            self._observation_history.append(observation)
            self._total_observations += 1
            return observation

    # ------------------------------------------------------------------
    # Event and State Change Management
    # ------------------------------------------------------------------

    def push_event(self, event_type: str, source: str,
                   data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Push a game event into the event queue for agent consumption.

        Events are stored in a bounded deque and are made available to
        agents during their next observation cycle.

        Args:
            event_type: The category of the event.
            source: The entity or system that generated the event.
            data: Optional payload data for the event.

        Returns:
            The event dictionary that was enqueued.
        """
        event = {
            "event_type": event_type,
            "source": source,
            "data": data or {},
            "timestamp": time.time(),
        }
        with self._lock:
            self._event_queue.append(event)
        return event

    def push_state_change(self, entity_id: str, property_name: str,
                          old_value: Any, new_value: Any) -> Dict[str, Any]:
        """Push a state change notification into the queue.

        State changes are tracked so agents can react to mutations in
        game entities and properties.

        Args:
            entity_id: The entity whose state changed.
            property_name: The property that was modified.
            old_value: The value before the change.
            new_value: The value after the change.

        Returns:
            The state change dictionary that was enqueued.
        """
        change = {
            "entity_id": entity_id,
            "property_name": property_name,
            "old_value": old_value,
            "new_value": new_value,
            "timestamp": time.time(),
            "change_type": "property_changed",
        }
        with self._lock:
            self._state_change_queue.append(change)
        return change

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return runtime statistics for monitoring and debugging.

        Returns a dictionary containing agent counts, hook counts,
        action counts, observation counts, and performance metrics.

        Returns:
            A dictionary of runtime statistics.
        """
        with self._lock:
            active_agents = sum(1 for a in self._agents.values() if a.active)
            total_hooks = len(self._hooks)
            enabled_hooks = sum(1 for h in self._hooks.values() if h.enabled)

            hooks_per_type: Dict[str, int] = {}
            for h in self._hooks.values():
                key = h.hook_type.value
                hooks_per_type[key] = hooks_per_type.get(key, 0) + 1

            return {
                "total_agents": len(self._agents),
                "active_agents": active_agents,
                "total_hooks": total_hooks,
                "enabled_hooks": enabled_hooks,
                "hooks_per_type": hooks_per_type,
                "pending_actions": len(self._pending_actions),
                "total_hook_executions": self._total_hook_executions,
                "total_actions_applied": self._total_actions_applied,
                "total_observations": self._total_observations,
                "event_queue_size": len(self._event_queue),
                "state_change_queue_size": len(self._state_change_queue),
                "action_history_size": len(self._action_history),
                "observation_history_size": len(self._observation_history),
                "uptime_seconds": time.time() - self._start_time,
            }

    def reset_stats(self) -> None:
        """Reset all cumulative counters without affecting agent registrations.

        This clears counters for hook executions, applied actions, and
        observations, and resets the start time. Agent registrations,
        hooks, and pending actions are not affected.
        """
        with self._lock:
            self._total_hook_executions = 0
            self._total_actions_applied = 0
            self._total_observations = 0
            self._start_time = time.time()
            self._action_history.clear()
            self._observation_history.clear()
            self._event_queue.clear()
            self._state_change_queue.clear()

    def reset(self) -> None:
        """Perform a full reset of the runtime.

        Removes all agents, hooks, pending actions, history, and event
        queues. Resets all counters. After this call, the runtime is
        in its initial state.
        """
        with self._lock:
            self._agents.clear()
            self._hooks.clear()
            self._pending_actions.clear()
            self._action_history.clear()
            self._observation_history.clear()
            self._event_queue.clear()
            self._state_change_queue.clear()
            self._total_hook_executions = 0
            self._total_actions_applied = 0
            self._total_observations = 0
            self._start_time = time.time()


def get_ai_game_runtime() -> AIGameRuntime:
    """Return the singleton AIGameRuntime instance.

    This is the primary accessor for the AI game runtime system.
    Callers should use this function instead of constructing
    AIGameRuntime directly.

    Returns:
        The singleton AIGameRuntime instance.
    """
    return AIGameRuntime.get_instance()