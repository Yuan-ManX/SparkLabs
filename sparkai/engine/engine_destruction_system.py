"""
SparkLabs Engine - Destruction Physics System

A comprehensive destruction and fracture physics system providing
configurable fracture patterns, Voronoi-based shattering, debris
simulation, structural integrity modeling, and efficient debris
pooling for the SparkLabs game engine.

Architecture:
  DestructionPhysicsEngine (Singleton)
    |-- FracturePattern       — predefined break pattern configurations
    |-- VoronoiFracture       — Voronoi diagram-based shattering
    |-- DestructionPhysics    — debris simulation and impulse resolution
    |-- StructuralIntegrity   — load-bearing and collapse modeling
    |-- DebrisPool            — object pooling for debris instances

Destruction Pipeline:
  1. Impact event triggers fracture at a contact point
  2. FracturePattern determines the break style (radial, grid, etc.)
  3. VoronoiFracture generates shard geometry via Voronoi cells
  4. DestructionPhysics applies impulse to fragments
  5. StructuralIntegrity evaluates support loss and cascading failure
  6. DebrisPool manages fragment lifecycle and recycling

Usage:
    engine = get_destruction_physics_engine()
    engine.fracture_object(object_id, impact_point=(0.5, 0.5), force=100.0)
    engine.update(delta_time)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FractureStyle(Enum):
    """Style of fracture pattern for object destruction."""
    RADIAL = "radial"
    GRID = "grid"
    VORONOI = "voronoi"
    CRACK = "crack"
    EXPLOSIVE = "explosive"
    SLICE = "slice"
    SHATTER = "shatter"


class MaterialStrength(Enum):
    """Material strength classification affecting fracture behavior."""
    GLASS = "glass"
    WOOD = "wood"
    STONE = "stone"
    METAL = "metal"
    CONCRETE = "concrete"
    ICE = "ice"
    CRYSTAL = "crystal"
    RUBBER = "rubber"
    FABRIC = "fabric"


class DebrisState(Enum):
    """Lifecycle state of a debris fragment."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    SETTLED = "settled"
    EXPIRED = "expired"


class StructureType(Enum):
    """Type of structure for integrity calculations."""
    WALL = "wall"
    COLUMN = "column"
    BEAM = "beam"
    FLOOR = "floor"
    ARCH = "arch"
    DOME = "dome"
    TOWER = "tower"
    BRIDGE = "bridge"


class CollapseMode(Enum):
    """Mode of structural collapse."""
    NONE = "none"
    LOCAL = "local"
    PROGRESSIVE = "progressive"
    PANCAKE = "pancake"
    TOPPLING = "toppling"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FracturePattern:
    """Predefined fracture pattern configuration.

    Defines how an object breaks when fractured, including the number
    of shards, crack propagation style, randomness, and material-
    specific behavior parameters.
    """
    pattern_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    style: FractureStyle = FractureStyle.RADIAL
    shard_count: int = 8
    crack_count: int = 3
    randomness: float = 0.3
    crack_propagation_depth: float = 0.8
    material: MaterialStrength = MaterialStrength.STONE
    impact_radius: float = 0.5
    min_shard_size: float = 0.05
    max_shard_size: float = 0.4
    secondary_fracture_probability: float = 0.2
    edge_jaggedness: float = 0.15

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "style": self.style.value,
            "shard_count": self.shard_count,
            "crack_count": self.crack_count,
            "randomness": self.randomness,
            "material": self.material.value,
            "impact_radius": self.impact_radius,
            "min_shard_size": self.min_shard_size,
            "max_shard_size": self.max_shard_size,
        }


