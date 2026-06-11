from __future__ import annotations

import threading
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

_time_module = time


class PerceptionModality(Enum):
    """Types of sensory perception modalities available to the agent."""
    VISUAL = "visual"
    AUDITORY = "auditory"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    SOCIAL = "social"
    MECHANICAL = "mechanical"
    ECONOMIC = "economic"
    ENVIRONMENTAL = "environmental"


class PerceptionConfidence(Enum):
    """Confidence levels for perceptual interpretations."""
    CERTAIN = "certain"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    SPECULATIVE = "speculative"


class WorldLayer(Enum):
    """Different layers of world understanding."""
    PHYSICAL = "physical"
    LOGICAL = "logical"
    SOCIAL = "social"
    NARRATIVE = "narrative"
    META = "meta"


class EntityCategory(Enum):
    """Categories of entities that can be perceived in the world."""
    PLAYER = "player"
    NPC = "npc"
    ITEM = "item"
    STRUCTURE = "structure"
    TERRAIN = "terrain"
    EFFECT = "effect"
    TRIGGER = "trigger"
    UNKNOWN = "unknown"


class PerceptionPriority(Enum):
    """Priority levels for attentional processing."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class SensoryInput:
    """Represents a single piece of sensory input from the environment."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    modality: PerceptionModality = PerceptionModality.VISUAL
    source_id: str = ""
    data: Dict = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: float = field(default_factory=_time_module.time)
    location: Optional[Tuple[float, ...]] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert sensory input to dictionary representation."""
        return {
            "id": self.id,
            "modality": self.modality.value,
            "source_id": self.source_id,
            "data": self.data,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "location": self.location,
            "metadata": self.metadata
        }


@dataclass
class PerceptionSnapshot:
    """A snapshot of world perception at a specific point in time."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_id: str = ""
    timestamp: float = field(default_factory=_time_module.time)
    entities_perceived: int = 0
    region_bounds: Optional[Tuple[float, float, float, float]] = None
    sensory_inputs: List[SensoryInput] = field(default_factory=list)
    attention_focus: Optional[Tuple[Tuple[float, ...], float, PerceptionPriority]] = None
    confidence_distribution: Dict[str, float] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict:
        """Convert perception snapshot to dictionary representation."""
        attention_dict = None
        if self.attention_focus:
            pos, radius, priority = self.attention_focus
            attention_dict = {
                "position": pos,
                "radius": radius,
                "priority": priority.value
            }

        return {
            "id": self.id,
            "world_id": self.world_id,
            "timestamp": self.timestamp,
            "entities_perceived": self.entities_perceived,
            "region_bounds": self.region_bounds,
            "sensory_inputs": [s.to_dict() for s in self.sensory_inputs],
            "attention_focus": attention_dict,
            "confidence_distribution": self.confidence_distribution,
            "duration_ms": self.duration_ms
        }


@dataclass
class WorldEntity:
    """Represents a perceived entity in the world."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    category: EntityCategory = EntityCategory.UNKNOWN
    name: str = ""
    position: Tuple[float, ...] = ()
    velocity: Tuple[float, ...] = ()
    properties: Dict = field(default_factory=dict)
    last_perceived: float = field(default_factory=_time_module.time)
    confidence: float = 0.0
    perception_count: int = 1
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert world entity to dictionary representation."""
        return {
            "id": self.id,
            "category": self.category.value,
            "name": self.name,
            "position": self.position,
            "velocity": self.velocity,
            "properties": self.properties,
            "last_perceived": self.last_perceived,
            "confidence": self.confidence,
            "perception_count": self.perception_count,
            "tags": self.tags
        }


@dataclass
class PerceptualMemory:
    """Memory record for a persistently perceived entity."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    first_perceived: float = field(default_factory=_time_module.time)
    last_perceived: float = field(default_factory=_time_module.time)
    total_observations: int = 1
    confidence_trend: List[float] = field(default_factory=list)
    position_history: List[Tuple[float, ...]] = field(default_factory=list)
    key_properties: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert perceptual memory to dictionary representation."""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "first_perceived": self.first_perceived,
            "last_perceived": self.last_perceived,
            "total_observations": self.total_observations,
            "confidence_trend": self.confidence_trend,
            "position_history": self.position_history,
            "key_properties": self.key_properties
        }


