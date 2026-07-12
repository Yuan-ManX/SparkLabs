"""
SparkLabs Engine - Formation System

Manages group movement formations for RPG and RTS gameplay inside the
SparkLabs AI-native game engine. The system lets designers register
formation templates (line, column, wedge, circle, phalanx, square, and
many more), spawn live formation instances, assign units to tactical
slots, issue movement orders, transition between formation shapes, and
analyze terrain to pick the best layout. A deterministic tick loop
advances marching formations toward their targets and updates slot
positions every frame.

Architecture:
  FormationSystem (singleton)
    |-- FormationType, FormationRole, FormationStatus, UnitType,
       MovementMode, SpacingMode, FormationFacing, TransitionType,
       FormationEventKind
    |-- FormationSlot, FormationTemplate, FormationInstance,
       FormationTransition, UnitAssignment, FormationConfig,
       FormationStats, FormationSnapshot, FormationEvent,
       FormationOrders, TerrainAnalysis
    |-- get_formation_system

Core Capabilities:
  - register_template / get_template / list_templates / remove_template
  - create_formation / get_formation / list_formations / remove_formation
  - assign_unit / unassign_unit / get_assignment / list_assignments /
    auto_assign_slots
  - set_formation_facing / set_formation_spacing / move_formation /
    stop_formation / activate_formation / disband_formation
  - create_transition / get_transition / update_transition /
    complete_transition / remove_transition
  - issue_order / get_order / list_orders / execute_order
  - analyze_terrain / get_terrain_analysis / suggest_formation /
    optimize_spacing
  - get_formation_info / get_status / get_stats / get_snapshot /
    get_config / set_config / tick / reset / list_events

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`FormationSystem.get_instance` or the module-level
:func:`get_formation_system` factory.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_TEMPLATES: int = 2000
_MAX_INSTANCES: int = 10000
_MAX_TRANSITIONS: int = 5000
_MAX_ASSIGNMENTS: int = 100000
_MAX_ORDERS: int = 50000
_MAX_TERRAIN_ANALYSES: int = 10000
_MAX_EVENTS: int = 10000

# Default slot count generated when a template is registered without slots
_DEFAULT_TEMPLATE_SLOT_COUNT: int = 8

# Movement epsilon used by the tick loop to detect arrival
_ARRIVAL_EPSILON: float = 1e-4

# Compass heading -> angle in degrees. North is 0 and rotates clockwise.
_FACING_ANGLES: Dict[str, float] = {
    "north": 0.0,
    "northeast": 45.0,
    "east": 90.0,
    "southeast": 135.0,
    "south": 180.0,
    "southwest": 225.0,
    "west": 270.0,
    "northwest": 315.0,
}

# Terrain groupings used by the deterministic AI helpers.
_OPEN_TERRAINS = (
    "plains", "field", "grassland", "meadow", "desert", "tundra",
    "steppe", "savanna", "prairie",
)
_NARROW_TERRAINS = (
    "canyon", "bridge", "corridor", "narrow", "pass", "ravine",
    "valley", "gorge",
)
_FOREST_TERRAINS = (
    "forest", "woods", "jungle", "swamp", "dense", "marsh",
)

# Preferred slot roles for each unit type. The first available slot whose
# role appears in this list wins; the list is consulted in priority order.
_UNIT_ROLE_PRIORITIES: Dict[str, List[str]] = {
    "tank": ["vanguard", "center", "rear"],
    "cavalry": ["vanguard", "flank_left", "flank_right"],
    "infantry": ["center", "rear", "vanguard"],
    "archer": ["rear", "support"],
    "mage": ["support", "rear"],
    "healer": ["support", "reserve"],
    "scout": ["scout", "flank_left", "flank_right", "skirmisher"],
    "commander": ["leader", "center"],
    "siege": ["rear", "support"],
    "flying": ["scout", "flank_left", "flank_right", "skirmisher"],
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


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


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Serialize a dataclass instance into a plain dict.

    The ``__dataclass_fields__`` attribute is checked BEFORE ``to_dict``
    so that dataclasses which also expose ``to_dict`` do not recurse
    through their own serializer.
    """
    if instance is None:
        return {}
    if hasattr(instance, "__dataclass_fields__"):
        out: Dict[str, Any] = {}
        for name in getattr(instance, "__dataclass_fields__", {}).keys():
            try:
                raw = getattr(instance, name)
            except Exception:
                continue
            out[name] = _to_jsonable(raw)
        return out
    if isinstance(instance, dict):
        return {str(k): _to_jsonable(v) for k, v in instance.items()}
    if hasattr(instance, "to_dict") and callable(instance.to_dict):
        return instance.to_dict()
    return {}


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