@dataclass
class VoronoiFracture:
    """Voronoi diagram-based fracture generation.

    Generates realistic shattering patterns using Voronoi cells.
    Seed points are placed around the impact point with configurable
    distribution to create natural-looking fracture geometry.
    """
    fracture_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    seed_points: List[Tuple[float, float]] = field(default_factory=list)
    shard_count: int = 12
    impact_point: Tuple[float, float] = (0.5, 0.5)
    spread_radius: float = 0.4
    noise_strength: float = 0.1
    _shards: List[Dict[str, Any]] = field(default_factory=list, repr=False)
    _generated: bool = False

    def generate_seeds(self) -> List[Tuple[float, float]]:
        """Generate Voronoi seed points around the impact point."""
        self.seed_points = []
        rng = random.Random()

        # Seed at impact point
        self.seed_points.append(self.impact_point)

        for i in range(self.shard_count - 1):
            angle = (i / (self.shard_count - 1)) * 2.0 * math.pi
            distance = self.spread_radius * rng.uniform(0.2, 1.0)
            offset_x = self.impact_point[0] + math.cos(angle) * distance
            offset_y = self.impact_point[1] + math.sin(angle) * distance

            offset_x += rng.uniform(-self.noise_strength, self.noise_strength)
            offset_y += rng.uniform(-self.noise_strength, self.noise_strength)

            offset_x = max(0.0, min(1.0, offset_x))
            offset_y = max(0.0, min(1.0, offset_y))

            self.seed_points.append((offset_x, offset_y))

        return self.seed_points

    def compute_shard(self, point: Tuple[float, float],
                      index: int) -> Dict[str, Any]:
        """Compute the Voronoi cell for a single seed point."""
        px, py = point
        closest_seed = -1
        min_dist = float("inf")

        for i, seed in enumerate(self.seed_points):
            dx = px - seed[0]
            dy = py - seed[1]
            dist = dx * dx + dy * dy
            if dist < min_dist:
                min_dist = dist
                closest_seed = i

        return {
            "shard_index": closest_seed,
            "point": (px, py),
            "distance": math.sqrt(min_dist),
        }

    def generate_shards(self, resolution: int = 64) -> List[Dict[str, Any]]:
        """Generate all shards by computing Voronoi cells on a grid."""
        self.generate_seeds()
        self._shards = []

        shard_data: Dict[int, List[Tuple[float, float]]] = defaultdict(list)

        for y in range(resolution):
            for x in range(resolution):
                px = x / resolution
                py = y / resolution
                result = self.compute_shard((px, py), x + y * resolution)
                shard_data[result["shard_index"]].append(result["point"])

        for shard_idx, points in shard_data.items():
            if len(points) < 3:
                continue

            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            center = (sum(xs) / len(xs), sum(ys) / len(ys))

            seed = self.seed_points[shard_idx]
            dx = center[0] - seed[0]
            dy = center[1] - seed[1]
            direction = math.atan2(dy, dx)

            self._shards.append({
                "shard_index": shard_idx,
                "center": center,
                "point_count": len(points),
                "launch_direction": direction,
                "launch_speed": math.sqrt(dx * dx + dy * dy) * 2.0,
                "area": len(points) / (resolution * resolution),
            })

        self._generated = True
        return self._shards

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fracture_id": self.fracture_id,
            "shard_count": self.shard_count,
            "impact_point": list(self.impact_point),
            "spread_radius": self.spread_radius,
            "seed_count": len(self.seed_points),
            "shards_generated": len(self._shards),
            "generated": self._generated,
        }