class AgentWorldPerception:
    """
    AI-driven World Perception module that enables agents to perceive and
    understand game world state through multi-modal sensory input.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls) -> AgentWorldPerception:
        """Singleton pattern implementation with double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the world perception system with empty storage."""
        if hasattr(self, '_initialized'):
            return

        self._entities: Dict[str, WorldEntity] = {}
        self._perceptual_memory: Dict[str, PerceptualMemory] = {}
        self._sensory_buffer: List[SensoryInput] = []
        self._snapshots: List[PerceptionSnapshot] = []
        self._attention_focus: Optional[Tuple[Tuple[float, ...], float, PerceptionPriority]] = None
        self._region_filters: Dict[WorldLayer, List[EntityCategory]] = {}
        self._modality_weights: Dict[PerceptionModality, float] = {
            modality: 1.0 for modality in PerceptionModality
        }
        self._stats: Dict = {
            "entities_tracked": 0,
            "snapshots_taken": 0,
            "memory_entries": 0,
            "total_sensory_inputs": 0,
            "average_confidence": 0.0,
            "start_time": _time_module.time()
        }

        self._initialized = True

    @classmethod
    def get_instance(cls) -> AgentWorldPerception:
        """Get the singleton instance of the world perception module."""
        if cls._instance is None:
            cls()
        return cls._instance

    def perceive(
        self,
        world_id: str,
        sensory_inputs: List[SensoryInput],
        delta_time: float
    ) -> PerceptionSnapshot:
        """
        Process sensory data and build a perception snapshot of the current world state.

        Args:
            world_id: Identifier for the world instance being perceived
            sensory_inputs: List of sensory inputs to process
            delta_time: Time elapsed since last perception cycle

        Returns:
            A PerceptionSnapshot containing the processed world perception
        """
        start_time = _time_module.time()
        snapshot = PerceptionSnapshot(world_id=world_id)
        snapshot.sensory_inputs.extend(sensory_inputs)

        region_bounds: Optional[Tuple[float, float, float, float]] = None
        entity_count = 0

        if self._attention_focus:
            snapshot.attention_focus = self._attention_focus

        confidence_sum: Dict[str, float] = {}
        confidence_count: Dict[str, int] = {}

        for sensory_input in sensory_inputs:
            modality_name = sensory_input.modality.value
            confidence_sum[modality_name] = confidence_sum.get(modality_name, 0.0) + sensory_input.confidence
            confidence_count[modality_name] = confidence_count.get(modality_name, 0) + 1

            if sensory_input.source_id and sensory_input.confidence >= 0.5:
                entity_count += 1

        for modality_name in confidence_sum:
            snapshot.confidence_distribution[modality_name] = (
                confidence_sum[modality_name] / confidence_count[modality_name]
            )

        snapshot.entities_perceived = entity_count
        snapshot.region_bounds = region_bounds

        self._sensory_buffer.extend(sensory_inputs)
        self._snapshots.append(snapshot)
        self._stats["snapshots_taken"] += 1
        self._stats["total_sensory_inputs"] += len(sensory_inputs)

        snapshot.duration_ms = (_time_module.time() - start_time) * 1000
        return snapshot

    def register_entity(self, entity_data: WorldEntity) -> WorldEntity:
        """
        Register or update a perceived entity in the world model.

        Args:
            entity_data: The entity data to register or update

        Returns:
            The registered or updated WorldEntity
        """
        if entity_data.id in self._entities:
            existing = self._entities[entity_data.id]
            entity_data.perception_count = existing.perception_count + 1
            entity_data.last_perceived = _time_module.time()
            entity_data.confidence = (
                (existing.confidence * existing.perception_count + entity_data.confidence) /
                (existing.perception_count + 1)
            )

        self._entities[entity_data.id] = entity_data
        self._stats["entities_tracked"] = len(self._entities)

        self.update_perceptual_memory(entity_data.id)
        return entity_data

    def update_perceptual_memory(self, entity_id: str) -> PerceptualMemory:
        """
        Update the perceptual memory for a specific entity.

        Args:
            entity_id: ID of the entity to update memory for

        Returns:
            The updated PerceptualMemory
        """
        entity = self._entities.get(entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        if entity_id in self._perceptual_memory:
            memory = self._perceptual_memory[entity_id]
            memory.last_perceived = entity.last_perceived
            memory.total_observations += 1
            memory.confidence_trend.append(entity.confidence)

            if len(memory.confidence_trend) > 100:
                memory.confidence_trend = memory.confidence_trend[-100:]

            if entity.position:
                memory.position_history.append(entity.position)
                if len(memory.position_history) > 100:
                    memory.position_history = memory.position_history[-100:]

            for key, value in entity.properties.items():
                if key not in memory.key_properties or value != memory.key_properties[key]:
                    memory.key_properties[key] = value
        else:
            memory = PerceptualMemory(
                entity_id=entity_id,
                first_perceived=entity.last_perceived - _time_module.time() * 0.0001,
                last_perceived=entity.last_perceived,
                confidence_trend=[entity.confidence]
            )
            if entity.position:
                memory.position_history.append(entity.position)
            memory.key_properties = entity.properties.copy()
            self._perceptual_memory[entity_id] = memory
            self._stats["memory_entries"] = len(self._perceptual_memory)

        return memory

    def filter_by_modality(
        self,
        modality: PerceptionModality,
        min_confidence: float = 0.0
    ) -> List[WorldEntity]:
        """
        Filter perceived entities by perception modality and minimum confidence.

        Args:
            modality: The perception modality to filter by
            min_confidence: Minimum confidence threshold (0.0 to 1.0)

        Returns:
            List of matching WorldEntity objects
        """
        results: List[WorldEntity] = []
        for entity in self._entities.values():
            if entity.confidence >= min_confidence:
                results.append(entity)
        return results

    def set_attention_focus(
        self,
        position: Tuple[float, ...],
        radius: float,
        priority: PerceptionPriority
    ) -> None:
        """
        Set the agent's attention focus to a specific region.

        Args:
            position: Center position of the attention focus
            radius: Radius of the attention region
            priority: Priority level for this focus
        """
        self._attention_focus = (position, radius, priority)

    def query_region(
        self,
        bounds: Tuple[float, float, float, float],
        layer: Optional[WorldLayer],
        categories: Optional[List[EntityCategory]]
    ) -> List[WorldEntity]:
        """
        Perform a spatial query for entities in a given region.

        Args:
            bounds: Region bounds as (min_x, min_y, max_x, max_y)
            layer: Optional world layer filter
            categories: Optional entity category filters

        Returns:
            List of WorldEntity objects within the query region
        """
        results: List[WorldEntity] = []
        min_x, min_y, max_x, max_y = bounds

        for entity in self._entities.values():
            if not entity.position or len(entity.position) < 2:
                continue

            x, y = entity.position[0], entity.position[1]
            if min_x <= x <= max_x and min_y <= y <= max_y:
                if categories and entity.category not in categories:
                    continue
                results.append(entity)

        return results

    def detect_changes(self, confidence_threshold: float) -> List[WorldEntity]:
        """
        Detect significant changes in world state based on perception history.

        Args:
            confidence_threshold: Minimum confidence change to be considered significant

        Returns:
            List of WorldEntity objects that have significant changes
        """
        changed_entities: List[WorldEntity] = []

        for entity_id, entity in self._entities.items():
            memory = self._perceptual_memory.get(entity_id)
            if not memory or len(memory.confidence_trend) < 2:
                continue

            if len(memory.confidence_trend) >= 2:
                recent = memory.confidence_trend[-1]
                previous = memory.confidence_trend[-2]
                if abs(recent - previous) >= confidence_threshold:
                    changed_entities.append(entity)
                elif entity.position and memory.position_history and len(memory.position_history) >= 2:
                    last_pos = memory.position_history[-1]
                    prev_pos = memory.position_history[-2]
                    if last_pos != prev_pos:
                        changed_entities.append(entity)

        return changed_entities

    def get_world_understanding(self, world_id: str) -> Dict:
        """
        Aggregate current understanding of the world into a comprehensive summary.

        Args:
            world_id: The world instance to get understanding for

        Returns:
            Dictionary containing structured world understanding
        """
        entity_counts: Dict[str, int] = {}
        for entity in self._entities.values():
            category = entity.category.value
            entity_counts[category] = entity_counts.get(category, 0) + 1

        changed_entities = self.detect_changes(0.2)
        recent_changes = [e.to_dict() for e in changed_entities]

        attention_hot_spots: List[Dict] = []
        if self._attention_focus:
            pos, radius, priority = self._attention_focus
            attention_hot_spots.append({
                "position": pos,
                "radius": radius,
                "priority": priority.value
            })

        total_confidence = sum(e.confidence for e in self._entities.values())
        avg_confidence = total_confidence / max(1, len(self._entities))

        modality_coverage: Dict[str, int] = {}
        for snapshot in self._snapshots[-10:]:
            for modality in snapshot.confidence_distribution:
                modality_coverage[modality] = modality_coverage.get(modality, 0) + 1

        entity_density: Dict[str, int] = {}
        if self._attention_focus:
            pos, radius, _ = self._attention_focus
            if len(pos) >= 2:
                cx, cy = pos[0], pos[1]
                region_bounds = (cx - radius, cy - radius, cx + radius, cy + radius)
                region_entities = self.query_region(region_bounds, None, None)
                entity_density["attention_region"] = len(region_entities)

        motion_trends: List[Dict] = []
        for entity_id, memory in self._perceptual_memory.items():
            if len(memory.position_history) >= 5:
                positions = memory.position_history[-5:]
                if len(positions) >= 2:
                    motion_trends.append({
                        "entity_id": entity_id,
                        "positions_observed": len(positions)
                    })

        return {
            "world_state_summary": {
                "entity_counts_by_category": entity_counts,
                "recent_changes": recent_changes,
                "attention_hot_spots": attention_hot_spots
            },
            "spatial_layout": {
                "entity_density_map": entity_density,
                "region_summaries": []
            },
            "temporal_patterns": {
                "motion_trends": motion_trends,
                "recurring_patterns": []
            },
            "confidence_metrics": {
                "average_confidence": avg_confidence,
                "modality_coverage": modality_coverage
            }
        }

    def get_status(self) -> Dict:
        """
        Get current status of the world perception system.

        Returns:
            Dictionary with current status information
        """
        modality_distribution: Dict[str, int] = {}
        for snapshot in self._snapshots[-100:]:
            for sensory_input in snapshot.sensory_inputs:
                modality = sensory_input.modality.value
                modality_distribution[modality] = modality_distribution.get(modality, 0) + 1

        if self._entities:
            avg_confidence = sum(e.confidence for e in self._entities.values()) / len(self._entities)
            self._stats["average_confidence"] = avg_confidence

        attention_status = None
        if self._attention_focus:
            pos, radius, priority = self._attention_focus
            attention_status = {
                "position": pos,
                "radius": radius,
                "priority": priority.value
            }

        return {
            "entities_tracked": self._stats["entities_tracked"],
            "snapshots_count": self._stats["snapshots_taken"],
            "memory_entries": self._stats["memory_entries"],
            "total_sensory_inputs": self._stats["total_sensory_inputs"],
            "attention_focus": attention_status,
            "modality_distribution": modality_distribution,
            "average_confidence": self._stats["average_confidence"],
            "uptime_seconds": _time_module.time() - self._stats["start_time"]
        }

    def reset(self) -> None:
        """Reset all perception data and start fresh."""
        self._entities.clear()
        self._perceptual_memory.clear()
        self._sensory_buffer.clear()
        self._snapshots.clear()
        self._attention_focus = None
        self._region_filters.clear()
        self._modality_weights = {modality: 1.0 for modality in PerceptionModality}
        self._stats = {
            "entities_tracked": 0,
            "snapshots_taken": 0,
            "memory_entries": 0,
            "total_sensory_inputs": 0,
            "average_confidence": 0.0,
            "start_time": _time_module.time()
        }


def get_world_perception() -> AgentWorldPerception:
    """
    Module-level accessor for the world perception singleton.

    Returns:
        The singleton AgentWorldPerception instance
    """
    return AgentWorldPerception.get_instance()
