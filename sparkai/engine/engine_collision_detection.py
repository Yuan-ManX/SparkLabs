"""
SparkLabs Engine - Collision Detection System

A full collision detection pipeline for the SparkLabs AI-native game
engine. Combines a dynamic bounding volume hierarchy (AABB tree) for
broadphase culling with precise narrowphase tests for the common
primitive shape pairs. Designed to feed a downstream physics solver
with stable contact manifolds and to drive gameplay collision events
(enter / stay / exit).

Architecture:
  CollisionDetectionSystem
    |-- BroadphaseAABBTree (dynamic BVH for pair generation)
    |-- NarrowphaseTests (sphere / box / capsule / convex hull pairs)
    |-- RayCaster (single + batch ray queries with layer filtering)
    |-- ShapeSweeper (continuous collision via time-of-impact)
    |-- ContactManager (persistent contacts for stable stacking)
    |-- CollisionFilter (layer/mask + group + custom callback)
    |-- DebugVisualizer (wireframe + contact point draw data)
    |-- StatisticsCollector (per-phase timing and throughput)

Shape Support: Box (AABB/OBB), Sphere, Capsule, Convex Hull (mesh),
Plane (infinite half-space).

Narrowphase Algorithms:
  - Sphere-Sphere: center distance check
  - Sphere-Box: closest point on box to sphere center
  - Box-Box: Separating Axis Theorem (SAT) over candidate axes
  - Capsule-Capsule: segment-segment shortest distance
  - Capsule-Sphere: point-segment shortest distance
  - Mesh-Mesh: GJK (Gilbert-Johnson-Keerthi) distance algorithm

The class is thread-safe; every public method acquires the internal
``threading.Lock``. AI-assisted helpers ``ai_optimize_broadphase`` and
``ai_predict_hotspots`` inspect scene structure and entity trajectories
to suggest broadphase parameters and flag regions likely to produce
collision spikes.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Capacity Constants
_MAX_COLLIDERS = 20000
_MAX_CONTACTS = 50000
_MAX_EVENTS = 4000
_REBALANCE_THRESHOLD = 8
_GJK_MAX_ITER = 32
_EPS = 1e-7

# Type aliases
Vec3 = Tuple[float, float, float]
Quat = Tuple[float, float, float, float]  # (x, y, z, w)


# Internal Helpers
def _uid() -> str:
    """Generate a unique identifier string."""
    return uuid.uuid4().hex


def _now_ts() -> float:
    """Return the current timestamp as a float (seconds since epoch)."""
    return time.time()


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a float value to the inclusive range [lo, hi]."""
    return max(lo, min(hi, value))


def _vadd(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vsub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vscale(v: Vec3, s: float) -> Vec3:
    return (v[0] * s, v[1] * s, v[2] * s)


def _vdot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vcross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _vlen(v: Vec3) -> float:
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])


def _vnorm(v: Vec3) -> Vec3:
    n = _vlen(v)
    return (0.0, 0.0, 0.0) if n < _EPS else (v[0]/n, v[1]/n, v[2]/n)


def _rotate_by_quat(v: Vec3, q: Quat) -> Vec3:
    """Rotate vector v by unit quaternion q = (x, y, z, w)."""
    t = _vscale(_vcross((q[0], q[1], q[2]), v), 2.0)
    return _vadd(_vadd(v, _vscale(t, q[3])), _vcross((q[0], q[1], q[2]), t))


def _aabb_combine(a_min: Vec3, a_max: Vec3, b_min: Vec3, b_max: Vec3) -> Tuple[Vec3, Vec3]:
    return (
        (min(a_min[0], b_min[0]), min(a_min[1], b_min[1]), min(a_min[2], b_min[2])),
        (max(a_max[0], b_max[0]), max(a_max[1], b_max[1]), max(a_max[2], b_max[2])),
    )


def _aabb_surface_area(minp: Vec3, maxp: Vec3) -> float:
    d = (maxp[0]-minp[0], maxp[1]-minp[1], maxp[2]-minp[2])
    return 2.0 * (d[0]*d[1] + d[1]*d[2] + d[2]*d[0])


def _aabb_overlap(a_min: Vec3, a_max: Vec3, b_min: Vec3, b_max: Vec3) -> bool:
    return (a_min[0] <= b_max[0] and a_max[0] >= b_min[0] and
            a_min[1] <= b_max[1] and a_max[1] >= b_min[1] and
            a_min[2] <= b_max[2] and a_max[2] >= b_min[2])


# Domain Enums
class ColliderShapeType(Enum):
    """Classification of a collider's primitive shape."""
    BOX = "box"
    SPHERE = "sphere"
    CAPSULE = "capsule"
    CONVEX_HULL = "convex_hull"
    PLANE = "plane"


class CollisionPhase(Enum):
    """Which stage of the pipeline produced a result."""
    BROADPHASE = "broadphase"
    NARROWPHASE = "narrowphase"


class CollisionEventType(Enum):
    """Lifecycle event for a collider pair across ticks."""
    ENTER = "enter"
    STAY = "stay"
    EXIT = "exit"


class BroadphaseMethod(Enum):
    """Active broadphase strategy for pair generation."""
    AABB_TREE = "aabb_tree"
    SWEEP_AND_PRUNE = "sweep_and_prune"
    UNIFORM_GRID = "uniform_grid"


# Shape Definitions
@dataclass
class BoxShape:
    """An axis-aligned or oriented box defined by half extents."""
    half_extents: Vec3 = (0.5, 0.5, 0.5)
    oriented: bool = False

    @property
    def shape_type(self) -> ColliderShapeType:
        return ColliderShapeType.BOX

    def to_dict(self) -> Dict[str, Any]:
        return {"shape_type": self.shape_type.value, "half_extents": list(self.half_extents), "oriented": self.oriented}


@dataclass
class SphereShape:
    """A sphere defined by a radius."""
    radius: float = 0.5

    @property
    def shape_type(self) -> ColliderShapeType:
        return ColliderShapeType.SPHERE

    def to_dict(self) -> Dict[str, Any]:
        return {"shape_type": self.shape_type.value, "radius": self.radius}


@dataclass
class CapsuleShape:
    """A capsule defined by a radius and a half height (segment half length)."""
    radius: float = 0.4
    half_height: float = 0.9
    axis: str = "y"  # local axis the segment lies along: x, y, or z

    @property
    def shape_type(self) -> ColliderShapeType:
        return ColliderShapeType.CAPSULE

    def to_dict(self) -> Dict[str, Any]:
        return {"shape_type": self.shape_type.value, "radius": self.radius, "half_height": self.half_height, "axis": self.axis}


@dataclass
class ConvexHullShape:
    """A convex mesh defined by local-space vertex positions."""
    vertices: List[Vec3] = field(default_factory=list)

    @property
    def shape_type(self) -> ColliderShapeType:
        return ColliderShapeType.CONVEX_HULL

    def to_dict(self) -> Dict[str, Any]:
        return {"shape_type": self.shape_type.value, "vertex_count": len(self.vertices), "vertices": [list(v) for v in self.vertices[:16]]}


@dataclass
class PlaneShape:
    """An infinite plane defined by a surface normal and an offset along it."""
    normal: Vec3 = (0.0, 1.0, 0.0)
    offset: float = 0.0

    @property
    def shape_type(self) -> ColliderShapeType:
        return ColliderShapeType.PLANE

    def to_dict(self) -> Dict[str, Any]:
        return {"shape_type": self.shape_type.value, "normal": list(self.normal), "offset": self.offset}


# Union of every supported concrete shape.
ColliderShape = Union[BoxShape, SphereShape, CapsuleShape, ConvexHullShape, PlaneShape]


def _coerce_shape(shape: Any) -> ColliderShape:
    """Coerce a string or dict into a concrete ColliderShape instance.

    Accepts:
      - existing ColliderShape instances (returned unchanged)
      - strings such as "box", "sphere", "capsule", "convex_hull", "plane"
      - dicts with a ``shape_type`` key and shape-specific fields
    Falls back to a unit SphereShape when coercion fails.
    """
    if hasattr(shape, "shape_type"):
        return shape
    if isinstance(shape, str):
        key = shape.strip().lower()
        mapping = {
            ColliderShapeType.BOX.value: BoxShape,
            ColliderShapeType.SPHERE.value: SphereShape,
            ColliderShapeType.CAPSULE.value: CapsuleShape,
            ColliderShapeType.CONVEX_HULL.value: ConvexHullShape,
            ColliderShapeType.PLANE.value: PlaneShape,
        }
        cls = mapping.get(key)
        if cls is None and key.upper() in ColliderShapeType.__members__:
            cls = mapping[ColliderShapeType[key.upper()].value]
        if cls is not None:
            try:
                return cls()
            except Exception:
                return SphereShape()
        return SphereShape()
    if isinstance(shape, dict):
        st = (shape.get("shape_type") or shape.get("type") or "sphere").lower()
        if st == ColliderShapeType.BOX.value:
            return BoxShape(half_extents=tuple(shape.get("half_extents", (0.5, 0.5, 0.5))))
        if st == ColliderShapeType.SPHERE.value:
            return SphereShape(radius=float(shape.get("radius", 0.5)))
        if st == ColliderShapeType.CAPSULE.value:
            return CapsuleShape(radius=float(shape.get("radius", 0.4)),
                                half_height=float(shape.get("half_height", 0.9)))
        if st == ColliderShapeType.PLANE.value:
            return PlaneShape(normal=tuple(shape.get("normal", (0.0, 1.0, 0.0))),
                              offset=float(shape.get("offset", 0.0)))
        if st == ColliderShapeType.CONVEX_HULL.value:
            return ConvexHullShape(vertices=shape.get("vertices", []))
    return SphereShape()