@dataclass
class DestructionPhysics:
    """Physics simulation for debris fragments after fracture.

    Manages the motion of debris pieces including initial impulse
    from the fracture event, gravity, air resistance, ground collision,
    and settling behavior.
    """
    physics_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    debris_pieces: List[Dict[str, Any]] = field(default_factory=list)
    gravity: float = 9.81
    air_resistance: float = 0.1
    ground_friction: float = 0.6
    restitution: float = 0.2
    settle_threshold: float = 0.01
    max_lifetime: float = 5.0
    _active_count: int = 0
    _settled_count: int = 0

    def spawn_debris(self, shards: List[Dict[str, Any]],
                     impact_force: float,
                     position: Tuple[float, float, float]) -> None:
        """Spawn debris pieces from fracture shards."""
        for shard in shards:
            speed = shard.get("launch_speed", 0.5) * impact_force
            direction = shard.get("launch_direction", 0.0)

            vx = math.cos(direction) * speed * random.uniform(0.5, 1.5)
            vy = math.sin(direction) * speed * random.uniform(0.5, 1.5)
            vz = impact_force * random.uniform(0.3, 0.8)

            piece = {
                "piece_id": uuid.uuid4().hex[:8],
                "position": [position[0], position[1], position[2]],
                "velocity": [vx, vy, vz],
                "angular_velocity": random.uniform(-5.0, 5.0),
                "rotation": random.uniform(0.0, 2.0 * math.pi),
                "scale": random.uniform(0.3, 1.0),
                "mass": random.uniform(0.1, 1.0),
                "lifetime": self.max_lifetime * random.uniform(0.8, 1.2),
                "age": 0.0,
                "state": DebrisState.ACTIVE,
                "shard_index": shard.get("shard_index", 0),
            }
            self.debris_pieces.append(piece)

        self._active_count = len(self.debris_pieces)

    def update(self, delta_time: float) -> None:
        """Update all debris pieces physics."""
        alive = []
        for piece in self.debris_pieces:
            if piece["state"] in (DebrisState.EXPIRED, DebrisState.INACTIVE):
                continue

            piece["age"] += delta_time
            if piece["age"] >= piece["lifetime"]:
                piece["state"] = DebrisState.EXPIRED
                continue

            # Gravity
            piece["velocity"][2] -= self.gravity * delta_time

            # Air resistance
            air_factor = 1.0 - self.air_resistance * delta_time
            piece["velocity"][0] *= air_factor
            piece["velocity"][1] *= air_factor
            piece["velocity"][2] *= air_factor

            # Update position
            piece["position"][0] += piece["velocity"][0] * delta_time
            piece["position"][1] += piece["velocity"][1] * delta_time
            piece["position"][2] += piece["velocity"][2] * delta_time

            # Ground collision
            if piece["position"][2] <= 0.0:
                piece["position"][2] = 0.0
                piece["velocity"][2] *= -self.restitution
                piece["velocity"][0] *= (1.0 - self.ground_friction * delta_time)
                piece["velocity"][1] *= (1.0 - self.ground_friction * delta_time)

                speed = math.sqrt(piece["velocity"][0] ** 2 +
                                  piece["velocity"][1] ** 2 +
                                  piece["velocity"][2] ** 2)
                if speed < self.settle_threshold:
                    piece["state"] = DebrisState.SETTLED
                    self._settled_count += 1

            piece["rotation"] += piece["angular_velocity"] * delta_time
            alive.append(piece)

        self.debris_pieces = alive
        self._active_count = sum(
            1 for p in self.debris_pieces if p["state"] == DebrisState.ACTIVE
        )

    def clear_debris(self) -> None:
        """Remove all debris pieces."""
        self.debris_pieces.clear()
        self._active_count = 0
        self._settled_count = 0

    def get_active_debris(self) -> List[Dict[str, Any]]:
        return [p for p in self.debris_pieces if p["state"] == DebrisState.ACTIVE]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "physics_id": self.physics_id,
            "total_pieces": len(self.debris_pieces),
            "active_count": self._active_count,
            "settled_count": self._settled_count,
            "gravity": self.gravity,
            "air_resistance": self.air_resistance,
        }


