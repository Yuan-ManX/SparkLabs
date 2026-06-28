"""
SparkLabs Agent - Action Space Definition Engine

Comprehensive action space system that defines, validates, and executes
the full spectrum of actions available to AI agents within the SparkLabs
game engine. Provides structured action definitions with preconditions,
effects, costs, and execution contexts for both game development and
runtime game simulation.

Architecture:
  ActionSpaceEngine (Singleton)
    |-- ActionDefinition (typed action with preconditions and effects)
    |-- ActionDomain (categorized group of related actions)
    |-- ActionExecutor (validates and executes actions with rollback)
    |-- ActionPlanner (generates action sequences from goals)
    |-- ActionValidator (enforces preconditions and constraints)

Action Categories:
  - ENGINE: render, physics, audio, input, scene management
  - GAME_LOGIC: entity creation, state changes, event triggers
  - AI_AGENT: navigation, decision, perception, communication
  - DEVELOPMENT: code generation, asset creation, testing, deployment
  - WORLD: terrain, weather, time, ecosystem manipulation
  - SOCIAL: dialogue, relationship, trade, faction operations

Usage:
    ae = get_action_space()
    ae.initialize()

    # Register a custom action
    ae.register_action(ActionDefinition(
        name="spawn_entity",
        category=ActionCategory.GAME_LOGIC,
        parameters={"entity_type": "str", "position": "tuple"},
        preconditions=["scene_loaded", "entity_type_valid"],
        effects=["entity_count_increased"],
    ))

    # Execute an action
    result = ae.execute("spawn_entity", {
        "entity_type": "NPC",
        "position": (100, 200),
    })

    # Plan a sequence of actions
    plan = ae.plan_actions(goal="create_platformer_level", max_steps=10)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class ActionCategory(Enum):
    """Categories of actions available to agents."""
    ENGINE = "engine"              # Engine-level operations
    GAME_LOGIC = "game_logic"      # Game logic and state changes
    AI_AGENT = "ai_agent"          # AI agent behaviors
    DEVELOPMENT = "development"    # Development and tooling
    WORLD = "world"                # World and environment
    SOCIAL = "social"              # Social interactions
    UI = "ui"                      # User interface actions
    NETWORK = "network"            # Network operations
    CUSTOM = "custom"              # User-defined actions


class ActionPriority(Enum):
    """Priority levels for action execution."""
    CRITICAL = 0     # Must execute immediately
    HIGH = 1         # High priority
    NORMAL = 2       # Standard priority
    LOW = 3          # Low priority, can be deferred
    BACKGROUND = 4   # Background tasks


class ActionExecutionStatus(Enum):
    """Status of an action execution attempt."""
    PENDING = "pending"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class ActionEffectType(Enum):
    """Types of effects an action can produce."""
    STATE_CHANGE = "state_change"        # Modifies entity/world state
    EVENT_EMISSION = "event_emission"    # Triggers an event
    RESOURCE_CONSUMPTION = "resource"    # Consumes resources
    SPAWN = "spawn"                      # Creates new entities
    DESTROY = "destroy"                  # Removes entities
    MODIFY = "modify"                    # Modifies existing entities
    TRIGGER = "trigger"                  # Triggers a chain reaction
    NOTIFICATION = "notification"        # Sends notification


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ActionParameter:
    """Definition of a parameter for an action."""
    name: str
    param_type: str = "any"
    required: bool = True
    default: Any = None
    description: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    validation: Optional[Callable[[Any], bool]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.param_type,
            "required": self.required,
            "default": self.default,
            "description": self.description,
            "constraints": self.constraints,
        }


@dataclass
class ActionPrecondition:
    """A precondition that must be satisfied before an action can execute."""
    condition_id: str
    description: str = ""
    evaluator: Optional[Callable[[Dict[str, Any]], bool]] = None
    is_satisfied: bool = False
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "description": self.description,
            "is_satisfied": self.is_satisfied,
            "error_message": self.error_message,
        }


@dataclass
class ActionEffect:
    """An effect produced by executing an action."""
    effect_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    effect_type: ActionEffectType = ActionEffectType.STATE_CHANGE
    target: str = ""
    description: str = ""
    magnitude: float = 1.0
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "effect_type": self.effect_type.value,
            "target": self.target,
            "description": self.description,
            "magnitude": self.magnitude,
            "duration": self.duration,
            "metadata": self.metadata,
        }


@dataclass
class ActionDefinition:
    """Complete definition of an executable action."""
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    category: ActionCategory = ActionCategory.CUSTOM
    description: str = ""
    parameters: List[ActionParameter] = field(default_factory=list)
    preconditions: List[ActionPrecondition] = field(default_factory=list)
    effects: List[ActionEffect] = field(default_factory=list)
    cost: float = 1.0
    priority: ActionPriority = ActionPriority.NORMAL
    cooldown_ms: float = 0.0
    max_retries: int = 3
    is_reversible: bool = True
    tags: List[str] = field(default_factory=list)
    executor: Optional[Callable[..., Dict[str, Any]]] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "preconditions": [p.to_dict() for p in self.preconditions],
            "effects": [e.to_dict() for e in self.effects],
            "cost": self.cost,
            "priority": self.priority.value,
            "cooldown_ms": self.cooldown_ms,
            "max_retries": self.max_retries,
            "is_reversible": self.is_reversible,
            "tags": self.tags,
        }


@dataclass
class ActionExecution:
    """Record of an action execution attempt."""
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action_id: str = ""
    action_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ActionExecutionStatus = ActionExecutionStatus.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    effects_applied: List[str] = field(default_factory=list)
    snapshot_before: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "action_id": self.action_id,
            "action_name": self.action_name,
            "parameters": self.parameters,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "effects_applied": self.effects_applied,
        }


@dataclass
class ActionPlan:
    """A sequence of actions to achieve a goal."""
    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str = ""
    actions: List[ActionDefinition] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_duration_ms: float = 0.0
    created_at: float = field(default_factory=time.time)
    status: str = "draft"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "action_count": len(self.actions),
            "actions": [a.name for a in self.actions],
            "estimated_cost": self.estimated_cost,
            "estimated_duration_ms": self.estimated_duration_ms,
            "status": self.status,
        }


@dataclass
class ActionDomain:
    """A domain grouping related actions together."""
    domain_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    category: ActionCategory = ActionCategory.CUSTOM
    description: str = ""
    actions: Dict[str, ActionDefinition] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "action_count": len(self.actions),
            "action_names": list(self.actions.keys()),
            "dependencies": self.dependencies,
        }


# =============================================================================
# ActionSpaceEngine (Singleton)
# =============================================================================


class ActionSpaceEngine:
    """Comprehensive action space definition and execution engine.

    Manages the complete lifecycle of agent actions: definition, validation,
    execution, and rollback. Provides action planning from high-level goals
    and tracks all action execution history for learning and optimization.

    Usage:
        ae = ActionSpaceEngine.get_instance()
        ae.initialize()

        ae.register_action(ActionDefinition(
            name="move_to",
            category=ActionCategory.AI_AGENT,
            parameters=[ActionParameter(name="target", param_type="position")],
        ))

        result = ae.execute("move_to", {"target": (100, 200)})
    """

    _instance: Optional["ActionSpaceEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if ActionSpaceEngine._instance is not None:
            raise RuntimeError("Use ActionSpaceEngine.get_instance()")
        self._initialized: bool = False
        self._lock = threading.RLock()
        self._actions: Dict[str, ActionDefinition] = {}
        self._domains: Dict[str, ActionDomain] = {}
        self._execution_history: List[ActionExecution] = []
        self._active_executions: Dict[str, ActionExecution] = {}
        self._plans: Dict[str, ActionPlan] = {}
        self._cooldowns: Dict[str, float] = {}
        self._total_executions: int = 0
        self._total_failures: int = 0
        self._custom_validators: Dict[str, Callable] = {}
        self._state_snapshots: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "ActionSpaceEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            if self._initialized:
                return {"status": "already_initialized", "success": True}

            self._register_default_actions()
            self._register_default_domains()
            self._initialized = True

            return {
                "status": "initialized",
                "success": True,
                "actions_registered": len(self._actions),
                "domains_created": len(self._domains),
            }

    def shutdown(self) -> Dict[str, Any]:
        with self._lock:
            self._initialized = False
            # Rollback any active executions
            for exec_id in list(self._active_executions.keys()):
                self._rollback_execution(exec_id)
            return {
                "success": True,
                "total_executions": self._total_executions,
                "total_failures": self._total_failures,
            }

    def _register_default_actions(self) -> None:
        """Register the built-in action definitions."""
        defaults = [
            # Engine actions
            ActionDefinition(
                name="engine_set_scene",
                category=ActionCategory.ENGINE,
                description="Switch to a different scene",
                parameters=[
                    ActionParameter(name="scene_name", param_type="str", required=True),
                    ActionParameter(name="transition", param_type="str", default="fade"),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.STATE_CHANGE, target="scene")],
            ),
            ActionDefinition(
                name="engine_set_camera",
                category=ActionCategory.ENGINE,
                description="Configure camera position and properties",
                parameters=[
                    ActionParameter(name="position", param_type="tuple", required=True),
                    ActionParameter(name="zoom", param_type="float", default=1.0),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.STATE_CHANGE, target="camera")],
            ),
            ActionDefinition(
                name="engine_play_audio",
                category=ActionCategory.ENGINE,
                description="Play an audio clip",
                parameters=[
                    ActionParameter(name="clip_id", param_type="str", required=True),
                    ActionParameter(name="volume", param_type="float", default=1.0),
                    ActionParameter(name="loop", param_type="bool", default=False),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.EVENT_EMISSION, target="audio")],
            ),
            # Game Logic actions
            ActionDefinition(
                name="spawn_entity",
                category=ActionCategory.GAME_LOGIC,
                description="Create a new game entity",
                parameters=[
                    ActionParameter(name="entity_type", param_type="str", required=True),
                    ActionParameter(name="position", param_type="tuple", required=True),
                    ActionParameter(name="properties", param_type="dict", default={}),
                ],
                preconditions=[
                    ActionPrecondition(condition_id="entity_type_valid", description="Entity type must be registered"),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.SPAWN, target="entity")],
            ),
            ActionDefinition(
                name="destroy_entity",
                category=ActionCategory.GAME_LOGIC,
                description="Remove a game entity",
                parameters=[
                    ActionParameter(name="entity_id", param_type="str", required=True),
                ],
                preconditions=[
                    ActionPrecondition(condition_id="entity_exists", description="Entity must exist"),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.DESTROY, target="entity")],
            ),
            ActionDefinition(
                name="modify_entity",
                category=ActionCategory.GAME_LOGIC,
                description="Modify entity properties",
                parameters=[
                    ActionParameter(name="entity_id", param_type="str", required=True),
                    ActionParameter(name="properties", param_type="dict", required=True),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.MODIFY, target="entity")],
            ),
            ActionDefinition(
                name="trigger_event",
                category=ActionCategory.GAME_LOGIC,
                description="Trigger a named game event",
                parameters=[
                    ActionParameter(name="event_name", param_type="str", required=True),
                    ActionParameter(name="event_data", param_type="dict", default={}),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.TRIGGER, target="event")],
            ),
            # AI Agent actions
            ActionDefinition(
                name="agent_move_to",
                category=ActionCategory.AI_AGENT,
                description="Move an AI agent to a target position",
                parameters=[
                    ActionParameter(name="agent_id", param_type="str", required=True),
                    ActionParameter(name="target", param_type="tuple", required=True),
                    ActionParameter(name="speed", param_type="float", default=1.0),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.STATE_CHANGE, target="agent_position")],
                cost=1.0,
            ),
            ActionDefinition(
                name="agent_perceive",
                category=ActionCategory.AI_AGENT,
                description="Agent perceives the world state",
                parameters=[
                    ActionParameter(name="agent_id", param_type="str", required=True),
                    ActionParameter(name="channels", param_type="list", default=["visual"]),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.STATE_CHANGE, target="agent_knowledge")],
                cost=0.5,
            ),
            ActionDefinition(
                name="agent_decide",
                category=ActionCategory.AI_AGENT,
                description="Agent makes a decision based on current state",
                parameters=[
                    ActionParameter(name="agent_id", param_type="str", required=True),
                    ActionParameter(name="context", param_type="dict", default={}),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.STATE_CHANGE, target="agent_intent")],
                cost=2.0,
            ),
            ActionDefinition(
                name="agent_communicate",
                category=ActionCategory.AI_AGENT,
                description="Agent sends a message to another agent",
                parameters=[
                    ActionParameter(name="sender_id", param_type="str", required=True),
                    ActionParameter(name="receiver_id", param_type="str", required=True),
                    ActionParameter(name="message", param_type="str", required=True),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.EVENT_EMISSION, target="communication")],
                cost=1.0,
            ),
            ActionDefinition(
                name="agent_learn",
                category=ActionCategory.AI_AGENT,
                description="Agent learns from experience",
                parameters=[
                    ActionParameter(name="agent_id", param_type="str", required=True),
                    ActionParameter(name="experience", param_type="dict", required=True),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.MODIFY, target="agent_memory")],
                cost=3.0,
            ),
            # Development actions
            ActionDefinition(
                name="dev_generate_code",
                category=ActionCategory.DEVELOPMENT,
                description="Generate game code from specification",
                parameters=[
                    ActionParameter(name="spec", param_type="str", required=True),
                    ActionParameter(name="language", param_type="str", default="python"),
                    ActionParameter(name="target_file", param_type="str", default=""),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.SPAWN, target="code")],
                cost=5.0,
            ),
            ActionDefinition(
                name="dev_create_asset",
                category=ActionCategory.DEVELOPMENT,
                description="Create a game asset",
                parameters=[
                    ActionParameter(name="asset_type", param_type="str", required=True),
                    ActionParameter(name="spec", param_type="dict", required=True),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.SPAWN, target="asset")],
                cost=4.0,
            ),
            ActionDefinition(
                name="dev_run_test",
                category=ActionCategory.DEVELOPMENT,
                description="Run automated tests",
                parameters=[
                    ActionParameter(name="test_suite", param_type="str", default="all"),
                    ActionParameter(name="target", param_type="str", default=""),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.EVENT_EMISSION, target="test_results")],
                cost=3.0,
            ),
            # World actions
            ActionDefinition(
                name="world_set_weather",
                category=ActionCategory.WORLD,
                description="Change world weather conditions",
                parameters=[
                    ActionParameter(name="weather_type", param_type="str", required=True),
                    ActionParameter(name="intensity", param_type="float", default=0.5),
                    ActionParameter(name="duration", param_type="float", default=60.0),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.STATE_CHANGE, target="weather")],
            ),
            ActionDefinition(
                name="world_set_time",
                category=ActionCategory.WORLD,
                description="Set world time of day",
                parameters=[
                    ActionParameter(name="hour", param_type="int", required=True),
                    ActionParameter(name="transition_speed", param_type="float", default=1.0),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.STATE_CHANGE, target="time")],
            ),
            ActionDefinition(
                name="world_spawn_resource",
                category=ActionCategory.WORLD,
                description="Spawn a resource node in the world",
                parameters=[
                    ActionParameter(name="resource_type", param_type="str", required=True),
                    ActionParameter(name="position", param_type="tuple", required=True),
                    ActionParameter(name="amount", param_type="float", default=100.0),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.SPAWN, target="resource")],
            ),
            # Social actions
            ActionDefinition(
                name="social_start_dialogue",
                category=ActionCategory.SOCIAL,
                description="Start a dialogue between entities",
                parameters=[
                    ActionParameter(name="initiator_id", param_type="str", required=True),
                    ActionParameter(name="target_id", param_type="str", required=True),
                    ActionParameter(name="dialogue_tree", param_type="str", default=""),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.TRIGGER, target="dialogue")],
            ),
            ActionDefinition(
                name="social_update_relationship",
                category=ActionCategory.SOCIAL,
                description="Update relationship between two entities",
                parameters=[
                    ActionParameter(name="entity_a", param_type="str", required=True),
                    ActionParameter(name="entity_b", param_type="str", required=True),
                    ActionParameter(name="change", param_type="float", required=True),
                ],
                effects=[ActionEffect(effect_type=ActionEffectType.MODIFY, target="relationship")],
            ),
        ]

        for action in defaults:
            self._actions[action.name] = action

    def _register_default_domains(self) -> None:
        """Register the built-in action domains."""
        domain_defs = [
            ("engine_core", ActionCategory.ENGINE, "Core engine operations",
             ["engine_set_scene", "engine_set_camera", "engine_play_audio"]),
            ("game_entities", ActionCategory.GAME_LOGIC, "Entity lifecycle management",
             ["spawn_entity", "destroy_entity", "modify_entity", "trigger_event"]),
            ("ai_behaviors", ActionCategory.AI_AGENT, "AI agent behaviors",
             ["agent_move_to", "agent_perceive", "agent_decide", "agent_communicate", "agent_learn"]),
            ("dev_tools", ActionCategory.DEVELOPMENT, "Development and tooling",
             ["dev_generate_code", "dev_create_asset", "dev_run_test"]),
            ("world_ops", ActionCategory.WORLD, "World manipulation",
             ["world_set_weather", "world_set_time", "world_spawn_resource"]),
            ("social_ops", ActionCategory.SOCIAL, "Social interactions",
             ["social_start_dialogue", "social_update_relationship"]),
        ]

        for name, category, desc, action_names in domain_defs:
            domain = ActionDomain(name=name, category=category, description=desc)
            for aname in action_names:
                if aname in self._actions:
                    domain.actions[aname] = self._actions[aname]
            self._domains[name] = domain

    # -------------------------------------------------------------------------
    # Action Registration
    # -------------------------------------------------------------------------

    def register_action(self, action: ActionDefinition) -> Dict[str, Any]:
        """Register a new action definition."""
        with self._lock:
            if action.name in self._actions:
                return {"success": False, "error": f"Action '{action.name}' already exists"}
            self._actions[action.name] = action
            return {"success": True, "action_id": action.action_id, "name": action.name}

    def unregister_action(self, name: str) -> Dict[str, Any]:
        """Remove an action definition."""
        with self._lock:
            if name not in self._actions:
                return {"success": False, "error": f"Action '{name}' not found"}
            del self._actions[name]
            return {"success": True, "name": name}

    def get_action(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an action definition by name."""
        action = self._actions.get(name)
        return action.to_dict() if action else None

    def list_actions(self, category: Optional[ActionCategory] = None) -> List[Dict[str, Any]]:
        """List all registered actions, optionally filtered by category."""
        actions = self._actions.values()
        if category:
            actions = [a for a in actions if a.category == category]
        return [a.to_dict() for a in actions]

    def register_domain(self, domain: ActionDomain) -> Dict[str, Any]:
        """Register a new action domain."""
        with self._lock:
            if domain.name in self._domains:
                return {"success": False, "error": f"Domain '{domain.name}' already exists"}
            self._domains[domain.name] = domain
            return {"success": True, "domain_id": domain.domain_id}

    def list_domains(self) -> List[Dict[str, Any]]:
        """List all registered action domains."""
        return [d.to_dict() for d in self._domains.values()]

    # -------------------------------------------------------------------------
    # Action Execution
    # -------------------------------------------------------------------------

    def execute(self, action_name: str, parameters: Dict[str, Any],
                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a named action with the given parameters."""
        action = self._actions.get(action_name)
        if not action:
            return {"success": False, "error": f"Action '{action_name}' not found"}

        # Check cooldown
        now = time.time()
        if action_name in self._cooldowns:
            remaining = self._cooldowns[action_name] - now
            if remaining > 0:
                return {"success": False, "error": f"Action on cooldown ({remaining:.1f}s remaining)"}

        execution = ActionExecution(
            action_id=action.action_id,
            action_name=action_name,
            parameters=parameters,
            status=ActionExecutionStatus.VALIDATING,
            started_at=now,
        )

        # Validate parameters
        validation = self._validate_parameters(action, parameters)
        if not validation["valid"]:
            execution.status = ActionExecutionStatus.FAILED
            execution.error = validation["error"]
            self._record_execution(execution)
            return {"success": False, "error": validation["error"]}

        # Check preconditions
        precond_result = self._check_preconditions(action, parameters, context or {})
        if not precond_result["satisfied"]:
            execution.status = ActionExecutionStatus.FAILED
            execution.error = precond_result["error"]
            self._record_execution(execution)
            return {"success": False, "error": precond_result["error"]}

        # Take snapshot for potential rollback
        if action.is_reversible:
            execution.snapshot_before = self._take_snapshot(action_name, parameters)

        # Execute
        execution.status = ActionExecutionStatus.EXECUTING
        self._active_executions[execution.execution_id] = execution

        try:
            if action.executor:
                result = action.executor(**parameters)
            else:
                result = self._default_executor(action, parameters)

            execution.status = ActionExecutionStatus.COMPLETED
            execution.result = result
            execution.effects_applied = [e.effect_id for e in action.effects]
            self._total_executions += 1
        except Exception as e:
            execution.status = ActionExecutionStatus.FAILED
            execution.error = str(e)
            self._total_failures += 1
            if action.is_reversible and execution.snapshot_before:
                self._rollback_execution(execution.execution_id)

        execution.completed_at = time.time()
        execution.duration_ms = (execution.completed_at - execution.started_at) * 1000

        # Set cooldown
        if action.cooldown_ms > 0:
            self._cooldowns[action_name] = now + action.cooldown_ms / 1000.0

        self._record_execution(execution)

        return {
            "success": execution.status == ActionExecutionStatus.COMPLETED,
            "execution_id": execution.execution_id,
            "status": execution.status.value,
            "result": execution.result,
            "duration_ms": execution.duration_ms,
            "error": execution.error,
        }

    def _validate_parameters(self, action: ActionDefinition,
                             parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that all required parameters are present and valid."""
        for param in action.parameters:
            if param.required and param.name not in parameters:
                return {"valid": False, "error": f"Missing required parameter: {param.name}"}
            if param.name in parameters:
                value = parameters[param.name]
                if param.validation and not param.validation(value):
                    return {"valid": False, "error": f"Validation failed for parameter: {param.name}"}
        return {"valid": True}

    def _check_preconditions(self, action: ActionDefinition,
                             parameters: Dict[str, Any],
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """Check all preconditions for an action."""
        for cond in action.preconditions:
            if cond.evaluator:
                try:
                    if not cond.evaluator({**parameters, **context}):
                        return {"satisfied": False, "error": cond.error_message or f"Precondition '{cond.condition_id}' not met"}
                except Exception as e:
                    return {"satisfied": False, "error": f"Precondition check error: {e}"}
        return {"satisfied": True}

    def _default_executor(self, action: ActionDefinition,
                          parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Default action executor for built-in actions."""
        return {
            "action": action.name,
            "parameters": parameters,
            "effects_applied": len(action.effects),
            "timestamp": time.time(),
        }

    def _take_snapshot(self, action_name: str,
                       parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Take a state snapshot for rollback purposes."""
        snapshot_id = uuid.uuid4().hex[:12]
        snapshot = {
            "snapshot_id": snapshot_id,
            "action_name": action_name,
            "parameters": dict(parameters),
            "timestamp": time.time(),
        }
        self._state_snapshots[snapshot_id] = snapshot
        return snapshot

    def _rollback_execution(self, execution_id: str) -> Dict[str, Any]:
        """Rollback a failed execution."""
        execution = self._active_executions.pop(execution_id, None)
        if not execution:
            return {"success": False, "error": "Execution not found"}
        execution.status = ActionExecutionStatus.ROLLED_BACK
        return {"success": True, "execution_id": execution_id}

    def _record_execution(self, execution: ActionExecution) -> None:
        """Record an execution in history."""
        with self._lock:
            self._execution_history.append(execution)
            if len(self._execution_history) > 10000:
                self._execution_history = self._execution_history[-5000:]

    # -------------------------------------------------------------------------
    # Action Planning
    # -------------------------------------------------------------------------

    def plan_actions(self, goal: str, max_steps: int = 10,
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate an action plan to achieve a goal."""
        plan = ActionPlan(goal=goal)

        # Simple heuristic: find actions with matching tags
        goal_lower = goal.lower()
        relevant_actions = []
        for action in self._actions.values():
            if any(tag in goal_lower for tag in action.tags):
                relevant_actions.append(action)
            elif action.category.value in goal_lower:
                relevant_actions.append(action)

        # If no matching tags, include all actions as candidates
        if not relevant_actions:
            relevant_actions = list(self._actions.values())

        # Sort by relevance (tags match count) and limit
        relevant_actions.sort(key=lambda a: sum(
            1 for tag in a.tags if tag in goal_lower
        ), reverse=True)
        plan.actions = relevant_actions[:max_steps]
        plan.estimated_cost = sum(a.cost for a in plan.actions)
        plan.estimated_duration_ms = sum(a.cooldown_ms for a in plan.actions)

        with self._lock:
            self._plans[plan.plan_id] = plan

        return plan.to_dict()

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get a plan by ID."""
        plan = self._plans.get(plan_id)
        return plan.to_dict() if plan else None

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_execution_history(self, action_name: Optional[str] = None,
                              limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution history, optionally filtered by action name."""
        history = self._execution_history
        if action_name:
            history = [e for e in history if e.action_name == action_name]
        return [e.to_dict() for e in history[-limit:]]

    def get_statistics(self) -> Dict[str, Any]:
        """Get action space statistics."""
        with self._lock:
            return {
                "total_actions": len(self._actions),
                "total_domains": len(self._domains),
                "total_executions": self._total_executions,
                "total_failures": self._total_failures,
                "success_rate": (
                    (self._total_executions - self._total_failures) / max(self._total_executions, 1)
                ),
                "active_executions": len(self._active_executions),
                "history_size": len(self._execution_history),
                "plans_created": len(self._plans),
                "categories": {c.value: len([a for a in self._actions.values() if a.category == c])
                              for c in ActionCategory},
            }

    def get_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        return {
            "initialized": self._initialized,
            "actions_registered": len(self._actions),
            "domains": len(self._domains),
            "total_executions": self._total_executions,
            "success_rate": (
                (self._total_executions - self._total_failures) / max(self._total_executions, 1)
                if self._total_executions > 0 else 0.0
            ),
        }


# ── Module Accessor ──

def get_action_space() -> ActionSpaceEngine:
    """Get the singleton action space engine instance."""
    return ActionSpaceEngine.get_instance()