# Collider and Broadphase Node
@dataclass
class Collider:
    """A registered collision object bound to a game entity.

    Each collider carries a world transform (position, rotation, scale),
    a layer bitmask, a collision mask (which layers it collides with),
    trigger/static flags, and an optional group id. Colliders sharing a
    non-empty group do not generate collision pairs against each other.
    """
    collider_id: str = field(default_factory=_uid)
    entity_id: str = ""
    name: str = ""
    shape: ColliderShape = field(default_factory=lambda: SphereShape())
    position: Vec3 = (0.0, 0.0, 0.0)
    rotation: Quat = (0.0, 0.0, 0.0, 1.0)
    scale: Vec3 = (1.0, 1.0, 1.0)
    layer: int = 1
    mask: int = 0xFFFF
    is_trigger: bool = False
    is_static: bool = False
    group: int = 0
    restitution: float = 0.2
    friction: float = 0.6
    enabled: bool = True
    aabb_min: Vec3 = (0.0, 0.0, 0.0)
    aabb_max: Vec3 = (0.0, 0.0, 0.0)
    node_id: Optional[int] = None
    created_ts: float = field(default_factory=_now_ts)
    updated_ts: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        st = self.shape.shape_type.value if hasattr(self.shape, "shape_type") else "unknown"
        return {
            "collider_id": self.collider_id, "entity_id": self.entity_id, "name": self.name,
            "shape_type": st, "position": list(self.position), "rotation": list(self.rotation),
            "scale": list(self.scale), "layer": self.layer, "mask": self.mask,
            "is_trigger": self.is_trigger, "is_static": self.is_static, "group": self.group,
            "restitution": self.restitution, "friction": self.friction, "enabled": self.enabled,
        }


@dataclass
class AABBNode:
    """A node in the dynamic AABB tree (broadphase BVH).

    Leaf nodes carry a ``collider_id``; internal nodes have two children
    and a combined AABB. Height is used by the rebalancing heuristic.
    """
    node_id: int = -1
    aabb_min: Vec3 = (0.0, 0.0, 0.0)
    aabb_max: Vec3 = (0.0, 0.0, 0.0)
    parent: Optional[int] = None
    left: Optional[int] = None
    right: Optional[int] = None
    height: int = 0
    collider_id: Optional[str] = None

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


# Contact and Manifold
@dataclass
class ContactPoint:
    """A single contact point between two colliders."""
    point: Vec3 = (0.0, 0.0, 0.0)
    normal: Vec3 = (0.0, 1.0, 0.0)
    penetration: float = 0.0
    feature_id: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"point": list(self.point), "normal": list(self.normal), "penetration": self.penetration, "feature_id": self.feature_id}


@dataclass
class CollisionManifold:
    """Result of a narrowphase test between two colliders."""
    collider_a: str = ""
    collider_b: str = ""
    contacts: List[ContactPoint] = field(default_factory=list)
    normal: Vec3 = (0.0, 1.0, 0.0)
    penetration: float = 0.0
    separating_axis: Vec3 = (0.0, 1.0, 0.0)
    colliding: bool = False
    phase: CollisionPhase = CollisionPhase.NARROWPHASE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collider_a": self.collider_a, "collider_b": self.collider_b,
            "contacts": [c.to_dict() for c in self.contacts], "normal": list(self.normal),
            "penetration": self.penetration, "separating_axis": list(self.separating_axis),
            "colliding": self.colliding, "phase": self.phase.value,
        }


# Ray Cast and Sweep Results
@dataclass
class RaycastHit:
    """Result of a ray cast against the collider set."""
    point: Vec3 = (0.0, 0.0, 0.0)
    normal: Vec3 = (0.0, 1.0, 0.0)
    distance: float = math.inf
    collider_id: str = ""
    entity_id: str = ""
    hit: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"point": list(self.point), "normal": list(self.normal), "distance": self.distance,
                "collider_id": self.collider_id, "entity_id": self.entity_id, "hit": self.hit}


@dataclass
class SweepResult:
    """Result of a shape sweep (continuous collision detection)."""
    hit: bool = False
    time_of_impact: float = 1.0
    contact_point: Vec3 = (0.0, 0.0, 0.0)
    normal: Vec3 = (0.0, 1.0, 0.0)
    collider_id: str = ""
    entity_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"hit": self.hit, "time_of_impact": self.time_of_impact, "contact_point": list(self.contact_point),
                "normal": list(self.normal), "collider_id": self.collider_id, "entity_id": self.entity_id}


# Pairs, Events and Constraints
@dataclass
class CollisionPair:
    """A candidate or confirmed collision pair for a single tick."""
    collider_a: str = ""
    collider_b: str = ""
    entity_a: str = ""
    entity_b: str = ""
    manifold: Optional[CollisionManifold] = None
    colliding: bool = False
    tick: int = 0

    def key(self) -> Tuple[str, str]:
        a, b = self.collider_a, self.collider_b
        return (a, b) if a <= b else (b, a)

    def to_dict(self) -> Dict[str, Any]:
        return {"collider_a": self.collider_a, "collider_b": self.collider_b, "entity_a": self.entity_a,
                "entity_b": self.entity_b, "colliding": self.colliding, "tick": self.tick,
                "manifold": self.manifold.to_dict() if self.manifold else None}


@dataclass
class CollisionEvent:
    """A lifecycle event (enter / stay / exit) for a collider pair."""
    event_type: CollisionEventType = CollisionEventType.STAY
    collider_a: str = ""
    collider_b: str = ""
    entity_a: str = ""
    entity_b: str = ""
    manifold: Optional[CollisionManifold] = None
    tick: int = 0
    timestamp: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {"event_type": self.event_type.value, "collider_a": self.collider_a, "collider_b": self.collider_b,
                "entity_a": self.entity_a, "entity_b": self.entity_b, "tick": self.tick,
                "timestamp": self.timestamp, "manifold": self.manifold.to_dict() if self.manifold else None}


@dataclass
class ContactConstraint:
    """A solver-ready contact constraint produced from a manifold."""
    constraint_id: str = field(default_factory=_uid)
    collider_a: str = ""
    collider_b: str = ""
    contact_point: Vec3 = (0.0, 0.0, 0.0)
    normal: Vec3 = (0.0, 1.0, 0.0)
    penetration: float = 0.0
    restitution: float = 0.2
    friction: float = 0.6
    persistent: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"constraint_id": self.constraint_id, "collider_a": self.collider_a, "collider_b": self.collider_b,
                "contact_point": list(self.contact_point), "normal": list(self.normal), "penetration": self.penetration,
                "restitution": self.restitution, "friction": self.friction, "persistent": self.persistent}


# Layer, Debug and Statistics
@dataclass
class CollisionLayer:
    """A named collision layer with a bit position and description."""
    layer_id: int = 0
    name: str = "default"
    bit: int = 1
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"layer_id": self.layer_id, "name": self.name, "bit": self.bit, "description": self.description}


@dataclass
class DebugDrawData:
    """Draw data intended for a debug renderer."""
    wireframes: List[Dict[str, Any]] = field(default_factory=list)
    aabbs: List[Dict[str, Any]] = field(default_factory=list)
    contact_points: List[Dict[str, Any]] = field(default_factory=list)
    contact_normals: List[Dict[str, Any]] = field(default_factory=list)
    ray_debug: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"wireframes": self.wireframes, "aabbs": self.aabbs, "contact_points": self.contact_points,
                "contact_normals": self.contact_normals, "ray_debug": self.ray_debug}


@dataclass
class CollisionStatistics:
    """Throughput and timing statistics for the pipeline."""
    tick_count: int = 0
    broadphase_time_ms: float = 0.0
    narrowphase_time_ms: float = 0.0
    total_time_ms: float = 0.0
    pair_count: int = 0
    contact_count: int = 0
    persistent_count: int = 0
    event_count: int = 0
    ray_queries: int = 0
    sweep_queries: int = 0
    avg_pair_count: float = 0.0
    avg_narrowphase_ms: float = 0.0
    queries_per_second: float = 0.0
    last_reset_ts: float = field(default_factory=_now_ts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick_count": self.tick_count, "broadphase_time_ms": round(self.broadphase_time_ms, 4),
            "narrowphase_time_ms": round(self.narrowphase_time_ms, 4), "total_time_ms": round(self.total_time_ms, 4),
            "pair_count": self.pair_count, "contact_count": self.contact_count, "persistent_count": self.persistent_count,
            "event_count": self.event_count, "ray_queries": self.ray_queries, "sweep_queries": self.sweep_queries,
            "avg_pair_count": round(self.avg_pair_count, 4), "avg_narrowphase_ms": round(self.avg_narrowphase_ms, 4),
            "queries_per_second": round(self.queries_per_second, 4),
        }