@dataclass
class StructuralIntegrity:
    """Models structural integrity for building collapse simulation.

    Tracks load-bearing elements, support relationships, and computes
    cascading failure when structural elements are destroyed. Supports
    different collapse modes based on structural type and damage.
    """
    integrity_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    structure_type: StructureType = StructureType.WALL
    total_integrity: float = 100.0
    current_integrity: float = 100.0
    damage_threshold: float = 30.0
    collapse_threshold: float = 0.0
    collapse_mode: CollapseMode = CollapseMode.NONE
    support_elements: List[str] = field(default_factory=list)
    supported_by: List[str] = field(default_factory=list)
    load_factor: float = 1.0
    vibration_damping: float = 0.95
    _integrity_history: deque = field(default_factory=lambda: deque(maxlen=60), repr=False)
    _last_damage_time: float = 0.0

    def apply_damage(self, damage: float, impact_point: Optional[Tuple[float, float, float]] = None) -> CollapseMode:
        """Apply damage to the structure and determine collapse mode."""
        self.current_integrity = max(0.0, self.current_integrity - damage)
        self._last_damage_time = _time_module.time()
        self._integrity_history.append(self.current_integrity)

        if self.current_integrity <= self.collapse_threshold:
            self.collapse_mode = self._determine_collapse_mode()
            return self.collapse_mode

        if self.current_integrity <= self.damage_threshold:
            self.collapse_mode = CollapseMode.PROGRESSIVE
            return self.collapse_mode

        if self.current_integrity < self.total_integrity * 0.5:
            self.collapse_mode = CollapseMode.LOCAL
            return self.collapse_mode

        self.collapse_mode = CollapseMode.NONE
        return self.collapse_mode

    def _determine_collapse_mode(self) -> CollapseMode:
        """Determine the collapse mode based on structure type and damage."""
        if self.structure_type == StructureType.TOWER:
            return CollapseMode.TOPPLING
        elif self.structure_type in (StructureType.FLOOR, StructureType.BEAM):
            return CollapseMode.PANCAKE
        elif self.structure_type == StructureType.BRIDGE:
            return CollapseMode.PROGRESSIVE
        else:
            return CollapseMode.LOCAL

    def get_integrity_ratio(self) -> float:
        """Get the current integrity as a ratio (0.0 to 1.0)."""
        if self.total_integrity <= 0.0:
            return 0.0
        return self.current_integrity / self.total_integrity

    def is_collapsed(self) -> bool:
        return self.collapse_mode != CollapseMode.NONE

    def repair(self, amount: float) -> None:
        """Repair structural integrity."""
        self.current_integrity = min(self.total_integrity,
                                     self.current_integrity + amount)
        if self.current_integrity > self.damage_threshold:
            self.collapse_mode = CollapseMode.NONE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integrity_id": self.integrity_id,
            "structure_type": self.structure_type.value,
            "total_integrity": self.total_integrity,
            "current_integrity": self.current_integrity,
            "integrity_ratio": self.get_integrity_ratio(),
            "collapse_mode": self.collapse_mode.value,
            "support_elements": list(self.support_elements),
            "supported_by": list(self.supported_by),
            "load_factor": self.load_factor,
        }


@dataclass
class DebrisPool:
    """Object pool for efficient debris fragment management.

    Pre-allocates debris objects and recycles them to avoid
    garbage collection overhead during intense destruction events.
    Supports configurable pool sizing and warmup.
    """
    pool_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    max_pool_size: int = 500
    initial_size: int = 100
    _pool: deque = field(default_factory=deque, repr=False)
    _active: List[str] = field(default_factory=list, repr=False)
    _acquired_count: int = 0
    _released_count: int = 0
    _overflow_count: int = 0

    def __post_init__(self) -> None:
        self._warmup()

    def _warmup(self) -> None:
        """Pre-allocate debris objects in the pool."""
        for _ in range(self.initial_size):
            self._pool.append(self._create_debris_object())

    @staticmethod
    def _create_debris_object() -> Dict[str, Any]:
        return {
            "debris_id": uuid.uuid4().hex[:8],
            "position": [0.0, 0.0, 0.0],
            "velocity": [0.0, 0.0, 0.0],
            "rotation": 0.0,
            "angular_velocity": 0.0,
            "scale": 1.0,
            "mass": 1.0,
            "age": 0.0,
            "lifetime": 5.0,
            "state": DebrisState.INACTIVE,
            "fracture_style": FractureStyle.SHATTER.value,
            "material": MaterialStrength.STONE.value,
        }

    def acquire(self) -> Dict[str, Any]:
        """Acquire a debris object from the pool."""
        if self._pool:
            obj = self._pool.popleft()
            obj["state"] = DebrisState.ACTIVE
            obj["age"] = 0.0
            self._active.append(obj["debris_id"])
            self._acquired_count += 1
            return obj

        obj = self._create_debris_object()
        obj["state"] = DebrisState.ACTIVE
        self._active.append(obj["debris_id"])
        self._acquired_count += 1
        self._overflow_count += 1
        return obj

    def release(self, debris_id: str) -> bool:
        """Release a debris object back to the pool."""
        if debris_id in self._active:
            self._active.remove(debris_id)
            self._released_count += 1

            if len(self._pool) < self.max_pool_size:
                obj = self._create_debris_object()
                obj["debris_id"] = debris_id
                self._pool.append(obj)
            return True
        return False

    def release_all(self) -> None:
        """Release all active debris back to the pool."""
        for debris_id in list(self._active):
            self.release(debris_id)

    def get_active_count(self) -> int:
        return len(self._active)

    def get_pool_available(self) -> int:
        return len(self._pool)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pool_id": self.pool_id,
            "max_pool_size": self.max_pool_size,
            "pool_available": len(self._pool),
            "active_count": len(self._active),
            "acquired_count": self._acquired_count,
            "released_count": self._released_count,
            "overflow_count": self._overflow_count,
        }


