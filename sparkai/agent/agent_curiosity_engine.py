"""
SparkLabs Agent - Curiosity Engine

Intrinsic motivation system that drives AI agents to explore unknown areas,
discover new patterns, and self-direct their learning through multiple
curiosity strategies. The Curiosity Engine computes novelty scores, surprise
metrics, and information-gain estimates to generate exploration goals that
keep agents autonomously engaged with their environment.

Architecture:
  AgentCuriosityEngine (Singleton)
    |-- CuriosityProfile Manager (per-agent motivation parameters)
    |-- Goal Generator (multi-strategy exploration goal synthesis)
    |-- Discovery Tracker (novelty-weighted discovery records)
    |-- Knowledge Zone Manager (spatial knowledge partitioning)
    |-- Phase Controller (SURVEY/FOCUS/EXPLOIT/REFRESH transitions)
    |-- Exploration Analyzer (efficiency scoring and reporting)

Curiosity Strategies:
  - NOVELTY_SEEKING: target least-explored regions
  - SURPRISE_MAXIMIZATION: target boundaries between known/unknown
  - UNCERTAINTY_REDUCTION: target low-confidence zones
  - INFORMATION_GAIN: target high-density, low-coverage areas
  - COMPETENCE_BUILDING: target zones matching agent skill level

Usage:
    engine = get_curiosity_engine()
    profile = engine.create_curiosity_profile("agent_42",
        dominant_strategy=CuriosityStrategy.NOVELTY_SEEKING)
    goal = engine.generate_exploration_goal("agent_42",
        world_bounds=(0, 0, 1000, 1000), known_zones=[...])
    engine.record_discovery("agent_42", DiscoveryType.OBJECT,
        (128, 256), "Ancient artifact found in ruins")
    report = engine.evaluate_exploration_efficiency("agent_42")
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CuriosityStrategy(str, Enum):
    """Intrinsic motivation strategy that drives an agent's exploration behavior."""
    NOVELTY_SEEKING = "novelty_seeking"
    SURPRISE_MAXIMIZATION = "surprise_maximization"
    UNCERTAINTY_REDUCTION = "uncertainty_reduction"
    INFORMATION_GAIN = "information_gain"
    COMPETENCE_BUILDING = "competence_building"


class ExplorationPhase(str, Enum):
    """Current phase of an agent's exploration lifecycle."""
    SURVEY = "survey"
    FOCUS = "focus"
    EXPLOIT = "exploit"
    REFRESH = "refresh"


class DiscoveryType(str, Enum):
    """Category of a world discovery made by an agent."""
    LOCATION = "location"
    OBJECT = "object"
    PATTERN = "pattern"
    MECHANIC = "mechanic"
    RELATIONSHIP = "relationship"
    ANOMALY = "anomaly"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ExplorationGoal:
    """A target location and strategy for the agent to explore next."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    target_position: Tuple[float, float] = (0.0, 0.0)
    strategy: CuriosityStrategy = CuriosityStrategy.NOVELTY_SEEKING
    priority: float = 0.5
    estimated_reward: float = 0.0
    expiry_time: float = field(default_factory=lambda: _time_module.time() + 300.0)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_position": list(self.target_position),
            "strategy": self.strategy.value,
            "priority": self.priority,
            "estimated_reward": self.estimated_reward,
            "expiry_time": self.expiry_time,
            "tags": self.tags,
        }


@dataclass
class DiscoveryRecord:
    """A record of something the agent has discovered in the world."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    discovery_type: DiscoveryType = DiscoveryType.LOCATION
    location: Tuple[float, float] = (0.0, 0.0)
    description: str = ""
    novelty_score: float = 0.0
    surprise_score: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "discovery_type": self.discovery_type.value,
            "location": list(self.location),
            "description": self.description,
            "novelty_score": self.novelty_score,
            "surprise_score": self.surprise_score,
            "timestamp": self.timestamp,
            "context": self.context,
        }


@dataclass
class KnowledgeZone:
    """A bounded region of the world with tracked exploration coverage."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    bounds: Tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0)
    explored_percentage: float = 0.0
    entity_count: int = 0
    last_visited: float = field(default_factory=_time_module.time)
    confidence: float = 0.1
    visited_positions: List[Tuple[float, float]] = field(default_factory=list)
    discovery_ids: List[str] = field(default_factory=list)
    entity_types: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.bounds
        return (x2 - x1) * (y2 - y1)

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bounds
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "bounds": list(self.bounds),
            "explored_percentage": self.explored_percentage,
            "entity_count": self.entity_count,
            "last_visited": self.last_visited,
            "confidence": self.confidence,
            "visited_count": len(self.visited_positions),
            "discovery_count": len(self.discovery_ids),
            "entity_types": self.entity_types,
        }


@dataclass
class CuriosityProfile:
    """Per-agent configuration and state for curiosity-driven exploration."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    dominant_strategy: CuriosityStrategy = CuriosityStrategy.NOVELTY_SEEKING
    exploration_rate: float = 0.5
    novelty_threshold: float = 0.3
    boredom_threshold: float = 0.7
    total_discoveries: int = 0
    favorite_zones: List[str] = field(default_factory=list)
    current_phase: ExplorationPhase = ExplorationPhase.SURVEY
    discovery_history: List[str] = field(default_factory=list)
    goal_history: List[str] = field(default_factory=list)
    zone_visit_counts: Dict[str, int] = field(default_factory=dict)
    strategy_weights: Dict[str, float] = field(default_factory=lambda: {
        CuriosityStrategy.NOVELTY_SEEKING.value: 1.0,
        CuriosityStrategy.SURPRISE_MAXIMIZATION.value: 0.8,
        CuriosityStrategy.UNCERTAINTY_REDUCTION.value: 0.9,
        CuriosityStrategy.INFORMATION_GAIN.value: 0.85,
        CuriosityStrategy.COMPETENCE_BUILDING.value: 0.7,
    })
    created_at: float = field(default_factory=_time_module.time)
    last_active: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "dominant_strategy": self.dominant_strategy.value,
            "exploration_rate": self.exploration_rate,
            "novelty_threshold": self.novelty_threshold,
            "boredom_threshold": self.boredom_threshold,
            "total_discoveries": self.total_discoveries,
            "favorite_zones": self.favorite_zones,
            "current_phase": self.current_phase.value,
            "discovery_count": len(self.discovery_history),
            "goal_count": len(self.goal_history),
            "strategy_weights": self.strategy_weights,
        }


