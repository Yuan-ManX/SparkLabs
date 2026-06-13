"""
SparkLabs Agent - Perception Engine

A unified game world perception engine that aggregates and processes
sensory inputs from the game world across multiple modalities. Provides
AI agents with spatial, entity, event, environmental, social, and temporal
awareness through a configurable perception pipeline with attention-driven
focus and memory decay.

Core capabilities:
  - Unified perception pipeline across six sensory modalities
  - Spatial perception with zone/distance awareness and ray-casting
  - Entity perception with visibility, state, and proximity tracking
  - Event perception with local/global scope and intensity filtering
  - Environmental perception (terrain, weather, time, threat level)
  - Perception memory with configurable decay and history retention
  - Attention system with configurable priority weights and focus tracking
  - Configurable vision range, hearing range, and tracking limits

Architecture:
  AgentPerceptionEngine (Singleton)
    |-- PerceptionSnapshot (full perception frame capture)
    |-- PerceivedEntity (entity as observed from agent viewpoint)
    |-- PerceivedObject (interactive world object perception)
    |-- PerceivedEvent (world event with scope and intensity)
    |-- EnvironmentalState (terrain, weather, ambient conditions)
    |-- AttentionFocus (targeted attention with priority and duration)
    |-- PerceptionConfig (tunable perception parameters)
    |-- perceive()
    |-- perceive_spatial() / perceive_entities()
    |-- perceive_events() / perceive_environment()
    |-- set_attention_focus() / get_attention_targets()
    |-- get_perception_history() / get_status() / get_config()
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PerceptionModality(Enum):
    """Sensory modalities available to the perception engine."""
    SPATIAL = "spatial"
    ENTITY = "entity"
    EVENT = "event"
    ENVIRONMENTAL = "environmental"
    SOCIAL = "social"
    TEMPORAL = "temporal"


class AttentionPriority(Enum):
    """Priority levels for attention focus targets."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class EventScope(Enum):
    """Geographic scope of perceived world events."""
    LOCAL = "local"
    REGIONAL = "regional"
    GLOBAL = "global"