# ---------------------------------------------------------------------------
# Material Fracture Presets
# ---------------------------------------------------------------------------

_MATERIAL_PRESETS: Dict[MaterialStrength, Dict[str, Any]] = {
    MaterialStrength.GLASS: {
        "shard_count": 15, "crack_count": 5, "randomness": 0.1,
        "impact_radius": 0.6, "edge_jaggedness": 0.05, "restitution": 0.1,
    },
    MaterialStrength.WOOD: {
        "shard_count": 6, "crack_count": 3, "randomness": 0.4,
        "impact_radius": 0.3, "edge_jaggedness": 0.3, "restitution": 0.15,
    },
    MaterialStrength.STONE: {
        "shard_count": 10, "crack_count": 4, "randomness": 0.25,
        "impact_radius": 0.4, "edge_jaggedness": 0.2, "restitution": 0.1,
    },
    MaterialStrength.METAL: {
        "shard_count": 4, "crack_count": 2, "randomness": 0.15,
        "impact_radius": 0.2, "edge_jaggedness": 0.1, "restitution": 0.3,
    },
    MaterialStrength.CONCRETE: {
        "shard_count": 12, "crack_count": 5, "randomness": 0.3,
        "impact_radius": 0.5, "edge_jaggedness": 0.25, "restitution": 0.05,
    },
    MaterialStrength.ICE: {
        "shard_count": 8, "crack_count": 3, "randomness": 0.1,
        "impact_radius": 0.45, "edge_jaggedness": 0.05, "restitution": 0.05,
    },
    MaterialStrength.CRYSTAL: {
        "shard_count": 20, "crack_count": 6, "randomness": 0.05,
        "impact_radius": 0.7, "edge_jaggedness": 0.02, "restitution": 0.15,
    },
    MaterialStrength.RUBBER: {
        "shard_count": 2, "crack_count": 1, "randomness": 0.5,
        "impact_radius": 0.1, "edge_jaggedness": 0.4, "restitution": 0.7,
    },
    MaterialStrength.FABRIC: {
        "shard_count": 1, "crack_count": 1, "randomness": 0.6,
        "impact_radius": 0.05, "edge_jaggedness": 0.5, "restitution": 0.1,
    },
}


# ---------------------------------------------------------------------------
# DestructionPhysicsEngine — Unified Destruction Singleton
# ---------------------------------------------------------------------------

