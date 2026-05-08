"""
SparkLabs Engine - Math Utilities

Core math primitives for the SparkLabs AI-native game engine.
Provides linear algebra, geometry, interpolation, and easing
functions used across physics, rendering, animation, and AI
subsystems. Designed as lightweight pure-Python math tools
that require no external dependencies.

Architecture:
  MathUtils
    |-- Vector2 (2D vector with full arithmetic suite)
    |-- Vector3 (3D vector for spatial operations)
    |-- Rect2 (axis-aligned bounding box)
    |-- Transform2D (affine 2D transformation matrix)
    |-- Easing (12 interpolation curves)
    |-- Interpolation (lerp, smoothstep, bezier)
    |-- Geometry2D (point-in-poly, intersection tests)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Vector2:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vector2:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector2:
        if scalar == 0:
            return Vector2(0, 0)
        return Vector2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vector2:
        return Vector2(-self.x, -self.y)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2):
            return False
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalized(self) -> Vector2:
        length = self.length()
        if length == 0:
            return Vector2(0, 0)
        return Vector2(self.x / length, self.y / length)

    def dot(self, other: Vector2) -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vector2) -> float:
        return self.x * other.y - self.y * other.x

    def distance_to(self, other: Vector2) -> float:
        return (self - other).length()

    def distance_squared_to(self, other: Vector2) -> float:
        return (self - other).length_squared()

    def angle(self) -> float:
        return math.atan2(self.y, self.x)

    def angle_to(self, other: Vector2) -> float:
        return math.atan2(other.y - self.y, other.x - self.x)

    def rotate(self, angle: float) -> Vector2:
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Vector2(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a,
        )

    def lerp(self, to: Vector2, t: float) -> Vector2:
        t = max(0.0, min(1.0, t))
        return Vector2(
            self.x + (to.x - self.x) * t,
            self.y + (to.y - self.y) * t,
        )

    def reflect(self, normal: Vector2) -> Vector2:
        d = self.dot(normal)
        return Vector2(
            self.x - 2 * d * normal.x,
            self.y - 2 * d * normal.y,
        )

    def perpendicular(self) -> Vector2:
        return Vector2(-self.y, self.x)

    def clamp_length(self, max_length: float) -> Vector2:
        if self.length_squared() > max_length * max_length:
            return self.normalized() * max_length
        return Vector2(self.x, self.y)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y}

    @staticmethod
    def zero() -> Vector2:
        return Vector2(0, 0)

    @staticmethod
    def one() -> Vector2:
        return Vector2(1, 1)

    @staticmethod
    def up() -> Vector2:
        return Vector2(0, -1)

    @staticmethod
    def down() -> Vector2:
        return Vector2(0, 1)

    @staticmethod
    def left() -> Vector2:
        return Vector2(-1, 0)

    @staticmethod
    def right() -> Vector2:
        return Vector2(1, 0)

    @staticmethod
    def from_angle(angle: float, length: float = 1.0) -> Vector2:
        return Vector2(math.cos(angle) * length, math.sin(angle) * length)

    @staticmethod
    def from_tuple(t: Tuple[float, float]) -> Vector2:
        return Vector2(t[0], t[1])


@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Vector3) -> Vector3:
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3) -> Vector3:
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vector3:
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self) -> Vector3:
        l = self.length()
        if l == 0:
            return Vector3(0, 0, 0)
        return Vector3(self.x / l, self.y / l, self.z / l)

    def dot(self, other: Vector3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3) -> Vector3:
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def lerp(self, to: Vector3, t: float) -> Vector3:
        t = max(0.0, min(1.0, t))
        return Vector3(
            self.x + (to.x - self.x) * t,
            self.y + (to.y - self.y) * t,
            self.z + (to.z - self.z) * t,
        )

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "z": self.z}

    @staticmethod
    def zero() -> Vector3:
        return Vector3(0, 0, 0)


@dataclass
class Rect2:
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    @property
    def position(self) -> Vector2:
        return Vector2(self.x, self.y)

    @property
    def size(self) -> Vector2:
        return Vector2(self.width, self.height)

    @property
    def end(self) -> Vector2:
        return Vector2(self.x + self.width, self.y + self.height)

    @property
    def center(self) -> Vector2:
        return Vector2(self.x + self.width / 2, self.y + self.height / 2)

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def area(self) -> float:
        return self.width * self.height

    def contains_point(self, point: Vector2) -> bool:
        return (
            self.left <= point.x <= self.right
            and self.top <= point.y <= self.bottom
        )

    def contains_rect(self, other: Rect2) -> bool:
        return (
            self.left <= other.left
            and self.right >= other.right
            and self.top <= other.top
            and self.bottom >= other.bottom
        )

    def overlaps(self, other: Rect2) -> bool:
        if self.right <= other.left or other.right <= self.left:
            return False
        if self.bottom <= other.top or other.bottom <= self.top:
            return False
        return True

    def intersection(self, other: Rect2) -> Optional[Rect2]:
        if not self.overlaps(other):
            return None
        x = max(self.left, other.left)
        y = max(self.top, other.top)
        w = min(self.right, other.right) - x
        h = min(self.bottom, other.bottom) - y
        return Rect2(x, y, w, h) if w > 0 and h > 0 else None

    def union(self, other: Rect2) -> Rect2:
        x = min(self.left, other.left)
        y = min(self.top, other.top)
        w = max(self.right, other.right) - x
        h = max(self.bottom, other.bottom) - y
        return Rect2(x, y, w, h)

    def expanded(self, amount: float) -> Rect2:
        return Rect2(
            self.x - amount,
            self.y - amount,
            self.width + amount * 2,
            self.height + amount * 2,
        )

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @staticmethod
    def from_center(center: Vector2, size: Vector2) -> Rect2:
        return Rect2(center.x - size.x / 2, center.y - size.y / 2, size.x, size.y)


@dataclass
class Transform2D:
    """Affine 2D transformation: position, rotation, scale."""

    origin: Vector2 = field(default_factory=Vector2.zero)
    rotation: float = 0.0
    scale: Vector2 = field(default_factory=Vector2.one)
    translation: Vector2 = field(default_factory=Vector2.zero)

    def transform(self, point: Vector2) -> Vector2:
        scaled = Vector2(point.x * self.scale.x, point.y * self.scale.y)
        rotated = scaled.rotate(self.rotation)
        return Vector2(
            rotated.x + self.translation.x,
            rotated.y + self.translation.y,
        )

    def inverse_transform(self, point: Vector2) -> Vector2:
        translated = Vector2(point.x - self.translation.x, point.y - self.translation.y)
        rotated = translated.rotate(-self.rotation)
        return Vector2(
            rotated.x / self.scale.x if self.scale.x != 0 else 0,
            rotated.y / self.scale.y if self.scale.y != 0 else 0,
        )

    def interpolate_with(self, other: Transform2D, t: float) -> Transform2D:
        t = max(0.0, min(1.0, t))
        return Transform2D(
            origin=self.origin.lerp(other.origin, t),
            rotation=self.rotation + (other.rotation - self.rotation) * t,
            scale=self.scale.lerp(other.scale, t),
            translation=self.translation.lerp(other.translation, t),
        )

    @staticmethod
    def identity() -> Transform2D:
        return Transform2D()


class Easing:
    """Collection of 12 easing functions for smooth animation curves."""

    @staticmethod
    def linear(t: float) -> float:
        return t

    @staticmethod
    def ease_in_quad(t: float) -> float:
        return t * t

    @staticmethod
    def ease_out_quad(t: float) -> float:
        return t * (2 - t)

    @staticmethod
    def ease_in_out_quad(t: float) -> float:
        if t < 0.5:
            return 2 * t * t
        return -1 + (4 - 2 * t) * t

    @staticmethod
    def ease_in_cubic(t: float) -> float:
        return t * t * t

    @staticmethod
    def ease_out_cubic(t: float) -> float:
        t -= 1
        return t * t * t + 1

    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        if t < 0.5:
            return 4 * t * t * t
        t -= 1
        return 4 * t * t * t + 1

    @staticmethod
    def ease_in_elastic(t: float) -> float:
        if t == 0 or t == 1:
            return t
        return -math.pow(2, 10 * (t - 1)) * math.sin((t - 1.075) * (2 * math.pi) / 0.3)

    @staticmethod
    def ease_out_elastic(t: float) -> float:
        if t == 0 or t == 1:
            return t
        return math.pow(2, -10 * t) * math.sin((t - 0.075) * (2 * math.pi) / 0.3) + 1

    @staticmethod
    def ease_in_out_elastic(t: float) -> float:
        if t == 0 or t == 1:
            return t
        if t < 0.5:
            return -0.5 * math.pow(2, 20 * t - 10) * math.sin((20 * t - 11.125) * (2 * math.pi) / 4.5)
        return 0.5 * math.pow(2, -20 * t + 10) * math.sin((20 * t - 11.125) * (2 * math.pi) / 4.5) + 1

    @staticmethod
    def ease_in_back(t: float) -> float:
        s = 1.70158
        return t * t * ((s + 1) * t - s)

    @staticmethod
    def ease_out_back(t: float) -> float:
        s = 1.70158
        t -= 1
        return t * t * ((s + 1) * t + s) + 1

    @staticmethod
    def ease_in_out_back(t: float) -> float:
        s = 1.70158 * 1.525
        if t < 0.5:
            return (t * 2) * (t * 2) * ((s + 1) * t * 2 - s) / 2
        t = t * 2 - 2
        return (t * t * ((s + 1) * t + s) + 2) / 2

    @staticmethod
    def ease_in_bounce(t: float) -> float:
        return 1 - Easing.ease_out_bounce(1 - t)

    @staticmethod
    def ease_out_bounce(t: float) -> float:
        if t < 1 / 2.75:
            return 7.5625 * t * t
        elif t < 2 / 2.75:
            t -= 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t -= 2.25 / 2.75
            return 7.5625 * t * t + 0.9375
        else:
            t -= 2.625 / 2.75
            return 7.5625 * t * t + 0.984375

    @staticmethod
    def ease_in_out_bounce(t: float) -> float:
        if t < 0.5:
            return Easing.ease_in_bounce(t * 2) * 0.5
        return Easing.ease_out_bounce(t * 2 - 1) * 0.5 + 0.5

    @classmethod
    def apply(cls, name: str, t: float) -> float:
        t = max(0.0, min(1.0, t))
        func = getattr(cls, name, None)
        if func is None:
            return t
        return func(t)

    @classmethod
    def list_all(cls) -> List[str]:
        return [
            "linear", "ease_in_quad", "ease_out_quad", "ease_in_out_quad",
            "ease_in_cubic", "ease_out_cubic", "ease_in_out_cubic",
            "ease_in_elastic", "ease_out_elastic", "ease_in_out_elastic",
            "ease_in_back", "ease_out_back", "ease_in_out_back",
            "ease_in_bounce", "ease_out_bounce", "ease_in_out_bounce",
        ]


class Interpolation:
    """Value interpolation utilities for smooth transitions."""

    @staticmethod
    def lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    @staticmethod
    def lerp_angle(from_angle: float, to_angle: float, t: float) -> float:
        diff = (to_angle - from_angle) % (2 * math.pi)
        if diff > math.pi:
            diff -= 2 * math.pi
        return from_angle + diff * t

    @staticmethod
    def inverse_lerp(a: float, b: float, value: float) -> float:
        if a == b:
            return 0.0
        return max(0.0, min(1.0, (value - a) / (b - a)))

    @staticmethod
    def smoothstep(edge0: float, edge1: float, x: float) -> float:
        t = Interpolation.inverse_lerp(edge0, edge1, x)
        return t * t * (3 - 2 * t)

    @staticmethod
    def bezier_cubic(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2, t: float) -> Vector2:
        u = 1 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t
        return Vector2(
            uuu * p0.x + 3 * uu * t * p1.x + 3 * u * tt * p2.x + ttt * p3.x,
            uuu * p0.y + 3 * uu * t * p1.y + 3 * u * tt * p2.y + ttt * p3.y,
        )

    @staticmethod
    def remap(value: float, from_min: float, from_max: float, to_min: float, to_max: float) -> float:
        t = Interpolation.inverse_lerp(from_min, from_max, value)
        return Interpolation.lerp(to_min, to_max, t)

    @staticmethod
    def ping_pong(t: float, length: float = 1.0) -> float:
        t = t % (length * 2)
        if t > length:
            return length * 2 - t
        return t


class Geometry2D:
    """2D geometry utility functions."""

    @staticmethod
    def point_in_polygon(point: Vector2, polygon: List[Vector2]) -> bool:
        n = len(polygon)
        if n < 3:
            return False
        inside = False
        j = n - 1
        for i in range(n):
            pi, pj = polygon[i], polygon[j]
            if ((pi.y > point.y) != (pj.y > point.y)) and (
                point.x < (pj.x - pi.x) * (point.y - pi.y) / (pj.y - pi.y) + pi.x
            ):
                inside = not inside
            j = i
        return inside

    @staticmethod
    def segment_intersection(a1: Vector2, a2: Vector2, b1: Vector2, b2: Vector2) -> Optional[Vector2]:
        d1 = a2 - a1
        d2 = b2 - b1
        cross = d1.cross(d2)
        if abs(cross) < 1e-10:
            return None
        t = (b1 - a1).cross(d2) / cross
        u = (b1 - a1).cross(d1) / cross
        if 0 <= t <= 1 and 0 <= u <= 1:
            return Vector2(a1.x + t * d1.x, a1.y + t * d1.y)
        return None

    @staticmethod
    def closest_point_on_segment(point: Vector2, seg_a: Vector2, seg_b: Vector2) -> Vector2:
        ab = seg_b - seg_a
        ap = point - seg_a
        t = ap.dot(ab)
        if t <= 0:
            return seg_a
        denom = ab.length_squared()
        if t >= denom:
            return seg_b
        return Vector2(seg_a.x + ab.x * t / denom, seg_a.y + ab.y * t / denom)

    @staticmethod
    def point_to_segment_distance(point: Vector2, seg_a: Vector2, seg_b: Vector2) -> float:
        closest = Geometry2D.closest_point_on_segment(point, seg_a, seg_b)
        return point.distance_to(closest)

    @staticmethod
    def circle_contains_point(center: Vector2, radius: float, point: Vector2) -> bool:
        return point.distance_squared_to(center) <= radius * radius

    @staticmethod
    def circle_overlaps_circle(c1: Vector2, r1: float, c2: Vector2, r2: float) -> bool:
        return c1.distance_squared_to(c2) <= (r1 + r2) * (r1 + r2)


class MathUtils:
    """
    Central math utility facade for the SparkLabs engine.

    Provides access to all math primitives through a single
    singleton instance. Used by physics, rendering, animation,
    AI pathfinding, and game logic subsystems.
    """

    _instance: Optional["MathUtils"] = None

    def __init__(self):
        self.Vector2 = Vector2
        self.Vector3 = Vector3
        self.Rect2 = Rect2
        self.Transform2D = Transform2D
        self.Easing = Easing
        self.Interpolation = Interpolation
        self.Geometry2D = Geometry2D

    @classmethod
    def get_instance(cls) -> "MathUtils":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def random_range(min_val: float, max_val: float) -> float:
        return min_val + random.random() * (max_val - min_val)

    @staticmethod
    def random_int(min_val: int, max_val: int) -> int:
        return random.randint(min_val, max_val)

    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        return max(min_val, min(max_val, value))

    @staticmethod
    def deg_to_rad(degrees: float) -> float:
        return degrees * math.pi / 180.0

    @staticmethod
    def rad_to_deg(radians: float) -> float:
        return radians * 180.0 / math.pi

    @staticmethod
    def move_toward(current: float, target: float, max_delta: float) -> float:
        diff = target - current
        if abs(diff) <= max_delta:
            return target
        return current + math.copysign(max_delta, diff)

    def get_stats(self) -> dict:
        return {
            "vector_types": ["Vector2", "Vector3"],
            "easing_curves": len(Easing.list_all()),
            "geometry_operations": 6,
        }


def get_math_utils() -> MathUtils:
    return MathUtils.get_instance()
