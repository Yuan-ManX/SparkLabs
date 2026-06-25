"""
SparkLabs Agent World Simulator - Autonomous AI-Driven World Simulation

Comprehensive world simulation engine with autonomous agents that perceive,
decide, act, and create emergent narratives in AI-generated worlds.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class WorldState(Enum):
    """Overall world simulation state."""
    CREATING = "creating"        # World is being generated
    RUNNING = "running"          # Simulation is active
    PAUSED = "paused"            # Simulation is paused
    STOPPED = "stopped"          # Simulation has ended


class AgentState(Enum):
    """Individual agent state within the simulation."""
    IDLE = "idle"                # Waiting for next action
    PERCEIVING = "perceiving"    # Observing environment
    DECIDING = "deciding"        # Planning next action
    ACTING = "acting"            # Executing an action
    INTERACTING = "interacting"  # Engaging with another agent
    RESTING = "resting"          # Inactive/dormant


class ActionType(Enum):
    """Types of actions an agent can perform."""
    MOVE = "move"                # Navigate to a location
    INTERACT = "interact"        # Interact with an object
    SPEAK = "speak"              # Communicate with another agent
    USE_ITEM = "use_item"        # Use an inventory item
    OBSERVE = "observe"          # Scan the environment
    WAIT = "wait"                # Do nothing for a tick
    CRAFT = "craft"              # Create a new item
    TRADE = "trade"              # Exchange items with another agent


class EmotionType(Enum):
    """Emotional states for agents."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    CURIOUS = "curious"
    BORED = "bored"


@dataclass
class WorldConfig:
    """Configuration for a simulated world."""
    name: str
    description: str
    size: Tuple[int, int] = (100, 100)
    agent_count: int = 10
    max_ticks: int = 10000
    tick_rate: float = 1.0  # seconds per tick
    seed: Optional[int] = None
    rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """2D position in the world."""
    x: float = 0.0
    y: float = 0.0

    def distance_to(self, other: "Position") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y}


@dataclass
class AgentMemory:
    """Memory structure for a simulated agent."""
    recent_events: List[Dict[str, Any]] = field(default_factory=list)
    relationships: Dict[str, float] = field(default_factory=dict)
    known_locations: List[Position] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    max_events: int = 100

    def record_event(self, event: Dict[str, Any]) -> None:
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_events:
            self.recent_events = self.recent_events[-self.max_events:]

    def update_relationship(self, agent_id: str, delta: float) -> None:
        current = self.relationships.get(agent_id, 0.0)
        self.relationships[agent_id] = max(-1.0, min(1.0, current + delta))


@dataclass
class SimulatedAgent:
    """An autonomous agent in the simulated world."""
    agent_id: str
    name: str
    personality: Dict[str, float]  # Trait name -> intensity (0.0-1.0)
    position: Position
    state: AgentState = AgentState.IDLE
    emotion: EmotionType = EmotionType.NEUTRAL
    emotion_intensity: float = 0.5
    inventory: List[str] = field(default_factory=list)
    memory: AgentMemory = field(default_factory=AgentMemory)
    current_goal: Optional[str] = None
    interaction_target: Optional[str] = None
    age_ticks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "personality": self.personality,
            "position": self.position.to_dict(),
            "state": self.state.value,
            "emotion": self.emotion.value,
            "emotion_intensity": self.emotion_intensity,
            "inventory": self.inventory,
            "current_goal": self.current_goal,
            "interaction_target": self.interaction_target,
            "age_ticks": self.age_ticks,
            "memory_size": len(self.memory.recent_events),
            "relationship_count": len(self.memory.relationships),
        }


@dataclass
class WorldObject:
    """An interactive object in the simulated world."""
    object_id: str
    name: str
    object_type: str
    position: Position
    properties: Dict[str, Any] = field(default_factory=dict)
    interactable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "name": self.name,
            "object_type": self.object_type,
            "position": self.position.to_dict(),
            "properties": self.properties,
            "interactable": self.interactable,
        }