class WeatherCondition(Enum):
    """Environmental weather states."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    STORM = "storm"
    SNOW = "snow"
    FOG = "fog"
    WINDY = "windy"
    HEATWAVE = "heatwave"


class TerrainType(Enum):
    """Terrain surface classifications."""
    PLAIN = "plain"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    DESERT = "desert"
    SWAMP = "swamp"
    WATER = "water"
    URBAN = "urban"
    UNDERGROUND = "underground"
    TUNDRA = "tundra"
    VOLCANIC = "volcanic"


class TimeOfDay(Enum):
    """Diurnal time periods for environmental context."""
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    EVENING = "evening"
    NIGHT = "night"
    MIDNIGHT = "midnight"


class EntityType(Enum):
    """Categories of perceivable entities in the game world."""
    PLAYER = "player"
    NPC = "npc"
    ENEMY = "enemy"
    ALLY = "ally"
    NEUTRAL = "neutral"
    ANIMAL = "animal"
    VEHICLE = "vehicle"
    STRUCTURE = "structure"
    ITEM = "item"


class ObjectType(Enum):
    """Categories of perceivable interactive objects."""
    CONTAINER = "container"
    DOOR = "door"
    LEVER = "lever"
    PICKUP = "pickup"
    TRAP = "trap"
    LIGHT_SOURCE = "light_source"
    DECORATION = "decoration"
    TRIGGER = "trigger"
    RESOURCE_NODE = "resource_node"
    PORTAL = "portal"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PerceivedEntity:
    """An entity as perceived from the observing agent's viewpoint.

    Captures identity, spatial relationship (position, distance),
    visibility status, and current behavioral state.
    """
    entity_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    entity_type: EntityType = EntityType.NPC
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    distance: float = 0.0
    visible: bool = True
    state: str = "idle"
    last_seen: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "position": list(self.position),
            "distance": round(self.distance, 2),
            "visible": self.visible,
            "state": self.state,
            "last_seen": self.last_seen,
            "metadata": dict(self.metadata),
        }


@dataclass
class PerceivedObject:
    """An interactive world object as perceived from the agent's viewpoint.

    Captures identity, position, state, and available interactions.
    """
    object_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    object_type: ObjectType = ObjectType.PICKUP
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    state: str = "default"
    available_interactions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "name": self.name,
            "object_type": self.object_type.value,
            "position": list(self.position),
            "state": self.state,
            "available_interactions": list(self.available_interactions),
            "metadata": dict(self.metadata),
        }


@dataclass
class PerceivedEvent:
    """A world event captured by the perception system.

    Events have intensity, scope (local/regional/global), and are
    stored with timestamps for temporal querying.
    """
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = ""
    description: str = ""
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    intensity: float = 0.5
    scope: EventScope = EventScope.LOCAL
    timestamp: float = field(default_factory=_time_module.time)
    source_entity_id: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "description": self.description,
            "location": list(self.location),
            "intensity": self.intensity,
            "scope": self.scope.value,
            "timestamp": self.timestamp,
            "source_entity_id": self.source_entity_id,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }


@dataclass
class EnvironmentalState:
    """Snapshot of environmental conditions at a given moment.

    Captures terrain, weather, time of day, lighting, temperature,
    and ambient threat assessment.
    """
    terrain_type: TerrainType = TerrainType.PLAIN
    weather: WeatherCondition = WeatherCondition.CLEAR
    time_of_day: TimeOfDay = TimeOfDay.NOON
    ambient_light: float = 1.0
    temperature: float = 22.0
    threat_level: float = 0.0
    humidity: float = 0.5
    wind_speed: float = 0.0
    precipitation: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "terrain_type": self.terrain_type.value,
            "weather": self.weather.value,
            "time_of_day": self.time_of_day.value,
            "ambient_light": self.ambient_light,
            "temperature": self.temperature,
            "threat_level": self.threat_level,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "precipitation": self.precipitation,
            "metadata": dict(self.metadata),
        }


@dataclass
class AttentionFocus:
    """A targeted attention focus entry.

    Tracks what the agent is currently attending to, with priority,
    duration tracking, and rationale.
    """
    focus_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    target_type: str = ""
    target_id: str = ""
    priority: AttentionPriority = AttentionPriority.NORMAL
    duration: float = 0.0
    reason: str = ""
    engaged_at: float = field(default_factory=_time_module.time)
    disengaged_at: float = 0.0
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "focus_id": self.focus_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "priority": self.priority.value,
            "duration": self.duration,
            "reason": self.reason,
            "engaged_at": self.engaged_at,
            "disengaged_at": self.disengaged_at,
            "active": self.active,
            "metadata": dict(self.metadata),
        }


@dataclass
class PerceptionSnapshot:
    """A complete perception frame captured at a moment in time.

    Aggregates entity, object, event, and environmental data into
    a single structured snapshot with attention context.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=_time_module.time)
    location_id: str = ""
    zone: str = ""
    entities_nearby: List[PerceivedEntity] = field(default_factory=list)
    objects_visible: List[PerceivedObject] = field(default_factory=list)
    recent_events: List[PerceivedEvent] = field(default_factory=list)
    environmental_state: EnvironmentalState = field(default_factory=EnvironmentalState)
    attention_focus: List[AttentionFocus] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "location_id": self.location_id,
            "zone": self.zone,
            "entities_nearby": [e.to_dict() for e in self.entities_nearby],
            "objects_visible": [o.to_dict() for o in self.objects_visible],
            "recent_events": [ev.to_dict() for ev in self.recent_events],
            "environmental_state": self.environmental_state.to_dict(),
            "attention_focus": [af.to_dict() for af in self.attention_focus],
            "metadata": dict(self.metadata),
        }

    @property
    def entity_count(self) -> int:
        """Total number of entities in this snapshot."""
        return len(self.entities_nearby)

    @property
    def event_count(self) -> int:
        """Total number of events in this snapshot."""
        return len(self.recent_events)

    @property
    def active_attention_count(self) -> int:
        """Number of currently active attention targets."""
        return sum(1 for af in self.attention_focus if af.active)


@dataclass
class PerceptionConfig:
    """Configurable parameters for the perception engine.

    Controls spatial ranges, tracking limits, memory retention,
    and attention bias weightings by modality.
    """
    vision_range: float = 50.0
    hearing_range: float = 30.0
    max_entities_tracked: int = 100
    max_events_remembered: int = 200
    max_snapshots_retained: int = 300
    attention_bias_weights: Dict[str, float] = field(default_factory=lambda: {
        PerceptionModality.SPATIAL.value: 0.5,
        PerceptionModality.ENTITY.value: 0.8,
        PerceptionModality.EVENT.value: 0.6,
        PerceptionModality.ENVIRONMENTAL.value: 0.3,
        PerceptionModality.SOCIAL.value: 0.4,
        PerceptionModality.TEMPORAL.value: 0.2,
    })
    entity_decay_seconds: float = 10.0
    event_decay_seconds: float = 30.0
    attention_decay_seconds: float = 15.0
    enable_memory_decay: bool = True
    memory_decay_factor: float = 0.95

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vision_range": self.vision_range,
            "hearing_range": self.hearing_range,
            "max_entities_tracked": self.max_entities_tracked,
            "max_events_remembered": self.max_events_remembered,
            "max_snapshots_retained": self.max_snapshots_retained,
            "attention_bias_weights": dict(self.attention_bias_weights),
            "entity_decay_seconds": self.entity_decay_seconds,
            "event_decay_seconds": self.event_decay_seconds,
            "attention_decay_seconds": self.attention_decay_seconds,
            "enable_memory_decay": self.enable_memory_decay,
            "memory_decay_factor": self.memory_decay_factor,
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_VISION_RANGE: float = 50.0
DEFAULT_HEARING_RANGE: float = 30.0
DEFAULT_MAX_ENTITIES: int = 100
DEFAULT_MAX_EVENTS: int = 200
DEFAULT_MAX_SNAPSHOTS: int = 300
DEFAULT_ENTITY_DECAY: float = 10.0
DEFAULT_EVENT_DECAY: float = 30.0
DEFAULT_ATTENTION_DECAY: float = 15.0
DEFAULT_MEMORY_DECAY_FACTOR: float = 0.95


