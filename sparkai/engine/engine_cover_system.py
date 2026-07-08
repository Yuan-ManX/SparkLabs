"""
SparkLabs Engine - Cover System

Manages tactical cover points for shooter and stealth games. Provides
cover quality scoring, flank detection, suppressive fire tracking,
cover degradation, and AI cover selection scoring. Designed for
integration with combat AI, navigation, and level design workflows.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> float:
    return time.time()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _distance_2d(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2)


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_COVER_POINTS = 5000
_MAX_OCCUPANTS = 2000
_MAX_SUPPRESSIONS = 3000
_MAX_EVENTS = 5000


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CoverQuality(str, Enum):
    FULL = "full"
    HALF = "half"
    PARTIAL = "partial"
    NONE = "none"
    DEGRADED = "degraded"


class CoverStance(str, Enum):
    STAND = "stand"
    CROUCH = "crouch"
    PRONE = "prone"
    LEAN_LEFT = "lean_left"
    LEAN_RIGHT = "lean_right"
    ANY = "any"


class CoverDirection(str, Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NORTHEAST = "northeast"
    NORTHWEST = "northwest"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"
    OMNI = "omni"


class CoverMaterial(str, Enum):
    CONCRETE = "concrete"
    BRICK = "brick"
    WOOD = "wood"
    METAL = "metal"
    SAND = "sand"
    GLASS = "glass"
    EARTH = "earth"
    WATER = "water"
    FLESH = "flesh"
    ENERGY = "energy"


class CoverStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    DESTROYED = "destroyed"
    DEGRADED = "degraded"


class CoverEventKind(str, Enum):
    REGISTERED = "registered"
    REMOVED = "removed"
    OCCUPIED = "occupied"
    VACATED = "vacated"
    RESERVED = "reserved"
    SUPPRESSED = "suppressed"
    DEGRADED = "degraded"
    DESTROYED = "destroyed"
    FLANKED = "flanked"
    REPAIRED = "repaired"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class CoverPoint:
    cover_id: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    quality: str = CoverQuality.FULL.value
    stance: str = CoverStance.CROUCH.value
    direction: str = CoverDirection.NORTH.value
    material: str = CoverMaterial.CONCRETE.value
    max_occupants: int = 1
    current_occupants: List[str] = field(default_factory=list)
    health: float = 100.0
    max_health: float = 100.0
    height: float = 1.0
    width: float = 1.5
    status: str = CoverStatus.AVAILABLE.value
    reserved_by: Optional[str] = None
    reserved_until: float = 0.0
    suppression_level: float = 0.0
    last_suppressed: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SuppressionRecord:
    suppression_id: str
    cover_id: str
    source_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    intensity: float = 0.5
    duration: float = 3.0
    timestamp: float = field(default_factory=_now)
    rounds_fired: int = 0
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CoverConfig:
    max_cover_points: int = 2000
    max_occupants_per_point: int = 4
    suppression_decay_rate: float = 0.15
    suppression_threshold: float = 0.7
    flank_detection_range: float = 25.0
    flank_angle_threshold: float = 60.0
    cover_destruction_threshold: float = 30.0
    repair_rate: float = 5.0
    auto_vacate_on_destroy: bool = True
    allow_shared_cover: bool = False
    reservation_timeout: float = 10.0
    degradation_per_hit: float = 8.0
    suppression_damage_factor: float = 0.3

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CoverStats:
    total_cover_points: int = 0
    available_points: int = 0
    occupied_points: int = 0
    destroyed_points: int = 0
    degraded_points: int = 0
    total_occupants: int = 0
    total_suppressions: int = 0
    total_flanks_detected: int = 0
    total_cover_destroyed: int = 0
    total_cover_repaired: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CoverSnapshot:
    cover_points: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CoverEvent:
    event_id: str
    kind: str
    cover_id: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Cover System
# ---------------------------------------------------------------------------

class CoverSystem:
    """Manages tactical cover points with quality scoring and suppressive fire."""

    _instance: Optional["CoverSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._cover_points: Dict[str, CoverPoint] = {}
        self._suppressions: Dict[str, SuppressionRecord] = {}
        self._events: List[CoverEvent] = []
        self._stats = CoverStats()
        self._config = CoverConfig()
        self._tick_count: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "CoverSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed sample cover points for testing."""
        # Concrete wall - full cover
        self._cover_points["cov_wall_north"] = CoverPoint(
            cover_id="cov_wall_north",
            position=(10.0, 0.0, 5.0),
            quality=CoverQuality.FULL.value,
            stance=CoverStance.STAND.value,
            direction=CoverDirection.NORTH.value,
            material=CoverMaterial.CONCRETE.value,
            health=100.0,
            max_health=100.0,
            height=1.8,
            width=3.0,
        )

        # Crate - half cover
        self._cover_points["cov_crate_east"] = CoverPoint(
            cover_id="cov_crate_east",
            position=(15.0, 0.0, 10.0),
            quality=CoverQuality.HALF.value,
            stance=CoverStance.CROUCH.value,
            direction=CoverDirection.EAST.value,
            material=CoverMaterial.WOOD.value,
            health=60.0,
            max_health=60.0,
            height=1.0,
            width=1.2,
        )

        # Sandbag - full cover
        self._cover_points["cov_sandbag_south"] = CoverPoint(
            cover_id="cov_sandbag_south",
            position=(5.0, 0.0, 15.0),
            quality=CoverQuality.FULL.value,
            stance=CoverStance.CROUCH.value,
            direction=CoverDirection.SOUTH.value,
            material=CoverMaterial.SAND.value,
            health=80.0,
            max_health=80.0,
            height=1.1,
            width=2.0,
        )

        # Barrel - partial cover
        self._cover_points["cov_barrel_west"] = CoverPoint(
            cover_id="cov_barrel_west",
            position=(20.0, 0.0, 20.0),
            quality=CoverQuality.PARTIAL.value,
            stance=CoverStance.CROUCH.value,
            direction=CoverDirection.WEST.value,
            material=CoverMaterial.METAL.value,
            health=50.0,
            max_health=50.0,
            height=0.9,
            width=0.6,
        )

        # Pillar - omni directional
        self._cover_points["cov_pillar_center"] = CoverPoint(
            cover_id="cov_pillar_center",
            position=(12.0, 0.0, 12.0),
            quality=CoverQuality.HALF.value,
            stance=CoverStance.STAND.value,
            direction=CoverDirection.OMNI.value,
            material=CoverMaterial.CONCRETE.value,
            health=120.0,
            max_health=120.0,
            height=2.0,
            width=0.8,
        )

        self._stats.total_cover_points = len(self._cover_points)
        self._stats.available_points = len(self._cover_points)
        self._initialized = True

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _emit_event(self, kind: str, cover_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        event = CoverEvent(
            event_id=f"evt_{self._tick_count}_{len(self._events)}",
            kind=kind,
            cover_id=cover_id,
            timestamp=_now(),
            details=details or {},
        )
        self._events.append(event)
        if len(self._events) > _MAX_EVENTS:
            self._events = self._events[-_MAX_EVENTS:]

    def _recompute_stats(self) -> None:
        self._stats.total_cover_points = len(self._cover_points)
        available = 0
        occupied = 0
        destroyed = 0
        degraded = 0
        total_occupants = 0
        for cp in self._cover_points.values():
            total_occupants += len(cp.current_occupants)
            if cp.status == CoverStatus.DESTROYED.value:
                destroyed += 1
            elif cp.status == CoverStatus.DEGRADED.value:
                degraded += 1
            elif cp.status == CoverStatus.OCCUPIED.value:
                occupied += 1
            elif cp.status == CoverStatus.AVAILABLE.value:
                available += 1
        self._stats.available_points = available
        self._stats.occupied_points = occupied
        self._stats.destroyed_points = destroyed
        self._stats.degraded_points = degraded
        self._stats.total_occupants = total_occupants

    def _material_strength_factor(self, material: str) -> float:
        factors = {
            CoverMaterial.CONCRETE.value: 1.0,
            CoverMaterial.BRICK.value: 0.85,
            CoverMaterial.WOOD.value: 0.55,
            CoverMaterial.METAL.value: 1.2,
            CoverMaterial.SAND.value: 0.75,
            CoverMaterial.GLASS.value: 0.15,
            CoverMaterial.EARTH.value: 0.70,
            CoverMaterial.WATER.value: 0.10,
            CoverMaterial.FLESH.value: 0.20,
            CoverMaterial.ENERGY.value: 1.5,
        }
        return factors.get(material, 0.5)

    def _quality_protection_factor(self, quality: str) -> float:
        factors = {
            CoverQuality.FULL.value: 1.0,
            CoverQuality.HALF.value: 0.6,
            CoverQuality.PARTIAL.value: 0.35,
            CoverQuality.NONE.value: 0.0,
            CoverQuality.DEGRADED.value: 0.3,
        }
        return factors.get(quality, 0.3)

    # ------------------------------------------------------------------
    # Cover Lifecycle
    # ------------------------------------------------------------------

    def register_cover(self, cover: CoverPoint) -> CoverPoint:
        with self._init_lock:
            if len(self._cover_points) >= _MAX_COVER_POINTS:
                oldest_id = next(iter(self._cover_points))
                del self._cover_points[oldest_id]
            self._cover_points[cover.cover_id] = cover
            cover.created_at = _now()
            cover.updated_at = _now()
            self._recompute_stats()
            self._emit_event(CoverEventKind.REGISTERED.value, cover.cover_id, {"quality": cover.quality, "position": cover.position})
            return cover

    def get_cover(self, cover_id: str) -> Optional[CoverPoint]:
        return self._cover_points.get(cover_id)

    def list_covers(
        self,
        quality: Optional[str] = None,
        status: Optional[str] = None,
        material: Optional[str] = None,
        limit: int = 100,
    ) -> List[CoverPoint]:
        results = list(self._cover_points.values())
        if quality:
            results = [c for c in results if c.quality == quality]
        if status:
            results = [c for c in results if c.status == status]
        if material:
            results = [c for c in results if c.material == material]
        return results[:max(0, int(limit))]

    def remove_cover(self, cover_id: str) -> bool:
        with self._init_lock:
            if cover_id not in self._cover_points:
                return False
            del self._cover_points[cover_id]
            self._recompute_stats()
            self._emit_event(CoverEventKind.REMOVED.value, cover_id)
            return True

    # ------------------------------------------------------------------
    # Occupancy
    # ------------------------------------------------------------------

    def occupy_cover(self, cover_id: str, occupant_id: str) -> Optional[CoverPoint]:
        cp = self._cover_points.get(cover_id)
        if cp is None:
            return None
        if cp.status == CoverStatus.DESTROYED.value:
            return None
        if occupant_id in cp.current_occupants:
            return cp
        max_occ = max(cp.max_occupants, 1 if not self._config.allow_shared_cover else self._config.max_occupants_per_point)
        if len(cp.current_occupants) >= max_occ:
            return None
        cp.current_occupants.append(occupant_id)
        cp.status = CoverStatus.OCCUPIED.value
        self._emit_event(CoverEventKind.OCCUPIED.value, cover_id, {"occupant": occupant_id})
        cp.updated_at = _now()
        return cp

    def vacate_cover(self, cover_id: str, occupant_id: str) -> Optional[CoverPoint]:
        cp = self._cover_points.get(cover_id)
        if cp is None:
            return None
        if occupant_id in cp.current_occupants:
            cp.current_occupants.remove(occupant_id)
            if not cp.current_occupants and cp.status == CoverStatus.OCCUPIED.value:
                cp.status = CoverStatus.AVAILABLE.value
            self._emit_event(CoverEventKind.VACATED.value, cover_id, {"occupant": occupant_id})
        cp.updated_at = _now()
        return cp

    def reserve_cover(self, cover_id: str, reserved_by: str, duration: Optional[float] = None) -> Optional[CoverPoint]:
        cp = self._cover_points.get(cover_id)
        if cp is None:
            return None
        if cp.status == CoverStatus.DESTROYED.value:
            return None
        cp.reserved_by = reserved_by
        cp.reserved_until = _now() + (duration or self._config.reservation_timeout)
        if cp.status == CoverStatus.AVAILABLE.value:
            cp.status = CoverStatus.RESERVED.value
        self._emit_event(CoverEventKind.RESERVED.value, cover_id, {"reserved_by": reserved_by})
        cp.updated_at = _now()
        return cp

    # ------------------------------------------------------------------
    # Suppression and Damage
    # ------------------------------------------------------------------

    def suppress_cover(
        self,
        cover_id: str,
        source_position: Tuple[float, float, float],
        intensity: float = 0.5,
        duration: float = 3.0,
        rounds_fired: int = 0,
    ) -> Optional[CoverPoint]:
        cp = self._cover_points.get(cover_id)
        if cp is None:
            return None
        sup_id = f"sup_{cover_id}_{len(self._suppressions)}"
        suppression = SuppressionRecord(
            suppression_id=sup_id,
            cover_id=cover_id,
            source_position=source_position,
            intensity=_clamp(intensity, 0.0, 1.0),
            duration=duration,
            rounds_fired=rounds_fired,
        )
        self._suppressions[sup_id] = suppression
        cp.suppression_level = min(1.0, cp.suppression_level + suppression.intensity)
        cp.last_suppressed = _now()
        # Suppression damages cover
        damage = intensity * self._config.suppression_damage_factor * max(rounds_fired, 1) * self._config.degradation_per_hit * 0.1
        cp.health = max(0.0, cp.health - damage)
        if cp.health <= self._config.cover_destruction_threshold:
            cp.status = CoverStatus.DEGRADED.value
            cp.quality = CoverQuality.DEGRADED.value
            self._emit_event(CoverEventKind.DEGRADED.value, cover_id, {"health": cp.health})
        if cp.health <= 0.0:
            cp.status = CoverStatus.DESTROYED.value
            cp.quality = CoverQuality.NONE.value
            if self._config.auto_vacate_on_destroy and cp.current_occupants:
                cp.current_occupants.clear()
            self._stats.total_cover_destroyed += 1
            self._emit_event(CoverEventKind.DESTROYED.value, cover_id)
        else:
            self._emit_event(CoverEventKind.SUPPRESSED.value, cover_id, {"intensity": intensity, "rounds": rounds_fired})
        self._stats.total_suppressions += 1
        cp.updated_at = _now()
        return cp

    def damage_cover(self, cover_id: str, amount: float) -> Optional[CoverPoint]:
        cp = self._cover_points.get(cover_id)
        if cp is None:
            return None
        amount = max(0.0, float(amount))
        cp.health = max(0.0, cp.health - amount)
        if cp.health <= self._config.cover_destruction_threshold and cp.status != CoverStatus.DESTROYED.value:
            cp.status = CoverStatus.DEGRADED.value
            cp.quality = CoverQuality.DEGRADED.value
            self._emit_event(CoverEventKind.DEGRADED.value, cover_id, {"health": cp.health})
        if cp.health <= 0.0 and cp.status != CoverStatus.DESTROYED.value:
            cp.status = CoverStatus.DESTROYED.value
            cp.quality = CoverQuality.NONE.value
            if self._config.auto_vacate_on_destroy and cp.current_occupants:
                cp.current_occupants.clear()
            self._stats.total_cover_destroyed += 1
            self._emit_event(CoverEventKind.DESTROYED.value, cover_id)
        cp.updated_at = _now()
        return cp

    def repair_cover(self, cover_id: str, amount: float = 100.0) -> Optional[CoverPoint]:
        cp = self._cover_points.get(cover_id)
        if cp is None:
            return None
        cp.health = min(cp.max_health, cp.health + max(0.0, float(amount)))
        if cp.health > self._config.cover_destruction_threshold:
            if cp.status == CoverStatus.DEGRADED.value:
                cp.status = CoverStatus.AVAILABLE.value if not cp.current_occupants else CoverStatus.OCCUPIED.value
                cp.quality = CoverQuality.FULL.value if cp.health >= cp.max_health * 0.8 else CoverQuality.HALF.value
            elif cp.status == CoverStatus.DESTROYED.value and cp.health > cp.max_health * 0.5:
                cp.status = CoverStatus.AVAILABLE.value
                cp.quality = CoverQuality.HALF.value
            self._stats.total_cover_repaired += 1
            self._emit_event(CoverEventKind.REPAIRED.value, cover_id, {"health": cp.health})
        cp.updated_at = _now()
        return cp

    # ------------------------------------------------------------------
    # Cover Scoring and Selection
    # ------------------------------------------------------------------

    def score_cover(
        self,
        cover_id: str,
        agent_position: Tuple[float, float, float],
        threat_positions: List[Tuple[float, float, float]],
    ) -> Optional[Dict[str, Any]]:
        """Score a cover point for an agent given threat positions."""
        cp = self._cover_points.get(cover_id)
        if cp is None:
            return None
        if cp.status == CoverStatus.DESTROYED.value:
            return {"cover_id": cover_id, "total_score": 0.0, "reason": "destroyed"}

        # Distance score (closer is better, but not too close)
        dist = _distance_2d(agent_position, cp.position)
        dist_score = _clamp(1.0 - dist / 50.0, 0.0, 1.0)
        if dist < 2.0:
            dist_score *= 0.5

        # Quality score
        quality_score = self._quality_protection_factor(cp.quality)

        # Material score
        material_score = self._material_strength_factor(cp.material)
        material_score = _clamp(material_score, 0.0, 1.0)

        # Health score
        health_score = cp.health / max(cp.max_health, 1.0)

        # Threat protection score
        threat_protection = 0.0
        flank_risk = 0.0
        for threat in threat_positions:
            threat_dist = _distance_2d(threat, cp.position)
            if threat_dist < 5.0:
                threat_protection += 0.1
            else:
                # Check if cover faces away from threat
                threat_angle = math.degrees(math.atan2(threat[2] - cp.position[2], threat[0] - cp.position[0]))
                cover_angle = self._direction_to_angle(cp.direction)
                angle_diff = abs(((threat_angle - cover_angle + 180) % 360) - 180)
                if angle_diff > 90:
                    threat_protection += 1.0
                else:
                    flank_risk += 1.0

        if threat_positions:
            threat_protection /= len(threat_positions)
            flank_risk /= len(threat_positions)
        else:
            threat_protection = 0.5
            flank_risk = 0.0

        # Suppression penalty
        suppression_penalty = cp.suppression_level

        # Occupancy penalty
        occupancy_penalty = 1.0 if cp.status == CoverStatus.OCCUPIED.value and not self._config.allow_shared_cover else 0.0

        # Total score (weighted)
        total = (
            dist_score * 0.25
            + quality_score * 0.20
            + material_score * 0.10
            + health_score * 0.15
            + threat_protection * 0.20
            + (1.0 - flank_risk) * 0.10
            - suppression_penalty * 0.15
            - occupancy_penalty * 0.50
        )
        total = _clamp(total, 0.0, 1.0)

        return {
            "cover_id": cover_id,
            "total_score": round(total, 4),
            "distance": round(dist, 2),
            "dist_score": round(dist_score, 4),
            "quality_score": round(quality_score, 4),
            "material_score": round(material_score, 4),
            "health_score": round(health_score, 4),
            "threat_protection": round(threat_protection, 4),
            "flank_risk": round(flank_risk, 4),
            "suppression_penalty": round(suppression_penalty, 4),
            "occupancy_penalty": round(occupancy_penalty, 4),
        }

    def find_best_cover(
        self,
        agent_position: Tuple[float, float, float],
        threat_positions: List[Tuple[float, float, float]],
        max_distance: float = 30.0,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find the best cover points for an agent near threats."""
        candidates = []
        for cp in self._cover_points.values():
            if cp.status == CoverStatus.DESTROYED.value:
                continue
            dist = _distance_2d(agent_position, cp.position)
            if dist > max_distance:
                continue
            scoring = self.score_cover(cp.cover_id, agent_position, threat_positions)
            if scoring:
                candidates.append(scoring)
        candidates.sort(key=lambda s: s["total_score"], reverse=True)
        return candidates[:max(0, int(limit))]

    def detect_flank(
        self,
        cover_id: str,
        threat_positions: List[Tuple[float, float, float]],
    ) -> Dict[str, Any]:
        """Detect if a cover point is being flanked."""
        cp = self._cover_points.get(cover_id)
        if cp is None:
            return {"cover_id": cover_id, "flanked": False, "flank_count": 0}
        cover_angle = self._direction_to_angle(cp.direction)
        flank_count = 0
        flank_directions = []
        for threat in threat_positions:
            threat_angle = math.degrees(math.atan2(threat[2] - cp.position[2], threat[0] - cp.position[0]))
            angle_diff = abs(((threat_angle - cover_angle + 180) % 360) - 180)
            if angle_diff < 90:
                flank_count += 1
                flank_directions.append(threat_angle)
        if flank_count > 0:
            self._stats.total_flanks_detected += 1
            self._emit_event(CoverEventKind.FLANKED.value, cover_id, {"flank_count": flank_count})
        return {
            "cover_id": cover_id,
            "flanked": flank_count > 0,
            "flank_count": flank_count,
            "flank_directions": [round(d, 1) for d in flank_directions],
        }

    def _direction_to_angle(self, direction: str) -> float:
        mapping = {
            CoverDirection.NORTH.value: 0.0,
            CoverDirection.NORTHEAST.value: 45.0,
            CoverDirection.EAST.value: 90.0,
            CoverDirection.SOUTHEAST.value: 135.0,
            CoverDirection.SOUTH.value: 180.0,
            CoverDirection.SOUTHWEST.value: 225.0,
            CoverDirection.WEST.value: 270.0,
            CoverDirection.NORTHWEST.value: 315.0,
            CoverDirection.OMNI.value: 0.0,
        }
        return mapping.get(direction, 0.0)

    # ------------------------------------------------------------------
    # Simulation Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.016, current_time: Optional[float] = None) -> Dict[str, Any]:
        self._tick_count += 1
        events_emitted = 0
        now = _now()

        # Decay suppression
        for cp in self._cover_points.values():
            if cp.suppression_level > 0.0:
                cp.suppression_level = max(0.0, cp.suppression_level - self._config.suppression_decay_rate * delta_time)

        # Expire reservations
        for cp in self._cover_points.values():
            if cp.status == CoverStatus.RESERVED.value and cp.reserved_until < now:
                cp.reserved_by = None
                cp.reserved_until = 0.0
                cp.status = CoverStatus.AVAILABLE.value

        # Expire suppressions
        expired = []
        for sup_id, sup in self._suppressions.items():
            if now - sup.timestamp > sup.duration:
                sup.active = False
                expired.append(sup_id)
        for sup_id in expired:
            del self._suppressions[sup_id]

        self._stats.tick_count = self._tick_count
        self._recompute_stats()

        return {
            "tick": self._tick_count,
            "cover_points_processed": len(self._cover_points),
            "active_suppressions": len(self._suppressions),
            "events_emitted": events_emitted,
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_suppressions(self, cover_id: Optional[str] = None, limit: int = 50) -> List[SuppressionRecord]:
        results = list(self._suppressions.values())
        if cover_id:
            results = [s for s in results if s.cover_id == cover_id]
        return results[-max(0, int(limit)):]

    def get_config(self) -> CoverConfig:
        return self._config

    def set_config(self, config: CoverConfig) -> CoverConfig:
        with self._init_lock:
            self._config = config
            return self._config

    def list_events(self, limit: int = 100, cover_id: Optional[str] = None) -> List[CoverEvent]:
        results = list(self._events)
        if cover_id:
            results = [e for e in results if e.cover_id == cover_id]
        return results[-max(0, int(limit)):]

    def get_stats(self) -> CoverStats:
        self._recompute_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_cover_points": len(self._cover_points),
            "available_points": sum(1 for c in self._cover_points.values() if c.status == CoverStatus.AVAILABLE.value),
            "occupied_points": sum(1 for c in self._cover_points.values() if c.status == CoverStatus.OCCUPIED.value),
            "active_suppressions": sum(1 for s in self._suppressions.values() if s.active),
            "tick_count": self._tick_count,
            "config": self._config.to_dict(),
        }

    def get_snapshot(self) -> CoverSnapshot:
        self._recompute_stats()
        return CoverSnapshot(
            cover_points=[c.to_dict() for c in list(self._cover_points.values())[:20]],
            stats=self._stats.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> None:
        self._cover_points.clear()
        self._suppressions.clear()
        self._events.clear()
        self._stats = CoverStats()
        self._config = CoverConfig()
        self._tick_count = 0
        self._seed()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_cover_system() -> CoverSystem:
    """Return the singleton CoverSystem instance."""
    return CoverSystem.get_instance()
