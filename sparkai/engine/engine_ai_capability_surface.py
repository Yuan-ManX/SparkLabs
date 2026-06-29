"""
SparkLabs Engine - AI Capability Surface

Exposes engine subsystem capabilities to AI agents in a uniform,
introspectable way. Each capability declares its target system,
operation name, parameter schema, return description, and optional
runtime handler. Agents can query the surface to discover what the
engine can do, invoke capabilities by name, and subscribe to
capability change events.

The surface is the canonical entry point for any AI-driven engine
mutation: rather than ad-hoc per-subsystem hooks, agents consult
the capability surface to learn the available operations and dispatch
through a single unified channel.

Architecture:
  AICapabilitySurface (Singleton)
    |-- CapabilityDescriptor (declares one engine operation)
    |-- CapabilityInvocation (one execution of a capability)
    |-- CapabilitySubscription (observer for change events)
    |-- CapabilitySnapshot (point-in-time state capture)

Capabilities are registered either explicitly (via register_capability)
or in batches via register_system. The surface validates invocations
against the declared parameter schema and emits structured events
before and after each invocation.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Enums
# =============================================================================


class CapabilityStatus(Enum):
    """Lifecycle status of a capability invocation."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    NOT_FOUND = "not_found"
    VALIDATION_FAILED = "validation_failed"