def _coerce_facing_angle(value: Any) -> float:
    """Coerce a facing value (compass name or number) into degrees."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return _safe_float(value, 0.0)
    key = str(value).strip().lower()
    if key in _FACING_ANGLES:
        return _FACING_ANGLES[key]
    # Numeric string fallback
    parsed = _safe_float(key, None)  # type: ignore[arg-type]
    if parsed is not None:
        return parsed
    return 0.0


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FormationType(str, Enum):
    """Shape of a formation."""
    LINE = "line"
    COLUMN = "column"
    WEDGE = "wedge"
    CIRCLE = "circle"
    PHALANX = "phalanx"
    SQUARE = "square"
    DIAMOND = "diamond"
    SCATTER = "scatter"
    COLUMN_OF_FILES = "column_of_files"
    LINE_OF_BATTLE = "line_of_battle"
    FLying_WEDGE = "flying_wedge"
    BOX = "box"
    ECHELON = "echelon"
    CUSTOM = "custom"


class FormationRole(str, Enum):
    """Tactical role of a slot within a formation."""
    LEADER = "leader"
    VANGUARD = "vanguard"
    CENTER = "center"
    REAR = "rear"
    FLANK_LEFT = "flank_left"
    FLANK_RIGHT = "flank_right"
    SCOUT = "scout"
    SUPPORT = "support"
    RESERVE = "reserve"
    SKIRMISHER = "skirmisher"


class FormationStatus(str, Enum):
    """Lifecycle status of a formation instance."""
    DRAFT = "draft"
    ACTIVE = "active"
    MARCHING = "marching"
    ENGAGED = "engaged"
    BROKEN = "broken"
    DISBANDED = "disbanded"


class UnitType(str, Enum):
    """Classification of a unit that can occupy a formation slot."""
    INFANTRY = "infantry"
    CAVALRY = "cavalry"
    ARCHER = "archer"
    MAGE = "mage"
    HEALER = "healer"
    TANK = "tank"
    SCOUT = "scout"
    COMMANDER = "commander"
    SIEGE = "siege"
    FLYING = "flying"


class MovementMode(str, Enum):
    """Locomotion style used while marching."""
    WALK = "walk"
    JOG = "jog"
    RUN = "run"
    CHARGE = "charge"
    SNEAK = "sneak"
    TELEPORT = "teleport"


class SpacingMode(str, Enum):
    """Density of spacing between slots."""
    TIGHT = "tight"
    NORMAL = "normal"
    LOOSE = "loose"
    SCATTERED = "scattered"


class FormationFacing(str, Enum):
    """Compass heading of a formation."""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NORTHEAST = "northeast"
    NORTHWEST = "northwest"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"


class TransitionType(str, Enum):
    """How a formation morphs from one shape into another."""
    INSTANT = "instant"
    MORPH = "morph"
    DISSOLVE_AND_REFORM = "dissolve_and_reform"
    WHEEL = "wheel"
    PIVOT = "pivot"
    FALL_BACK = "fall_back"


class FormationEventKind(str, Enum):
    """Audit event types emitted by the formation system."""
    FORMATION_CREATED = "formation_created"
    FORMATION_UPDATED = "formation_updated"
    FORMATION_REMOVED = "formation_removed"
    SLOT_ASSIGNED = "slot_assigned"
    SLOT_REMOVED = "slot_removed"
    FORMATION_ACTIVATED = "formation_activated"
    FORMATION_DISBANDED = "formation_disbanded"
    TRANSITION_STARTED = "transition_started"
    TRANSITION_COMPLETED = "transition_completed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class FormationSlot:
    """A single position within a formation that a unit may occupy."""
    slot_id: str
    role: str = FormationRole.CENTER.value
    unit_id: str = ""
    unit_type: str = ""
    offset_x: float = 0.0
    offset_y: float = 0.0
    offset_z: float = 0.0
    rotation: float = 0.0
    scale: float = 1.0
    occupied: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FormationTemplate:
    """Reusable definition of a formation shape and its slot layout."""
    template_id: str
    name: str
    description: str = ""
    formation_type: str = FormationType.LINE.value
    slots: List[FormationSlot] = field(default_factory=list)
    default_spacing: float = 2.0
    facing: str = FormationFacing.NORTH.value
    min_units: int = 1
    max_units: int = 100
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FormationInstance:
    """A live formation placed in the world."""
    formation_id: str
    template_id: str
    name: str
    leader_id: str = ""
    status: str = FormationStatus.DRAFT.value
    slots: List[FormationSlot] = field(default_factory=list)
    center_x: float = 0.0
    center_y: float = 0.0
    center_z: float = 0.0
    facing: float = 0.0
    spacing: float = 2.0
    movement_mode: str = MovementMode.WALK.value
    speed: float = 1.0
    target_x: float = 0.0
    target_y: float = 0.0
    target_z: float = 0.0
    active: bool = False
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FormationTransition:
    """An in-progress shape change for a formation instance."""
    transition_id: str
    formation_id: str
    from_type: str = FormationType.LINE.value
    to_type: str = FormationType.WEDGE.value
    transition_type: str = TransitionType.MORPH.value
    duration: float = 2.0
    progress: float = 0.0
    active: bool = True
    started_at: str = field(default_factory=_now)
    completed_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class UnitAssignment:
    """A binding between a unit and a formation slot."""
    assignment_id: str
    formation_id: str
    unit_id: str
    slot_id: str = ""
    role: str = FormationRole.CENTER.value
    unit_type: str = UnitType.INFANTRY.value
    assigned_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FormationConfig:
    """Tunable configuration for the formation system."""
    max_templates: int = _MAX_TEMPLATES
    max_instances: int = _MAX_INSTANCES
    max_transitions: int = _MAX_TRANSITIONS
    max_assignments: int = _MAX_ASSIGNMENTS
    max_events: int = _MAX_EVENTS
    default_spacing: float = 2.0
    default_speed: float = 5.0
    auto_assign_slots: bool = False
    enable_transitions: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FormationStats:
    """Roll-up statistics maintained across the system lifetime."""
    total_templates: int = 0
    total_instances: int = 0
    total_transitions: int = 0
    total_assignments: int = 0
    active_formations: int = 0
    marching_formations: int = 0
    engaged_formations: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FormationSnapshot:
    """A point-in-time snapshot of the full system state."""
    timestamp: str
    templates: List[Dict[str, Any]] = field(default_factory=list)
    instances: List[Dict[str, Any]] = field(default_factory=list)
    transitions: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FormationEvent:
    """An internal audit event emitted by the formation system."""
    event_id: str
    timestamp: str
    event_type: str
    formation_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FormationOrders:
    """A movement or combat order issued to a formation."""
    order_id: str
    formation_id: str
    order_type: str = "move"
    target_x: float = 0.0
    target_y: float = 0.0
    target_z: float = 0.0
    facing: float = 0.0
    movement_mode: str = MovementMode.WALK.value
    speed: float = 1.0
    issued_at: str = field(default_factory=_now)
    executed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TerrainAnalysis:
    """Result of analyzing terrain for a formation placement."""
    analysis_id: str
    formation_id: str
    terrain_type: str = "plains"
    width: float = 100.0
    height: float = 100.0
    obstacles: List[Dict[str, Any]] = field(default_factory=list)
    bottleneck_areas: List[Dict[str, Any]] = field(default_factory=list)
    recommended_formation: str = FormationType.LINE.value
    recommended_spacing: float = 2.0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Slot Position Calculation
# ---------------------------------------------------------------------------

def _line_offsets(n: int, spacing: float) -> List[Tuple[str, float, float, float]]:
    """Line: units side by side along the x-axis with the leader centered."""
    result: List[Tuple[str, float, float, float]] = []
    for i in range(n):
        offset_x = (i - n / 2.0) * spacing
        role = FormationRole.LEADER.value if i == n // 2 else FormationRole.CENTER.value
        result.append((role, offset_x, 0.0, 0.0))
    return result


def _column_offsets(n: int, spacing: float) -> List[Tuple[str, float, float, float]]:
    """Column: units in a single file along the y-axis, leader at the front."""
    result: List[Tuple[str, float, float, float]] = []
    for i in range(n):
        offset_y = (i - n / 2.0) * spacing
        role = FormationRole.LEADER.value if i == 0 else FormationRole.CENTER.value
        result.append((role, 0.0, offset_y, 0.0))
    return result


def _wedge_offsets(n: int, spacing: float) -> List[Tuple[str, float, float, float]]:
    """Wedge: V-shape with the leader at the front tip and wings behind."""
    result: List[Tuple[str, float, float, float]] = [
        (FormationRole.LEADER.value, 0.0, 0.0, 0.0)
    ]
    depth = 1
    placed = 1
    while placed < n:
        result.append((FormationRole.FLANK_LEFT.value, -depth * spacing, depth * spacing, 0.0))
        placed += 1
        if placed < n:
            result.append((FormationRole.FLANK_RIGHT.value, depth * spacing, depth * spacing, 0.0))
            placed += 1
        depth += 1
    return result


def _circle_offsets(n: int, spacing: float) -> List[Tuple[str, float, float, float]]:
    """Circle: units arranged evenly around a ring sized to the spacing."""
    result: List[Tuple[str, float, float, float]] = []
    if n <= 0:
        return result
    radius = (spacing * n) / (2.0 * math.pi) if n > 0 else 0.0
    for i in range(n):
        angle = (2.0 * math.pi * i) / n
        offset_x = radius * math.cos(angle)
        offset_y = radius * math.sin(angle)
        role = FormationRole.LEADER.value if i == 0 else FormationRole.SUPPORT.value
        result.append((role, offset_x, offset_y, 0.0))
    return result


def _phalanx_offsets(n: int, spacing: float) -> List[Tuple[str, float, float, float]]:
    """Phalanx: filled grid of rows and columns."""
    result: List[Tuple[str, float, float, float]] = []
    if n <= 0:
        return result
    cols = max(1, int(math.ceil(math.sqrt(n))))
    rows = max(1, int(math.ceil(n / float(cols))))
    for i in range(n):
        row = i // cols
        col = i % cols
        offset_x = (col - (cols - 1) / 2.0) * spacing
        offset_y = (row - (rows - 1) / 2.0) * spacing
        if row == 0 and col == cols // 2:
            role = FormationRole.LEADER.value
        elif row == 0:
            role = FormationRole.VANGUARD.value
        elif row == rows - 1:
            role = FormationRole.REAR.value
        else:
            role = FormationRole.CENTER.value
        result.append((role, offset_x, offset_y, 0.0))
    return result


def _square_offsets(n: int, spacing: float) -> List[Tuple[str, float, float, float]]:
    """Square: hollow square with units distributed around the perimeter."""
    result: List[Tuple[str, float, float, float]] = []
    if n <= 0:
        return result
    side_units = max(1, int(math.ceil(n / 4.0)))
    side_len = side_units * spacing
    half = side_len / 2.0
    for i in range(n):
        t = i / float(n)
        perim = t * 4.0 * side_len
        side_idx = int(perim // side_len) % 4
        local = (perim % side_len) - half
        if side_idx == 0:        # top edge, left to right
            offset_x, offset_y = local, -half
            role = FormationRole.VANGUARD.value
        elif side_idx == 1:      # right edge, top to bottom
            offset_x, offset_y = half, local
            role = FormationRole.FLANK_RIGHT.value
        elif side_idx == 2:      # bottom edge, right to left
            offset_x, offset_y = -local, half
            role = FormationRole.REAR.value
        else:                    # left edge, bottom to top
            offset_x, offset_y = -half, -local
            role = FormationRole.FLANK_LEFT.value
        if i == 0:
            role = FormationRole.LEADER.value
        result.append((role, offset_x, offset_y, 0.0))
    return result


def _diamond_offsets(n: int, spacing: float) -> List[Tuple[str, float, float, float]]:
    """Diamond: a square formation rotated 45 degrees."""
    base = _square_offsets(n, spacing)
    cos45 = math.cos(math.pi / 4.0)
    sin45 = math.sin(math.pi / 4.0)
    result: List[Tuple[str, float, float, float]] = []
    for role, ox, oy, oz in base:
        nx = ox * cos45 - oy * sin45
        ny = ox * sin45 + oy * cos45
        result.append((role, nx, ny, oz))
    return result


def _scatter_offsets(n: int, spacing: float) -> List[Tuple[str, float, float, float]]:
    """Scatter: loosely spread skirmisher positions using a deterministic mix."""
    result: List[Tuple[str, float, float, float]] = []
    spread = max(spacing * 2.0, float(n) * spacing * 0.5)
    for i in range(n):
        seed_val = (i * 9301 + 49297) % 233280
        rx = (seed_val / 233280.0) - 0.5
        ry = ((seed_val * 7 + 1337) % 233280) / 233280.0 - 0.5
        offset_x = rx * spread
        offset_y = ry * spread
        result.append((FormationRole.SKIRMISHER.value, offset_x, offset_y, 0.0))
    return result


def _column_of_files_offsets(n: int, spacing: float) -> List[Tuple[str, float, float, float]]:
    """Column of files: two parallel columns marching forward."""
    result: List[Tuple[str, float, float, float]] = []
    cols = 2
    rows = max(1, int(math.ceil(n / float(cols))))
    for i in range(n):
        col = i % cols
        row = i // cols
        offset_x = (col - (cols - 1) / 2.0) * spacing
        offset_y = (row - (rows - 1) / 2.0) * spacing
        role = FormationRole.LEADER.value if i == 0 else FormationRole.CENTER.value
        result.append((role, offset_x, offset_y, 0.0))
    return result


def _line_of_battle_offsets(n: int, spacing: float) -> List[Tuple[str, float, float, float]]:
    """Line of battle: a wide front rank with a reserve rank behind."""
    result: List[Tuple[str, float, float, float]] = []
    front = max(1, int(math.ceil(n / 2.0)))
    for i in range(n):
        if i < front:
            col = i
            offset_x = (col - (front - 1) / 2.0) * spacing
            offset_y = -spacing / 2.0
            role = FormationRole.LEADER.value if col == front // 2 else FormationRole.VANGUARD.value
        else:
            col = i - front
            reserve = n - front
            offset_x = (col - (reserve - 1) / 2.0) * spacing
            offset_y = spacing / 2.0
            role = FormationRole.RESERVE.value
        result.append((role, offset_x, offset_y, 0.0))
    return result


def _flying_wedge_offsets(n: int, spacing: float) -> List[Tuple[str, float, float, float]]:
    """Flying wedge: a filled triangular block with the leader at the tip."""
    result: List[Tuple[str, float, float, float]] = [
        (FormationRole.LEADER.value, 0.0, 0.0, 0.0)
    ]
    placed = 1
    row = 1
    while placed < n:
        for col in range(row * 2 + 1):
            if placed >= n:
                break
            offset_x = (col - row) * spacing
            offset_y = row * spacing
            role = FormationRole.VANGUARD.value if row == 1 else FormationRole.CENTER.value
            result.append((role, offset_x, offset_y, 0.0))
            placed += 1
        row += 1
    return result


def _echelon_offsets(n: int, spacing: float) -> List[Tuple[str, float, float, float]]:
    """Echelon: a staggered diagonal line."""
    result: List[Tuple[str, float, float, float]] = []
    for i in range(n):
        offset_x = i * spacing
        offset_y = -i * spacing
        role = FormationRole.LEADER.value if i == 0 else FormationRole.CENTER.value
        result.append((role, offset_x, offset_y, 0.0))
    return result


def _compute_slot_offsets(
    formation_type: str,
    count: int,
    spacing: float,
) -> List[Tuple[str, float, float, float]]:
    """Dispatch to the per-shape offset calculator."""
    n = max(0, int(count))
    sp = _safe_float(spacing, 2.0)
    ft = str(formation_type).lower()
    if ft == FormationType.LINE.value:
        return _line_offsets(n, sp)
    if ft == FormationType.COLUMN.value:
        return _column_offsets(n, sp)
    if ft == FormationType.WEDGE.value:
        return _wedge_offsets(n, sp)
    if ft == FormationType.CIRCLE.value:
        return _circle_offsets(n, sp)
    if ft == FormationType.PHALANX.value:
        return _phalanx_offsets(n, sp)
    if ft == FormationType.SQUARE.value:
        return _square_offsets(n, sp)
    if ft == FormationType.DIAMOND.value:
        return _diamond_offsets(n, sp)
    if ft == FormationType.SCATTER.value:
        return _scatter_offsets(n, sp)
    if ft == FormationType.COLUMN_OF_FILES.value:
        return _column_of_files_offsets(n, sp)
    if ft == FormationType.LINE_OF_BATTLE.value:
        return _line_of_battle_offsets(n, sp)
    if ft == FormationType.FLying_WEDGE.value:
        return _flying_wedge_offsets(n, sp)
    if ft == FormationType.BOX.value:
        return _square_offsets(n, sp)
    if ft == FormationType.ECHELON.value:
        return _echelon_offsets(n, sp)
    # CUSTOM and any unknown type fall back to a simple line.
    return _line_offsets(n, sp)


def compute_formation_slots(
    formation_type: str,
    count: int,
    spacing: float = 2.0,
) -> List[FormationSlot]:
    """Build a list of FormationSlot objects for a given shape.

    This is the single source of truth for slot layout math and is used
    both by the seed data and by template registration.
    """
    offsets = _compute_slot_offsets(formation_type, count, spacing)
    slots: List[FormationSlot] = []
    for i, (role, ox, oy, oz) in enumerate(offsets):
        slots.append(FormationSlot(
            slot_id=f"slot_{i:03d}",
            role=role,
            unit_id="",
            unit_type="",
            offset_x=ox,
            offset_y=oy,
            offset_z=oz,
            rotation=0.0,
            scale=1.0,
            occupied=False,
            metadata={},
        ))
    return slots


def recommend_formation_type(
    unit_count: int,
    terrain_type: str = "plains",
    enemy_direction: Optional[str] = None,
) -> str:
    """Deterministically pick the best FormationType value for a situation.

    Open terrain favors line or wedge, narrow terrain favors column, and
    being surrounded favors a defensive circle or square.
    """
    count = max(0, _safe_int(unit_count, 0))
    terrain = str(terrain_type).strip().lower()
    direction = str(enemy_direction).strip().lower() if enemy_direction else ""

    surrounded = direction in ("all", "surrounded", "surrounding", "")
    if direction in ("all", "surrounded"):
        if count >= 12:
            return FormationType.SQUARE.value
        return FormationType.CIRCLE.value

    if terrain in _NARROW_TERRAINS:
        return FormationType.COLUMN.value

    if terrain in _FOREST_TERRAINS:
        # Loose terrain favors a column to keep a clear path.
        return FormationType.COLUMN.value

    # Open terrain defaults.
    if count >= 20:
        return FormationType.PHALANX.value
    if count >= 8:
        return FormationType.LINE.value
    return FormationType.WEDGE.value


# ---------------------------------------------------------------------------
# Formation System (Singleton)
# ---------------------------------------------------------------------------

class FormationSystem:
    """Manages group movement formations for RPG and RTS gameplay.

    The system is thread-safe and implemented as a singleton with
    double-checked locking. ``_init_lock`` guards singleton creation and
    seeding; ``_lock`` guards all mutating operations to keep internal
    dictionaries consistent.
    """

    _instance: Optional["FormationSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._templates: Dict[str, FormationTemplate] = {}
        self._formations: Dict[str, FormationInstance] = {}
        self._transitions: Dict[str, FormationTransition] = {}
        self._assignments: Dict[str, UnitAssignment] = {}
        self._formation_assignments: Dict[str, List[str]] = {}
        self._orders: Dict[str, FormationOrders] = {}
        self._formation_orders: Dict[str, List[str]] = {}
        self._terrain_analyses: Dict[str, TerrainAnalysis] = {}
        self._events: List[FormationEvent] = []
        self._config = FormationConfig()
        self._stats = FormationStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self.initialize()

    @classmethod
    def get_instance(cls) -> "FormationSystem":
        """Return the shared singleton, creating and seeding it if needed."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Explicitly seed the system if it has not been seeded yet."""
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._seed()

    def _seed(self) -> None:
        """Populate the system with a canonical set of formation data."""
        with self._lock:
            if self._initialized:
                return

            # ----------------------------------------------------------
            # Formation Templates (6)
            # ----------------------------------------------------------
            template_seeds: List[Tuple[str, str, str, str, int, float, str, int, int, List[str]]] = [
                ("tpl_line", "Infantry Line", "A broad line of infantry ideal for open fields.",
                 FormationType.LINE.value, 8, 2.0, "north", 2, 32, ["offense", "open"]),
                ("tpl_column", "Marching Column", "A single file column for moving through narrow terrain.",
                 FormationType.COLUMN.value, 8, 2.5, "north", 2, 48, ["travel", "narrow"]),
                ("tpl_wedge", "Assault Wedge", "A V-shaped wedge that punches through enemy lines.",
                 FormationType.WEDGE.value, 7, 2.0, "north", 3, 21, ["offense", "breakthrough"]),
                ("tpl_circle", "Defensive Circle", "A ring formation for all-around defense.",
                 FormationType.CIRCLE.value, 8, 2.0, "north", 4, 24, ["defense", "surrounded"]),
                ("tpl_phalanx", "Shield Phalanx", "A dense grid of shield-bearing infantry.",
                 FormationType.PHALANX.value, 9, 1.5, "north", 9, 36, ["defense", "dense"]),
                ("tpl_square", "Hollow Square", "A hollow square that protects a vulnerable center.",
                 FormationType.SQUARE.value, 8, 2.0, "north", 8, 32, ["defense", "formation"]),
            ]
            for (tpl_id, name, desc, ftype, slot_count, sp, facing,
                 min_u, max_u, tags) in template_seeds:
                slots = compute_formation_slots(ftype, slot_count, sp)
                tpl = FormationTemplate(
                    template_id=tpl_id,
                    name=name,
                    description=desc,
                    formation_type=ftype,
                    slots=slots,
                    default_spacing=sp,
                    facing=facing,
                    min_units=min_u,
                    max_units=max_u,
                    tags=list(tags),
                )
                self._templates[tpl_id] = tpl

            # ----------------------------------------------------------
            # Formation Instances (4)
            # ----------------------------------------------------------
            self._create_seeded_formation(
                "form_line_01", "tpl_line", "Alpha Line", "cmd_01",
                FormationStatus.ACTIVE.value, center_x=0.0, center_y=0.0,
                facing=0.0, spacing=2.0, active=True,
            )
            self._create_seeded_formation(
                "form_column_01", "tpl_column", "Bravo Column", "cmd_02",
                FormationStatus.MARCHING.value, center_x=120.0, center_y=40.0,
                facing=90.0, spacing=2.5, active=True,
                target_x=300.0, target_y=40.0, speed=5.0,
                movement_mode=MovementMode.JOG.value,
            )
            self._create_seeded_formation(
                "form_wedge_01", "tpl_wedge", "Charlie Wedge", "cmd_03",
                FormationStatus.ENGAGED.value, center_x=-60.0, center_y=80.0,
                facing=270.0, spacing=2.0, active=True,
            )
            self._create_seeded_formation(
                "form_circle_01", "tpl_circle", "Delta Reserve", "cmd_04",
                FormationStatus.ACTIVE.value, center_x=200.0, center_y=-50.0,
                facing=180.0, spacing=2.0, active=True,
            )

            # ----------------------------------------------------------
            # Unit Assignments (8)
            # ----------------------------------------------------------
            assignment_seeds: List[Tuple[str, str, str, str, str, str]] = [
                ("asg_01", "form_line_01", "unit_tank_01", "slot_003", FormationRole.VANGUARD.value, UnitType.TANK.value),
                ("asg_02", "form_line_01", "unit_archer_01", "slot_000", FormationRole.REAR.value, UnitType.ARCHER.value),
                ("asg_03", "form_line_01", "unit_inf_01", "slot_004", FormationRole.CENTER.value, UnitType.INFANTRY.value),
                ("asg_04", "form_column_01", "unit_cav_01", "slot_000", FormationRole.LEADER.value, UnitType.CAVALRY.value),
                ("asg_05", "form_column_01", "unit_inf_02", "slot_001", FormationRole.CENTER.value, UnitType.INFANTRY.value),
                ("asg_06", "form_wedge_01", "unit_tank_02", "slot_000", FormationRole.LEADER.value, UnitType.TANK.value),
                ("asg_07", "form_wedge_01", "unit_mage_01", "slot_001", FormationRole.FLANK_LEFT.value, UnitType.MAGE.value),
                ("asg_08", "form_circle_01", "unit_heal_01", "slot_000", FormationRole.LEADER.value, UnitType.HEALER.value),
            ]
            for asg_id, form_id, unit_id, slot_id, role, utype in assignment_seeds:
                formation = self._formations.get(form_id)
                if formation is None:
                    continue
                slot = self._find_slot(formation, slot_id)
                if slot is not None:
                    slot.occupied = True
                    slot.unit_id = unit_id
                    slot.unit_type = utype
                assignment = UnitAssignment(
                    assignment_id=asg_id,
                    formation_id=form_id,
                    unit_id=unit_id,
                    slot_id=slot_id,
                    role=role,
                    unit_type=utype,
                )
                self._assignments[asg_id] = assignment
                self._formation_assignments.setdefault(form_id, []).append(asg_id)

            # ----------------------------------------------------------
            # Transitions (3)
            # ----------------------------------------------------------
            transition_seeds: List[Tuple[str, str, str, str, str, float, float, bool]] = [
                ("trans_01", "form_line_01", FormationType.LINE.value, FormationType.WEDGE.value,
                 TransitionType.MORPH.value, 2.0, 0.35, True),
                ("trans_02", "form_column_01", FormationType.COLUMN.value, FormationType.PHALANX.value,
                 TransitionType.MORPH.value, 3.0, 0.10, True),
                ("trans_03", "form_circle_01", FormationType.CIRCLE.value, FormationType.SQUARE.value,
                 TransitionType.WHEEL.value, 4.0, 0.0, True),
            ]
            for tid, form_id, from_t, to_t, ttype, dur, prog, active in transition_seeds:
                transition = FormationTransition(
                    transition_id=tid,
                    formation_id=form_id,
                    from_type=from_t,
                    to_type=to_t,
                    transition_type=ttype,
                    duration=dur,
                    progress=prog,
                    active=active,
                )
                self._transitions[tid] = transition

            # ----------------------------------------------------------
            # Orders (5)
            # ----------------------------------------------------------
            order_seeds: List[Tuple[str, str, str, float, float, float, float, str, float, bool]] = [
                ("order_01", "form_column_01", "move", 300.0, 40.0, 0.0, 90.0, MovementMode.JOG.value, 5.0, False),
                ("order_02", "form_line_01", "move", 10.0, 0.0, 0.0, 0.0, MovementMode.WALK.value, 2.0, True),
                ("order_03", "form_wedge_01", "charge", -80.0, 80.0, 0.0, 270.0, MovementMode.CHARGE.value, 8.0, True),
                ("order_04", "form_circle_01", "move", 200.0, -80.0, 0.0, 180.0, MovementMode.WALK.value, 3.0, False),
                ("order_05", "form_column_01", "halt", 120.0, 40.0, 0.0, 90.0, MovementMode.WALK.value, 0.0, False),
            ]
            for oid, form_id, otype, tx, ty, tz, facing, mode, spd, executed in order_seeds:
                order = FormationOrders(
                    order_id=oid,
                    formation_id=form_id,
                    order_type=otype,
                    target_x=tx,
                    target_y=ty,
                    target_z=tz,
                    facing=facing,
                    movement_mode=mode,
                    speed=spd,
                    executed=executed,
                )
                self._orders[oid] = order
                self._formation_orders.setdefault(form_id, []).append(oid)

            # ----------------------------------------------------------
            # Terrain Analyses (3)
            # ----------------------------------------------------------
            self._seed_terrain_analysis("terrain_01", "form_line_01", "plains", 120.0, 120.0)
            self._seed_terrain_analysis("terrain_02", "form_column_01", "canyon", 60.0, 200.0)
            self._seed_terrain_analysis("terrain_03", "form_wedge_01", "forest", 100.0, 100.0)

            # ----------------------------------------------------------
            # Events (6)
            # ----------------------------------------------------------
            event_seeds: List[Tuple[str, str, str, str]] = [
                (FormationEventKind.FORMATION_CREATED.value, "form_line_01", "Formation Alpha Line created."),
                (FormationEventKind.FORMATION_ACTIVATED.value, "form_line_01", "Formation Alpha Line activated."),
                (FormationEventKind.SLOT_ASSIGNED.value, "form_wedge_01", "Tank assigned to wedge leader slot."),
                (FormationEventKind.TRANSITION_STARTED.value, "form_line_01", "Line to wedge transition started."),
                (FormationEventKind.FORMATION_CREATED.value, "form_column_01", "Formation Bravo Column created."),
                (FormationEventKind.SLOT_ASSIGNED.value, "form_circle_01", "Healer assigned to circle leader slot."),
            ]
            for kind, form_id, desc in event_seeds:
                self._event_counter += 1
                self._events.append(FormationEvent(
                    event_id=f"fevt_{self._event_counter:08d}",
                    timestamp=_now(),
                    event_type=kind,
                    formation_id=form_id,
                    description=desc,
                ))
            _evict_fifo_list(self._events, _MAX_EVENTS)

            self._refresh_stats()
            self._initialized = True

    def _create_seeded_formation(
        self,
        formation_id: str,
        template_id: str,
        name: str,
        leader_id: str,
        status: str,
        center_x: float = 0.0,
        center_y: float = 0.0,
        center_z: float = 0.0,
        facing: float = 0.0,
        spacing: float = 2.0,
        movement_mode: str = MovementMode.WALK.value,
        speed: float = 1.0,
        target_x: float = 0.0,
        target_y: float = 0.0,
        target_z: float = 0.0,
        active: bool = False,
    ) -> None:
        """Helper used by _seed to build a formation instance from a template."""
        template = self._templates.get(template_id)
        if template is None:
            return
        # Deep-copy the template slots so each instance owns its layout.
        slots = [FormationSlot(
            slot_id=s.slot_id,
            role=s.role,
            unit_id="",
            unit_type="",
            offset_x=s.offset_x,
            offset_y=s.offset_y,
            offset_z=s.offset_z,
            rotation=s.rotation,
            scale=s.scale,
            occupied=False,
            metadata=dict(s.metadata),
        ) for s in template.slots]
        instance = FormationInstance(
            formation_id=formation_id,
            template_id=template_id,
            name=name,
            leader_id=leader_id,
            status=status,
            slots=slots,
            center_x=center_x,
            center_y=center_y,
            center_z=center_z,
            facing=facing,
            spacing=spacing,
            movement_mode=movement_mode,
            speed=speed,
            target_x=target_x,
            target_y=target_y,
            target_z=target_z,
            active=active,
        )
        self._formations[formation_id] = instance

    def _seed_terrain_analysis(
        self,
        analysis_id: str,
        formation_id: str,
        terrain_type: str,
        width: float,
        height: float,
    ) -> None:
        """Helper used by _seed to build a terrain analysis record."""
        unit_count = len(self._formations.get(formation_id).slots) if self._formations.get(formation_id) else 8
        recommended = recommend_formation_type(unit_count, terrain_type, None)
        if terrain_type in _NARROW_TERRAINS:
            recommended_spacing = 1.5
            obstacles = [{"type": "cliff", "x": 0.0, "y": 0.0, "radius": 5.0}]
            bottlenecks = [{"x": width / 2.0, "y": height / 2.0, "width": 8.0}]
        elif terrain_type in _FOREST_TERRAINS:
            recommended_spacing = 3.0
            obstacles = [
                {"type": "tree", "x": 10.0, "y": 10.0, "radius": 1.0},
                {"type": "tree", "x": 30.0, "y": 20.0, "radius": 1.0},
                {"type": "tree", "x": 20.0, "y": 45.0, "radius": 1.0},
            ]
            bottlenecks = []
        else:
            recommended_spacing = 2.0
            obstacles = [{"type": "rock", "x": 50.0, "y": 50.0, "radius": 2.0}]
            bottlenecks = []
        analysis = TerrainAnalysis(
            analysis_id=analysis_id,
            formation_id=formation_id,
            terrain_type=terrain_type,
            width=width,
            height=height,
            obstacles=obstacles,
            bottleneck_areas=bottlenecks,
            recommended_formation=recommended,
            recommended_spacing=recommended_spacing,
        )
        self._terrain_analyses[analysis_id] = analysis

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        formation_id: str = "",
        description: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._event_counter += 1
        event = FormationEvent(
            event_id=f"fevt_{self._event_counter:08d}",
            timestamp=_now(),
            event_type=event_type,
            formation_id=formation_id,
            description=description,
            metadata=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        self._stats.total_templates = len(self._templates)
        self._stats.total_instances = len(self._formations)
        self._stats.total_transitions = len(self._transitions)
        self._stats.total_assignments = len(self._assignments)
        self._stats.active_formations = sum(
            1 for f in self._formations.values() if f.active
        )
        self._stats.marching_formations = sum(
            1 for f in self._formations.values()
            if f.status == FormationStatus.MARCHING.value
        )
        self._stats.engaged_formations = sum(
            1 for f in self._formations.values()
            if f.status == FormationStatus.ENGAGED.value
        )
        self._stats.tick_count = self._tick_count

    @staticmethod
    def _find_slot(formation: FormationInstance, slot_id: str) -> Optional[FormationSlot]:
        for slot in formation.slots:
            if slot.slot_id == slot_id:
                return slot
        return None

    def _find_empty_slot_for_role(
        self,
        formation: FormationInstance,
        role: str,
    ) -> Optional[FormationSlot]:
        """Return the first unoccupied slot whose role matches, else any empty slot."""
        for slot in formation.slots:
            if not slot.occupied and slot.role == role:
                return slot
        for slot in formation.slots:
            if not slot.occupied:
                return slot
        return None

    def _recompute_slots(
        self,
        formation: FormationInstance,
        formation_type: str,
    ) -> None:
        """Rebuild slot offsets for a formation while preserving assignments."""
        # Capture current unit assignments per slot role ordering.
        previous: List[Tuple[str, str, str]] = []
        for slot in formation.slots:
            if slot.occupied and slot.unit_id:
                previous.append((slot.unit_id, slot.unit_type, slot.role))
        new_slots = compute_formation_slots(formation_type, len(formation.slots), formation.spacing)
        formation.slots = new_slots
        # Re-apply units to the front of the new slot list.
        for i, (unit_id, unit_type, _role) in enumerate(previous):
            if i < len(formation.slots):
                formation.slots[i].occupied = True
                formation.slots[i].unit_id = unit_id
                formation.slots[i].unit_type = unit_type

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def register_template(
        self,
        template_id: str,
        name: str,
        formation_type: str,
        description: str = "",
        slots: Optional[List[FormationSlot]] = None,
        default_spacing: float = 2.0,
        facing: str = "north",
        min_units: int = 1,
        max_units: int = 100,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[FormationTemplate]]:
        """Register a new formation template."""
        with self._lock:
            if template_id in self._templates:
                return False, "already_exists", None
            ftype = _coerce_enum(FormationType, formation_type, FormationType.CUSTOM).value
            spacing = max(0.1, _safe_float(default_spacing, self._config.default_spacing))
            facing_str = _coerce_enum(FormationFacing, facing, FormationFacing.NORTH).value
            min_u = max(1, _safe_int(min_units, 1))
            max_u = max(min_u, _safe_int(max_units, min_u))

            if slots is not None:
                slot_list: List[FormationSlot] = []
                for idx, s in enumerate(slots):
                    if isinstance(s, FormationSlot):
                        slot_list.append(FormationSlot(
                            slot_id=s.slot_id or f"slot_{idx:03d}",
                            role=s.role,
                            unit_id=s.unit_id,
                            unit_type=s.unit_type,
                            offset_x=_safe_float(s.offset_x, 0.0),
                            offset_y=_safe_float(s.offset_y, 0.0),
                            offset_z=_safe_float(s.offset_z, 0.0),
                            rotation=_safe_float(s.rotation, 0.0),
                            scale=_safe_float(s.scale, 1.0),
                            occupied=bool(s.occupied),
                            metadata=dict(s.metadata),
                        ))
                    elif isinstance(s, dict):
                        slot_list.append(FormationSlot(
                            slot_id=s.get("slot_id") or f"slot_{idx:03d}",
                            role=str(s.get("role", FormationRole.CENTER.value)),
                            unit_id=str(s.get("unit_id", "")),
                            unit_type=str(s.get("unit_type", "")),
                            offset_x=_safe_float(s.get("offset_x"), 0.0),
                            offset_y=_safe_float(s.get("offset_y"), 0.0),
                            offset_z=_safe_float(s.get("offset_z"), 0.0),
                            rotation=_safe_float(s.get("rotation"), 0.0),
                            scale=_safe_float(s.get("scale"), 1.0),
                            occupied=bool(s.get("occupied", False)),
                            metadata=dict(s.get("metadata", {})),
                        ))
                final_slots = slot_list
            else:
                count = max(min_u, min(max_u, _DEFAULT_TEMPLATE_SLOT_COUNT))
                final_slots = compute_formation_slots(ftype, count, spacing)

            template = FormationTemplate(
                template_id=template_id,
                name=name,
                description=description,
                formation_type=ftype,
                slots=final_slots,
                default_spacing=spacing,
                facing=facing_str,
                min_units=min_u,
                max_units=max_u,
                tags=list(tags) if tags else [],
                metadata=dict(metadata) if metadata else {},
            )
            self._templates[template_id] = template
            _evict_fifo_dict(self._templates, self._config.max_templates)
            self._refresh_stats()
            self._emit(
                FormationEventKind.FORMATION_CREATED.value,
                description=f"Template registered: {template_id}",
                data={"template_id": template_id, "formation_type": ftype},
            )
            return True, "registered", template

    def get_template(self, template_id: str) -> Optional[FormationTemplate]:
        """Return a template by id, or None if it does not exist."""
        return self._templates.get(template_id)

    def list_templates(
        self,
        formation_type: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 100,
    ) -> List[FormationTemplate]:
        """List templates, optionally filtered by formation type or tag."""
        cap = max(1, _safe_int(limit, 100))
        result: List[FormationTemplate] = []
        ftype = None
        if formation_type is not None:
            ftype = _coerce_enum(FormationType, formation_type)
            ftype = ftype.value if ftype else str(formation_type).lower()
        for template in self._templates.values():
            if ftype is not None and template.formation_type != ftype:
                continue
            if tag is not None and tag not in template.tags:
                continue
            result.append(template)
            if len(result) >= cap:
                break
        return result

    def remove_template(self, template_id: str) -> Tuple[bool, str]:
        """Remove a template by id."""
        with self._lock:
            if template_id not in self._templates:
                return False, "not_found"
            del self._templates[template_id]
            self._refresh_stats()
            self._emit(
                FormationEventKind.FORMATION_REMOVED.value,
                description=f"Template removed: {template_id}",
                data={"template_id": template_id},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Formations
    # ------------------------------------------------------------------

    def create_formation(
        self,
        formation_id: str,
        template_id: str,
        name: str,
        leader_id: str,
        center_x: float = 0.0,
        center_y: float = 0.0,
        center_z: float = 0.0,
        facing: float = 0.0,
        spacing: float = 2.0,
        movement_mode: str = "walk",
        speed: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[FormationInstance]]:
        """Spawn a live formation instance from a registered template."""
        with self._lock:
            if formation_id in self._formations:
                return False, "already_exists", None
            template = self._templates.get(template_id)
            if template is None:
                return False, "template_not_found", None
            mode = _coerce_enum(MovementMode, movement_mode, MovementMode.WALK).value
            sp = max(0.1, _safe_float(spacing, template.default_spacing))
            slots = [FormationSlot(
                slot_id=s.slot_id,
                role=s.role,
                unit_id="",
                unit_type="",
                offset_x=s.offset_x,
                offset_y=s.offset_y,
                offset_z=s.offset_z,
                rotation=s.rotation,
                scale=s.scale,
                occupied=False,
                metadata=dict(s.metadata),
            ) for s in template.slots]
            instance = FormationInstance(
                formation_id=formation_id,
                template_id=template_id,
                name=name,
                leader_id=leader_id,
                status=FormationStatus.DRAFT.value,
                slots=slots,
                center_x=_safe_float(center_x, 0.0),
                center_y=_safe_float(center_y, 0.0),
                center_z=_safe_float(center_z, 0.0),
                facing=_safe_float(facing, 0.0),
                spacing=sp,
                movement_mode=mode,
                speed=max(0.0, _safe_float(speed, 1.0)),
                target_x=_safe_float(center_x, 0.0),
                target_y=_safe_float(center_y, 0.0),
                target_z=_safe_float(center_z, 0.0),
                active=False,
                metadata=dict(metadata) if metadata else {},
            )
            self._formations[formation_id] = instance
            _evict_fifo_dict(self._formations, self._config.max_instances)
            self._refresh_stats()
            self._emit(
                FormationEventKind.FORMATION_CREATED.value,
                formation_id=formation_id,
                description=f"Formation created: {name}",
                data={"formation_id": formation_id, "template_id": template_id},
            )
            return True, "created", instance

    def get_formation(self, formation_id: str) -> Optional[FormationInstance]:
        """Return a formation instance by id."""
        return self._formations.get(formation_id)

    def list_formations(
        self,
        status: Optional[str] = None,
        active: Optional[bool] = None,
        limit: int = 100,
    ) -> List[FormationInstance]:
        """List formation instances, optionally filtered by status or active flag."""
        cap = max(1, _safe_int(limit, 100))
        status_value = None
        if status is not None:
            coerced = _coerce_enum(FormationStatus, status)
            status_value = coerced.value if coerced else str(status).lower()
        result: List[FormationInstance] = []
        for formation in self._formations.values():
            if status_value is not None and formation.status != status_value:
                continue
            if active is not None and formation.active != active:
                continue
            result.append(formation)
            if len(result) >= cap:
                break
        return result

    def remove_formation(self, formation_id: str) -> Tuple[bool, str]:
        """Remove a formation instance and its associated assignments."""
        with self._lock:
            if formation_id not in self._formations:
                return False, "not_found"
            del self._formations[formation_id]
            # Remove assignments bound to this formation.
            stale_ids = [aid for aid, a in self._assignments.items() if a.formation_id == formation_id]
            for aid in stale_ids:
                del self._assignments[aid]
            self._formation_assignments.pop(formation_id, None)
            # Remove orders bound to this formation.
            stale_orders = [oid for oid, o in self._orders.items() if o.formation_id == formation_id]
            for oid in stale_orders:
                del self._orders[oid]
            self._formation_orders.pop(formation_id, None)
            # Remove transitions bound to this formation.
            stale_trans = [tid for tid, t in self._transitions.items() if t.formation_id == formation_id]
            for tid in stale_trans:
                del self._transitions[tid]
            self._refresh_stats()
            self._emit(
                FormationEventKind.FORMATION_REMOVED.value,
                formation_id=formation_id,
                description=f"Formation removed: {formation_id}",
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Assignments
    # ------------------------------------------------------------------

    def assign_unit(
        self,
        formation_id: str,
        unit_id: str,
        slot_id: str = "",
        role: str = "center",
        unit_type: str = "infantry",
    ) -> Tuple[bool, str, Optional[UnitAssignment]]:
        """Assign a unit to a slot within a formation."""
        with self._lock:
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "formation_not_found", None
            # Reject duplicate unit assignment within the same formation.
            for existing in self._assignments.values():
                if existing.formation_id == formation_id and existing.unit_id == unit_id:
                    return False, "unit_already_assigned", None
            role_value = _coerce_enum(FormationRole, role, FormationRole.CENTER).value
            utype = _coerce_enum(UnitType, unit_type, UnitType.INFANTRY).value

            target_slot: Optional[FormationSlot] = None
            if slot_id:
                target_slot = self._find_slot(formation, slot_id)
                if target_slot is None:
                    return False, "slot_not_found", None
                if target_slot.occupied:
                    return False, "slot_occupied", None
            else:
                target_slot = self._find_empty_slot_for_role(formation, role_value)
                if target_slot is None:
                    return False, "no_empty_slot", None

            target_slot.occupied = True
            target_slot.unit_id = unit_id
            target_slot.unit_type = utype
            assignment_id = _new_id("asg")
            assignment = UnitAssignment(
                assignment_id=assignment_id,
                formation_id=formation_id,
                unit_id=unit_id,
                slot_id=target_slot.slot_id,
                role=target_slot.role,
                unit_type=utype,
            )
            self._assignments[assignment_id] = assignment
            self._formation_assignments.setdefault(formation_id, []).append(assignment_id)
            _evict_fifo_dict(self._assignments, self._config.max_assignments)
            formation.updated_at = _now()
            self._refresh_stats()
            self._emit(
                FormationEventKind.SLOT_ASSIGNED.value,
                formation_id=formation_id,
                description=f"Unit {unit_id} assigned to slot {target_slot.slot_id}",
                data={"assignment_id": assignment_id, "unit_id": unit_id},
            )
            return True, "assigned", assignment

    def unassign_unit(self, formation_id: str, unit_id: str) -> Tuple[bool, str]:
        """Remove a unit assignment from a formation."""
        with self._lock:
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "formation_not_found"
            target_assignment: Optional[UnitAssignment] = None
            target_aid = ""
            for aid, assignment in self._assignments.items():
                if assignment.formation_id == formation_id and assignment.unit_id == unit_id:
                    target_assignment = assignment
                    target_aid = aid
                    break
            if target_assignment is None:
                return False, "assignment_not_found"
            slot = self._find_slot(formation, target_assignment.slot_id)
            if slot is not None:
                slot.occupied = False
                slot.unit_id = ""
                slot.unit_type = ""
            del self._assignments[target_aid]
            bucket = self._formation_assignments.get(formation_id)
            if bucket and target_aid in bucket:
                bucket.remove(target_aid)
            formation.updated_at = _now()
            self._refresh_stats()
            self._emit(
                FormationEventKind.SLOT_REMOVED.value,
                formation_id=formation_id,
                description=f"Unit {unit_id} unassigned from formation",
                data={"unit_id": unit_id},
            )
            return True, "unassigned"

    def get_assignment(self, assignment_id: str) -> Optional[UnitAssignment]:
        """Return a unit assignment by id."""
        return self._assignments.get(assignment_id)

    def list_assignments(
        self,
        formation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[UnitAssignment]:
        """List assignments, optionally filtered by formation."""
        cap = max(1, _safe_int(limit, 100))
        result: List[UnitAssignment] = []
        for assignment in self._assignments.values():
            if formation_id is not None and assignment.formation_id != formation_id:
                continue
            result.append(assignment)
            if len(result) >= cap:
                break
        return result

    # ------------------------------------------------------------------
    # Formation manipulation
    # ------------------------------------------------------------------

    def set_formation_facing(
        self,
        formation_id: str,
        facing: Any,
    ) -> Tuple[bool, str, Optional[FormationInstance]]:
        """Set the facing (compass name or angle) of a formation."""
        with self._lock:
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "not_found", None
            formation.facing = _coerce_facing_angle(facing)
            formation.updated_at = _now()
            self._emit(
                FormationEventKind.FORMATION_UPDATED.value,
                formation_id=formation_id,
                description=f"Facing set to {formation.facing}",
                data={"facing": formation.facing},
            )
            return True, "updated", formation

    def set_formation_spacing(
        self,
        formation_id: str,
        spacing: float,
    ) -> Tuple[bool, str, Optional[FormationInstance]]:
        """Set the spacing of a formation and recompute slot offsets."""
        with self._lock:
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "not_found", None
            new_spacing = max(0.1, _safe_float(spacing, formation.spacing))
            formation.spacing = new_spacing
            # Recompute offsets for the current shape using the template type.
            template = self._templates.get(formation.template_id)
            ftype = template.formation_type if template else FormationType.CUSTOM.value
            self._recompute_slots(formation, ftype)
            formation.updated_at = _now()
            self._emit(
                FormationEventKind.FORMATION_UPDATED.value,
                formation_id=formation_id,
                description=f"Spacing set to {new_spacing}",
                data={"spacing": new_spacing},
            )
            return True, "updated", formation

    def move_formation(
        self,
        formation_id: str,
        target_x: float,
        target_y: float,
        target_z: float = 0.0,
        movement_mode: str = "walk",
        speed: float = 1.0,
    ) -> Tuple[bool, str, Optional[FormationInstance]]:
        """Order a formation to march toward a target position."""
        with self._lock:
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "not_found", None
            if not formation.active:
                return False, "not_active", None
            mode = _coerce_enum(MovementMode, movement_mode, MovementMode.WALK).value
            formation.target_x = _safe_float(target_x, 0.0)
            formation.target_y = _safe_float(target_y, 0.0)
            formation.target_z = _safe_float(target_z, 0.0)
            formation.movement_mode = mode
            formation.speed = max(0.0, _safe_float(speed, formation.speed))
            if formation.status not in (
                FormationStatus.ENGAGED.value,
                FormationStatus.BROKEN.value,
                FormationStatus.DISBANDED.value,
            ):
                formation.status = FormationStatus.MARCHING.value
            formation.updated_at = _now()
            self._emit(
                FormationEventKind.FORMATION_UPDATED.value,
                formation_id=formation_id,
                description=f"Formation moving to ({formation.target_x}, {formation.target_y})",
                data={"target_x": formation.target_x, "target_y": formation.target_y},
            )
            return True, "moving", formation

    def stop_formation(self, formation_id: str) -> Tuple[bool, str, Optional[FormationInstance]]:
        """Halt a marching formation at its current position."""
        with self._lock:
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "not_found", None
            formation.target_x = formation.center_x
            formation.target_y = formation.center_y
            formation.target_z = formation.center_z
            if formation.status == FormationStatus.MARCHING.value:
                formation.status = FormationStatus.ACTIVE.value
            formation.updated_at = _now()
            self._emit(
                FormationEventKind.FORMATION_UPDATED.value,
                formation_id=formation_id,
                description="Formation stopped",
            )
            return True, "stopped", formation

    def activate_formation(self, formation_id: str) -> Tuple[bool, str]:
        """Activate a formation so it can receive orders."""
        with self._lock:
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "not_found"
            if formation.status == FormationStatus.DISBANDED.value:
                return False, "disbanded"
            formation.active = True
            if formation.status == FormationStatus.DRAFT.value:
                formation.status = FormationStatus.ACTIVE.value
            formation.updated_at = _now()
            self._refresh_stats()
            self._emit(
                FormationEventKind.FORMATION_ACTIVATED.value,
                formation_id=formation_id,
                description="Formation activated",
            )
            return True, "activated"

    def disband_formation(self, formation_id: str) -> Tuple[bool, str]:
        """Disband a formation, freeing its units and deactivating it."""
        with self._lock:
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "not_found"
            formation.active = False
            formation.status = FormationStatus.DISBANDED.value
            for slot in formation.slots:
                slot.occupied = False
                slot.unit_id = ""
                slot.unit_type = ""
            # Drop assignments for this formation.
            stale_ids = [aid for aid, a in self._assignments.items() if a.formation_id == formation_id]
            for aid in stale_ids:
                del self._assignments[aid]
            self._formation_assignments.pop(formation_id, None)
            formation.updated_at = _now()
            self._refresh_stats()
            self._emit(
                FormationEventKind.FORMATION_DISBANDED.value,
                formation_id=formation_id,
                description="Formation disbanded",
            )
            return True, "disbanded"

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def create_transition(
        self,
        transition_id: str,
        formation_id: str,
        to_type: str,
        transition_type: str = "morph",
        duration: float = 2.0,
    ) -> Tuple[bool, str, Optional[FormationTransition]]:
        """Begin a shape transition for a formation."""
        with self._lock:
            if not self._config.enable_transitions:
                return False, "transitions_disabled", None
            if transition_id in self._transitions:
                return False, "already_exists", None
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "formation_not_found", None
            template = self._templates.get(formation.template_id)
            from_type = template.formation_type if template else FormationType.CUSTOM.value
            to_t = _coerce_enum(FormationType, to_type, FormationType.CUSTOM).value
            ttype = _coerce_enum(TransitionType, transition_type, TransitionType.MORPH).value
            transition = FormationTransition(
                transition_id=transition_id,
                formation_id=formation_id,
                from_type=from_type,
                to_type=to_t,
                transition_type=ttype,
                duration=max(0.0, _safe_float(duration, 2.0)),
                progress=0.0,
                active=True,
            )
            self._transitions[transition_id] = transition
            _evict_fifo_dict(self._transitions, self._config.max_transitions)
            self._refresh_stats()
            self._emit(
                FormationEventKind.TRANSITION_STARTED.value,
                formation_id=formation_id,
                description=f"Transition {from_type} -> {to_t} started",
                data={"transition_id": transition_id, "to_type": to_t},
            )
            return True, "created", transition

    def get_transition(self, transition_id: str) -> Optional[FormationTransition]:
        """Return a transition by id."""
        return self._transitions.get(transition_id)

    def update_transition(
        self,
        transition_id: str,
        progress: float,
    ) -> Tuple[bool, str, Optional[FormationTransition]]:
        """Advance a transition's progress value."""
        with self._lock:
            transition = self._transitions.get(transition_id)
            if transition is None:
                return False, "not_found", None
            transition.progress = _clamp(_safe_float(progress, 0.0), 0.0, 1.0)
            if transition.progress >= 1.0:
                return self.complete_transition(transition_id)
            return True, "updated", transition

    def complete_transition(
        self,
        transition_id: str,
    ) -> Tuple[bool, str, Optional[FormationInstance]]:
        """Finalize a transition, applying the new shape to the formation."""
        with self._lock:
            transition = self._transitions.get(transition_id)
            if transition is None:
                return False, "not_found", None
            transition.progress = 1.0
            transition.active = False
            transition.completed_at = _now()
            formation = self._formations.get(transition.formation_id)
            if formation is not None:
                self._recompute_slots(formation, transition.to_type)
                formation.updated_at = _now()
            self._refresh_stats()
            self._emit(
                FormationEventKind.TRANSITION_COMPLETED.value,
                formation_id=transition.formation_id,
                description=f"Transition to {transition.to_type} completed",
                data={"transition_id": transition_id, "to_type": transition.to_type},
            )
            return True, "completed", formation

    def remove_transition(self, transition_id: str) -> Tuple[bool, str]:
        """Remove a transition record."""
        with self._lock:
            if transition_id not in self._transitions:
                return False, "not_found"
            del self._transitions[transition_id]
            self._refresh_stats()
            return True, "removed"

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def issue_order(
        self,
        formation_id: str,
        order_type: str,
        target_x: float = 0.0,
        target_y: float = 0.0,
        target_z: float = 0.0,
        facing: float = 0.0,
        movement_mode: str = "walk",
        speed: float = 1.0,
    ) -> Tuple[bool, str, Optional[FormationOrders]]:
        """Issue a movement or combat order to a formation."""
        with self._lock:
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "formation_not_found", None
            mode = _coerce_enum(MovementMode, movement_mode, MovementMode.WALK).value
            order_id = _new_id("order")
            order = FormationOrders(
                order_id=order_id,
                formation_id=formation_id,
                order_type=str(order_type),
                target_x=_safe_float(target_x, 0.0),
                target_y=_safe_float(target_y, 0.0),
                target_z=_safe_float(target_z, 0.0),
                facing=_safe_float(facing, 0.0),
                movement_mode=mode,
                speed=max(0.0, _safe_float(speed, 1.0)),
            )
            self._orders[order_id] = order
            self._formation_orders.setdefault(formation_id, []).append(order_id)
            self._emit(
                FormationEventKind.FORMATION_UPDATED.value,
                formation_id=formation_id,
                description=f"Order '{order_type}' issued",
                data={"order_id": order_id, "order_type": order_type},
            )
            return True, "issued", order

    def get_order(self, order_id: str) -> Optional[FormationOrders]:
        """Return an order by id."""
        return self._orders.get(order_id)

    def list_orders(
        self,
        formation_id: Optional[str] = None,
        executed: Optional[bool] = None,
        limit: int = 100,
    ) -> List[FormationOrders]:
        """List orders, optionally filtered by formation or execution state."""
        cap = max(1, _safe_int(limit, 100))
        result: List[FormationOrders] = []
        for order in self._orders.values():
            if formation_id is not None and order.formation_id != formation_id:
                continue
            if executed is not None and order.executed != executed:
                continue
            result.append(order)
            if len(result) >= cap:
                break
        return result

    def execute_order(self, order_id: str) -> Tuple[bool, str, Optional[FormationInstance]]:
        """Apply a pending order to its formation and mark it executed."""
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                return False, "order_not_found", None
            if order.executed:
                return False, "already_executed", None
            formation = self._formations.get(order.formation_id)
            if formation is None:
                return False, "formation_not_found", None
            if order.order_type == "halt":
                formation.target_x = formation.center_x
                formation.target_y = formation.center_y
                formation.target_z = formation.center_z
                if formation.status == FormationStatus.MARCHING.value:
                    formation.status = FormationStatus.ACTIVE.value
            else:
                formation.target_x = order.target_x
                formation.target_y = order.target_y
                formation.target_z = order.target_z
                formation.facing = order.facing
                formation.movement_mode = order.movement_mode
                formation.speed = order.speed
                if formation.active and formation.status not in (
                    FormationStatus.ENGAGED.value,
                    FormationStatus.DISBANDED.value,
                ):
                    formation.status = FormationStatus.MARCHING.value
            order.executed = True
            formation.updated_at = _now()
            self._emit(
                FormationEventKind.FORMATION_UPDATED.value,
                formation_id=formation.formation_id,
                description=f"Order '{order.order_type}' executed",
                data={"order_id": order_id},
            )
            return True, "executed", formation

    # ------------------------------------------------------------------
    # Terrain analysis and AI helpers
    # ------------------------------------------------------------------

    def analyze_terrain(
        self,
        formation_id: str,
        terrain_type: str = "plains",
        width: float = 100.0,
        height: float = 100.0,
        obstacles: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[bool, str, Optional[TerrainAnalysis]]:
        """Analyze terrain and recommend a formation shape and spacing."""
        with self._lock:
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "formation_not_found", None
            unit_count = len(formation.slots)
            recommended = recommend_formation_type(unit_count, terrain_type, None)
            if terrain_type in _NARROW_TERRAINS:
                recommended_spacing = 1.5
                bottlenecks = [{"x": width / 2.0, "y": height / 2.0, "width": 8.0}]
            elif terrain_type in _FOREST_TERRAINS:
                recommended_spacing = 3.0
                bottlenecks = []
            else:
                recommended_spacing = 2.0
                bottlenecks = []
            analysis_id = _new_id("terrain")
            analysis = TerrainAnalysis(
                analysis_id=analysis_id,
                formation_id=formation_id,
                terrain_type=str(terrain_type),
                width=max(0.0, _safe_float(width, 100.0)),
                height=max(0.0, _safe_float(height, 100.0)),
                obstacles=list(obstacles) if obstacles else [],
                bottleneck_areas=bottlenecks,
                recommended_formation=recommended,
                recommended_spacing=recommended_spacing,
            )
            self._terrain_analyses[analysis_id] = analysis
            _evict_fifo_dict(self._terrain_analyses, _MAX_TERRAIN_ANALYSES)
            self._emit(
                FormationEventKind.FORMATION_UPDATED.value,
                formation_id=formation_id,
                description=f"Terrain analyzed: {terrain_type}",
                data={"analysis_id": analysis_id, "recommended": recommended},
            )
            return True, "analyzed", analysis

    def get_terrain_analysis(self, analysis_id: str) -> Optional[TerrainAnalysis]:
        """Return a terrain analysis by id."""
        return self._terrain_analyses.get(analysis_id)

    def auto_assign_slots(
        self,
        formation_id: str,
    ) -> Tuple[bool, str, List[UnitAssignment]]:
        """Auto-assign a formation's units to optimal slots by unit type.

        Tanks move to the vanguard, archers to the rear, scouts to the
        flanks, and so on. Existing assignments are reshuffled in place.
        """
        with self._lock:
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "formation_not_found", []
            assignment_ids = list(self._formation_assignments.get(formation_id, []))
            assignments = [self._assignments[aid] for aid in assignment_ids if aid in self._assignments]
            if not assignments:
                return False, "no_units", []
            # Clear slot occupancy.
            for slot in formation.slots:
                slot.occupied = False
                slot.unit_id = ""
                slot.unit_type = ""
            used_slot_ids: set = set()
            new_assignments: List[UnitAssignment] = []
            # Sort so that commanders and leaders are placed first.
            priority_order = [
                UnitType.COMMANDER.value,
                UnitType.TANK.value,
                UnitType.CAVALRY.value,
                UnitType.INFANTRY.value,
                UnitType.ARCHER.value,
                UnitType.MAGE.value,
                UnitType.SIEGE.value,
                UnitType.HEALER.value,
                UnitType.SCOUT.value,
                UnitType.FLYING.value,
            ]
            def _priority_key(a: UnitAssignment) -> Tuple[int, str]:
                try:
                    return (priority_order.index(a.unit_type), a.unit_id)
                except ValueError:
                    return (len(priority_order), a.unit_id)
            sorted_assignments = sorted(assignments, key=_priority_key)
            for assignment in sorted_assignments:
                priorities = _UNIT_ROLE_PRIORITIES.get(assignment.unit_type, [FormationRole.CENTER.value])
                placed = False
                for priority_role in priorities:
                    for slot in formation.slots:
                        if slot.slot_id in used_slot_ids:
                            continue
                        if slot.role == priority_role:
                            slot.occupied = True
                            slot.unit_id = assignment.unit_id
                            slot.unit_type = assignment.unit_type
                            assignment.slot_id = slot.slot_id
                            assignment.role = slot.role
                            used_slot_ids.add(slot.slot_id)
                            new_assignments.append(assignment)
                            placed = True
                            break
                    if placed:
                        break
                if not placed:
                    # Fall back to any remaining empty slot.
                    for slot in formation.slots:
                        if slot.slot_id not in used_slot_ids:
                            slot.occupied = True
                            slot.unit_id = assignment.unit_id
                            slot.unit_type = assignment.unit_type
                            assignment.slot_id = slot.slot_id
                            assignment.role = slot.role
                            used_slot_ids.add(slot.slot_id)
                            new_assignments.append(assignment)
                            placed = True
                            break
                if not placed:
                    # No slot available; leave the unit unassigned in place.
                    assignment.slot_id = ""
            formation.updated_at = _now()
            self._emit(
                FormationEventKind.SLOT_ASSIGNED.value,
                formation_id=formation_id,
                description=f"Auto-assigned {len(new_assignments)} units to slots",
                data={"count": len(new_assignments)},
            )
            return True, "auto_assigned", new_assignments

    def suggest_formation(
        self,
        unit_count: int,
        terrain_type: str = "plains",
        enemy_direction: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[FormationTemplate]]:
        """Suggest the best formation template for a tactical situation."""
        recommended = recommend_formation_type(unit_count, terrain_type, enemy_direction)
        count = max(0, _safe_int(unit_count, 0))
        # Prefer a template whose capacity fits the unit count.
        for template in self._templates.values():
            if template.formation_type == recommended:
                if template.min_units <= count <= template.max_units:
                    return True, "suggested", template
        # Fall back to any template of the recommended shape.
        for template in self._templates.values():
            if template.formation_type == recommended:
                return True, "suggested", template
        return False, "no_match", None

    def optimize_spacing(
        self,
        formation_id: str,
        terrain_type: str = "plains",
    ) -> Tuple[bool, str, Optional[FormationInstance]]:
        """Optimize a formation's spacing for the given terrain type."""
        with self._lock:
            formation = self._formations.get(formation_id)
            if formation is None:
                return False, "not_found", None
            terrain = str(terrain_type).strip().lower()
            if terrain in _NARROW_TERRAINS:
                new_spacing = 1.5  # tight to fit through bottlenecks
            elif terrain in _FOREST_TERRAINS:
                new_spacing = 3.0  # loose to navigate around trees
            else:
                new_spacing = 2.0  # normal for open ground
            formation.spacing = new_spacing
            template = self._templates.get(formation.template_id)
            ftype = template.formation_type if template else FormationType.CUSTOM.value
            self._recompute_slots(formation, ftype)
            formation.updated_at = _now()
            self._emit(
                FormationEventKind.FORMATION_UPDATED.value,
                formation_id=formation_id,
                description=f"Spacing optimized to {new_spacing} for {terrain}",
                data={"spacing": new_spacing, "terrain_type": terrain},
            )
            return True, "optimized", formation

    def get_formation_info(self, formation_id: str) -> Optional[Dict[str, Any]]:
        """Return a summary of a formation with slot and assignment counts."""
        formation = self._formations.get(formation_id)
        if formation is None:
            return None
        total_slots = len(formation.slots)
        occupied_slots = sum(1 for s in formation.slots if s.occupied)
        assignment_ids = self._formation_assignments.get(formation_id, [])
        order_ids = self._formation_orders.get(formation_id, [])
        transitions = [
            t.to_dict() for t in self._transitions.values()
            if t.formation_id == formation_id
        ]
        return {
            "formation_id": formation.formation_id,
            "name": formation.name,
            "template_id": formation.template_id,
            "leader_id": formation.leader_id,
            "status": formation.status,
            "active": formation.active,
            "formation_type": self._templates.get(formation.template_id).formation_type
            if self._templates.get(formation.template_id) else FormationType.CUSTOM.value,
            "center": [formation.center_x, formation.center_y, formation.center_z],
            "target": [formation.target_x, formation.target_y, formation.target_z],
            "facing": formation.facing,
            "spacing": formation.spacing,
            "movement_mode": formation.movement_mode,
            "speed": formation.speed,
            "total_slots": total_slots,
            "occupied_slots": occupied_slots,
            "assignment_count": len(assignment_ids),
            "order_count": len(order_ids),
            "transitions": transitions,
            "created_at": formation.created_at,
            "updated_at": formation.updated_at,
        }

    # ------------------------------------------------------------------
    # Status, stats, snapshot, config
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a lightweight status dictionary."""
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "templates": len(self._templates),
                "formations": len(self._formations),
                "transitions": len(self._transitions),
                "assignments": len(self._assignments),
                "orders": len(self._orders),
                "terrain_analyses": len(self._terrain_analyses),
                "events": len(self._events),
                "tick_count": self._tick_count,
                "config": self._config.to_dict(),
            }

    def get_stats(self) -> FormationStats:
        """Return aggregate statistics."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> FormationSnapshot:
        """Return a point-in-time snapshot of the full system state."""
        with self._lock:
            self._refresh_stats()
            return FormationSnapshot(
                timestamp=_now(),
                templates=[t.to_dict() for t in list(self._templates.values())[-100:]],
                instances=[f.to_dict() for f in list(self._formations.values())[-100:]],
                transitions=[t.to_dict() for t in list(self._transitions.values())[-100:]],
                events=[e.to_dict() for e in self._events[-100:]],
                stats=self._stats.to_dict(),
            )

    def get_config(self) -> FormationConfig:
        """Return the current configuration."""
        return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, FormationConfig]:
        """Update tunable configuration fields by keyword."""
        with self._lock:
            known = set(self._config.__dataclass_fields__.keys())
            applied: List[str] = []
            for key, value in kwargs.items():
                if key not in known:
                    continue
                if key in ("max_templates", "max_instances", "max_transitions",
                           "max_assignments", "max_events"):
                    setattr(self._config, key, max(1, _safe_int(value, getattr(self._config, key))))
                elif key in ("default_spacing", "default_speed"):
                    setattr(self._config, key, max(0.0, _safe_float(value, getattr(self._config, key))))
                elif key in ("auto_assign_slots", "enable_transitions"):
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
                FormationEventKind.FORMATION_UPDATED.value,
                description="Configuration updated",
                data={"fields": applied},
            )
            return True, "updated", self._config

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[FormationEvent]:
        """Return the most recent events, newest last."""
        cap = max(1, _safe_int(limit, 100))
        return list(self._events[-cap:])

    # ------------------------------------------------------------------
    # Tick and lifecycle
    # ------------------------------------------------------------------

    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        """Advance the simulation by one tick.

        Marching formations move toward their targets, active transitions
        advance their progress, and statistics are refreshed.
        """
        with self._lock:
            self._tick_count += 1
            step = max(0.0, _safe_float(dt, 0.016))
            moved: List[str] = []
            arrived: List[str] = []
            for formation in self._formations.values():
                if not formation.active:
                    continue
                if formation.status != FormationStatus.MARCHING.value:
                    continue
                dx = formation.target_x - formation.center_x
                dy = formation.target_y - formation.center_y
                dz = formation.target_z - formation.center_z
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                if dist <= _ARRIVAL_EPSILON:
                    formation.status = FormationStatus.ACTIVE.value
                    arrived.append(formation.formation_id)
                    formation.updated_at = _now()
                    continue
                travel = formation.speed * step
                if travel >= dist:
                    formation.center_x = formation.target_x
                    formation.center_y = formation.target_y
                    formation.center_z = formation.target_z
                    formation.status = FormationStatus.ACTIVE.value
                    arrived.append(formation.formation_id)
                else:
                    formation.center_x += (dx / dist) * travel
                    formation.center_y += (dy / dist) * travel
                    formation.center_z += (dz / dist) * travel
                    moved.append(formation.formation_id)
                formation.updated_at = _now()

            # Advance active transitions proportionally to dt.
            completed_transitions: List[str] = []
            for transition in self._transitions.values():
                if not transition.active:
                    continue
                if transition.duration <= 0:
                    completed_transitions.append(transition.transition_id)
                    continue
                transition.progress = _clamp(
                    transition.progress + (step / transition.duration), 0.0, 1.0
                )
                if transition.progress >= 1.0:
                    completed_transitions.append(transition.transition_id)
            for tid in completed_transitions:
                self.complete_transition(tid)

            self._refresh_stats()
            self._emit(
                FormationEventKind.FORMATION_UPDATED.value,
                description=f"Tick #{self._tick_count}",
                data={
                    "tick": self._tick_count,
                    "dt": step,
                    "moved": moved,
                    "arrived": arrived,
                    "completed_transitions": completed_transitions,
                },
            )
            return {
                "status": "ok",
                "tick": self._tick_count,
                "dt": step,
                "moved": moved,
                "arrived": arrived,
                "completed_transitions": completed_transitions,
                "marching_formations": self._stats.marching_formations,
                "active_formations": self._stats.active_formations,
                "stats": self._stats.to_dict(),
            }

    def reset(self) -> None:
        """Clear all system state and re-seed the canonical dataset."""
        with self._lock:
            self._templates.clear()
            self._formations.clear()
            self._transitions.clear()
            self._assignments.clear()
            self._formation_assignments.clear()
            self._orders.clear()
            self._formation_orders.clear()
            self._terrain_analyses.clear()
            self._events.clear()
            self._config = FormationConfig()
            self._stats = FormationStats()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_formation_system() -> FormationSystem:
    """Return the shared FormationSystem singleton instance."""
    return FormationSystem.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "FormationType",
    "FormationRole",
    "FormationStatus",
    "UnitType",
    "MovementMode",
    "SpacingMode",
    "FormationFacing",
    "TransitionType",
    "FormationEventKind",
    # Data classes
    "FormationSlot",
    "FormationTemplate",
    "FormationInstance",
    "FormationTransition",
    "UnitAssignment",
    "FormationConfig",
    "FormationStats",
    "FormationSnapshot",
    "FormationEvent",
    "FormationOrders",
    "TerrainAnalysis",
    # Main system
    "FormationSystem",
    "get_formation_system",
    # Module-level utilities
    "compute_formation_slots",
    "recommend_formation_type",
]
