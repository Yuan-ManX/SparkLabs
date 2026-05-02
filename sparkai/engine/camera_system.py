"""
SparkLabs Engine - Camera System

Dynamic 2D camera with smooth following, dead zones, screen shake,
zoom transitions, and multi-target framing. Provides the viewport
transformation layer for AI-generated game scenes.

Architecture:
  CameraSystem
    |-- Camera (position, zoom, bounds, shake state)
    |-- CameraTarget (follow target with offset + dead zone)
    |-- CameraShake (trauma-based procedural shake)
    |-- CameraTransition (smooth pan/zoom interpolation)

Camera Modes:
  - FOLLOW: tracks a target entity with smoothing
  - FREE: manually positioned via set_position()
  - FRAME: frames multiple targets within viewport
  - SCRIPTED: follows a predefined path of keyframes

Usage:
    cam = CameraSystem(viewport_width=800, viewport_height=600)
    cam.follow(target_entity, smoothing=0.1, dead_zone=(50, 30))
    cam.set_bounds(0, 0, 3200, 2400)
    cam.shake(intensity=0.8, duration=0.5)
    world_pos = cam.screen_to_world(screen_x, screen_y)
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class CameraMode(Enum):
    FOLLOW = auto()
    FREE = auto()
    FRAME = auto()
    SCRIPTED = auto()


@dataclass
class CameraKeyframe:
    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0
    duration: float = 1.0
    easing: str = "linear"


@dataclass
class CameraTarget:
    entity_id: str = ""
    offset_x: float = 0.0
    offset_y: float = 0.0
    dead_zone_width: float = 0.0
    dead_zone_height: float = 0.0


@dataclass
class CameraShakeState:
    intensity: float = 0.0
    duration: float = 0.0
    elapsed: float = 0.0
    frequency: float = 30.0
    falloff: str = "linear"


@dataclass
class CameraStats:
    position_x: float = 0.0
    position_y: float = 0.0
    zoom: float = 1.0
    target_zoom: float = 1.0
    mode: str = "free"
    shake_active: bool = False
    bounds_enabled: bool = False
    target_count: int = 0


class Camera:
    def __init__(self, viewport_w: float = 800.0, viewport_h: float = 600.0):
        self.x: float = 0.0
        self.y: float = 0.0
        self.zoom: float = 1.0
        self.target_zoom: float = 1.0
        self.viewport_width: float = viewport_w
        self.viewport_height: float = viewport_h
        self.rotation: float = 0.0
        self.mode: CameraMode = CameraMode.FREE
        self.target: CameraTarget = CameraTarget()
        self.smoothing: float = 0.1
        self._bounds: Optional[Tuple[float, float, float, float]] = None

    @property
    def bounds(self) -> Optional[Tuple[float, float, float, float]]:
        return self._bounds

    @bounds.setter
    def bounds(self, value: Optional[Tuple[float, float, float, float]]) -> None:
        self._bounds = value

    def clamp_to_bounds(self) -> None:
        if self._bounds is None:
            return
        min_x, min_y, max_x, max_y = self._bounds
        half_w = self.viewport_width / (2.0 * self.zoom)
        half_h = self.viewport_height / (2.0 * self.zoom)
        self.x = max(min_x + half_w, min(self.x, max_x - half_w))
        self.y = max(min_y + half_h, min(self.y, max_y - half_h))


class CameraSystem:
    _instance: Optional["CameraSystem"] = None

    def __init__(self, viewport_width: float = 800.0, viewport_height: float = 600.0):
        self._camera: Camera = Camera(viewport_width, viewport_height)
        self._shake: CameraShakeState = CameraShakeState()
        self._targets: Dict[str, CameraTarget] = {}
        self._entity_positions: Dict[str, Tuple[float, float]] = {}
        self._keyframes: List[CameraKeyframe] = []
        self._keyframe_index: int = 0
        self._keyframe_elapsed: float = 0.0
        self._transitions: List[Dict[str, Any]] = []
        self._transition_elapsed: float = 0.0

    @classmethod
    def get_instance(cls) -> "CameraSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def camera(self) -> Camera:
        return self._camera

    @property
    def x(self) -> float:
        return self._camera.x

    @property
    def y(self) -> float:
        return self._camera.y

    @property
    def zoom(self) -> float:
        return self._camera.zoom

    def set_position(self, x: float, y: float) -> None:
        self._camera.mode = CameraMode.FREE
        self._camera.x = x
        self._camera.y = y
        self._camera.clamp_to_bounds()

    def move(self, dx: float, dy: float) -> None:
        self.set_position(self._camera.x + dx, self._camera.y + dy)

    def set_zoom(self, zoom: float) -> None:
        self._camera.target_zoom = max(0.1, min(zoom, 10.0))

    def zoom_in(self, factor: float = 0.1) -> None:
        self.set_zoom(self._camera.target_zoom + factor)

    def zoom_out(self, factor: float = 0.1) -> None:
        self.set_zoom(self._camera.target_zoom - factor)

    def set_bounds(self, left: float, top: float, right: float, bottom: float) -> None:
        self._camera.bounds = (left, top, right, bottom)
        self._camera.clamp_to_bounds()

    def clear_bounds(self) -> None:
        self._camera.bounds = None

    def follow(
        self,
        entity_id: str,
        smoothing: float = 0.1,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        dead_zone_width: float = 0.0,
        dead_zone_height: float = 0.0,
    ) -> None:
        self._camera.mode = CameraMode.FOLLOW
        self._camera.smoothing = max(0.001, min(smoothing, 1.0))
        self._camera.target = CameraTarget(
            entity_id=entity_id,
            offset_x=offset_x,
            offset_y=offset_y,
            dead_zone_width=dead_zone_width,
            dead_zone_height=dead_zone_height,
        )

    def frame_targets(
        self,
        entity_ids: List[str],
        padding: float = 50.0,
        max_zoom: float = 1.0,
    ) -> None:
        self._camera.mode = CameraMode.FRAME
        self._targets.clear()
        for eid in entity_ids:
            self._targets[eid] = CameraTarget(entity_id=eid)
        self._frame_padding = padding
        self._frame_max_zoom = max_zoom

    def set_scripted_path(self, keyframes: List[CameraKeyframe]) -> None:
        self._camera.mode = CameraMode.SCRIPTED
        self._keyframes = keyframes
        self._keyframe_index = 0
        self._keyframe_elapsed = 0.0

    def free_mode(self) -> None:
        self._camera.mode = CameraMode.FREE

    def shake(
        self,
        intensity: float = 0.5,
        duration: float = 0.3,
        frequency: float = 30.0,
        falloff: str = "linear",
    ) -> None:
        self._shake.intensity = max(0.0, min(intensity, 1.0))
        self._shake.duration = duration
        self._shake.elapsed = 0.0
        self._shake.frequency = frequency
        self._shake.falloff = falloff

    def stop_shake(self) -> None:
        self._shake.intensity = 0.0
        self._shake.elapsed = self._shake.duration

    def transition_to(
        self,
        target_x: float,
        target_y: float,
        target_zoom: float = 1.0,
        duration: float = 1.0,
        easing: str = "ease_in_out",
    ) -> None:
        self._transitions.append({
            "start_x": self._camera.x,
            "start_y": self._camera.y,
            "start_zoom": self._camera.zoom,
            "target_x": target_x,
            "target_y": target_y,
            "target_zoom": target_zoom,
            "duration": duration,
            "easing": easing,
        })
        self._transition_elapsed = 0.0

    def update_entity_position(self, entity_id: str, x: float, y: float) -> None:
        self._entity_positions[entity_id] = (x, y)

    def remove_entity(self, entity_id: str) -> None:
        self._entity_positions.pop(entity_id, None)
        self._targets.pop(entity_id, None)
        if self._camera.target.entity_id == entity_id:
            self._camera.mode = CameraMode.FREE

    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[float, float]:
        screen_x = (world_x - self._camera.x) * self._camera.zoom + self._camera.viewport_width / 2.0
        screen_y = (world_y - self._camera.y) * self._camera.zoom + self._camera.viewport_height / 2.0
        return (screen_x, screen_y)

    def screen_to_world(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        world_x = (screen_x - self._camera.viewport_width / 2.0) / self._camera.zoom + self._camera.x
        world_y = (screen_y - self._camera.viewport_height / 2.0) / self._camera.zoom + self._camera.y
        return (world_x, world_y)

    def get_visible_bounds(self) -> Tuple[float, float, float, float]:
        half_w = self._camera.viewport_width / (2.0 * self._camera.zoom)
        half_h = self._camera.viewport_height / (2.0 * self._camera.zoom)
        return (
            self._camera.x - half_w,
            self._camera.y - half_h,
            self._camera.x + half_w,
            self._camera.y + half_h,
        )

    def is_visible(
        self,
        world_x: float,
        world_y: float,
        margin: float = 0.0,
    ) -> bool:
        left, top, right, bottom = self.get_visible_bounds()
        return (
            world_x >= left - margin and world_x <= right + margin
            and world_y >= top - margin and world_y <= bottom + margin
        )

    def update(self, dt: float) -> CameraStats:
        self._update_zoom(dt)
        self._update_camera_mode(dt)
        self._update_shake(dt)

        if self._shake.intensity > 0.0:
            self._apply_shake_offset()

        self._camera.clamp_to_bounds()

        return self.get_stats()

    def _update_zoom(self, dt: float) -> None:
        zoom_diff = self._camera.target_zoom - self._camera.zoom
        if abs(zoom_diff) < 0.001:
            self._camera.zoom = self._camera.target_zoom
        else:
            self._camera.zoom += zoom_diff * min(dt * 8.0, 1.0)

    def _update_camera_mode(self, dt: float) -> None:
        if self._camera.mode == CameraMode.FOLLOW:
            self._update_follow_mode(dt)
        elif self._camera.mode == CameraMode.FRAME:
            self._update_frame_mode(dt)
        elif self._camera.mode == CameraMode.SCRIPTED:
            self._update_scripted_mode(dt)

    def _update_follow_mode(self, dt: float) -> None:
        target = self._camera.target
        pos = self._entity_positions.get(target.entity_id)
        if pos is None:
            return

        target_x = pos[0] + target.offset_x
        target_y = pos[1] + target.offset_y

        if target.dead_zone_width > 0 and target.dead_zone_height > 0:
            half_dw = target.dead_zone_width / 2.0
            half_dh = target.dead_zone_height / 2.0
            if abs(target_x - self._camera.x) < half_dw:
                target_x = self._camera.x
            if abs(target_y - self._camera.y) < half_dh:
                target_y = self._camera.y

        smoothing = max(dt / max(self._camera.smoothing, 0.001), 0.0)
        smoothing = min(smoothing, 1.0)
        self._camera.x += (target_x - self._camera.x) * smoothing
        self._camera.y += (target_y - self._camera.y) * smoothing

    def _update_frame_mode(self, dt: float) -> None:
        active_targets = []
        for eid in self._targets:
            pos = self._entity_positions.get(eid)
            if pos is not None:
                active_targets.append(pos)

        if not active_targets:
            return

        min_x = min(p[0] for p in active_targets)
        min_y = min(p[1] for p in active_targets)
        max_x = max(p[0] for p in active_targets)
        max_y = max(p[1] for p in active_targets)

        pad = self._frame_padding if hasattr(self, '_frame_padding') else 50.0
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0

        required_w = (max_x - min_x) + pad * 2
        required_h = (max_y - min_y) + pad * 2
        zoom_x = self._camera.viewport_width / max(required_w, 1.0)
        zoom_y = self._camera.viewport_height / max(required_h, 1.0)
        fit_zoom = min(zoom_x, zoom_y)

        max_z = self._frame_max_zoom if hasattr(self, '_frame_max_zoom') else 1.0
        self._camera.target_zoom = min(fit_zoom, max_z)

        smoothing = min(dt / 0.1, 1.0)
        self._camera.x += (center_x - self._camera.x) * smoothing
        self._camera.y += (center_y - self._camera.y) * smoothing

    def _update_scripted_mode(self, dt: float) -> None:
        if not self._keyframes or self._keyframe_index >= len(self._keyframes):
            self._camera.mode = CameraMode.FREE
            return

        kf = self._keyframes[self._keyframe_index]
        self._keyframe_elapsed += dt

        t = min(self._keyframe_elapsed / max(kf.duration, 0.001), 1.0)
        t = self._apply_easing(t, kf.easing)

        prev_kf = self._keyframes[self._keyframe_index - 1] if self._keyframe_index > 0 else None
        start_x = prev_kf.x if prev_kf else self._camera.x
        start_y = prev_kf.y if prev_kf else self._camera.y
        start_zoom = prev_kf.zoom if prev_kf else self._camera.zoom

        self._camera.x = start_x + (kf.x - start_x) * t
        self._camera.y = start_y + (kf.y - start_y) * t
        self._camera.zoom = start_zoom + (kf.zoom - start_zoom) * t

        if self._keyframe_elapsed >= kf.duration:
            self._keyframe_index += 1
            self._keyframe_elapsed = 0.0

    def _update_shake(self, dt: float) -> None:
        if self._shake.intensity <= 0.0:
            return
        self._shake.elapsed += dt
        if self._shake.elapsed >= self._shake.duration:
            self._shake.intensity = 0.0
            return
        if self._shake.falloff == "linear":
            progress = self._shake.elapsed / max(self._shake.duration, 0.001)
            self._shake.intensity *= (1.0 - progress)
        elif self._shake.falloff == "exponential":
            self._shake.intensity *= 0.9 ** (dt * 30.0)

    def _apply_shake_offset(self) -> None:
        noise_x = (random.random() * 2.0 - 1.0) * self._shake.intensity * 10.0
        noise_y = (random.random() * 2.0 - 1.0) * self._shake.intensity * 10.0
        self._camera.x += noise_x
        self._camera.y += noise_y

    @staticmethod
    def _apply_easing(t: float, easing: str) -> float:
        if easing == "linear":
            return t
        elif easing == "ease_in":
            return t * t
        elif easing == "ease_out":
            return t * (2.0 - t)
        elif easing == "ease_in_out":
            if t < 0.5:
                return 2.0 * t * t
            else:
                return -1.0 + (4.0 - 2.0 * t) * t
        elif easing == "bounce_out":
            if t < 1.0 / 2.75:
                return 7.5625 * t * t
            elif t < 2.0 / 2.75:
                t -= 1.5 / 2.75
                return 7.5625 * t * t + 0.75
            elif t < 2.5 / 2.75:
                t -= 2.25 / 2.75
                return 7.5625 * t * t + 0.9375
            else:
                t -= 2.625 / 2.75
                return 7.5625 * t * t + 0.984375
        else:
            return t

    def get_stats(self) -> CameraStats:
        return CameraStats(
            position_x=self._camera.x,
            position_y=self._camera.y,
            zoom=self._camera.zoom,
            target_zoom=self._camera.target_zoom,
            mode=self._camera.mode.name.lower(),
            shake_active=self._shake.intensity > 0.0,
            bounds_enabled=self._camera.bounds is not None,
            target_count=len(self._targets),
        )


def get_camera_system() -> CameraSystem:
    return CameraSystem.get_instance()
