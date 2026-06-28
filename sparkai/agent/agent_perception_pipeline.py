"""
SparkLabs Agent - Perception Pipeline

Multi-modal perception pipeline that enables agents to observe, interpret,
and understand their game world environment through multiple sensory channels.
Processes raw game state data into structured percepts that feed into the
agent's decision-making and world model.

Architecture:
  PerceptionPipeline (Singleton)
    |-- SensoryChannel (abstract base for perception modalities)
    |   |-- VisualChannel (game object detection, spatial awareness)
    |   |-- SpatialChannel (position, distance, navigation)
    |   |-- SocialChannel (agent relationships, group dynamics)
    |   |-- EventChannel (world events, state changes)
    |-- PerceptFusion (combines multi-channel percepts into unified view)
    |-- AttentionManager (prioritizes percepts by relevance)

Perception Channels:
  - VISUAL: what the agent can see in the game world
  - SPATIAL: spatial relationships and navigation data
  - SOCIAL: social dynamics and relationship information
  - EVENT: world events and state transitions
  - AUDITORY: audio cues and environmental sounds
  - TACTILE: collision and physics-based perception

Usage:
    pp = get_perception_pipeline()
    pp.initialize()

    percepts = pp.perceive(
        agent_id="agent_42",
        world_state=current_world_state,
        channels=[PerceptionChannel.VISUAL, PerceptionChannel.SPATIAL],
    )

    attention = pp.get_attention_focus("agent_42")
    pp.shutdown()
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class PerceptionChannel(Enum):
    """Sensory channels available to game agents."""
    VISUAL = "visual"          # Visual perception of game objects
    SPATIAL = "spatial"        # Spatial relationships and navigation
    SOCIAL = "social"          # Social dynamics and relationships
    EVENT = "event"            # World events and state changes
    AUDITORY = "auditory"      # Audio cues and environmental sounds
    TACTILE = "tactile"        # Collision and physics-based perception


class PerceptType(Enum):
    """Types of percepts that can be generated."""
    OBJECT_DETECTED = "object_detected"
    OBJECT_LOST = "object_lost"
    POSITION_CHANGED = "position_changed"
    DISTANCE_MEASURED = "distance_measured"
    RELATIONSHIP_CHANGED = "relationship_changed"
    SOCIAL_EVENT = "social_event"
    WORLD_EVENT = "world_event"
    STATE_TRANSITION = "state_transition"
    THREAT_DETECTED = "threat_detected"
    OPPORTUNITY_DETECTED = "opportunity_detected"
    NAVIGATION_UPDATE = "navigation_update"


class AttentionPriority(Enum):
    """Priority levels for attention allocation."""
    CRITICAL = 1    # Immediate threat or opportunity
    HIGH = 2        # Important but not urgent
    MEDIUM = 3      # Standard attention
    LOW = 4         # Background observation
    IGNORED = 5     # Filtered out


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Percept:
    """A single percept generated from sensory input."""
    percept_id: str
    percept_type: PerceptType
    channel: PerceptionChannel
    content: str
    confidence: float = 0.8
    priority: AttentionPriority = AttentionPriority.MEDIUM
    source_id: str = ""
    source_position: Optional[Tuple[float, float, float]] = None
    target_id: str = ""
    target_position: Optional[Tuple[float, float, float]] = None
    distance: Optional[float] = None
    intensity: float = 0.5
    timestamp: float = field(default_factory=time.time)
    ttl: float = 10.0       # Time-to-live in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl

    def to_dict(self) -> Dict[str, Any]:
        return {
            "percept_id": self.percept_id,
            "percept_type": self.percept_type.value,
            "channel": self.channel.value,
            "content": self.content,
            "confidence": self.confidence,
            "priority": self.priority.value,
            "source_id": self.source_id,
            "source_position": list(self.source_position) if self.source_position else None,
            "target_id": self.target_id,
            "target_position": list(self.target_position) if self.target_position else None,
            "distance": self.distance,
            "intensity": self.intensity,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "metadata": self.metadata,
        }


@dataclass
class AttentionFocus:
    """Current attention focus of an agent."""
    agent_id: str
    primary_target_id: Optional[str] = None
    primary_interest: Optional[str] = None
    secondary_interests: List[str] = field(default_factory=list)
    attention_span: float = 5.0
    last_shift: float = field(default_factory=time.time)
    focus_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "primary_target_id": self.primary_target_id,
            "primary_interest": self.primary_interest,
            "secondary_interests": self.secondary_interests,
            "attention_span": self.attention_span,
            "last_shift": self.last_shift,
            "focus_history": self.focus_history[-10:],
        }


@dataclass
class PerceptionSnapshot:
    """Complete perception snapshot for an agent at a point in time."""
    snapshot_id: str
    agent_id: str
    percepts: List[Percept] = field(default_factory=list)
    fused_view: str = ""
    attention_focus: Optional[AttentionFocus] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "percept_count": len(self.percepts),
            "percepts": [p.to_dict() for p in self.percepts],
            "fused_view": self.fused_view,
            "attention_focus": self.attention_focus.to_dict() if self.attention_focus else None,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


# =============================================================================
# Perception Pipeline
# =============================================================================


class PerceptionPipeline:
    """
    Multi-modal perception pipeline for AI game agents.
    Processes raw game state into structured percepts across multiple sensory channels.
    """

    _instance: Optional["PerceptionPipeline"] = None
    _instance_lock = threading.RLock()

    # Perception range constants
    DEFAULT_VISUAL_RANGE = 100.0
    DEFAULT_AUDITORY_RANGE = 200.0
    DEFAULT_SOCIAL_RANGE = 50.0

    def __init__(self) -> None:
        if PerceptionPipeline._instance is not None:
            raise RuntimeError("Use PerceptionPipeline.get_instance()")
        self._initialized: bool = False
        self._snapshots: Dict[str, List[PerceptionSnapshot]] = {}
        self._attention_states: Dict[str, AttentionFocus] = {}
        self._channel_processors: Dict[PerceptionChannel, Callable] = {}
        self._percept_history: Dict[str, List[Percept]] = {}
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "PerceptionPipeline":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the perception pipeline with default channel processors."""
        with self._lock:
            if self._initialized:
                return
            self._channel_processors[PerceptionChannel.VISUAL] = self._process_visual
            self._channel_processors[PerceptionChannel.SPATIAL] = self._process_spatial
            self._channel_processors[PerceptionChannel.SOCIAL] = self._process_social
            self._channel_processors[PerceptionChannel.EVENT] = self._process_event
            self._channel_processors[PerceptionChannel.AUDITORY] = self._process_auditory
            self._channel_processors[PerceptionChannel.TACTILE] = self._process_tactile
            self._initialized = True

    def perceive(
        self,
        agent_id: str,
        world_state: Dict[str, Any],
        channels: Optional[List[PerceptionChannel]] = None,
        agent_position: Optional[Tuple[float, float, float]] = None,
        max_percepts: int = 20,
    ) -> PerceptionSnapshot:
        """
        Generate a perception snapshot for an agent from the world state.

        Args:
            agent_id: The perceiving agent's ID.
            world_state: Current world state dictionary.
            channels: Specific channels to process (None = all).
            agent_position: Agent's current position in the world.
            max_percepts: Maximum number of percepts to generate.

        Returns:
            PerceptionSnapshot containing all generated percepts.
        """
        with self._lock:
            snapshot_id = uuid.uuid4().hex[:12]
            channels = channels or list(PerceptionChannel)
            all_percepts: List[Percept] = []

            # Process each channel
            for channel in channels:
                processor = self._channel_processors.get(channel)
                if processor:
                    channel_percepts = processor(
                        agent_id, world_state, agent_position, max_percepts // len(channels)
                    )
                    all_percepts.extend(channel_percepts)

            # Sort by priority and limit
            all_percepts.sort(key=lambda p: p.priority.value)
            all_percepts = all_percepts[:max_percepts]

            # Fuse percepts into unified view
            fused_view = self._fuse_percepts(agent_id, all_percepts)

            # Get or create attention focus
            attention = self._attention_states.get(agent_id)
            if not attention:
                attention = AttentionFocus(agent_id=agent_id)
                self._attention_states[agent_id] = attention

            # Update attention based on new percepts
            self._update_attention(attention, all_percepts)

            snapshot = PerceptionSnapshot(
                snapshot_id=snapshot_id,
                agent_id=agent_id,
                percepts=all_percepts,
                fused_view=fused_view,
                attention_focus=attention,
                metadata={"channels": [c.value for c in channels]},
            )

            # Store snapshot
            if agent_id not in self._snapshots:
                self._snapshots[agent_id] = []
            self._snapshots[agent_id].append(snapshot)

            # Store percept history
            if agent_id not in self._percept_history:
                self._percept_history[agent_id] = []
            self._percept_history[agent_id].extend(all_percepts)

            # Clean old percepts
            self._percept_history[agent_id] = [
                p for p in self._percept_history[agent_id]
                if not p.is_expired
            ][-100:]

            return snapshot

    # ── Channel Processors ──

    def _process_visual(
        self,
        agent_id: str,
        world_state: Dict[str, Any],
        agent_position: Optional[Tuple[float, float, float]],
        max_count: int,
    ) -> List[Percept]:
        """Process visual perception channel."""
        percepts: List[Percept] = []
        objects = world_state.get("objects", [])
        entities = world_state.get("entities", [])

        for obj in objects[:max_count]:
            if obj.get("visible", True):
                obj_pos = obj.get("position", (0, 0, 0))
                distance = self._calculate_distance(agent_position, obj_pos) if agent_position else None
                if distance is None or distance <= self.DEFAULT_VISUAL_RANGE:
                    percepts.append(Percept(
                        percept_id=uuid.uuid4().hex[:12],
                        percept_type=PerceptType.OBJECT_DETECTED,
                        channel=PerceptionChannel.VISUAL,
                        content=f"Detected object: {obj.get('name', 'unknown')}",
                        source_id=agent_id,
                        source_position=agent_position,
                        target_id=obj.get("id", ""),
                        target_position=obj_pos,
                        distance=distance,
                        intensity=1.0 - min((distance or 0) / self.DEFAULT_VISUAL_RANGE, 1.0),
                        priority=AttentionPriority.LOW,
                    ))

        for entity in entities[:max_count]:
            entity_pos = entity.get("position", (0, 0, 0))
            distance = self._calculate_distance(agent_position, entity_pos) if agent_position else None
            if distance is None or distance <= self.DEFAULT_VISUAL_RANGE:
                is_threat = entity.get("hostile", False)
                percepts.append(Percept(
                    percept_id=uuid.uuid4().hex[:12],
                    percept_type=PerceptType.THREAT_DETECTED if is_threat else PerceptType.OBJECT_DETECTED,
                    channel=PerceptionChannel.VISUAL,
                    content=f"{'Threat' if is_threat else 'Entity'} detected: {entity.get('name', 'unknown')}",
                    source_id=agent_id,
                    source_position=agent_position,
                    target_id=entity.get("id", ""),
                    target_position=entity_pos,
                    distance=distance,
                    priority=AttentionPriority.CRITICAL if is_threat and (distance or 999) < 30 else AttentionPriority.MEDIUM,
                    intensity=1.0 - min((distance or 0) / self.DEFAULT_VISUAL_RANGE, 1.0),
                ))

        return percepts

    def _process_spatial(
        self,
        agent_id: str,
        world_state: Dict[str, Any],
        agent_position: Optional[Tuple[float, float, float]],
        max_count: int,
    ) -> List[Percept]:
        """Process spatial perception channel."""
        percepts: List[Percept] = []
        waypoints = world_state.get("waypoints", [])
        obstacles = world_state.get("obstacles", [])
        navmesh = world_state.get("navmesh", {})

        for wp in waypoints[:max_count]:
            wp_pos = wp.get("position", (0, 0, 0))
            distance = self._calculate_distance(agent_position, wp_pos) if agent_position else None
            percepts.append(Percept(
                percept_id=uuid.uuid4().hex[:12],
                percept_type=PerceptType.NAVIGATION_UPDATE,
                channel=PerceptionChannel.SPATIAL,
                content=f"Waypoint: {wp.get('name', 'unknown')}",
                source_id=agent_id,
                target_position=wp_pos,
                distance=distance,
                priority=AttentionPriority.LOW,
            ))

        for obs in obstacles[:max_count]:
            obs_pos = obs.get("position", (0, 0, 0))
            distance = self._calculate_distance(agent_position, obs_pos) if agent_position else None
            if distance is not None and distance < 50:
                percepts.append(Percept(
                    percept_id=uuid.uuid4().hex[:12],
                    percept_type=PerceptType.NAVIGATION_UPDATE,
                    channel=PerceptionChannel.SPATIAL,
                    content=f"Obstacle at distance {distance:.1f}",
                    source_id=agent_id,
                    target_position=obs_pos,
                    distance=distance,
                    priority=AttentionPriority.HIGH if distance < 20 else AttentionPriority.MEDIUM,
                ))

        return percepts

    def _process_social(
        self,
        agent_id: str,
        world_state: Dict[str, Any],
        agent_position: Optional[Tuple[float, float, float]],
        max_count: int,
    ) -> List[Percept]:
        """Process social perception channel."""
        percepts: List[Percept] = []
        relationships = world_state.get("relationships", {})
        social_events = world_state.get("social_events", [])

        for rel_key, rel_data in list(relationships.items())[:max_count]:
            if agent_id in rel_key:
                percepts.append(Percept(
                    percept_id=uuid.uuid4().hex[:12],
                    percept_type=PerceptType.RELATIONSHIP_CHANGED,
                    channel=PerceptionChannel.SOCIAL,
                    content=f"Relationship: {rel_data.get('type', 'neutral')}",
                    source_id=agent_id,
                    priority=AttentionPriority.MEDIUM,
                    metadata={"relationship": rel_data},
                ))

        for event in social_events[:max_count]:
            percepts.append(Percept(
                percept_id=uuid.uuid4().hex[:12],
                percept_type=PerceptType.SOCIAL_EVENT,
                channel=PerceptionChannel.SOCIAL,
                content=event.get("description", "Social event occurred"),
                source_id=event.get("source_id", ""),
                priority=AttentionPriority(event.get("priority", 3)),
                metadata={"event_data": event},
            ))

        return percepts

    def _process_event(
        self,
        agent_id: str,
        world_state: Dict[str, Any],
        agent_position: Optional[Tuple[float, float, float]],
        max_count: int,
    ) -> List[Percept]:
        """Process world event perception channel."""
        percepts: List[Percept] = []
        events = world_state.get("events", [])
        state_changes = world_state.get("state_changes", [])

        for event in events[:max_count]:
            percepts.append(Percept(
                percept_id=uuid.uuid4().hex[:12],
                percept_type=PerceptType.WORLD_EVENT,
                channel=PerceptionChannel.EVENT,
                content=event.get("description", "World event"),
                priority=AttentionPriority(event.get("priority", 3)),
                intensity=event.get("intensity", 0.5),
                metadata={"event_type": event.get("type", "unknown")},
            ))

        for change in state_changes[:max_count]:
            percepts.append(Percept(
                percept_id=uuid.uuid4().hex[:12],
                percept_type=PerceptType.STATE_TRANSITION,
                channel=PerceptionChannel.EVENT,
                content=f"State change: {change.get('key', 'unknown')} → {change.get('value', 'unknown')}",
                priority=AttentionPriority.MEDIUM,
            ))

        return percepts

    def _process_auditory(
        self,
        agent_id: str,
        world_state: Dict[str, Any],
        agent_position: Optional[Tuple[float, float, float]],
        max_count: int,
    ) -> List[Percept]:
        """Process auditory perception channel."""
        percepts: List[Percept] = []
        sounds = world_state.get("sounds", [])
        audio_events = world_state.get("audio_events", [])

        for sound in sounds[:max_count]:
            sound_pos = sound.get("position", (0, 0, 0))
            distance = self._calculate_distance(agent_position, sound_pos) if agent_position else None
            if distance is None or distance <= self.DEFAULT_AUDITORY_RANGE:
                percepts.append(Percept(
                    percept_id=uuid.uuid4().hex[:12],
                    percept_type=PerceptType.WORLD_EVENT,
                    channel=PerceptionChannel.AUDITORY,
                    content=f"Sound: {sound.get('type', 'unknown')}",
                    source_position=sound_pos,
                    distance=distance,
                    intensity=1.0 - min((distance or 0) / self.DEFAULT_AUDITORY_RANGE, 1.0),
                    priority=AttentionPriority.LOW,
                ))

        return percepts

    def _process_tactile(
        self,
        agent_id: str,
        world_state: Dict[str, Any],
        agent_position: Optional[Tuple[float, float, float]],
        max_count: int,
    ) -> List[Percept]:
        """Process tactile/physics perception channel."""
        percepts: List[Percept] = []
        collisions = world_state.get("collisions", [])
        forces = world_state.get("forces", [])

        for collision in collisions[:max_count]:
            if collision.get("entity_id") == agent_id:
                percepts.append(Percept(
                    percept_id=uuid.uuid4().hex[:12],
                    percept_type=PerceptType.WORLD_EVENT,
                    channel=PerceptionChannel.TACTILE,
                    content=f"Collision with: {collision.get('with', 'unknown')}",
                    priority=AttentionPriority.HIGH,
                    intensity=collision.get("force", 0.5),
                ))

        return percepts

    # ── Fusion & Attention ──

    def _fuse_percepts(self, agent_id: str, percepts: List[Percept]) -> str:
        """Fuse multiple percepts into a unified situational view."""
        if not percepts:
            return f"Agent {agent_id}: No percepts available."

        by_channel: Dict[str, List[str]] = {}
        for p in percepts:
            ch = p.channel.value
            if ch not in by_channel:
                by_channel[ch] = []
            by_channel[ch].append(p.content)

        parts = []
        for ch, contents in by_channel.items():
            parts.append(f"[{ch}] {len(contents)} percepts: {contents[0]}")

        critical = [p for p in percepts if p.priority == AttentionPriority.CRITICAL]
        if critical:
            parts.insert(0, f"ALERT: {critical[0].content}")

        return " | ".join(parts)

    def _update_attention(
        self,
        attention: AttentionFocus,
        percepts: List[Percept],
    ) -> None:
        """Update the agent's attention focus based on new percepts."""
        critical = [p for p in percepts if p.priority == AttentionPriority.CRITICAL]
        high = [p for p in percepts if p.priority == AttentionPriority.HIGH]

        if critical:
            attention.primary_target_id = critical[0].target_id
            attention.primary_interest = critical[0].content
            attention.last_shift = time.time()
            attention.focus_history.append({
                "target": critical[0].target_id,
                "reason": critical[0].content,
                "timestamp": time.time(),
            })
        elif high:
            attention.secondary_interests = [p.target_id for p in high[:3]]

    # ── Utility ──

    @staticmethod
    def _calculate_distance(
        pos1: Optional[Tuple[float, float, float]],
        pos2: Optional[Tuple[float, float, float]],
    ) -> Optional[float]:
        """Calculate Euclidean distance between two positions."""
        if pos1 is None or pos2 is None:
            return None
        return math.sqrt(
            (pos1[0] - pos2[0]) ** 2 +
            (pos1[1] - pos2[1]) ** 2 +
            (pos1[2] - pos2[2]) ** 2
        )

    # ── Public API ──

    def get_attention_focus(self, agent_id: str) -> Optional[AttentionFocus]:
        """Get the current attention focus for an agent."""
        return self._attention_states.get(agent_id)

    def get_recent_percepts(
        self,
        agent_id: str,
        channel: Optional[PerceptionChannel] = None,
        limit: int = 20,
    ) -> List[Percept]:
        """Get recent percepts for an agent, optionally filtered by channel."""
        percepts = self._percept_history.get(agent_id, [])
        if channel:
            percepts = [p for p in percepts if p.channel == channel]
        return percepts[-limit:]

    def get_latest_snapshot(self, agent_id: str) -> Optional[PerceptionSnapshot]:
        """Get the latest perception snapshot for an agent."""
        snapshots = self._snapshots.get(agent_id, [])
        return snapshots[-1] if snapshots else None

    def clear_agent_percepts(self, agent_id: str) -> None:
        """Clear all percepts and snapshots for an agent."""
        with self._lock:
            self._snapshots.pop(agent_id, None)
            self._percept_history.pop(agent_id, None)
            self._attention_states.pop(agent_id, None)

    def get_snapshots(self, agent_id: str) -> List[PerceptionSnapshot]:
        """Get all perception snapshots for an agent."""
        return self._snapshots.get(agent_id, [])

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the perception pipeline."""
        return {
            "initialized": self._initialized,
            "active_agents": len(self._attention_states),
            "total_snapshots": sum(len(s) for s in self._snapshots.values()),
            "total_percepts": sum(len(p) for p in self._percept_history.values()),
            "channels": [c.value for c in self._channel_processors.keys()],
        }

    def shutdown(self) -> None:
        """Shutdown the perception pipeline."""
        with self._lock:
            self._snapshots.clear()
            self._attention_states.clear()
            self._percept_history.clear()
            self._channel_processors.clear()
            self._initialized = False


# =============================================================================
# Singleton Accessor
# =============================================================================

def get_perception_pipeline() -> PerceptionPipeline:
    """Get the singleton PerceptionPipeline instance."""
    return PerceptionPipeline.get_instance()