# Collision Detection System
class CollisionDetectionSystem:
    """Full broadphase + narrowphase collision detection pipeline.

    Holds the collider registry, the dynamic AABB tree, the active
    collision pairs, persistent contacts, and per-tick events. All
    public methods are guarded by an internal ``threading.Lock`` so the
    system can be safely polled from gameplay, physics, and AI threads.
    """

    MAX_LAYERS: int = 32
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized = False
        self._colliders: Dict[str, Collider] = {}
        self._nodes: Dict[int, AABBNode] = {}
        self._collider_to_node: Dict[str, int] = {}
        self._next_node_id = 1
        self._root_node: Optional[int] = None
        self._collision_matrix: Dict[int, int] = {}
        self._layers: Dict[int, CollisionLayer] = {}
        self._filter_callback: Optional[Callable[[Collider, Collider], bool]] = None
        self._pairs: List[CollisionPair] = []
        self._pair_set: set = set()
        self._events: List[CollisionEvent] = []
        self._persistent: Dict[Tuple[str, str], CollisionManifold] = {}
        self._prev_colliding: set = set()
        self._statistics = CollisionStatistics()
        self._ray_history: List[Dict[str, Any]] = []
        self._broadphase_method = BroadphaseMethod.AABB_TREE
        self._tick = 0
        self._auto_rebalance = True
        self._max_tree_depth_seen = 0
        self._seed_default_layers()

    # Initialization and lifecycle
    def _seed_default_layers(self) -> None:
        defaults = [
            (0, "default", 1 << 0, "Default layer"),
            (1, "player", 1 << 1, "Player character"),
            (2, "enemy", 1 << 2, "Hostile NPCs"),
            (3, "projectile", 1 << 3, "Projectiles"),
            (4, "terrain", 1 << 4, "Ground, walls, platforms"),
            (5, "trigger", 1 << 5, "Trigger volumes"),
            (6, "vehicle", 1 << 6, "Driveable vehicles"),
            (7, "pickup", 1 << 7, "Collectible items"),
        ]
        for layer_id, name, bit, desc in defaults:
            self._layers[layer_id] = CollisionLayer(layer_id=layer_id, name=name, bit=bit, description=desc)
        for i in range(8):
            self._collision_matrix[i] = 0xFFFFFFFF

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Initialize the system and seed sample colliders.

        Accepts an optional config dict with keys such as
        ``auto_rebalance``, ``broadphase_method`` and ``seed_sample``.
        Returns a status dict describing the post-initialization state.
        """
        with self._lock:
            config = config or {}
            self._auto_rebalance = bool(config.get("auto_rebalance", True))
            method = config.get("broadphase_method", "aabb_tree")
            try:
                self._broadphase_method = BroadphaseMethod(method)
            except ValueError:
                self._broadphase_method = BroadphaseMethod.AABB_TREE
            if config.get("seed_sample", True):
                self._seed_sample_colliders()
            self._initialized = True
            return self.get_status()

    def _seed_sample_colliders(self) -> None:
        """Seed the registry with a representative sample scene."""
        self._register_internal(Collider(
            collider_id="collider_player", entity_id="entity_player", name="player",
            shape=CapsuleShape(radius=0.4, half_height=0.9, axis="y"),
            position=(0.0, 1.0, 0.0), layer=1 << 1, mask=0xFFFFFFFF))
        self._register_internal(Collider(
            collider_id="collider_terrain", entity_id="entity_terrain", name="terrain",
            shape=BoxShape(half_extents=(50.0, 0.5, 50.0)),
            position=(0.0, 0.0, 0.0), layer=1 << 4, mask=0, is_static=True))
        for i in range(3):
            angle = i * 2.0944  # ~120 degrees apart
            self._register_internal(Collider(
                collider_id=f"collider_enemy_{i}", entity_id=f"entity_enemy_{i}", name=f"enemy_{i}",
                shape=SphereShape(radius=0.5),
                position=(math.cos(angle) * 3.0, 0.5, math.sin(angle) * 3.0),
                layer=1 << 2, mask=0xFFFFFFFF))
        for name, pos, half in [
            ("north", (0.0, 1.0, -10.0), (10.0, 1.0, 0.5)),
            ("south", (0.0, 1.0, 10.0), (10.0, 1.0, 0.5)),
            ("east", (10.0, 1.0, 0.0), (0.5, 1.0, 10.0)),
            ("west", (-10.0, 1.0, 0.0), (0.5, 1.0, 10.0)),
        ]:
            self._register_internal(Collider(
                collider_id=f"collider_wall_{name}", entity_id=f"entity_wall_{name}", name=f"wall_{name}",
                shape=BoxShape(half_extents=half), position=pos, layer=1 << 4, mask=0, is_static=True))
        self._register_internal(Collider(
            collider_id="collider_trigger_spawn", entity_id="entity_trigger_spawn", name="trigger_spawn",
            shape=BoxShape(half_extents=(2.0, 0.2, 2.0)), position=(0.0, 0.1, 0.0),
            layer=1 << 5, mask=1 << 1, is_trigger=True, is_static=True))

    def reset(self) -> Dict[str, Any]:
        """Clear every store and re-seed default layers and sample scene."""
        with self._lock:
            self._colliders.clear()
            self._nodes.clear()
            self._collider_to_node.clear()
            self._next_node_id = 1
            self._root_node = None
            self._pairs.clear()
            self._pair_set.clear()
            self._events.clear()
            self._persistent.clear()
            self._prev_colliding.clear()
            self._ray_history.clear()
            self._tick = 0
            self._statistics = CollisionStatistics()
            self._seed_default_layers()
            self._seed_sample_colliders()
            self._initialized = True
            return self.get_status()

    # Collider registration and mutation
    def _register_internal(self, collider: Collider) -> Collider:
        if len(self._colliders) >= _MAX_COLLIDERS:
            raise RuntimeError("Collider capacity reached")
        self._compute_world_aabb(collider)
        self._colliders[collider.collider_id] = collider
        self._insert_into_tree(collider)
        collider.updated_ts = _now_ts()
        return collider

    def register_collider(self, entity_id: str, shape: ColliderShape,
                          position: Vec3 = (0.0, 0.0, 0.0), rotation: Quat = (0.0, 0.0, 0.0, 1.0),
                          scale: Vec3 = (1.0, 1.0, 1.0), layer: int = 1, mask: int = 0xFFFF,
                          is_trigger: bool = False, is_static: bool = False, group: int = 0,
                          name: str = "", restitution: float = 0.2, friction: float = 0.6) -> Collider:
        """Register a new collider and insert it into the broadphase tree."""
        shape = _coerce_shape(shape)
        with self._lock:
            collider = Collider(
                entity_id=entity_id, name=name or entity_id, shape=shape, position=position,
                rotation=rotation, scale=scale, layer=layer, mask=mask, is_trigger=is_trigger,
                is_static=is_static, group=group, restitution=_clamp(restitution, 0.0, 1.0),
                friction=_clamp(friction, 0.0, 2.0))
            return self._register_internal(collider)

    def remove_collider(self, collider_id: str) -> bool:
        """Remove a collider from the registry and the broadphase tree."""
        with self._lock:
            collider = self._colliders.get(collider_id)
            if collider is None:
                return False
            self._remove_from_tree(collider)
            del self._colliders[collider_id]
            stale = [k for k in self._persistent if k[0] == collider_id or k[1] == collider_id]
            for k in stale:
                del self._persistent[k]
            return True

    def get_collider(self, collider_id: str) -> Optional[Collider]:
        """Return a collider by id, or None if not registered."""
        with self._lock:
            return self._colliders.get(collider_id)

    def update_collider(self, collider_id: str, position: Optional[Vec3] = None,
                        rotation: Optional[Quat] = None, scale: Optional[Vec3] = None,
                        shape: Optional[ColliderShape] = None) -> Optional[Collider]:
        """Update one or more transform / shape fields and refresh the AABB."""
        if shape is not None:
            shape = _coerce_shape(shape)
        with self._lock:
            collider = self._colliders.get(collider_id)
            if collider is None:
                return None
            if position is not None:
                collider.position = position
            if rotation is not None:
                collider.rotation = rotation
            if scale is not None:
                collider.scale = scale
            if shape is not None:
                collider.shape = shape
            collider.updated_ts = _now_ts()
            self._compute_world_aabb(collider)
            self._update_in_tree(collider)
            return collider

    def move_collider(self, collider_id: str, delta: Vec3) -> Optional[Collider]:
        """Translate a collider by a delta vector and refresh its AABB."""
        with self._lock:
            collider = self._colliders.get(collider_id)
            if collider is None:
                return None
            collider.position = _vadd(collider.position, delta)
            collider.updated_ts = _now_ts()
            self._compute_world_aabb(collider)
            self._update_in_tree(collider)
            return collider

    def set_collider_layer(self, collider_id: str, layer: int) -> Optional[Collider]:
        """Set the collision layer bitmask of a collider."""
        with self._lock:
            collider = self._colliders.get(collider_id)
            if collider is None:
                return None
            collider.layer = layer
            collider.updated_ts = _now_ts()
            return collider

    def set_collider_mask(self, collider_id: str, mask: int) -> Optional[Collider]:
        """Set the collision mask (which layers this collider tests against)."""
        with self._lock:
            collider = self._colliders.get(collider_id)
            if collider is None:
                return None
            collider.mask = mask
            collider.updated_ts = _now_ts()
            return collider

    def set_collider_trigger(self, collider_id: str, is_trigger: bool) -> Optional[Collider]:
        """Toggle whether a collider is a non-physical trigger volume."""
        with self._lock:
            collider = self._colliders.get(collider_id)
            if collider is None:
                return None
            collider.is_trigger = is_trigger
            collider.updated_ts = _now_ts()
            return collider

    def set_collider_static(self, collider_id: str, is_static: bool) -> Optional[Collider]:
        """Toggle whether a collider is treated as static (never moved)."""
        with self._lock:
            collider = self._colliders.get(collider_id)
            if collider is None:
                return None
            collider.is_static = is_static
            collider.updated_ts = _now_ts()
            return collider

    def list_colliders(self) -> List[Collider]:
        """Return a shallow list of every registered collider."""
        with self._lock:
            return list(self._colliders.values())

    def get_colliders_in_layer(self, layer: int) -> List[Collider]:
        """Return every collider whose layer bitmask intersects ``layer``."""
        with self._lock:
            return [c for c in self._colliders.values() if (c.layer & layer) != 0 and c.enabled]

    # World AABB computation
    def _compute_world_aabb(self, collider: Collider) -> None:
        """Compute and cache the world-space AABB for a collider."""
        shape = collider.shape
        pos = collider.position
        scale = collider.scale
        if isinstance(shape, SphereShape):
            r = shape.radius * max(scale)
            collider.aabb_min = (pos[0]-r, pos[1]-r, pos[2]-r)
            collider.aabb_max = (pos[0]+r, pos[1]+r, pos[2]+r)
        elif isinstance(shape, BoxShape):
            he = (shape.half_extents[0]*scale[0], shape.half_extents[1]*scale[1], shape.half_extents[2]*scale[2])
            if shape.oriented:
                corners = []
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        for sz in (-1, 1):
                            local = (he[0]*sx, he[1]*sy, he[2]*sz)
                            corners.append(_vadd(pos, _rotate_by_quat(local, collider.rotation)))
                xs = [c[0] for c in corners]; ys = [c[1] for c in corners]; zs = [c[2] for c in corners]
                collider.aabb_min = (min(xs), min(ys), min(zs))
                collider.aabb_max = (max(xs), max(ys), max(zs))
            else:
                collider.aabb_min = (pos[0]-he[0], pos[1]-he[1], pos[2]-he[2])
                collider.aabb_max = (pos[0]+he[0], pos[1]+he[1], pos[2]+he[2])
        elif isinstance(shape, CapsuleShape):
            r = shape.radius * max(scale)
            hh = shape.half_height * (scale[1] if shape.axis == "y" else max(scale))
            collider.aabb_min = (pos[0]-r, pos[1]-hh-r, pos[2]-r)
            collider.aabb_max = (pos[0]+r, pos[1]+hh+r, pos[2]+r)
        elif isinstance(shape, ConvexHullShape):
            if not shape.vertices:
                collider.aabb_min = pos; collider.aabb_max = pos
            else:
                transformed = [_vadd(pos, _rotate_by_quat(v, collider.rotation)) for v in shape.vertices]
                xs = [c[0] for c in transformed]; ys = [c[1] for c in transformed]; zs = [c[2] for c in transformed]
                collider.aabb_min = (min(xs), min(ys), min(zs))
                collider.aabb_max = (max(xs), max(ys), max(zs))
        elif isinstance(shape, PlaneShape):
            n = shape.normal; big = 1.0e6
            center = _vadd(pos, _vscale(n, shape.offset))
            collider.aabb_min = tuple(center[i] - big if abs(n[i]) < 0.5 else center[i] - 1.0 for i in range(3))
            collider.aabb_max = tuple(center[i] + big if abs(n[i]) < 0.5 else center[i] + 1.0 for i in range(3))
        else:
            collider.aabb_min = (pos[0]-0.5, pos[1]-0.5, pos[2]-0.5)
            collider.aabb_max = (pos[0]+0.5, pos[1]+0.5, pos[2]+0.5)

    # Broadphase AABB tree
    def _alloc_node(self, aabb_min: Vec3, aabb_max: Vec3) -> int:
        node_id = self._next_node_id
        self._next_node_id += 1
        self._nodes[node_id] = AABBNode(node_id=node_id, aabb_min=aabb_min, aabb_max=aabb_max)
        return node_id

    def _free_node(self, node_id: int) -> None:
        self._nodes.pop(node_id, None)

    def _insert_into_tree(self, collider: Collider) -> None:
        if collider.node_id is not None and collider.node_id in self._nodes:
            self._update_in_tree(collider); return
        leaf = self._alloc_node(collider.aabb_min, collider.aabb_max)
        leaf_node = self._nodes[leaf]
        leaf_node.collider_id = collider.collider_id
        collider.node_id = leaf
        self._collider_to_node[collider.collider_id] = leaf
        self._insert_leaf(leaf)

    def _insert_leaf(self, leaf: int) -> None:
        if self._root_node is None:
            self._root_node = leaf
            self._nodes[leaf].parent = None
            return
        leaf_node = self._nodes[leaf]
        lb = (leaf_node.aabb_min, leaf_node.aabb_max)
        current = self._root_node
        while True:
            node = self._nodes[current]
            if node.is_leaf:
                break
            left = self._nodes[node.left]; right = self._nodes[node.right]
            combined = _aabb_combine(lb[0], lb[1], node.aabb_min, node.aabb_max)
            cost = 2.0 * _aabb_surface_area(combined[0], combined[1])
            inheritance = cost - _aabb_surface_area(node.aabb_min, node.aabb_max)
            lc = _aabb_combine(lb[0], lb[1], left.aabb_min, left.aabb_max)
            left_cost = inheritance + (1.0 if left.is_leaf else -1.0) * _aabb_surface_area(lc[0], lc[1])
            rc = _aabb_combine(lb[0], lb[1], right.aabb_min, right.aabb_max)
            right_cost = inheritance + (1.0 if right.is_leaf else -1.0) * _aabb_surface_area(rc[0], rc[1])
            if cost < left_cost and cost < right_cost:
                break
            current = node.left if left_cost < right_cost else node.right
        sibling = current
        new_parent = self._alloc_node(*_aabb_combine(lb[0], lb[1], self._nodes[sibling].aabb_min, self._nodes[sibling].aabb_max))
        npn = self._nodes[new_parent]; sn = self._nodes[sibling]
        parent = sn.parent
        npn.parent = parent; npn.left = sibling; npn.right = leaf; npn.height = sn.height + 1
        sn.parent = new_parent; leaf_node.parent = new_parent
        if parent is None:
            self._root_node = new_parent
        else:
            pn = self._nodes[parent]
            if pn.left == sibling:
                pn.left = new_parent
            else:
                pn.right = new_parent
        self._sync_upward(new_parent)

    def _sync_upward(self, node_id: Optional[int]) -> None:
        current = node_id
        while current is not None:
            node = self._nodes[current]
            left = self._nodes[node.left]; right = self._nodes[node.right]
            node.aabb_min, node.aabb_max = _aabb_combine(left.aabb_min, left.aabb_max, right.aabb_min, right.aabb_max)
            node.height = 1 + max(left.height, right.height)
            self._max_tree_depth_seen = max(self._max_tree_depth_seen, node.height)
            current = node.parent

    def _remove_from_tree(self, collider: Collider) -> None:
        node_id = collider.node_id
        if node_id is None or node_id not in self._nodes:
            return
        self._remove_leaf(node_id)
        self._free_node(node_id)
        collider.node_id = None
        self._collider_to_node.pop(collider.collider_id, None)

    def _remove_leaf(self, leaf: int) -> None:
        if leaf == self._root_node:
            self._root_node = None; return
        leaf_node = self._nodes[leaf]
        parent = leaf_node.parent
        if parent is None:
            self._root_node = None; return
        pn = self._nodes[parent]
        sibling = pn.right if pn.left == leaf else pn.left
        grandparent = pn.parent
        sn = self._nodes[sibling]
        sn.parent = grandparent
        if grandparent is None:
            self._root_node = sibling
        else:
            gpn = self._nodes[grandparent]
            if gpn.left == parent:
                gpn.left = sibling
            else:
                gpn.right = sibling
        self._sync_upward(grandparent)
        self._free_node(parent)

    def _update_in_tree(self, collider: Collider) -> None:
        node_id = collider.node_id
        if node_id is None or node_id not in self._nodes:
            self._insert_into_tree(collider); return
        self._remove_leaf(node_id)
        self._nodes[node_id] = AABBNode(node_id=node_id, aabb_min=collider.aabb_min,
                                        aabb_max=collider.aabb_max, collider_id=collider.collider_id, height=0)
        self._insert_leaf(node_id)

    def add_to_broadphase(self, collider_id: str) -> bool:
        """Insert a registered collider into the broadphase tree."""
        with self._lock:
            collider = self._colliders.get(collider_id)
            if collider is None:
                return False
            self._insert_into_tree(collider)
            return True

    def update_in_broadphase(self, collider_id: str) -> bool:
        """Refresh a collider's broadphase node after a transform change."""
        with self._lock:
            collider = self._colliders.get(collider_id)
            if collider is None:
                return False
            self._compute_world_aabb(collider)
            self._update_in_tree(collider)
            return True

    def remove_from_broadphase(self, collider_id: str) -> bool:
        """Remove a collider from the broadphase tree without unregistering it."""
        with self._lock:
            collider = self._colliders.get(collider_id)
            if collider is None or collider.node_id is None:
                return False
            self._remove_from_tree(collider)
            return True

    def query_aabb(self, aabb_min: Vec3, aabb_max: Vec3, layer_mask: int = 0xFFFF) -> List[str]:
        """Return collider ids whose AABBs overlap the query box."""
        with self._lock:
            results: List[str] = []
            if self._root_node is None:
                return results
            stack = [self._root_node]
            while stack:
                node = self._nodes.get(stack.pop())
                if node is None:
                    continue
                if not _aabb_overlap(node.aabb_min, node.aabb_max, aabb_min, aabb_max):
                    continue
                if node.is_leaf and node.collider_id is not None:
                    c = self._colliders.get(node.collider_id)
                    if c is not None and c.enabled and (c.layer & layer_mask) != 0:
                        results.append(node.collider_id)
                else:
                    if node.left is not None:
                        stack.append(node.left)
                    if node.right is not None:
                        stack.append(node.right)
            return results

    def rebalance_tree(self) -> Dict[str, Any]:
        """Rebalance the broadphase tree and report depth statistics."""
        with self._lock:
            before = self._tree_depth()
            leaves = list(self._collider_to_node.keys())
            self._nodes.clear()
            self._collider_to_node.clear()
            self._next_node_id = 1
            self._root_node = None
            for cid in leaves:
                c = self._colliders.get(cid)
                if c is not None:
                    c.node_id = None
                    self._insert_into_tree(c)
            after = self._tree_depth()
            return {"rebalanced": True, "depth_before": before, "depth_after": after,
                    "node_count": len(self._nodes), "leaf_count": len(self._collider_to_node)}

    def _tree_depth(self) -> int:
        if self._root_node is None:
            return 0
        return self._nodes[self._root_node].height

    def _query_node(self, node_id: int, qmin: Vec3, qmax: Vec3) -> List[str]:
        results: List[str] = []
        stack = [node_id]
        while stack:
            node = self._nodes.get(stack.pop())
            if node is None:
                continue
            if not _aabb_overlap(node.aabb_min, node.aabb_max, qmin, qmax):
                continue
            if node.is_leaf and node.collider_id is not None:
                results.append(node.collider_id)
            else:
                if node.left is not None:
                    stack.append(node.left)
                if node.right is not None:
                    stack.append(node.right)
        return results

    def _broadphase_pairs(self) -> List[Tuple[str, str]]:
        """Generate candidate collider pairs by traversing the AABB tree."""
        pairs: List[Tuple[str, str]] = []
        if self._root_node is None:
            return pairs
        seen: set = set()
        for collider_id, node_id in self._collider_to_node.items():
            node = self._nodes.get(node_id)
            if node is None:
                continue
            collider = self._colliders.get(collider_id)
            if collider is None or not collider.enabled:
                continue
            for other_id in self._query_node(self._root_node, node.aabb_min, node.aabb_max):
                if other_id == collider_id:
                    continue
                other = self._colliders.get(other_id)
                if other is None or not other.enabled:
                    continue
                if not self._can_collide(collider, other):
                    continue
                key = (collider_id, other_id) if collider_id <= other_id else (other_id, collider_id)
                if key in seen:
                    continue
                seen.add(key)
                pairs.append(key)
        return pairs

    # Collision filtering
    def _can_collide(self, a: Collider, b: Collider) -> bool:
        """Apply layer/mask, group, and custom filter checks."""
        if a.is_trigger and b.is_trigger:
            return False
        if (a.layer & b.mask) == 0 and (b.layer & a.mask) == 0:
            return False
        if a.group != 0 and a.group == b.group:
            return False
        if not self._matrix_allows(a.layer, b.layer):
            return False
        if self._filter_callback is not None:
            try:
                if not self._filter_callback(a, b):
                    return False
            except Exception:
                return False
        return True

    def _matrix_allows(self, layer_a: int, layer_b: int) -> bool:
        return (self._collision_matrix.get(layer_a, 0) & layer_b) != 0

    def set_collision_matrix(self, layer_a: int, layer_b: int, collide: bool = True) -> None:
        """Configure whether two layer bitmasks may collide."""
        with self._lock:
            row = self._collision_matrix.get(layer_a, 0)
            if collide:
                row |= layer_b
            else:
                row &= ~layer_b
            self._collision_matrix[layer_a] = row

    def get_collision_matrix(self) -> Dict[int, int]:
        """Return a copy of the full collision matrix."""
        with self._lock:
            return dict(self._collision_matrix)

    def set_custom_filter(self, callback: Optional[Callable[[Collider, Collider], bool]]) -> None:
        """Install a custom filter callback returning True to allow a pair."""
        with self._lock:
            self._filter_callback = callback

    def check_pair(self, collider_id_a: str, collider_id_b: str) -> CollisionManifold:
        """Run a full narrowphase test between two registered colliders."""
        with self._lock:
            a = self._colliders.get(collider_id_a)
            b = self._colliders.get(collider_id_b)
            if a is None or b is None:
                return CollisionManifold(collider_a=collider_id_a, collider_b=collider_id_b, colliding=False)
            return self._narrowphase(a, b)

    # Narrowphase dispatch
    def _narrowphase(self, a: Collider, b: Collider) -> CollisionManifold:
        """Dispatch to the correct narrowphase test by shape pair."""
        ta = a.shape.shape_type; tb = b.shape.shape_type
        key = (ta, tb) if ta.value <= tb.value else (tb, ta)
        if key == (ColliderShapeType.SPHERE, ColliderShapeType.SPHERE):
            mf = self._sphere_sphere(a, b)
        elif key == (ColliderShapeType.SPHERE, ColliderShapeType.BOX):
            mf = self._sphere_box(a, b) if ta == ColliderShapeType.SPHERE else self._sphere_box(b, a)
            if ta == ColliderShapeType.BOX:
                mf.normal = _vscale(mf.normal, -1.0)
        elif key == (ColliderShapeType.BOX, ColliderShapeType.BOX):
            mf = self._box_box(a, b)
        elif key == (ColliderShapeType.CAPSULE, ColliderShapeType.CAPSULE):
            mf = self._capsule_capsule(a, b)
        elif key == (ColliderShapeType.CAPSULE, ColliderShapeType.SPHERE):
            mf = self._capsule_sphere(a, b) if ta == ColliderShapeType.CAPSULE else self._capsule_sphere(b, a)
            if ta == ColliderShapeType.SPHERE:
                mf.normal = _vscale(mf.normal, -1.0)
        elif key == (ColliderShapeType.CAPSULE, ColliderShapeType.BOX):
            mf = self._capsule_box(a, b) if ta == ColliderShapeType.CAPSULE else self._capsule_box(b, a)
            if ta == ColliderShapeType.BOX:
                mf.normal = _vscale(mf.normal, -1.0)
        elif key == (ColliderShapeType.CONVEX_HULL, ColliderShapeType.CONVEX_HULL):
            mf = self._gjk_narrowphase(a, b)
        elif key == (ColliderShapeType.PLANE, ColliderShapeType.SPHERE):
            mf = self._plane_sphere(a, b) if ta == ColliderShapeType.PLANE else self._plane_sphere(b, a)
            if ta == ColliderShapeType.SPHERE:
                mf.normal = _vscale(mf.normal, -1.0)
        else:
            mf = CollisionManifold(collider_a=a.collider_id, collider_b=b.collider_id,
                                   colliding=_aabb_overlap(a.aabb_min, a.aabb_max, b.aabb_min, b.aabb_max))
        mf.collider_a = a.collider_id; mf.collider_b = b.collider_id
        mf.phase = CollisionPhase.NARROWPHASE
        return mf

    def _sphere_sphere(self, a: Collider, b: Collider) -> CollisionManifold:
        sa: SphereShape = a.shape  # type: ignore
        sb: SphereShape = b.shape  # type: ignore
        delta = _vsub(b.position, a.position)
        dist = _vlen(delta)
        radius_sum = sa.radius + sb.radius
        if dist >= radius_sum:
            return CollisionManifold(colliding=False)
        normal = _vnorm(delta) if dist > _EPS else (0.0, 1.0, 0.0)
        penetration = radius_sum - dist
        point = _vadd(a.position, _vscale(normal, sa.radius))
        return CollisionManifold(contacts=[ContactPoint(point=point, normal=normal, penetration=penetration)],
                                 normal=normal, penetration=penetration, separating_axis=normal, colliding=True)

    def _closest_point_on_aabb(self, point: Vec3, bmin: Vec3, bmax: Vec3) -> Vec3:
        return (_clamp(point[0], bmin[0], bmax[0]), _clamp(point[1], bmin[1], bmax[1]), _clamp(point[2], bmin[2], bmax[2]))

    def _sphere_box(self, sphere: Collider, box: Collider) -> CollisionManifold:
        s: SphereShape = sphere.shape  # type: ignore
        closest = self._closest_point_on_aabb(sphere.position, box.aabb_min, box.aabb_max)
        delta = _vsub(sphere.position, closest)
        dist = _vlen(delta)
        if dist >= s.radius:
            return CollisionManifold(colliding=False)
        normal = _vnorm(delta) if dist > _EPS else (0.0, 1.0, 0.0)
        penetration = s.radius - dist
        return CollisionManifold(contacts=[ContactPoint(point=closest, normal=normal, penetration=penetration)],
                                 normal=normal, penetration=penetration, separating_axis=normal, colliding=True)

    def _box_box(self, a: Collider, b: Collider) -> CollisionManifold:
        """Separating Axis Theorem for two axis-aligned boxes."""
        a_min, a_max = a.aabb_min, a.aabb_max
        b_min, b_max = b.aabb_min, b.aabb_max
        if not _aabb_overlap(a_min, a_max, b_min, b_max):
            return CollisionManifold(colliding=False)
        overlaps = []
        for i in range(3):
            ov = min(a_max[i], b_max[i]) - max(a_min[i], b_min[i])
            if ov <= 0:
                return CollisionManifold(colliding=False)
            overlaps.append(ov)
        axis_index = overlaps.index(min(overlaps))
        penetration = overlaps[axis_index]
        a_center = tuple((a_min[i] + a_max[i]) * 0.5 for i in range(3))
        b_center = tuple((b_min[i] + b_max[i]) * 0.5 for i in range(3))
        delta = _vsub(b_center, a_center)
        normal = [0.0, 0.0, 0.0]
        normal[axis_index] = 1.0 if delta[axis_index] >= 0 else -1.0
        nt = (normal[0], normal[1], normal[2])
        cp = tuple((a_center[i] + b_center[i]) * 0.5 for i in range(3))
        return CollisionManifold(contacts=[ContactPoint(point=cp, normal=nt, penetration=penetration)],
                                 normal=nt, penetration=penetration, separating_axis=nt, colliding=True)

    def _capsule_endpoints(self, c: Collider) -> Tuple[Vec3, Vec3]:
        cap: CapsuleShape = c.shape  # type: ignore
        hh = cap.half_height
        if cap.axis == "x":
            la, lb = (-hh, 0.0, 0.0), (hh, 0.0, 0.0)
        elif cap.axis == "z":
            la, lb = (0.0, 0.0, -hh), (0.0, 0.0, hh)
        else:
            la, lb = (0.0, -hh, 0.0), (0.0, hh, 0.0)
        return (_vadd(c.position, _rotate_by_quat(la, c.rotation)),
                _vadd(c.position, _rotate_by_quat(lb, c.rotation)))

    def _segment_segment(self, p1: Vec3, p2: Vec3, p3: Vec3, p4: Vec3) -> Tuple[float, Vec3, Vec3]:
        """Return (distance, closest_on_a, closest_on_b) for two segments."""
        d1 = _vsub(p2, p1); d2 = _vsub(p4, p3); r = _vsub(p1, p3)
        a = _vdot(d1, d1); e = _vdot(d2, d2); f = _vdot(d2, r)
        if a <= _EPS and e <= _EPS:
            return _vlen(_vsub(p1, p3)), p1, p3
        if a <= _EPS:
            s = 0.0; t = _clamp(f / e, 0.0, 1.0)
        else:
            c = _vdot(d1, r)
            if e <= _EPS:
                t = 0.0; s = _clamp(-c / a, 0.0, 1.0)
            else:
                b = _vdot(d1, d2); denom = a * e - b * b
                s = _clamp((b * f - c * e) / denom, 0.0, 1.0) if denom != 0.0 else 0.0
                t = (b * s + f) / e
                if t < 0.0:
                    t = 0.0; s = _clamp(-c / a, 0.0, 1.0)
                elif t > 1.0:
                    t = 1.0; s = _clamp((b - c) / a, 0.0, 1.0)
        ca = _vadd(p1, _vscale(d1, s)); cb = _vadd(p3, _vscale(d2, t))
        return _vlen(_vsub(ca, cb)), ca, cb

    def _capsule_capsule(self, a: Collider, b: Collider) -> CollisionManifold:
        ca: CapsuleShape = a.shape  # type: ignore
        cb: CapsuleShape = b.shape  # type: ignore
        a1, a2 = self._capsule_endpoints(a); b1, b2 = self._capsule_endpoints(b)
        dist, pa, pb = self._segment_segment(a1, a2, b1, b2)
        radius_sum = ca.radius + cb.radius
        if dist >= radius_sum:
            return CollisionManifold(colliding=False)
        normal = _vnorm(_vsub(pb, pa)) if dist > _EPS else (0.0, 1.0, 0.0)
        penetration = radius_sum - dist
        point = _vadd(pa, _vscale(normal, ca.radius))
        return CollisionManifold(contacts=[ContactPoint(point=point, normal=normal, penetration=penetration)],
                                 normal=normal, penetration=penetration, separating_axis=normal, colliding=True)

    def _capsule_sphere(self, cap_c: Collider, sph_c: Collider) -> CollisionManifold:
        cap: CapsuleShape = cap_c.shape  # type: ignore
        sph: SphereShape = sph_c.shape  # type: ignore
        a1, a2 = self._capsule_endpoints(cap_c)
        d = _vsub(a2, a1); seg_len2 = _vdot(d, d)
        if seg_len2 < _EPS:
            closest = a1
        else:
            t = _clamp(_vdot(_vsub(sph_c.position, a1), d) / seg_len2, 0.0, 1.0)
            closest = _vadd(a1, _vscale(d, t))
        delta = _vsub(sph_c.position, closest)
        dist = _vlen(delta)
        radius_sum = cap.radius + sph.radius
        if dist >= radius_sum:
            return CollisionManifold(colliding=False)
        normal = _vnorm(delta) if dist > _EPS else (0.0, 1.0, 0.0)
        penetration = radius_sum - dist
        return CollisionManifold(contacts=[ContactPoint(point=closest, normal=normal, penetration=penetration)],
                                 normal=normal, penetration=penetration, separating_axis=normal, colliding=True)

    def _capsule_box(self, cap_c: Collider, box_c: Collider) -> CollisionManifold:
        cap: CapsuleShape = cap_c.shape  # type: ignore
        a1, a2 = self._capsule_endpoints(cap_c)
        mid = _vscale(_vadd(a1, a2), 0.5)
        closest = self._closest_point_on_aabb(mid, box_c.aabb_min, box_c.aabb_max)
        delta = _vsub(mid, closest)
        dist = _vlen(delta)
        if dist >= cap.radius:
            return CollisionManifold(colliding=False)
        normal = _vnorm(delta) if dist > _EPS else (0.0, 1.0, 0.0)
        penetration = cap.radius - dist
        return CollisionManifold(contacts=[ContactPoint(point=closest, normal=normal, penetration=penetration)],
                                 normal=normal, penetration=penetration, separating_axis=normal, colliding=True)

    def _plane_sphere(self, plane_c: Collider, sph_c: Collider) -> CollisionManifold:
        plane: PlaneShape = plane_c.shape  # type: ignore
        sph: SphereShape = sph_c.shape  # type: ignore
        n = _vnorm(plane.normal)
        d = _vdot(n, sph_c.position) - plane.offset - _vdot(n, plane_c.position)
        if d >= sph.radius:
            return CollisionManifold(colliding=False)
        penetration = sph.radius - d
        point = _vsub(sph_c.position, _vscale(n, d))
        return CollisionManifold(contacts=[ContactPoint(point=point, normal=n, penetration=penetration)],
                                 normal=n, penetration=penetration, separating_axis=n, colliding=True)

    # GJK narrowphase for convex hulls
    def _support_hull(self, collider: Collider, direction: Vec3) -> Vec3:
        hull: ConvexHullShape = collider.shape  # type: ignore
        inv_rot = (-collider.rotation[0], -collider.rotation[1], -collider.rotation[2], collider.rotation[3])
        local_dir = _rotate_by_quat(direction, inv_rot)
        best = hull.vertices[0]; best_dot = _vdot(best, local_dir)
        for v in hull.vertices[1:]:
            d = _vdot(v, local_dir)
            if d > best_dot:
                best_dot = d; best = v
        return _vadd(collider.position, _rotate_by_quat(best, collider.rotation))

    def _minkowski_support(self, a: Collider, b: Collider, direction: Vec3) -> Vec3:
        return _vsub(self._support_hull(a, direction), self._support_hull(b, _vscale(direction, -1.0)))

    def _gjk_narrowphase(self, a: Collider, b: Collider) -> CollisionManifold:
        """GJK distance algorithm for two convex hulls.

        Returns a manifold. When the hulls intersect the penetration is
        approximated along the final simplex direction (a full EPA pass
        is out of scope here but the contact normal is still usable).
        """
        direction = (1.0, 0.0, 0.0)
        simplex: List[Vec3] = [self._minkowski_support(a, b, direction)]
        direction = _vscale(simplex[0], -1.0)
        for _ in range(_GJK_MAX_ITER):
            support = self._minkowski_support(a, b, direction)
            if _vdot(support, direction) < -_EPS:
                return CollisionManifold(colliding=False)
            simplex.append(support)
            contained, direction, simplex = self._simplex_step(simplex)
            if contained:
                normal = _vnorm(direction) if _vlen(direction) > _EPS else (0.0, 1.0, 0.0)
                point = _vscale(_vadd(a.position, b.position), 0.5)
                return CollisionManifold(contacts=[ContactPoint(point=point, normal=normal, penetration=0.05)],
                                         normal=normal, penetration=0.05, separating_axis=normal, colliding=True)
            if _vlen(direction) < _EPS:
                break
        return CollisionManifold(colliding=False)

    def _simplex_step(self, simplex: List[Vec3]) -> Tuple[bool, Vec3, List[Vec3]]:
        """Update the GJK simplex. Returns (contains_origin, direction, simplex)."""
        n = len(simplex)
        if n == 2:
            b, a = simplex[1], simplex[0]
            ab = _vsub(b, a); ao = _vscale(a, -1.0)
            if _vdot(ab, ao) > 0:
                return False, _vcross(_vcross(ab, ao), ab), simplex
            return False, ao, [a]
        if n == 3:
            c, b, a = simplex[2], simplex[1], simplex[0]
            ab = _vsub(b, a); ac = _vsub(c, a); ao = _vscale(a, -1.0)
            abc = _vcross(ab, ac)
            if _vdot(_vcross(abc, ac), ao) > 0:
                if _vdot(ac, ao) > 0:
                    return False, _vcross(_vcross(ac, ao), ac), [a, c]
                return self._simplex_step([a, b])
            if _vdot(_vcross(ab, abc), ao) > 0:
                return self._simplex_step([a, b])
            if _vdot(abc, ao) > 0:
                return False, abc, simplex
            return False, _vscale(abc, -1.0), [a, c, b]
        if n == 4:
            d, c, b, a = simplex[3], simplex[2], simplex[1], simplex[0]
            ab = _vsub(b, a); ac = _vsub(c, a); ad = _vsub(d, a); ao = _vscale(a, -1.0)
            abc = _vcross(ab, ac); acd = _vcross(ac, ad); adb = _vcross(ad, ab)
            if _vdot(abc, ao) > 0:
                return self._simplex_step([a, b, c])
            if _vdot(acd, ao) > 0:
                return self._simplex_step([a, c, d])
            if _vdot(adb, ao) > 0:
                return self._simplex_step([a, d, b])
            return True, (0.0, 0.0, 0.0), simplex
        return False, (1.0, 0.0, 0.0), simplex

    # Ray casting
    def ray_cast(self, origin: Vec3, direction: Vec3, max_distance: float = 1000.0,
                 layer_mask: int = 0xFFFF, ignore_triggers: bool = False) -> RaycastHit:
        """Cast a single ray and return the closest hit."""
        with self._lock:
            self._statistics.ray_queries += 1
            d = _vnorm(direction)
            if _vlen(d) < _EPS:
                return RaycastHit()
            best = RaycastHit(distance=max_distance)
            for collider in self._colliders.values():
                if not collider.enabled or (collider.layer & layer_mask) == 0:
                    continue
                if ignore_triggers and collider.is_trigger:
                    continue
                hit = self._ray_vs_collider(origin, d, collider, max_distance)
                if hit.hit and hit.distance < best.distance:
                    best = hit
            if best.hit:
                best.distance = min(best.distance, max_distance)
            self._ray_history.append({"origin": list(origin), "direction": list(d),
                                      "max_distance": max_distance, "hit": best.hit, "timestamp": _now_ts()})
            if len(self._ray_history) > 256:
                self._ray_history.pop(0)
            return best

    def ray_cast_batch(self, rays: List[Tuple[Vec3, Vec3]], max_distance: float = 1000.0,
                       layer_mask: int = 0xFFFF, ignore_triggers: bool = False) -> List[RaycastHit]:
        """Cast many rays and return one hit per ray."""
        with self._lock:
            results: List[RaycastHit] = []
            for origin, direction in rays:
                d = _vnorm(direction)
                if _vlen(d) < _EPS:
                    results.append(RaycastHit()); continue
                best = RaycastHit(distance=max_distance)
                for collider in self._colliders.values():
                    if not collider.enabled or (collider.layer & layer_mask) == 0:
                        continue
                    if ignore_triggers and collider.is_trigger:
                        continue
                    hit = self._ray_vs_collider(origin, d, collider, max_distance)
                    if hit.hit and hit.distance < best.distance:
                        best = hit
                results.append(best)
            self._statistics.ray_queries += len(rays)
            return results

    def _ray_vs_collider(self, origin: Vec3, direction: Vec3, collider: Collider, max_distance: float) -> RaycastHit:
        """Dispatch ray-shape intersection by shape type."""
        shape = collider.shape
        if isinstance(shape, SphereShape):
            return self._ray_sphere(origin, direction, collider, shape, max_distance)
        if isinstance(shape, (BoxShape, CapsuleShape, ConvexHullShape)):
            return self._ray_aabb(origin, direction, collider, max_distance)
        if isinstance(shape, PlaneShape):
            return self._ray_plane(origin, direction, collider, shape, max_distance)
        return RaycastHit()

    def _ray_sphere(self, origin: Vec3, direction: Vec3, collider: Collider, sphere: SphereShape, max_distance: float) -> RaycastHit:
        oc = _vsub(origin, collider.position)
        b = _vdot(oc, direction)
        c = _vdot(oc, oc) - sphere.radius * sphere.radius
        if c > 0.0 and b > 0.0:
            return RaycastHit()
        disc = b * b - c
        if disc < 0.0:
            return RaycastHit()
        t = -b - math.sqrt(disc)
        if t < 0.0:
            t = 0.0
        if t > max_distance:
            return RaycastHit()
        point = _vadd(origin, _vscale(direction, t))
        return RaycastHit(point=point, normal=_vnorm(_vsub(point, collider.position)), distance=t,
                          collider_id=collider.collider_id, entity_id=collider.entity_id, hit=True)

    def _ray_aabb(self, origin: Vec3, direction: Vec3, collider: Collider, max_distance: float) -> RaycastHit:
        bmin, bmax = collider.aabb_min, collider.aabb_max
        tmin, tmax = 0.0, max_distance
        for i in range(3):
            if abs(direction[i]) < _EPS:
                if origin[i] < bmin[i] or origin[i] > bmax[i]:
                    return RaycastHit()
            else:
                inv = 1.0 / direction[i]
                t1 = (bmin[i] - origin[i]) * inv; t2 = (bmax[i] - origin[i]) * inv
                if t1 > t2:
                    t1, t2 = t2, t1
                tmin = max(tmin, t1); tmax = min(tmax, t2)
                if tmin > tmax:
                    return RaycastHit()
        if tmin < 0.0:
            tmin = 0.0
        point = _vadd(origin, _vscale(direction, tmin))
        center = tuple((bmin[i] + bmax[i]) * 0.5 for i in range(3))
        local = _vsub(point, center)
        extents = tuple((bmax[i] - bmin[i]) * 0.5 for i in range(3))
        nrm = tuple(local[i] / extents[i] if extents[i] > _EPS else 0.0 for i in range(3))
        ax, ay, az = abs(nrm[0]), abs(nrm[1]), abs(nrm[2])
        if ax >= ay and ax >= az:
            normal = (1.0 if nrm[0] > 0 else -1.0, 0.0, 0.0)
        elif ay >= ax and ay >= az:
            normal = (0.0, 1.0 if nrm[1] > 0 else -1.0, 0.0)
        else:
            normal = (0.0, 0.0, 1.0 if nrm[2] > 0 else -1.0)
        return RaycastHit(point=point, normal=normal, distance=tmin, collider_id=collider.collider_id,
                          entity_id=collider.entity_id, hit=True)

    def _ray_plane(self, origin: Vec3, direction: Vec3, collider: Collider, plane: PlaneShape, max_distance: float) -> RaycastHit:
        n = _vnorm(plane.normal)
        denom = _vdot(n, direction)
        if abs(denom) < _EPS:
            return RaycastHit()
        plane_point = _vadd(collider.position, _vscale(n, plane.offset))
        t = _vdot(_vsub(plane_point, origin), n) / denom
        if t < 0.0 or t > max_distance:
            return RaycastHit()
        point = _vadd(origin, _vscale(direction, t))
        return RaycastHit(point=point, normal=n if denom < 0 else _vscale(n, -1.0), distance=t,
                          collider_id=collider.collider_id, entity_id=collider.entity_id, hit=True)

    # Shape sweeping (continuous collision detection)
    def sweep_shape(self, shape: ColliderShape, start: Vec3, end: Vec3,
                    rotation: Quat = (0.0, 0.0, 0.0, 1.0), layer_mask: int = 0xFFFF,
                    max_distance: float = 1000.0) -> SweepResult:
        """Sweep a shape from start to end and return the time-of-impact."""
        with self._lock:
            self._statistics.sweep_queries += 1
            delta = _vsub(end, start)
            total = _vlen(delta)
            if total < _EPS:
                return SweepResult(hit=False, time_of_impact=1.0)
            temp = Collider(shape=shape, position=start, rotation=rotation, layer=layer_mask, mask=0xFFFF)
            steps = 32
            for i in range(steps + 1):
                t = i / steps
                temp.position = _vadd(start, _vscale(delta, t))
                self._compute_world_aabb(temp)
                for cid in self.query_aabb(temp.aabb_min, temp.aabb_max, layer_mask):
                    collider = self._colliders.get(cid)
                    if collider is None or not collider.enabled or collider.is_trigger:
                        continue
                    if not self._can_collide(temp, collider):
                        continue
                    mf = self._narrowphase(temp, collider)
                    if mf.colliding:
                        return SweepResult(hit=True, time_of_impact=t,
                                           contact_point=mf.contacts[0].point if mf.contacts else temp.position,
                                           normal=mf.normal, collider_id=cid, entity_id=collider.entity_id)
                if (total / steps) * i > max_distance:
                    break
            return SweepResult(hit=False, time_of_impact=1.0)

    # Tick pipeline: pairs, contacts, events
    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        """Run one full pipeline tick: broadphase, narrowphase, events."""
        with self._lock:
            t_start = _now_ts()
            self._tick += 1
            current_tick = self._tick
            t_broad = _now_ts()
            candidate_keys = self._broadphase_pairs()
            broad_ms = (_now_ts() - t_broad) * 1000.0
            t_narrow = _now_ts()
            new_pairs: List[CollisionPair] = []
            new_colliding: set = set()
            for key in candidate_keys:
                a = self._colliders.get(key[0]); b = self._colliders.get(key[1])
                if a is None or b is None:
                    continue
                mf = self._narrowphase(a, b)
                pair = CollisionPair(collider_a=key[0], collider_b=key[1], entity_a=a.entity_id,
                                     entity_b=b.entity_id, manifold=mf, colliding=mf.colliding, tick=current_tick)
                new_pairs.append(pair)
                if mf.colliding:
                    new_colliding.add(key)
                    self._persistent[key] = mf
            narrow_ms = (_now_ts() - t_narrow) * 1000.0
            # Events: enter / stay / exit.
            prev = self._prev_colliding
            events: List[CollisionEvent] = []
            for key in new_colliding:
                etype = CollisionEventType.STAY if key in prev else CollisionEventType.ENTER
                events.append(CollisionEvent(event_type=etype, collider_a=key[0], collider_b=key[1],
                                             manifold=self._persistent.get(key), tick=current_tick))
            for key in prev:
                if key not in new_colliding:
                    events.append(CollisionEvent(event_type=CollisionEventType.EXIT, collider_a=key[0],
                                                 collider_b=key[1], tick=current_tick))
                    self._persistent.pop(key, None)
            self._pairs = new_pairs
            self._pair_set = new_colliding
            self._events = events[-_MAX_EVENTS:]
            self._prev_colliding = new_colliding
            # Statistics.
            total_ms = (_now_ts() - t_start) * 1000.0
            stats = self._statistics
            stats.tick_count += 1
            stats.broadphase_time_ms = broad_ms
            stats.narrowphase_time_ms = narrow_ms
            stats.total_time_ms = total_ms
            stats.pair_count = len(new_pairs)
            stats.contact_count = sum(1 for p in new_pairs if p.colliding)
            stats.persistent_count = len(self._persistent)
            stats.event_count = len(events)
            n = stats.tick_count
            stats.avg_pair_count = (stats.avg_pair_count * (n - 1) + len(new_pairs)) / n
            stats.avg_narrowphase_ms = (stats.avg_narrowphase_ms * (n - 1) + narrow_ms) / n
            elapsed = max(_now_ts() - stats.last_reset_ts, _EPS)
            stats.queries_per_second = (stats.ray_queries + stats.sweep_queries) / elapsed
            if self._auto_rebalance and self._max_tree_depth_seen > _REBALANCE_THRESHOLD and n % 60 == 0:
                self.rebalance_tree()
            return {"tick": current_tick, "broadphase_ms": round(broad_ms, 4),
                    "narrowphase_ms": round(narrow_ms, 4), "total_ms": round(total_ms, 4),
                    "pairs": len(new_pairs), "colliding": len(new_colliding), "events": len(events)}

    def get_collision_pairs(self, only_colliding: bool = False) -> List[CollisionPair]:
        """Return the most recent collision pairs from the last tick."""
        with self._lock:
            return [p for p in self._pairs if p.colliding] if only_colliding else list(self._pairs)

    def get_contacts(self) -> List[ContactPoint]:
        """Return every contact point from colliding pairs this tick."""
        with self._lock:
            contacts: List[ContactPoint] = []
            for pair in self._pairs:
                if pair.colliding and pair.manifold is not None:
                    contacts.extend(pair.manifold.contacts)
            return contacts

    def get_persistent_contacts(self) -> Dict[Tuple[str, str], CollisionManifold]:
        """Return the map of persistent contact manifolds."""
        with self._lock:
            return dict(self._persistent)

    def get_collision_events(self, event_type: Optional[CollisionEventType] = None) -> List[CollisionEvent]:
        """Return collision events, optionally filtered by type."""
        with self._lock:
            if event_type is None:
                return list(self._events)
            return [e for e in self._events if e.event_type == event_type]

    # Contact constraints for the physics solver
    def _build_constraints(self) -> List[ContactConstraint]:
        constraints: List[ContactConstraint] = []
        for pair in self._pairs:
            if not pair.colliding or pair.manifold is None:
                continue
            a = self._colliders.get(pair.collider_a); b = self._colliders.get(pair.collider_b)
            if a is None or b is None:
                continue
            restitution = (a.restitution + b.restitution) * 0.5
            friction = (a.friction + b.friction) * 0.5
            persistent = pair.key() in self._persistent
            for cp in pair.manifold.contacts:
                constraints.append(ContactConstraint(collider_a=pair.collider_a, collider_b=pair.collider_b,
                    contact_point=cp.point, normal=cp.normal, penetration=cp.penetration,
                    restitution=restitution, friction=friction, persistent=persistent))
        return constraints[:_MAX_CONTACTS]

    def get_contact_constraints(self) -> List[ContactConstraint]:
        """Return solver-ready contact constraints built from current pairs."""
        with self._lock:
            return self._build_constraints()

    # Debug visualization
    def get_debug_data(self, layers: Optional[int] = None, triggers_only: bool = False,
                       persistent_only: bool = False, include_aabbs: bool = True,
                       include_contacts: bool = True) -> DebugDrawData:
        """Generate draw data for a debug renderer with optional filters."""
        with self._lock:
            data = DebugDrawData()
            for collider in self._colliders.values():
                if not collider.enabled:
                    continue
                if layers is not None and (collider.layer & layers) == 0:
                    continue
                if triggers_only and not collider.is_trigger:
                    continue
                shape = collider.shape
                wf: Dict[str, Any] = {"collider_id": collider.collider_id, "entity_id": collider.entity_id,
                    "name": collider.name, "position": list(collider.position), "is_trigger": collider.is_trigger,
                    "shape_type": shape.shape_type.value if hasattr(shape, "shape_type") else "unknown"}
                if isinstance(shape, BoxShape):
                    wf["half_extents"] = list(shape.half_extents)
                elif isinstance(shape, SphereShape):
                    wf["radius"] = shape.radius
                elif isinstance(shape, CapsuleShape):
                    wf["radius"] = shape.radius; wf["half_height"] = shape.half_height
                data.wireframes.append(wf)
                if include_aabbs:
                    data.aabbs.append({"collider_id": collider.collider_id, "min": list(collider.aabb_min), "max": list(collider.aabb_max)})
            if include_contacts:
                for pair in self._pairs:
                    if not pair.colliding or pair.manifold is None:
                        continue
                    if persistent_only and pair.key() not in self._persistent:
                        continue
                    for cp in pair.manifold.contacts:
                        data.contact_points.append({"point": list(cp.point), "collider_a": pair.collider_a,
                                                    "collider_b": pair.collider_b, "penetration": cp.penetration})
                        data.contact_normals.append({"point": list(cp.point), "normal": list(cp.normal),
                                                     "collider_a": pair.collider_a, "collider_b": pair.collider_b})
            data.ray_debug.extend(self._ray_history)
            return data

    # Statistics and status
    def get_statistics(self) -> CollisionStatistics:
        """Return the current statistics object."""
        with self._lock:
            return self._statistics

    def get_stats(self) -> Dict[str, Any]:
        """Return statistics as a dictionary."""
        with self._lock:
            return self._statistics.to_dict()

    def get_status(self) -> Dict[str, Any]:
        """Return a high-level status snapshot of the system."""
        with self._lock:
            return {
                "initialized": self._initialized, "broadphase_method": self._broadphase_method.value,
                "collider_count": len(self._colliders), "node_count": len(self._nodes),
                "tree_depth": self._tree_depth(), "max_tree_depth_seen": self._max_tree_depth_seen,
                "auto_rebalance": self._auto_rebalance, "tick": self._tick,
                "active_pairs": len(self._pair_set), "persistent_contacts": len(self._persistent),
                "pending_events": len(self._events),
                "layers": {lid: layer.to_dict() for lid, layer in self._layers.items()},
            }

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a full snapshot of registry and tree state for persistence."""
        with self._lock:
            return {
                "status": self.get_status(), "statistics": self._statistics.to_dict(),
                "colliders": [c.to_dict() for c in self._colliders.values()],
                "pairs": [p.to_dict() for p in self._pairs],
                "events": [e.to_dict() for e in self._events],
                "collision_matrix": dict(self._collision_matrix),
                "broadphase_method": self._broadphase_method.value, "tick": self._tick, "snapshot_ts": _now_ts(),
            }

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary summary suitable for serialization."""
        return self.get_snapshot()

    # AI-assisted helpers
    def ai_optimize_broadphase(self) -> Dict[str, Any]:
        """Analyze the scene and suggest broadphase parameters.

        Inspects collider count, spatial density, tree depth and the
        static/dynamic split. Returns suggested tuning parameters and a
        short rationale string describing the chosen strategy.
        """
        with self._lock:
            total = len(self._colliders)
            if total == 0:
                return {"suggested_method": self._broadphase_method.value,
                        "rationale": "Scene is empty; current method retained.",
                        "suggested_auto_rebalance": True, "density": 0.0}
            static_count = sum(1 for c in self._colliders.values() if c.is_static)
            mins = [c.aabb_min for c in self._colliders.values()]
            maxs = [c.aabb_max for c in self._colliders.values()]
            scene_min = (min(m[0] for m in mins), min(m[1] for m in mins), min(m[2] for m in mins))
            scene_max = (max(m[0] for m in maxs), max(m[1] for m in maxs), max(m[2] for m in maxs))
            volume = max((scene_max[0]-scene_min[0]) * (scene_max[1]-scene_min[1]) * (scene_max[2]-scene_min[2]), _EPS)
            density = total / volume
            depth = self._tree_depth()
            if total < 200:
                suggested, rationale = BroadphaseMethod.SWEEP_AND_PRUNE, "Low collider count favors sweep-and-prune for minimal overhead."
            elif density > 0.5:
                suggested, rationale = BroadphaseMethod.UNIFORM_GRID, "High spatial density favors a uniform grid broadphase."
            else:
                suggested, rationale = BroadphaseMethod.AABB_TREE, "Moderate density and spread favors the dynamic AABB tree."
            return {
                "collider_count": total, "static_count": static_count, "dynamic_count": total - static_count,
                "density": round(density, 6), "current_tree_depth": depth, "current_method": self._broadphase_method.value,
                "suggested_method": suggested.value, "rationale": rationale,
                "suggested_auto_rebalance": depth > _REBALANCE_THRESHOLD,
                "scene_min": list(scene_min), "scene_max": list(scene_max),
            }

    def ai_predict_hotspots(self, trajectories: Dict[str, Vec3], horizon: float = 1.0) -> List[Dict[str, Any]]:
        """Predict collision hotspots from entity velocity trajectories.

        ``trajectories`` maps collider ids to a velocity vector. The
        method projects each dynamic collider forward by ``horizon``
        seconds, collects regions where projected AABBs overlap, and
        returns a list of hotspot descriptors sorted by severity.
        """
        with self._lock:
            projected: Dict[str, Tuple[Vec3, Vec3]] = {}
            for cid, vel in trajectories.items():
                collider = self._colliders.get(cid)
                if collider is None or not collider.enabled:
                    continue
                future = Collider(shape=collider.shape, position=_vadd(collider.position, _vscale(vel, horizon)),
                                  rotation=collider.rotation, scale=collider.scale)
                self._compute_world_aabb(future)
                projected[cid] = (future.aabb_min, future.aabb_max)
            hotspots: List[Dict[str, Any]] = []
            ids = list(projected.keys())
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    a_id, b_id = ids[i], ids[j]
                    a_min, a_max = projected[a_id]; b_min, b_max = projected[b_id]
                    if not _aabb_overlap(a_min, a_max, b_min, b_max):
                        continue
                    a = self._colliders.get(a_id); b = self._colliders.get(b_id)
                    if a is None or b is None or not self._can_collide(a, b):
                        continue
                    ov = (min(a_max[0], b_max[0]) - max(a_min[0], b_min[0]),
                          min(a_max[1], b_max[1]) - max(a_min[1], b_min[1]),
                          min(a_max[2], b_max[2]) - max(a_min[2], b_min[2]))
                    severity = ov[0] * ov[1] * ov[2]
                    center = ((max(a_min[0], b_min[0]) + min(a_max[0], b_max[0])) * 0.5,
                              (max(a_min[1], b_min[1]) + min(a_max[1], b_max[1])) * 0.5,
                              (max(a_min[2], b_min[2]) + min(a_max[2], b_max[2])) * 0.5)
                    hotspots.append({"collider_a": a_id, "collider_b": b_id, "entity_a": a.entity_id,
                                     "entity_b": b.entity_id, "center": list(center),
                                     "severity": round(severity, 6), "horizon": horizon})
            hotspots.sort(key=lambda h: h["severity"], reverse=True)
            return hotspots


# Module Factory
def get_collision_detection_system() -> CollisionDetectionSystem:
    """Get or create the global CollisionDetectionSystem singleton instance."""
    return CollisionDetectionSystem.get_instance()


def get_collision_detection() -> CollisionDetectionSystem:
    """Alias for get_collision_detection_system."""
    return CollisionDetectionSystem.get_instance()
