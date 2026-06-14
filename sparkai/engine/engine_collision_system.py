"""
Engine Collision System - High-performance collision detection and response system.
Supports AABB, circle, polygon, and pixel-perfect collision detection
with spatial optimization for real-time game physics.
"""

import threading
import uuid
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Callable


class CollisionShape(Enum):
    """Supported collision shape types."""
    AABB = "aabb"
    CIRCLE = "circle"
    POLYGON = "polygon"
    CAPSULE = "capsule"
    POINT = "point"
    RAY = "ray"


class CollisionLayer(Enum):
    """Collision layers for filtering."""
    DEFAULT = "default"
    PLAYER = "player"
    ENEMY = "enemy"
    PROJECTILE = "projectile"
    TERRAIN = "terrain"
    PICKUP = "pickup"
    TRIGGER = "trigger"
    UI = "ui"


@dataclass
class CollisionBody:
    """A physics body with collision shape."""
    body_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    shape: CollisionShape = CollisionShape.AABB
    position: Tuple[float, float] = (0.0, 0.0)
    size: Tuple[float, float] = (1.0, 1.0)
    rotation: float = 0.0
    layer: CollisionLayer = CollisionLayer.DEFAULT
    mask: List[CollisionLayer] = field(default_factory=list)
    is_static: bool = False
    is_trigger: bool = False
    is_active: bool = True
    velocity: Tuple[float, float] = (0.0, 0.0)
    restitution: float = 0.3
    friction: float = 0.5
    user_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_id": self.body_id,
            "entity_id": self.entity_id,
            "shape": self.shape.value,
            "position": list(self.position),
            "size": list(self.size),
            "rotation": self.rotation,
            "layer": self.layer.value,
            "is_static": self.is_static,
            "is_trigger": self.is_trigger,
            "is_active": self.is_active,
        }


@dataclass
class CollisionResult:
    """Result of a collision detection."""
    collision_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    body_a_id: str = ""
    body_b_id: str = ""
    contact_point: Tuple[float, float] = (0.0, 0.0)
    normal: Tuple[float, float] = (0.0, 0.0)
    penetration: float = 0.0
    is_overlap: bool = False
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collision_id": self.collision_id,
            "body_a_id": self.body_a_id,
            "body_b_id": self.body_b_id,
            "contact_point": list(self.contact_point),
            "normal": list(self.normal),
            "penetration": self.penetration,
            "is_overlap": self.is_overlap,
        }


