"""
SparkLabs Agent - Embodiment Interface

Embodiment interface that links cognitive agents to game entities, providing
a sensory channel for perceiving the world through entity sensors and a motor
channel for acting through entity actuators. Supports one-to-many (swarm),
many-to-one (shared control), and one-to-one embodiment relationships.

When an agent inhabits an entity, it receives periodic perception updates
from the entity's sensory channels and can issue motor actions through the
entity's actuators. Conflicting actions from multiple agents inhabiting the
same entity are resolved through configurable arbitration strategies.

The module focuses on the embodiment contract and lifecycle. Actual sensory
data acquisition and motor action execution are delegated to registered
supplier callbacks, allowing integration with any perception or action
system.

Architecture:
  AgentEmbodimentEngine (Singleton)
    |-- EmbodimentProfile (agent <-> entity link contract)
    |-- SensoryInput (single channel reading)
    |-- PerceptSnapshot (aggregated perception delivered to an agent)
    |-- MotorAction (action issued through an entity actuator)
    |-- EmbodimentEvent (lifecycle event audit trail)
    |-- EmbodimentSnapshot (point-in-time engine state)
    |-- inhabit() / leave() / suspend() / resume()
    |-- receive_perception() / issue_action()
    |-- arbitrate_actions() (conflict resolution)
    |-- tick() (advance the embodiment clock)
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SensoryChannel(Enum):
    """Sensory channels through which an agent perceives the world."""
    VISUAL = "visual"
    AUDITORY = "auditory"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    SOCIAL = "social"
    MECHANICAL = "mechanical"
    ENVIRONMENTAL = "environmental"
    CUSTOM = "custom"


class MotorChannel(Enum):
    """Motor channels through which an agent acts on the world."""
    MOVEMENT = "movement"
    ACTION = "action"
    COMMUNICATION = "communication"
    EXPRESSION = "expression"
    INTERACTION = "interaction"
    CUSTOM = "custom"


class EmbodimentState(Enum):
    """Lifecycle states of an embodiment link."""
    INACTIVE = "inactive"
    INHABITING = "inhabiting"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LEAVING = "leaving"


class ArbitrationStrategy(Enum):
    """Strategies for resolving conflicting motor actions."""
    PRIORITY = "priority"
    VOTING = "voting"
    AVERAGE = "average"
    LAST_WRITER = "last_writer"
    FIRST_WRITER = "first_writer"
    ROUND_ROBIN = "round_robin"


class EmbodimentEventKind(Enum):
    """Kinds of embodiment lifecycle events."""
    INHABIT = "inhabit"
    LEAVE = "leave"
    PERCEPTION_RECEIVED = "perception_received"
    ACTION_ISSUED = "action_issued"
    ACTION_ARBITRATED = "action_arbitrated"
    ACTION_REJECTED = "action_rejected"
    STATE_CHANGED = "state_changed"
    CONFLICT_DETECTED = "conflict_detected"


class ActionStatus(Enum):
    """Status of a motor action."""
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SensoryInput:
    """A single sensory reading from one channel.

    Captures the channel, originating entity, payload data, and a
    confidence value describing how reliable the reading is.
    """
    channel: SensoryChannel = SensoryChannel.CUSTOM
    source_entity_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel.value,
            "source_entity_id": self.source_entity_id,
            "data": dict(self.data),
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class MotorAction:
    """A motor action issued by an agent through an entity's actuator."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    channel: MotorChannel = MotorChannel.CUSTOM
    action_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    issued_by: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat()
    )
    status: ActionStatus = ActionStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "channel": self.channel.value,
            "action_type": self.action_type,
            "parameters": dict(self.parameters),
            "priority": self.priority,
            "issued_by": self.issued_by,
            "timestamp": self.timestamp,
            "status": self.status.value,
        }


@dataclass
class EmbodimentProfile:
    """A link between an agent and an entity.

    Describes which sensory channels the agent receives, which motor
    channels it may act through, the arbitration strategy to use when
    multiple agents share the entity, and the current lifecycle state.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    entity_id: str = ""
    sensory_channels: List[SensoryChannel] = field(default_factory=list)
    motor_channels: List[MotorChannel] = field(default_factory=list)
    arbitration_strategy: ArbitrationStrategy = ArbitrationStrategy.PRIORITY
    priority: int = 0
    state: EmbodimentState = EmbodimentState.INACTIVE
    created_at: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "entity_id": self.entity_id,
            "sensory_channels": [c.value for c in self.sensory_channels],
            "motor_channels": [c.value for c in self.motor_channels],
            "arbitration_strategy": self.arbitration_strategy.value,
            "priority": self.priority,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class PerceptSnapshot:
    """Aggregated sensory inputs delivered to an agent for one tick."""
    profile_id: str = ""
    agent_id: str = ""
    entity_id: str = ""
    sensory_inputs: List[SensoryInput] = field(default_factory=list)
    aggregated_percept: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "entity_id": self.entity_id,
            "sensory_inputs": [s.to_dict() for s in self.sensory_inputs],
            "aggregated_percept": dict(self.aggregated_percept),
            "timestamp": self.timestamp,
        }


@dataclass
class EmbodimentEvent:
    """A lifecycle event emitted by the embodiment engine."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: EmbodimentEventKind = EmbodimentEventKind.STATE_CHANGED
    profile_id: str = ""
    agent_id: str = ""
    entity_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "entity_id": self.entity_id,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


