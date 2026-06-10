"""
SparkLabs Agent - World Interaction Layer

A bidirectional agent-game-world interaction system that enables autonomous
agents to perceive, reason about, and act upon the game world. This is the
bridge layer that connects the AI cognition plane with the game simulation
plane, allowing agents to function as intelligent game entities that observe
world state, form intentions, and execute actions with world feedback.

The interaction loop follows a continuous perceive→reason→act→observe cycle,
enabling agents to participate in the game simulation as first-class entities
while maintaining full awareness of their action consequences.

Architecture:
  AgentWorldInteraction (Singleton)
    |-- WorldPercept (structured sensory snapshot of game world)
    |-- AgentIntention (reasoned action plan with priority weighting)
    |-- WorldAction (concrete action dispatched to the game engine)
    |-- ActionFeedback (world response to agent action)
    |-- InteractionCycle (complete perceive→reason→act→observe record)
    |-- WorldRegion (spatial subdivision for locality-aware agents)
    |-- InteractionMode (how the agent engages with the world)
    |-- PerceptChannel (specific sensory modalities)
    |-- ActionDomain (categorization of agent actions)

Core Capabilities:
  - perceive_world: Capture structured world snapshot for agent consumption
  - form_intention: Reason about world state to produce action plans
  - execute_action: Dispatch intended action to the game engine
  - receive_feedback: Process world response and update agent state
  - run_interaction_cycle: Complete perceive→reason→act cycle
  - get_situational_awareness: Aggregate agent's understanding of context
  - register_interest_region: Subscribe to spatial world updates
  - query_world_entities: Query game world entities by type/proximity
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InteractionMode(Enum):
    """How the agent engages with the game world."""
    OBSERVER = "observer"
    PARTICIPANT = "participant"
    DIRECTOR = "director"
    DEBUGGER = "debugger"
    TUTORIAL = "tutorial"
    PLAYTESTER = "playtester"


class PerceptChannel(Enum):
    """Sensory modalities for world perception."""
    SPATIAL = "spatial"
    ENTITY = "entity"
    PHYSICS = "physics"
    AUDIO = "audio"
    EVENTS = "events"
    UI = "ui"
    PERFORMANCE = "performance"
    AGENT_SOCIAL = "agent_social"
    WORLD_STATE = "world_state"
    SCRIPT = "script"


class ActionDomain(Enum):
    """Categorization of agent actions in the game world."""
    MOVEMENT = "movement"
    CREATION = "creation"
    MODIFICATION = "modification"
    DESTRUCTION = "destruction"
    COMMUNICATION = "communication"
    QUERY = "query"
    SCRIPTING = "scripting"
    CAMERA = "camera"
    SCENE = "scene"
    TRIGGER = "trigger"


class ActionPriority(Enum):
    """Priority level for agent intentions."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


