"""
SparkLabs Engine - Reality Bubble Projector"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class RealityZone(Enum):
    """Zones of fidelity around the player."""
    CORE = "core"                       # full simulation, ~15m radius
    SHADOW = "shadow"                   # lightweight sim, ~50m radius
    DEEP_SUPERPOSITION = "deep_superposition"  # probability cloud only


class EntityFidelity(Enum):
    """How concretely an entity is being simulated."""
    FULL = "full"               # all systems active
    LITE = "lite"               # only position + state
    PROBABILISTIC = "probabilistic"  # probability distribution only
    DORMANT = "dormant"         # not simulated


class BubblePhase(Enum):
    """Phases of the reality bubble cycle."""
    PROJECT = "project"
    OBSERVE = "observe"
    COLLAPSE = "collapse"
    DISSOLVE = "dissolve"
    PROPAGATE = "propagate"


class CollapseReason(Enum):
    """Why an entity was collapsed into concrete state."""
    PLAYER_PROXIMITY = "player_proximity"
    PLAYER_LINE_OF_SIGHT = "player_los"
    NARRATIVE_TRIGGER = "narrative_trigger"
    AI_QUERY = "ai_query"
    MANUAL = "manual"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class BubbleEntity:
    """An entity tracked by the reality bubble projector."""
    entity_id: str
    name: str
    category: str               # "npc", "item", "creature", "prop", "effect"
    position: Tuple[float, float, float]
    zone: RealityZone
    fidelity: EntityFidelity
    # Probabilistic state (used when in DEEP_SUPERPOSITION)
    probable_positions: List[Tuple[float, float, float]] = field(default_factory=list)
    probable_states: List[Tuple[str, float]] = field(default_factory=list)  # (state, prob)
    position_variance: float = 0.0   # how uncertain the position is (meters)
    state_entropy: float = 0.0       # how uncertain the state is (0-1)
    # Concrete state (used when in CORE/SHADOW)
    concrete_state: str = "idle"
    concrete_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    # History
    last_collapsed_at: float = 0.0
    last_dissolved_at: float = 0.0
    collapse_count: int = 0
    # Properties
    importance: float = 0.5     # 0-1, narrative/gameplay weight
    tags: List[str] = field(default_factory=list)


@dataclass
class BubbleConfig:
    """Configuration for the reality bubble."""
    core_radius: float = 15.0       # full simulation radius
    shadow_radius: float = 50.0     # lite simulation radius
    # Beyond shadow_radius = deep superposition
    max_probable_positions: int = 5  # samples for probability cloud
    collapse_cooldown_s: float = 2.0  # min time between collapses of same entity
    dissolve_cooldown_s: float = 1.0  # min time between dissolves of same entity
    propagation_step_s: float = 1.0  # how often distant probabilities update
    importance_bias: float = 0.3    # high-importance entities get larger effective bubble


@dataclass
class BubbleStats:
    """Aggregate statistics for the bubble projector."""
    total_cycles: int = 0
    total_collapses: int = 0
    total_dissolves: int = 0
    total_propagations: int = 0
    avg_core_count: float = 0.0
    avg_shadow_count: float = 0.0
    avg_deep_count: float = 0.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


@dataclass
class BubbleSnapshot:
    """Point-in-time snapshot of the bubble state."""
    timestamp: float
    player_position: Tuple[float, float, float]
    core_count: int
    shadow_count: int
    deep_count: int
    total_entities: int


# =============================================================================
# Engine Reality Bubble Projector
# =============================================================================

class EngineRealityBubbleProjector:
    """
    Singleton engine module that projects a fidelity bubble around the
    player and manages entity state transitions between zones.

    The projector runs a 5-phase cycle:
      1. PROJECT   - Position the bubble around the current player location
      2. OBSERVE   - Classify all entities by their distance-based zone
      3. COLLAPSE  - Materialize superposed entities that entered the bubble
      4. DISSOLVE  - Dematerialize concrete entities that left the bubble
      5. PROPAGATE - Update probabilistic state of deep-superposition entities

    The projector ensures smooth transitions and maintains consistency
    between what the player observes and what the engine simulates.
    """

    _instance: Optional["EngineRealityBubbleProjector"] = None
    _instance_lock = threading.Lock()

    # Position variance growth per propagation step (meters)
    VARIANCE_GROWTH_RATE = 0.5
    # Maximum position variance for deep superposition
    MAX_VARIANCE = 20.0
    # Maximum state entropy
    MAX_ENTROPY = 1.0
    # Entropy growth per propagation step
    ENTROPY_GROWTH_RATE = 0.05

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._config = BubbleConfig()
        self._player_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._player_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._entities: Dict[str, BubbleEntity] = {}
        self._stats = BubbleStats()
        self._cycle_count: int = 0
        self._last_propagation_at: float = 0.0
        self._active: bool = False
        self._snapshots: Deque[BubbleSnapshot] = deque(maxlen=100)
        self._events: Deque[Dict[str, Any]] = deque(maxlen=100)

    @classmethod
    def get_instance(cls) -> "EngineRealityBubbleProjector":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Entity Registration
    # -------------------------------------------------------------------------

    def register_entity(self, entity_id: str, name: str, category: str,
                        position: Tuple[float, float, float],
                        importance: float = 0.5,
                        initial_state: str = "idle",
                        tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Register a new entity with the bubble projector."""
        with self._lock:
            if entity_id in self._entities:
                return {"error": f"Entity already registered: {entity_id}"}
            entity = BubbleEntity(
                entity_id=entity_id,
                name=name,
                category=category,
                position=position,
                zone=RealityZone.DEEP_SUPERPOSITION,
                fidelity=EntityFidelity.PROBABILISTIC,
                probable_positions=[position],
                probable_states=[(initial_state, 1.0)],
                concrete_state=initial_state,
                importance=max(0.0, min(1.0, importance)),
                tags=list(tags or []),
            )
            # Initial classification
            self._classify_entity(entity)
            self._entities[entity_id] = entity
            return self._entity_to_dict(entity)

    def remove_entity(self, entity_id: str) -> Dict[str, Any]:
        """Remove an entity from tracking."""
        with self._lock:
            entity = self._entities.pop(entity_id, None)
            if entity is None:
                return {"error": f"Entity not found: {entity_id}"}
            return {"removed": True, "entity_id": entity_id}

    def update_player(self, position: Tuple[float, float, float],
                      velocity: Optional[Tuple[float, float, float]] = None) -> Dict[str, Any]:
        """Update player position and velocity."""
        with self._lock:
            self._player_position = position
            if velocity is not None:
                self._player_velocity = velocity
            return {
                "player_position": list(position),
                "player_velocity": list(self._player_velocity),
            }

    def update_config(self, **kwargs) -> Dict[str, Any]:
        """Update bubble configuration."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, float(value))
            return self._config_to_dict()

    def _config_to_dict(self) -> Dict[str, Any]:
        return {
            "core_radius": self._config.core_radius,
            "shadow_radius": self._config.shadow_radius,
            "max_probable_positions": self._config.max_probable_positions,
            "collapse_cooldown_s": self._config.collapse_cooldown_s,
            "dissolve_cooldown_s": self._config.dissolve_cooldown_s,
            "propagation_step_s": self._config.propagation_step_s,
            "importance_bias": self._config.importance_bias,
        }

    # -------------------------------------------------------------------------
    # Phase 1: PROJECT - Position the bubble
    # -------------------------------------------------------------------------

    def _project_phase(self) -> Dict[str, Any]:
        """The bubble follows the player. No-op if player hasn't moved."""
        return {
            "player_position": list(self._player_position),
            "core_radius": self._config.core_radius,
            "shadow_radius": self._config.shadow_radius,
        }

    # -------------------------------------------------------------------------
    # Phase 2: OBSERVE - Classify entities by zone
    # -------------------------------------------------------------------------

    def _classify_entity(self, entity: BubbleEntity) -> None:
        """Classify an entity into a zone based on distance to player."""
        distance = self._distance(entity.position, self._player_position)
        # Importance biases the effective bubble size
        effective_core = self._config.core_radius * (1.0 + entity.importance * self._config.importance_bias)
        effective_shadow = self._config.shadow_radius * (1.0 + entity.importance * self._config.importance_bias)

        if distance <= effective_core:
            new_zone = RealityZone.CORE
        elif distance <= effective_shadow:
            new_zone = RealityZone.SHADOW
        else:
            new_zone = RealityZone.DEEP_SUPERPOSITION

        entity.zone = new_zone

    def _observe_phase(self) -> Dict[str, Any]:
        """Classify all entities by their current zone."""
        counts = {RealityZone.CORE: 0, RealityZone.SHADOW: 0, RealityZone.DEEP_SUPERPOSITION: 0}
        for entity in self._entities.values():
            self._classify_entity(entity)
            counts[entity.zone] += 1
        return {
            "core_count": counts[RealityZone.CORE],
            "shadow_count": counts[RealityZone.SHADOW],
            "deep_count": counts[RealityZone.DEEP_SUPERPOSITION],
        }

    # -------------------------------------------------------------------------
    # Phase 3: COLLAPSE - Materialize superposed entities
    # -------------------------------------------------------------------------

    def _collapse_phase(self) -> int:
        """Collapse entities that entered the bubble from superposition."""
        now = time.time()
        collapsed = 0
        for entity in self._entities.values():
            # Only collapse entities in CORE or SHADOW that are still probabilistic
            if entity.zone == RealityZone.DEEP_SUPERPOSITION:
                continue
            if entity.fidelity == EntityFidelity.FULL:
                continue
            # Cooldown check
            if now - entity.last_collapsed_at < self._config.collapse_cooldown_s:
                continue
            # Collapse: pick a concrete position from probable positions
            if entity.probable_positions:
                # Pick the most likely position (first one with highest weight)
                entity.position = entity.probable_positions[0]
            # Pick concrete state from probable states
            if entity.probable_states:
                # Sort by probability, take highest
                sorted_states = sorted(entity.probable_states, key=lambda x: -x[1])
                entity.concrete_state = sorted_states[0][0]
            # Update fidelity based on zone
            if entity.zone == RealityZone.CORE:
                entity.fidelity = EntityFidelity.FULL
            else:
                entity.fidelity = EntityFidelity.LITE
            # Reset probabilistic uncertainty
            entity.position_variance = 0.0
            entity.state_entropy = 0.0
            entity.last_collapsed_at = now
            entity.collapse_count += 1
            collapsed += 1
            self._events.append({
                "type": "collapse",
                "entity_id": entity.entity_id,
                "zone": entity.zone.value,
                "fidelity": entity.fidelity.value,
                "position": list(entity.position),
                "state": entity.concrete_state,
                "timestamp": now,
            })

        self._stats.total_collapses += collapsed
        return collapsed

    def force_collapse(self, entity_id: str,
                       reason: str = "manual") -> Dict[str, Any]:
        """Manually force an entity to collapse into concrete state."""
        with self._lock:
            entity = self._entities.get(entity_id)
            if entity is None:
                return {"error": f"Entity not found: {entity_id}"}
            now = time.time()
            if entity.probable_positions:
                entity.position = entity.probable_positions[0]
            if entity.probable_states:
                sorted_states = sorted(entity.probable_states, key=lambda x: -x[1])
                entity.concrete_state = sorted_states[0][0]
            entity.fidelity = EntityFidelity.FULL
            entity.position_variance = 0.0
            entity.state_entropy = 0.0
            entity.last_collapsed_at = now
            entity.collapse_count += 1
            self._stats.total_collapses += 1
            self._events.append({
                "type": "force_collapse",
                "entity_id": entity_id,
                "reason": reason,
                "timestamp": now,
            })
            return self._entity_to_dict(entity)

    # -------------------------------------------------------------------------
    # Phase 4: DISSOLVE - Dematerialize concrete entities
    # -------------------------------------------------------------------------

    def _dissolve_phase(self) -> int:
        """Dissolve entities that left the bubble into superposition."""
        now = time.time()
        dissolved = 0
        for entity in self._entities.values():
            # Only dissolve entities that are now in DEEP_SUPERPOSITION but were concrete
            if entity.zone != RealityZone.DEEP_SUPERPOSITION:
                continue
            if entity.fidelity == EntityFidelity.PROBABILISTIC:
                continue
            if entity.fidelity == EntityFidelity.DORMANT:
                continue
            # Cooldown check
            if now - entity.last_dissolved_at < self._config.dissolve_cooldown_s:
                continue
            # Dissolve: convert concrete state to probable states
            entity.probable_positions = [entity.position]
            entity.probable_states = [(entity.concrete_state, 1.0)]
            entity.fidelity = EntityFidelity.PROBABILISTIC
            # Initial uncertainty
            entity.position_variance = 1.0
            entity.state_entropy = 0.1
            entity.last_dissolved_at = now
            dissolved += 1
            self._events.append({
                "type": "dissolve",
                "entity_id": entity.entity_id,
                "position": list(entity.position),
                "timestamp": now,
            })

        self._stats.total_dissolves += dissolved
        return dissolved

    # -------------------------------------------------------------------------
    # Phase 5: PROPAGATE - Update distant probabilities
    # -------------------------------------------------------------------------

    def _propagate_phase(self) -> int:
        """Propagate probability distributions for deep-superposition entities."""
        now = time.time()
        propagated = 0
        for entity in self._entities.values():
            if entity.zone != RealityZone.DEEP_SUPERPOSITION:
                continue
            if entity.fidelity != EntityFidelity.PROBABILISTIC:
                continue

            # Grow position variance
            entity.position_variance = min(
                self.MAX_VARIANCE,
                entity.position_variance + self.VARIANCE_GROWTH_RATE
            )
            # Grow state entropy
            entity.state_entropy = min(
                self.MAX_ENTROPY,
                entity.state_entropy + self.ENTROPY_GROWTH_RATE
            )
            # Generate new probable positions by sampling around current position
            new_positions = [entity.position]
            base = entity.position
            var = entity.position_variance
            for _ in range(min(self._config.max_probable_positions - 1, 4)):
                offset = (
                    random.gauss(0, var),
                    random.gauss(0, var),
                    random.gauss(0, var * 0.3),  # less z variance
                )
                new_pos = (base[0] + offset[0], base[1] + offset[1], base[2] + offset[2])
                new_positions.append(new_pos)
            entity.probable_positions = new_positions

            # Spread state probabilities based on entropy
            if entity.probable_states and entity.state_entropy > 0.2:
                # Add a small probability to neighboring states
                current_state = entity.probable_states[0][0]
                current_prob = entity.probable_states[0][1]
                # Decay current probability, add "wandering" state
                new_prob = max(0.3, current_prob - entity.state_entropy * 0.3)
                entity.probable_states = [(current_state, new_prob)]
                if entity.state_entropy > 0.5:
                    entity.probable_states.append(("wandering", entity.state_entropy * 0.3))
                # Normalize
                total = sum(p for _, p in entity.probable_states)
                if total > 0:
                    entity.probable_states = [(s, p / total) for s, p in entity.probable_states]

            propagated += 1

        self._stats.total_propagations += propagated
        return propagated

    # -------------------------------------------------------------------------
    # Bubble Cycle Orchestration
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single reality bubble cycle.

        Phases: PROJECT -> OBSERVE -> COLLAPSE -> DISSOLVE -> PROPAGATE
        """
        start_time = time.time()
        with self._lock:
            self._active = True
            phase = BubblePhase.PROJECT

            # Phase 1: PROJECT
            project_info = self._project_phase()

            # Phase 2: OBSERVE
            phase = BubblePhase.OBSERVE
            observe_info = self._observe_phase()

            # Phase 3: COLLAPSE
            phase = BubblePhase.COLLAPSE
            collapsed = self._collapse_phase()

            # Phase 4: DISSOLVE
            phase = BubblePhase.DISSOLVE
            dissolved = self._dissolve_phase()

            # Phase 5: PROPAGATE
            phase = BubblePhase.PROPAGATE
            propagated = self._propagate_phase()

            elapsed_ms = (time.time() - start_time) * 1000
            self._cycle_count += 1
            self._stats.total_cycles += 1
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)

            # Update rolling averages
            n = self._stats.total_cycles
            self._stats.avg_core_count = round(
                (self._stats.avg_core_count * (n - 1) + observe_info["core_count"]) / n, 2
            )
            self._stats.avg_shadow_count = round(
                (self._stats.avg_shadow_count * (n - 1) + observe_info["shadow_count"]) / n, 2
            )
            self._stats.avg_deep_count = round(
                (self._stats.avg_deep_count * (n - 1) + observe_info["deep_count"]) / n, 2
            )

            # Take snapshot
            snapshot = BubbleSnapshot(
                timestamp=time.time(),
                player_position=self._player_position,
                core_count=observe_info["core_count"],
                shadow_count=observe_info["shadow_count"],
                deep_count=observe_info["deep_count"],
                total_entities=len(self._entities),
            )
            self._snapshots.append(snapshot)

            self._active = False

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "player_position": list(self._player_position),
                "core_count": observe_info["core_count"],
                "shadow_count": observe_info["shadow_count"],
                "deep_count": observe_info["deep_count"],
                "collapsed": collapsed,
                "dissolved": dissolved,
                "propagated": propagated,
                "total_entities": len(self._entities),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def simulate(self, cycles: int = 10,
                 move_player: bool = True) -> Dict[str, Any]:
        """Run multiple bubble cycles with synthetic data."""
        with self._lock:
            # Seed entities if empty
            if not self._entities:
                self._seed_synthetic_entities()
            results = []
            for i in range(max(1, cycles)):
                if move_player:
                    # Move player in a circle
                    angle = i * 0.3
                    radius = 20.0
                    new_pos = (
                        math.cos(angle) * radius,
                        math.sin(angle) * radius,
                        0.0,
                    )
                    self.update_player(new_pos)
                results.append(self.run_cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_stats": self._stats_to_dict(),
            }

    def _seed_synthetic_entities(self) -> None:
        """Seed synthetic entities for simulation."""
        categories = ["npc", "creature", "item", "prop"]
        names_by_cat = {
            "npc": ["villager", "guard", "merchant", "traveler"],
            "creature": ["wolf", "deer", "goblin", "rabbit"],
            "item": ["sword", "potion", "chest", "gem"],
            "prop": ["tree", "rock", "bush", "barrel"],
        }
        for i in range(40):
            cat = random.choice(categories)
            name = random.choice(names_by_cat[cat])
            # Spread entities in a 100m radius
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(5, 80)
            pos = (math.cos(angle) * dist, math.sin(angle) * dist, 0.0)
            self.register_entity(
                entity_id=f"ent_{i}",
                name=name,
                category=cat,
                position=pos,
                importance=round(random.uniform(0.1, 0.9), 2),
                initial_state=random.choice(["idle", "wandering", "alert", "resting"]),
                tags=[cat],
            )

    # -------------------------------------------------------------------------
    # Query and Inspection
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return current bubble projector status."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "player_position": list(self._player_position),
                "player_velocity": list(self._player_velocity),
                "total_entities": len(self._entities),
                "config": self._config_to_dict(),
                "stats": self._stats_to_dict(),
            }

    def _stats_to_dict(self) -> Dict[str, Any]:
        return {
            "total_cycles": self._stats.total_cycles,
            "total_collapses": self._stats.total_collapses,
            "total_dissolves": self._stats.total_dissolves,
            "total_propagations": self._stats.total_propagations,
            "avg_core_count": self._stats.avg_core_count,
            "avg_shadow_count": self._stats.avg_shadow_count,
            "avg_deep_count": self._stats.avg_deep_count,
            "last_cycle_time_ms": self._stats.last_cycle_time_ms,
            "active": self._stats.active,
        }

    def list_entities(self, zone: Optional[str] = None,
                      limit: int = 20) -> List[Dict[str, Any]]:
        """List entities, optionally filtered by zone."""
        with self._lock:
            results = []
            for entity in self._entities.values():
                if zone and entity.zone.value != zone:
                    continue
                results.append(self._entity_to_dict(entity))
            # Sort by distance to player
            results.sort(key=lambda e: self._distance(
                tuple(e["position"]), self._player_position))
            return results[:limit]

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entity = self._entities.get(entity_id)
            return self._entity_to_dict(entity) if entity else None

    def list_snapshots(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._snapshot_to_dict(s) for s in list(self._snapshots)[-limit:]]

    def list_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._events)[-limit:]

    def query_observable(self, radius: Optional[float] = None) -> Dict[str, Any]:
        """Query what entities are currently observable (collapsed) within radius."""
        with self._lock:
            r = radius or self._config.shadow_radius
            observable = []
            for entity in self._entities.values():
                if entity.fidelity == EntityFidelity.DORMANT:
                    continue
                if entity.fidelity == EntityFidelity.PROBABILISTIC:
                    continue
                dist = self._distance(entity.position, self._player_position)
                if dist <= r:
                    observable.append({
                        "entity_id": entity.entity_id,
                        "name": entity.name,
                        "category": entity.category,
                        "position": list(entity.position),
                        "distance": round(dist, 2),
                        "state": entity.concrete_state,
                        "fidelity": entity.fidelity.value,
                    })
            observable.sort(key=lambda e: e["distance"])
            return {
                "radius": r,
                "observable_count": len(observable),
                "entities": observable,
            }

    def query_superposition(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Query entities in deep superposition (probabilistic)."""
        with self._lock:
            results = []
            for entity in self._entities.values():
                if entity.fidelity != EntityFidelity.PROBABILISTIC:
                    continue
                results.append({
                    "entity_id": entity.entity_id,
                    "name": entity.name,
                    "category": entity.category,
                    "probable_positions": [list(p) for p in entity.probable_positions],
                    "probable_states": entity.probable_states,
                    "position_variance": round(entity.position_variance, 2),
                    "state_entropy": round(entity.state_entropy, 3),
                    "importance": entity.importance,
                })
            return results[:limit]

    def reset(self) -> Dict[str, Any]:
        """Reset the projector to empty state."""
        with self._lock:
            count = len(self._entities)
            self._entities.clear()
            self._snapshots.clear()
            self._events.clear()
            self._stats = BubbleStats()
            self._cycle_count = 0
            self._player_position = (0.0, 0.0, 0.0)
            self._player_velocity = (0.0, 0.0, 0.0)
            return {"reset": True, "cleared_entities": count}

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    @staticmethod
    def _distance(a: Tuple[float, float, float],
                  b: Tuple[float, float, float]) -> float:
        """Euclidean distance between two 3D points."""
        return math.sqrt(
            (a[0] - b[0]) ** 2 +
            (a[1] - b[1]) ** 2 +
            (a[2] - b[2]) ** 2
        )

    # -------------------------------------------------------------------------
    # Serialization helpers
    # -------------------------------------------------------------------------

    def _entity_to_dict(self, entity: BubbleEntity) -> Dict[str, Any]:
        return {
            "entity_id": entity.entity_id,
            "name": entity.name,
            "category": entity.category,
            "position": list(entity.position),
            "zone": entity.zone.value,
            "fidelity": entity.fidelity.value,
            "probable_positions": [list(p) for p in entity.probable_positions],
            "probable_states": entity.probable_states,
            "position_variance": round(entity.position_variance, 2),
            "state_entropy": round(entity.state_entropy, 3),
            "concrete_state": entity.concrete_state,
            "concrete_velocity": list(entity.concrete_velocity),
            "last_collapsed_at": entity.last_collapsed_at,
            "last_dissolved_at": entity.last_dissolved_at,
            "collapse_count": entity.collapse_count,
            "importance": entity.importance,
            "tags": entity.tags,
        }

    def _snapshot_to_dict(self, s: BubbleSnapshot) -> Dict[str, Any]:
        return {
            "timestamp": s.timestamp,
            "player_position": list(s.player_position),
            "core_count": s.core_count,
            "shadow_count": s.shadow_count,
            "deep_count": s.deep_count,
            "total_entities": s.total_entities,
        }
