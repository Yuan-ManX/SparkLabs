"""
SparkLabs Engine - Destructible Structure System

A real-time structural destruction runtime for the SparkLabs AI-native game
engine. Structures are represented as node-edge meshes where each node carries
mass and position and each edge carries strength, material, and stress state.
The system simulates impact damage, explosive blasts, fracture propagation,
progressive collapse, debris physics, and chain-reaction destruction across
linked structures. An AI analysis layer evaluates weak points, tunes fracture
parameters, predicts collapse scenarios, and generates controlled demolition
plans.

Architecture:
  _DestructibleStructureSystem (singleton)
    |-- MaterialType, FracturePattern, StructureStatus, DebrisStatus,
       DestructibleEventKind
    |-- MaterialProperties, StructureNode, StructureEdge, Structure,
       FractureRecord, DebrisPiece, CollapseEvent, DestructibleConfig,
       DestructibleStats, DestructibleSnapshot, DestructibleEvent
    |-- get_destructible_structure_system

Core Capabilities:
  - register_structure / get_structure / remove_structure / list_structures:
    structure lifecycle with node-edge meshes, position, and integrity.
  - register_material_type / get_material_type / list_material_types /
    remove_material_type: material definitions with yield stress and density.
  - apply_damage / apply_explosive: impact and blast damage that propagates
    stress through connected edges and creates fractures.
  - create_fracture / propagate_fracture: explicit fracture creation and
    chain-reaction propagation to neighboring edges.
  - check_structural_integrity / compute_load_distribution / get_stress_map /
    assess_damage: structural analysis of load paths and weak points.
  - trigger_collapse / simulate_collapse: progressive collapse simulation
    that breaks edges, displaces nodes, and spawns debris.
  - register_debris / get_debris / list_debris / remove_debris / settle_debris
    / compute_debris_pile: debris lifecycle with simple settling physics.
  - ai_assess_vulnerability / ai_optimize_fracture / ai_predict_collapse /
    ai_generate_destruction_plan: AI-driven analysis and tuning.
  - get_node / get_edge / list_nodes / list_edges: mesh element access.
  - get_fracture / list_fractures / get_collapse_event / list_collapse_events:
    damage history inspection.
  - reset_structure / repair_structure: structure recovery operations.
  - get_deformation_summary / get_visualization_data: rendering helpers.
  - get_status / get_stats / get_snapshot / get_config / set_config:
    observability and configuration management.
  - list_events / tick: event log and per-frame simulation step.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`_DestructibleStructureSystem.get_instance` or the module-level
:func:`get_destructible_structure_system` factory.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sparkai.engine.engine_formation_system import _dataclass_to_dict


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_STRUCTURES: int = 500
_MAX_MATERIALS: int = 200
_MAX_FRACTURES: int = 5000
_MAX_DEBRIS: int = 5000
_MAX_COLLAPSE_EVENTS: int = 2000
_MAX_EVENTS: int = 5000
_MAX_NODES_PER_STRUCTURE: int = 2000
_MAX_EDGES_PER_STRUCTURE: int = 4000

# Physics constants
_EPSILON: float = 1e-9
_GRAVITY: float = 9.81
_DEFAULT_DT: float = 0.016
_COLLAPSE_THRESHOLD: float = 0.25  # Integrity below this triggers collapse
_DAMAGE_TO_INTEGRITY: float = 1.0  # 1:1 mapping by default
_STRESS_PROPAGATION_FACTOR: float = 0.6  # Fraction of stress redistributed
_BLAST_FALLOFF: float = 2.0  # Quadratic blast falloff exponent
_DEBRIS_SETTLE_TIME: float = 3.0  # Seconds before debris settles
_DEBRIS_DRAG: float = 0.4  # Velocity drag coefficient
_DEBRIS_GRAVITY: float = 9.81


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix.

    Combines a millisecond timestamp with a monotonic counter and a short
    random suffix to guarantee uniqueness even within the same millisecond.
    """
    base = f"{int(time.time() * 1000) % 1000000:06d}"
    suffix = _new_id._counter  # type: ignore[attr-defined]
    _new_id._counter += 1  # type: ignore[attr-defined]
    return f"{prefix}_{base}_{suffix:04d}" if prefix else f"{base}_{suffix:04d}"


_new_id._counter = 0  # type: ignore[attr-defined]


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to default."""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    """Convert arbitrary values into JSON-serializable primitives."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Parse a float, returning default on failure or non-finite input."""
    try:
        if value is None:
            return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Parse an int, returning default on failure."""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _vec3_distance(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    """Compute the Euclidean distance between two 3D points."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _vec3_length(v: Tuple[float, float, float]) -> float:
    """Return the magnitude of a 3D vector."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _vec3_normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Return the unit vector of v, or a zero vector if v is near zero."""
    length = _vec3_length(v)
    if length < _EPSILON:
        return (0.0, 0.0, 0.0)
    inv = 1.0 / length
    return (v[0] * inv, v[1] * inv, v[2] * inv)