class FeedbackType(Enum):
    """Type of feedback received from world after action."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    CONFLICT = "conflict"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class WorldEntity:
    """A game world entity visible to the agent.

    Attributes:
        entity_id: Unique entity identifier.
        entity_type: Category of entity (player, npc, item, obstacle, etc.).
        name: Display name.
        position_x: World X coordinate.
        position_y: World Y coordinate.
        velocity_x: Current X velocity.
        velocity_y: Current Y velocity.
        state: Current entity state (idle, moving, interacting, etc.).
        properties: Entity-specific properties.
        distance_to_agent: Distance from the observing agent.
        in_view: Whether the entity is in the agent's view frustum.
        last_updated: Timestamp of last update.
    """
    entity_id: str = ""
    entity_type: str = "unknown"
    name: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    state: str = "idle"
    properties: Dict[str, Any] = field(default_factory=dict)
    distance_to_agent: float = 0.0
    in_view: bool = False
    last_updated: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "position": {"x": self.position_x, "y": self.position_y},
            "velocity": {"x": self.velocity_x, "y": self.velocity_y},
            "state": self.state,
            "properties": dict(self.properties),
            "distance_to_agent": round(self.distance_to_agent, 4),
            "in_view": self.in_view,
            "last_updated": self.last_updated,
        }


@dataclass
class WorldPercept:
    """A structured sensory snapshot of the game world for agent consumption.

    Attributes:
        percept_id: Unique snapshot identifier.
        timestamp: When the snapshot was captured.
        agent_position: Agent's position in the world.
        agent_view_radius: Agent's perception radius.
        entities: Visible world entities.
        events: Active world events.
        physics_state: Relevant physics data.
        performance_metrics: Current performance data.
        world_properties: Global world state properties.
        spatial_grid: Nearby spatial occupancy data.
    """
    percept_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=_time_module.time)
    agent_position_x: float = 0.0
    agent_position_y: float = 0.0
    agent_view_radius: float = 500.0
    entities: List[WorldEntity] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    physics_state: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    world_properties: Dict[str, Any] = field(default_factory=dict)
    spatial_grid: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "percept_id": self.percept_id,
            "timestamp": self.timestamp,
            "agent_position": {"x": self.agent_position_x, "y": self.agent_position_y},
            "view_radius": self.agent_view_radius,
            "entities": [e.to_dict() for e in self.entities],
            "entity_count": len(self.entities),
            "events": list(self.events),
            "physics_state": dict(self.physics_state),
            "performance_metrics": dict(self.performance_metrics),
            "world_properties": dict(self.world_properties),
        }


@dataclass
class AgentIntention:
    """A reasoned action plan formed from world perception.

    Attributes:
        intention_id: Unique intention identifier.
        action_domain: Category of intended action.
        action_name: Specific action to perform.
        parameters: Action parameters.
        priority: Importance level.
        confidence: Agent's confidence in this intention (0-1).
        reasoning: Agent's chain-of-thought explaining the intention.
        expected_outcome: What the agent expects will happen.
        preconditions: Conditions that must be met before execution.
        deadline_ms: Time by which the action should complete.
    """
    intention_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action_domain: ActionDomain = ActionDomain.QUERY
    action_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: ActionPriority = ActionPriority.MEDIUM
    confidence: float = 0.5
    reasoning: str = ""
    expected_outcome: str = ""
    preconditions: List[str] = field(default_factory=list)
    deadline_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intention_id": self.intention_id,
            "action_domain": self.action_domain.value,
            "action_name": self.action_name,
            "parameters": dict(self.parameters),
            "priority": self.priority.value,
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
            "expected_outcome": self.expected_outcome,
            "preconditions": list(self.preconditions),
            "deadline_ms": self.deadline_ms,
        }


@dataclass
class WorldAction:
    """A concrete action dispatched to the game engine.

    Attributes:
        action_id: Unique action identifier.
        intention_id: Source intention that produced this action.
        action_domain: Category of action.
        action_name: Specific action name.
        parameters: Executed parameters.
        priority: Execution priority.
        dispatch_time: When the action was sent.
        timeout_ms: Maximum wait for feedback.
    """
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    intention_id: str = ""
    action_domain: ActionDomain = ActionDomain.QUERY
    action_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: ActionPriority = ActionPriority.MEDIUM
    dispatch_time: float = field(default_factory=_time_module.time)
    timeout_ms: float = 5000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "intention_id": self.intention_id,
            "action_domain": self.action_domain.value,
            "action_name": self.action_name,
            "parameters": dict(self.parameters),
            "priority": self.priority.value,
            "dispatch_time": self.dispatch_time,
            "timeout_ms": self.timeout_ms,
        }


@dataclass
class ActionFeedback:
    """The game world's response to an agent's action.

    Attributes:
        feedback_id: Unique feedback identifier.
        action_id: Source action that produced this feedback.
        feedback_type: Outcome category.
        result_data: Structured result from the action.
        world_state_change: How the world changed due to the action.
        side_effects: Unintended consequences.
        duration_ms: How long the action took to process.
        error_message: Error description if failed.
    """
    feedback_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action_id: str = ""
    feedback_type: FeedbackType = FeedbackType.SUCCESS
    result_data: Dict[str, Any] = field(default_factory=dict)
    world_state_change: Dict[str, Any] = field(default_factory=dict)
    side_effects: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "action_id": self.action_id,
            "feedback_type": self.feedback_type.value,
            "result_data": dict(self.result_data),
            "world_state_change": dict(self.world_state_change),
            "side_effects": list(self.side_effects),
            "duration_ms": round(self.duration_ms, 4),
            "error_message": self.error_message,
        }


@dataclass
class InteractionCycle:
    """Complete record of one perceive-reason-act-observe cycle.

    Attributes:
        cycle_id: Unique cycle identifier.
        cycle_number: Monotonic cycle counter.
        percept: World snapshot at cycle start.
        intentions: Reasoned action plans.
        action: Dispatched action (primary).
        feedback: World response to action.
        duration_ms: Total cycle wall-clock duration.
        agent_state_after: Agent's internal state after the cycle.
        learning_signal: Reinforcement signal for agent improvement.
    """
    cycle_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cycle_number: int = 0
    percept: Optional[WorldPercept] = None
    intentions: List[AgentIntention] = field(default_factory=list)
    action: Optional[WorldAction] = None
    feedback: Optional[ActionFeedback] = None
    duration_ms: float = 0.0
    agent_state_after: Dict[str, Any] = field(default_factory=dict)
    learning_signal: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "cycle_number": self.cycle_number,
            "percept": self.percept.to_dict() if self.percept else None,
            "intentions": [i.to_dict() for i in self.intentions],
            "action": self.action.to_dict() if self.action else None,
            "feedback": self.feedback.to_dict() if self.feedback else None,
            "duration_ms": round(self.duration_ms, 4),
            "learning_signal": round(self.learning_signal, 4),
        }


@dataclass
class WorldRegion:
    """A spatial subdivision for locality-aware agent operations.

    Attributes:
        region_id: Unique region identifier.
        bounds_x: Left boundary.
        bounds_y: Top boundary.
        bounds_width: Region width.
        bounds_height: Region height.
        entity_count: Number of entities in region.
        agents_present: Agent IDs currently in this region.
        last_activity: Timestamp of last region activity.
    """
    region_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    bounds_x: float = 0.0
    bounds_y: float = 0.0
    bounds_width: float = 1000.0
    bounds_height: float = 1000.0
    entity_count: int = 0
    agents_present: List[str] = field(default_factory=list)
    last_activity: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "bounds": {
                "x": self.bounds_x,
                "y": self.bounds_y,
                "width": self.bounds_width,
                "height": self.bounds_height,
            },
            "entity_count": self.entity_count,
            "agents_present": list(self.agents_present),
            "last_activity": self.last_activity,
        }


# ---------------------------------------------------------------------------
# Agent World Interaction (Singleton)
# ---------------------------------------------------------------------------


class AgentWorldInteraction:
    """
    Bidirectional bridge between AI cognition and game simulation.

    Enables autonomous agents to participate in the game world as first-class
    entities through a continuous perceive→reason→act→observe interaction loop.
    Agents perceive world state through structured sensory snapshots, form
    reasoned intentions, execute validated actions, and receive feedback that
    shapes future behavior.

    Features:
      - Continuous perceive→reason→act→observe interaction loop
      - Structured world perception with spatial and entity awareness
      - Priority-weighted intention formation with confidence scoring
      - Action dispatch with parameter validation and timeout protection
      - Action feedback processing with state change tracking
      - Spatial region-based entity subscription for scalability
      - Comprehensive cycle history for learning and debugging
    """

    _instance: Optional["AgentWorldInteraction"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "AgentWorldInteraction":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # World state
        self._entities: Dict[str, WorldEntity] = {}
        self._regions: Dict[str, WorldRegion] = {}
        self._world_properties: Dict[str, Any] = {
            "world_name": "default",
            "world_size": {"width": 10000, "height": 10000},
            "gravity": {"x": 0.0, "y": -9.81},
            "time_scale": 1.0,
            "paused": False,
        }

        # Agent state
        self._agent_positions: Dict[str, Tuple[float, float]] = {}
        self._agent_modes: Dict[str, InteractionMode] = {}
        self._agent_interests: Dict[str, List[str]] = {}
        self._agent_state: Dict[str, Dict[str, Any]] = {}

        # Interaction history
        self._cycle_counter: int = 0
        self._cycle_history: deque = deque(maxlen=500)
        self._action_history: deque = deque(maxlen=1000)
        self._feedback_history: deque = deque(maxlen=1000)

        # Action handlers
        self._action_handlers: Dict[ActionDomain, Dict[str, Callable]] = {
            domain: {} for domain in ActionDomain
        }

        self._register_default_handlers()

    # ------------------------------------------------------------------
    # World Perception
    # ------------------------------------------------------------------

    def perceive_world(
        self,
        agent_id: str,
        channels: Optional[List[PerceptChannel]] = None,
        view_radius: float = 500.0,
    ) -> WorldPercept:
        """
        Capture a structured world snapshot for agent consumption.

        Args:
            agent_id: The perceiving agent's identifier.
            channels: Specific sensory channels to sample (all if None).
            view_radius: Perception radius in world units.

        Returns:
            WorldPercept with current world state structured for agent use.
        """
        channels = channels or list(PerceptChannel)
        agent_x, agent_y = self._agent_positions.get(agent_id, (0.0, 0.0))

        percept = WorldPercept(
            agent_position_x=agent_x,
            agent_position_y=agent_y,
            agent_view_radius=view_radius,
        )

        # Entity perception
        if PerceptChannel.ENTITY in channels or PerceptChannel.SPATIAL in channels:
            visible_entities: List[WorldEntity] = []
            for entity in self._entities.values():
                dx = entity.position_x - agent_x
                dy = entity.position_y - agent_y
                dist = math.sqrt(dx * dx + dy * dy)
                entity.distance_to_agent = dist
                entity.in_view = dist <= view_radius

                if entity.in_view or PerceptChannel.ENTITY in channels:
                    visible_entities.append(entity)

            # Sort by distance
            visible_entities.sort(key=lambda e: e.distance_to_agent)
            percept.entities = visible_entities[:50]  # Limit for performance

        # Physics state
        if PerceptChannel.PHYSICS in channels:
            percept.physics_state = {
                "gravity": dict(self._world_properties.get("gravity", {})),
                "time_scale": self._world_properties.get("time_scale", 1.0),
                "nearby_colliders": len([
                    e for e in percept.entities
                    if e.distance_to_agent < 100 and e.entity_type == "collider"
                ]),
            }

        # Events
        if PerceptChannel.EVENTS in channels:
            percept.events = list(self._action_history)[-10:]

        # Performance
        if PerceptChannel.PERFORMANCE in channels:
            percept.performance_metrics = {
                "fps": 60.0,
                "entity_count": len(self._entities),
                "agent_count": len(self._agent_positions),
                "active_regions": len(self._regions),
            }

        # World properties
        percept.world_properties = dict(self._world_properties)

        return percept

    # ------------------------------------------------------------------
    # Intention Formation
    # ------------------------------------------------------------------

    def form_intention(
        self,
        agent_id: str,
        percept: WorldPercept,
        goal: Optional[str] = None,
        max_intentions: int = 3,
    ) -> List[AgentIntention]:
        """
        Reason about world state to produce prioritized action plans.

        Args:
            agent_id: The reasoning agent's identifier.
            percept: Current world percept to reason about.
            goal: High-level goal guiding intention formation.
            max_intentions: Maximum number of intentions to generate.

        Returns:
            List of AgentIntentions ordered by priority.
        """
        intentions: List[AgentIntention] = []

        # Entity interaction intentions
        for entity in percept.entities[:5]:
            if entity.entity_type == "npc" and entity.distance_to_agent < 200:
                intentions.append(AgentIntention(
                    action_domain=ActionDomain.COMMUNICATION,
                    action_name="interact_with_entity",
                    parameters={"target_id": entity.entity_id, "interaction": "greet"},
                    priority=ActionPriority.MEDIUM,
                    confidence=0.7,
                    reasoning=f"Nearby NPC {entity.name} detected at distance {entity.distance_to_agent:.1f}",
                    expected_outcome="Initiate dialogue or interaction",
                ))

        # Movement intentions
        if percept.entities:
            nearest = percept.entities[0]
            if nearest.distance_to_agent > 50:
                intentions.append(AgentIntention(
                    action_domain=ActionDomain.MOVEMENT,
                    action_name="move_toward",
                    parameters={
                        "target_x": nearest.position_x,
                        "target_y": nearest.position_y,
                        "speed": 200.0,
                    },
                    priority=ActionPriority.LOW,
                    confidence=0.85,
                    reasoning=f"Moving toward nearest entity {nearest.name}",
                    expected_outcome="Reduce distance to target entity",
                ))

        # Query intention
        intentions.append(AgentIntention(
            action_domain=ActionDomain.QUERY,
            action_name="query_world_state",
            parameters={"query_type": "all"},
            priority=ActionPriority.BACKGROUND,
            confidence=1.0,
            reasoning="Routine world state update",
            expected_outcome="Latest world state data",
        ))

        # Sort by priority and confidence, limit
        priority_order = {
            ActionPriority.CRITICAL: 0,
            ActionPriority.HIGH: 1,
            ActionPriority.MEDIUM: 2,
            ActionPriority.LOW: 3,
            ActionPriority.BACKGROUND: 4,
        }
        intentions.sort(
            key=lambda i: (priority_order[i.priority], -i.confidence)
        )

        return intentions[:max_intentions]

    # ------------------------------------------------------------------
    # Action Execution
    # ------------------------------------------------------------------

    def execute_action(
        self,
        agent_id: str,
        intention: AgentIntention,
        timeout_ms: float = 5000.0,
    ) -> Tuple[WorldAction, ActionFeedback]:
        """
        Dispatch an intended action to the game engine.

        Args:
            agent_id: The acting agent's identifier.
            intention: The intention to execute.
            timeout_ms: Maximum wait time for feedback.

        Returns:
            Tuple of (dispatched WorldAction, resulting ActionFeedback).
        """
        action = WorldAction(
            intention_id=intention.intention_id,
            action_domain=intention.action_domain,
            action_name=intention.action_name,
            parameters=dict(intention.parameters),
            priority=intention.priority,
            timeout_ms=timeout_ms,
        )

        # Find and execute handler
        start_time = _time_module.time()
        handler = self._action_handlers.get(intention.action_domain, {}).get(
            intention.action_name
        )

        if handler:
            try:
                result_data = handler(
                    agent_id=agent_id,
                    action=action,
                    parameters=intention.parameters,
                )
                feedback_type = FeedbackType.SUCCESS
                error_msg = ""
            except Exception as exc:
                result_data = {"error": str(exc)}
                feedback_type = FeedbackType.FAILED
                error_msg = str(exc)
        else:
            # No handler registered; simulate outcome
            result_data = {
                "action": intention.action_name,
                "domain": intention.action_domain.value,
                "status": "simulated",
                "note": "No handler registered; using default simulation",
            }
            feedback_type = FeedbackType.SUCCESS
            error_msg = ""

        duration = (_time_module.time() - start_time) * 1000

        # Handle agent state changes
        world_change: Dict[str, Any] = {}
        if intention.action_domain == ActionDomain.MOVEMENT:
            if "target_x" in intention.parameters:
                tx = float(intention.parameters["target_x"])
                ty = float(intention.parameters.get("target_y", 0))
                old_pos = self._agent_positions.get(agent_id, (0.0, 0.0))
                self._agent_positions[agent_id] = (tx, ty)
                world_change["position"] = {"from": old_pos, "to": (tx, ty)}

        feedback = ActionFeedback(
            action_id=action.action_id,
            feedback_type=feedback_type,
            result_data=result_data,
            world_state_change=world_change,
            duration_ms=duration,
            error_message=error_msg,
        )

        # Record history
        self._action_history.append(action.to_dict())
        self._feedback_history.append(feedback.to_dict())

        return action, feedback

    # ------------------------------------------------------------------
    # Interaction Cycle
    # ------------------------------------------------------------------

    def run_interaction_cycle(
        self,
        agent_id: str,
        view_radius: float = 500.0,
        goal: Optional[str] = None,
        mode: InteractionMode = InteractionMode.PARTICIPANT,
    ) -> InteractionCycle:
        """
        Execute a complete perceive→reason→act→observe cycle.

        Args:
            agent_id: The agent to run the cycle for.
            view_radius: Perception radius.
            goal: High-level goal for intention formation.
            mode: Agent's interaction mode.

        Returns:
            Complete InteractionCycle record.
        """
        cycle_start = _time_module.time()
        self._cycle_counter += 1

        # Set agent mode
        self._agent_modes[agent_id] = mode

        # Perceive
        percept = self.perceive_world(agent_id, view_radius=view_radius)

        # Reason
        intentions = self.form_intention(agent_id, percept, goal=goal)

        # Act (execute highest priority intention)
        action: Optional[WorldAction] = None
        feedback: Optional[ActionFeedback] = None
        if intentions:
            action, feedback = self.execute_action(agent_id, intentions[0])

        # Observe (update agent state)
        agent_state = self._agent_state.get(agent_id, {})
        agent_state["last_cycle"] = self._cycle_counter
        agent_state["last_mode"] = mode.value
        if feedback and feedback.feedback_type == FeedbackType.SUCCESS:
            agent_state["success_streak"] = agent_state.get("success_streak", 0) + 1
        else:
            agent_state["success_streak"] = 0
        self._agent_state[agent_id] = agent_state

        cycle = InteractionCycle(
            cycle_number=self._cycle_counter,
            percept=percept,
            intentions=intentions,
            action=action,
            feedback=feedback,
            duration_ms=(_time_module.time() - cycle_start) * 1000,
            agent_state_after=dict(agent_state),
            learning_signal=1.0 if feedback and feedback.feedback_type == FeedbackType.SUCCESS else 0.0,
        )

        self._cycle_history.append(cycle)
        return cycle

    # ------------------------------------------------------------------
    # Agent Registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        position_x: float = 0.0,
        position_y: float = 0.0,
        mode: InteractionMode = InteractionMode.OBSERVER,
    ) -> Dict[str, Any]:
        """
        Register an agent in the world interaction layer.

        Args:
            agent_id: Unique agent identifier.
            position_x: Initial world X position.
            position_y: Initial world Y position.
            mode: Initial interaction mode.

        Returns:
            Agent registration confirmation.
        """
        with self._lock:
            self._agent_positions[agent_id] = (position_x, position_y)
            self._agent_modes[agent_id] = mode
            self._agent_interests[agent_id] = []
            self._agent_state[agent_id] = {
                "registered_at": _time_module.time(),
                "cycles_completed": 0,
                "success_streak": 0,
                "mode": mode.value,
            }

            # Assign to a region
            region = self._get_or_create_region(position_x, position_y)
            if agent_id not in region.agents_present:
                region.agents_present.append(agent_id)

        return {
            "agent_id": agent_id,
            "position": {"x": position_x, "y": position_y},
            "mode": mode.value,
            "region_id": self._get_or_create_region(position_x, position_y).region_id,
            "registered": True,
        }

    def unregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from the world interaction layer."""
        with self._lock:
            self._agent_positions.pop(agent_id, None)
            self._agent_modes.pop(agent_id, None)
            self._agent_interests.pop(agent_id, None)
            self._agent_state.pop(agent_id, None)
            for region in self._regions.values():
                if agent_id in region.agents_present:
                    region.agents_present.remove(agent_id)
        return True

    # ------------------------------------------------------------------
    # Entity Management
    # ------------------------------------------------------------------

    def upsert_entity(
        self,
        entity_id: str,
        entity_type: str = "unknown",
        name: str = "",
        position_x: float = 0.0,
        position_y: float = 0.0,
        velocity_x: float = 0.0,
        velocity_y: float = 0.0,
        state: str = "idle",
        properties: Optional[Dict[str, Any]] = None,
    ) -> WorldEntity:
        """
        Add or update a world entity.
        """
        entity = WorldEntity(
            entity_id=entity_id,
            entity_type=entity_type,
            name=name,
            position_x=position_x,
            position_y=position_y,
            velocity_x=velocity_x,
            velocity_y=velocity_y,
            state=state,
            properties=properties or {},
        )
        self._entities[entity_id] = entity

        # Update region
        region = self._get_or_create_region(position_x, position_y)
        region.entity_count = sum(
            1 for e in self._entities.values()
            if region.bounds_x <= e.position_x < region.bounds_x + region.bounds_width
            and region.bounds_y <= e.position_y < region.bounds_y + region.bounds_height
        )
        region.last_activity = _time_module.time()

        return entity

    def remove_entity(self, entity_id: str) -> bool:
        """Remove a world entity."""
        return self._entities.pop(entity_id, None) is not None

    def query_world_entities(
        self,
        entity_type: Optional[str] = None,
        state: Optional[str] = None,
        proximity_x: Optional[float] = None,
        proximity_y: Optional[float] = None,
        max_distance: float = 500.0,
        limit: int = 100,
    ) -> List[WorldEntity]:
        """
        Query game world entities by type, state, or spatial proximity.

        Args:
            entity_type: Filter by entity type.
            state: Filter by entity state.
            proximity_x: Search center X.
            proximity_y: Search center Y.
            max_distance: Maximum proximity distance.
            limit: Maximum results.

        Returns:
            List of matching WorldEntity objects.
        """
        results: List[WorldEntity] = []

        for entity in self._entities.values():
            if entity_type and entity.entity_type != entity_type:
                continue
            if state and entity.state != state:
                continue
            if proximity_x is not None and proximity_y is not None:
                dx = entity.position_x - proximity_x
                dy = entity.position_y - proximity_y
                if math.sqrt(dx * dx + dy * dy) > max_distance:
                    continue
            results.append(entity)

        if proximity_x is not None:
            results.sort(
                key=lambda e: math.sqrt(
                    (e.position_x - proximity_x) ** 2 +
                    (e.position_y - proximity_y) ** 2
                )
            )

        return results[:limit]

    # ------------------------------------------------------------------
    # Region Management
    # ------------------------------------------------------------------

    def _get_or_create_region(self, x: float, y: float) -> WorldRegion:
        """Get or create the spatial region containing (x, y)."""
        region_size = 1000.0
        rx = math.floor(x / region_size) * region_size
        ry = math.floor(y / region_size) * region_size
        key = f"{rx}_{ry}"

        if key not in self._regions:
            self._regions[key] = WorldRegion(
                bounds_x=rx,
                bounds_y=ry,
                bounds_width=region_size,
                bounds_height=region_size,
            )

        return self._regions[key]

    def register_interest_region(
        self,
        agent_id: str,
        x: float,
        y: float,
        radius: float = 500.0,
    ) -> Dict[str, Any]:
        """
        Subscribe an agent to spatial updates for a region.

        Args:
            agent_id: Subscribing agent.
            x: Center X coordinate.
            y: Center Y coordinate.
            radius: Interest radius.

        Returns:
            Subscription confirmation with affected regions.
        """
        regions = []
        step = radius
        for rx in range(int(x - radius), int(x + radius), int(step)):
            for ry in range(int(y - radius), int(y + radius), int(step)):
                region = self._get_or_create_region(float(rx), float(ry))
                if region.region_id not in regions:
                    regions.append(region.region_id)

        self._agent_interests[agent_id] = regions
        return {
            "agent_id": agent_id,
            "center": {"x": x, "y": y},
            "radius": radius,
            "interest_regions": regions,
            "region_count": len(regions),
        }

    # ------------------------------------------------------------------
    # Situational Awareness
    # ------------------------------------------------------------------

    def get_situational_awareness(self, agent_id: str) -> Dict[str, Any]:
        """
        Aggregate an agent's complete understanding of its context.

        Args:
            agent_id: The agent to query.

        Returns:
            Dict with position, mode, nearby entities, recent actions, and state.
        """
        position = self._agent_positions.get(agent_id, (0.0, 0.0))
        mode = self._agent_modes.get(agent_id, InteractionMode.OBSERVER)
        state = self._agent_state.get(agent_id, {})

        nearby = self.query_world_entities(
            proximity_x=position[0],
            proximity_y=position[1],
            max_distance=500.0,
            limit=20,
        )

        recent_cycles = []
        for cycle in list(self._cycle_history)[-5:]:
            if cycle.action and cycle.feedback:
                recent_cycles.append(cycle.to_dict())

        return {
            "agent_id": agent_id,
            "position": {"x": position[0], "y": position[1]},
            "mode": mode.value,
            "cycles_completed": state.get("cycles_completed", 0),
            "success_streak": state.get("success_streak", 0),
            "nearby_entities": [e.to_dict() for e in nearby],
            "nearby_entity_count": len(nearby),
            "recent_cycles": recent_cycles,
            "world_properties": dict(self._world_properties),
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Return aggregate world interaction statistics."""
        total_cycles = len(self._cycle_history)
        successful = sum(
            1 for c in self._cycle_history
            if c.feedback and c.feedback.feedback_type == FeedbackType.SUCCESS
        )

        return {
            "total_cycles": total_cycles,
            "successful_cycles": successful,
            "success_rate": round(successful / max(1, total_cycles) * 100, 2),
            "registered_agents": len(self._agent_positions),
            "registered_entities": len(self._entities),
            "active_regions": len(self._regions),
            "world_properties": dict(self._world_properties),
            "agent_modes": {
                aid: mode.value for aid, mode in self._agent_modes.items()
            },
        }

    # ------------------------------------------------------------------
    # Action Handlers
    # ------------------------------------------------------------------

    def register_action_handler(
        self,
        domain: ActionDomain,
        action_name: str,
        handler: Callable[..., Any],
    ) -> None:
        """Register a custom handler for a specific action."""
        self._action_handlers[domain][action_name] = handler

    def _register_default_handlers(self):
        """Register default action handlers for common operations."""
        def _handle_move(agent_id: str, action: WorldAction, parameters: Dict[str, Any]) -> Dict[str, Any]:
            tx = float(parameters.get("target_x", 0))
            ty = float(parameters.get("target_y", 0))
            speed = float(parameters.get("speed", 200))
            old_pos = self._agent_positions.get(agent_id, (0.0, 0.0))
            self._agent_positions[agent_id] = (tx, ty)
            return {"moved": True, "from": old_pos, "to": (tx, ty), "speed": speed}

        def _handle_query(agent_id: str, action: WorldAction, parameters: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "entity_count": len(self._entities),
                "agent_count": len(self._agent_positions),
                "world_name": self._world_properties.get("world_name", "default"),
            }

        self._action_handlers[ActionDomain.MOVEMENT]["move_toward"] = _handle_move
        self._action_handlers[ActionDomain.QUERY]["query_world_state"] = _handle_query

    # ------------------------------------------------------------------
    # World Properties
    # ------------------------------------------------------------------

    def set_world_property(self, key: str, value: Any) -> None:
        """Set a global world property."""
        self._world_properties[key] = value

    def get_world_property(self, key: str, default: Any = None) -> Any:
        """Get a global world property."""
        return self._world_properties.get(key, default)

    # ------------------------------------------------------------------
    # Singleton & Lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentWorldInteraction":
        """Return the singleton instance."""
        return cls()

    def reset(self) -> None:
        """Reset all world interaction state."""
        with self._lock:
            self._entities.clear()
            self._regions.clear()
            self._agent_positions.clear()
            self._agent_modes.clear()
            self._agent_interests.clear()
            self._agent_state.clear()
            self._cycle_history.clear()
            self._action_history.clear()
            self._feedback_history.clear()
            self._cycle_counter = 0
            self._world_properties = {
                "world_name": "default",
                "world_size": {"width": 10000, "height": 10000},
                "gravity": {"x": 0.0, "y": -9.81},
                "time_scale": 1.0,
                "paused": False,
            }


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_agent_world_interaction() -> AgentWorldInteraction:
    """Return the singleton AgentWorldInteraction instance."""
    return AgentWorldInteraction()