"""
SparkLabs Engine - Spline System

Parametric curve pathing for AI-native games. Supports multiple
interpolation types for smooth camera paths, AI patrol routes,
track generation, and procedural geometry placement.

Architecture:
  SplineSystem
    |-- SplineEvaluator (parametric curve evaluation engine)
    |-- ControlPointManager (point insertion and removal)
    |-- LengthCalculator (arc-length parameterization)
    |-- UniformSampler (evenly spaced point distribution)

Spline Types:
  - LINEAR, BEZIER, CATMULL_ROM, HERMITE, B_SPLINE
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SplineType(Enum):
    LINEAR = "linear"
    BEZIER = "bezier"
    CATMULL_ROM = "catmull_rom"
    HERMITE = "hermite"
    B_SPLINE = "b_spline"


@dataclass
class SplineControlPoint:
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    tangent_in_x: float = 0.0
    tangent_in_y: float = 0.0
    tangent_in_z: float = 0.0
    tangent_out_x: float = 0.0
    tangent_out_y: float = 0.0
    tangent_out_z: float = 0.0
    tension: float = 0.0
    continuity: float = 0.0
    bias: float = 0.0

    @property
    def position(self) -> Tuple[float, float, float]:
        return (self.position_x, self.position_y, self.position_z)

    @property
    def tangent_in(self) -> Tuple[float, float, float]:
        return (self.tangent_in_x, self.tangent_in_y, self.tangent_in_z)

    @property
    def tangent_out(self) -> Tuple[float, float, float]:
        return (self.tangent_out_x, self.tangent_out_y, self.tangent_out_z)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": list(self.position),
            "tangent_in": list(self.tangent_in),
            "tangent_out": list(self.tangent_out),
            "tension": self.tension,
            "continuity": self.continuity,
            "bias": self.bias,
        }


@dataclass
class SplinePath:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    spline_type: SplineType = SplineType.CATMULL_ROM
    control_points: List[SplineControlPoint] = field(default_factory=list)
    closed_loop: bool = False
    resolution: int = 32

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "spline_type": self.spline_type.value,
            "control_point_count": len(self.control_points),
            "closed_loop": self.closed_loop,
            "resolution": self.resolution,
        }


class SplineSystem:
    _instance: Optional[SplineSystem] = None

    def __init__(self):
        self._paths: Dict[str, SplinePath] = {}
        self._evaluation_cache: Dict[str, List[Tuple[float, float, float]]] = {}
        self._total_evaluations: int = 0

    @classmethod
    def get_instance(cls) -> SplineSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_path(
        self,
        name: str,
        spline_type: SplineType = SplineType.CATMULL_ROM,
        closed_loop: bool = False,
        resolution: int = 32,
    ) -> str:
        path = SplinePath(
            name=name,
            spline_type=spline_type,
            closed_loop=closed_loop,
            resolution=resolution,
        )
        self._paths[path.id] = path
        return path.id

    def remove_path(self, path_id: str) -> bool:
        if path_id not in self._paths:
            return False
        del self._paths[path_id]
        self._evaluation_cache.pop(path_id, None)
        return True

    def add_control_point(
        self,
        path_id: str,
        position: Tuple[float, float, float],
        tangent_in: Optional[Tuple[float, float, float]] = None,
        tangent_out: Optional[Tuple[float, float, float]] = None,
        tension: float = 0.0,
        continuity: float = 0.0,
        bias: float = 0.0,
    ) -> bool:
        path = self._paths.get(path_id)
        if path is None:
            return False

        ti = tangent_in or (0.0, 0.0, 0.0)
        to = tangent_out or (0.0, 0.0, 0.0)

        point = SplineControlPoint(
            position_x=position[0],
            position_y=position[1],
            position_z=position[2],
            tangent_in_x=ti[0],
            tangent_in_y=ti[1],
            tangent_in_z=ti[2],
            tangent_out_x=to[0],
            tangent_out_y=to[1],
            tangent_out_z=to[2],
            tension=tension,
            continuity=continuity,
            bias=bias,
        )
        path.control_points.append(point)
        self._evaluation_cache.pop(path_id, None)
        return True

    def remove_control_point(self, path_id: str, index: int) -> bool:
        path = self._paths.get(path_id)
        if path is None or index < 0 or index >= len(path.control_points):
            return False
        path.control_points.pop(index)
        self._evaluation_cache.pop(path_id, None)
        return True

    def evaluate_at(self, path_id: str, t: float) -> Optional[Tuple[float, float, float]]:
        path = self._paths.get(path_id)
        if path is None or len(path.control_points) < 2:
            return None

        t = max(0.0, min(1.0, t))
        self._total_evaluations += 1

        if path.spline_type == SplineType.LINEAR:
            return self._evaluate_linear(path, t)
        elif path.spline_type == SplineType.BEZIER:
            return self._evaluate_bezier(path, t)
        elif path.spline_type == SplineType.CATMULL_ROM:
            return self._evaluate_catmull_rom(path, t)
        elif path.spline_type == SplineType.HERMITE:
            return self._evaluate_hermite(path, t)
        elif path.spline_type == SplineType.B_SPLINE:
            return self._evaluate_bspline(path, t)
        return None

    def _evaluate_linear(
        self, path: SplinePath, t: float
    ) -> Tuple[float, float, float]:
        points = path.control_points
        if t >= 1.0:
            return points[-1].position
        if t <= 0.0:
            return points[0].position

        segment_count = len(points) - 1
        local_t = t * segment_count
        idx = min(int(local_t), segment_count - 1)
        local_t -= idx

        p0 = points[idx].position
        p1 = points[idx + 1].position
        return (
            p0[0] + (p1[0] - p0[0]) * local_t,
            p0[1] + (p1[1] - p0[1]) * local_t,
            p0[2] + (p1[2] - p0[2]) * local_t,
        )

    def _evaluate_bezier(
        self, path: SplinePath, t: float
    ) -> Tuple[float, float, float]:
        points = path.control_points
        if len(points) < 2:
            return points[0].position if points else (0.0, 0.0, 0.0)

        if len(points) == 3:
            p0, c1, p1 = points
            u = 1.0 - t
            return (
                u * u * p0.position_x + 2 * u * t * c1.position_x + t * t * p1.position_x,
                u * u * p0.position_y + 2 * u * t * c1.position_y + t * t * p1.position_y,
                u * u * p0.position_z + 2 * u * t * c1.position_z + t * t * p1.position_z,
            )

        if len(points) == 4:
            p0, c1, c2, p1 = points
            u = 1.0 - t
            return (
                u * u * u * p0.position_x + 3 * u * u * t * c1.position_x
                + 3 * u * t * t * c2.position_x + t * t * t * p1.position_x,
                u * u * u * p0.position_y + 3 * u * u * t * c1.position_y
                + 3 * u * t * t * c2.position_y + t * t * t * p1.position_y,
                u * u * u * p0.position_z + 3 * u * u * t * c1.position_z
                + 3 * u * t * t * c2.position_z + t * t * t * p1.position_z,
            )

        return points[0].position

    def _evaluate_catmull_rom(
        self, path: SplinePath, t: float
    ) -> Tuple[float, float, float]:
        points = path.control_points
        n = len(points)

        if path.closed_loop:
            extended = [points[-1]] + points + [points[0], points[1]]
        else:
            extended = [points[0]] + points + [points[-1]]

        segment_count = n - 1 if not path.closed_loop else n
        if t >= 1.0:
            return points[-1].position
        if t <= 0.0:
            return points[0].position

        local_t = t * segment_count
        idx = min(int(local_t), segment_count - 1)
        local_t -= idx

        idx += 1

        p0 = extended[idx - 1].position
        p1 = extended[idx].position
        p2 = extended[idx + 1].position
        p3 = extended[idx + 2].position

        tt = local_t * local_t
        ttt = tt * local_t

        q0 = -0.5 * ttt + tt - 0.5 * local_t
        q1 = 1.5 * ttt - 2.5 * tt + 1.0
        q2 = -1.5 * ttt + 2.0 * tt + 0.5 * local_t
        q3 = 0.5 * ttt - 0.5 * tt

        return (
            q0 * p0[0] + q1 * p1[0] + q2 * p2[0] + q3 * p3[0],
            q0 * p0[1] + q1 * p1[1] + q2 * p2[1] + q3 * p3[1],
            q0 * p0[2] + q1 * p1[2] + q2 * p2[2] + q3 * p3[2],
        )

    def _evaluate_hermite(
        self, path: SplinePath, t: float
    ) -> Tuple[float, float, float]:
        points = path.control_points
        if t >= 1.0:
            return points[-1].position
        if t <= 0.0:
            return points[0].position

        segment_count = len(points) - 1
        local_t = t * segment_count
        idx = min(int(local_t), segment_count - 1)
        local_t -= idx

        p0 = points[idx]
        p1 = points[idx + 1]

        tt = local_t * local_t
        ttt = tt * local_t

        h00 = 2 * ttt - 3 * tt + 1
        h10 = ttt - 2 * tt + local_t
        h01 = -2 * ttt + 3 * tt
        h11 = ttt - tt

        tangent_scale = 1.0
        m0 = p0.tangent_out if p0.tangent_out != (0.0, 0.0, 0.0) else (
            (p1.position_x - p0.position_x) * tangent_scale,
            (p1.position_y - p0.position_y) * tangent_scale,
            (p1.position_z - p0.position_z) * tangent_scale,
        )
        m1 = p1.tangent_in if p1.tangent_in != (0.0, 0.0, 0.0) else (
            (p1.position_x - points[max(0, idx - 1)].position_x) * tangent_scale,
            (p1.position_y - points[max(0, idx - 1)].position_y) * tangent_scale,
            (p1.position_z - points[max(0, idx - 1)].position_z) * tangent_scale,
        )

        return (
            h00 * p0.position_x + h10 * m0[0] + h01 * p1.position_x + h11 * m1[0],
            h00 * p0.position_y + h10 * m0[1] + h01 * p1.position_y + h11 * m1[1],
            h00 * p0.position_z + h10 * m0[2] + h01 * p1.position_z + h11 * m1[2],
        )

    def _evaluate_bspline(
        self, path: SplinePath, t: float
    ) -> Tuple[float, float, float]:
        points = path.control_points
        n = len(points)
        if n < 4:
            return self._evaluate_linear(path, t)

        if t >= 1.0:
            return points[-1].position
        if t <= 0.0:
            return points[0].position

        if path.closed_loop:
            working_points = points + points[:3]
        else:
            working_points = points

        segment_count = len(working_points) - 3
        local_t = t * segment_count
        idx = min(int(local_t), segment_count - 1)
        local_t -= idx

        p0 = working_points[idx].position
        p1 = working_points[idx + 1].position
        p2 = working_points[idx + 2].position
        p3 = working_points[idx + 3].position

        tt = local_t * local_t
        ttt = tt * local_t

        return (
            ((-ttt + 3 * tt - 3 * local_t + 1) * p0[0]
             + (3 * ttt - 6 * tt + 4) * p1[0]
             + (-3 * ttt + 3 * tt + 3 * local_t + 1) * p2[0]
             + ttt * p3[0]) / 6.0,
            ((-ttt + 3 * tt - 3 * local_t + 1) * p0[1]
             + (3 * ttt - 6 * tt + 4) * p1[1]
             + (-3 * ttt + 3 * tt + 3 * local_t + 1) * p2[1]
             + ttt * p3[1]) / 6.0,
            ((-ttt + 3 * tt - 3 * local_t + 1) * p0[2]
             + (3 * ttt - 6 * tt + 4) * p1[2]
             + (-3 * ttt + 3 * tt + 3 * local_t + 1) * p2[2]
             + ttt * p3[2]) / 6.0,
        )

    def get_total_length(self, path_id: str, sample_count: int = 100) -> float:
        path = self._paths.get(path_id)
        if path is None or len(path.control_points) < 2:
            return 0.0

        total = 0.0
        prev = None
        for i in range(sample_count + 1):
            t = i / sample_count
            pt = self.evaluate_at(path_id, t)
            if pt is None:
                continue
            if prev is not None:
                dx = pt[0] - prev[0]
                dy = pt[1] - prev[1]
                dz = pt[2] - prev[2]
                total += math.sqrt(dx * dx + dy * dy + dz * dz)
            prev = pt

        return total

    def get_uniform_points(self, path_id: str, count: int) -> List[Tuple[float, float, float]]:
        if count <= 0:
            return []

        points: List[Tuple[float, float, float]] = []
        if count == 1:
            pt = self.evaluate_at(path_id, 0.0)
            if pt:
                points.append(pt)
            return points

        for i in range(count):
            t = i / (count - 1) if count > 1 else 0.0
            pt = self.evaluate_at(path_id, t)
            if pt is not None:
                points.append(pt)

        return points

    def get_path(self, path_id: str) -> Optional[SplinePath]:
        return self._paths.get(path_id)

    def get_all_paths(self) -> Dict[str, SplinePath]:
        return dict(self._paths)

    def clear_control_points(self, path_id: str) -> bool:
        path = self._paths.get(path_id)
        if path is None:
            return False
        path.control_points.clear()
        self._evaluation_cache.pop(path_id, None)
        return True

    def get_stats(self) -> Dict[str, Any]:
        path_details = {}
        for path_id, path in self._paths.items():
            length = self.get_total_length(path_id)
            path_details[path_id] = {
                "name": path.name,
                "type": path.spline_type.value,
                "control_points": len(path.control_points),
                "closed_loop": path.closed_loop,
                "approximate_length": round(length, 3),
            }
        return {
            "total_paths": len(self._paths),
            "total_evaluations": self._total_evaluations,
            "paths": path_details,
        }


def get_spline_system() -> SplineSystem:
    return SplineSystem.get_instance()