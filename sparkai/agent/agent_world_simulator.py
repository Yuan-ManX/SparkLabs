"""
SparkLabs Agent World Simulator

Provides autonomous world simulation capabilities for AI-native game worlds.
Characters make decisions, interact with the environment, form relationships,
and drive emergent narratives without pre-scripted storylines.

Core architecture:
  - Entity Management: Tracks all world entities and their states
  - Decision Engine: Autonomous decision-making for NPCs
  - Interaction System: Entity-to-entity and entity-to-environment interactions
  - Time Progression: Day/night cycles, seasons, and temporal events
  - State Persistence: World state snapshots and timeline management
  - Event System: Broadcast and reactive event handling
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DayPhase(Enum):
    """Phases of the day/night cycle."""
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    EVENING = "evening"
    NIGHT = "night"
    MIDNIGHT = "midnight"


class Season(Enum):
    """Seasons affecting world behavior."""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class EntityType(Enum):
    """Types of entities in the simulated world."""
    CHARACTER = "character"
    ITEM = "item"
    STRUCTURE = "structure"
    LOCATION = "location"
    FACTION = "faction"
    RESOURCE = "resource"
    EVENT = "event"


class EntityState(Enum):
    """Operational states for world entities."""
    ACTIVE = "active"
    IDLE = "idle"
    SLEEPING = "sleeping"
    BUSY = "busy"
    DISABLED = "disabled"
    DESTROYED = "destroyed"


class InteractionType(Enum):
    """Types of interactions between entities."""
    SOCIAL = "social"
    COMBAT = "combat"
    TRADE = "trade"
    EXPLORE = "explore"
    GATHER = "gather"
    BUILD = "build"
    TRAVEL = "travel"
    REST = "rest"
    DIALOGUE = "dialogue"
    QUEST = "quest"


class EventCategory(Enum):
    """Categories of world events."""
    NATURAL = "natural"
    SOCIAL = "social"
    POLITICAL = "political"
    ECONOMIC = "economic"
    MYSTICAL = "mystical"
    PLAYER_ACTION = "player_action"
    RANDOM = "random"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SimEntity:
    """A simulated entity in the world."""
    entity_id: str
    name: str
    entity_type: EntityType
    state: EntityState = EntityState.ACTIVE
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    properties: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, float] = field(default_factory=dict)
    inventory: List[str] = field(default_factory=list)
    memory: List[str] = field(default_factory=list)
    current_goal: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_updated_at: float = field(default_factory=time.time)


@dataclass
class WorldInteraction:
    """An interaction between two entities in the world."""
    interaction_id: str
    source_id: str
    target_id: str
    interaction_type: InteractionType
    description: str
    outcome: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    succeeded: bool = True
    timestamp: float = field(default_factory=time.time)


@dataclass
class WorldEvent:
    """A world-level event that affects multiple entities."""
    event_id: str
    category: EventCategory
    name: str
    description: str
    affected_entities: List[str] = field(default_factory=list)
    affected_regions: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    intensity: float = 0.5
    resolved: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class WorldStateSnapshot:
    """A complete snapshot of the world state at a point in time."""
    snapshot_id: str
    tick: int
    day_phase: DayPhase
    season: Season
    active_entities: int
    pending_events: int
    interactions_this_tick: int
    world_data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# World Simulator Engine
# ---------------------------------------------------------------------------

class WorldSimulatorEngine:
    """Autonomous world simulation engine for AI-native game worlds.

    Drives a living, breathing game world where entities make autonomous
    decisions, interact with each other, and respond to world events.
    Supports multi-day evolution with persistent state and timeline
    management.

    Usage:
        engine = get_world_simulator_engine()
        entity = engine.create_entity("Village Elder", "character", position={"x": 100, "y": 200})
        engine.simulate_tick()
        snapshot = engine.get_world_state()
    """

    _instance: Optional["WorldSimulatorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_ENTITIES: int = 10000
    MAX_INTERACTIONS_PER_TICK: int = 500
    MAX_EVENTS: int = 1000
    TICK_DURATION_MS: float = 1000.0  # 1 second per tick
    DAY_TICKS: int = 86400  # Ticks per in-game day

    def __new__(cls) -> "WorldSimulatorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "WorldSimulatorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        time.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._entities: Dict[str, SimEntity] = {}
            self._interactions: List[WorldInteraction] = []
            self._events: Dict[str, WorldEvent] = []
            self._snapshots: Dict[str, WorldStateSnapshot] = {}
            self._tick: int = 0
            self._day: int = 1
            self._day_phase: DayPhase = DayPhase.MORNING
            self._season: Season = Season.SPRING
            self._simulation_speed: float = 1.0
            self._is_running: bool = False
            self._total_entities_created: int = 0
            self._total_interactions: int = 0
            self._total_events: int = 0
            self._initialized = True

    # ------------------------------------------------------------------
    # Entity Management
    # ------------------------------------------------------------------

    def create_entity(
        self,
        name: str,
        entity_type: str,
        position: Optional[Dict[str, float]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> SimEntity:
        """Create a new entity in the simulated world.

        Args:
            name: Display name for the entity.
            entity_type: Type of entity (character, item, structure, etc.).
            position: World position coordinates.
            properties: Custom properties for the entity.

        Returns:
            The created SimEntity.
        """
        time.sleep(0.001)
        with self._lock:
            entity = SimEntity(
                entity_id=uuid.uuid4().hex,
                name=name,
                entity_type=EntityType(entity_type),
                position=position or {"x": 0.0, "y": 0.0},
                properties=properties or {},
            )
            self._entities[entity.entity_id] = entity
            self._total_entities_created += 1
            return entity

    def update_entity(
        self,
        entity_id: str,
        updates: Dict[str, Any],
    ) -> Optional[SimEntity]:
        """Update properties of an existing entity.

        Args:
            entity_id: The entity to update.
            updates: Dictionary of properties to update.

        Returns:
            The updated entity, or None if not found.
        """
        with self._lock:
            if entity_id not in self._entities:
                return None

            entity = self._entities[entity_id]

            if "state" in updates:
                entity.state = EntityState(updates["state"])
            if "position" in updates:
                entity.position.update(updates["position"])
            if "properties" in updates:
                entity.properties.update(updates["properties"])
            if "current_goal" in updates:
                entity.current_goal = updates["current_goal"]

            entity.last_updated_at = time.time()
            return entity

    def get_entity(self, entity_id: str) -> Optional[SimEntity]:
        """Get an entity by ID."""
        with self._lock:
            return self._entities.get(entity_id)

    def get_entities_in_region(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        entity_type: Optional[str] = None,
    ) -> List[SimEntity]:
        """Get entities within a circular region.

        Args:
            center_x: Center X coordinate.
            center_y: Center Y coordinate.
            radius: Search radius.
            entity_type: Optional filter by entity type.

        Returns:
            List of entities within the region.
        """
        with self._lock:
            results = []
            for entity in self._entities.values():
                if entity.state in (EntityState.DISABLED, EntityState.DESTROYED):
                    continue
                if entity_type and entity.entity_type.value != entity_type:
                    continue

                dx = entity.position.get("x", 0) - center_x
                dy = entity.position.get("y", 0) - center_y
                if (dx * dx + dy * dy) <= radius * radius:
                    results.append(entity)

            return results

    # ------------------------------------------------------------------
    # Interaction System
    # ------------------------------------------------------------------

    def create_interaction(
        self,
        source_id: str,
        target_id: str,
        interaction_type: str,
        description: str,
        outcome: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorldInteraction]:
        """Create an interaction between two entities.

        Args:
            source_id: Initiating entity ID.
            target_id: Target entity ID.
            interaction_type: Type of interaction.
            description: Description of the interaction.
            outcome: Outcome data for the interaction.

        Returns:
            The created WorldInteraction, or None if entities not found.
        """
        time.sleep(0.001)
        with self._lock:
            if source_id not in self._entities or target_id not in self._entities:
                return None

            interaction = WorldInteraction(
                interaction_id=uuid.uuid4().hex,
                source_id=source_id,
                target_id=target_id,
                interaction_type=InteractionType(interaction_type),
                description=description,
                outcome=outcome or {},
            )

            self._interactions.append(interaction)
            self._total_interactions += 1

            # Update relationships
            source = self._entities[source_id]
            current_relation = source.relationships.get(target_id, 0.0)
            source.relationships[target_id] = current_relation + 0.1

            # Prune old interactions
            if len(self._interactions) > self.MAX_INTERACTIONS_PER_TICK * 10:
                self._interactions = self._interactions[-self.MAX_INTERACTIONS_PER_TICK * 5:]

            return interaction

    # ------------------------------------------------------------------
    # Event System
    # ------------------------------------------------------------------

    def broadcast_event(
        self,
        category: str,
        name: str,
        description: str,
        affected_entities: Optional[List[str]] = None,
        affected_regions: Optional[List[str]] = None,
        intensity: float = 0.5,
    ) -> WorldEvent:
        """Broadcast a world event affecting multiple entities.

        Args:
            category: Event category.
            name: Event name.
            description: Event description.
            affected_entities: Entities affected by this event.
            affected_regions: Regions affected by this event.
            intensity: Event intensity (0.0 to 1.0).

        Returns:
            The created WorldEvent.
        """
        time.sleep(0.001)
        with self._lock:
            event = WorldEvent(
                event_id=uuid.uuid4().hex,
                category=EventCategory(category),
                name=name,
                description=description,
                affected_entities=affected_entities or [],
                affected_regions=affected_regions or [],
                intensity=intensity,
            )

            self._events.append(event)
            self._total_events += 1

            # Prune old events
            if len(self._events) > self.MAX_EVENTS:
                self._events = self._events[-self.MAX_EVENTS:]

            return event

    def resolve_event(self, event_id: str) -> Optional[WorldEvent]:
        """Mark a world event as resolved."""
        with self._lock:
            for event in self._events:
                if event.event_id == event_id:
                    event.resolved = True
                    event.duration_ms = (time.time() - event.timestamp) * 1000
                    return event
            return None

    # ------------------------------------------------------------------
    # Time Progression
    # ------------------------------------------------------------------

    def simulate_tick(self, num_ticks: int = 1) -> WorldStateSnapshot:
        """Advance the simulation by one or more ticks.

        Each tick processes entity states, interactions, and events.
        Updates the day/night cycle and seasonal progression.

        Args:
            num_ticks: Number of ticks to simulate.

        Returns:
            WorldStateSnapshot after the simulation.
        """
        time.sleep(0.001)
        with self._lock:
            for _ in range(num_ticks):
                self._tick += 1

                # Update day phase
                tick_in_day = self._tick % self.DAY_TICKS
                self._day_phase = self._calculate_day_phase(tick_in_day)

                # Advance day
                if tick_in_day == 0 and self._tick > 0:
                    self._day += 1

                # Update season
                if self._tick % (self.DAY_TICKS * 30) == 0:
                    self._advance_season()

                # Process entity states
                self._process_entity_states()

                # Process pending events
                self._process_events()

            # Create snapshot
            snapshot = WorldStateSnapshot(
                snapshot_id=uuid.uuid4().hex,
                tick=self._tick,
                day_phase=self._day_phase,
                season=self._season,
                active_entities=sum(
                    1 for e in self._entities.values()
                    if e.state == EntityState.ACTIVE
                ),
                pending_events=sum(
                    1 for e in self._events if not e.resolved
                ),
                interactions_this_tick=len(self._interactions),
            )
            self._snapshots[snapshot.snapshot_id] = snapshot

            return snapshot

    def _calculate_day_phase(self, tick_in_day: int) -> DayPhase:
        """Calculate the day phase based on tick position."""
        segment = self.DAY_TICKS // 8
        if tick_in_day < segment:
            return DayPhase.DAWN
        elif tick_in_day < segment * 2:
            return DayPhase.MORNING
        elif tick_in_day < segment * 3:
            return DayPhase.NOON
        elif tick_in_day < segment * 4:
            return DayPhase.AFTERNOON
        elif tick_in_day < segment * 5:
            return DayPhase.DUSK
        elif tick_in_day < segment * 6:
            return DayPhase.EVENING
        elif tick_in_day < segment * 7:
            return DayPhase.NIGHT
        else:
            return DayPhase.MIDNIGHT

    def _advance_season(self) -> None:
        """Advance to the next season."""
        season_order = [Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER]
        idx = season_order.index(self._season)
        self._season = season_order[(idx + 1) % 4]

    def _process_entity_states(self) -> None:
        """Process entity state transitions based on time and conditions."""
        for entity in list(self._entities.values()):
            if entity.state == EntityState.DESTROYED:
                continue

            # Characters sleep at night
            if entity.entity_type == EntityType.CHARACTER:
                if self._day_phase in (DayPhase.NIGHT, DayPhase.MIDNIGHT):
                    if entity.state == EntityState.ACTIVE:
                        entity.state = EntityState.SLEEPING
                elif self._day_phase == DayPhase.DAWN:
                    if entity.state == EntityState.SLEEPING:
                        entity.state = EntityState.ACTIVE

            entity.last_updated_at = time.time()

    def _process_events(self) -> None:
        """Process active world events."""
        for event in list(self._events):
            if event.resolved:
                continue

            # Apply event effects to affected entities
            for entity_id in event.affected_entities:
                if entity_id in self._entities:
                    entity = self._entities[entity_id]
                    entity.memory.append(f"Event: {event.name} - {event.description}")

                    # Keep memory bounded
                    if len(entity.memory) > 50:
                        entity.memory = entity.memory[-50:]

    # ------------------------------------------------------------------
    # Timeline Management
    # ------------------------------------------------------------------

    def create_timeline_branch(
        self,
        branch_name: str,
        from_tick: Optional[int] = None,
    ) -> str:
        """Create a branch in the world timeline.

        Args:
            branch_name: Name for the new timeline branch.
            from_tick: Starting tick for the branch (defaults to current).

        Returns:
            The branch identifier.
        """
        time.sleep(0.001)
        with self._lock:
            branch_id = f"timeline_{branch_name}_{uuid.uuid4().hex[:8]}"
            source_tick = from_tick or self._tick

            # Save current state as branch point
            snapshot = WorldStateSnapshot(
                snapshot_id=branch_id,
                tick=source_tick,
                day_phase=self._day_phase,
                season=self._season,
                active_entities=len(self._entities),
                pending_events=len(self._events),
                interactions_this_tick=len(self._interactions),
            )
            self._snapshots[branch_id] = snapshot

            return branch_id

    def restore_timeline(self, snapshot_id: str) -> bool:
        """Restore the world to a previous snapshot.

        Args:
            snapshot_id: The snapshot to restore from.

        Returns:
            True if successful, False if snapshot not found.
        """
        with self._lock:
            if snapshot_id not in self._snapshots:
                return False

            snapshot = self._snapshots[snapshot_id]
            self._tick = snapshot.tick
            self._day_phase = snapshot.day_phase
            self._season = snapshot.season
            return True

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_world_state(self) -> Dict[str, Any]:
        """Get the current world state summary."""
        with self._lock:
            return {
                "tick": self._tick,
                "day": self._day,
                "day_phase": self._day_phase.value,
                "season": self._season.value,
                "total_entities": len(self._entities),
                "active_entities": sum(
                    1 for e in self._entities.values()
                    if e.state == EntityState.ACTIVE
                ),
                "pending_events": sum(
                    1 for e in self._events if not e.resolved
                ),
                "total_interactions": self._total_interactions,
                "total_events": self._total_events,
                "is_running": self._is_running,
            }

    def get_simulation_stats(self) -> Dict[str, Any]:
        """Get comprehensive simulation statistics."""
        with self._lock:
            entity_type_counts = {}
            for entity in self._entities.values():
                etype = entity.entity_type.value
                entity_type_counts[etype] = entity_type_counts.get(etype, 0) + 1

            return {
                **self.get_world_state(),
                "entity_type_counts": entity_type_counts,
                "total_entities_created": self._total_entities_created,
                "snapshots_stored": len(self._snapshots),
                "simulation_speed": self._simulation_speed,
            }

    def get_recent_interactions(
        self,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get recent world interactions."""
        with self._lock:
            recent = self._interactions[-limit:]
            return [
                {
                    "interaction_id": i.interaction_id,
                    "source_id": i.source_id,
                    "target_id": i.target_id,
                    "interaction_type": i.interaction_type.value,
                    "description": i.description,
                    "outcome": i.outcome,
                    "succeeded": i.succeeded,
                    "timestamp": i.timestamp,
                }
                for i in recent
            ]

    def get_pending_events(self) -> List[Dict[str, Any]]:
        """Get unresolved world events."""
        with self._lock:
            return [
                {
                    "event_id": e.event_id,
                    "category": e.category.value,
                    "name": e.name,
                    "description": e.description,
                    "intensity": e.intensity,
                    "affected_entities": len(e.affected_entities),
                    "timestamp": e.timestamp,
                }
                for e in self._events
                if not e.resolved
            ]

    def set_simulation_speed(self, speed: float) -> None:
        """Set the simulation speed multiplier."""
        with self._lock:
            self._simulation_speed = max(0.1, min(10.0, speed))


# ---------------------------------------------------------------------------
# Singleton Accessor
# ---------------------------------------------------------------------------

def get_world_simulator_engine() -> WorldSimulatorEngine:
    """Get the singleton WorldSimulatorEngine instance."""
    return WorldSimulatorEngine.get_instance()