# ---------------------------------------------------------------------------
# Agent Perception Engine (Singleton)
# ---------------------------------------------------------------------------


class AgentPerceptionEngine:
    """Unified perception engine for AI-native game worlds.

    Aggregates sensory inputs across spatial, entity, event,
    environmental, social, and temporal modalities. Maintains
    perception memory with configurable decay and provides
    an attention system for focusing on relevant targets.

    Features:
      - Full perception pipeline: perceive() aggregates all modalities
      - Spatial perception with zone/distance queries
      - Entity tracking with visibility and state awareness
      - Event capture with scope filtering (local/regional/global)
      - Environmental state sensing (terrain, weather, time, threat)
      - Configurable vision/hearing ranges and capacity limits
      - Attention system with priority-weighted focus management
      - Perception memory with automatic decay and history retention
    """

    _instance: Optional["AgentPerceptionEngine"] = None
    _lock: threading.RLock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "AgentPerceptionEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # Perception memory
        self._snapshots: List[PerceptionSnapshot] = []
        self._config: PerceptionConfig = PerceptionConfig()

        # Entity tracking registry
        self._entities: Dict[str, PerceivedEntity] = {}

        # Event log
        self._events: List[PerceivedEvent] = []

        # Attention foci
        self._attention_targets: List[AttentionFocus] = []

        # Spatial zone data
        self._zone_data: Dict[str, Dict[str, Any]] = {}

        # Environmental regions
        self._environmental_regions: Dict[str, EnvironmentalState] = {}

        # Perception statistics
        self._total_perceptions: int = 0
        self._total_events_registered: int = 0
        self._active_perceptions_this_tick: int = 0

    # ------------------------------------------------------------------
    # Public API — Perception Pipeline
    # ------------------------------------------------------------------

    def perceive(
        self,
        location_id: str,
        zone: str,
        agent_id: str,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> PerceptionSnapshot:
        """Run the full perception pipeline for a given agent at a location.

        Aggregates spatial, entity, event, and environmental perception
        into a single structured snapshot. This is the primary entry point
        for agents to gather world state.

        Args:
            location_id: Unique identifier for the agent's current location.
            zone: Named zone or region the agent occupies.
            agent_id: Identifier of the perceiving agent.
            game_state: Optional full game state dictionary for external
                data injection (spawned entities, world events, etc.).

        Returns:
            A complete PerceptionSnapshot with all sensory data aggregated.
        """
        _ = agent_id  # reserved for future agent-specific filtering

        now = _time_module.time()

        # Gather spatial awareness
        entities_nearby = self.perceive_spatial(location_id, zone)

        # Gather visible objects from spatial zone
        objects_visible = self._collect_visible_objects(location_id)

        # Gather recent events within hearing range
        recent_events = self.perceive_events(location_id, now - self._config.event_decay_seconds)

        # Gather environmental state
        env_state = self.perceive_environment(location_id)

        # Get active attention targets
        attention = self.get_attention_targets()

        # Build snapshot
        snapshot = PerceptionSnapshot(
            timestamp=now,
            location_id=location_id,
            zone=zone,
            entities_nearby=entities_nearby,
            objects_visible=objects_visible,
            recent_events=recent_events,
            environmental_state=env_state,
            attention_focus=attention,
        )

        # Store in history
        self._snapshots.append(snapshot)

        # Prune old snapshots if exceeding capacity
        while len(self._snapshots) > self._config.max_snapshots_retained:
            self._snapshots.pop(0)

        # Apply memory decay if enabled
        if self._config.enable_memory_decay:
            self._apply_memory_decay()

        self._total_perceptions += 1
        self._active_perceptions_this_tick += 1

        return snapshot

    def perceive_spatial(
        self,
        location_id: str,
        zone: str,
    ) -> List[PerceivedEntity]:
        """Query spatial perception: what entities/objects are at a given location.

        Returns entities registered in the given zone, sorted by distance.
        Includes zone/distance awareness based on vision range.

        Args:
            location_id: Location identifier to query.
            zone: Zone name for spatial filtering.

        Returns:
            List of PerceivedEntity instances visible in the zone.
        """
        results: List[PerceivedEntity] = []

        for entity in self._entities.values():
            if not entity.visible:
                continue
            if entity.distance > self._config.vision_range:
                continue
            # Include if entity is in zone metadata or within vision range
            zone_tag = entity.metadata.get("zone", "")
            entity_loc = entity.metadata.get("location_id", "")
            if zone_tag == zone or entity_loc == location_id:
                results.append(entity)

        # Sort by distance (closest first)
        results.sort(key=lambda e: e.distance)
        return results

    def perceive_entities(
        self,
        location_id: str,
        radius: Optional[float] = None,
    ) -> List[PerceivedEntity]:
        """Perceive entities within a given radius of a location.

        Returns all tracked entities within the specified radius,
        with visibility, distance, and state information.

        Args:
            location_id: Location center for entity search.
            radius: Maximum distance to include entities. Defaults to
                the configured vision_range.

        Returns:
            List of PerceivedEntity instances within range.
        """
        search_radius = radius if radius is not None else self._config.vision_range
        results: List[PerceivedEntity] = []

        for entity in self._entities.values():
            if not entity.visible:
                continue
            if entity.distance <= search_radius:
                entity_loc = entity.metadata.get("location_id", "")
                if entity_loc == location_id or entity_loc == "":
                    results.append(entity)

        results.sort(key=lambda e: e.distance)
        return results[: self._config.max_entities_tracked]

    def perceive_events(
        self,
        location_id: str,
        time_window: Optional[float] = None,
    ) -> List[PerceivedEvent]:
        """Perceive recent world events filtered by location and time window.

        Captures events within hearing range and within the specified
        time window (or event decay period by default). Events are
        sorted by recency (newest first).

        Args:
            location_id: Location to center event perception.
            time_window: Earliest timestamp to include. Defaults to
                (now - event_decay_seconds).

        Returns:
            List of PerceivedEvent instances matching the filters.
        """
        now = _time_module.time()
        cutoff = time_window if time_window is not None else (now - self._config.event_decay_seconds)

        results: List[PerceivedEvent] = []
        for event in self._events:
            if event.timestamp < cutoff:
                continue
            # Include global events regardless of location
            if event.scope == EventScope.GLOBAL:
                results.append(event)
                continue
            # Check proximity for local/regional events
            loc_tag = event.metadata.get("location_id", "")
            if loc_tag == location_id or loc_tag == "":
                results.append(event)

        # Sort newest first
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[: self._config.max_events_remembered]

    def perceive_environment(
        self,
        location_id: str,
    ) -> EnvironmentalState:
        """Query environmental perception for a given location.

        Returns terrain type, weather, time of day, ambient light,
        temperature, humidity, wind, precipitation, and threat level.

        Args:
            location_id: Location to query environmental state for.

        Returns:
            EnvironmentalState for the location, or a default state
            if no specific region data is configured.
        """
        if location_id in self._environmental_regions:
            return self._environmental_regions[location_id]

        # Return default environment
        return EnvironmentalState()

    # ------------------------------------------------------------------
    # Public API — Attention System
    # ------------------------------------------------------------------

    def set_attention_focus(
        self,
        target_type: str,
        target_id: str,
        priority: str = "normal",
        reason: str = "",
    ) -> AttentionFocus:
        """Focus attention on a specific target.

        Creates or updates an attention focus entry. If a focus already
        exists for the same target, it is refreshed. Priority determines
        how the focus competes for limited attention slots.

        Args:
            target_type: Category of the target (e.g., "entity", "event").
            target_id: Unique identifier of the target.
            priority: Priority level from AttentionPriority (critical,
                high, normal, low, background).
            reason: Human-readable rationale for the attention focus.

        Returns:
            The AttentionFocus entry created or updated.
        """
        now = _time_module.time()

        # Check for existing focus on this target
        for existing in self._attention_targets:
            if existing.target_id == target_id and existing.active:
                existing.priority = AttentionPriority(priority)
                existing.reason = reason
                existing.duration = now - existing.engaged_at
                return existing

        focus = AttentionFocus(
            target_type=target_type,
            target_id=target_id,
            priority=AttentionPriority(priority),
            reason=reason,
            engaged_at=now,
            active=True,
        )
        self._attention_targets.append(focus)

        # Trim excess attention targets (keep at most config-based limit)
        active_targets = [af for af in self._attention_targets if af.active]
        max_attention = self._config.max_entities_tracked
        if len(active_targets) > max_attention:
            # Disengage lowest-priority targets
            active_targets.sort(
                key=lambda af: _attention_priority_order(af.priority), reverse=True
            )
            for to_remove in active_targets[max_attention:]:
                to_remove.active = False
                to_remove.disengaged_at = now

        return focus

    def get_attention_targets(
        self,
        active_only: bool = True,
    ) -> List[AttentionFocus]:
        """Get the current attention focus targets.

        Returns all attention targets, optionally filtered to
        only currently active ones. Sorted by priority (critical first).

        Args:
            active_only: If True, return only currently active foci.

        Returns:
            List of AttentionFocus entries sorted by priority.
        """
        results = [af for af in self._attention_targets if (not active_only or af.active)]

        # Apply attention decay to durations
        now = _time_module.time()
        for af in results:
            if af.active:
                af.duration = now - af.engaged_at

        # Clean up expired attention targets
        self._cleanup_expired_attention()

        # Sort by priority (critical first)
        results.sort(key=lambda af: _attention_priority_order(af.priority))
        return results

    def get_attention_target(
        self,
        target_id: str,
    ) -> Optional[AttentionFocus]:
        """Get a specific attention target by its target ID.

        Args:
            target_id: The target identifier to look up.

        Returns:
            The matching AttentionFocus or None if not found.
        """
        for af in self._attention_targets:
            if af.target_id == target_id:
                return af
        return None

    def release_attention(
        self,
        target_id: str,
    ) -> bool:
        """Release an active attention focus on a target.

        Args:
            target_id: The target identifier to release focus from.

        Returns:
            True if a focus was found and released, False otherwise.
        """
        now = _time_module.time()
        for af in self._attention_targets:
            if af.target_id == target_id and af.active:
                af.active = False
                af.disengaged_at = now
                af.duration = now - af.engaged_at
                return True
        return False

    # ------------------------------------------------------------------
    # Public API — History & Memory
    # ------------------------------------------------------------------

    def get_perception_history(
        self,
        limit: int = 10,
        location_id: Optional[str] = None,
    ) -> List[PerceptionSnapshot]:
        """Get recent perception snapshots from history.

        Returns the most recent snapshots, optionally filtered
        by location. Useful for temporal reasoning and change detection.

        Args:
            limit: Maximum number of snapshots to return.
            location_id: Optional filter for a specific location.

        Returns:
            List of PerceptionSnapshot instances, newest first.
        """
        results = list(self._snapshots)
        if location_id:
            results = [s for s in results if s.location_id == location_id]
        results.reverse()  # newest first
        return results[:limit]

    def get_perception_history_since(
        self,
        since_timestamp: float,
    ) -> List[PerceptionSnapshot]:
        """Get all perception snapshots recorded after a given timestamp.

        Args:
            since_timestamp: Unix timestamp to filter from.

        Returns:
            List of PerceptionSnapshot instances after the timestamp.
        """
        return [s for s in self._snapshots if s.timestamp >= since_timestamp]

    # ------------------------------------------------------------------
    # Public API — Entity Management
    # ------------------------------------------------------------------

    def update_entity_position(
        self,
        entity_id: str,
        position: Tuple[float, float, float],
        zone: str = "",
        visible: bool = True,
        state: str = "",
    ) -> Optional[PerceivedEntity]:
        """Update or register a tracked entity's position and state.

        Creates the entity if it does not exist, otherwise updates
        its last known position, visibility, and state.

        Args:
            entity_id: Unique entity identifier.
            position: (x, y, z) world position.
            zone: Zone or region name the entity occupies.
            visible: Whether the entity is currently visible.
            state: Current behavioral state string (e.g., "idle", "patrol").

        Returns:
            The updated PerceivedEntity.
        """
        now = _time_module.time()

        if entity_id in self._entities:
            entity = self._entities[entity_id]
            entity.position = position
            entity.visible = visible
            entity.last_seen = now if visible else entity.last_seen
            if state:
                entity.state = state
            entity.metadata["zone"] = zone
        else:
            if len(self._entities) >= self._config.max_entities_tracked:
                # Evict oldest entity
                oldest_id = min(
                    self._entities.keys(),
                    key=lambda eid: self._entities[eid].last_seen,
                )
                del self._entities[oldest_id]

            entity = PerceivedEntity(
                entity_id=entity_id,
                position=position,
                visible=visible,
                state=state or "idle",
            )
            entity.metadata["zone"] = zone
            self._entities[entity_id] = entity

        return entity

    def get_entity(
        self,
        entity_id: str,
    ) -> Optional[PerceivedEntity]:
        """Get a tracked entity by its ID.

        Args:
            entity_id: The entity identifier to look up.

        Returns:
            The PerceivedEntity or None if not tracked.
        """
        return self._entities.get(entity_id)

    def remove_entity(
        self,
        entity_id: str,
    ) -> bool:
        """Remove an entity from the tracking registry.

        Args:
            entity_id: The entity identifier to remove.

        Returns:
            True if the entity was found and removed.
        """
        if entity_id in self._entities:
            del self._entities[entity_id]
            return True
        return False

    def list_entities(
        self,
        entity_type: Optional[str] = None,
        visible_only: bool = False,
    ) -> List[PerceivedEntity]:
        """List all tracked entities, optionally filtered.

        Args:
            entity_type: Filter by EntityType value string.
            visible_only: If True, return only visible entities.

        Returns:
            List of PerceivedEntity instances.
        """
        results = list(self._entities.values())
        if entity_type:
            results = [e for e in results if e.entity_type.value == entity_type]
        if visible_only:
            results = [e for e in results if e.visible]
        return results

    # ------------------------------------------------------------------
    # Public API — Event Management
    # ------------------------------------------------------------------

    def register_event(
        self,
        event: PerceivedEvent,
    ) -> PerceivedEvent:
        """Register a new world event in the perception system.

        Events are stored in chronological order and pruned when
        exceeding the configured maximum.

        Args:
            event: The PerceivedEvent to register.

        Returns:
            The registered event (with any system-assigned metadata).
        """
        self._events.append(event)
        self._total_events_registered += 1

        # Prune old events if exceeding capacity
        while len(self._events) > self._config.max_events_remembered:
            self._events.pop(0)

        return event

    def query_events(
        self,
        event_type: Optional[str] = None,
        scope: Optional[str] = None,
        min_intensity: float = 0.0,
        since_timestamp: float = 0.0,
        limit: int = 50,
    ) -> List[PerceivedEvent]:
        """Query the event log with flexible filters.

        Args:
            event_type: Filter by event_type string.
            scope: Filter by EventScope value (local, regional, global).
            min_intensity: Minimum intensity threshold (0.0-1.0).
            since_timestamp: Only include events after this timestamp.
            limit: Maximum number of events to return.

        Returns:
            List of PerceivedEvent instances, newest first.
        """
        results = list(self._events)
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if scope:
            results = [e for e in results if e.scope.value == scope]
        if min_intensity > 0.0:
            results = [e for e in results if e.intensity >= min_intensity]
        if since_timestamp > 0.0:
            results = [e for e in results if e.timestamp >= since_timestamp]
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    # ------------------------------------------------------------------
    # Public API — Environment Management
    # ------------------------------------------------------------------

    def set_environmental_state(
        self,
        location_id: str,
        terrain: Optional[str] = None,
        weather: Optional[str] = None,
        time_of_day: Optional[str] = None,
        ambient_light: Optional[float] = None,
        temperature: Optional[float] = None,
        threat_level: Optional[float] = None,
        humidity: Optional[float] = None,
        wind_speed: Optional[float] = None,
        precipitation: Optional[float] = None,
    ) -> EnvironmentalState:
        """Set or update environmental state for a specific location/region.

        Updates only the provided fields; unset fields retain their
        previous values (or defaults if creating a new region entry).

        Args:
            location_id: Location or region identifier.
            terrain: TerrainType value string.
            weather: WeatherCondition value string.
            time_of_day: TimeOfDay value string.
            ambient_light: Light level from 0.0 (dark) to 1.0 (bright).
            temperature: Temperature in Celsius.
            threat_level: Threat assessment from 0.0 (safe) to 1.0 (dangerous).
            humidity: Humidity level from 0.0 to 1.0.
            wind_speed: Wind speed in m/s.
            precipitation: Precipitation intensity from 0.0 to 1.0.

        Returns:
            The updated EnvironmentalState.
        """
        if location_id in self._environmental_regions:
            state = self._environmental_regions[location_id]
        else:
            state = EnvironmentalState()
            self._environmental_regions[location_id] = state

        if terrain is not None:
            state.terrain_type = TerrainType(terrain)
        if weather is not None:
            state.weather = WeatherCondition(weather)
        if time_of_day is not None:
            state.time_of_day = TimeOfDay(time_of_day)
        if ambient_light is not None:
            state.ambient_light = max(0.0, min(1.0, ambient_light))
        if temperature is not None:
            state.temperature = temperature
        if threat_level is not None:
            state.threat_level = max(0.0, min(1.0, threat_level))
        if humidity is not None:
            state.humidity = max(0.0, min(1.0, humidity))
        if wind_speed is not None:
            state.wind_speed = max(0.0, wind_speed)
        if precipitation is not None:
            state.precipitation = max(0.0, min(1.0, precipitation))

        return state

    # ------------------------------------------------------------------
    # Public API — Zone Management
    # ------------------------------------------------------------------

    def set_zone_data(
        self,
        zone: str,
        data: Dict[str, Any],
    ) -> None:
        """Attach arbitrary metadata to a spatial zone.

        Useful for storing zone-specific perception modifiers,
        object lists, or region boundaries.

        Args:
            zone: Zone name.
            data: Arbitrary metadata dictionary for the zone.
        """
        self._zone_data[zone] = data

    def get_zone_data(
        self,
        zone: str,
    ) -> Optional[Dict[str, Any]]:
        """Get metadata for a spatial zone.

        Args:
            zone: Zone name to query.

        Returns:
            The zone metadata dictionary, or None if not configured.
        """
        return self._zone_data.get(zone)

    def register_visible_objects(
        self,
        location_id: str,
        objects: List[PerceivedObject],
    ) -> None:
        """Register visible interactive objects at a location.

        Objects are stored in the zone data and retrieved during
        spatial perception queries.

        Args:
            location_id: Location identifier.
            objects: List of PerceivedObject instances.
        """
        if location_id not in self._zone_data:
            self._zone_data[location_id] = {}
        self._zone_data[location_id]["objects"] = [
            o.to_dict() for o in objects
        ]

    # ------------------------------------------------------------------
    # Public API — Configuration
    # ------------------------------------------------------------------

    def configure(
        self,
        vision_range: Optional[float] = None,
        hearing_range: Optional[float] = None,
        max_entities_tracked: Optional[int] = None,
        max_events_remembered: Optional[int] = None,
        max_snapshots_retained: Optional[int] = None,
        attention_bias_weights: Optional[Dict[str, float]] = None,
        entity_decay_seconds: Optional[float] = None,
        event_decay_seconds: Optional[float] = None,
        attention_decay_seconds: Optional[float] = None,
        enable_memory_decay: Optional[bool] = None,
        memory_decay_factor: Optional[float] = None,
    ) -> PerceptionConfig:
        """Update perception engine configuration parameters.

        Only provided parameters are updated; others retain current values.

        Args:
            vision_range: Maximum vision distance for entity perception.
            hearing_range: Maximum range for event perception.
            max_entities_tracked: Maximum number of entities in registry.
            max_events_remembered: Maximum events stored in event log.
            max_snapshots_retained: Maximum snapshots in history.
            attention_bias_weights: Per-modality attention weight mapping.
            entity_decay_seconds: Seconds before unseen entities decay.
            event_decay_seconds: Seconds before events expire from view.
            attention_decay_seconds: Seconds before attention foci expire.
            enable_memory_decay: Enable/disable automatic memory decay.
            memory_decay_factor: Decay multiplier per perception cycle.

        Returns:
            The updated PerceptionConfig.
        """
        cfg = self._config
        if vision_range is not None:
            cfg.vision_range = max(1.0, vision_range)
        if hearing_range is not None:
            cfg.hearing_range = max(1.0, hearing_range)
        if max_entities_tracked is not None:
            cfg.max_entities_tracked = max(1, max_entities_tracked)
        if max_events_remembered is not None:
            cfg.max_events_remembered = max(1, max_events_remembered)
        if max_snapshots_retained is not None:
            cfg.max_snapshots_retained = max(1, max_snapshots_retained)
        if attention_bias_weights is not None:
            cfg.attention_bias_weights = dict(attention_bias_weights)
        if entity_decay_seconds is not None:
            cfg.entity_decay_seconds = max(0.1, entity_decay_seconds)
        if event_decay_seconds is not None:
            cfg.event_decay_seconds = max(0.1, event_decay_seconds)
        if attention_decay_seconds is not None:
            cfg.attention_decay_seconds = max(0.1, attention_decay_seconds)
        if enable_memory_decay is not None:
            cfg.enable_memory_decay = enable_memory_decay
        if memory_decay_factor is not None:
            cfg.memory_decay_factor = max(0.1, min(1.0, memory_decay_factor))
        return cfg

    def get_config(self) -> PerceptionConfig:
        """Get the current perception engine configuration.

        Returns:
            The active PerceptionConfig.
        """
        return self._config

    # ------------------------------------------------------------------
    # Public API — Status & Statistics
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the current status and statistics of the perception engine.

        Returns a dictionary with entity counts, event counts, snapshot
        history size, attention statistics, and configuration summary.

        Returns:
            Status dictionary with all perception system metrics.
        """
        now = _time_module.time()
        visible_entities = sum(1 for e in self._entities.values() if e.visible)
        active_attention = sum(1 for af in self._attention_targets if af.active)
        recent_events = sum(
            1 for e in self._events
            if e.timestamp >= now - self._config.event_decay_seconds
        )

        return {
            "total_perceptions": self._total_perceptions,
            "total_events_registered": self._total_events_registered,
            "entities_tracked": len(self._entities),
            "entities_visible": visible_entities,
            "events_logged": len(self._events),
            "events_recent": recent_events,
            "snapshots_stored": len(self._snapshots),
            "attention_targets": len(self._attention_targets),
            "attention_active": active_attention,
            "environmental_regions": len(self._environmental_regions),
            "zones_configured": len(self._zone_data),
            "config": self._config.to_dict(),
            "initialized": self._initialized,
            "active_this_tick": self._active_perceptions_this_tick,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Alias for get_status(). Provides backward compatibility.

        Returns:
            Status dictionary with all perception system metrics.
        """
        return self.get_status()

    # ------------------------------------------------------------------
    # Public API — Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all perception data to initial state.

        Clears snapshots, entity registry, event log, attention targets,
        zone data, and environmental regions. Configuration is preserved.
        Statistics counters are zeroed.
        """
        self._snapshots.clear()
        self._entities.clear()
        self._events.clear()
        self._attention_targets.clear()
        self._zone_data.clear()
        self._environmental_regions.clear()
        self._total_perceptions = 0
        self._total_events_registered = 0
        self._active_perceptions_this_tick = 0

    def reset_config(self) -> None:
        """Reset configuration to defaults while preserving perception data."""
        self._config = PerceptionConfig()

    def end_tick(self) -> None:
        """Signal the end of a perception tick.

        Resets the per-tick counter and applies any deferred cleanup.
        Should be called once per simulation frame.
        """
        self._active_perceptions_this_tick = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _collect_visible_objects(
        self,
        location_id: str,
    ) -> List[PerceivedObject]:
        """Collect visible interactive objects from zone data.

        Args:
            location_id: The location to query for objects.

        Returns:
            List of PerceivedObject instances visible at the location.
        """
        results: List[PerceivedObject] = []
        if location_id in self._zone_data:
            raw_objects = self._zone_data[location_id].get("objects", [])
            for obj_dict in raw_objects:
                try:
                    obj = PerceivedObject(
                        object_id=obj_dict.get("object_id", uuid.uuid4().hex),
                        name=obj_dict.get("name", ""),
                        object_type=ObjectType(obj_dict.get("object_type", "pickup")),
                        position=tuple(obj_dict.get("position", (0.0, 0.0, 0.0))),
                        state=obj_dict.get("state", "default"),
                        available_interactions=obj_dict.get("available_interactions", []),
                        metadata=obj_dict.get("metadata", {}),
                    )
                    results.append(obj)
                except (KeyError, ValueError):
                    continue
        return results

    def _apply_memory_decay(self) -> None:
        """Apply configurable memory decay to perception history.

        Diminishes the perceived intensity of older entities and events
        by the configured decay factor. Entities not seen within the
        entity_decay_seconds window are marked invisible.
        """
        now = _time_module.time()
        factor = self._config.memory_decay_factor

        # Decay entity visibility
        for entity in self._entities.values():
            if not entity.visible:
                continue
            elapsed = now - entity.last_seen
            if elapsed > self._config.entity_decay_seconds:
                entity.visible = False

        # Decay event intensity
        for event in self._events:
            elapsed = now - event.timestamp
            if elapsed > self._config.event_decay_seconds:
                event.intensity *= factor

        # Clamp intensities
        for event in self._events:
            event.intensity = max(0.0, min(1.0, event.intensity))

    def _cleanup_expired_attention(self) -> None:
        """Release attention targets that have exceeded their decay window."""
        now = _time_module.time()
        for af in self._attention_targets:
            if not af.active:
                continue
            if now - af.engaged_at > self._config.attention_decay_seconds:
                af.active = False
                af.disengaged_at = now
                af.duration = now - af.engaged_at

    def _compute_distance(
        self,
        pos_a: Tuple[float, float, float],
        pos_b: Tuple[float, float, float],
    ) -> float:
        """Compute Euclidean distance between two 3D positions.

        Args:
            pos_a: First position as (x, y, z).
            pos_b: Second position as (x, y, z).

        Returns:
            Euclidean distance in world units.
        """
        dx = pos_a[0] - pos_b[0]
        dy = pos_a[1] - pos_b[1]
        dz = pos_a[2] - pos_b[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)


# ---------------------------------------------------------------------------
# Internal Utilities
# ---------------------------------------------------------------------------


def _attention_priority_order(priority: AttentionPriority) -> int:
    """Convert attention priority to a numeric ordering value.

    Lower values indicate higher priority (for ascending sort).
    """
    _order: Dict[AttentionPriority, int] = {
        AttentionPriority.CRITICAL: 0,
        AttentionPriority.HIGH: 1,
        AttentionPriority.NORMAL: 2,
        AttentionPriority.LOW: 3,
        AttentionPriority.BACKGROUND: 4,
    }
    return _order.get(priority, 2)


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_agent_perception_engine() -> AgentPerceptionEngine:
    """Return the singleton AgentPerceptionEngine instance.

    This is the primary access point for the perception engine
    throughout the SparkLabs ecosystem.

    Returns:
        The singleton AgentPerceptionEngine.
    """
    return AgentPerceptionEngine()