@dataclass
class EmbodimentSnapshot:
    """A point-in-time snapshot of the embodiment engine state."""
    profile_count: int = 0
    active_profile_count: int = 0
    total_perceptions: int = 0
    total_actions: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_count": self.profile_count,
            "active_profile_count": self.active_profile_count,
            "total_perceptions": self.total_perceptions,
            "total_actions": self.total_actions,
            "stats": dict(self.stats),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_EVENTS: int = 1000
_MAX_ACTIONS: int = 5000
_MAX_PERCEPTS: int = 2000


# ---------------------------------------------------------------------------
# Agent Embodiment Engine (Singleton)
# ---------------------------------------------------------------------------


class AgentEmbodimentEngine:
    """Singleton engine managing embodiment links between agents and entities.

    Provides sensory aggregation and motor arbitration for AI agents
    inhabiting game entities. Supports one-to-many, many-to-one, and
    one-to-one embodiment relationships with configurable arbitration.

    Features:
      - Create and remove embodiment links (inhabit/leave)
      - Suspend and resume embodiment state
      - Distribute sensory inputs to all inhabiting agents
      - Issue motor actions with conflict arbitration
      - Configurable arbitration strategies (priority, voting, average,
        last-writer, first-writer, round-robin)
      - Lifecycle event emission with handler subscription
      - Tick-based clock for supplier-driven perception and action flush
    """

    _instance: Optional["AgentEmbodimentEngine"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        # Embodiment profiles keyed by profile id
        self._profiles: Dict[str, EmbodimentProfile] = {}
        # Latest percept per profile id
        self._percepts: Dict[str, PerceptSnapshot] = {}
        # All actions log
        self._actions: List[MotorAction] = []
        # Actions issued in the current tick, keyed by (entity_id, channel)
        self._tick_actions: Dict[Tuple[str, str], List[MotorAction]] = {}
        # Pending actions awaiting arbitration or tick flush
        self._pending_actions: List[Tuple[str, MotorAction]] = []
        # Sensory suppliers keyed by channel
        self._sensory_suppliers: Dict[
            SensoryChannel, Callable[[str], Dict[str, Any]]
        ] = {}
        # Motor suppliers keyed by channel
        self._motor_suppliers: Dict[
            MotorChannel, Callable[[str, MotorAction], bool]
        ] = {}
        # Event handlers keyed by kind
        self._event_handlers: Dict[
            EmbodimentEventKind, List[Callable[[EmbodimentEvent], None]]
        ] = {}
        # Event history
        self._events: List[EmbodimentEvent] = []
        self._round_robin_index: Dict[Tuple[str, str], int] = {}
        # Tick counter
        self._tick_count: int = 0
        # Statistics
        self._stats: Dict[str, int] = {
            "total_inhabits": 0,
            "total_leaves": 0,
            "total_perceptions_received": 0,
            "total_actions_issued": 0,
            "total_actions_applied": 0,
            "total_actions_rejected": 0,
            "total_conflicts_detected": 0,
            "total_ticks": 0,
        }
        # Instance lock for runtime operations
        self._instance_lock = threading.RLock()
        # Register default suppliers
        self._register_default_suppliers()
        self._initialized: bool = True

    @classmethod
    def get_instance(cls) -> "AgentEmbodimentEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Default suppliers
    # ------------------------------------------------------------------

    def _register_default_suppliers(self) -> None:
        """Register default no-op sensory and motor suppliers."""
        self._sensory_suppliers[SensoryChannel.VISUAL] = lambda entity_id: {}
        self._sensory_suppliers[SensoryChannel.SPATIAL] = lambda entity_id: {}
        self._motor_suppliers[MotorChannel.MOVEMENT] = lambda entity_id, action: True
        self._motor_suppliers[MotorChannel.ACTION] = lambda entity_id, action: True

    # ------------------------------------------------------------------
    # Channel normalization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_sensory_channel(channel: Any) -> SensoryChannel:
        """Normalize a channel reference to a SensoryChannel enum value."""
        if isinstance(channel, SensoryChannel):
            return channel
        if isinstance(channel, str):
            try:
                return SensoryChannel[channel]
            except KeyError:
                return SensoryChannel(channel)
        raise ValueError(f"Invalid sensory channel: {channel!r}")

    @staticmethod
    def _normalize_motor_channel(channel: Any) -> MotorChannel:
        """Normalize a channel reference to a MotorChannel enum value."""
        if isinstance(channel, MotorChannel):
            return channel
        if isinstance(channel, str):
            try:
                return MotorChannel[channel]
            except KeyError:
                return MotorChannel(channel)
        raise ValueError(f"Invalid motor channel: {channel!r}")

    def _normalize_sensory_channels(
        self, channels: Optional[List[Any]]
    ) -> List[SensoryChannel]:
        """Normalize a list of sensory channels, defaulting to all channels."""
        if channels is None:
            return list(SensoryChannel)
        return [self._normalize_sensory_channel(c) for c in channels]

    def _normalize_motor_channels(
        self, channels: Optional[List[Any]]
    ) -> List[MotorChannel]:
        """Normalize a list of motor channels, defaulting to all channels."""
        if channels is None:
            return list(MotorChannel)
        return [self._normalize_motor_channel(c) for c in channels]

    @staticmethod
    def _touch(profile: EmbodimentProfile) -> None:
        """Update the profile timestamp."""
        profile.updated_at = datetime.datetime.now().isoformat()

    # ------------------------------------------------------------------
    # Embodiment lifecycle
    # ------------------------------------------------------------------

    def inhabit(
        self,
        agent_id: str,
        entity_id: str,
        sensory_channels: Optional[List[Any]] = None,
        motor_channels: Optional[List[Any]] = None,
        arbitration_strategy: ArbitrationStrategy = ArbitrationStrategy.PRIORITY,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbodimentProfile:
        """Create an embodiment link between an agent and an entity.

        Args:
            agent_id: Identifier of the agent that will inhabit the entity.
            entity_id: Identifier of the entity to be inhabited.
            sensory_channels: Sensory channels the agent will receive. If
                None, all sensory channels are subscribed.
            motor_channels: Motor channels the agent may act through. If
                None, all motor channels are available.
            arbitration_strategy: Strategy for resolving conflicts when
                multiple agents share the entity.
            priority: Priority of this agent for priority-based arbitration.
            metadata: Optional metadata for the profile.

        Returns:
            The created EmbodimentProfile.
        """
        if not agent_id or not entity_id:
            raise ValueError("agent_id and entity_id are required")

        with self._instance_lock:
            profile = EmbodimentProfile(
                agent_id=agent_id,
                entity_id=entity_id,
                sensory_channels=self._normalize_sensory_channels(sensory_channels),
                motor_channels=self._normalize_motor_channels(motor_channels),
                arbitration_strategy=arbitration_strategy,
                priority=priority,
                state=EmbodimentState.ACTIVE,
                metadata=dict(metadata) if metadata else {},
            )
            self._profiles[profile.id] = profile
            self._stats["total_inhabits"] += 1

            self._emit_event(
                EmbodimentEventKind.INHABIT,
                profile_id=profile.id,
                agent_id=agent_id,
                entity_id=entity_id,
                payload={"priority": priority},
            )
            return profile

    def leave(self, profile_id: str) -> bool:
        """Remove an embodiment link.

        Args:
            profile_id: Identifier of the profile to remove.

        Returns:
            True if the profile was found and removed.
        """
        with self._instance_lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False
            profile.state = EmbodimentState.LEAVING
            del self._profiles[profile_id]
            self._percepts.pop(profile_id, None)
            self._stats["total_leaves"] += 1

            self._emit_event(
                EmbodimentEventKind.LEAVE,
                profile_id=profile_id,
                agent_id=profile.agent_id,
                entity_id=profile.entity_id,
                payload={},
            )
            return True

    def leave_entity(self, entity_id: str) -> int:
        """Remove all embodiment links for an entity.

        Args:
            entity_id: Identifier of the entity whose profiles are removed.

        Returns:
            The number of profiles removed.
        """
        with self._instance_lock:
            target_ids = [
                p.id for p in self._profiles.values() if p.entity_id == entity_id
            ]
            count = 0
            for pid in target_ids:
                if self.leave(pid):
                    count += 1
            return count

    def leave_agent(self, agent_id: str) -> int:
        """Remove all embodiment links for an agent.

        Args:
            agent_id: Identifier of the agent whose profiles are removed.

        Returns:
            The number of profiles removed.
        """
        with self._instance_lock:
            target_ids = [
                p.id for p in self._profiles.values() if p.agent_id == agent_id
            ]
            count = 0
            for pid in target_ids:
                if self.leave(pid):
                    count += 1
            return count

    def get_profile(self, profile_id: str) -> Optional[EmbodimentProfile]:
        """Get an embodiment profile by its id."""
        with self._instance_lock:
            return self._profiles.get(profile_id)

    def list_profiles(
        self,
        agent_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        state: Optional[EmbodimentState] = None,
    ) -> List[EmbodimentProfile]:
        """List embodiment profiles, optionally filtered.

        Args:
            agent_id: Filter by agent identifier.
            entity_id: Filter by entity identifier.
            state: Filter by embodiment state.

        Returns:
            List of matching EmbodimentProfile instances.
        """
        with self._instance_lock:
            results = list(self._profiles.values())
            if agent_id is not None:
                results = [p for p in results if p.agent_id == agent_id]
            if entity_id is not None:
                results = [p for p in results if p.entity_id == entity_id]
            if state is not None:
                results = [p for p in results if p.state == state]
            return results

    def suspend(self, profile_id: str) -> EmbodimentProfile:
        """Suspend an embodiment link.

        Sets the profile state to SUSPENDED, pausing perception delivery
        and action issuance until resumed.

        Args:
            profile_id: Identifier of the profile to suspend.

        Returns:
            The updated EmbodimentProfile.

        Raises:
            KeyError: If the profile does not exist.
        """
        with self._instance_lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                raise KeyError(f"Profile not found: {profile_id}")
            previous = profile.state
            profile.state = EmbodimentState.SUSPENDED
            self._touch(profile)
            self._emit_event(
                EmbodimentEventKind.STATE_CHANGED,
                profile_id=profile_id,
                agent_id=profile.agent_id,
                entity_id=profile.entity_id,
                payload={"from": previous.value, "to": profile.state.value},
            )
            return profile

    def resume(self, profile_id: str) -> EmbodimentProfile:
        """Resume a suspended embodiment link.

        Args:
            profile_id: Identifier of the profile to resume.

        Returns:
            The updated EmbodimentProfile.

        Raises:
            KeyError: If the profile does not exist.
        """
        with self._instance_lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                raise KeyError(f"Profile not found: {profile_id}")
            previous = profile.state
            profile.state = EmbodimentState.ACTIVE
            self._touch(profile)
            self._emit_event(
                EmbodimentEventKind.STATE_CHANGED,
                profile_id=profile_id,
                agent_id=profile.agent_id,
                entity_id=profile.entity_id,
                payload={"from": previous.value, "to": profile.state.value},
            )
            return profile

    # ------------------------------------------------------------------
    # Perception
    # ------------------------------------------------------------------

    def receive_perception(
        self,
        entity_id: str,
        channel: Any,
        data: Dict[str, Any],
        source_entity_id: Optional[str] = None,
        confidence: float = 1.0,
    ) -> List[PerceptSnapshot]:
        """Inject sensory data for an entity.

        Distributes the sensory input to all profiles inhabiting the
        entity that subscribe to the given channel.

        Args:
            entity_id: Entity the perception originates from.
            channel: Sensory channel of the input.
            data: Sensory payload dictionary.
            source_entity_id: Optional source entity identifier.
            confidence: Confidence value between 0.0 and 1.0.

        Returns:
            List of PerceptSnapshot instances delivered to each agent.
        """
        sensory_channel = self._normalize_sensory_channel(channel)
        now_iso = datetime.datetime.now().isoformat()

        with self._instance_lock:
            matching_profiles = [
                p
                for p in self._profiles.values()
                if p.entity_id == entity_id
                and sensory_channel in p.sensory_channels
                and p.state == EmbodimentState.ACTIVE
            ]

            snapshots: List[PerceptSnapshot] = []
            for profile in matching_profiles:
                sensory_input = SensoryInput(
                    channel=sensory_channel,
                    source_entity_id=source_entity_id or "",
                    data=dict(data) if data else {},
                    confidence=confidence,
                    timestamp=now_iso,
                )

                existing = self._percepts.get(profile.id)
                if existing is not None:
                    existing.sensory_inputs.append(sensory_input)
                    existing.aggregated_percept[sensory_channel.value] = (
                        sensory_input.data
                    )
                    existing.timestamp = now_iso
                    snapshot = existing
                else:
                    aggregated = {sensory_channel.value: dict(data) if data else {}}
                    snapshot = PerceptSnapshot(
                        profile_id=profile.id,
                        agent_id=profile.agent_id,
                        entity_id=entity_id,
                        sensory_inputs=[sensory_input],
                        aggregated_percept=aggregated,
                        timestamp=now_iso,
                    )
                    self._percepts[profile.id] = snapshot

                snapshots.append(snapshot)
                self._stats["total_perceptions_received"] += 1

                self._emit_event(
                    EmbodimentEventKind.PERCEPTION_RECEIVED,
                    profile_id=profile.id,
                    agent_id=profile.agent_id,
                    entity_id=entity_id,
                    payload={"channel": sensory_channel.value},
                )

            return snapshots

    def get_perception(self, profile_id: str) -> Optional[PerceptSnapshot]:
        """Get the latest percept for a profile.

        Args:
            profile_id: Identifier of the profile.

        Returns:
            The latest PerceptSnapshot or None if no percept has been
            delivered yet.
        """
        with self._instance_lock:
            return self._percepts.get(profile_id)

    def get_entity_percepts(self, entity_id: str) -> List[PerceptSnapshot]:
        """Get the latest percepts for all agents inhabiting an entity.

        Args:
            entity_id: Identifier of the entity.

        Returns:
            List of PerceptSnapshot instances for the inhabiting agents.
        """
        with self._instance_lock:
            results: List[PerceptSnapshot] = []
            for profile in self._profiles.values():
                if profile.entity_id != entity_id:
                    continue
                percept = self._percepts.get(profile.id)
                if percept is not None:
                    results.append(percept)
            return results

    # ------------------------------------------------------------------
    # Motor actions
    # ------------------------------------------------------------------

    def issue_action(
        self,
        profile_id: str,
        channel: Any,
        action_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        priority: Optional[int] = None,
    ) -> MotorAction:
        """Issue a motor action through an entity.

        If multiple agents inhabit the entity, arbitration may reject or
        modify the action according to the configured strategy.

        Args:
            profile_id: Identifier of the issuing profile.
            channel: Motor channel of the action.
            action_type: Type label of the action.
            parameters: Action parameters dictionary.
            priority: Optional action priority override. Defaults to the
                profile priority.

        Returns:
            The issued MotorAction with its final status set.
        """
        motor_channel = self._normalize_motor_channel(channel)

        with self._instance_lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                raise KeyError(f"Profile not found: {profile_id}")
            if profile.state == EmbodimentState.SUSPENDED:
                raise RuntimeError(f"Profile {profile_id} is suspended")
            if motor_channel not in profile.motor_channels:
                raise ValueError(
                    f"Motor channel {motor_channel.value} not available "
                    f"for profile {profile_id}"
                )

            action_priority = (
                priority if priority is not None else profile.priority
            )
            action = MotorAction(
                channel=motor_channel,
                action_type=action_type,
                parameters=dict(parameters) if parameters else {},
                priority=action_priority,
                issued_by=profile.agent_id,
            )
            self._actions.append(action)
            self._trim_actions()
            self._stats["total_actions_issued"] += 1

            tick_key = (profile.entity_id, motor_channel.value)
            self._tick_actions.setdefault(tick_key, []).append(action)

            self._emit_event(
                EmbodimentEventKind.ACTION_ISSUED,
                profile_id=profile_id,
                agent_id=profile.agent_id,
                entity_id=profile.entity_id,
                payload={
                    "action_id": action.id,
                    "channel": motor_channel.value,
                    "action_type": action_type,
                },
            )

            self._resolve_action(profile, action, tick_key)
            return action

    def _resolve_action(
        self,
        profile: EmbodimentProfile,
        action: MotorAction,
        tick_key: Tuple[str, str],
    ) -> None:
        """Resolve an action, applying arbitration when shared control exists."""
        entity_id = profile.entity_id
        inhabitants = [
            p
            for p in self._profiles.values()
            if p.entity_id == entity_id and action.channel in p.motor_channels
            and p.state != EmbodimentState.SUSPENDED
        ]

        if len(inhabitants) <= 1:
            self._apply_action(entity_id, action)
            return

        competing = [
            a for a in self._tick_actions.get(tick_key, [])
            if a.status == ActionStatus.PENDING
        ]

        if len(competing) < 2:
            action.status = ActionStatus.PENDING
            self._pending_actions.append((entity_id, action))
            return

        winner, rejected = self.arbitrate_actions(
            entity_id, action.channel, competing
        )

        if winner is not None and winner.status != ActionStatus.REJECTED:
            self._apply_action(entity_id, winner)
            self._stats["total_actions_applied"] += 1
        else:
            action.status = ActionStatus.REJECTED

        for rejected_action in rejected:
            rejected_action.status = ActionStatus.REJECTED
            self._stats["total_actions_rejected"] += 1
            self._emit_event(
                EmbodimentEventKind.ACTION_REJECTED,
                profile_id=profile.id,
                agent_id=rejected_action.issued_by,
                entity_id=entity_id,
                payload={
                    "action_id": rejected_action.id,
                    "action_type": rejected_action.action_type,
                },
            )

        self._stats["total_conflicts_detected"] += 1
        self._emit_event(
            EmbodimentEventKind.CONFLICT_DETECTED,
            profile_id=profile.id,
            agent_id=profile.agent_id,
            entity_id=entity_id,
            payload={
                "channel": action.channel.value,
                "competing_count": len(competing),
                "winner": winner.id if winner is not None else None,
            },
        )
        self._emit_event(
            EmbodimentEventKind.ACTION_ARBITRATED,
            profile_id=profile.id,
            agent_id=profile.agent_id,
            entity_id=entity_id,
            payload={
                "channel": action.channel.value,
                "winner": winner.id if winner is not None else None,
                "rejected_count": len(rejected),
            },
        )

    def _apply_action(self, entity_id: str, action: MotorAction) -> None:
        """Apply a motor action through its registered motor supplier."""
        supplier = self._motor_suppliers.get(action.channel)
        success = True
        if supplier is not None:
            try:
                success = bool(supplier(entity_id, action))
            except Exception:
                success = False
        action.status = ActionStatus.APPLIED if success else ActionStatus.REJECTED
        if success:
            self._stats["total_actions_applied"] += 1
        else:
            self._stats["total_actions_rejected"] += 1

    # ------------------------------------------------------------------
    # Arbitration
    # ------------------------------------------------------------------

    def arbitrate_actions(
        self,
        entity_id: str,
        channel: Any,
        actions: List[MotorAction],
    ) -> Tuple[MotorAction, List[MotorAction]]:
        """Resolve conflicting actions for an entity and channel.

        Args:
            entity_id: Entity the actions target.
            channel: Motor channel of the conflict.
            actions: List of competing MotorAction instances.

        Returns:
            A tuple of (winning_action, rejected_actions). When no winner
            can be determined (e.g. voting without a majority), the winner
            is the first action and is also included in the rejected list.
        """
        motor_channel = self._normalize_motor_channel(channel)

        with self._instance_lock:
            if not actions:
                raise ValueError("No actions to arbitrate")

            strategy = self._resolve_strategy(entity_id, motor_channel)
            winner, rejected = self._run_arbitration(
                entity_id, motor_channel, strategy, list(actions)
            )
            return winner, rejected

    def _resolve_strategy(
        self, entity_id: str, channel: MotorChannel
    ) -> ArbitrationStrategy:
        """Determine the arbitration strategy for an entity and channel."""
        for profile in self._profiles.values():
            if (
                profile.entity_id == entity_id
                and channel in profile.motor_channels
                and profile.state != EmbodimentState.SUSPENDED
            ):
                return profile.arbitration_strategy
        return ArbitrationStrategy.PRIORITY

    def _profile_priority(self, agent_id: str, entity_id: str) -> int:
        """Return the priority of the profile for an agent on an entity."""
        for profile in self._profiles.values():
            if (
                profile.agent_id == agent_id
                and profile.entity_id == entity_id
            ):
                return profile.priority
        return 0

    def _run_arbitration(
        self,
        entity_id: str,
        channel: MotorChannel,
        strategy: ArbitrationStrategy,
        actions: List[MotorAction],
    ) -> Tuple[MotorAction, List[MotorAction]]:
        """Execute a single arbitration strategy over the competing actions."""
        tick_key = (entity_id, channel.value)

        if strategy == ArbitrationStrategy.PRIORITY:
            winner = max(
                actions,
                key=lambda a: (
                    self._profile_priority(a.issued_by, entity_id),
                    a.priority,
                ),
            )
            rejected = [a for a in actions if a.id != winner.id]
            return winner, rejected

        if strategy == ArbitrationStrategy.VOTING:
            type_counts: Dict[str, int] = {}
            for a in actions:
                type_counts[a.action_type] = (
                    type_counts.get(a.action_type, 0) + 1
                )
            majority_type, majority_count = max(
                type_counts.items(), key=lambda kv: kv[1]
            )
            if majority_count > len(actions) / 2:
                winner = next(
                    a for a in actions if a.action_type == majority_type
                )
                rejected = [a for a in actions if a.id != winner.id]
                return winner, rejected
            return actions[0], list(actions)

        if strategy == ArbitrationStrategy.AVERAGE:
            numeric_values: List[float] = []
            for a in actions:
                value = a.parameters.get("value")
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    numeric_values.append(float(value))
            if numeric_values:
                averaged = sum(numeric_values) / len(numeric_values)
                winner = actions[0]
                winner.parameters = dict(winner.parameters)
                winner.parameters["value"] = averaged
                rejected = [a for a in actions if a.id != winner.id]
                return winner, rejected
            return self._run_arbitration(
                entity_id, channel, ArbitrationStrategy.PRIORITY, actions
            )

        if strategy == ArbitrationStrategy.LAST_WRITER:
            winner = max(actions, key=lambda a: a.timestamp)
            rejected = [a for a in actions if a.id != winner.id]
            return winner, rejected

        if strategy == ArbitrationStrategy.FIRST_WRITER:
            winner = min(actions, key=lambda a: a.timestamp)
            rejected = [a for a in actions if a.id != winner.id]
            return winner, rejected

        if strategy == ArbitrationStrategy.ROUND_ROBIN:
            agent_order: List[str] = []
            seen = set()
            for a in actions:
                if a.issued_by not in seen:
                    seen.add(a.issued_by)
                    agent_order.append(a.issued_by)
            if not agent_order:
                return actions[0], list(actions[1:])
            index = self._round_robin_index.get(tick_key, 0) % len(agent_order)
            chosen_agent = agent_order[index]
            self._round_robin_index[tick_key] = (index + 1) % len(agent_order)
            winner = next(a for a in actions if a.issued_by == chosen_agent)
            rejected = [a for a in actions if a.id != winner.id]
            return winner, rejected

        winner = max(actions, key=lambda a: a.priority)
        rejected = [a for a in actions if a.id != winner.id]
        return winner, rejected

    # ------------------------------------------------------------------
    # Suppliers
    # ------------------------------------------------------------------

    def register_sensory_supplier(
        self,
        channel: Any,
        supplier: Callable[[str], Dict[str, Any]],
    ) -> None:
        """Register a callback that provides sensory data for a channel.

        Args:
            channel: Sensory channel the supplier serves.
            supplier: Callable accepting an entity id and returning a data
                dictionary.
        """
        sensory_channel = self._normalize_sensory_channel(channel)
        with self._instance_lock:
            self._sensory_suppliers[sensory_channel] = supplier

    def register_motor_supplier(
        self,
        channel: Any,
        supplier: Callable[[str, MotorAction], bool],
    ) -> None:
        """Register a callback that executes motor actions for a channel.

        Args:
            channel: Motor channel the supplier serves.
            supplier: Callable accepting an entity id and a MotorAction,
                returning True on success.
        """
        motor_channel = self._normalize_motor_channel(channel)
        with self._instance_lock:
            self._motor_suppliers[motor_channel] = supplier

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        """Advance the embodiment clock by one tick.

        Triggers registered sensory suppliers to deliver percepts for each
        active profile, then processes any pending motor actions through
        their motor suppliers.

        Returns:
            A summary dictionary describing the tick outcome.
        """
        with self._instance_lock:
            perceptions_delivered = 0
            suppliers_invoked = 0

            entity_channels: Dict[str, set] = {}
            for profile in self._profiles.values():
                if profile.state != EmbodimentState.ACTIVE:
                    continue
                channel_set = entity_channels.setdefault(profile.entity_id, set())
                for channel in profile.sensory_channels:
                    if channel in self._sensory_suppliers:
                        channel_set.add(channel)

            for entity_id, channels in entity_channels.items():
                for channel in channels:
                    supplier = self._sensory_suppliers.get(channel)
                    if supplier is None:
                        continue
                    try:
                        data = supplier(entity_id) or {}
                    except Exception:
                        data = {}
                    suppliers_invoked += 1
                    delivered = self.receive_perception(
                        entity_id, channel, data
                    )
                    perceptions_delivered += len(delivered)

            actions_applied = 0
            actions_rejected = 0
            for entity_id, action in list(self._pending_actions):
                if action.status != ActionStatus.PENDING:
                    continue
                self._apply_action(entity_id, action)
                if action.status == ActionStatus.APPLIED:
                    actions_applied += 1
                else:
                    actions_rejected += 1
            self._pending_actions.clear()

            self._tick_actions.clear()
            self._tick_count += 1
            self._stats["total_ticks"] += 1

            return {
                "tick": self._tick_count,
                "suppliers_invoked": suppliers_invoked,
                "perceptions_delivered": perceptions_delivered,
                "actions_applied": actions_applied,
                "actions_rejected": actions_rejected,
            }

    # ------------------------------------------------------------------
    # Actions query
    # ------------------------------------------------------------------

    def list_actions(
        self,
        profile_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MotorAction]:
        """List motor actions, optionally filtered.

        Args:
            profile_id: Filter by issuing profile.
            entity_id: Filter by target entity.
            limit: Maximum number of actions to return.

        Returns:
            List of MotorAction instances, most recent first.
        """
        with self._instance_lock:
            results = list(self._actions)
            if profile_id is not None:
                profile = self._profiles.get(profile_id)
                if profile is None:
                    return []
                results = [a for a in results if a.issued_by == profile.agent_id]
            if entity_id is not None:
                agent_ids = {
                    p.agent_id
                    for p in self._profiles.values()
                    if p.entity_id == entity_id
                }
                results = [a for a in results if a.issued_by in agent_ids]
            results.reverse()
            return results[:limit]

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        kind: EmbodimentEventKind,
        handler: Callable[[EmbodimentEvent], None],
    ) -> None:
        """Subscribe to embodiment events of a given kind.

        Args:
            kind: Event kind to subscribe to.
            handler: Callable invoked with each matching EmbodimentEvent.
        """
        with self._instance_lock:
            self._event_handlers.setdefault(kind, []).append(handler)

    def list_events(self, limit: int = 100) -> List[EmbodimentEvent]:
        """Return recent embodiment events.

        Args:
            limit: Maximum number of events to return.

        Returns:
            List of EmbodimentEvent instances, most recent first.
        """
        with self._instance_lock:
            results = list(self._events)
            results.reverse()
            return results[:limit]

    def _emit_event(
        self,
        kind: EmbodimentEventKind,
        profile_id: str = "",
        agent_id: str = "",
        entity_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> EmbodimentEvent:
        """Create, store, and dispatch an embodiment event."""
        event = EmbodimentEvent(
            kind=kind,
            profile_id=profile_id,
            agent_id=agent_id,
            entity_id=entity_id,
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        self._trim_events()
        handlers = list(self._event_handlers.get(kind, []))
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                continue
        return event

    # ------------------------------------------------------------------
    # Status and snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return the current status and statistics of the engine."""
        with self._instance_lock:
            active_profiles = sum(
                1
                for p in self._profiles.values()
                if p.state == EmbodimentState.ACTIVE
            )
            return {
                "profiles": len(self._profiles),
                "active_profiles": active_profiles,
                "pending_actions": len(self._pending_actions),
                "events_stored": len(self._events),
                "actions_stored": len(self._actions),
                "percepts_stored": len(self._percepts),
                "tick_count": self._tick_count,
                "sensory_suppliers": [
                    c.value for c in self._sensory_suppliers.keys()
                ],
                "motor_suppliers": [
                    c.value for c in self._motor_suppliers.keys()
                ],
                **dict(self._stats),
            }

    def get_snapshot(self) -> EmbodimentSnapshot:
        """Return a point-in-time snapshot of the engine state."""
        with self._instance_lock:
            active_profiles = sum(
                1
                for p in self._profiles.values()
                if p.state == EmbodimentState.ACTIVE
            )
            return EmbodimentSnapshot(
                profile_count=len(self._profiles),
                active_profile_count=active_profiles,
                total_perceptions=self._stats["total_perceptions_received"],
                total_actions=self._stats["total_actions_issued"],
                stats=dict(self._stats),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all embodiment data to the initial state.

        Clears profiles, percepts, actions, events, tick state, and
        statistics. Re-registers default suppliers.
        """
        with self._instance_lock:
            self._profiles.clear()
            self._percepts.clear()
            self._actions.clear()
            self._tick_actions.clear()
            self._pending_actions.clear()
            self._events.clear()
            self._event_handlers.clear()
            self._round_robin_index.clear()
            self._tick_count = 0
            self._stats = {
                "total_inhabits": 0,
                "total_leaves": 0,
                "total_perceptions_received": 0,
                "total_actions_issued": 0,
                "total_actions_applied": 0,
                "total_actions_rejected": 0,
                "total_conflicts_detected": 0,
                "total_ticks": 0,
            }
            self._sensory_suppliers.clear()
            self._motor_suppliers.clear()
            self._register_default_suppliers()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _trim_events(self) -> None:
        """Trim the event history to the configured maximum."""
        while len(self._events) > _MAX_EVENTS:
            self._events.pop(0)

    def _trim_actions(self) -> None:
        """Trim the action log to the configured maximum."""
        while len(self._actions) > _MAX_ACTIONS:
            self._actions.pop(0)

    def _trim_percepts(self) -> None:
        """Trim the percept cache to the configured maximum."""
        while len(self._percepts) > _MAX_PERCEPTS:
            oldest_id = next(iter(self._percepts))
            self._percepts.pop(oldest_id, None)


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_embodiment_engine() -> AgentEmbodimentEngine:
    """Return the singleton AgentEmbodimentEngine instance.

    This is the primary access point for the embodiment engine
    throughout the SparkLabs ecosystem.

    Returns:
        The singleton AgentEmbodimentEngine.
    """
    return AgentEmbodimentEngine.get_instance()