class ParameterType(Enum):
    """JSON-ish parameter type identifiers."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    ANY = "any"


class CapabilityTier(Enum):
    """Tier indicating stability and intended audience."""
    CORE = "core"
    STABLE = "stable"
    EXPERIMENTAL = "experimental"
    INTERNAL = "internal"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ParameterDescriptor:
    """Describes a single capability parameter.

    Attributes:
        name: Parameter name.
        type: Expected value type.
        description: Human-readable description.
        required: Whether the parameter is mandatory.
        default_value: Default value when omitted.
        enum_values: Optional list of allowed values.
    """
    name: str = ""
    type: ParameterType = ParameterType.ANY
    description: str = ""
    required: bool = False
    default_value: Any = None
    enum_values: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "required": self.required,
            "default_value": self.default_value,
            "enum_values": list(self.enum_values),
        }


@dataclass
class CapabilityDescriptor:
    """Declares one engine operation exposed to AI agents.

    Attributes:
        capability_id: Auto-generated unique identifier.
        target_system: Engine subsystem name (e.g. ``physics_dynamics``).
        operation_name: Operation name within the subsystem.
        display_name: Human-readable name.
        description: Long-form description of what the operation does.
        parameters: Parameter descriptors.
        returns: Description of the return value.
        tier: Stability tier.
        tags: Free-form tags for filtering.
        handler_key: Optional key for the registered runtime handler.
    """
    capability_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    target_system: str = ""
    operation_name: str = ""
    display_name: str = ""
    description: str = ""
    parameters: List[ParameterDescriptor] = field(default_factory=list)
    returns: str = ""
    tier: CapabilityTier = CapabilityTier.STABLE
    tags: List[str] = field(default_factory=list)
    handler_key: str = ""

    @property
    def key(self) -> str:
        """Composite key used for lookup."""
        return f"{self.target_system}.{self.operation_name}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "target_system": self.target_system,
            "operation_name": self.operation_name,
            "display_name": self.display_name,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "returns": self.returns,
            "tier": self.tier.value,
            "tags": list(self.tags),
            "handler_key": self.handler_key,
            "key": self.key,
        }


@dataclass
class CapabilityInvocation:
    """Records one execution of a capability.

    Attributes:
        invocation_id: Auto-generated unique identifier.
        capability_id: ID of the invoked capability.
        target_system: Subsystem name.
        operation_name: Operation name.
        parameters: Invocation parameters.
        status: Execution status.
        result: Result payload on success.
        error: Error message on failure.
        caller: Optional caller identifier (e.g. agent_id).
        started_at: Execution start timestamp.
        finished_at: Execution finish timestamp.
    """
    invocation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    capability_id: str = ""
    target_system: str = ""
    operation_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: CapabilityStatus = CapabilityStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    caller: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invocation_id": self.invocation_id,
            "capability_id": self.capability_id,
            "target_system": self.target_system,
            "operation_name": self.operation_name,
            "parameters": dict(self.parameters),
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "caller": self.caller,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass
class CapabilitySubscription:
    """A subscription to capability surface events.

    Attributes:
        subscription_id: Auto-generated unique identifier.
        subscriber: Subscriber identifier (e.g. agent_id).
        event_filter: Optional filter expression. Currently only
            supports filtering by ``target_system`` or ``operation_name``
            (e.g. ``target_system=physics_dynamics``).
        callback: Callable invoked with the event payload.
        created_at: Subscription creation timestamp.
        active: Whether the subscription is currently active.
    """
    subscription_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    subscriber: str = ""
    event_filter: str = ""
    callback: Optional[Callable[[Dict[str, Any]], None]] = None
    created_at: float = field(default_factory=time.time)
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "subscriber": self.subscriber,
            "event_filter": self.event_filter,
            "created_at": self.created_at,
            "active": self.active,
        }


@dataclass
class CapabilitySnapshot:
    """Point-in-time snapshot of the capability surface.

    Attributes:
        snapshot_id: Auto-generated unique identifier.
        captured_at: POSIX timestamp of capture.
        capability_count: Total registered capabilities.
        invocation_count: Total invocations recorded.
        system_count: Number of distinct target systems.
        capabilities: Serialized capabilities (optionally filtered).
        recent_invocations: Most recent invocations.
        system_status: Aggregate status dictionary.
    """
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    captured_at: float = field(default_factory=time.time)
    capability_count: int = 0
    invocation_count: int = 0
    system_count: int = 0
    capabilities: List[Dict[str, Any]] = field(default_factory=list)
    recent_invocations: List[Dict[str, Any]] = field(default_factory=list)
    system_status: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "capability_count": self.capability_count,
            "invocation_count": self.invocation_count,
            "system_count": self.system_count,
            "capabilities": list(self.capabilities),
            "recent_invocations": list(self.recent_invocations),
            "system_status": dict(self.system_status),
        }


# =============================================================================
# Capability Surface (Singleton)
# =============================================================================


class AICapabilitySurface:
    """Singleton registry exposing engine capabilities to AI agents.

    The surface decouples agent intent from engine internals: agents
    interact with capabilities by name, while engine subsystems
    register their operations and handlers in a uniform way.

    Capabilities may be registered without a handler (declaration
    only) so that AI tooling can introspect the available surface
    even when the underlying engine is not running. When a handler
    is later registered, the capability becomes invocable.
    """

    _instance: Optional["AICapabilitySurface"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_HISTORY: int = 500

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._capabilities: Dict[str, CapabilityDescriptor] = {}
        self._handlers: Dict[str, Callable[..., Any]] = {}
        self._invocations: Dict[str, CapabilityInvocation] = {}
        self._subscriptions: Dict[str, CapabilitySubscription] = {}
        self._stats: Dict[str, int] = {
            "capabilities_registered": 0,
            "handlers_registered": 0,
            "invocations_total": 0,
            "invocations_succeeded": 0,
            "invocations_failed": 0,
            "invocations_not_found": 0,
            "invocations_validation_failed": 0,
        }
        self._register_default_capabilities()

    @classmethod
    def get_instance(cls) -> "AICapabilitySurface":
        """Return the singleton AICapabilitySurface instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Default Capability Registration
    # ------------------------------------------------------------------

    def _register_default_capabilities(self) -> None:
        """Register a curated set of engine capability declarations.

        These declarations describe operations that engine subsystems
        typically expose. They are registered without handlers so that
        AI tooling can introspect the surface; subsystems register
        handlers separately via :meth:`register_handler`.
        """
        default_caps = [
            CapabilityDescriptor(
                target_system="physics_dynamics",
                operation_name="scale_damage",
                display_name="Scale Damage Output",
                description="Scale all damage values produced by physics bodies by a multiplicative factor.",
                parameters=[
                    ParameterDescriptor(name="factor", type=ParameterType.FLOAT,
                                        description="Damage multiplier (e.g. 1.25 = +25%).",
                                        required=True, default_value=1.0),
                ],
                returns="dict with the previous and new damage scale",
                tags=["combat", "physics"],
            ),
            CapabilityDescriptor(
                target_system="physics_dynamics",
                operation_name="set_gravity",
                display_name="Set Gravity Vector",
                description="Override the world gravity vector used by the physics solver.",
                parameters=[
                    ParameterDescriptor(name="x", type=ParameterType.FLOAT,
                                        description="Horizontal gravity component.",
                                        required=True, default_value=0.0),
                    ParameterDescriptor(name="y", type=ParameterType.FLOAT,
                                        description="Vertical gravity component.",
                                        required=True, default_value=-9.81),
                ],
                returns="dict confirming the new gravity vector",
                tags=["physics", "world"],
            ),
            CapabilityDescriptor(
                target_system="ai_system",
                operation_name="set_aggression",
                display_name="Set AI Aggression Level",
                description="Set the global aggression level for AI-controlled entities.",
                parameters=[
                    ParameterDescriptor(name="level", type=ParameterType.STRING,
                                        description="Aggression level label.",
                                        required=True, default_value="normal",
                                        enum_values=["low", "normal", "high", "berserk"]),
                ],
                returns="dict with the previous and new aggression level",
                tags=["ai", "combat"],
            ),
            CapabilityDescriptor(
                target_system="ai_system",
                operation_name="spawn_pursuer",
                display_name="Spawn Pursuer Entity",
                description="Spawn an AI pursuer that tracks the player.",
                parameters=[
                    ParameterDescriptor(name="count", type=ParameterType.INTEGER,
                                        description="Number of pursuers to spawn.",
                                        required=False, default_value=1),
                ],
                returns="list of spawned pursuer entity ids",
                tags=["ai", "combat", "spawning"],
            ),
            CapabilityDescriptor(
                target_system="audio_spatial",
                operation_name="swap_track",
                display_name="Swap Active Audio Track",
                description="Switch the active background music track to one matching a mood.",
                parameters=[
                    ParameterDescriptor(name="mood", type=ParameterType.STRING,
                                        description="Desired mood label.",
                                        required=True, default_value="neutral",
                                        enum_values=["calm", "tense", "epic", "neutral"]),
                ],
                returns="dict with the previous and new track id",
                tags=["audio", "music"],
            ),
            CapabilityDescriptor(
                target_system="audio_spatial",
                operation_name="set_ambient",
                display_name="Set Ambient Bed",
                description="Replace the ambient audio bed with a named preset.",
                parameters=[
                    ParameterDescriptor(name="preset", type=ParameterType.STRING,
                                        description="Ambient preset name.",
                                        required=True, default_value="default",
                                        enum_values=["default", "calm", "eerie", "uplifting", "forest", "city"]),
                ],
                returns="dict confirming the ambient preset change",
                tags=["audio", "ambient"],
            ),
            CapabilityDescriptor(
                target_system="camera_controller",
                operation_name="enable_shake",
                display_name="Enable Camera Shake",
                description="Enable procedural camera shake with a given amplitude.",
                parameters=[
                    ParameterDescriptor(name="amplitude", type=ParameterType.FLOAT,
                                        description="Shake amplitude in [0.0, 1.0].",
                                        required=True, default_value=0.5),
                ],
                returns="dict with the shake configuration applied",
                tags=["camera", "fx"],
            ),
            CapabilityDescriptor(
                target_system="camera_controller",
                operation_name="set_follow",
                display_name="Set Camera Follow Style",
                description="Change the camera follow style (e.g. gentle, chase, rigid).",
                parameters=[
                    ParameterDescriptor(name="style", type=ParameterType.STRING,
                                        description="Follow style label.",
                                        required=True, default_value="default",
                                        enum_values=["default", "gentle", "chase", "rigid", "cinematic"]),
                ],
                returns="dict with the previous and new follow style",
                tags=["camera", "cinematic"],
            ),
            CapabilityDescriptor(
                target_system="lighting_2d",
                operation_name="dim_lights",
                display_name="Dim Scene Lights",
                description="Scale the intensity of all 2D lights toward a target level.",
                parameters=[
                    ParameterDescriptor(name="level", type=ParameterType.FLOAT,
                                        description="Target light intensity in [0.0, 1.0].",
                                        required=True, default_value=0.5),
                ],
                returns="dict with the previous and new light levels",
                tags=["lighting", "atmosphere"],
            ),
            CapabilityDescriptor(
                target_system="lighting_2d",
                operation_name="brighten",
                display_name="Brighten Scene Lights",
                description="Scale the intensity of all 2D lights up to a target level.",
                parameters=[
                    ParameterDescriptor(name="level", type=ParameterType.FLOAT,
                                        description="Target light intensity in [0.0, 1.0].",
                                        required=True, default_value=0.9),
                ],
                returns="dict with the previous and new light levels",
                tags=["lighting", "atmosphere"],
            ),
            CapabilityDescriptor(
                target_system="particle_system",
                operation_name="spawn_aura",
                display_name="Spawn Aura Particles",
                description="Spawn an aura particle effect attached to an entity.",
                parameters=[
                    ParameterDescriptor(name="intensity", type=ParameterType.STRING,
                                        description="Aura intensity label.",
                                        required=True, default_value="medium",
                                        enum_values=["low", "medium", "high"]),
                ],
                returns="dict with the spawned emitter id",
                tags=["particles", "fx"],
            ),
            CapabilityDescriptor(
                target_system="particle_system",
                operation_name="spawn_fog",
                display_name="Spawn Fog Volume",
                description="Spawn a volumetric fog effect with a given density.",
                parameters=[
                    ParameterDescriptor(name="density", type=ParameterType.FLOAT,
                                        description="Fog density in [0.0, 1.0].",
                                        required=True, default_value=0.5),
                ],
                returns="dict with the spawned fog volume id",
                tags=["particles", "atmosphere"],
            ),
            CapabilityDescriptor(
                target_system="procedural_world",
                operation_name="seed_landmarks",
                display_name="Seed World Landmarks",
                description="Distribute procedural landmarks across the world.",
                parameters=[
                    ParameterDescriptor(name="density", type=ParameterType.FLOAT,
                                        description="Landmark density in [0.0, 1.0].",
                                        required=True, default_value=0.5),
                ],
                returns="list of seeded landmark ids",
                tags=["world", "procedural"],
            ),
            CapabilityDescriptor(
                target_system="quest_generator",
                operation_name="spawn_side_quests",
                display_name="Spawn Side Quests",
                description="Generate additional side quests for the player.",
                parameters=[
                    ParameterDescriptor(name="count", type=ParameterType.INTEGER,
                                        description="Number of quests to generate.",
                                        required=False, default_value=1),
                ],
                returns="list of generated quest ids",
                tags=["quest", "narrative"],
            ),
            CapabilityDescriptor(
                target_system="economy_simulator",
                operation_name="inflate_rewards",
                display_name="Inflate Economy Rewards",
                description="Multiply reward payouts by a factor greater than 1.",
                parameters=[
                    ParameterDescriptor(name="factor", type=ParameterType.FLOAT,
                                        description="Reward multiplier.",
                                        required=True, default_value=1.25),
                ],
                returns="dict with the previous and new reward multiplier",
                tags=["economy", "balance"],
            ),
            CapabilityDescriptor(
                target_system="economy_simulator",
                operation_name="deflate_rewards",
                display_name="Deflate Economy Rewards",
                description="Multiply reward payouts by a factor less than 1.",
                parameters=[
                    ParameterDescriptor(name="factor", type=ParameterType.FLOAT,
                                        description="Reward multiplier.",
                                        required=True, default_value=0.8),
                ],
                returns="dict with the previous and new reward multiplier",
                tags=["economy", "balance"],
            ),
            CapabilityDescriptor(
                target_system="scene_manager",
                operation_name="load_scene",
                display_name="Load Scene",
                description="Load a scene by its identifier with optional transition.",
                parameters=[
                    ParameterDescriptor(name="scene_id", type=ParameterType.STRING,
                                        description="Scene identifier to load.",
                                        required=True),
                    ParameterDescriptor(name="transition", type=ParameterType.STRING,
                                        description="Transition style.",
                                        required=False, default_value="fade",
                                        enum_values=["fade", "cut", "slide"]),
                ],
                returns="dict confirming scene load",
                tags=["scene"],
            ),
            CapabilityDescriptor(
                target_system="scene_manager",
                operation_name="unload_scene",
                display_name="Unload Scene",
                description="Unload a scene by its identifier.",
                parameters=[
                    ParameterDescriptor(name="scene_id", type=ParameterType.STRING,
                                        description="Scene identifier to unload.",
                                        required=True),
                ],
                returns="dict confirming scene unload",
                tags=["scene"],
            ),
        ]
        for cap in default_caps:
            self._capabilities[cap.key] = cap

    # ------------------------------------------------------------------
    # Capability Management
    # ------------------------------------------------------------------

    def register_capability(self, capability: CapabilityDescriptor) -> CapabilityDescriptor:
        """Register or replace a capability declaration."""
        with self._instance_lock:
            self._capabilities[capability.key] = capability
            self._stats["capabilities_registered"] = len(self._capabilities)
            self._emit_event("capability_registered", capability.to_dict())
            return capability

    def create_capability(
        self,
        target_system: str,
        operation_name: str,
        display_name: str = "",
        description: str = "",
        parameters: Optional[List[ParameterDescriptor]] = None,
        returns: str = "",
        tier: CapabilityTier = CapabilityTier.STABLE,
        tags: Optional[List[str]] = None,
    ) -> CapabilityDescriptor:
        """Create and register a capability declaration."""
        cap = CapabilityDescriptor(
            target_system=target_system,
            operation_name=operation_name,
            display_name=display_name or f"{target_system}.{operation_name}",
            description=description,
            parameters=list(parameters) if parameters else [],
            returns=returns,
            tier=tier,
            tags=list(tags) if tags else [],
        )
        return self.register_capability(cap)

    def remove_capability(self, target_system: str, operation_name: str) -> bool:
        """Remove a capability declaration by composite key."""
        key = f"{target_system}.{operation_name}"
        with self._instance_lock:
            removed = self._capabilities.pop(key, None) is not None
            self._handlers.pop(key, None)
            if removed:
                self._stats["capabilities_registered"] = len(self._capabilities)
            return removed

    def get_capability(self, target_system: str, operation_name: str) -> Optional[CapabilityDescriptor]:
        """Retrieve a capability descriptor by composite key."""
        with self._instance_lock:
            return self._capabilities.get(f"{target_system}.{operation_name}")

    def list_capabilities(
        self,
        target_system: Optional[str] = None,
        tag: Optional[str] = None,
        tier: Optional[CapabilityTier] = None,
    ) -> List[CapabilityDescriptor]:
        """List capabilities, optionally filtered."""
        with self._instance_lock:
            caps = list(self._capabilities.values())
        if target_system is not None:
            caps = [c for c in caps if c.target_system == target_system]
        if tag is not None:
            caps = [c for c in caps if tag in c.tags]
        if tier is not None:
            caps = [c for c in caps if c.tier == tier]
        return caps

    def list_target_systems(self) -> List[str]:
        """Return the sorted list of distinct target systems."""
        with self._instance_lock:
            return sorted({c.target_system for c in self._capabilities.values()})

    # ------------------------------------------------------------------
    # Handler Management
    # ------------------------------------------------------------------

    def register_handler(
        self, target_system: str, operation_name: str, handler: Callable[..., Any]
    ) -> None:
        """Register a runtime handler for a capability."""
        key = f"{target_system}.{operation_name}"
        with self._instance_lock:
            self._handlers[key] = handler
            self._stats["handlers_registered"] = len(self._handlers)

    def unregister_handler(self, target_system: str, operation_name: str) -> bool:
        """Remove a previously-registered handler."""
        key = f"{target_system}.{operation_name}"
        with self._instance_lock:
            removed = self._handlers.pop(key, None) is not None
            if removed:
                self._stats["handlers_registered"] = len(self._handlers)
            return removed

    def list_handlers(self) -> List[Dict[str, str]]:
        """List all registered handler keys."""
        with self._instance_lock:
            return [
                {"target_system": k.split(".", 1)[0], "operation_name": k.split(".", 1)[1]}
                for k in self._handlers.keys()
            ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_parameter(
        descriptor: ParameterDescriptor, value: Any
    ) -> Tuple[bool, Optional[str]]:
        """Validate a single parameter against its descriptor."""
        if value is None:
            if descriptor.required and descriptor.default_value is None:
                return False, f"Missing required parameter: {descriptor.name}"
            return True, None
        type_map = {
            ParameterType.STRING: str,
            ParameterType.INTEGER: int,
            ParameterType.FLOAT: (int, float),
            ParameterType.BOOLEAN: bool,
        }
        expected = type_map.get(descriptor.type)
        if expected is not None and not isinstance(value, expected):
            # Allow int in place of float for ergonomic API use.
            if descriptor.type == ParameterType.FLOAT and isinstance(value, int):
                pass
            else:
                return False, (
                    f"Parameter '{descriptor.name}' expected "
                    f"{descriptor.type.value}, got {type(value).__name__}"
                )
        if descriptor.enum_values and value not in descriptor.enum_values:
            return False, (
                f"Parameter '{descriptor.name}' value '{value}' "
                f"not in allowed values {descriptor.enum_values}"
            )
        return True, None

    def _validate_invocation(
        self, capability: CapabilityDescriptor, parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate an invocation against the capability schema."""
        for descriptor in capability.parameters:
            value = parameters.get(descriptor.name, descriptor.default_value)
            ok, err = self._validate_parameter(descriptor, value)
            if not ok:
                return False, err
        return True, None

    # ------------------------------------------------------------------
    # Invocation
    # ------------------------------------------------------------------

    def invoke(
        self,
        target_system: str,
        operation_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        caller: str = "",
    ) -> CapabilityInvocation:
        """Invoke a capability by name.

        Returns a :class:`CapabilityInvocation` recording the outcome.
        If no handler is registered, the invocation is recorded as
        ``NOT_FOUND`` rather than raising.
        """
        params = dict(parameters) if parameters else {}
        key = f"{target_system}.{operation_name}"
        invocation = CapabilityInvocation(
            target_system=target_system,
            operation_name=operation_name,
            parameters=params,
            caller=caller,
            started_at=time.time(),
        )
        with self._instance_lock:
            capability = self._capabilities.get(key)
            if capability is None:
                invocation.status = CapabilityStatus.NOT_FOUND
                invocation.error = f"Capability not found: {key}"
                invocation.finished_at = time.time()
                self._record_invocation(invocation)
                self._stats["invocations_not_found"] += 1
                self._emit_event("invocation_failed", invocation.to_dict())
                return invocation
            invocation.capability_id = capability.capability_id
            ok, err = self._validate_invocation(capability, params)
            if not ok:
                invocation.status = CapabilityStatus.VALIDATION_FAILED
                invocation.error = err
                invocation.finished_at = time.time()
                self._record_invocation(invocation)
                self._stats["invocations_validation_failed"] += 1
                self._emit_event("invocation_failed", invocation.to_dict())
                return invocation
            handler = self._handlers.get(key)

        # Emit pre-invocation event while not holding the lock.
        self._emit_event("invocation_started", invocation.to_dict())

        if handler is None:
            invocation.status = CapabilityStatus.NOT_FOUND
            invocation.error = f"No handler registered for capability: {key}"
        else:
            invocation.status = CapabilityStatus.RUNNING
            try:
                # Apply default values for missing parameters.
                for descriptor in capability.parameters:
                    if descriptor.name not in params and descriptor.default_value is not None:
                        params[descriptor.name] = descriptor.default_value
                result = handler(**params) if params else handler()
                if isinstance(result, dict):
                    invocation.result = result
                else:
                    invocation.result = {"value": str(result) if result is not None else None}
                invocation.status = CapabilityStatus.SUCCESS
            except Exception as exc:  # noqa: BLE001 - surface must stay alive
                invocation.status = CapabilityStatus.FAILED
                invocation.error = str(exc)
        invocation.finished_at = time.time()

        with self._instance_lock:
            self._record_invocation(invocation)
            self._stats["invocations_total"] += 1
            if invocation.status == CapabilityStatus.SUCCESS:
                self._stats["invocations_succeeded"] += 1
                event_name = "invocation_succeeded"
            else:
                self._stats["invocations_failed"] += 1
                event_name = "invocation_failed"
        self._emit_event(event_name, invocation.to_dict())
        return invocation

    def _record_invocation(self, invocation: CapabilityInvocation) -> None:
        """Record an invocation and trim history if needed."""
        self._invocations[invocation.invocation_id] = invocation
        if len(self._invocations) > self._MAX_HISTORY:
            sorted_invocations = sorted(
                self._invocations.items(),
                key=lambda kv: kv[1].started_at,
            )
            excess = len(self._invocations) - self._MAX_HISTORY
            for inv_id, _ in sorted_invocations[:excess]:
                self._invocations.pop(inv_id, None)

    # ------------------------------------------------------------------
    # Subscription / Event Emission
    # ------------------------------------------------------------------

    def subscribe(
        self,
        subscriber: str,
        callback: Callable[[Dict[str, Any]], None],
        event_filter: str = "",
    ) -> CapabilitySubscription:
        """Subscribe to capability surface events."""
        sub = CapabilitySubscription(
            subscriber=subscriber,
            callback=callback,
            event_filter=event_filter,
        )
        with self._instance_lock:
            self._subscriptions[sub.subscription_id] = sub
        return sub

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription."""
        with self._instance_lock:
            return self._subscriptions.pop(subscription_id, None) is not None

    def _emit_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Emit an event to matching subscribers."""
        with self._instance_lock:
            subs = list(self._subscriptions.values())
        envelope = {
            "event": event_name,
            "payload": payload,
            "timestamp": time.time(),
        }
        for sub in subs:
            if not sub.active or sub.callback is None:
                continue
            if sub.event_filter:
                # Simple filter: ``key=value`` pairs separated by ';'.
                try:
                    if not self._matches_filter(payload, sub.event_filter):
                        continue
                except Exception:  # noqa: BLE001
                    continue
            try:
                sub.callback(envelope)
            except Exception:  # noqa: BLE001 - subscribers must not break emitters
                pass

    @staticmethod
    def _matches_filter(payload: Dict[str, Any], filter_expr: str) -> bool:
        """Evaluate a simple ``key=value`` filter against a payload."""
        for clause in filter_expr.split(";"):
            clause = clause.strip()
            if not clause:
                continue
            if "=" not in clause:
                continue
            key, expected = clause.split("=", 1)
            key = key.strip()
            expected = expected.strip()
            actual = str(payload.get(key, ""))
            if actual != expected:
                return False
        return True

    # ------------------------------------------------------------------
    # Query & Introspection
    # ------------------------------------------------------------------

    def get_invocation(self, invocation_id: str) -> Optional[CapabilityInvocation]:
        """Retrieve an invocation by id."""
        with self._instance_lock:
            return self._invocations.get(invocation_id)

    def list_invocations(self, limit: int = 50) -> List[CapabilityInvocation]:
        """Return the most recent invocations."""
        with self._instance_lock:
            invocations = sorted(
                self._invocations.values(),
                key=lambda i: i.started_at,
                reverse=True,
            )
            return invocations[:limit]

    def get_status(self) -> Dict[str, Any]:
        """Return aggregate status."""
        with self._instance_lock:
            return {
                "capability_count": len(self._capabilities),
                "handler_count": len(self._handlers),
                "invocation_count": len(self._invocations),
                "subscription_count": len(self._subscriptions),
                "target_systems": self.list_target_systems(),
                "stats": dict(self._stats),
            }

    def get_snapshot(
        self,
        target_system: Optional[str] = None,
    ) -> CapabilitySnapshot:
        """Capture a point-in-time snapshot of the surface."""
        with self._instance_lock:
            caps = self.list_capabilities(target_system=target_system)
            return CapabilitySnapshot(
                capability_count=len(self._capabilities),
                invocation_count=len(self._invocations),
                system_count=len({c.target_system for c in self._capabilities.values()}),
                capabilities=[c.to_dict() for c in caps],
                recent_invocations=[i.to_dict() for i in self.list_invocations(20)],
                system_status=self.get_status(),
            )

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the surface to its initial state."""
        with self._instance_lock:
            self._capabilities.clear()
            self._handlers.clear()
            self._invocations.clear()
            self._subscriptions.clear()
            for key in self._stats:
                self._stats[key] = 0
            self._register_default_capabilities()


def get_ai_capability_surface() -> AICapabilitySurface:
    """Return the singleton AICapabilitySurface instance."""
    return AICapabilitySurface.get_instance()