@dataclass
class WorldEvent:
    """An event that occurred in the simulation."""
    event_id: str
    event_type: str
    description: str
    source_agent: Optional[str] = None
    target_agent: Optional[str] = None
    position: Optional[Position] = None
    tick: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "description": self.description,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "position": self.position.to_dict() if self.position else None,
            "tick": self.tick,
            "timestamp": self.timestamp,
        }


class WorldSimulator:
    """Autonomous AI-driven world simulation engine.

    Creates living worlds where agents perceive, decide, act, and generate
    emergent narratives through their interactions. Supports God Mode for
    real-time intervention.
    """

    _instance: Optional["WorldSimulator"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if self._instance is not None:
            raise RuntimeError("Use WorldSimulator.get_instance()")
        self._config: Optional[WorldConfig] = None
        self._state: WorldState = WorldState.STOPPED
        self._agents: Dict[str, SimulatedAgent] = {}
        self._objects: Dict[str, WorldObject] = {}
        self._events: List[WorldEvent] = []
        self._tick_count: int = 0
        self._initialized: bool = False
        self._running: bool = False
        self._simulation_thread: Optional[threading.Thread] = None
        self._event_callbacks: List[Callable] = []
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "WorldSimulator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, config: WorldConfig) -> None:
        with self._lock:
            self._config = config
            self._state = WorldState.CREATING
            self._generate_world(config)
            self._state = WorldState.RUNNING
            self._initialized = True

    def start(self) -> None:
        with self._lock:
            if not self._initialized:
                raise RuntimeError("World not initialized")
            self._running = True
            self._state = WorldState.RUNNING

    def pause(self) -> None:
        with self._lock:
            self._state = WorldState.PAUSED

    def resume(self) -> None:
        with self._lock:
            if self._state == WorldState.PAUSED:
                self._state = WorldState.RUNNING

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._state = WorldState.STOPPED

    def tick(self) -> List[WorldEvent]:
        """Advance the simulation by one tick."""
        with self._lock:
            if self._state != WorldState.RUNNING:
                return []

            self._tick_count += 1
            events: List[WorldEvent] = []

            # Update each agent
            for agent in self._agents.values():
                agent.age_ticks += 1
                agent_events = self._update_agent(agent)
                events.extend(agent_events)

            # Check world-level events
            config = self._config
            if config and self._tick_count >= config.max_ticks:
                self._state = WorldState.STOPPED
                events.append(WorldEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    event_type="world_end",
                    description=f"World simulation ended after {self._tick_count} ticks",
                    tick=self._tick_count,
                ))

            self._events.extend(events)
            for callback in self._event_callbacks:
                try:
                    callback(events)
                except Exception:
                    pass

            return events

    def add_event_callback(self, callback: Callable) -> None:
        self._event_callbacks.append(callback)

    def add_agent(self, name: str, personality: Dict[str, float],
                  position: Optional[Position] = None) -> SimulatedAgent:
        with self._lock:
            agent_id = f"agent_{uuid.uuid4().hex[:8]}"
            if position is None:
                config = self._config
                if config:
                    position = Position(
                        x=hash(name) % config.size[0],
                        y=hash(name + "y") % config.size[1],
                    )
                else:
                    position = Position(0, 0)
            agent = SimulatedAgent(
                agent_id=agent_id,
                name=name,
                personality=personality,
                position=position,
            )
            self._agents[agent_id] = agent
            return agent

    def add_object(self, name: str, object_type: str,
                   position: Position,
                   properties: Optional[Dict[str, Any]] = None) -> WorldObject:
        with self._lock:
            object_id = f"obj_{uuid.uuid4().hex[:8]}"
            obj = WorldObject(
                object_id=object_id,
                name=name,
                object_type=object_type,
                position=position,
                properties=properties or {},
            )
            self._objects[object_id] = obj
            return obj

    def broadcast_event(self, event_type: str, description: str,
                        target_agents: Optional[List[str]] = None) -> WorldEvent:
        """God Mode: broadcast an event to all or specific agents."""
        with self._lock:
            event = WorldEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type=event_type,
                description=description,
                tick=self._tick_count,
            )
            self._events.append(event)
            if target_agents:
                for agent_id in target_agents:
                    agent = self._agents.get(agent_id)
                    if agent:
                        agent.memory.record_event({
                            "type": event_type,
                            "description": description,
                            "tick": self._tick_count,
                        })
            return event

    def edit_agent(self, agent_id: str,
                   updates: Dict[str, Any]) -> Optional[SimulatedAgent]:
        """God Mode: modify an agent's state."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return None
            for key, value in updates.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
            return agent

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        agent = self._agents.get(agent_id)
        return agent.to_dict() if agent else None

    def get_all_agents(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._agents.values()]

    def get_all_objects(self) -> List[Dict[str, Any]]:
        return [o.to_dict() for o in self._objects.values()]

    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._events[-limit:]]

    def get_world_state(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "tick_count": self._tick_count,
            "agent_count": len(self._agents),
            "object_count": len(self._objects),
            "event_count": len(self._events),
            "initialized": self._initialized,
            "config": self._config.__dict__ if self._config else None,
        }

    def _generate_world(self, config: WorldConfig) -> None:
        """Generate the initial world state."""
        # Generate agents with diverse personalities
        personalities = [
            {"openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.7,
             "agreeableness": 0.5, "curiosity": 0.9},
            {"openness": 0.3, "conscientiousness": 0.9, "extraversion": 0.2,
             "agreeableness": 0.8, "caution": 0.7},
            {"openness": 0.7, "conscientiousness": 0.4, "extraversion": 0.9,
             "agreeableness": 0.3, "ambition": 0.8},
            {"openness": 0.5, "conscientiousness": 0.7, "extraversion": 0.5,
             "agreeableness": 0.6, "creativity": 0.7},
            {"openness": 0.9, "conscientiousness": 0.3, "extraversion": 0.8,
             "agreeableness": 0.7, "exploration": 0.9},
        ]

        for i in range(config.agent_count):
            personality = personalities[i % len(personalities)].copy()
            pos = Position(
                x=(hash(f"agent_{i}") % config.size[0]),
                y=(hash(f"agent_{i}_y") % config.size[1]),
            )
            agent = SimulatedAgent(
                agent_id=f"agent_{uuid.uuid4().hex[:8]}",
                name=f"Agent_{i}",
                personality=personality,
                position=pos,
            )
            self._agents[agent.agent_id] = agent

        # Generate some world objects
        object_types = ["resource", "structure", "decoration", "interactive"]
        for i in range(min(config.agent_count * 2, 50)):
            obj_type = object_types[i % len(object_types)]
            pos = Position(
                x=(hash(f"obj_{i}") % config.size[0]),
                y=(hash(f"obj_{i}_y") % config.size[1]),
            )
            obj = WorldObject(
                object_id=f"obj_{uuid.uuid4().hex[:8]}",
                name=f"{obj_type}_{i}",
                object_type=obj_type,
                position=pos,
            )
            self._objects[obj.object_id] = obj

        self._events.append(WorldEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            event_type="world_created",
            description=f"World '{config.name}' created with {config.agent_count} agents",
            tick=0,
        ))

    def _update_agent(self, agent: SimulatedAgent) -> List[WorldEvent]:
        """Update a single agent for one tick - perceive, decide, act."""
        events: List[WorldEvent] = []

        # Phase 1: Perceive
        agent.state = AgentState.PERCEIVING
        nearby_agents = self._find_nearby_agents(agent, radius=10.0)
        nearby_objects = self._find_nearby_objects(agent, radius=5.0)

        # Phase 2: Decide
        agent.state = AgentState.DECIDING
        action = self._decide_action(agent, nearby_agents, nearby_objects)

        # Phase 3: Act
        agent.state = AgentState.ACTING
        action_events = self._execute_action(agent, action, nearby_agents,
                                            nearby_objects)
        events.extend(action_events)

        # Update emotional state
        self._update_emotion(agent, events)

        agent.state = AgentState.IDLE
        return events

    def _find_nearby_agents(self, agent: SimulatedAgent,
                            radius: float) -> List[SimulatedAgent]:
        nearby = []
        for other in self._agents.values():
            if other.agent_id != agent.agent_id:
                dist = agent.position.distance_to(other.position)
                if dist <= radius:
                    nearby.append(other)
        return nearby

    def _find_nearby_objects(self, agent: SimulatedAgent,
                             radius: float) -> List[WorldObject]:
        nearby = []
        for obj in self._objects.values():
            if obj.interactable:
                dist = agent.position.distance_to(obj.position)
                if dist <= radius:
                    nearby.append(obj)
        return nearby

    def _decide_action(self, agent: SimulatedAgent,
                       nearby_agents: List[SimulatedAgent],
                       nearby_objects: List[WorldObject]) -> Tuple[ActionType, Dict[str, Any]]:
        """Decide what action the agent should take this tick."""
        # Simple decision-making based on personality and context
        extraversion = agent.personality.get("extraversion", 0.5)
        curiosity = agent.personality.get("curiosity", 0.5)

        # If there are nearby agents, interact based on extraversion
        if nearby_agents and extraversion > 0.4:
            target = nearby_agents[0]
            return (ActionType.INTERACT, {"target_id": target.agent_id})

        # If there are nearby objects, investigate based on curiosity
        if nearby_objects and curiosity > 0.3:
            target = nearby_objects[0]
            return (ActionType.INTERACT, {"target_id": target.object_id})

        # Otherwise, move randomly
        config = self._config
        if config:
            new_x = agent.position.x + (hash(str(self._tick_count)) % 5 - 2)
            new_y = agent.position.y + (hash(str(self._tick_count + 1)) % 5 - 2)
            new_x = max(0, min(config.size[0], new_x))
            new_y = max(0, min(config.size[1], new_y))
            return (ActionType.MOVE, {"target": Position(new_x, new_y)})

        return (ActionType.WAIT, {})

    def _execute_action(self, agent: SimulatedAgent,
                        action: Tuple[ActionType, Dict[str, Any]],
                        nearby_agents: List[SimulatedAgent],
                        nearby_objects: List[WorldObject]) -> List[WorldEvent]:
        """Execute the decided action and return resulting events."""
        action_type, params = action
        events: List[WorldEvent] = []

        if action_type == ActionType.MOVE:
            target = params.get("target")
            if isinstance(target, Position):
                agent.position = target
                agent.memory.known_locations.append(target)

        elif action_type == ActionType.INTERACT:
            target_id = params.get("target_id", "")
            # Check if target is an agent
            target_agent = self._agents.get(target_id)
            if target_agent:
                agent.state = AgentState.INTERACTING
                agent.interaction_target = target_id
                agent.memory.update_relationship(target_id, 0.05)
                target_agent.memory.update_relationship(agent.agent_id, 0.05)
                events.append(WorldEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    event_type="interaction",
                    description=f"{agent.name} interacted with {target_agent.name}",
                    source_agent=agent.agent_id,
                    target_agent=target_id,
                    position=agent.position,
                    tick=self._tick_count,
                ))

            # Check if target is an object
            target_obj = self._objects.get(target_id)
            if target_obj:
                events.append(WorldEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:8]}",
                    event_type="object_interaction",
                    description=f"{agent.name} used {target_obj.name}",
                    source_agent=agent.agent_id,
                    position=target_obj.position,
                    tick=self._tick_count,
                ))

        elif action_type == ActionType.WAIT:
            pass

        return events

    def _update_emotion(self, agent: SimulatedAgent,
                        events: List[WorldEvent]) -> None:
        """Update agent's emotional state based on events."""
        # Natural decay toward neutral
        if agent.emotion != EmotionType.NEUTRAL:
            agent.emotion_intensity = max(0.0, agent.emotion_intensity - 0.01)
            if agent.emotion_intensity < 0.1:
                agent.emotion = EmotionType.NEUTRAL
                agent.emotion_intensity = 0.5

        # Event-driven emotion changes
        for event in events:
            if event.event_type == "interaction":
                if event.target_agent == agent.agent_id:
                    agent.emotion = EmotionType.HAPPY
                    agent.emotion_intensity = min(1.0, agent.emotion_intensity + 0.2)


def get_world_simulator() -> WorldSimulator:
    """Get the global WorldSimulator instance."""
    return WorldSimulator.get_instance()