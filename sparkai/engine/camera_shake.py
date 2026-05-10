"""
SparkLabs Engine - Camera Shake System

Dynamic 2D camera effects system providing screen shake, smooth
follow, zoom transitions, and cinematic camera behaviors for
game feel and player feedback.

Architecture:
  CameraShakeSystem
    |-- ShakePreset (trauma-based procedural shake profiles)
    |-- CameraFollow (smooth tracking with dead zones)
    |-- ZoomController (animated field-of-view transitions)
    |-- CameraEffects (composite effect layering)
    |-- ShakeMixer (multi-source shake blending)

Shake Presets:
  - EXPLOSION: high trauma, rapid decay, large amplitude
  - IMPACT: medium trauma, moderate decay
  - RUMBLE: low trauma, slow decay, continuous
  - WOBBLE: sinusoidal periodic oscillation
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class ShakePreset(Enum):
    EXPLOSION = "explosion"
    IMPACT = "impact"
    RUMBLE = "rumble"
    WOBBLE = "wobble"
    CUSTOM = "custom"


class CameraMode(Enum):
    STATIC = "static"
    FOLLOW = "follow"
    SHAKE = "shake"
    CINEMATIC = "cinematic"


@dataclass
class ShakeConfig:
    amplitude_x: float = 5.0
    amplitude_y: float = 5.0
    frequency: float = 30.0
    duration: float = 0.5
    decay: float = 0.9
    roughness: float = 0.5


@dataclass
class CameraState:
    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0
    rotation: float = 0.0
    offset_x: float = 0.0
    offset_y: float = 0.0


SHAKE_PRESETS: Dict[ShakePreset, ShakeConfig] = {
    ShakePreset.EXPLOSION: ShakeConfig(
        amplitude_x=15.0, amplitude_y=15.0, frequency=40.0, duration=0.6, decay=0.7, roughness=0.8,
    ),
    ShakePreset.IMPACT: ShakeConfig(
        amplitude_x=8.0, amplitude_y=6.0, frequency=25.0, duration=0.3, decay=0.85, roughness=0.5,
    ),
    ShakePreset.RUMBLE: ShakeConfig(
        amplitude_x=3.0, amplitude_y=2.0, frequency=15.0, duration=1.5, decay=0.95, roughness=0.3,
    ),
    ShakePreset.WOBBLE: ShakeConfig(
        amplitude_x=4.0, amplitude_y=4.0, frequency=10.0, duration=2.0, decay=0.98, roughness=0.2,
    ),
}


@dataclass
class ActiveShake:
    config: ShakeConfig = field(default_factory=ShakeConfig)
    elapsed: float = 0.0
    trauma: float = 1.0
    seed_x: float = field(default_factory=lambda: random.uniform(0, 1000))
    seed_y: float = field(default_factory=lambda: random.uniform(0, 1000))

    def is_expired(self) -> bool:
        return self.elapsed >= self.config.duration

    def get_offset(self, dt: float) -> Tuple[float, float]:
        self.elapsed += dt
        progress = min(self.elapsed / self.config.duration, 1.0)
        remaining = 1.0 - progress
        decay_factor = self.config.decay ** (self.elapsed * 10)

        noise_x = self._perlin_noise(self.seed_x + self.elapsed * self.config.frequency)
        noise_y = self._perlin_noise(self.seed_y + self.elapsed * self.config.frequency)

        roughness = self.config.roughness
        noise_x = noise_x * (1.0 - roughness) + (random.uniform(-1, 1)) * roughness
        noise_y = noise_y * (1.0 - roughness) + (random.uniform(-1, 1)) * roughness

        ax = self.config.amplitude_x * noise_x * decay_factor * remaining
        ay = self.config.amplitude_y * noise_y * decay_factor * remaining

        return (ax, ay)

    @staticmethod
    def _perlin_noise(x: float) -> float:
        x0 = math.floor(x)
        x1 = x0 + 1
        sx = x - x0
        u = sx * sx * (3.0 - 2.0 * sx)

        a = (math.sin(x0 * 12.9898 + 78.233) * 43758.5453) % 1
        b = (math.sin(x1 * 12.9898 + 78.233) * 43758.5453) % 1
        a = a * 2 - 1
        b = b * 2 - 1

        return a + u * (b - a)


class CameraShakeSystem:
    """
    2D camera effects system for game feel and player feedback.

    Manages screen shake, smooth camera follow, zoom transitions,
    and composite effect layering. Shake is trauma-based with
    configurable presets for common game scenarios.

    Usage:
        cam = CameraShakeSystem()
        cam.shake(ShakePreset.EXPLOSION)
        offset = cam.update(0.016)
        renderer.set_camera_offset(offset)
    """

    _instance: Optional["CameraShakeSystem"] = None

    def __init__(self):
        self._position: Tuple[float, float] = (0.0, 0.0)
        self._target: Optional[Tuple[float, float]] = None
        self._zoom: float = 1.0
        self._target_zoom: float = 1.0
        self._rotation: float = 0.0
        self._mode: CameraMode = CameraMode.STATIC
        self._active_shakes: List[ActiveShake] = []
        self._follow_speed: float = 5.0
        self._dead_zone: float = 16.0
        self._zoom_speed: float = 3.0
        self._offset_x: float = 0.0
        self._offset_y: float = 0.0
        self._shake_count: int = 0

    @classmethod
    def get_instance(cls) -> "CameraShakeSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_position(self, x: float, y: float) -> None:
        self._position = (x, y)

    def set_target(self, x: Optional[float] = None, y: Optional[float] = None) -> None:
        if x is not None and y is not None:
            self._target = (x, y)
            self._mode = CameraMode.FOLLOW
        else:
            self._target = None
            self._mode = CameraMode.STATIC

    def set_zoom(self, zoom: float, animated: bool = True) -> None:
        if animated:
            self._target_zoom = max(0.1, min(10.0, zoom))
        else:
            self._zoom = max(0.1, min(10.0, zoom))
            self._target_zoom = self._zoom

    def shake(
        self,
        preset: ShakePreset = ShakePreset.IMPACT,
        config: Optional[ShakeConfig] = None,
    ) -> None:
        if config is None:
            config = SHAKE_PRESETS.get(preset, SHAKE_PRESETS[ShakePreset.IMPACT])

        self._active_shakes.append(ActiveShake(config=ShakeConfig(
            amplitude_x=config.amplitude_x,
            amplitude_y=config.amplitude_y,
            frequency=config.frequency,
            duration=config.duration,
            decay=config.decay,
            roughness=config.roughness,
        )))
        self._shake_count += 1

    def stop_all_shakes(self) -> None:
        self._active_shakes.clear()
        self._offset_x = 0.0
        self._offset_y = 0.0

    def update(self, dt: float) -> CameraState:
        self._update_follow(dt)
        self._update_zoom(dt)
        self._update_shake(dt)

        return CameraState(
            x=self._position[0] + self._offset_x,
            y=self._position[1] + self._offset_y,
            zoom=self._zoom,
            rotation=self._rotation,
            offset_x=self._offset_x,
            offset_y=self._offset_y,
        )

    def _update_follow(self, dt: float) -> None:
        if self._mode != CameraMode.FOLLOW or self._target is None:
            return

        tx, ty = self._target
        cx, cy = self._position

        dx = tx - cx
        dy = ty - cy
        dist = math.sqrt(dx * dx + dy * dy)

        if dist <= self._dead_zone:
            return

        lerp = min(self._follow_speed * dt, 1.0)
        nx = cx + dx * lerp
        ny = cy + dy * lerp

        self._position = (nx, ny)

    def _update_zoom(self, dt: float) -> None:
        if abs(self._zoom - self._target_zoom) < 0.001:
            self._zoom = self._target_zoom
            return

        lerp = min(self._zoom_speed * dt, 1.0)
        self._zoom += (self._target_zoom - self._zoom) * lerp

    def _update_shake(self, dt: float) -> None:
        total_offset_x = 0.0
        total_offset_y = 0.0

        remaining: List[ActiveShake] = []
        for shake in self._active_shakes:
            if shake.is_expired():
                continue
            ox, oy = shake.get_offset(dt)
            total_offset_x += ox
            total_offset_y += oy
            remaining.append(shake)

        self._active_shakes = remaining
        self._offset_x = total_offset_x
        self._offset_y = total_offset_y

    def set_follow_speed(self, speed: float) -> None:
        self._follow_speed = max(0.1, speed)

    def set_dead_zone(self, zone: float) -> None:
        self._dead_zone = max(0.0, zone)

    def set_zoom_speed(self, speed: float) -> None:
        self._zoom_speed = max(0.1, speed)

    def get_state(self) -> CameraState:
        return CameraState(
            x=self._position[0] + self._offset_x,
            y=self._position[1] + self._offset_y,
            zoom=self._zoom,
            rotation=self._rotation,
            offset_x=self._offset_x,
            offset_y=self._offset_y,
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "mode": self._mode.value,
            "position": list(self._position),
            "target": list(self._target) if self._target else None,
            "zoom": round(self._zoom, 2),
            "active_shakes": len(self._active_shakes),
            "total_shakes_triggered": self._shake_count,
            "offset": [round(self._offset_x, 2), round(self._offset_y, 2)],
        }


def get_camera_shake_system() -> CameraShakeSystem:
    return CameraShakeSystem.get_instance()