class DestructionPhysicsEngine:
    """Complete destruction and fracture physics engine for SparkLabs.

    Manages fracture pattern generation, Voronoi-based shattering,
    debris physics simulation, structural integrity modeling, and
    efficient debris pooling for high-performance destruction events.
    """

    _instance: Optional["DestructionPhysicsEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "DestructionPhysicsEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "DestructionPhysicsEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._fracture_patterns: Dict[str, FracturePattern] = {}
        self._voronoi_fractures: Dict[str, VoronoiFracture] = {}
        self._destruction_physics = DestructionPhysics()
        self._structures: Dict[str, StructuralIntegrity] = {}
        self._debris_pool = DebrisPool()
        self._fracture_count: int = 0
        self._frame_count: int = 0
        self._total_debris_spawned: int = 0

    def create_fracture_pattern(self, name: str = "",
                                style: FractureStyle = FractureStyle.RADIAL,
                                material: MaterialStrength = MaterialStrength.STONE
                                ) -> FracturePattern:
        """Create a fracture pattern with material-based presets."""
        preset = _MATERIAL_PRESETS.get(material, _MATERIAL_PRESETS[MaterialStrength.STONE])
        pattern = FracturePattern(
            name=name, style=style, material=material,
            shard_count=preset["shard_count"],
            crack_count=preset["crack_count"],
            randomness=preset["randomness"],
            impact_radius=preset["impact_radius"],
            edge_jaggedness=preset["edge_jaggedness"],
        )
        self._fracture_patterns[pattern.pattern_id] = pattern
        return pattern

    def get_fracture_pattern(self, pattern_id: str) -> Optional[FracturePattern]:
        return self._fracture_patterns.get(pattern_id)

    def fracture_object(self, object_id: str,
                        impact_point: Tuple[float, float] = (0.5, 0.5),
                        force: float = 100.0,
                        pattern: Optional[FracturePattern] = None,
                        position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
                        ) -> List[Dict[str, Any]]:
        """Fracture an object at the specified impact point."""
        if pattern is None:
            pattern = FracturePattern(
                name="default", style=FractureStyle.RADIAL,
                material=MaterialStrength.STONE,
            )

        voronoi = VoronoiFracture(
            shard_count=pattern.shard_count,
            impact_point=impact_point,
            spread_radius=pattern.impact_radius,
            noise_strength=pattern.randomness,
        )
        shards = voronoi.generate_shards()
        self._voronoi_fractures[voronoi.fracture_id] = voronoi

        self._destruction_physics.spawn_debris(shards, force, position)
        self._fracture_count += 1
        self._total_debris_spawned += len(shards)

        return shards

    def create_structure(self, structure_type: StructureType = StructureType.WALL,
                         total_integrity: float = 100.0,
                         damage_threshold: float = 30.0) -> StructuralIntegrity:
        """Create a structural integrity simulation for a building element."""
        structure = StructuralIntegrity(
            structure_type=structure_type,
            total_integrity=total_integrity,
            current_integrity=total_integrity,
            damage_threshold=damage_threshold,
        )
        self._structures[structure.integrity_id] = structure
        return structure

    def get_structure(self, integrity_id: str) -> Optional[StructuralIntegrity]:
        return self._structures.get(integrity_id)

    def damage_structure(self, integrity_id: str, damage: float,
                         impact_point: Optional[Tuple[float, float, float]] = None
                         ) -> Optional[CollapseMode]:
        """Apply damage to a structure and check for collapse."""
        structure = self._structures.get(integrity_id)
        if structure is None:
            return None
        return structure.apply_damage(damage, impact_point)

    def add_support(self, parent_id: str, child_id: str) -> None:
        """Add a support relationship between two structural elements."""
        parent = self._structures.get(parent_id)
        child = self._structures.get(child_id)
        if parent and child:
            parent.support_elements.append(child_id)
            child.supported_by.append(parent_id)

    def acquire_debris(self) -> Dict[str, Any]:
        """Acquire a debris object from the pool."""
        return self._debris_pool.acquire()

    def release_debris(self, debris_id: str) -> bool:
        """Release a debris object back to the pool."""
        return self._debris_pool.release(debris_id)

    def get_active_debris(self) -> List[Dict[str, Any]]:
        return self._destruction_physics.get_active_debris()

    def clear_all_debris(self) -> None:
        """Clear all active debris and return to pool."""
        self._destruction_physics.clear_debris()
        self._debris_pool.release_all()

    def update(self, delta_time: float) -> None:
        """Execute one frame of the destruction physics simulation."""
        self._destruction_physics.update(delta_time)

        for structure in self._structures.values():
            if structure.is_collapsed():
                structure.current_integrity = max(
                    0.0, structure.current_integrity - 0.5 * delta_time
                )

        self._frame_count += 1

    def get_stats(self) -> Dict[str, Any]:
        return {
            "fracture_pattern_count": len(self._fracture_patterns),
            "voronoi_fracture_count": len(self._voronoi_fractures),
            "structure_count": len(self._structures),
            "collapsed_structures": sum(
                1 for s in self._structures.values() if s.is_collapsed()
            ),
            "fracture_count": self._fracture_count,
            "total_debris_spawned": self._total_debris_spawned,
            "active_debris": self._destruction_physics._active_count,
            "settled_debris": self._destruction_physics._settled_count,
            "debris_pool": self._debris_pool.to_dict(),
            "destruction_physics": self._destruction_physics.to_dict(),
            "frame_count": self._frame_count,
        }


# ---------------------------------------------------------------------------
# Convenience Accessor
# ---------------------------------------------------------------------------

def get_destruction_physics_engine() -> DestructionPhysicsEngine:
    """Get the global DestructionPhysicsEngine singleton instance."""
    return DestructionPhysicsEngine()