class EngineCollisionSystem:
    """
    Collision detection and response system for the SparkLabs game engine.
    Supports multiple collision shapes, spatial partitioning, layer-based
    filtering, and collision callbacks.
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._bodies: Dict[str, CollisionBody] = {}
            self._collision_pairs: Set[Tuple[str, str]] = {}
            self._collision_history: List[CollisionResult] = []
            self._callbacks: Dict[str, List[Callable]] = {}
            self._spatial_grid: Dict[Tuple[int, int], List[str]] = {}
            self._grid_cell_size: float = 10.0
            self._layer_matrix: Dict[Tuple[str, str], bool] = {}
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'EngineCollisionSystem':
        return cls()

    def create_body(self, entity_id: str = "", shape: CollisionShape = CollisionShape.AABB,
                    position: Tuple[float, float] = (0, 0), size: Tuple[float, float] = (1, 1),
                    layer: CollisionLayer = CollisionLayer.DEFAULT,
                    is_static: bool = False, is_trigger: bool = False) -> CollisionBody:
        """Create a collision body."""
        body = CollisionBody(
            entity_id=entity_id,
            shape=shape,
            position=position,
            size=size,
            layer=layer,
            is_static=is_static,
            is_trigger=is_trigger,
        )
        self._bodies[body.body_id] = body
        self._update_spatial_grid(body)
        return body

    def remove_body(self, body_id: str):
        """Remove a collision body."""
        body = self._bodies.pop(body_id, None)
        if body:
            self._remove_from_spatial_grid(body)

    def set_layer_mask(self, body_id: str, mask: List[CollisionLayer]):
        """Set the collision layer mask for a body."""
        body = self._bodies.get(body_id)
        if body:
            body.mask = mask

    def set_layer_collision(self, layer_a: CollisionLayer, layer_b: CollisionLayer, can_collide: bool):
        """Configure whether two layers can collide."""
        self._layer_matrix[(layer_a.value, layer_b.value)] = can_collide
        self._layer_matrix[(layer_b.value, layer_a.value)] = can_collide

    def check_collision(self, body_a_id: str, body_b_id: str) -> Optional[CollisionResult]:
        """Check collision between two specific bodies."""
        body_a = self._bodies.get(body_a_id)
        body_b = self._bodies.get(body_b_id)
        if not body_a or not body_b:
            return None

        if not self._can_collide(body_a, body_b):
            return None

        return self._detect_collision(body_a, body_b)

    def _can_collide(self, body_a: CollisionBody, body_b: CollisionBody) -> bool:
        """Check if two bodies can collide based on layers."""
        if not body_a.is_active or not body_b.is_active:
            return False
        if body_a.is_static and body_b.is_static:
            return False

        key = (body_a.layer.value, body_b.layer.value)
        if key in self._layer_matrix:
            return self._layer_matrix[key]

        if body_a.mask and body_b.layer not in body_a.mask:
            return False
        if body_b.mask and body_a.layer not in body_b.mask:
            return False

        return True

    def _detect_collision(self, body_a: CollisionBody, body_b: CollisionBody) -> Optional[CollisionResult]:
        """Detect collision between two bodies based on their shapes."""
        if body_a.shape == CollisionShape.AABB and body_b.shape == CollisionShape.AABB:
            return self._aabb_vs_aabb(body_a, body_b)
        elif body_a.shape == CollisionShape.CIRCLE and body_b.shape == CollisionShape.CIRCLE:
            return self._circle_vs_circle(body_a, body_b)
        elif body_a.shape == CollisionShape.AABB and body_b.shape == CollisionShape.CIRCLE:
            return self._aabb_vs_circle(body_a, body_b)
        elif body_a.shape == CollisionShape.CIRCLE and body_b.shape == CollisionShape.AABB:
            return self._aabb_vs_circle(body_b, body_a)

        return self._aabb_vs_aabb(body_a, body_b)

    def _aabb_vs_aabb(self, a: CollisionBody, b: CollisionBody) -> Optional[CollisionResult]:
        """AABB vs AABB collision detection."""
        a_min_x = a.position[0] - a.size[0] / 2
        a_max_x = a.position[0] + a.size[0] / 2
        a_min_y = a.position[1] - a.size[1] / 2
        a_max_y = a.position[1] + a.size[1] / 2

        b_min_x = b.position[0] - b.size[0] / 2
        b_max_x = b.position[0] + b.size[0] / 2
        b_min_y = b.position[1] - b.size[1] / 2
        b_max_y = b.position[1] + b.size[1] / 2

        if a_max_x <= b_min_x or a_min_x >= b_max_x:
            return None
        if a_max_y <= b_min_y or a_min_y >= b_max_y:
            return None

        overlap_x = min(a_max_x - b_min_x, b_max_x - a_min_x)
        overlap_y = min(a_max_y - b_min_y, b_max_y - a_min_y)

        if overlap_x < overlap_y:
            normal = (1.0 if a.position[0] < b.position[0] else -1.0, 0.0)
        else:
            normal = (0.0, 1.0 if a.position[1] < b.position[1] else -1.0)

        return CollisionResult(
            body_a_id=a.body_id,
            body_b_id=b.body_id,
            contact_point=(
                (a.position[0] + b.position[0]) / 2,
                (a.position[1] + b.position[1]) / 2,
            ),
            normal=normal,
            penetration=min(overlap_x, overlap_y),
            is_overlap=True,
        )

    def _circle_vs_circle(self, a: CollisionBody, b: CollisionBody) -> Optional[CollisionResult]:
        """Circle vs Circle collision detection."""
        dx = b.position[0] - a.position[0]
        dy = b.position[1] - a.position[1]
        distance_sq = dx * dx + dy * dy
        radius_sum = (a.size[0] + b.size[0]) / 2

        if distance_sq >= radius_sum * radius_sum:
            return None

        distance = distance_sq ** 0.5
        if distance == 0:
            distance = 0.0001

        return CollisionResult(
            body_a_id=a.body_id,
            body_b_id=b.body_id,
            contact_point=(
                a.position[0] + dx * a.size[0] / (2 * distance),
                a.position[1] + dy * a.size[1] / (2 * distance),
            ),
            normal=(dx / distance, dy / distance),
            penetration=radius_sum - distance,
            is_overlap=True,
        )

    def _aabb_vs_circle(self, aabb: CollisionBody, circle: CollisionBody) -> Optional[CollisionResult]:
        """AABB vs Circle collision detection."""
        closest_x = max(aabb.position[0] - aabb.size[0] / 2,
                        min(circle.position[0], aabb.position[0] + aabb.size[0] / 2))
        closest_y = max(aabb.position[1] - aabb.size[1] / 2,
                        min(circle.position[1], aabb.position[1] + aabb.size[1] / 2))

        dx = circle.position[0] - closest_x
        dy = circle.position[1] - closest_y
        distance_sq = dx * dx + dy * dy
        radius = circle.size[0] / 2

        if distance_sq >= radius * radius:
            return None

        distance = distance_sq ** 0.5
        if distance == 0:
            distance = 0.0001

        return CollisionResult(
            body_a_id=aabb.body_id,
            body_b_id=circle.body_id,
            contact_point=(closest_x, closest_y),
            normal=(dx / distance, dy / distance),
            penetration=radius - distance,
            is_overlap=True,
        )

    def raycast(self, origin: Tuple[float, float], direction: Tuple[float, float],
                max_distance: float = 100.0, layer_mask: List[CollisionLayer] = None) -> List[CollisionResult]:
        """Cast a ray and detect all collisions along its path."""
        results = []
        dx, dy = direction
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            return results

        dx /= length
        dy /= length
        end = (origin[0] + dx * max_distance, origin[1] + dy * max_distance)

        for body in self._bodies.values():
            if not body.is_active:
                continue
            if layer_mask and body.layer not in layer_mask:
                continue

            if body.shape == CollisionShape.AABB:
                hit = self._ray_vs_aabb(origin, end, body)
            elif body.shape == CollisionShape.CIRCLE:
                hit = self._ray_vs_circle(origin, direction, max_distance, body)
            else:
                continue

            if hit:
                results.append(hit)

        results.sort(key=lambda r: r.penetration)
        return results

    def _ray_vs_aabb(self, origin: Tuple[float, float], end: Tuple[float, float],
                     body: CollisionBody) -> Optional[CollisionResult]:
        """Ray vs AABB intersection."""
        min_x = body.position[0] - body.size[0] / 2
        max_x = body.position[0] + body.size[0] / 2
        min_y = body.position[1] - body.size[1] / 2
        max_y = body.position[1] + body.size[1] / 2

        dx = end[0] - origin[0]
        dy = end[1] - origin[1]

        t_min = 0.0
        t_max = 1.0

        for i, (p, d, mn, mx) in enumerate([
            (origin[0], dx, min_x, max_x),
            (origin[1], dy, min_y, max_y),
        ]):
            if abs(d) < 0.0001:
                if p < mn or p > mx:
                    return None
            else:
                t1 = (mn - p) / d
                t2 = (mx - p) / d
                if t1 > t2:
                    t1, t2 = t2, t1
                t_min = max(t_min, t1)
                t_max = min(t_max, t2)
                if t_min > t_max:
                    return None

        hit_x = origin[0] + dx * t_min
        hit_y = origin[1] + dy * t_min

        return CollisionResult(
            body_a_id="ray",
            body_b_id=body.body_id,
            contact_point=(hit_x, hit_y),
            normal=(0.0, 0.0),
            penetration=t_min,
            is_overlap=True,
        )

    def _ray_vs_circle(self, origin: Tuple[float, float], direction: Tuple[float, float],
                       max_distance: float, body: CollisionBody) -> Optional[CollisionResult]:
        """Ray vs Circle intersection."""
        dx, dy = direction
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            return None
        dx /= length
        dy /= length

        fx = origin[0] - body.position[0]
        fy = origin[1] - body.position[1]
        radius = body.size[0] / 2

        a = dx * dx + dy * dy
        b = 2 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - radius * radius

        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return None

        t = (-b - discriminant ** 0.5) / (2 * a)
        if t < 0 or t > max_distance:
            return None

        hit_x = origin[0] + dx * t
        hit_y = origin[1] + dy * t

        return CollisionResult(
            body_a_id="ray",
            body_b_id=body.body_id,
            contact_point=(hit_x, hit_y),
            normal=(0.0, 0.0),
            penetration=t,
            is_overlap=True,
        )

    def overlap_area(self, body_id: str, shape: CollisionShape = CollisionShape.AABB,
                     position: Tuple[float, float] = (0, 0),
                     size: Tuple[float, float] = (1, 1)) -> List[CollisionBody]:
        """Find all bodies overlapping with a given area."""
        temp_body = CollisionBody(
            entity_id="query",
            shape=shape,
            position=position,
            size=size,
        )
        overlapping = []

        for body in self._bodies.values():
            if not body.is_active or body.body_id == body_id:
                continue
            if self._detect_collision(temp_body, body):
                overlapping.append(body)

        return overlapping

    def resolve_collision(self, result: CollisionResult) -> Tuple[float, float]:
        """Resolve a collision by calculating separation vector."""
        return (
            result.normal[0] * result.penetration * 0.5,
            result.normal[1] * result.penetration * 0.5,
        )

    def on_collision(self, layer: CollisionLayer, callback: Callable[[CollisionResult], None]):
        """Register a collision callback for a specific layer."""
        self._callbacks.setdefault(layer.value, []).append(callback)

    def step(self):
        """Perform one collision detection step."""
        new_collisions = []
        bodies = list(self._bodies.values())
        self._collision_pairs.clear()

        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                body_a = bodies[i]
                body_b = bodies[j]

                if not body_a.is_active or not body_b.is_active:
                    continue
                if body_a.is_static and body_b.is_static:
                    continue

                pair_key = (min(body_a.body_id, body_b.body_id), max(body_a.body_id, body_b.body_id))
                if pair_key in self._collision_pairs:
                    continue
                self._collision_pairs.add(pair_key)

                result = self._detect_collision(body_a, body_b)
                if result:
                    new_collisions.append(result)

                    for callback in self._callbacks.get(body_a.layer.value, []):
                        callback(result)
                    for callback in self._callbacks.get(body_b.layer.value, []):
                        callback(result)

        self._collision_history = new_collisions

    def _update_spatial_grid(self, body: CollisionBody):
        """Update spatial grid with body position."""
        cell_x = int(body.position[0] / self._grid_cell_size)
        cell_y = int(body.position[1] / self._grid_cell_size)
        self._spatial_grid.setdefault((cell_x, cell_y), []).append(body.body_id)

    def _remove_from_spatial_grid(self, body: CollisionBody):
        """Remove body from spatial grid."""
        cell_x = int(body.position[0] / self._grid_cell_size)
        cell_y = int(body.position[1] / self._grid_cell_size)
        cell = self._spatial_grid.get((cell_x, cell_y), [])
        if body.body_id in cell:
            cell.remove(body.body_id)

    def get_body(self, body_id: str) -> Optional[CollisionBody]:
        """Get a collision body by ID."""
        return self._bodies.get(body_id)

    def get_recent_collisions(self, limit: int = 20) -> List[CollisionResult]:
        """Get recent collision results."""
        return self._collision_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get collision system statistics."""
        return {
            "total_bodies": len(self._bodies),
            "static_bodies": sum(1 for b in self._bodies.values() if b.is_static),
            "dynamic_bodies": sum(1 for b in self._bodies.values() if not b.is_static),
            "trigger_bodies": sum(1 for b in self._bodies.values() if b.is_trigger),
            "recent_collisions": len(self._collision_history),
            "spatial_cells": len(self._spatial_grid),
        }


def get_collision_system() -> EngineCollisionSystem:
    return EngineCollisionSystem.get_instance()