def _vec3_sub(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Subtract vector b from vector a."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec3_add(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Add two 3D vectors."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vec3_scale(v: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    """Scale a 3D vector by a scalar."""
    return (v[0] * s, v[1] * s, v[2] * s)


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b by parameter t."""
    return a + (b - a) * _clamp(t, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MaterialType(str, Enum):
    """Classification of structural materials by physical properties."""
    CONCRETE = "concrete"
    WOOD = "wood"
    STEEL = "steel"
    GLASS = "glass"
    STONE = "stone"
    BRICK = "brick"


class FracturePattern(str, Enum):
    """Pattern describing how an edge or region breaks apart."""
    SHATTER = "shatter"
    SPLINTER = "splinter"
    CRUMBLE = "crumble"
    SHEAR = "shear"
    EXPLOSIVE = "explosive"


class StructureStatus(str, Enum):
    """Lifecycle status of a destructible structure."""
    INTACT = "intact"
    DAMAGED = "damaged"
    COLLAPSING = "collapsing"
    DESTROYED = "destroyed"
    RUBBLE = "rubble"


class DebrisStatus(str, Enum):
    """Status of a debris piece in the simulation."""
    ACTIVE = "active"
    SETTLED = "settled"
    REMOVED = "removed"


class DestructibleEventKind(str, Enum):
    """Audit event types emitted by the destructible structure system."""
    STRUCTURE_REGISTERED = "structure_registered"
    STRUCTURE_REMOVED = "structure_removed"
    MATERIAL_REGISTERED = "material_registered"
    MATERIAL_REMOVED = "material_removed"
    DAMAGE_APPLIED = "damage_applied"
    EXPLOSIVE_DETONATED = "explosive_detonated"
    FRACTURE_CREATED = "fracture_created"
    FRACTURE_PROPAGATED = "fracture_propagated"
    COLLAPSE_TRIGGERED = "collapse_triggered"
    COLLAPSE_SIMULATED = "collapse_simulated"
    COLLAPSE_COMPLETED = "collapse_completed"
    DEBRIS_REGISTERED = "debris_registered"
    DEBRIS_REMOVED = "debris_removed"
    DEBRIS_SETTLED = "debris_settled"
    REPAIR_APPLIED = "repair_applied"
    STRUCTURE_RESET = "structure_reset"
    AI_ASSESSMENT = "ai_assessment"
    CONFIG_UPDATED = "config_updated"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Material property presets (loaded as seed data)
# ---------------------------------------------------------------------------

_MATERIAL_TYPE_PRESETS: Dict[str, Dict[str, Any]] = {
    "mt_concrete": {
        "name": "Reinforced Concrete",
        "base_material": MaterialType.CONCRETE.value,
        "yield_stress": 30.0,
        "density": 2400.0,
        "fracture_toughness": 1.2,
        "elastic_modulus": 30.0,
        "brittleness": 0.6,
    },
    "mt_wood": {
        "name": "Oak Timber",
        "base_material": MaterialType.WOOD.value,
        "yield_stress": 40.0,
        "density": 700.0,
        "fracture_toughness": 0.8,
        "elastic_modulus": 12.0,
        "brittleness": 0.3,
    },
    "mt_steel": {
        "name": "Structural Steel",
        "base_material": MaterialType.STEEL.value,
        "yield_stress": 250.0,
        "density": 7850.0,
        "fracture_toughness": 2.5,
        "elastic_modulus": 200.0,
        "brittleness": 0.15,
    },
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class MaterialProperties:
    """Definition of a structural material with physical properties."""
    material_id: str
    name: str = ""
    base_material: str = MaterialType.CONCRETE.value
    yield_stress: float = 30.0
    density: float = 2400.0
    fracture_toughness: float = 1.0
    elastic_modulus: float = 30.0
    brittleness: float = 0.5
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class StructureNode:
    """A single point in the structure mesh with position and mass."""
    node_id: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    mass: float = 1.0
    connections: List[str] = field(default_factory=list)
    stress: float = 0.0
    displacement: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    is_support: bool = False
    is_broken: bool = False
    load: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class StructureEdge:
    """A connection between two nodes carrying strength and stress state."""
    edge_id: str
    node_a: str = ""
    node_b: str = ""
    strength: float = 100.0
    material: str = MaterialType.CONCRETE.value
    rest_length: float = 1.0
    current_length: float = 1.0
    stress: float = 0.0
    strain: float = 0.0
    is_broken: bool = False
    load_capacity: float = 100.0
    damage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Structure:
    """A complete destructible structure with a node-edge mesh."""
    structure_id: str
    name: str = ""
    material_type: str = MaterialType.CONCRETE.value
    nodes: List[StructureNode] = field(default_factory=list)
    edges: List[StructureEdge] = field(default_factory=list)
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    status: str = StructureStatus.INTACT.value
    integrity: float = 1.0
    max_integrity: float = 1.0
    damage_accumulated: float = 0.0
    collapse_progress: float = 0.0
    collapse_duration: float = 5.0
    original_edge_count: int = 0
    original_node_count: int = 0
    bounding_radius: float = 10.0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FractureRecord:
    """Records a single fracture event on a structure edge."""
    fracture_id: str
    structure_id: str
    edge_id: str = ""
    pattern: str = FracturePattern.SHEAR.value
    severity: float = 0.5
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    stress_at_fracture: float = 0.0
    propagated: bool = False
    propagated_to: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DebrisPiece:
    """A piece of debris spawned during structural destruction."""
    debris_id: str
    structure_id: str = ""
    mass: float = 1.0
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    size: float = 1.0
    material: str = MaterialType.CONCRETE.value
    status: str = DebrisStatus.ACTIVE.value
    age: float = 0.0
    settled_at: str = ""
    spawned_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CollapseEvent:
    """Records a structural collapse with progression tracking."""
    event_id: str
    structure_id: str
    triggered_by: str = "manual"
    progress: float = 0.0
    duration: float = 5.0
    nodes_collapsed: int = 0
    edges_broken: int = 0
    debris_generated: int = 0
    started_at: str = field(default_factory=_now)
    completed_at: str = ""
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DestructibleConfig:
    """Tunable configuration for the destructible structure system."""
    max_structures: int = _MAX_STRUCTURES
    max_materials: int = _MAX_MATERIALS
    max_fractures: int = _MAX_FRACTURES
    max_debris: int = _MAX_DEBRIS
    max_collapse_events: int = _MAX_COLLAPSE_EVENTS
    max_events: int = _MAX_EVENTS
    gravity: float = _GRAVITY
    damage_decay: float = 0.05
    fracture_propagation_rate: float = _STRESS_PROPAGATION_FACTOR
    collapse_speed: float = 1.0
    collapse_threshold: float = _COLLAPSE_THRESHOLD
    debris_settle_time: float = _DEBRIS_SETTLE_TIME
    debris_drag: float = _DEBRIS_DRAG
    enable_chain_reactions: bool = True
    enable_debris_physics: bool = True
    enable_auto_collapse: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DestructibleStats:
    """Roll-up statistics maintained across the system lifetime."""
    total_structures: int = 0
    total_materials: int = 0
    total_fractures: int = 0
    total_collapses: int = 0
    total_debris: int = 0
    intact_structures: int = 0
    damaged_structures: int = 0
    collapsing_structures: int = 0
    destroyed_structures: int = 0
    rubble_structures: int = 0
    active_debris: int = 0
    settled_debris: int = 0
    total_damage_applied: float = 0.0
    total_repair_applied: float = 0.0
    total_explosive_force: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DestructibleSnapshot:
    """A point-in-time snapshot of the full system state."""
    timestamp: str
    structures: List[Dict[str, Any]] = field(default_factory=list)
    materials: List[Dict[str, Any]] = field(default_factory=list)
    fractures: List[Dict[str, Any]] = field(default_factory=list)
    debris: List[Dict[str, Any]] = field(default_factory=list)
    collapse_events: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DestructibleEvent:
    """An internal audit event emitted by the destructible structure system."""
    event_id: str
    timestamp: str
    event_type: str
    structure_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Structure Mesh Builders
# ---------------------------------------------------------------------------

def _build_grid_mesh(
    width: int,
    height: int,
    spacing: float,
    base_pos: Tuple[float, float, float],
    material: str,
    strength: float,
    support_rows: Optional[List[int]] = None,
) -> Tuple[List[StructureNode], List[StructureEdge]]:
    """Build a rectangular grid of nodes with horizontal, vertical, and
    diagonal bracing edges.

    Args:
        width: Number of nodes along the x-axis.
        height: Number of nodes along the y-axis (vertical).
        spacing: Distance between adjacent nodes.
        base_pos: World position offset for the grid origin.
        material: Material type string for all edges.
        strength: Base strength value for all edges.
        support_rows: Y-indices whose nodes are marked as load-bearing
            supports (typically the bottom row).

    Returns:
        A tuple of (nodes, edges).
    """
    if support_rows is None:
        support_rows = [0]
    nodes: List[StructureNode] = []
    edges: List[StructureEdge] = []
    node_lookup: Dict[Tuple[int, int], str] = {}

    # Create nodes
    for j in range(height):
        for i in range(width):
            node_id = f"n_{i:03d}_{j:03d}"
            pos = (
                base_pos[0] + i * spacing,
                base_pos[1] + j * spacing,
                base_pos[2],
            )
            mass = 1.0
            is_support = j in support_rows
            node = StructureNode(
                node_id=node_id,
                position=pos,
                mass=mass,
                is_support=is_support,
            )
            nodes.append(node)
            node_lookup[(i, j)] = node_id

    edge_counter = 0

    def _make_edge(a_key: Tuple[int, int], b_key: Tuple[int, int]) -> None:
        nonlocal edge_counter
        na = node_lookup.get(a_key)
        nb = node_lookup.get(b_key)
        if na is None or nb is None:
            return
        eid = f"e_{edge_counter:04d}"
        edge_counter += 1
        rest = _vec3_distance(
            _find_node_pos(nodes, na),
            _find_node_pos(nodes, nb),
        )
        edge = StructureEdge(
            edge_id=eid,
            node_a=na,
            node_b=nb,
            strength=strength,
            material=material,
            rest_length=rest,
            current_length=rest,
            load_capacity=strength,
        )
        edges.append(edge)
        _register_connection(nodes, na, eid)
        _register_connection(nodes, nb, eid)

    # Horizontal edges
    for j in range(height):
        for i in range(width - 1):
            _make_edge((i, j), (i + 1, j))
    # Vertical edges
    for j in range(height - 1):
        for i in range(width):
            _make_edge((i, j), (i, j + 1))
    # Diagonal bracing
    for j in range(height - 1):
        for i in range(width - 1):
            _make_edge((i, j), (i + 1, j + 1))
            _make_edge((i + 1, j), (i, j + 1))

    return nodes, edges


def _find_node_pos(
    nodes: List[StructureNode], node_id: str
) -> Tuple[float, float, float]:
    """Look up a node's position by id. Returns origin if not found."""
    for n in nodes:
        if n.node_id == node_id:
            return n.position
    return (0.0, 0.0, 0.0)


def _register_connection(
    nodes: List[StructureNode], node_id: str, edge_id: str
) -> None:
    """Append an edge id to a node's connection list."""
    for n in nodes:
        if n.node_id == node_id:
            if edge_id not in n.connections:
                n.connections.append(edge_id)
            return


def _build_tower_mesh(
    material: str,
    strength: float,
    base_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> Tuple[List[StructureNode], List[StructureEdge]]:
    """Build a tower: a tall narrow grid with a wide base."""
    nodes, edges = _build_grid_mesh(
        width=3,
        height=8,
        spacing=2.5,
        base_pos=base_pos,
        material=material,
        strength=strength,
        support_rows=[0],
    )
    return nodes, edges


def _build_wall_mesh(
    material: str,
    strength: float,
    base_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> Tuple[List[StructureNode], List[StructureEdge]]:
    """Build a wall: a wide, short grid."""
    nodes, edges = _build_grid_mesh(
        width=8,
        height=4,
        spacing=2.0,
        base_pos=base_pos,
        material=material,
        strength=strength,
        support_rows=[0],
    )
    return nodes, edges


def _build_bridge_mesh(
    material: str,
    strength: float,
    base_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> Tuple[List[StructureNode], List[StructureEdge]]:
    """Build a bridge: a long, low structure with supports at both ends."""
    nodes, edges = _build_grid_mesh(
        width=10,
        height=3,
        spacing=3.0,
        base_pos=base_pos,
        material=material,
        strength=strength,
        support_rows=[0],
    )
    return nodes, edges


def _build_fortress_mesh(
    material: str,
    strength: float,
    base_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> Tuple[List[StructureNode], List[StructureEdge]]:
    """Build a fortress: a large, dense grid."""
    nodes, edges = _build_grid_mesh(
        width=6,
        height=6,
        spacing=3.0,
        base_pos=base_pos,
        material=material,
        strength=strength,
        support_rows=[0],
    )
    return nodes, edges


def _build_house_mesh(
    material: str,
    strength: float,
    base_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> Tuple[List[StructureNode], List[StructureEdge]]:
    """Build a house: a small box structure."""
    nodes, edges = _build_grid_mesh(
        width=4,
        height=4,
        spacing=2.0,
        base_pos=base_pos,
        material=material,
        strength=strength,
        support_rows=[0],
    )
    return nodes, edges


# ---------------------------------------------------------------------------
# Main System Class
# ---------------------------------------------------------------------------

class _DestructibleStructureSystem:
    """Manages real-time structural destruction for the game engine.

    The system is thread-safe and implemented as a singleton with
    double-checked locking. ``_init_lock`` guards singleton creation and
    seeding; ``_lock`` guards all mutating operations to keep internal
    dictionaries consistent.

    Usage:
        system = get_destructible_structure_system()
        ok, msg, structure = system.register_structure(
            "wall_01", "East Wall", "brick", nodes, edges, (0, 0, 0))
        ok, msg, result = system.apply_damage("wall_01", (5, 3, 0), 500, 3.0)
        summary = system.tick(0.016)
    """

    _instance: Optional["_DestructibleStructureSystem"] = None
    _init_lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        # Double-checked initialization guard so repeated construction is safe.
        if getattr(self, "_initialized", False):
            return
        with self._init_lock:
            if getattr(self, "_initialized", False):
                return

            self._lock: threading.RLock = threading.RLock()
            self._materials: Dict[str, MaterialProperties] = {}
            self._structures: Dict[str, Structure] = {}
            self._fractures: Dict[str, FractureRecord] = {}
            self._structure_fractures: Dict[str, List[str]] = {}
            self._debris: Dict[str, DebrisPiece] = {}
            self._structure_debris: Dict[str, List[str]] = {}
            self._collapse_events: Dict[str, CollapseEvent] = {}
            self._structure_collapses: Dict[str, List[str]] = {}
            self._events: List[DestructibleEvent] = []
            self._config: DestructibleConfig = DestructibleConfig()
            self._stats: DestructibleStats = DestructibleStats()
            self._tick_count: int = 0
            self._event_counter: int = 0
            self._global_time: float = 0.0
            self._total_damage_applied: float = 0.0
            self._total_repair_applied: float = 0.0
            self._total_explosive_force: float = 0.0

            self._seeded: bool = False
            self._initialized: bool = True

    # ------------------------------------------------------------------
    # Singleton lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "_DestructibleStructureSystem":
        """Return the shared singleton, creating it if needed."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Tear down the singleton so a fresh instance can be built."""
        with cls._init_lock:
            cls._instance = None

    def initialize(self) -> Tuple[bool, str]:
        """Load seed data including materials, structures, fractures, debris,
        and collapse events.

        Idempotent: calling initialize() multiple times is safe and will not
        duplicate seed entries.
        """
        if self._seeded:
            return True, "Already initialized"
        with self._lock:
            if self._seeded:
                return True, "Already initialized"
            self._load_seed_materials()
            self._load_seed_structures()
            self._load_seed_fractures()
            self._load_seed_debris()
            self._load_seed_collapse_events()
            self._seeded = True
            self._refresh_stats()
            self._emit(
                DestructibleEventKind.STRUCTURE_REGISTERED.value,
                description="System initialized with seed data",
                data={
                    "materials": len(self._materials),
                    "structures": len(self._structures),
                    "fractures": len(self._fractures),
                    "debris": len(self._debris),
                    "collapse_events": len(self._collapse_events),
                },
            )
        return True, (
            f"Initialized with {len(self._materials)} materials, "
            f"{len(self._structures)} structures, "
            f"{len(self._fractures)} fractures, "
            f"{len(self._debris)} debris pieces, "
            f"{len(self._collapse_events)} collapse events"
        )

    # ------------------------------------------------------------------
    # Seed Data Loading
    # ------------------------------------------------------------------

    def _load_seed_materials(self) -> None:
        """Load three material presets: concrete, wood, steel."""
        for mat_id, props in _MATERIAL_TYPE_PRESETS.items():
            self._materials[mat_id] = MaterialProperties(
                material_id=mat_id,
                name=props["name"],
                base_material=props["base_material"],
                yield_stress=props["yield_stress"],
                density=props["density"],
                fracture_toughness=props["fracture_toughness"],
                elastic_modulus=props["elastic_modulus"],
                brittleness=props["brittleness"],
            )

    def _load_seed_structures(self) -> None:
        """Load five seed structures: tower, wall, bridge, fortress, house."""
        # Tower guard - concrete, tall and narrow
        tower_nodes, tower_edges = _build_tower_mesh(
            material=MaterialType.CONCRETE.value,
            strength=120.0,
            base_pos=(0.0, 0.0, 0.0),
        )
        self._create_seeded_structure(
            structure_id="tower_guard",
            name="Guard Tower",
            material_type=MaterialType.CONCRETE.value,
            nodes=tower_nodes,
            edges=tower_edges,
            position=(0.0, 0.0, 0.0),
        )

        # East wall - brick, wide and short
        wall_nodes, wall_edges = _build_wall_mesh(
            material=MaterialType.BRICK.value,
            strength=90.0,
            base_pos=(0.0, 0.0, 0.0),
        )
        self._create_seeded_structure(
            structure_id="wall_east",
            name="East Wall",
            material_type=MaterialType.BRICK.value,
            nodes=wall_nodes,
            edges=wall_edges,
            position=(50.0, 0.0, 0.0),
        )

        # Stone bridge - long and low
        bridge_nodes, bridge_edges = _build_bridge_mesh(
            material=MaterialType.STONE.value,
            strength=150.0,
            base_pos=(0.0, 0.0, 0.0),
        )
        self._create_seeded_structure(
            structure_id="bridge_stone",
            name="Stone Bridge",
            material_type=MaterialType.STONE.value,
            nodes=bridge_nodes,
            edges=bridge_edges,
            position=(100.0, 0.0, 0.0),
        )

        # Main fortress - concrete, large and dense
        fortress_nodes, fortress_edges = _build_fortress_mesh(
            material=MaterialType.CONCRETE.value,
            strength=200.0,
            base_pos=(0.0, 0.0, 0.0),
        )
        self._create_seeded_structure(
            structure_id="fortress_main",
            name="Main Fortress",
            material_type=MaterialType.CONCRETE.value,
            nodes=fortress_nodes,
            edges=fortress_edges,
            position=(200.0, 0.0, 0.0),
        )

        # Wooden house - small and light
        house_nodes, house_edges = _build_house_mesh(
            material=MaterialType.WOOD.value,
            strength=60.0,
            base_pos=(0.0, 0.0, 0.0),
        )
        self._create_seeded_structure(
            structure_id="house_wood",
            name="Wooden House",
            material_type=MaterialType.WOOD.value,
            nodes=house_nodes,
            edges=house_edges,
            position=(300.0, 0.0, 0.0),
        )

    def _load_seed_fractures(self) -> None:
        """Load four seed fracture records on various structures."""
        fracture_seeds: List[Tuple[str, str, str, str, float, Tuple[float, float, float], float]] = [
            ("frac_seed_01", "wall_east", "e_0005",
             FracturePattern.SHEAR.value, 0.3, (52.0, 2.0, 0.0), 85.0),
            ("frac_seed_02", "wall_east", "e_0012",
             FracturePattern.CRUMBLE.value, 0.5, (56.0, 4.0, 0.0), 95.0),
            ("frac_seed_03", "tower_guard", "e_0008",
             FracturePattern.SPLINTER.value, 0.4, (2.0, 10.0, 0.0), 70.0),
            ("frac_seed_04", "house_wood", "e_0003",
             FracturePattern.SPLINTER.value, 0.6, (301.0, 2.0, 0.0), 55.0),
        ]
        for fid, struct_id, edge_id, pattern, severity, pos, stress in fracture_seeds:
            # Mark the corresponding edge as broken if it exists
            structure = self._structures.get(struct_id)
            if structure is not None:
                for edge in structure.edges:
                    if edge.edge_id == edge_id:
                        edge.is_broken = True
                        edge.damage = 1.0
                        break
            fracture = FractureRecord(
                fracture_id=fid,
                structure_id=struct_id,
                edge_id=edge_id,
                pattern=pattern,
                severity=severity,
                position=pos,
                stress_at_fracture=stress,
                propagated=False,
            )
            self._fractures[fid] = fracture
            self._structure_fractures.setdefault(struct_id, []).append(fid)

        # Update structure statuses based on seed fractures
        self._refresh_structure_statuses()

    def _load_seed_debris(self) -> None:
        """Load three seed debris pieces from various structures."""
        debris_seeds: List[Tuple[str, str, float, Tuple[float, float, float], Tuple[float, float, float], float, str]] = [
            ("debris_seed_01", "wall_east", 2.5,
             (53.0, 1.0, 0.0), (1.0, -2.0, 0.5), 1.2, MaterialType.BRICK.value),
            ("debris_seed_02", "tower_guard", 1.8,
             (1.0, 5.0, 0.0), (0.5, -3.0, 0.0), 0.9, MaterialType.CONCRETE.value),
            ("debris_seed_03", "house_wood", 0.8,
             (302.0, 1.0, 0.0), (2.0, -1.5, 0.3), 0.6, MaterialType.WOOD.value),
        ]
        for did, struct_id, mass, pos, vel, size, mat in debris_seeds:
            debris = DebrisPiece(
                debris_id=did,
                structure_id=struct_id,
                mass=mass,
                position=pos,
                velocity=vel,
                size=size,
                material=mat,
                status=DebrisStatus.ACTIVE.value,
            )
            self._debris[did] = debris
            self._structure_debris.setdefault(struct_id, []).append(did)

    def _load_seed_collapse_events(self) -> None:
        """Load two seed collapse events."""
        collapse_seeds: List[Tuple[str, str, str, float, float, int, int, int, bool, str]] = [
            ("collapse_seed_01", "house_wood", "damage", 1.0, 4.0,
             8, 6, 3, False, "Collapsed due to accumulated splinter fractures"),
            ("collapse_seed_02", "wall_east", "explosive", 0.7, 6.0,
             6, 5, 2, True, "Partial collapse from blast damage"),
        ]
        for (eid, struct_id, triggered_by, progress, duration,
             nodes_col, edges_broken, debris_gen, is_active, note) in collapse_seeds:
            event = CollapseEvent(
                event_id=eid,
                structure_id=struct_id,
                triggered_by=triggered_by,
                progress=progress,
                duration=duration,
                nodes_collapsed=nodes_col,
                edges_broken=edges_broken,
                debris_generated=debris_gen,
                is_active=is_active,
                completed_at="" if is_active else _now(),
                metadata={"note": note},
            )
            self._collapse_events[eid] = event
            self._structure_collapses.setdefault(struct_id, []).append(eid)

    def _create_seeded_structure(
        self,
        structure_id: str,
        name: str,
        material_type: str,
        nodes: List[StructureNode],
        edges: List[StructureEdge],
        position: Tuple[float, float, float],
    ) -> None:
        """Helper used by seed loading to build a structure instance."""
        structure = Structure(
            structure_id=structure_id,
            name=name,
            material_type=material_type,
            nodes=list(nodes),
            edges=list(edges),
            position=position,
            status=StructureStatus.INTACT.value,
            integrity=1.0,
            max_integrity=1.0,
            original_edge_count=len(edges),
            original_node_count=len(nodes),
            bounding_radius=self._compute_bounding_radius(nodes),
        )
        self._structures[structure_id] = structure

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        structure_id: str = "",
        description: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a new audit event to the event log."""
        self._event_counter += 1
        event = DestructibleEvent(
            event_id=f"dsevt_{self._event_counter:08d}",
            timestamp=_now(),
            event_type=event_type,
            structure_id=structure_id,
            description=description,
            metadata=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, self._config.max_events)

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from current state."""
        self._stats.total_structures = len(self._structures)
        self._stats.total_materials = len(self._materials)
        self._stats.total_fractures = len(self._fractures)
        self._stats.total_collapses = len(self._collapse_events)
        self._stats.total_debris = len(self._debris)
        self._stats.intact_structures = sum(
            1 for s in self._structures.values()
            if s.status == StructureStatus.INTACT.value
        )
        self._stats.damaged_structures = sum(
            1 for s in self._structures.values()
            if s.status == StructureStatus.DAMAGED.value
        )
        self._stats.collapsing_structures = sum(
            1 for s in self._structures.values()
            if s.status == StructureStatus.COLLAPSING.value
        )
        self._stats.destroyed_structures = sum(
            1 for s in self._structures.values()
            if s.status == StructureStatus.DESTROYED.value
        )
        self._stats.rubble_structures = sum(
            1 for s in self._structures.values()
            if s.status == StructureStatus.RUBBLE.value
        )
        self._stats.active_debris = sum(
            1 for d in self._debris.values()
            if d.status == DebrisStatus.ACTIVE.value
        )
        self._stats.settled_debris = sum(
            1 for d in self._debris.values()
            if d.status == DebrisStatus.SETTLED.value
        )
        self._stats.total_damage_applied = self._total_damage_applied
        self._stats.total_repair_applied = self._total_repair_applied
        self._stats.total_explosive_force = self._total_explosive_force
        self._stats.tick_count = self._tick_count

    def _refresh_structure_statuses(self) -> None:
        """Update each structure's status based on its integrity and damage."""
        for structure in self._structures.values():
            self._update_structure_status(structure)

    def _update_structure_status(self, structure: Structure) -> None:
        """Set a structure's status from its current integrity value."""
        if structure.status == StructureStatus.RUBBLE.value:
            return
        if structure.status == StructureStatus.COLLAPSING.value:
            if structure.collapse_progress >= 1.0:
                structure.status = StructureStatus.DESTROYED.value
            return
        integrity = structure.integrity
        if integrity >= 0.999:
            if structure.status != StructureStatus.INTACT.value:
                structure.status = StructureStatus.INTACT.value
        elif integrity >= self._config.collapse_threshold:
            structure.status = StructureStatus.DAMAGED.value
        elif integrity > 0.01:
            if self._config.enable_auto_collapse:
                structure.status = StructureStatus.COLLAPSING.value
            else:
                structure.status = StructureStatus.DAMAGED.value
        else:
            structure.status = StructureStatus.DESTROYED.value
        structure.updated_at = _now()

    def _compute_bounding_radius(self, nodes: List[StructureNode]) -> float:
        """Compute the bounding radius of a set of nodes from their centroid."""
        if not nodes:
            return 0.0
        cx = sum(n.position[0] for n in nodes) / len(nodes)
        cy = sum(n.position[1] for n in nodes) / len(nodes)
        cz = sum(n.position[2] for n in nodes) / len(nodes)
        max_dist = 0.0
        for n in nodes:
            dist = _vec3_distance(n.position, (cx, cy, cz))
            if dist > max_dist:
                max_dist = dist
        return max_dist + _EPSILON

    def _get_node(
        self, structure: Structure, node_id: str
    ) -> Optional[StructureNode]:
        """Find a node by id within a structure."""
        for n in structure.nodes:
            if n.node_id == node_id:
                return n
        return None

    def _get_edge(
        self, structure: Structure, edge_id: str
    ) -> Optional[StructureEdge]:
        """Find an edge by id within a structure."""
        for e in structure.edges:
            if e.edge_id == edge_id:
                return e
        return None

    def _compute_structure_integrity(self, structure: Structure) -> float:
        """Compute overall structural integrity from intact edge ratio.

        Integrity is the ratio of intact (unbroken) edges to the original
        edge count, weighted by the average remaining strength of intact
        edges.
        """
        if structure.original_edge_count <= 0:
            return 1.0
        intact_edges = [e for e in structure.edges if not e.is_broken]
        if not intact_edges:
            return 0.0
        # Ratio of surviving edges to original count
        edge_ratio = len(intact_edges) / float(structure.original_edge_count)
        # Average remaining strength factor (1 - damage)
        avg_strength = sum(
            (1.0 - _clamp(e.damage)) for e in intact_edges
        ) / len(intact_edges)
        integrity = edge_ratio * avg_strength
        return _clamp(integrity, 0.0, 1.0)

    def _find_nodes_in_radius(
        self,
        structure: Structure,
        center: Tuple[float, float, float],
        radius: float,
    ) -> List[StructureNode]:
        """Return all nodes of a structure within a given radius of center."""
        result: List[StructureNode] = []
        r_sq = radius * radius
        for node in structure.nodes:
            if node.is_broken:
                continue
            dx = node.position[0] - center[0]
            dy = node.position[1] - center[1]
            dz = node.position[2] - center[2]
            if dx * dx + dy * dy + dz * dz <= r_sq:
                result.append(node)
        return result

    def _find_edges_for_nodes(
        self,
        structure: Structure,
        node_ids: List[str],
    ) -> List[StructureEdge]:
        """Return all edges connected to any of the given node ids."""
        node_set = set(node_ids)
        result: List[StructureEdge] = []
        for edge in structure.edges:
            if edge.is_broken:
                continue
            if edge.node_a in node_set or edge.node_b in node_set:
                result.append(edge)
        return result

    def _apply_stress_to_edge(
        self,
        edge: StructureEdge,
        stress: float,
        material: Optional[MaterialProperties] = None,
    ) -> bool:
        """Apply stress to an edge. Returns True if the edge broke.

        The edge accumulates damage proportional to stress beyond its
        yield point. When damage exceeds 1.0, the edge is marked broken.
        """
        if edge.is_broken:
            return False
        edge.stress += stress
        yield_point = edge.strength
        if material is not None:
            yield_point = material.yield_stress * edge.strength / 100.0
        if edge.stress > yield_point:
            excess = edge.stress - yield_point
            damage_increment = excess / max(yield_point, _EPSILON)
            edge.damage = _clamp(edge.damage + damage_increment * 0.5)
            if edge.damage >= 1.0:
                edge.is_broken = True
                edge.damage = 1.0
                return True
        # Compute strain based on stress and elastic modulus
        modulus = material.elastic_modulus if material else 30.0
        edge.strain = edge.stress / max(modulus * 100.0, _EPSILON)
        edge.current_length = edge.rest_length * (1.0 + edge.strain)
        return False

    def _create_fracture_internal(
        self,
        structure: Structure,
        edge: StructureEdge,
        pattern: str,
        severity: float,
        stress: float,
    ) -> FractureRecord:
        """Create and store a FractureRecord for a broken edge."""
        fracture_id = _new_id("frac")
        node_a = self._get_node(structure, edge.node_a)
        pos = node_a.position if node_a else structure.position
        fracture = FractureRecord(
            fracture_id=fracture_id,
            structure_id=structure.structure_id,
            edge_id=edge.edge_id,
            pattern=pattern,
            severity=_clamp(severity),
            position=pos,
            stress_at_fracture=stress,
        )
        self._fractures[fracture_id] = fracture
        self._structure_fractures.setdefault(
            structure.structure_id, []
        ).append(fracture_id)
        _evict_fifo_dict(self._fractures, self._config.max_fractures)
        return fracture

    def _spawn_debris_from_edge(
        self,
        structure: Structure,
        edge: StructureEdge,
        pattern: str,
    ) -> Optional[DebrisPiece]:
        """Spawn a debris piece from a broken edge."""
        if not self._config.enable_debris_physics:
            return None
        node_a = self._get_node(structure, edge.node_a)
        node_b = self._get_node(structure, edge.node_b)
        if node_a is None or node_b is None:
            return None
        midpoint = (
            (node_a.position[0] + node_b.position[0]) * 0.5,
            (node_a.position[1] + node_b.position[1]) * 0.5,
            (node_a.position[2] + node_b.position[2]) * 0.5,
        )
        mass = (node_a.mass + node_b.mass) * 0.5
        # Initial velocity: upward and outward based on fracture pattern
        upward = 2.0
        outward = 1.0
        if pattern == FracturePattern.EXPLOSIVE.value:
            upward = 5.0
            outward = 4.0
        elif pattern == FracturePattern.SHATTER.value:
            upward = 3.0
            outward = 3.0
        elif pattern == FracturePattern.CRUMBLE.value:
            upward = 0.5
            outward = 0.5
        velocity = (
            outward * (0.5 - (hash(edge.edge_id) % 100) / 100.0),
            upward,
            outward * (0.5 - (hash(edge.edge_id) % 97) / 100.0),
        )
        debris_id = _new_id("debris")
        debris = DebrisPiece(
            debris_id=debris_id,
            structure_id=structure.structure_id,
            mass=mass,
            position=midpoint,
            velocity=velocity,
            size=edge.rest_length * 0.5,
            material=edge.material,
            status=DebrisStatus.ACTIVE.value,
        )
        self._debris[debris_id] = debris
        self._structure_debris.setdefault(
            structure.structure_id, []
        ).append(debris_id)
        _evict_fifo_dict(self._debris, self._config.max_debris)
        return debris

    def _check_support_connectivity(
        self, structure: Structure
    ) -> Tuple[bool, List[str]]:
        """Check if all non-support nodes have a path to a support node.

        Uses BFS from all support nodes through intact edges. Returns
        (is_fully_supported, list of unsupported node ids).
        """
        support_nodes = [
            n.node_id for n in structure.nodes if n.is_support and not n.is_broken
        ]
        if not support_nodes:
            return False, [n.node_id for n in structure.nodes if not n.is_broken]

        # Build adjacency list from intact edges
        adjacency: Dict[str, List[str]] = {}
        for edge in structure.edges:
            if edge.is_broken:
                continue
            adjacency.setdefault(edge.node_a, []).append(edge.node_b)
            adjacency.setdefault(edge.node_b, []).append(edge.node_a)

        # BFS from all supports
        visited: set = set(support_nodes)
        queue: List[str] = list(support_nodes)
        while queue:
            current = queue.pop(0)
            for neighbor in adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        unsupported: List[str] = []
        for node in structure.nodes:
            if node.is_broken:
                continue
            if node.node_id not in visited:
                unsupported.append(node.node_id)
        return len(unsupported) == 0, unsupported

    def _get_material_for_structure(
        self, structure: Structure
    ) -> Optional[MaterialProperties]:
        """Find the best matching material properties for a structure."""
        for mat in self._materials.values():
            if mat.base_material == structure.material_type:
                return mat
        return None

    def _pick_fracture_pattern(
        self, material: str, force: float
    ) -> str:
        """Deterministically select a fracture pattern from material and force."""
        if material == MaterialType.GLASS.value:
            return FracturePattern.SHATTER.value
        if material == MaterialType.WOOD.value:
            return FracturePattern.SPLINTER.value
        if material == MaterialType.STONE.value:
            return FracturePattern.CRUMBLE.value
        if material == MaterialType.STEEL.value:
            return FracturePattern.SHEAR.value
        if force > 500.0:
            return FracturePattern.EXPLOSIVE.value
        return FracturePattern.SHEAR.value

    # ------------------------------------------------------------------
    # Structure Management (8 methods)
    # ------------------------------------------------------------------

    def register_structure(
        self,
        structure_id: str,
        name: str,
        material_type: str,
        nodes: Optional[List[StructureNode]] = None,
        edges: Optional[List[StructureEdge]] = None,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Structure]]:
        """Register a new destructible structure with a node-edge mesh."""
        with self._lock:
            if structure_id in self._structures:
                return False, "already_exists", None
            mat = _coerce_enum(MaterialType, material_type, MaterialType.CONCRETE).value
            node_list: List[StructureNode] = []
            if nodes is not None:
                for n in nodes:
                    if isinstance(n, StructureNode):
                        node_list.append(StructureNode(
                            node_id=n.node_id,
                            position=tuple(n.position),
                            mass=max(0.01, _safe_float(n.mass, 1.0)),
                            connections=list(n.connections),
                            stress=_safe_float(n.stress, 0.0),
                            displacement=tuple(n.displacement),
                            velocity=tuple(n.velocity),
                            is_support=bool(n.is_support),
                            is_broken=bool(n.is_broken),
                            load=_safe_float(n.load, 0.0),
                            metadata=dict(n.metadata),
                        ))
                    elif isinstance(n, dict):
                        node_list.append(StructureNode(
                            node_id=str(n.get("node_id", _new_id("n"))),
                            position=tuple(n.get("position", (0.0, 0.0, 0.0))),
                            mass=max(0.01, _safe_float(n.get("mass"), 1.0)),
                            connections=list(n.get("connections", [])),
                            stress=_safe_float(n.get("stress"), 0.0),
                            is_support=bool(n.get("is_support", False)),
                            is_broken=bool(n.get("is_broken", False)),
                            load=_safe_float(n.get("load"), 0.0),
                        ))
            edge_list: List[StructureEdge] = []
            if edges is not None:
                for e in edges:
                    if isinstance(e, StructureEdge):
                        rest = max(_EPSILON, _safe_float(e.rest_length, 1.0))
                        edge_list.append(StructureEdge(
                            edge_id=e.edge_id,
                            node_a=e.node_a,
                            node_b=e.node_b,
                            strength=max(0.0, _safe_float(e.strength, 100.0)),
                            material=e.material or mat,
                            rest_length=rest,
                            current_length=rest,
                            stress=_safe_float(e.stress, 0.0),
                            strain=_safe_float(e.strain, 0.0),
                            is_broken=bool(e.is_broken),
                            load_capacity=max(0.0, _safe_float(e.load_capacity, e.strength)),
                            damage=_clamp(_safe_float(e.damage, 0.0)),
                            metadata=dict(e.metadata),
                        ))
                    elif isinstance(e, dict):
                        strength_val = max(0.0, _safe_float(e.get("strength"), 100.0))
                        rest = max(_EPSILON, _safe_float(e.get("rest_length"), 1.0))
                        edge_list.append(StructureEdge(
                            edge_id=str(e.get("edge_id", _new_id("e"))),
                            node_a=str(e.get("node_a", "")),
                            node_b=str(e.get("node_b", "")),
                            strength=strength_val,
                            material=str(e.get("material", mat)),
                            rest_length=rest,
                            current_length=rest,
                            is_broken=bool(e.get("is_broken", False)),
                            load_capacity=max(0.0, _safe_float(e.get("load_capacity"), strength_val)),
                        ))
            bounding = self._compute_bounding_radius(node_list) if node_list else 10.0
            structure = Structure(
                structure_id=structure_id,
                name=name,
                material_type=mat,
                nodes=node_list,
                edges=edge_list,
                position=tuple(position),
                status=StructureStatus.INTACT.value,
                integrity=1.0,
                max_integrity=1.0,
                original_edge_count=len(edge_list),
                original_node_count=len(node_list),
                bounding_radius=bounding,
                metadata=dict(metadata) if metadata else {},
            )
            self._structures[structure_id] = structure
            _evict_fifo_dict(self._structures, self._config.max_structures)
            self._refresh_stats()
            self._emit(
                DestructibleEventKind.STRUCTURE_REGISTERED.value,
                structure_id=structure_id,
                description=f"Structure registered: {name}",
                data={
                    "material_type": mat,
                    "node_count": len(node_list),
                    "edge_count": len(edge_list),
                },
            )
            return True, "registered", structure

    def get_structure(self, structure_id: str) -> Optional[Structure]:
        """Return a structure by id, or None if it does not exist."""
        return self._structures.get(structure_id)

    def list_structures(
        self,
        status: Optional[str] = None,
        material_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Structure]:
        """List structures, optionally filtered by status or material type."""
        cap = max(1, _safe_int(limit, 100))
        result: List[Structure] = []
        status_filter = None
        if status is not None:
            status_filter = _coerce_enum(StructureStatus, status)
            status_filter = status_filter.value if status_filter else str(status).lower()
        mat_filter = None
        if material_type is not None:
            mat_filter = _coerce_enum(MaterialType, material_type)
            mat_filter = mat_filter.value if mat_filter else str(material_type).lower()
        for structure in self._structures.values():
            if status_filter is not None and structure.status != status_filter:
                continue
            if mat_filter is not None and structure.material_type != mat_filter:
                continue
            result.append(structure)
            if len(result) >= cap:
                break
        return result

    def remove_structure(self, structure_id: str) -> Tuple[bool, str]:
        """Remove a structure and all associated fractures, debris, and events."""
        with self._lock:
            if structure_id not in self._structures:
                return False, "not_found"
            del self._structures[structure_id]
            # Remove associated fractures
            frac_ids = self._structure_fractures.pop(structure_id, [])
            for fid in frac_ids:
                self._fractures.pop(fid, None)
            # Remove associated debris
            debris_ids = self._structure_debris.pop(structure_id, [])
            for did in debris_ids:
                self._debris.pop(did, None)
            # Remove associated collapse events
            coll_ids = self._structure_collapses.pop(structure_id, [])
            for cid in coll_ids:
                self._collapse_events.pop(cid, None)
            self._refresh_stats()
            self._emit(
                DestructibleEventKind.STRUCTURE_REMOVED.value,
                structure_id=structure_id,
                description=f"Structure removed: {structure_id}",
            )
            return True, "removed"

    def register_material_type(
        self,
        type_id: str,
        name: str,
        base_material: str,
        yield_stress: float = 30.0,
        density: float = 2400.0,
        fracture_toughness: float = 1.0,
        elastic_modulus: float = 30.0,
        brittleness: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[MaterialProperties]]:
        """Register a new material type with physical properties."""
        with self._lock:
            if type_id in self._materials:
                return False, "already_exists", None
            base = _coerce_enum(MaterialType, base_material, MaterialType.CONCRETE).value
            material = MaterialProperties(
                material_id=type_id,
                name=name,
                base_material=base,
                yield_stress=max(0.0, _safe_float(yield_stress, 30.0)),
                density=max(0.01, _safe_float(density, 2400.0)),
                fracture_toughness=max(0.01, _safe_float(fracture_toughness, 1.0)),
                elastic_modulus=max(0.01, _safe_float(elastic_modulus, 30.0)),
                brittleness=_clamp(_safe_float(brittleness, 0.5)),
                metadata=dict(metadata) if metadata else {},
            )
            self._materials[type_id] = material
            _evict_fifo_dict(self._materials, self._config.max_materials)
            self._refresh_stats()
            self._emit(
                DestructibleEventKind.MATERIAL_REGISTERED.value,
                description=f"Material registered: {name}",
                data={"material_id": type_id, "base_material": base},
            )
            return True, "registered", material

    def get_material_type(self, type_id: str) -> Optional[MaterialProperties]:
        """Return a material type by id, or None if it does not exist."""
        return self._materials.get(type_id)

    def list_material_types(
        self,
        base_material: Optional[str] = None,
        limit: int = 100,
    ) -> List[MaterialProperties]:
        """List material types, optionally filtered by base material."""
        cap = max(1, _safe_int(limit, 100))
        result: List[MaterialProperties] = []
        mat_filter = None
        if base_material is not None:
            mat_filter = _coerce_enum(MaterialType, base_material)
            mat_filter = mat_filter.value if mat_filter else str(base_material).lower()
        for material in self._materials.values():
            if mat_filter is not None and material.base_material != mat_filter:
                continue
            result.append(material)
            if len(result) >= cap:
                break
        return result

    def remove_material_type(self, type_id: str) -> Tuple[bool, str]:
        """Remove a material type by id."""
        with self._lock:
            if type_id not in self._materials:
                return False, "not_found"
            del self._materials[type_id]
            self._refresh_stats()
            self._emit(
                DestructibleEventKind.MATERIAL_REMOVED.value,
                description=f"Material removed: {type_id}",
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Damage and Fracture (10 methods)
    # ------------------------------------------------------------------

    def apply_damage(
        self,
        structure_id: str,
        impact_point: Tuple[float, float, float],
        force: float,
        radius: float,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Apply impact damage to all nodes within a radius of the impact point.

        Stress is distributed to connected edges based on proximity. Edges
        that exceed their yield stress accumulate damage and may fracture.
        The structure integrity is recomputed after damage application.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            if structure.status in (
                StructureStatus.DESTROYED.value,
                StructureStatus.RUBBLE.value,
            ):
                return False, "structure_already_destroyed", None
            material = self._get_material_for_structure(structure)
            force_val = max(0.0, _safe_float(force, 0.0))
            radius_val = max(0.01, _safe_float(radius, 1.0))
            impact = tuple(impact_point)

            affected_nodes = self._find_nodes_in_radius(structure, impact, radius_val)
            if not affected_nodes:
                return True, "no_nodes_in_radius", {
                    "structure_id": structure_id,
                    "affected_nodes": 0,
                    "fractures_created": 0,
                    "integrity": structure.integrity,
                }

            fractures_created: List[str] = []
            edges_affected: List[str] = []
            total_stress_applied: float = 0.0

            affected_node_ids = [n.node_id for n in affected_nodes]
            affected_edges = self._find_edges_for_nodes(structure, affected_node_ids)

            for node in affected_nodes:
                dist = _vec3_distance(node.position, impact)
                # Stress falls off linearly with distance from impact
                falloff = max(0.0, 1.0 - (dist / radius_val))
                stress = force_val * falloff
                node.stress += stress
                node.load += stress
                total_stress_applied += stress

            for edge in affected_edges:
                dist_a = _vec3_distance(
                    self._get_node(structure, edge.node_a).position if self._get_node(structure, edge.node_a) else impact,
                    impact,
                )
                dist_b = _vec3_distance(
                    self._get_node(structure, edge.node_b).position if self._get_node(structure, edge.node_b) else impact,
                    impact,
                )
                avg_dist = (dist_a + dist_b) * 0.5
                falloff = max(0.0, 1.0 - (avg_dist / radius_val))
                stress = force_val * falloff * 0.5
                broke = self._apply_stress_to_edge(edge, stress, material)
                edges_affected.append(edge.edge_id)
                if broke:
                    pattern = self._pick_fracture_pattern(
                        structure.material_type, force_val
                    )
                    fracture = self._create_fracture_internal(
                        structure, edge, pattern, _clamp(stress / max(edge.strength, _EPSILON)), stress
                    )
                    fractures_created.append(fracture.fracture_id)
                    self._spawn_debris_from_edge(structure, edge, pattern)
                    self._emit(
                        DestructibleEventKind.FRACTURE_CREATED.value,
                        structure_id=structure_id,
                        description=f"Edge {edge.edge_id} fractured via impact",
                        data={
                            "fracture_id": fracture.fracture_id,
                            "pattern": pattern,
                            "stress": stress,
                        },
                    )

            structure.damage_accumulated += total_stress_applied
            self._total_damage_applied += total_stress_applied
            structure.integrity = self._compute_structure_integrity(structure)
            self._update_structure_status(structure)
            structure.updated_at = _now()

            result = {
                "structure_id": structure_id,
                "affected_nodes": len(affected_nodes),
                "edges_affected": len(edges_affected),
                "fractures_created": len(fractures_created),
                "fracture_ids": fractures_created,
                "total_stress_applied": total_stress_applied,
                "integrity": structure.integrity,
                "status": structure.status,
            }
            self._emit(
                DestructibleEventKind.DAMAGE_APPLIED.value,
                structure_id=structure_id,
                description=f"Damage applied: force={force_val}, radius={radius_val}",
                data=result,
            )
            self._refresh_stats()
            # Check for auto-collapse trigger
            if (self._config.enable_auto_collapse
                    and structure.status == StructureStatus.COLLAPSING.value
                    and structure.collapse_progress == 0.0):
                self._trigger_collapse_internal(structure, "damage")
            return True, "damage_applied", result

    def apply_explosive(
        self,
        structure_id: str,
        center: Tuple[float, float, float],
        blast_force: float,
        radius: float,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Apply explosive blast damage with quadratic falloff from center.

        The blast affects all nodes within the radius, with stress decreasing
        quadratically with distance. Multiple fractures are typically created
        and the structure may immediately begin collapsing.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            if structure.status in (
                StructureStatus.DESTROYED.value,
                StructureStatus.RUBBLE.value,
            ):
                return False, "structure_already_destroyed", None
            material = self._get_material_for_structure(structure)
            blast = max(0.0, _safe_float(blast_force, 0.0))
            radius_val = max(0.01, _safe_float(radius, 1.0))
            center_pt = tuple(center)

            affected_nodes = self._find_nodes_in_radius(structure, center_pt, radius_val)
            if not affected_nodes:
                return True, "no_nodes_in_radius", {
                    "structure_id": structure_id,
                    "affected_nodes": 0,
                    "fractures_created": 0,
                    "integrity": structure.integrity,
                }

            fractures_created: List[str] = []
            total_stress_applied: float = 0.0
            affected_node_ids = [n.node_id for n in affected_nodes]
            affected_edges = self._find_edges_for_nodes(structure, affected_node_ids)

            for node in affected_nodes:
                dist = _vec3_distance(node.position, center_pt)
                # Quadratic falloff for explosive blast
                normalized_dist = dist / radius_val
                falloff = max(0.0, 1.0 - normalized_dist ** _BLAST_FALLOFF)
                stress = blast * falloff
                node.stress += stress
                node.load += stress
                total_stress_applied += stress

            for edge in affected_edges:
                node_a = self._get_node(structure, edge.node_a)
                node_b = self._get_node(structure, edge.node_b)
                if node_a is None or node_b is None:
                    continue
                dist_a = _vec3_distance(node_a.position, center_pt)
                dist_b = _vec3_distance(node_b.position, center_pt)
                avg_dist = (dist_a + dist_b) * 0.5
                normalized_dist = avg_dist / radius_val
                falloff = max(0.0, 1.0 - normalized_dist ** _BLAST_FALLOFF)
                stress = blast * falloff * 0.7
                broke = self._apply_stress_to_edge(edge, stress, material)
                if broke:
                    fracture = self._create_fracture_internal(
                        structure, edge,
                        FracturePattern.EXPLOSIVE.value,
                        _clamp(stress / max(edge.strength, _EPSILON)),
                        stress,
                    )
                    fractures_created.append(fracture.fracture_id)
                    self._spawn_debris_from_edge(
                        structure, edge, FracturePattern.EXPLOSIVE.value
                    )

            structure.damage_accumulated += total_stress_applied
            self._total_damage_applied += total_stress_applied
            self._total_explosive_force += blast
            structure.integrity = self._compute_structure_integrity(structure)
            self._update_structure_status(structure)
            structure.updated_at = _now()

            result = {
                "structure_id": structure_id,
                "affected_nodes": len(affected_nodes),
                "edges_affected": len(affected_edges),
                "fractures_created": len(fractures_created),
                "fracture_ids": fractures_created,
                "total_stress_applied": total_stress_applied,
                "blast_force": blast,
                "integrity": structure.integrity,
                "status": structure.status,
            }
            self._emit(
                DestructibleEventKind.EXPLOSIVE_DETONATED.value,
                structure_id=structure_id,
                description=f"Explosive detonated: force={blast}, radius={radius_val}",
                data=result,
            )
            self._refresh_stats()
            # Explosions frequently trigger immediate collapse
            if (self._config.enable_auto_collapse
                    and structure.status == StructureStatus.COLLAPSING.value
                    and structure.collapse_progress == 0.0):
                self._trigger_collapse_internal(structure, "explosive")
            return True, "explosive_detonated", result

    def create_fracture(
        self,
        structure_id: str,
        edge_id: str,
        pattern: str,
        severity: float = 0.5,
    ) -> Tuple[bool, str, Optional[FractureRecord]]:
        """Explicitly create a fracture on a specific edge of a structure."""
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            edge = self._get_edge(structure, edge_id)
            if edge is None:
                return False, "edge_not_found", None
            if edge.is_broken:
                return False, "edge_already_broken", None
            pat = _coerce_enum(FracturePattern, pattern, FracturePattern.SHEAR).value
            sev = _clamp(_safe_float(severity, 0.5))
            edge.is_broken = True
            edge.damage = 1.0
            edge.stress = edge.strength * (1.0 + sev)
            fracture = self._create_fracture_internal(
                structure, edge, pat, sev, edge.stress
            )
            structure.integrity = self._compute_structure_integrity(structure)
            self._update_structure_status(structure)
            structure.updated_at = _now()
            self._spawn_debris_from_edge(structure, edge, pat)
            self._emit(
                DestructibleEventKind.FRACTURE_CREATED.value,
                structure_id=structure_id,
                description=f"Fracture created on edge {edge_id}",
                data={
                    "fracture_id": fracture.fracture_id,
                    "pattern": pat,
                    "severity": sev,
                },
            )
            self._refresh_stats()
            return True, "fracture_created", fracture

    def propagate_fracture(
        self,
        structure_id: str,
        fracture_id: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Propagate a fracture to neighboring edges via stress redistribution.

        When an edge breaks, the load it was carrying is redistributed to
        adjacent edges. This can cause a chain reaction where neighboring
        edges also fracture if the redistributed stress exceeds their yield
        point.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            fracture = self._fractures.get(fracture_id)
            if fracture is None:
                return False, "fracture_not_found", None
            if fracture.structure_id != structure_id:
                return False, "fracture_belongs_to_different_structure", None
            if fracture.propagated:
                return True, "already_propagated", {
                    "fracture_id": fracture_id,
                    "propagated_to": fracture.propagated_to,
                    "new_fractures": 0,
                }

            source_edge = self._get_edge(structure, fracture.edge_id)
            if source_edge is None:
                return False, "source_edge_not_found", None

            material = self._get_material_for_structure(structure)
            # Find edges connected to the same nodes as the source edge
            node_ids = [source_edge.node_a, source_edge.node_b]
            neighbor_edges = self._find_edges_for_nodes(structure, node_ids)
            # Exclude the already-broken source edge
            neighbor_edges = [
                e for e in neighbor_edges
                if e.edge_id != source_edge.edge_id and not e.is_broken
            ]

            new_fractures: List[str] = []
            redistributed_stress = source_edge.stress * self._config.fracture_propagation_rate
            stress_per_edge = redistributed_stress / max(len(neighbor_edges), 1)

            for neighbor in neighbor_edges:
                broke = self._apply_stress_to_edge(
                    neighbor, stress_per_edge, material
                )
                if broke:
                    pattern = self._pick_fracture_pattern(
                        structure.material_type, stress_per_edge
                    )
                    new_frac = self._create_fracture_internal(
                        structure, neighbor, pattern,
                        _clamp(stress_per_edge / max(neighbor.strength, _EPSILON)),
                        stress_per_edge,
                    )
                    new_fractures.append(new_frac.fracture_id)
                    fracture.propagated_to.append(neighbor.edge_id)
                    self._spawn_debris_from_edge(structure, neighbor, pattern)

            fracture.propagated = True
            structure.integrity = self._compute_structure_integrity(structure)
            self._update_structure_status(structure)
            structure.updated_at = _now()

            result = {
                "fracture_id": fracture_id,
                "propagated_to": fracture.propagated_to,
                "new_fractures": len(new_fractures),
                "new_fracture_ids": new_fractures,
                "redistributed_stress": redistributed_stress,
                "integrity": structure.integrity,
                "status": structure.status,
            }
            self._emit(
                DestructibleEventKind.FRACTURE_PROPAGATED.value,
                structure_id=structure_id,
                description=f"Fracture {fracture_id} propagated to {len(new_fractures)} neighbors",
                data=result,
            )
            self._refresh_stats()
            # Chain reaction: propagate new fractures if enabled
            if (self._config.enable_chain_reactions and new_fractures
                    and structure.integrity > 0.05):
                for nfid in new_fractures[:3]:  # Limit chain depth
                    self.propagate_fracture(structure_id, nfid)
            return True, "propagated", result

    def check_structural_integrity(
        self,
        structure_id: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Compute and return the structural integrity assessment.

        Evaluates edge ratio, support connectivity, and identifies
        unsupported nodes that are at risk of collapsing.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            integrity = self._compute_structure_integrity(structure)
            structure.integrity = integrity
            is_supported, unsupported = self._check_support_connectivity(structure)
            broken_edges = sum(1 for e in structure.edges if e.is_broken)
            broken_nodes = sum(1 for n in structure.nodes if n.is_broken)
            intact_edges = len(structure.edges) - broken_edges
            result = {
                "structure_id": structure_id,
                "integrity": integrity,
                "status": structure.status,
                "total_edges": len(structure.edges),
                "intact_edges": intact_edges,
                "broken_edges": broken_edges,
                "broken_nodes": broken_nodes,
                "is_fully_supported": is_supported,
                "unsupported_nodes": unsupported,
                "original_edge_count": structure.original_edge_count,
                "edge_survival_ratio": (
                    intact_edges / max(structure.original_edge_count, 1)
                ),
            }
            self._update_structure_status(structure)
            return True, "checked", result

    def compute_load_distribution(
        self,
        structure_id: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Compute how load flows through the structure to support nodes.

        Each node's load is the sum of stress from connected intact edges.
        Support nodes carry the accumulated load of the structure above them.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None

            node_loads: Dict[str, float] = {}
            edge_loads: Dict[str, float] = {}
            for node in structure.nodes:
                node_loads[node.node_id] = 0.0
            for edge in structure.edges:
                edge_loads[edge.edge_id] = 0.0

            # Accumulate edge stress into node loads
            for edge in structure.edges:
                if edge.is_broken:
                    continue
                edge_loads[edge.edge_id] = edge.stress
                node_loads[edge.node_a] = node_loads.get(edge.node_a, 0.0) + edge.stress * 0.5
                node_loads[edge.node_b] = node_loads.get(edge.node_b, 0.0) + edge.stress * 0.5

            # Propagate loads downward: each node transfers load to its
            # neighbors that are closer to a support node (lower y position)
            for node in sorted(
                structure.nodes,
                key=lambda n: -n.position[1],  # Top to bottom
            ):
                if node.is_broken:
                    continue
                load = node_loads.get(node.node_id, 0.0)
                if load <= 0:
                    continue
                # Find connected nodes below this one
                below_neighbors: List[str] = []
                for edge in structure.edges:
                    if edge.is_broken:
                        continue
                    other = None
                    if edge.node_a == node.node_id:
                        other = edge.node_b
                    elif edge.node_b == node.node_id:
                        other = edge.node_a
                    if other is not None:
                        other_node = self._get_node(structure, other)
                        if other_node and other_node.position[1] < node.position[1]:
                            below_neighbors.append(other)
                if below_neighbors:
                    share = load / len(below_neighbors)
                    for nid in below_neighbors:
                        node_loads[nid] = node_loads.get(nid, 0.0) + share
                    # Update node load field
                    node.load = node_loads.get(node.node_id, 0.0)

            support_load = sum(
                node_loads.get(n.node_id, 0.0)
                for n in structure.nodes if n.is_support
            )
            max_node_load = max(node_loads.values()) if node_loads else 0.0
            max_edge_load = max(edge_loads.values()) if edge_loads else 0.0
            result = {
                "structure_id": structure_id,
                "node_loads": node_loads,
                "edge_loads": edge_loads,
                "total_support_load": support_load,
                "max_node_load": max_node_load,
                "max_edge_load": max_edge_load,
                "node_count": len(node_loads),
                "edge_count": len(edge_loads),
            }
            return True, "computed", result

    def get_stress_map(
        self,
        structure_id: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Return a per-node and per-edge stress map for visualization.

        Each entry contains the stress value normalized to 0-1 range
        relative to the maximum stress in the structure.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            node_stresses: Dict[str, float] = {}
            edge_stresses: Dict[str, float] = {}
            max_stress = _EPSILON
            for node in structure.nodes:
                node_stresses[node.node_id] = node.stress
                if node.stress > max_stress:
                    max_stress = node.stress
            for edge in structure.edges:
                edge_stresses[edge.edge_id] = edge.stress
                if edge.stress > max_stress:
                    max_stress = edge.stress
            # Normalize to 0-1
            normalized_nodes = {
                nid: _clamp(s / max_stress) for nid, s in node_stresses.items()
            }
            normalized_edges = {
                eid: _clamp(s / max_stress) for eid, s in edge_stresses.items()
            }
            result = {
                "structure_id": structure_id,
                "node_stress": node_stresses,
                "edge_stress": edge_stresses,
                "normalized_node_stress": normalized_nodes,
                "normalized_edge_stress": normalized_edges,
                "max_stress": max_stress,
                "hot_nodes": [
                    nid for nid, s in normalized_nodes.items() if s > 0.7
                ],
                "hot_edges": [
                    eid for eid, s in normalized_edges.items() if s > 0.7
                ],
            }
            return True, "computed", result

    def assess_damage(
        self,
        structure_id: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Provide a comprehensive damage assessment for a structure.

        Combines integrity, fracture count, broken element counts, support
        connectivity, and recommendations into a single summary.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            integrity = self._compute_structure_integrity(structure)
            structure.integrity = integrity
            is_supported, unsupported = self._check_support_connectivity(structure)
            fracture_ids = self._structure_fractures.get(structure_id, [])
            broken_edges = sum(1 for e in structure.edges if e.is_broken)
            broken_nodes = sum(1 for n in structure.nodes if n.is_broken)
            debris_count = len(self._structure_debris.get(structure_id, []))
            collapse_count = len(self._structure_collapses.get(structure_id, []))

            # Generate recommendations based on assessment
            recommendations: List[str] = []
            if integrity < self._config.collapse_threshold:
                recommendations.append("imminent_collapse_evacuate")
            if not is_supported:
                recommendations.append("unsupported_nodes_detected")
            if broken_edges > structure.original_edge_count * 0.3:
                recommendations.append("structural_compromise_critical")
            if integrity > 0.7 and broken_edges > 0:
                recommendations.append("minor_repair_recommended")
            if not recommendations:
                recommendations.append("no_action_needed")

            severity: str
            if integrity > 0.75:
                severity = "minor"
            elif integrity > 0.5:
                severity = "moderate"
            elif integrity > self._config.collapse_threshold:
                severity = "severe"
            elif integrity > 0.01:
                severity = "critical"
            else:
                severity = "total"

            result = {
                "structure_id": structure_id,
                "integrity": integrity,
                "status": structure.status,
                "severity": severity,
                "fracture_count": len(fracture_ids),
                "broken_edges": broken_edges,
                "broken_nodes": broken_nodes,
                "total_edges": len(structure.edges),
                "total_nodes": len(structure.nodes),
                "debris_count": debris_count,
                "collapse_event_count": collapse_count,
                "is_fully_supported": is_supported,
                "unsupported_node_count": len(unsupported),
                "recommendations": recommendations,
            }
            return True, "assessed", result

    def get_fracture(self, fracture_id: str) -> Optional[FractureRecord]:
        """Return a fracture record by id, or None if it does not exist."""
        return self._fractures.get(fracture_id)

    def list_fractures(
        self,
        structure_id: str,
        pattern: Optional[str] = None,
        limit: int = 100,
    ) -> List[FractureRecord]:
        """List fracture records for a structure, optionally filtered by pattern."""
        cap = max(1, _safe_int(limit, 100))
        frac_ids = self._structure_fractures.get(structure_id, [])
        result: List[FractureRecord] = []
        pat_filter = None
        if pattern is not None:
            pat_filter = _coerce_enum(FracturePattern, pattern)
            pat_filter = pat_filter.value if pat_filter else str(pattern).lower()
        for fid in frac_ids:
            fracture = self._fractures.get(fid)
            if fracture is None:
                continue
            if pat_filter is not None and fracture.pattern != pat_filter:
                continue
            result.append(fracture)
            if len(result) >= cap:
                break
        return result

    # ------------------------------------------------------------------
    # Collapse and Debris (8 methods)
    # ------------------------------------------------------------------

    def _trigger_collapse_internal(
        self,
        structure: Structure,
        triggered_by: str,
    ) -> CollapseEvent:
        """Internal helper to create and start a collapse event."""
        event_id = _new_id("collapse")
        collapse = CollapseEvent(
            event_id=event_id,
            structure_id=structure.structure_id,
            triggered_by=triggered_by,
            progress=0.0,
            duration=structure.collapse_duration,
            is_active=True,
        )
        self._collapse_events[event_id] = collapse
        self._structure_collapses.setdefault(
            structure.structure_id, []
        ).append(event_id)
        _evict_fifo_dict(self._collapse_events, self._config.max_collapse_events)
        structure.status = StructureStatus.COLLAPSING.value
        structure.updated_at = _now()
        self._emit(
            DestructibleEventKind.COLLAPSE_TRIGGERED.value,
            structure_id=structure.structure_id,
            description=f"Collapse triggered by {triggered_by}",
            data={"collapse_event_id": event_id},
        )
        return collapse

    def trigger_collapse(
        self,
        structure_id: str,
        triggered_by: str = "manual",
    ) -> Tuple[bool, str, Optional[CollapseEvent]]:
        """Manually trigger a structural collapse regardless of integrity."""
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            if structure.status in (
                StructureStatus.DESTROYED.value,
                StructureStatus.RUBBLE.value,
            ):
                return False, "structure_already_destroyed", None
            if structure.status == StructureStatus.COLLAPSING.value:
                # Return the existing active collapse event
                for evt in reversed(
                    self._structure_collapses.get(structure_id, [])
                ):
                    existing = self._collapse_events.get(evt)
                    if existing and existing.is_active:
                        return True, "already_collapsing", existing
            collapse = self._trigger_collapse_internal(structure, triggered_by)
            self._refresh_stats()
            return True, "collapse_triggered", collapse

    def simulate_collapse(
        self,
        structure_id: str,
        dt: float,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Advance the collapse simulation for a structure by dt seconds.

        Progressively breaks edges from top to bottom, displaces nodes
        downward, and spawns debris. When progress reaches 1.0, the
        structure is marked as destroyed.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            if structure.status not in (
                StructureStatus.COLLAPSING.value,
                StructureStatus.DESTROYED.value,
            ):
                return False, "structure_not_collapsing", None
            step = max(0.001, _safe_float(dt, _DEFAULT_DT))
            # Find the active collapse event
            active_collapse: Optional[CollapseEvent] = None
            for eid in reversed(self._structure_collapses.get(structure_id, [])):
                evt = self._collapse_events.get(eid)
                if evt and evt.is_active:
                    active_collapse = evt
                    break
            if active_collapse is None:
                return False, "no_active_collapse_event", None

            # Advance progress
            progress_increment = step / max(active_collapse.duration, _EPSILON)
            active_collapse.progress = _clamp(
                active_collapse.progress + progress_increment * self._config.collapse_speed,
                0.0, 1.0,
            )
            structure.collapse_progress = active_collapse.progress

            # Break edges from top to bottom based on progress
            sorted_nodes = sorted(
                [n for n in structure.nodes if not n.is_broken],
                key=lambda n: -n.position[1],
            )
            nodes_to_collapse = int(
                len(sorted_nodes) * progress_increment * self._config.collapse_speed * 3
            )
            nodes_to_collapse = max(1, nodes_to_collapse)
            collapsed_count = 0
            for node in sorted_nodes[:nodes_to_collapse]:
                if node.is_broken:
                    continue
                node.is_broken = True
                node.velocity = (
                    node.velocity[0],
                    node.velocity[1] - self._config.gravity * step,
                    node.velocity[2],
                )
                # Displace downward
                node.displacement = (
                    node.displacement[0],
                    node.displacement[1] - step * 2.0,
                    node.displacement[2],
                )
                node.position = (
                    node.position[0] + node.displacement[0] * step,
                    node.position[1] + node.displacement[1] * step,
                    node.position[2] + node.displacement[2] * step,
                )
                collapsed_count += 1
                active_collapse.nodes_collapsed += 1

            # Break edges connected to collapsed nodes
            edges_broken_this_step = 0
            for edge in structure.edges:
                if edge.is_broken:
                    continue
                node_a = self._get_node(structure, edge.node_a)
                node_b = self._get_node(structure, edge.node_b)
                if (node_a and node_a.is_broken) or (node_b and node_b.is_broken):
                    edge.is_broken = True
                    edge.damage = 1.0
                    edges_broken_this_step += 1
                    active_collapse.edges_broken += 1
                    # Spawn debris from newly broken edges
                    debris = self._spawn_debris_from_edge(
                        structure, edge, FracturePattern.CRUMBLE.value
                    )
                    if debris is not None:
                        active_collapse.debris_generated += 1

            structure.integrity = self._compute_structure_integrity(structure)

            # Check if collapse is complete
            if active_collapse.progress >= 1.0 or structure.integrity <= 0.01:
                active_collapse.is_active = False
                active_collapse.progress = 1.0
                active_collapse.completed_at = _now()
                structure.status = StructureStatus.DESTROYED.value
                structure.integrity = 0.0
                structure.collapse_progress = 1.0
                self._emit(
                    DestructibleEventKind.COLLAPSE_COMPLETED.value,
                    structure_id=structure_id,
                    description=f"Structure {structure_id} fully collapsed",
                    data={
                        "collapse_event_id": active_collapse.event_id,
                        "total_nodes_collapsed": active_collapse.nodes_collapsed,
                        "total_edges_broken": active_collapse.edges_broken,
                        "total_debris_generated": active_collapse.debris_generated,
                    },
                )
            else:
                structure.status = StructureStatus.COLLAPSING.value

            structure.updated_at = _now()
            result = {
                "structure_id": structure_id,
                "collapse_event_id": active_collapse.event_id,
                "progress": active_collapse.progress,
                "nodes_collapsed_this_step": collapsed_count,
                "edges_broken_this_step": edges_broken_this_step,
                "total_nodes_collapsed": active_collapse.nodes_collapsed,
                "total_edges_broken": active_collapse.edges_broken,
                "total_debris_generated": active_collapse.debris_generated,
                "integrity": structure.integrity,
                "status": structure.status,
                "is_active": active_collapse.is_active,
            }
            self._emit(
                DestructibleEventKind.COLLAPSE_SIMULATED.value,
                structure_id=structure_id,
                description=f"Collapse simulated: dt={step}, progress={active_collapse.progress:.3f}",
                data=result,
            )
            self._refresh_stats()
            return True, "collapse_simulated", result

    def register_debris(
        self,
        debris_id: str,
        structure_id: str,
        mass: float = 1.0,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        size: float = 1.0,
        material: str = MaterialType.CONCRETE.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[DebrisPiece]]:
        """Register a new debris piece in the simulation."""
        with self._lock:
            if debris_id in self._debris:
                return False, "already_exists", None
            mat = _coerce_enum(MaterialType, material, MaterialType.CONCRETE).value
            debris = DebrisPiece(
                debris_id=debris_id,
                structure_id=structure_id,
                mass=max(0.01, _safe_float(mass, 1.0)),
                position=tuple(position),
                velocity=tuple(velocity),
                size=max(0.01, _safe_float(size, 1.0)),
                material=mat,
                status=DebrisStatus.ACTIVE.value,
                metadata=dict(metadata) if metadata else {},
            )
            self._debris[debris_id] = debris
            self._structure_debris.setdefault(structure_id, []).append(debris_id)
            _evict_fifo_dict(self._debris, self._config.max_debris)
            self._emit(
                DestructibleEventKind.DEBRIS_REGISTERED.value,
                structure_id=structure_id,
                description=f"Debris registered: {debris_id}",
                data={"mass": debris.mass, "material": mat},
            )
            self._refresh_stats()
            return True, "registered", debris

    def get_debris(self, debris_id: str) -> Optional[DebrisPiece]:
        """Return a debris piece by id, or None if it does not exist."""
        return self._debris.get(debris_id)

    def list_debris(
        self,
        structure_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[DebrisPiece]:
        """List debris pieces, optionally filtered by structure or status."""
        cap = max(1, _safe_int(limit, 100))
        result: List[DebrisPiece] = []
        status_filter = None
        if status is not None:
            status_filter = _coerce_enum(DebrisStatus, status)
            status_filter = status_filter.value if status_filter else str(status).lower()
        if structure_id is not None:
            debris_ids = self._structure_debris.get(structure_id, [])
            for did in debris_ids:
                debris = self._debris.get(did)
                if debris is None:
                    continue
                if status_filter is not None and debris.status != status_filter:
                    continue
                result.append(debris)
                if len(result) >= cap:
                    break
        else:
            for debris in self._debris.values():
                if status_filter is not None and debris.status != status_filter:
                    continue
                result.append(debris)
                if len(result) >= cap:
                    break
        return result

    def remove_debris(self, debris_id: str) -> Tuple[bool, str]:
        """Remove a debris piece from the simulation."""
        with self._lock:
            if debris_id not in self._debris:
                return False, "not_found"
            debris = self._debris.pop(debris_id)
            struct_list = self._structure_debris.get(debris.structure_id, [])
            if debris_id in struct_list:
                struct_list.remove(debris_id)
            self._emit(
                DestructibleEventKind.DEBRIS_REMOVED.value,
                structure_id=debris.structure_id,
                description=f"Debris removed: {debris_id}",
            )
            self._refresh_stats()
            return True, "removed"

    def settle_debris(self, debris_id: str) -> Tuple[bool, str, Optional[DebrisPiece]]:
        """Mark a debris piece as settled (no longer moving)."""
        with self._lock:
            debris = self._debris.get(debris_id)
            if debris is None:
                return False, "not_found", None
            if debris.status == DebrisStatus.SETTLED.value:
                return True, "already_settled", debris
            debris.status = DebrisStatus.SETTLED.value
            debris.velocity = (0.0, 0.0, 0.0)
            debris.angular_velocity = (0.0, 0.0, 0.0)
            debris.settled_at = _now()
            self._emit(
                DestructibleEventKind.DEBRIS_SETTLED.value,
                structure_id=debris.structure_id,
                description=f"Debris settled: {debris_id}",
            )
            self._refresh_stats()
            return True, "settled", debris

    def compute_debris_pile(
        self,
        structure_id: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Compute a summary of the debris pile for a structure.

        Aggregates all debris pieces associated with a structure into
        centroid position, total mass, pile radius, and count by status.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            debris_ids = self._structure_debris.get(structure_id, [])
            debris_list = [
                self._debris.get(did) for did in debris_ids
                if self._debris.get(did) is not None
            ]
            if not debris_list:
                return True, "no_debris", {
                    "structure_id": structure_id,
                    "total_debris": 0,
                    "total_mass": 0.0,
                    "centroid": structure.position,
                    "pile_radius": 0.0,
                }
            total_mass = sum(d.mass for d in debris_list)
            cx = sum(d.position[0] * d.mass for d in debris_list) / max(total_mass, _EPSILON)
            cy = sum(d.position[1] * d.mass for d in debris_list) / max(total_mass, _EPSILON)
            cz = sum(d.position[2] * d.mass for d in debris_list) / max(total_mass, _EPSILON)
            centroid = (cx, cy, cz)
            max_dist = 0.0
            for d in debris_list:
                dist = _vec3_distance(d.position, centroid)
                if dist > max_dist:
                    max_dist = dist
            active_count = sum(1 for d in debris_list if d.status == DebrisStatus.ACTIVE.value)
            settled_count = sum(1 for d in debris_list if d.status == DebrisStatus.SETTLED.value)
            result = {
                "structure_id": structure_id,
                "total_debris": len(debris_list),
                "active_debris": active_count,
                "settled_debris": settled_count,
                "total_mass": total_mass,
                "centroid": centroid,
                "pile_radius": max_dist,
                "average_size": sum(d.size for d in debris_list) / len(debris_list),
            }
            return True, "computed", result

    # ------------------------------------------------------------------
    # AI Methods (4 methods)
    # ------------------------------------------------------------------

    def ai_assess_vulnerability(
        self,
        structure_id: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """AI-driven analysis of structural weak points and vulnerabilities.

        Identifies the most stressed nodes and edges, nodes with the most
        broken connections, and edges closest to their yield point. Returns
        a vulnerability score and list of critical elements.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            material = self._get_material_for_structure(structure)
            yield_stress = material.yield_stress if material else 30.0

            # Score each node by stress and number of broken connections
            node_scores: List[Tuple[str, float, str]] = []
            for node in structure.nodes:
                if node.is_broken:
                    continue
                broken_connections = sum(
                    1 for eid in node.connections
                    if self._get_edge(structure, eid)
                    and self._get_edge(structure, eid).is_broken
                )
                total_connections = max(len(node.connections), 1)
                connectivity_ratio = broken_connections / total_connections
                stress_ratio = node.stress / max(yield_stress, _EPSILON)
                vulnerability = stress_ratio * 0.5 + connectivity_ratio * 0.5
                node_scores.append((node.node_id, vulnerability, "node"))

            # Score each edge by proximity to yield
            edge_scores: List[Tuple[str, float, str]] = []
            for edge in structure.edges:
                if edge.is_broken:
                    continue
                stress_ratio = edge.stress / max(edge.strength, _EPSILON)
                damage_factor = edge.damage
                vulnerability = stress_ratio * 0.6 + damage_factor * 0.4
                edge_scores.append((edge.edge_id, vulnerability, "edge"))

            all_scores = node_scores + edge_scores
            all_scores.sort(key=lambda x: -x[1])
            critical_elements = [
                {"id": eid, "type": etype, "vulnerability": round(vul, 4)}
                for eid, vul, etype in all_scores[:10]
            ]
            # Overall vulnerability score: average of top 5
            top_scores = [s[1] for s in all_scores[:5]]
            overall_vulnerability = (
                sum(top_scores) / len(top_scores) if top_scores else 0.0
            )
            overall_vulnerability = _clamp(overall_vulnerability)

            # Generate AI insight
            if overall_vulnerability > 0.7:
                insight = "Critical vulnerability detected. Immediate reinforcement recommended."
            elif overall_vulnerability > 0.4:
                insight = "Moderate vulnerability. Monitor stress accumulation in critical elements."
            else:
                insight = "Structure is stable. No immediate action required."

            result = {
                "structure_id": structure_id,
                "overall_vulnerability": overall_vulnerability,
                "insight": insight,
                "critical_elements": critical_elements,
                "assessed_nodes": len(node_scores),
                "assessed_edges": len(edge_scores),
                "yield_stress": yield_stress,
                "integrity": structure.integrity,
            }
            self._emit(
                DestructibleEventKind.AI_ASSESSMENT.value,
                structure_id=structure_id,
                description="AI vulnerability assessment completed",
                data=result,
            )
            return True, "assessed", result

    def ai_optimize_fracture(
        self,
        structure_id: str,
        target_pattern: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """AI-driven tuning of fracture parameters for a desired pattern.

        Adjusts the brittleness and stress thresholds of edges to favor
        the specified fracture pattern. Returns the adjusted parameters
        and a summary of changes.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            pattern = _coerce_enum(
                FracturePattern, target_pattern, FracturePattern.SHEAR
            ).value
            material = self._get_material_for_structure(structure)

            # Determine optimal parameters for the target pattern
            if pattern == FracturePattern.SHATTER.value:
                # Shatter requires high brittleness and low toughness
                target_brittleness = 0.9
                strength_multiplier = 0.7
                stress_threshold_factor = 0.8
            elif pattern == FracturePattern.SPLINTER.value:
                # Splinter requires moderate brittleness and directional stress
                target_brittleness = 0.5
                strength_multiplier = 0.85
                stress_threshold_factor = 0.9
            elif pattern == FracturePattern.CRUMBLE.value:
                # Crumble requires low brittleness and gradual failure
                target_brittleness = 0.2
                strength_multiplier = 1.0
                stress_threshold_factor = 1.1
            elif pattern == FracturePattern.SHEAR.value:
                # Shear requires clean stress concentration at specific points
                target_brittleness = 0.4
                strength_multiplier = 0.9
                stress_threshold_factor = 1.0
            elif pattern == FracturePattern.EXPLOSIVE.value:
                # Explosive requires rapid stress propagation
                target_brittleness = 0.8
                strength_multiplier = 0.6
                stress_threshold_factor = 0.7
            else:
                target_brittleness = 0.5
                strength_multiplier = 0.9
                stress_threshold_factor = 1.0

            adjusted_edges = 0
            total_strength_change = 0.0
            for edge in structure.edges:
                if edge.is_broken:
                    continue
                old_strength = edge.strength
                edge.strength = max(
                    1.0, old_strength * strength_multiplier
                )
                edge.load_capacity = edge.strength
                total_strength_change += (edge.strength - old_strength)
                adjusted_edges += 1

            # Update material brittleness if available
            old_brittleness = 0.5
            if material is not None:
                old_brittleness = material.brittleness
                material.brittleness = target_brittleness

            avg_strength_change = (
                total_strength_change / max(adjusted_edges, 1)
            )
            result = {
                "structure_id": structure_id,
                "target_pattern": pattern,
                "adjusted_edges": adjusted_edges,
                "average_strength_change": avg_strength_change,
                "old_brittleness": old_brittleness,
                "new_brittleness": target_brittleness,
                "strength_multiplier": strength_multiplier,
                "stress_threshold_factor": stress_threshold_factor,
                "recommendation": (
                    f"Edges tuned for {pattern} pattern. "
                    f"Apply force to {adjusted_edges} edges for optimal fracturing."
                ),
            }
            self._emit(
                DestructibleEventKind.AI_ASSESSMENT.value,
                structure_id=structure_id,
                description=f"AI fracture optimization for {pattern} pattern",
                data=result,
            )
            return True, "optimized", result

    def ai_predict_collapse(
        self,
        structure_id: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """AI-driven prediction of potential collapse scenarios.

        Simulates progressive edge failure to determine the critical failure
        point and estimates the collapse cascade. Returns probability,
        estimated time to collapse, and the critical failure sequence.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            integrity = self._compute_structure_integrity(structure)
            is_supported, unsupported = self._check_support_connectivity(structure)

            # Sort edges by stress (highest first) to find failure sequence
            intact_edges = [
                e for e in structure.edges if not e.is_broken
            ]
            sorted_edges = sorted(
                intact_edges,
                key=lambda e: -(e.stress / max(e.strength, _EPSILON))
            )

            # Simulate progressive failure: remove edges one by one
            # and check when the structure would collapse
            critical_sequence: List[Dict[str, Any]] = []
            simulated_integrity = integrity
            collapse_at_step = -1
            temp_broken: set = set()

            for i, edge in enumerate(sorted_edges[:20]):  # Limit simulation depth
                stress_ratio = edge.stress / max(edge.strength, _EPSILON)
                temp_broken.add(edge.edge_id)
                remaining = len(intact_edges) - len(temp_broken)
                sim_integrity = remaining / max(structure.original_edge_count, 1)
                critical_sequence.append({
                    "step": i + 1,
                    "edge_id": edge.edge_id,
                    "stress_ratio": round(stress_ratio, 4),
                    "simulated_integrity": round(sim_integrity, 4),
                })
                if sim_integrity < self._config.collapse_threshold and collapse_at_step < 0:
                    collapse_at_step = i + 1
                if sim_integrity <= 0.01:
                    break

            # Compute collapse probability
            if integrity < self._config.collapse_threshold:
                probability = 0.95
            elif not is_supported:
                probability = 0.8
            elif integrity < 0.5:
                probability = 0.6
            elif integrity < 0.75:
                probability = 0.3
            else:
                probability = 0.1
            probability = _clamp(probability, 0.0, 1.0)

            # Estimate time to collapse (in seconds of simulation time)
            if probability > 0.9:
                time_to_collapse = 0.5
            elif probability > 0.7:
                time_to_collapse = 2.0
            elif probability > 0.4:
                time_to_collapse = 10.0
            elif probability > 0.1:
                time_to_collapse = 60.0
            else:
                time_to_collapse = -1.0  # No collapse predicted

            # Generate prediction insight
            if probability > 0.7:
                prediction = "Imminent collapse predicted. Recommend immediate evacuation."
            elif probability > 0.4:
                prediction = "Moderate collapse risk. Monitor for progressive failure."
            elif probability > 0.1:
                prediction = "Low collapse risk. Structure is stable under current load."
            else:
                prediction = "Structure is stable. No collapse predicted."

            result = {
                "structure_id": structure_id,
                "collapse_probability": probability,
                "time_to_collapse_seconds": time_to_collapse,
                "prediction": prediction,
                "integrity": integrity,
                "is_fully_supported": is_supported,
                "unsupported_node_count": len(unsupported),
                "critical_failure_sequence": critical_sequence,
                "collapse_at_step": collapse_at_step,
                "edges_analyzed": len(sorted_edges[:20]),
            }
            self._emit(
                DestructibleEventKind.AI_ASSESSMENT.value,
                structure_id=structure_id,
                description="AI collapse prediction completed",
                data=result,
            )
            return True, "predicted", result

    def ai_generate_destruction_plan(
        self,
        structure_id: str,
        target_state: str = "destroyed",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """AI-driven generation of a controlled demolition plan.

        Analyzes the structure and produces a sequence of targeted actions
        (damage, explosive, fracture) designed to bring the structure to the
        target state efficiently and safely.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            target = str(target_state).lower()
            if target not in (
                StructureStatus.DAMAGED.value,
                StructureStatus.DESTROYED.value,
                StructureStatus.RUBBLE.value,
            ):
                return False, "invalid_target_state", None

            # Analyze the structure for weak points
            ok, _, vuln = self.ai_assess_vulnerability(structure_id)
            if vuln is None:
                return False, "vulnerability_assessment_failed", None
            critical_elements = vuln.get("critical_elements", [])

            # Determine the number and type of actions based on target state
            if target == StructureStatus.DESTROYED.value:
                num_charges = max(3, len(structure.nodes) // 10)
                force_per_charge = 300.0
                radius_per_charge = 5.0
            elif target == StructureStatus.RUBBLE.value:
                num_charges = max(5, len(structure.nodes) // 6)
                force_per_charge = 500.0
                radius_per_charge = 8.0
            else:  # damaged
                num_charges = max(1, len(structure.nodes) // 20)
                force_per_charge = 150.0
                radius_per_charge = 3.0

            # Build the action sequence
            actions: List[Dict[str, Any]] = []
            # Step 1: Target the most vulnerable nodes first
            for i, elem in enumerate(critical_elements[:num_charges]):
                if elem["type"] == "node":
                    node = self._get_node(structure, elem["id"])
                    if node:
                        actions.append({
                            "step": i + 1,
                            "action": "apply_explosive",
                            "target": elem["id"],
                            "position": node.position,
                            "blast_force": force_per_charge,
                            "radius": radius_per_charge,
                            "priority": "high" if i < 2 else "medium",
                        })
                else:
                    edge = self._get_edge(structure, elem["id"])
                    if edge:
                        node_a = self._get_node(structure, edge.node_a)
                        pos = node_a.position if node_a else structure.position
                        actions.append({
                            "step": i + 1,
                            "action": "create_fracture",
                            "target": elem["id"],
                            "position": pos,
                            "pattern": self._pick_fracture_pattern(
                                structure.material_type, force_per_charge
                            ),
                            "priority": "high" if i < 2 else "medium",
                        })

            # Step 2: For full destruction, add base-level charges to undermine supports
            if target in (
                StructureStatus.DESTROYED.value,
                StructureStatus.RUBBLE.value,
            ):
                support_nodes = [
                    n for n in structure.nodes if n.is_support and not n.is_broken
                ]
                for i, node in enumerate(support_nodes[:3]):
                    actions.append({
                        "step": len(actions) + 1,
                        "action": "apply_explosive",
                        "target": node.node_id,
                        "position": node.position,
                        "blast_force": force_per_charge * 1.5,
                        "radius": radius_per_charge * 1.2,
                        "priority": "critical",
                        "note": "Undermine support structure",
                    })

            # Step 3: For rubble, trigger collapse after initial damage
            if target == StructureStatus.RUBBLE.value:
                actions.append({
                    "step": len(actions) + 1,
                    "action": "trigger_collapse",
                    "target": structure_id,
                    "triggered_by": "controlled_demolition",
                    "priority": "final",
                })

            # Estimate outcome
            estimated_integrity = max(
                0.0, structure.integrity - (num_charges * force_per_charge / 1000.0)
            )
            estimated_debris = num_charges * 3
            estimated_time = len(actions) * 2.0  # 2 seconds per action

            result = {
                "structure_id": structure_id,
                "target_state": target,
                "plan_id": _new_id("plan"),
                "actions": actions,
                "total_steps": len(actions),
                "estimated_final_integrity": _clamp(estimated_integrity, 0.0, 1.0),
                "estimated_debris_generated": estimated_debris,
                "estimated_time_seconds": estimated_time,
                "current_integrity": structure.integrity,
                "summary": (
                    f"Demolition plan generated: {len(actions)} steps to reach "
                    f"'{target}' state. Estimated time: {estimated_time:.1f}s."
                ),
            }
            self._emit(
                DestructibleEventKind.AI_ASSESSMENT.value,
                structure_id=structure_id,
                description=f"AI destruction plan generated for target: {target}",
                data=result,
            )
            return True, "plan_generated", result

    # ------------------------------------------------------------------
    # Query and State (17 methods)
    # ------------------------------------------------------------------

    def get_collapse_event(self, event_id: str) -> Optional[CollapseEvent]:
        """Return a collapse event by id, or None if it does not exist."""
        return self._collapse_events.get(event_id)

    def list_collapse_events(
        self,
        structure_id: Optional[str] = None,
        active_only: bool = False,
        limit: int = 100,
    ) -> List[CollapseEvent]:
        """List collapse events, optionally filtered by structure or active state."""
        cap = max(1, _safe_int(limit, 100))
        result: List[CollapseEvent] = []
        if structure_id is not None:
            event_ids = self._structure_collapses.get(structure_id, [])
            for eid in event_ids:
                evt = self._collapse_events.get(eid)
                if evt is None:
                    continue
                if active_only and not evt.is_active:
                    continue
                result.append(evt)
                if len(result) >= cap:
                    break
        else:
            for evt in self._collapse_events.values():
                if active_only and not evt.is_active:
                    continue
                result.append(evt)
                if len(result) >= cap:
                    break
        return result

    def get_deformation_summary(
        self,
        structure_id: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Return a summary of node displacements and edge deformations."""
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            node_displacements: List[Dict[str, Any]] = []
            edge_deformations: List[Dict[str, Any]] = []
            total_displacement = 0.0
            max_displacement = 0.0
            for node in structure.nodes:
                if node.is_broken:
                    continue
                disp_mag = _vec3_length(node.displacement)
                total_displacement += disp_mag
                if disp_mag > max_displacement:
                    max_displacement = disp_mag
                if disp_mag > _EPSILON:
                    node_displacements.append({
                        "node_id": node.node_id,
                        "displacement": node.displacement,
                        "magnitude": disp_mag,
                        "position": node.position,
                    })
            total_strain = 0.0
            max_strain = 0.0
            for edge in structure.edges:
                if edge.is_broken:
                    continue
                strain = edge.strain
                total_strain += abs(strain)
                if abs(strain) > max_strain:
                    max_strain = abs(strain)
                if abs(strain) > _EPSILON:
                    edge_deformations.append({
                        "edge_id": edge.edge_id,
                        "strain": strain,
                        "rest_length": edge.rest_length,
                        "current_length": edge.current_length,
                        "deformation": edge.current_length - edge.rest_length,
                    })
            avg_displacement = (
                total_displacement / max(len(node_displacements), 1)
            )
            avg_strain = total_strain / max(len(edge_deformations), 1)
            result = {
                "structure_id": structure_id,
                "total_displacement": total_displacement,
                "max_displacement": max_displacement,
                "average_displacement": avg_displacement,
                "displaced_nodes": len(node_displacements),
                "node_displacements": node_displacements[:50],
                "total_strain": total_strain,
                "max_strain": max_strain,
                "average_strain": avg_strain,
                "deformed_edges": len(edge_deformations),
                "edge_deformations": edge_deformations[:50],
            }
            return True, "computed", result

    def get_visualization_data(
        self,
        structure_id: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Return data suitable for rendering the structure and its damage state.

        Includes node positions, edge endpoints, stress colors, and
        fracture locations formatted for a rendering pipeline.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            # Find max stress for normalization
            max_stress = _EPSILON
            for node in structure.nodes:
                if node.stress > max_stress:
                    max_stress = node.stress
            for edge in structure.edges:
                if edge.stress > max_stress:
                    max_stress = edge.stress

            vis_nodes: List[Dict[str, Any]] = []
            for node in structure.nodes:
                stress_norm = _clamp(node.stress / max_stress) if max_stress > _EPSILON else 0.0
                vis_nodes.append({
                    "id": node.node_id,
                    "position": list(node.position),
                    "mass": node.mass,
                    "stress": node.stress,
                    "stress_normalized": stress_norm,
                    "is_support": node.is_support,
                    "is_broken": node.is_broken,
                    "color": self._stress_to_color(stress_norm),
                })

            vis_edges: List[Dict[str, Any]] = []
            for edge in structure.edges:
                node_a = self._get_node(structure, edge.node_a)
                node_b = self._get_node(structure, edge.node_b)
                if node_a is None or node_b is None:
                    continue
                stress_norm = _clamp(edge.stress / max_stress) if max_stress > _EPSILON else 0.0
                vis_edges.append({
                    "id": edge.edge_id,
                    "from": node_a.position,
                    "to": node_b.position,
                    "strength": edge.strength,
                    "stress": edge.stress,
                    "stress_normalized": stress_norm,
                    "damage": edge.damage,
                    "is_broken": edge.is_broken,
                    "material": edge.material,
                    "color": self._stress_to_color(stress_norm),
                })

            # Fracture positions for rendering
            fracture_ids = self._structure_fractures.get(structure_id, [])
            vis_fractures: List[Dict[str, Any]] = []
            for fid in fracture_ids:
                frac = self._fractures.get(fid)
                if frac is None:
                    continue
                vis_fractures.append({
                    "fracture_id": frac.fracture_id,
                    "position": list(frac.position),
                    "pattern": frac.pattern,
                    "severity": frac.severity,
                })

            result = {
                "structure_id": structure_id,
                "name": structure.name,
                "material_type": structure.material_type,
                "status": structure.status,
                "integrity": structure.integrity,
                "position": list(structure.position),
                "bounding_radius": structure.bounding_radius,
                "nodes": vis_nodes,
                "edges": vis_edges,
                "fractures": vis_fractures,
                "node_count": len(vis_nodes),
                "edge_count": len(vis_edges),
                "fracture_count": len(vis_fractures),
            }
            return True, "computed", result

    def _stress_to_color(self, normalized_stress: float) -> Tuple[int, int, int]:
        """Map a normalized stress value (0-1) to an RGB color.

        Low stress is green, medium is yellow, high is red.
        """
        s = _clamp(normalized_stress)
        if s < 0.5:
            # Green to yellow
            t = s * 2.0
            return (int(255 * t), 255, 0)
        else:
            # Yellow to red
            t = (s - 0.5) * 2.0
            return (255, int(255 * (1.0 - t)), 0)

    def get_status(self) -> Dict[str, Any]:
        """Return a lightweight status dictionary."""
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "seeded": self._seeded,
                "structures": len(self._structures),
                "materials": len(self._materials),
                "fractures": len(self._fractures),
                "debris": len(self._debris),
                "collapse_events": len(self._collapse_events),
                "events": len(self._events),
                "tick_count": self._tick_count,
                "global_time": self._global_time,
                "config": self._config.to_dict(),
                "stats": self._stats.to_dict(),
            }

    def get_stats(self) -> DestructibleStats:
        """Return aggregate statistics."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> DestructibleSnapshot:
        """Return a point-in-time snapshot of the full system state."""
        with self._lock:
            self._refresh_stats()
            return DestructibleSnapshot(
                timestamp=_now(),
                structures=[
                    s.to_dict() for s in list(self._structures.values())[-50:]
                ],
                materials=[
                    m.to_dict() for m in list(self._materials.values())[-50:]
                ],
                fractures=[
                    f.to_dict() for f in list(self._fractures.values())[-50:]
                ],
                debris=[
                    d.to_dict() for d in list(self._debris.values())[-50:]
                ],
                collapse_events=[
                    c.to_dict() for c in list(self._collapse_events.values())[-50:]
                ],
                events=[e.to_dict() for e in self._events[-50:]],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
            )

    def get_config(self) -> DestructibleConfig:
        """Return the current configuration."""
        return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, DestructibleConfig]:
        """Update tunable configuration fields by keyword."""
        with self._lock:
            known = set(self._config.__dataclass_fields__.keys())
            applied: List[str] = []
            int_fields = (
                "max_structures", "max_materials", "max_fractures",
                "max_debris", "max_collapse_events", "max_events",
            )
            float_fields = (
                "gravity", "damage_decay", "fracture_propagation_rate",
                "collapse_speed", "collapse_threshold",
                "debris_settle_time", "debris_drag",
            )
            bool_fields = (
                "enable_chain_reactions", "enable_debris_physics",
                "enable_auto_collapse",
            )
            for key, value in kwargs.items():
                if key not in known:
                    continue
                if key in int_fields:
                    setattr(
                        self._config, key,
                        max(1, _safe_int(value, getattr(self._config, key))),
                    )
                elif key in float_fields:
                    setattr(
                        self._config, key,
                        max(0.0, _safe_float(value, getattr(self._config, key))),
                    )
                elif key in bool_fields:
                    setattr(self._config, key, bool(value))
                elif key == "metadata":
                    if isinstance(value, dict):
                        self._config.metadata = dict(value)
                else:
                    continue
                applied.append(key)
            if not applied:
                return False, "no_valid_config_fields_supplied", self._config
            self._emit(
                DestructibleEventKind.CONFIG_UPDATED.value,
                description="Configuration updated",
                data={"fields": applied},
            )
            return True, "updated", self._config

    def list_events(
        self,
        kind: Optional[str] = None,
        limit: int = 100,
    ) -> List[DestructibleEvent]:
        """Return the most recent events, optionally filtered by event kind."""
        cap = max(1, _safe_int(limit, 100))
        result: List[DestructibleEvent] = []
        for event in reversed(self._events):
            if kind is not None and event.event_type != kind:
                continue
            result.append(event)
            if len(result) >= cap:
                break
        result.reverse()
        return result

    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        """Advance the simulation by one tick.

        Processes active debris physics (gravity, drag, settling),
        advances active collapse simulations, applies damage decay to
        intact edges, and refreshes statistics.
        """
        with self._lock:
            self._tick_count += 1
            step = max(0.001, _safe_float(dt, _DEFAULT_DT))
            self._global_time += step

            settled_debris: List[str] = []
            moved_debris: List[str] = []
            collapsed_structures: List[str] = []

            # Update active debris physics
            if self._config.enable_debris_physics:
                for debris in self._debris.values():
                    if debris.status != DebrisStatus.ACTIVE.value:
                        continue
                    debris.age += step
                    # Apply gravity
                    vx, vy, vz = debris.velocity
                    vy -= self._config.gravity * step
                    # Apply drag
                    drag_factor = max(0.0, 1.0 - self._config.debris_drag * step)
                    vx *= drag_factor
                    vy *= drag_factor
                    vz *= drag_factor
                    debris.velocity = (vx, vy, vz)
                    # Update position
                    px, py, pz = debris.position
                    px += vx * step
                    py += vy * step
                    pz += vz * step
                    # Ground collision: debris settles when it hits y=0
                    if py <= 0.0:
                        py = 0.0
                        debris.position = (px, py, pz)
                        debris.status = DebrisStatus.SETTLED.value
                        debris.settled_at = _now()
                        debris.velocity = (0.0, 0.0, 0.0)
                        settled_debris.append(debris.debris_id)
                    else:
                        debris.position = (px, py, pz)
                        moved_debris.append(debris.debris_id)
                    # Auto-settle debris that has been active too long
                    if (debris.status == DebrisStatus.ACTIVE.value
                            and debris.age > self._config.debris_settle_time):
                        debris.status = DebrisStatus.SETTLED.value
                        debris.settled_at = _now()
                        debris.velocity = (0.0, 0.0, 0.0)
                        settled_debris.append(debris.debris_id)

            # Advance active collapses
            for structure in self._structures.values():
                if structure.status != StructureStatus.COLLAPSING.value:
                    continue
                ok, _, _ = self.simulate_collapse(
                    structure.structure_id, step
                )
                if ok:
                    collapsed_structures.append(structure.structure_id)

            # Apply damage decay to intact edges (stress relaxation)
            if self._config.damage_decay > 0.0:
                for structure in self._structures.values():
                    for edge in structure.edges:
                        if edge.is_broken:
                            continue
                        if edge.stress > 0.0:
                            edge.stress = max(
                                0.0,
                                edge.stress * (1.0 - self._config.damage_decay * step)
                            )
                    for node in structure.nodes:
                        if node.is_broken:
                            continue
                        if node.stress > 0.0:
                            node.stress = max(
                                0.0,
                                node.stress * (1.0 - self._config.damage_decay * step)
                            )

            self._refresh_stats()
            self._emit(
                DestructibleEventKind.TICK.value,
                description=f"Tick #{self._tick_count}",
                data={
                    "tick": self._tick_count,
                    "dt": step,
                    "settled_debris": settled_debris,
                    "moved_debris": moved_debris,
                    "collapsed_structures": collapsed_structures,
                },
            )
            return {
                "status": "ok",
                "tick": self._tick_count,
                "dt": step,
                "global_time": self._global_time,
                "settled_debris": settled_debris,
                "moved_debris": moved_debris,
                "collapsed_structures": collapsed_structures,
                "stats": self._stats.to_dict(),
            }

    def reset_structure(self, structure_id: str) -> Tuple[bool, str, Optional[Structure]]:
        """Reset a structure to its initial intact state.

        Restores all nodes and edges to unbroken state, resets stress and
        damage, and clears associated fractures and debris for the structure.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            # Reset all nodes
            for node in structure.nodes:
                node.is_broken = False
                node.stress = 0.0
                node.load = 0.0
                node.displacement = (0.0, 0.0, 0.0)
                node.velocity = (0.0, 0.0, 0.0)
            # Reset all edges
            for edge in structure.edges:
                edge.is_broken = False
                edge.damage = 0.0
                edge.stress = 0.0
                edge.strain = 0.0
                edge.current_length = edge.rest_length
            # Reset structure state
            structure.status = StructureStatus.INTACT.value
            structure.integrity = 1.0
            structure.damage_accumulated = 0.0
            structure.collapse_progress = 0.0
            structure.updated_at = _now()
            # Remove associated fractures
            frac_ids = self._structure_fractures.pop(structure_id, [])
            for fid in frac_ids:
                self._fractures.pop(fid, None)
            # Remove associated debris
            debris_ids = self._structure_debris.pop(structure_id, [])
            for did in debris_ids:
                self._debris.pop(did, None)
            # Mark collapse events as inactive
            coll_ids = self._structure_collapses.get(structure_id, [])
            for cid in coll_ids:
                evt = self._collapse_events.get(cid)
                if evt:
                    evt.is_active = False
            self._emit(
                DestructibleEventKind.STRUCTURE_RESET.value,
                structure_id=structure_id,
                description=f"Structure reset to intact state",
                data={
                    "cleared_fractures": len(frac_ids),
                    "cleared_debris": len(debris_ids),
                },
            )
            self._refresh_stats()
            return True, "reset", structure

    def repair_structure(
        self,
        structure_id: str,
        amount: float = 0.1,
    ) -> Tuple[bool, str, Optional[Structure]]:
        """Repair a structure by restoring integrity and healing damage.

        Heals a fraction of edge damage proportional to the repair amount.
        Broken edges have a chance to be restored if the repair amount is
        sufficient. The structure status is updated after repair.
        """
        with self._lock:
            structure = self._structures.get(structure_id)
            if structure is None:
                return False, "structure_not_found", None
            if structure.status in (
                StructureStatus.DESTROYED.value,
                StructureStatus.RUBBLE.value,
            ):
                return False, "structure_beyond_repair", None
            repair_amt = _clamp(_safe_float(amount, 0.1), 0.0, 1.0)
            edges_repaired = 0
            edges_restored = 0
            for edge in structure.edges:
                if edge.is_broken:
                    # Chance to restore broken edges based on repair amount
                    if repair_amt > 0.3:
                        edge.is_broken = False
                        edge.damage = max(0.0, 1.0 - repair_amt)
                        edge.stress = 0.0
                        edges_restored += 1
                else:
                    if edge.damage > 0.0:
                        edge.damage = max(0.0, edge.damage - repair_amt)
                        edges_repaired += 1
                    if edge.stress > 0.0:
                        edge.stress = max(0.0, edge.stress * (1.0 - repair_amt))
            # Heal node stress
            for node in structure.nodes:
                if node.is_broken and repair_amt > 0.3:
                    node.is_broken = False
                if node.stress > 0.0:
                    node.stress = max(0.0, node.stress * (1.0 - repair_amt))
                if node.load > 0.0:
                    node.load = max(0.0, node.load * (1.0 - repair_amt))
            # Recompute integrity
            structure.integrity = self._compute_structure_integrity(structure)
            self._total_repair_applied += repair_amt * (edges_repaired + edges_restored)
            self._update_structure_status(structure)
            structure.updated_at = _now()
            self._emit(
                DestructibleEventKind.REPAIR_APPLIED.value,
                structure_id=structure_id,
                description=f"Structure repaired by {repair_amt:.2f}",
                data={
                    "repair_amount": repair_amt,
                    "edges_repaired": edges_repaired,
                    "edges_restored": edges_restored,
                    "new_integrity": structure.integrity,
                },
            )
            self._refresh_stats()
            return True, "repaired", structure

    def get_node(
        self,
        structure_id: str,
        node_id: str,
    ) -> Optional[StructureNode]:
        """Return a node by id within a structure, or None if not found."""
        structure = self._structures.get(structure_id)
        if structure is None:
            return None
        return self._get_node(structure, node_id)

    def get_edge(
        self,
        structure_id: str,
        edge_id: str,
    ) -> Optional[StructureEdge]:
        """Return an edge by id within a structure, or None if not found."""
        structure = self._structures.get(structure_id)
        if structure is None:
            return None
        return self._get_edge(structure, edge_id)

    def list_nodes(
        self,
        structure_id: str,
        include_broken: bool = True,
        limit: int = 200,
    ) -> List[StructureNode]:
        """List nodes in a structure, optionally excluding broken ones."""
        cap = max(1, _safe_int(limit, 200))
        structure = self._structures.get(structure_id)
        if structure is None:
            return []
        result: List[StructureNode] = []
        for node in structure.nodes:
            if not include_broken and node.is_broken:
                continue
            result.append(node)
            if len(result) >= cap:
                break
        return result

    def list_edges(
        self,
        structure_id: str,
        include_broken: bool = True,
        limit: int = 200,
    ) -> List[StructureEdge]:
        """List edges in a structure, optionally excluding broken ones."""
        cap = max(1, _safe_int(limit, 200))
        structure = self._structures.get(structure_id)
        if structure is None:
            return []
        result: List[StructureEdge] = []
        for edge in structure.edges:
            if not include_broken and edge.is_broken:
                continue
            result.append(edge)
            if len(result) >= cap:
                break
        return result


# ---------------------------------------------------------------------------
# Module-Level Factory Function
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()
_INSTANCE: Optional[_DestructibleStructureSystem] = None


def get_destructible_structure_system() -> _DestructibleStructureSystem:
    """Return the singleton _DestructibleStructureSystem instance, seeding on first use.

    This is the primary entry point for consumers of the destructible
    structure system. It ensures the singleton is created and seed data is
    loaded before returning the instance.
    """
    global _INSTANCE
    if _INSTANCE is None:
        with _LOCK:
            if _INSTANCE is None:
                _INSTANCE = _DestructibleStructureSystem()
                _INSTANCE.initialize()
    return _INSTANCE


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "MaterialType",
    "FracturePattern",
    "StructureStatus",
    "DebrisStatus",
    "DestructibleEventKind",
    # Data classes
    "MaterialProperties",
    "StructureNode",
    "StructureEdge",
    "Structure",
    "FractureRecord",
    "DebrisPiece",
    "CollapseEvent",
    "DestructibleConfig",
    "DestructibleStats",
    "DestructibleSnapshot",
    "DestructibleEvent",
    # Main system
    "_DestructibleStructureSystem",
    "get_destructible_structure_system",
]