@dataclass
class ExplorationReport:
    """A summary report of an agent's exploration activity and efficiency."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=_time_module.time)
    zones_explored: int = 0
    discoveries: List[DiscoveryRecord] = field(default_factory=list)
    exploration_efficiency: float = 0.0
    suggested_goals: List[ExplorationGoal] = field(default_factory=list)
    agent_id: str = ""
    elapsed_seconds: float = 0.0
    total_coverage_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "zones_explored": self.zones_explored,
            "discovery_count": len(self.discoveries),
            "exploration_efficiency": self.exploration_efficiency,
            "suggested_goals": [g.to_dict() for g in self.suggested_goals],
            "agent_id": self.agent_id,
            "elapsed_seconds": self.elapsed_seconds,
            "total_coverage_pct": self.total_coverage_pct,
        }


# ---------------------------------------------------------------------------
# Agent Curiosity Engine (Singleton)
# ---------------------------------------------------------------------------

class AgentCuriosityEngine:
    """
    Intrinsic motivation system that drives agents to explore, discover,
    and learn autonomously. Computes multi-strategy exploration goals,
    tracks discoveries with novelty and surprise scoring, and manages
    knowledge zone partitioning for spatial awareness.

    Singleton pattern with thread-safe double-checked locking.
    """

    _instance: Optional["AgentCuriosityEngine"] = None
    _lock = threading.RLock()

    # Configuration constants
    _DEFAULT_GOAL_EXPIRY_SECONDS: float = 300.0
    _MIN_ZONE_AREA: float = 100.0
    _NOVELTY_DECAY_RATE: float = 0.95
    _SURPRISE_WINDOW_SECONDS: float = 600.0
    _MAX_SUGGESTED_GOALS: int = 10
    _COVERAGE_SURVEY_THRESHOLD: float = 0.3
    _COVERAGE_FOCUS_THRESHOLD: float = 0.6
    _COVERAGE_EXPLOIT_THRESHOLD: float = 0.85
    _BOREDOM_REFRESH_INTERVAL: float = 900.0

    def __new__(cls) -> "AgentCuriosityEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentCuriosityEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # Core state
        self._profiles: Dict[str, CuriosityProfile] = {}
        self._discoveries: Dict[str, DiscoveryRecord] = {}
        self._zones: Dict[str, KnowledgeZone] = {}
        self._goals: Dict[str, ExplorationGoal] = {}

        # Per-agent index structures
        self._agent_discoveries: Dict[str, List[str]] = {}
        self._agent_goals: Dict[str, List[str]] = {}
        self._agent_visited_positions: Dict[str, List[Tuple[float, float]]] = {}
        self._agent_phase_history: Dict[str, List[Tuple[float, ExplorationPhase]]] = {}

        # Spatial index: grid-based lookup for nearby zones
        self._spatial_grid: Dict[Tuple[int, int], List[str]] = {}
        self._grid_cell_size: float = 100.0

        # Global counters
        self._total_discoveries: int = 0
        self._total_goals_generated: int = 0
        self._total_zones_registered: int = 0

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def create_curiosity_profile(
        self,
        agent_id: str,
        dominant_strategy: CuriosityStrategy = CuriosityStrategy.NOVELTY_SEEKING,
        exploration_rate: float = 0.5,
        novelty_threshold: float = 0.3,
        boredom_threshold: float = 0.7,
        strategy_weights: Optional[Dict[str, float]] = None,
    ) -> CuriosityProfile:
        """
        Initialize curiosity parameters for an agent. Creates a profile
        with the given motivation configuration or returns the existing one.
        """
        with self._lock:
            profile = CuriosityProfile(
                agent_id=agent_id,
                dominant_strategy=dominant_strategy,
                exploration_rate=exploration_rate,
                novelty_threshold=novelty_threshold,
                boredom_threshold=boredom_threshold,
            )
            if strategy_weights:
                profile.strategy_weights.update(strategy_weights)
            self._profiles[agent_id] = profile
            self._agent_discoveries.setdefault(agent_id, [])
            self._agent_goals.setdefault(agent_id, [])
            self._agent_visited_positions.setdefault(agent_id, [])
            self._agent_phase_history.setdefault(agent_id, [])
            return profile

    def get_curiosity_profile(self, agent_id: str) -> CuriosityProfile:
        """
        Get or create a profile for an agent. If no profile exists,
        a default one is created automatically.
        """
        with self._lock:
            if agent_id not in self._profiles:
                return self.create_curiosity_profile(agent_id)
            return self._profiles[agent_id]

    # ------------------------------------------------------------------
    # Exploration Goal Generation
    # ------------------------------------------------------------------

    def generate_exploration_goal(
        self,
        agent_id: str,
        world_bounds: Tuple[float, float, float, float],
        known_zones: Optional[List[str]] = None,
    ) -> ExplorationGoal:
        """
        Generate the next exploration target for an agent using the
        agent's dominant curiosity strategy. Considers:
          - NOVELTY_SEEKING: pick least-explored zone
          - SURPRISE_MAXIMIZATION: pick zones near boundaries of known areas
          - UNCERTAINTY_REDUCTION: pick zones with lowest confidence
          - INFORMATION_GAIN: pick zones with highest potential entity
            density but lowest coverage
          - COMPETENCE_BUILDING: pick zones with moderate exploration
            (neither too easy nor too hard)
        """
        with self._lock:
            profile = self.get_curiosity_profile(agent_id)
            strategy = profile.dominant_strategy

            # Gather candidate zones
            candidate_zone_ids = list(self._zones.keys())
            if known_zones:
                candidate_zone_ids = [z for z in known_zones if z in self._zones]

            target_position: Tuple[float, float]
            priority: float
            estimated_reward: float
            tags: List[str] = [strategy.value]
            goal_strategy = strategy

            if strategy == CuriosityStrategy.NOVELTY_SEEKING:
                target_position, priority, estimated_reward = (
                    self._goal_novelty_seeking(profile, candidate_zone_ids, world_bounds)
                )

            elif strategy == CuriosityStrategy.SURPRISE_MAXIMIZATION:
                target_position, priority, estimated_reward = (
                    self._goal_surprise_maximization(profile, candidate_zone_ids, world_bounds)
                )

            elif strategy == CuriosityStrategy.UNCERTAINTY_REDUCTION:
                target_position, priority, estimated_reward = (
                    self._goal_uncertainty_reduction(profile, candidate_zone_ids, world_bounds)
                )

            elif strategy == CuriosityStrategy.INFORMATION_GAIN:
                target_position, priority, estimated_reward = (
                    self._goal_information_gain(profile, candidate_zone_ids, world_bounds)
                )

            elif strategy == CuriosityStrategy.COMPETENCE_BUILDING:
                target_position, priority, estimated_reward = (
                    self._goal_competence_building(profile, candidate_zone_ids, world_bounds)
                )

            else:
                # Fallback: pick a random position within world bounds
                target_position = self._random_position_in_bounds(world_bounds)
                priority = 0.3
                estimated_reward = 0.1
                goal_strategy = CuriosityStrategy.NOVELTY_SEEKING

            now = _time_module.time()
            goal = ExplorationGoal(
                target_position=target_position,
                strategy=goal_strategy,
                priority=priority,
                estimated_reward=estimated_reward,
                expiry_time=now + self._DEFAULT_GOAL_EXPIRY_SECONDS,
                tags=tags,
            )

            # Record the goal
            self._goals[goal.id] = goal
            self._agent_goals[agent_id] = self._agent_goals.get(agent_id, [])
            self._agent_goals[agent_id].append(goal.id)
            profile.goal_history.append(goal.id)
            profile.last_active = now
            self._total_goals_generated += 1

            return goal

    def _goal_novelty_seeking(
        self,
        profile: CuriosityProfile,
        candidate_zone_ids: List[str],
        world_bounds: Tuple[float, float, float, float],
    ) -> Tuple[Tuple[float, float], float, float]:
        """Generate goal targeting the least-explored zone."""
        if not candidate_zone_ids:
            return self._random_position_in_bounds(world_bounds), 0.4, 0.1

        # Find least explored zone
        least_explored: Optional[KnowledgeZone] = None
        min_coverage = float("inf")
        for zid in candidate_zone_ids:
            zone = self._zones.get(zid)
            if zone and zone.explored_percentage < min_coverage:
                min_coverage = zone.explored_percentage
                least_explored = zone

        if least_explored and min_coverage < 1.0:
            # Pick an unexplored position within the zone
            position = self._unexplored_position_in_zone(least_explored, profile)
            novelty_gap = 1.0 - min_coverage
            priority = 0.5 + novelty_gap * 0.5
            estimated_reward = novelty_gap * profile.exploration_rate
            return position, priority, estimated_reward

        return self._random_position_in_bounds(world_bounds), 0.3, 0.05

    def _goal_surprise_maximization(
        self,
        profile: CuriosityProfile,
        candidate_zone_ids: List[str],
        world_bounds: Tuple[float, float, float, float],
    ) -> Tuple[Tuple[float, float], float, float]:
        """Generate goal near boundaries between explored and unexplored areas."""
        boundary_zones: List[Tuple[KnowledgeZone, float]] = []

        for zid in candidate_zone_ids:
            zone = self._zones.get(zid)
            if zone is None:
                continue
            # Boundary score: zones near 50% explored have the most uncertainty
            boundary_score = 1.0 - abs(zone.explored_percentage - 0.5) * 2.0
            # Also weight by recent surprise scores from discoveries in this zone
            recent_surprises = 0.0
            for did in zone.discovery_ids:
                disc = self._discoveries.get(did)
                if disc:
                    age = _time_module.time() - disc.timestamp
                    if age < self._SURPRISE_WINDOW_SECONDS:
                        recent_surprises += disc.surprise_score * (1.0 - age / self._SURPRISE_WINDOW_SECONDS)

            combined_score = boundary_score * 0.6 + min(recent_surprises, 1.0) * 0.4
            boundary_zones.append((zone, combined_score))

        if boundary_zones:
            boundary_zones.sort(key=lambda x: x[1], reverse=True)
            best_zone, score = boundary_zones[0]
            position = self._boundary_position_in_zone(best_zone)
            priority = 0.4 + score * 0.6
            estimated_reward = score * profile.exploration_rate * 1.5
            return position, priority, estimated_reward

        return self._random_position_in_bounds(world_bounds), 0.3, 0.1

    def _goal_uncertainty_reduction(
        self,
        profile: CuriosityProfile,
        candidate_zone_ids: List[str],
        world_bounds: Tuple[float, float, float, float],
    ) -> Tuple[Tuple[float, float], float, float]:
        """Generate goal targeting zones with lowest confidence."""
        if not candidate_zone_ids:
            return self._random_position_in_bounds(world_bounds), 0.4, 0.1

        lowest_confidence_zone: Optional[KnowledgeZone] = None
        min_conf = float("inf")
        for zid in candidate_zone_ids:
            zone = self._zones.get(zid)
            if zone and zone.confidence < min_conf:
                min_conf = zone.confidence
                lowest_confidence_zone = zone

        if lowest_confidence_zone:
            # Target center of low-confidence zone (highest uncertainty)
            position = lowest_confidence_zone.center
            uncertainty = 1.0 - min_conf
            priority = 0.3 + uncertainty * 0.7
            estimated_reward = uncertainty * profile.exploration_rate * 1.2
            return position, priority, estimated_reward

        return self._random_position_in_bounds(world_bounds), 0.3, 0.05

    def _goal_information_gain(
        self,
        profile: CuriosityProfile,
        candidate_zone_ids: List[str],
        world_bounds: Tuple[float, float, float, float],
    ) -> Tuple[Tuple[float, float], float, float]:
        """
        Generate goal targeting zones with highest entity density but
        lowest exploration coverage (maximum potential information gain).
        """
        if not candidate_zone_ids:
            return self._random_position_in_bounds(world_bounds), 0.4, 0.1

        best_zone: Optional[KnowledgeZone] = None
        best_info_gain = -float("inf")

        for zid in candidate_zone_ids:
            zone = self._zones.get(zid)
            if zone is None or zone.area <= 0:
                continue
            # Information gain ≈ expected entity density × unexplored fraction
            entity_density = zone.entity_count / zone.area
            unexplored_ratio = 1.0 - zone.explored_percentage
            # Normalize: cap entity density influence
            normalized_density = min(entity_density / 0.01, 1.0)
            info_gain = normalized_density * 0.6 + unexplored_ratio * 0.4
            if info_gain > best_info_gain:
                best_info_gain = info_gain
                best_zone = zone

        if best_zone:
            position = self._unexplored_position_in_zone(best_zone, profile)
            priority = 0.3 + best_info_gain * 0.7
            estimated_reward = best_info_gain * profile.exploration_rate * 2.0
            return position, priority, estimated_reward

        return self._random_position_in_bounds(world_bounds), 0.3, 0.1

    def _goal_competence_building(
        self,
        profile: CuriosityProfile,
        candidate_zone_ids: List[str],
        world_bounds: Tuple[float, float, float, float],
    ) -> Tuple[Tuple[float, float], float, float]:
        """
        Generate goal targeting zones with moderate exploration difficulty -
        neither fully known (too easy) nor completely unknown (too hard).
        """
        if not candidate_zone_ids:
            return self._random_position_in_bounds(world_bounds), 0.4, 0.1

        # Competence is maximized at ~50% explored (zone of proximal development)
        best_zone: Optional[KnowledgeZone] = None
        best_fit = float("inf")

        for zid in candidate_zone_ids:
            zone = self._zones.get(zid)
            if zone is None:
                continue
            # Distance from "sweet spot" of moderate difficulty
            distance_from_sweet_spot = abs(zone.explored_percentage - 0.5)
            # Also consider visit recency (prefer zones not recently visited)
            recency_factor = min(
                (_time_module.time() - zone.last_visited) / self._BOREDOM_REFRESH_INTERVAL,
                1.0,
            )
            composite = distance_from_sweet_spot * 0.7 - recency_factor * 0.3
            if composite < best_fit:
                best_fit = composite
                best_zone = zone

        if best_zone:
            position = self._zone_position_near_center(best_zone)
            competence_score = 1.0 - abs(best_zone.explored_percentage - 0.5) * 2.0
            priority = 0.3 + competence_score * 0.5
            estimated_reward = competence_score * profile.exploration_rate
            return position, priority, estimated_reward

        return self._random_position_in_bounds(world_bounds), 0.3, 0.1

    # ------------------------------------------------------------------
    # Discovery Recording
    # ------------------------------------------------------------------

    def record_discovery(
        self,
        agent_id: str,
        discovery_type: DiscoveryType,
        location: Tuple[float, float],
        description: str,
        predicted_state: Optional[Dict[str, Any]] = None,
        actual_state: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> DiscoveryRecord:
        """
        Register a new discovery, compute novelty and surprise scores,
        update the knowledge zones, and link the discovery to the agent.
        """
        # Normalize discovery_type from string to enum if needed
        if isinstance(discovery_type, str):
            try:
                discovery_type = DiscoveryType(discovery_type)
            except ValueError:
                discovery_type = DiscoveryType.OBJECT
        with self._lock:
            profile = self.get_curiosity_profile(agent_id)

            # Compute scores
            novelty_score = self._compute_novelty_score_internal(
                agent_id, location, discovery_type
            )
            surprise_score = self._compute_surprise_score_internal(
                predicted_state or {}, actual_state or {}
            )

            record = DiscoveryRecord(
                discovery_type=discovery_type,
                location=location,
                description=description,
                novelty_score=novelty_score,
                surprise_score=surprise_score,
                context=context or {},
            )

            self._discoveries[record.id] = record
            self._agent_discoveries[agent_id] = self._agent_discoveries.get(agent_id, [])
            self._agent_discoveries[agent_id].append(record.id)
            self._agent_visited_positions[agent_id] = self._agent_visited_positions.get(agent_id, [])
            self._agent_visited_positions[agent_id].append(location)

            profile.total_discoveries += 1
            profile.discovery_history.append(record.id)
            profile.last_active = _time_module.time()
            self._total_discoveries += 1

            # Associate with relevant knowledge zone
            self._associate_discovery_with_zones(record)

            return record

    def _associate_discovery_with_zones(self, discovery: DiscoveryRecord) -> None:
        """Add a discovery to any knowledge zone that contains its location."""
        for zone in self._zones.values():
            if self._point_in_bounds(discovery.location, zone.bounds):
                zone.discovery_ids.append(discovery.id)
                zone.last_visited = _time_module.time()
                zone.confidence = min(
                    1.0,
                    zone.confidence + 0.02 * (1.0 + discovery.novelty_score),
                )

    # ------------------------------------------------------------------
    # Knowledge Zone Management
    # ------------------------------------------------------------------

    def register_knowledge_zone(
        self,
        bounds: Tuple[float, float, float, float],
        entity_types: Optional[List[str]] = None,
        entity_count: int = 0,
    ) -> KnowledgeZone:
        """
        Define a new area of the world worth exploring. Registers it
        in the spatial index and returns the zone object.
        """
        with self._lock:
            zone = KnowledgeZone(
                bounds=bounds,
                entity_count=entity_count,
                entity_types=entity_types or [],
            )
            self._zones[zone.id] = zone
            self._total_zones_registered += 1

            # Update spatial grid
            self._insert_zone_into_grid(zone)
            return zone

    def update_zone_exploration(
        self,
        zone_id: str,
        visited_positions: List[Tuple[float, float]],
    ) -> Optional[KnowledgeZone]:
        """
        Update how much of a zone has been explored. Computes explored
        percentage based on spatial coverage of visited positions.
        """
        with self._lock:
            zone = self._zones.get(zone_id)
            if zone is None:
                return None

            # Track visited positions with deduplication
            existing = set(zone.visited_positions)
            for pos in visited_positions:
                if self._point_in_bounds(pos, zone.bounds):
                    existing.add(pos)
            zone.visited_positions = list(existing)

            # Compute coverage using grid-based approximation
            coverage = self._compute_zone_coverage(zone)
            zone.explored_percentage = coverage
            zone.last_visited = _time_module.time()

            # Update confidence based on coverage
            zone.confidence = 0.1 + coverage * 0.9
            return zone

    def _compute_zone_coverage(self, zone: KnowledgeZone) -> float:
        """
        Estimate explored percentage by discretizing the zone into cells
        and checking which cells contain visited positions.
        """
        if not zone.visited_positions:
            return 0.0

        x1, y1, x2, y2 = zone.bounds
        width = x2 - x1
        height = y2 - y1
        if width <= 0 or height <= 0:
            return 0.0

        # Adaptive cell size based on zone area
        grid_resolution = max(4, min(16, int(math.sqrt(zone.area) / 10.0)))
        cell_w = width / grid_resolution
        cell_h = height / grid_resolution
        total_cells = grid_resolution * grid_resolution
        visited_cells: Set[Tuple[int, int]] = set()

        for px, py in zone.visited_positions:
            col = int((px - x1) / cell_w) if cell_w > 0 else 0
            row = int((py - y1) / cell_h) if cell_h > 0 else 0
            col = max(0, min(col, grid_resolution - 1))
            row = max(0, min(row, grid_resolution - 1))
            visited_cells.add((col, row))

        return len(visited_cells) / max(total_cells, 1)

    # ------------------------------------------------------------------
    # Scoring Functions
    # ------------------------------------------------------------------

    def calculate_novelty_score(self, location: Tuple[float, float]) -> float:
        """
        Compute how novel a location is based on visit history and
        neighboring zones. Returns a score in [0, 1] where 1 is
        completely novel.
        """
        with self._lock:
            return self._compute_novelty_score_internal(
                "", location, DiscoveryType.LOCATION
            )

    def _compute_novelty_score_internal(
        self,
        agent_id: str,
        location: Tuple[float, float],
        discovery_type: DiscoveryType,
    ) -> float:
        """Internal novelty computation with agent-specific history."""
        # Distance to nearest previous visit
        min_distance = float("inf")
        for pos_list in self._agent_visited_positions.values():
            for past_pos in pos_list:
                dist = math.hypot(
                    location[0] - past_pos[0],
                    location[1] - past_pos[1],
                )
                if dist < min_distance:
                    min_distance = dist

        # Novelty decays with distance
        if min_distance == float("inf"):
            distance_novelty = 1.0
        else:
            # Use a sigmoid-like decay: close = low novelty, far = high novelty
            decay = math.exp(-min_distance / 200.0)
            distance_novelty = 1.0 - decay

        # Check if this discovery type has been seen before nearby
        type_novelty = 1.0
        for did in self._agent_discoveries.get(agent_id, []):
            past = self._discoveries.get(did)
            if past and past.discovery_type == discovery_type:
                type_novelty = min(type_novelty, 0.5)

        # Composite novelty score
        novelty = distance_novelty * 0.7 + type_novelty * 0.3
        return max(0.0, min(1.0, novelty))

    def calculate_surprise_score(
        self,
        actual: Dict[str, Any],
        predicted: Dict[str, Any],
    ) -> float:
        """
        Compare actual observations against predictions. Returns a
        surprise score in [0, 1] where 1 is highly surprising.
        """
        return self._compute_surprise_score_internal(predicted, actual)

    def _compute_surprise_score_internal(
        self,
        predicted: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> float:
        """Internal surprise computation."""
        if not predicted and not actual:
            return 0.0
        if not predicted:
            return 0.8  # Unexpected discovery with no prior prediction
        if not actual:
            return 0.0

        all_keys = set(predicted.keys()) | set(actual.keys())
        if not all_keys:
            return 0.0

        total_error = 0.0
        total_weight = 0.0

        for key in all_keys:
            pred_val = predicted.get(key)
            actual_val = actual.get(key)

            if isinstance(pred_val, (int, float)) and isinstance(actual_val, (int, float)):
                # Numerical: relative error
                p = float(pred_val)
                a = float(actual_val)
                denom = max(abs(p), abs(a), 1.0)
                error = abs(p - a) / denom
            elif isinstance(pred_val, str) and isinstance(actual_val, str):
                # Categorical: zero if match, full surprise if mismatch
                error = 0.0 if pred_val == actual_val else 1.0
            elif pred_val is None and actual_val is not None:
                error = 1.0  # Unexpected presence
            elif pred_val is not None and actual_val is None:
                error = 0.5  # Absence of expected
            else:
                error = 0.0

            total_error += error
            total_weight += 1.0

        # Bayesian surprise: KL-divergence approximation via mean error
        surprise = total_error / max(total_weight, 1.0)
        return max(0.0, min(1.0, surprise))

    # ------------------------------------------------------------------
    # Exploration Efficiency
    # ------------------------------------------------------------------

    def evaluate_exploration_efficiency(self, agent_id: str) -> ExplorationReport:
        """
        Calculate discoveries per unit time/area. Returns a comprehensive
        report with efficiency metrics and suggested goals.
        """
        with self._lock:
            profile = self.get_curiosity_profile(agent_id)
            now = _time_module.time()

            # Get agent's discoveries and relevant zones
            agent_disc_ids = self._agent_discoveries.get(agent_id, [])
            agent_discoveries = [
                self._discoveries[did]
                for did in agent_disc_ids
                if did in self._discoveries
            ]

            # Determine time span
            if agent_discoveries:
                first_ts = min(d.timestamp for d in agent_discoveries)
                elapsed = now - first_ts if now > first_ts else 1.0
            else:
                elapsed = 1.0

            # Determine explored zones
            explored_zone_ids: Set[str] = set()
            for zone in self._zones.values():
                for did in zone.discovery_ids:
                    if did in agent_disc_ids:
                        explored_zone_ids.add(zone.id)
                        break

            zones_explored = len(explored_zone_ids)

            # Compute total coverage
            if self._zones:
                total_coverage = sum(
                    z.explored_percentage for z in self._zones.values()
                ) / len(self._zones)
            else:
                total_coverage = 0.0

            # Efficiency = discoveries per minute adjusted by coverage
            discoveries_per_minute = len(agent_discoveries) / (elapsed / 60.0)
            area_coverage_factor = max(total_coverage, 0.01)
            efficiency = discoveries_per_minute / area_coverage_factor
            # Normalize to [0, 1] range
            exploration_efficiency = min(1.0, efficiency / 10.0)

            # Generate suggested goals
            suggested = self.get_suggested_goals(
                agent_id, max_goals=3
            )

            report = ExplorationReport(
                zones_explored=zones_explored,
                discoveries=agent_discoveries[-20:],
                exploration_efficiency=exploration_efficiency,
                suggested_goals=suggested,
                agent_id=agent_id,
                elapsed_seconds=elapsed,
                total_coverage_pct=total_coverage * 100.0,
            )

            return report

    # ------------------------------------------------------------------
    # Suggested Goals
    # ------------------------------------------------------------------

    def get_suggested_goals(
        self,
        agent_id: str,
        max_goals: int = 5,
    ) -> List[ExplorationGoal]:
        """
        Get a ranked list of exploration goals for an agent. Goals are
        generated using all strategies with weights from the agent's
        profile, then ranked by priority.
        """
        with self._lock:
            profile = self.get_curiosity_profile(agent_id)
            all_goals: List[ExplorationGoal] = []

            # Default world bounds (use union of all zones)
            world_bounds = self._compute_world_bounds()
            zone_ids = list(self._zones.keys())

            # Generate goals using each strategy
            strategies = list(CuriosityStrategy)
            for strategy in strategies:
                weight = profile.strategy_weights.get(strategy.value, 0.5)
                if weight <= 0:
                    continue

                target_pos: Tuple[float, float]
                priority: float
                reward: float

                if strategy == CuriosityStrategy.NOVELTY_SEEKING:
                    target_pos, priority, reward = self._goal_novelty_seeking(
                        profile, zone_ids, world_bounds
                    )
                elif strategy == CuriosityStrategy.SURPRISE_MAXIMIZATION:
                    target_pos, priority, reward = self._goal_surprise_maximization(
                        profile, zone_ids, world_bounds
                    )
                elif strategy == CuriosityStrategy.UNCERTAINTY_REDUCTION:
                    target_pos, priority, reward = self._goal_uncertainty_reduction(
                        profile, zone_ids, world_bounds
                    )
                elif strategy == CuriosityStrategy.INFORMATION_GAIN:
                    target_pos, priority, reward = self._goal_information_gain(
                        profile, zone_ids, world_bounds
                    )
                elif strategy == CuriosityStrategy.COMPETENCE_BUILDING:
                    target_pos, priority, reward = self._goal_competence_building(
                        profile, zone_ids, world_bounds
                    )
                else:
                    continue

                # Adjust priority by strategy weight
                adjusted_priority = priority * weight
                adjusted_reward = reward * weight

                goal = ExplorationGoal(
                    target_position=target_pos,
                    strategy=strategy,
                    priority=adjusted_priority,
                    estimated_reward=adjusted_reward,
                    expiry_time=_time_module.time() + self._DEFAULT_GOAL_EXPIRY_SECONDS,
                    tags=[strategy.value],
                )
                all_goals.append(goal)

            # Rank by priority descending
            all_goals.sort(key=lambda g: g.priority, reverse=True)

            # Take top N, but also include top from each strategy if possible
            selected: List[ExplorationGoal] = []
            seen_strategies: Set[str] = set()

            # First pass: pick top goal per strategy
            for goal in all_goals:
                if goal.strategy.value not in seen_strategies:
                    selected.append(goal)
                    seen_strategies.add(goal.strategy.value)
                    if len(selected) >= max_goals:
                        break

            # Second pass: fill remaining slots by priority if needed
            if len(selected) < max_goals:
                for goal in all_goals:
                    if goal not in selected:
                        selected.append(goal)
                        if len(selected) >= max_goals:
                            break

            # Store generated goals
            for goal in selected:
                self._goals[goal.id] = goal

            return selected[:max_goals]

    # ------------------------------------------------------------------
    # Phase Controller
    # ------------------------------------------------------------------

    def update_exploration_phase(self, agent_id: str) -> ExplorationPhase:
        """
        Automatically transition between SURVEY → FOCUS → EXPLOIT → REFRESH
        phases based on overall world coverage. Agents in SURVEY phase
        broadly explore; FOCUS phase targets specific interesting areas;
        EXPLOIT phase revisits rewarding locations; REFRESH phase resets
        when boredom threshold exceeded.
        """
        with self._lock:
            profile = self.get_curiosity_profile(agent_id)

            # Calculate overall coverage
            if self._zones:
                total_coverage = sum(
                    z.explored_percentage for z in self._zones.values()
                ) / len(self._zones)
            else:
                total_coverage = 0.0

            now = _time_module.time()
            phase: ExplorationPhase

            # Check for refresh (boredom)
            zone_count = len(profile.zone_visit_counts)
            revisit_ratio = 0.0
            if zone_count > 0:
                revisits = sum(1 for c in profile.zone_visit_counts.values() if c > 3)
                revisit_ratio = revisits / zone_count

            if revisit_ratio >= profile.boredom_threshold and total_coverage >= self._COVERAGE_EXPLOIT_THRESHOLD:
                phase = ExplorationPhase.REFRESH
                # Reset zone visit counts to encourage re-exploration
                profile.zone_visit_counts = {
                    k: max(0, v - 2) for k, v in profile.zone_visit_counts.items()
                }
            elif total_coverage >= self._COVERAGE_EXPLOIT_THRESHOLD:
                phase = ExplorationPhase.EXPLOIT
            elif total_coverage >= self._COVERAGE_FOCUS_THRESHOLD:
                phase = ExplorationPhase.FOCUS
            elif total_coverage >= self._COVERAGE_SURVEY_THRESHOLD:
                phase = ExplorationPhase.FOCUS
            else:
                phase = ExplorationPhase.SURVEY

            # Record phase transition
            if phase != profile.current_phase:
                self._agent_phase_history[agent_id] = self._agent_phase_history.get(agent_id, [])
                self._agent_phase_history[agent_id].append((now, phase))

            profile.current_phase = phase
            profile.last_active = now
            return phase

    # ------------------------------------------------------------------
    # Stats & Query
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive curiosity engine statistics."""
        with self._lock:
            phase_distribution: Dict[str, int] = {}
            strategy_distribution: Dict[str, int] = {}
            for profile in self._profiles.values():
                phase = profile.current_phase.value
                phase_distribution[phase] = phase_distribution.get(phase, 0) + 1
                strat = profile.dominant_strategy.value
                strategy_distribution[strat] = strategy_distribution.get(strat, 0) + 1

            type_distribution: Dict[str, int] = {}
            avg_novelty = 0.0
            avg_surprise = 0.0
            disc_count = len(self._discoveries)
            for disc in self._discoveries.values():
                t = disc.discovery_type.value if hasattr(disc.discovery_type, 'value') else disc.discovery_type
                type_distribution[t] = type_distribution.get(t, 0) + 1
                avg_novelty += disc.novelty_score
                avg_surprise += disc.surprise_score

            if disc_count > 0:
                avg_novelty /= disc_count
                avg_surprise /= disc_count

            total_coverage = 0.0
            if self._zones:
                total_coverage = sum(
                    z.explored_percentage for z in self._zones.values()
                ) / len(self._zones)

            return {
                "subsystem": "agent_curiosity_engine",
                "total_profiles": len(self._profiles),
                "total_discoveries": self._total_discoveries,
                "total_goals": self._total_goals_generated,
                "total_zones": self._total_zones_registered,
                "stored_discoveries": disc_count,
                "stored_zones": len(self._zones),
                "stored_goals": len(self._goals),
                "average_novelty_score": round(avg_novelty, 4),
                "average_surprise_score": round(avg_surprise, 4),
                "overall_coverage_pct": round(total_coverage * 100.0, 2),
                "phase_distribution": phase_distribution,
                "strategy_distribution": strategy_distribution,
                "discovery_type_distribution": type_distribution,
                "grid_cells": len(self._spatial_grid),
                "active_agents": len([
                    p for p in self._profiles.values()
                    if _time_module.time() - p.last_active < 3600.0
                ]),
            }

    def get_zone(self, zone_id: str) -> Optional[KnowledgeZone]:
        """Retrieve a knowledge zone by ID."""
        return self._zones.get(zone_id)

    def get_discovery(self, discovery_id: str) -> Optional[DiscoveryRecord]:
        """Retrieve a discovery record by ID."""
        return self._discoveries.get(discovery_id)

    def get_goal(self, goal_id: str) -> Optional[ExplorationGoal]:
        """Retrieve an exploration goal by ID."""
        return self._goals.get(goal_id)

    def get_agent_discoveries(
        self, agent_id: str, limit: int = 50
    ) -> List[DiscoveryRecord]:
        """Get discovery records for a specific agent."""
        disc_ids = self._agent_discoveries.get(agent_id, [])
        return [
            self._discoveries[did]
            for did in disc_ids[:limit]
            if did in self._discoveries
        ]

    def get_all_zones(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all registered knowledge zones."""
        zones = list(self._zones.values())[:limit]
        return [z.to_dict() for z in zones]

    # ------------------------------------------------------------------
    # Spatial Index Helpers
    # ------------------------------------------------------------------

    def _insert_zone_into_grid(self, zone: KnowledgeZone) -> None:
        """Add a zone to the spatial grid for fast lookup."""
        x1, y1, x2, y2 = zone.bounds
        min_col = int(x1 / self._grid_cell_size)
        max_col = int(x2 / self._grid_cell_size) + 1
        min_row = int(y1 / self._grid_cell_size)
        max_row = int(y2 / self._grid_cell_size) + 1

        for col in range(min_col, max_col):
            for row in range(min_row, max_row):
                key = (col, row)
                self._spatial_grid.setdefault(key, [])
                if zone.id not in self._spatial_grid[key]:
                    self._spatial_grid[key].append(zone.id)

    def _compute_world_bounds(self) -> Tuple[float, float, float, float]:
        """Compute the bounding box encompassing all registered zones."""
        if not self._zones:
            return (0.0, 0.0, 1000.0, 1000.0)

        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")

        for zone in self._zones.values():
            x1, y1, x2, y2 = zone.bounds
            min_x = min(min_x, x1)
            min_y = min(min_y, y1)
            max_x = max(max_x, x2)
            max_y = max(max_y, y2)

        return (min_x, min_y, max_x, max_y)

    # ------------------------------------------------------------------
    # Spatial Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _point_in_bounds(
        point: Tuple[float, float],
        bounds: Tuple[float, float, float, float],
    ) -> bool:
        """Check if a point is within the given bounds."""
        x, y = point
        x1, y1, x2, y2 = bounds
        return x1 <= x <= x2 and y1 <= y <= y2

    @staticmethod
    def _random_position_in_bounds(
        bounds: Tuple[float, float, float, float],
    ) -> Tuple[float, float]:
        """Generate a random position within the given bounds."""
        x1, y1, x2, y2 = bounds
        return (
            random.uniform(x1, x2),
            random.uniform(y1, y2),
        )

    def _unexplored_position_in_zone(
        self, zone: KnowledgeZone, profile: CuriosityProfile
    ) -> Tuple[float, float]:
        """Find a position within a zone that has not been visited yet."""
        x1, y1, x2, y2 = zone.bounds
        # Try to find a gap between visited positions
        visited_set = set(zone.visited_positions)

        best_pos = zone.center
        best_dist = 0.0

        for _ in range(30):
            candidate = self._random_position_in_bounds(zone.bounds)
            if candidate not in visited_set:
                min_dist = float("inf")
                for vp in visited_set:
                    d = math.hypot(candidate[0] - vp[0], candidate[1] - vp[1])
                    if d < min_dist:
                        min_dist = d
                if min_dist > best_dist:
                    best_dist = min_dist
                    best_pos = candidate

        return best_pos

    def _boundary_position_in_zone(self, zone: KnowledgeZone) -> Tuple[float, float]:
        """Pick a position near the boundary between explored and unexplored region."""
        x1, y1, x2, y2 = zone.bounds
        cx, cy = zone.center

        if zone.visited_positions:
            # Compute centroid of visited positions
            vx = sum(p[0] for p in zone.visited_positions) / len(zone.visited_positions)
            vy = sum(p[1] for p in zone.visited_positions) / len(zone.visited_positions)
            # Place target halfway between visited centroid and zone edge
            edge_x = x1 if vx > cx else x2
            edge_y = y1 if vy > cy else y2
            return (
                (vx + edge_x) / 2.0,
                (vy + edge_y) / 2.0,
            )

        return (cx, cy)

    def _zone_position_near_center(self, zone: KnowledgeZone) -> Tuple[float, float]:
        """Return a position near the center with slight random offset."""
        cx, cy = zone.center
        x1, y1, x2, y2 = zone.bounds
        offset_range = min(x2 - x1, y2 - y1) * 0.15
        return (
            cx + random.uniform(-offset_range, offset_range),
            cy + random.uniform(-offset_range, offset_range),
        )


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_curiosity_engine() -> AgentCuriosityEngine:
    """Get or create the singleton AgentCuriosityEngine instance."""
    return AgentCuriosityEngine.get_instance()