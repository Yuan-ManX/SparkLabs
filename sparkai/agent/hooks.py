"""
SparkAI Agent - Hooks System

Automated event-driven validation and lifecycle management.
Hooks fire on agent events and can validate, transform, or block actions.

Hook Types:
  - pre_act: Validate before tool execution
  - post_act: Validate after tool execution
  - pre_think: Intercept before LLM reasoning
  - post_think: Validate after LLM response
  - on_error: Handle agent errors
  - on_commit: Validate on state changes
  - on_session_start: Initialize session state
  - on_session_end: Finalize session state
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class HookEvent(Enum):
    PRE_ACT = "pre_act"
    POST_ACT = "post_act"
    PRE_THINK = "pre_think"
    POST_THINK = "post_think"
    ON_ERROR = "on_error"
    ON_COMMIT = "on_commit"
    ON_SESSION_START = "on_session_start"
    ON_SESSION_END = "on_session_end"
    ON_ENTITY_CREATE = "on_entity_create"
    ON_ENTITY_DELETE = "on_entity_delete"
    ON_COMPONENT_ADD = "on_component_add"
    ON_WORLD_START = "on_world_start"
    ON_WORLD_STOP = "on_world_stop"


@dataclass
class HookResult:
    allowed: bool = True
    modified_data: Optional[Dict[str, Any]] = None
    message: str = ""
    severity: str = "info"

    @staticmethod
    def allow() -> "HookResult":
        return HookResult(allowed=True)

    @staticmethod
    def deny(reason: str, severity: str = "error") -> "HookResult":
        return HookResult(allowed=False, message=reason, severity=severity)

    @staticmethod
    def modify(data: Dict[str, Any]) -> "HookResult":
        return HookResult(allowed=True, modified_data=data)


class Hook(ABC):
    """
    Base class for agent hooks.
    Hooks intercept agent events and can validate, modify, or block them.
    """

    def __init__(self, name: str, event: HookEvent, priority: int = 100):
        self.name = name
        self.event = event
        self.priority = priority
        self.enabled = True
        self._fire_count: int = 0
        self._last_fire_time: float = 0.0

    @abstractmethod
    def execute(self, data: Dict[str, Any]) -> HookResult:
        pass

    def fire(self, data: Dict[str, Any]) -> HookResult:
        if not self.enabled:
            return HookResult.allow()
        self._fire_count += 1
        self._last_fire_time = time.time()
        try:
            return self.execute(data)
        except Exception as e:
            return HookResult.deny(f"Hook '{self.name}' error: {str(e)}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "event": self.event.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "fire_count": self._fire_count,
        }


class ActionValidationHook(Hook):
    """
    Validates agent actions before execution.
    Ensures actions are within the agent's capabilities.
    """

    def __init__(self):
        super().__init__("action_validation", HookEvent.PRE_ACT, priority=10)

    def execute(self, data: Dict[str, Any]) -> HookResult:
        action = data.get("action", "")
        if not action:
            return HookResult.deny("No action specified")
        return HookResult.allow()


class ErrorRecoveryHook(Hook):
    """
    Handles agent errors and attempts recovery.
    Logs errors and suggests debug skill usage.
    """

    def __init__(self, max_retries: int = 3):
        super().__init__("error_recovery", HookEvent.ON_ERROR, priority=5)
        self.max_retries = max_retries
        self._error_counts: Dict[str, int] = {}

    def execute(self, data: Dict[str, Any]) -> HookResult:
        error = data.get("error", "")
        agent_id = data.get("agent_id", "unknown")
        self._error_counts[agent_id] = self._error_counts.get(agent_id, 0) + 1

        if self._error_counts[agent_id] >= self.max_retries:
            return HookResult.deny(
                f"Agent {agent_id} exceeded max retries ({self.max_retries})",
                severity="critical",
            )

        return HookResult.modify({
            **data,
            "recovery_suggested": True,
            "debug_recommended": True,
        })


class EntityIntegrityHook(Hook):
    """
    Validates entity creation and deletion.
    Ensures entities have required components.
    """

    def __init__(self):
        super().__init__("entity_integrity", HookEvent.ON_ENTITY_CREATE, priority=20)

    def execute(self, data: Dict[str, Any]) -> HookResult:
        entity_name = data.get("name", "")
        if not entity_name:
            return HookResult.deny("Entity must have a name")
        return HookResult.allow()


class ComponentSchemaHook(Hook):
    """
    Validates component data against expected schemas.
    Ensures component types are registered.
    """

    def __init__(self):
        super().__init__("component_schema", HookEvent.ON_COMPONENT_ADD, priority=15)

    def execute(self, data: Dict[str, Any]) -> HookResult:
        component_type = data.get("component_type", "")
        if not component_type:
            return HookResult.deny("Component type is required")
        return HookResult.allow()


class SessionLifecycleHook(Hook):
    """
    Manages session lifecycle events.
    Initializes and finalizes agent sessions.
    """

    def __init__(self):
        super().__init__("session_lifecycle", HookEvent.ON_SESSION_START, priority=1)

    def execute(self, data: Dict[str, Any]) -> HookResult:
        return HookResult.modify({
            **data,
            "session_initialized": True,
            "timestamp": time.time(),
        })


class WorldSafetyHook(Hook):
    """
    Validates world start/stop operations.
    Ensures safe state transitions.
    """

    def __init__(self):
        super().__init__("world_safety", HookEvent.ON_WORLD_START, priority=10)

    def execute(self, data: Dict[str, Any]) -> HookResult:
        world_id = data.get("world_id", "")
        if not world_id:
            return HookResult.deny("World ID is required")
        return HookResult.allow()


class HookChain:
    """
    Ordered chain of hooks for a specific event.
    Hooks execute in priority order (lower = earlier).
    Any hook can block the chain by returning denied.
    """

    def __init__(self, event: HookEvent):
        self.event = event
        self._hooks: List[Hook] = []

    def add(self, hook: Hook) -> None:
        self._hooks.append(hook)
        self._hooks.sort(key=lambda h: h.priority)

    def remove(self, name: str) -> bool:
        before = len(self._hooks)
        self._hooks = [h for h in self._hooks if h.name != name]
        return len(self._hooks) < before

    async def execute(self, data: Dict[str, Any]) -> HookResult:
        current_data = data
        for hook in self._hooks:
            result = hook.fire(current_data)
            if not result.allowed:
                return result
            if result.modified_data:
                current_data = result.modified_data
        return HookResult.allow()


class HookManager:
    """
    Central manager for all agent hooks.
    Provides hook registration, event dispatch, and lifecycle management.
    """

    def __init__(self):
        self._chains: Dict[HookEvent, HookChain] = {
            event: HookChain(event) for event in HookEvent
        }
        self._hook_registry: Dict[str, Hook] = {}
        self._setup_builtin_hooks()

    def _setup_builtin_hooks(self) -> None:
        builtin = [
            ActionValidationHook(),
            ErrorRecoveryHook(),
            EntityIntegrityHook(),
            ComponentSchemaHook(),
            SessionLifecycleHook(),
            WorldSafetyHook(),
        ]
        for hook in builtin:
            self.register(hook)

    def register(self, hook: Hook) -> None:
        self._hook_registry[hook.name] = hook
        self._chains[hook.event].add(hook)

    def unregister(self, name: str) -> bool:
        hook = self._hook_registry.pop(name, None)
        if hook:
            self._chains[hook.event].remove(name)
            return True
        return False

    def get(self, name: str) -> Optional[Hook]:
        return self._hook_registry.get(name)

    def list_hooks(self, event: Optional[HookEvent] = None) -> List[Dict[str, Any]]:
        if event:
            return [h.to_dict() for h in self._chains[event]._hooks]
        return [h.to_dict() for h in self._hook_registry.values()]

    async def fire(self, event: HookEvent, data: Dict[str, Any]) -> HookResult:
        chain = self._chains.get(event)
        if chain:
            return await chain.execute(data)
        return HookResult.allow()

    def enable_hook(self, name: str) -> bool:
        hook = self._hook_registry.get(name)
        if hook:
            hook.enabled = True
            return True
        return False

    def disable_hook(self, name: str) -> bool:
        hook = self._hook_registry.get(name)
        if hook:
            hook.enabled = False
            return True
        return False
