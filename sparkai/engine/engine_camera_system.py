"""
SparkLabs Engine - Camera System

A camera and viewport management system for 2D games providing
follow mechanics, shake effects, boundary constraints, and
coordinate transformation between world and screen space.

Architecture:
  EngineCameraSystem (Singleton)
    |-- CameraViewport — viewport definition with position, zoom, rotation
    |-- CameraTarget  — follow target with lookahead and motion modes
    |-- CameraShake   — runtime shake effect with configurable waveforms
    |-- CameraBounds  — boundary constraints with damping
    |-- CameraEffect  — time-based camera post-effects
    |-- CameraSnapshot — capture of camera state at a point in time
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CameraFollowMode(str, Enum):
    """Algorithm used to move the camera toward a follow target."""
    NONE = "none"
    LERP = "lerp"
    SNAP = "snap"
    SMOOTH_DAMP = "smooth-damp"
    SPRING = "spring"


class CameraShakeType(str, Enum):
    """Waveform used to compute per-frame shake offsets."""
    RANDOM = "random"
    SINE_WAVE = "sine-wave"
    PERLIN = "perlin"


class CameraConstraint(str, Enum):
    """How the camera reacts when it reaches a boundary."""
    NONE = "none"
    BOUNDS = "bounds"
    CLAMP = "clamp"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CameraViewport:
    """Defines a camera's frustum, position, and display properties."""
    camera_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "default_camera"
    position_x: float = 0.0
    position_y: float = 0.0
    zoom: float = 1.0
    rotation: float = 0.0
    viewport_width: int = 1920
    viewport_height: int = 1080
    near_z: float = 0.0
    far_z: float = 1000.0
    background_color: Tuple[int, int, int, int] = (0, 0, 0, 255)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "name": self.name,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "zoom": self.zoom,
            "rotation": self.rotation,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "near_z": self.near_z,
            "far_z": self.far_z,
            "background_color": list(self.background_color),
        }


@dataclass
class CameraTarget:
    """Follow target descriptor with lookahead and motion parameters."""
    camera_id: str = ""
    target_x: float = 0.0
    target_y: float = 0.0
    lookahead_x: float = 0.0
    lookahead_y: float = 0.0
    follow_mode: CameraFollowMode = CameraFollowMode.LERP
    follow_speed: float = 5.0
    smooth_time: float = 0.3
    spring_stiffness: float = 100.0
    spring_damping: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "target_x": self.target_x,
            "target_y": self.target_y,
            "lookahead_x": self.lookahead_x,
            "lookahead_y": self.lookahead_y,
            "follow_mode": self.follow_mode.value,
            "follow_speed": self.follow_speed,
            "smooth_time": self.smooth_time,
            "spring_stiffness": self.spring_stiffness,
            "spring_damping": self.spring_damping,
        }


@dataclass
class CameraShake:
    """Runtime shake effect with configurable amplitude and waveform."""
    shake_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    camera_id: str = ""
    amplitude_x: float = 0.0
    amplitude_y: float = 0.0
    frequency: float = 1.0
    duration: float = 0.0
    elapsed: float = 0.0
    shake_type: CameraShakeType = CameraShakeType.RANDOM
    falloff: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shake_id": self.shake_id,
            "camera_id": self.camera_id,
            "amplitude_x": self.amplitude_x,
            "amplitude_y": self.amplitude_y,
            "frequency": self.frequency,
            "duration": self.duration,
            "elapsed": self.elapsed,
            "shake_type": self.shake_type.value,
            "falloff": self.falloff,
        }


@dataclass
class CameraBounds:
    """Rectangular boundary constraints for a camera."""
    camera_id: str = ""
    min_x: float = -10000.0
    min_y: float = -10000.0
    max_x: float = 10000.0
    max_y: float = 10000.0
    constraint: CameraConstraint = CameraConstraint.CLAMP
    damping: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "min_x": self.min_x,
            "min_y": self.min_y,
            "max_x": self.max_x,
            "max_y": self.max_y,
            "constraint": self.constraint.value,
            "damping": self.damping,
        }


@dataclass
class CameraEffect:
    """Time-based post-processing effect applied to a camera."""
    effect_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    camera_id: str = ""
    name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    elapsed: float = 0.0
    duration: float = 0.0
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "camera_id": self.camera_id,
            "name": self.name,
            "parameters": dict(self.parameters),
            "elapsed": self.elapsed,
            "duration": self.duration,
            "active": self.active,
        }


@dataclass
class CameraSnapshot:
    """Immutable capture of a camera's state at a point in time."""
    camera_id: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    zoom: float = 1.0
    rotation: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "zoom": self.zoom,
            "rotation": self.rotation,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Internal Spring State
# ---------------------------------------------------------------------------

@dataclass
class _SpringState:
    """Internal velocity tracking for spring-based camera follow."""
    velocity_x: float = 0.0
    velocity_y: float = 0.0


# ---------------------------------------------------------------------------
# EngineCameraSystem — Thread-Safe Singleton
# ---------------------------------------------------------------------------

class EngineCameraSystem:
    """
    Central camera and viewport orchestrator.

    Manages multiple cameras with follow behaviours, shake effects,
    boundary constraints, coordinate transforms, and post-effects.
    Thread-safe via reentrant lock.

    Usage:
        cam_sys = get_camera_system()
        cv = cam_sys.create_camera("main", 1920, 1080)
        target = CameraTarget(camera_id=cv.camera_id, target_x=100, target_y=50)
        cam_sys.set_follow_target(cv.camera_id, target)
        cam_sys.update_follow(cv.camera_id, 0.016)
    """

    _instance: Optional["EngineCameraSystem"] = None
    _lock = threading.RLock()

    DEFAULT_ZOOM_MIN: float = 0.1
    DEFAULT_ZOOM_MAX: float = 10.0

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    def __new__(cls) -> "EngineCameraSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineCameraSystem":
        """Return the singleton EngineCameraSystem instance."""
        return cls()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._viewports: Dict[str, CameraViewport] = {}
        self._targets: Dict[str, CameraTarget] = {}
        self._shakes: Dict[str, CameraShake] = {}
        self._bounds: Dict[str, CameraBounds] = {}
        self._effects: Dict[str, Dict[str, CameraEffect]] = {}
        self._snapshots: Dict[str, List[CameraSnapshot]] = {}
        self._spring_states: Dict[str, _SpringState] = {}

        self._total_cameras_created: int = 0
        self._total_shakes_started: int = 0
        self._total_effects_applied: int = 0

    # ------------------------------------------------------------------
    # Camera Lifecycle
    # ------------------------------------------------------------------

    def create_camera(
        self,
        name: str,
        viewport_w: int = 1920,
        viewport_h: int = 1080,
    ) -> CameraViewport:
        """Create a new camera viewport and return its descriptor."""
        with self._lock:
            vp = CameraViewport(
                name=name,
                viewport_width=viewport_w,
                viewport_height=viewport_h,
            )
            self._viewports[vp.camera_id] = vp
            self._effects[vp.camera_id] = {}
            self._snapshots[vp.camera_id] = []
            self._total_cameras_created += 1
            return vp

    def get_camera_viewport(self, camera_id: str) -> Optional[CameraViewport]:
        """Return the viewport for the given camera, or None."""
        return self._viewports.get(camera_id)

    # ------------------------------------------------------------------
    # Position / Zoom / Rotation
    # ------------------------------------------------------------------

    def set_camera_position(self, camera_id: str, x: float, y: float) -> bool:
        """Immediately set the camera world position."""
        vp = self._viewports.get(camera_id)
        if vp is None:
            return False
        vp.position_x = x
        vp.position_y = y
        return True

    def set_camera_zoom(self, camera_id: str, zoom: float) -> bool:
        """Set camera zoom, clamped to [0.1, 10.0]."""
        vp = self._viewports.get(camera_id)
        if vp is None:
            return False
        vp.zoom = max(self.DEFAULT_ZOOM_MIN, min(self.DEFAULT_ZOOM_MAX, zoom))
        return True

    def set_camera_rotation(self, camera_id: str, degrees: float) -> bool:
        """Set the camera rotation in degrees."""
        vp = self._viewports.get(camera_id)
        if vp is None:
            return False
        vp.rotation = degrees
        return True

    # ------------------------------------------------------------------
    # Follow Mechanics
    # ------------------------------------------------------------------

    def set_follow_target(self, camera_id: str, target: CameraTarget) -> bool:
        """Attach a follow target to the given camera."""
        vp = self._viewports.get(camera_id)
        if vp is None:
            return False
        target.camera_id = camera_id
        self._targets[camera_id] = target
        return True

    def update_follow(self, camera_id: str, delta_time: float) -> Optional[CameraViewport]:
        """Advance the camera toward its follow target by one frame."""
        vp = self._viewports.get(camera_id)
        if vp is None:
            return None
        target = self._targets.get(camera_id)
        if target is None or target.follow_mode == CameraFollowMode.NONE:
            return vp

        desired_x = target.target_x + target.lookahead_x
        desired_y = target.target_y + target.lookahead_y

        dt = max(0.0, delta_time)

        if target.follow_mode == CameraFollowMode.SNAP:
            vp.position_x = desired_x
            vp.position_y = desired_y

        elif target.follow_mode == CameraFollowMode.LERP:
            factor = min(1.0, target.follow_speed * dt)
            vp.position_x += (desired_x - vp.position_x) * factor
            vp.position_y += (desired_y - vp.position_y) * factor

        elif target.follow_mode == CameraFollowMode.SMOOTH_DAMP:
            spring = self._spring_states.get(camera_id)
            if spring is None:
                spring = _SpringState()
                self._spring_states[camera_id] = spring
            smooth_time = max(0.0001, target.smooth_time)
            omega = 2.0 / smooth_time
            k1 = 1.0 / (1.0 + omega * dt)
            k2 = omega * dt / (1.0 + omega * dt)

            dx = desired_x - vp.position_x
            dy = desired_y - vp.position_y

            spring.velocity_x = k1 * spring.velocity_x + k2 * dx / max(dt, 0.0001)
            spring.velocity_y = k1 * spring.velocity_y + k2 * dy / max(dt, 0.0001)

            vp.position_x += spring.velocity_x * dt
            vp.position_y += spring.velocity_y * dt

        elif target.follow_mode == CameraFollowMode.SPRING:
            spring = self._spring_states.get(camera_id)
            if spring is None:
                spring = _SpringState()
                self._spring_states[camera_id] = spring

            stiffness = max(0.0, target.spring_stiffness)
            damping = max(0.0, target.spring_damping)

            dx = desired_x - vp.position_x
            dy = desired_y - vp.position_y

            spring.velocity_x += (stiffness * dx - damping * spring.velocity_x) * dt
            spring.velocity_y += (stiffness * dy - damping * spring.velocity_y) * dt

            vp.position_x += spring.velocity_x * dt
            vp.position_y += spring.velocity_y * dt

        return vp

    # ------------------------------------------------------------------
    # Shake
    # ------------------------------------------------------------------

    def start_shake(
        self,
        camera_id: str,
        amplitude_x: float,
        amplitude_y: float,
        frequency: float,
        duration: float,
        shake_type: CameraShakeType = CameraShakeType.RANDOM,
    ) -> Optional[CameraShake]:
        """Begin a shake effect on the given camera."""
        vp = self._viewports.get(camera_id)
        if vp is None:
            return None
        shake = CameraShake(
            camera_id=camera_id,
            amplitude_x=amplitude_x,
            amplitude_y=amplitude_y,
            frequency=frequency,
            duration=duration,
            shake_type=shake_type,
        )
        self._shakes[camera_id] = shake
        self._total_shakes_started += 1
        return shake

    def update_shake(self, camera_id: str, delta_time: float) -> Tuple[float, float]:
        """Compute the (dx, dy) shake offset for this frame."""
        shake = self._shakes.get(camera_id)
        if shake is None:
            return (0.0, 0.0)

        shake.elapsed += max(0.0, delta_time)
        progress = min(1.0, shake.elapsed / max(shake.duration, 0.001))
        intensity = 1.0 - progress if shake.falloff else 1.0

        base_amp_x = shake.amplitude_x * intensity
        base_amp_y = shake.amplitude_y * intensity

        if shake.shake_type == CameraShakeType.RANDOM:
            # Use elapsed time as a pseudo-random seed
            seed = shake.elapsed * shake.frequency * 127.1
            dx = base_amp_x * (math.sin(seed * 12.9898 + 78.233) % 1.0 * 2.0 - 1.0)
            dy = base_amp_y * (math.sin(seed * 78.233 + 12.9898) % 1.0 * 2.0 - 1.0)

        elif shake.shake_type == CameraShakeType.SINE_WAVE:
            phase = shake.elapsed * shake.frequency * 2.0 * math.pi
            dx = base_amp_x * math.sin(phase)
            dy = base_amp_y * math.cos(phase * 1.3)

        else:  # PERLIN — approximate with layered sine waves
            t = shake.elapsed * shake.frequency
            dx = base_amp_x * (
                math.sin(t * 2.0 * math.pi) * 0.6
                + math.sin(t * 4.0 * math.pi + 1.0) * 0.3
                + math.sin(t * 8.0 * math.pi + 2.0) * 0.1
            )
            dy = base_amp_y * (
                math.cos(t * 2.0 * math.pi + 0.5) * 0.6
                + math.cos(t * 4.0 * math.pi + 1.5) * 0.3
                + math.cos(t * 8.0 * math.pi + 2.5) * 0.1
            )

        if progress >= 1.0:
            self._shakes.pop(camera_id, None)

        return (dx, dy)

    def stop_shake(self, camera_id: str) -> bool:
        """Immediately stop any active shake on the camera."""
        if camera_id in self._shakes:
            del self._shakes[camera_id]
            return True
        return False

    # ------------------------------------------------------------------
    # Bounds & Constraints
    # ------------------------------------------------------------------

    def set_bounds(self, camera_id: str, bounds: CameraBounds) -> bool:
        """Set boundary constraints for a camera."""
        vp = self._viewports.get(camera_id)
        if vp is None:
            return False
        bounds.camera_id = camera_id
        self._bounds[camera_id] = bounds
        return True

    def constrain_to_bounds(self, camera_id: str) -> bool:
        """Clamp the camera position to its boundary rect."""
        vp = self._viewports.get(camera_id)
        if vp is None:
            return False
        bounds = self._bounds.get(camera_id)
        if bounds is None or bounds.constraint == CameraConstraint.NONE:
            return True

        if bounds.constraint == CameraConstraint.CLAMP:
            vp.position_x = max(bounds.min_x, min(bounds.max_x, vp.position_x))
            vp.position_y = max(bounds.min_y, min(bounds.max_y, vp.position_y))
        elif bounds.constraint == CameraConstraint.BOUNDS:
            damping = max(0.0, min(1.0, bounds.damping))
            if vp.position_x < bounds.min_x:
                vp.position_x += (bounds.min_x - vp.position_x) * damping
            elif vp.position_x > bounds.max_x:
                vp.position_x += (bounds.max_x - vp.position_x) * damping
            if vp.position_y < bounds.min_y:
                vp.position_y += (bounds.min_y - vp.position_y) * damping
            elif vp.position_y > bounds.max_y:
                vp.position_y += (bounds.max_y - vp.position_y) * damping

        return True

    # ------------------------------------------------------------------
    # Coordinate Transforms
    # ------------------------------------------------------------------

    def world_to_screen(
        self, camera_id: str, world_x: float, world_y: float,
    ) -> Tuple[float, float]:
        """Convert world coordinates to screen coordinates."""
        vp = self._viewports.get(camera_id)
        if vp is None:
            return (world_x, world_y)

        # Translate relative to camera position
        rel_x = (world_x - vp.position_x) * vp.zoom
        rel_y = (world_y - vp.position_y) * vp.zoom

        # Apply rotation
        if vp.rotation != 0.0:
            rad = math.radians(-vp.rotation)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            rx = rel_x * cos_a - rel_y * sin_a
            ry = rel_x * sin_a + rel_y * cos_a
            rel_x, rel_y = rx, ry

        # Center in viewport
        screen_x = rel_x + vp.viewport_width / 2.0
        screen_y = rel_y + vp.viewport_height / 2.0

        return (screen_x, screen_y)

    def screen_to_world(
        self, camera_id: str, screen_x: float, screen_y: float,
    ) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates."""
        vp = self._viewports.get(camera_id)
        if vp is None:
            return (screen_x, screen_y)

        # Undo viewport centering
        rel_x = screen_x - vp.viewport_width / 2.0
        rel_y = screen_y - vp.viewport_height / 2.0

        # Undo rotation (rotate in opposite direction)
        if vp.rotation != 0.0:
            rad = math.radians(vp.rotation)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            rx = rel_x * cos_a - rel_y * sin_a
            ry = rel_x * sin_a + rel_y * cos_a
            rel_x, rel_y = rx, ry

        # Undo zoom and camera offset
        safe_zoom = max(vp.zoom, 0.0001)
        world_x = rel_x / safe_zoom + vp.position_x
        world_y = rel_y / safe_zoom + vp.position_y

        return (world_x, world_y)

    # ------------------------------------------------------------------
    # Effects
    # ------------------------------------------------------------------

    def add_effect(
        self,
        camera_id: str,
        name: str,
        duration: float,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[CameraEffect]:
        """Add a time-based post-effect to a camera."""
        if camera_id not in self._viewports:
            return None
        effect = CameraEffect(
            camera_id=camera_id,
            name=name,
            duration=duration,
            parameters=params or {},
        )
        self._effects[camera_id][effect.effect_id] = effect
        self._total_effects_applied += 1
        return effect

    def update_effects(self, camera_id: str, delta_time: float) -> List[CameraEffect]:
        """Advance all effects on a camera; return still-active effects."""
        if camera_id not in self._effects:
            return []
        dt = max(0.0, delta_time)
        active: List[CameraEffect] = []
        expired: List[str] = []

        for eff_id, effect in self._effects[camera_id].items():
            if not effect.active:
                expired.append(eff_id)
                continue
            effect.elapsed += dt
            if effect.duration > 0.0 and effect.elapsed >= effect.duration:
                effect.active = False
                expired.append(eff_id)
            else:
                active.append(effect)

        for eid in expired:
            self._effects[camera_id].pop(eid, None)

        return active

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def take_snapshot(self, camera_id: str) -> Optional[CameraSnapshot]:
        """Capture the current camera state."""
        vp = self._viewports.get(camera_id)
        if vp is None:
            return None
        snap = CameraSnapshot(
            camera_id=camera_id,
            position_x=vp.position_x,
            position_y=vp.position_y,
            zoom=vp.zoom,
            rotation=vp.rotation,
        )
        self._snapshots[camera_id].append(snap)
        return snap

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_camera_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about all cameras."""
        active_shakes = len(self._shakes)
        active_effects = sum(
            1 for effs in self._effects.values()
            for e in effs.values() if e.active
        )
        return {
            "camera_count": len(self._viewports),
            "total_cameras_created": self._total_cameras_created,
            "active_shakes": active_shakes,
            "total_shakes_started": self._total_shakes_started,
            "active_effects": active_effects,
            "total_effects_applied": self._total_effects_applied,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Remove all cameras and associated state."""
        with self._lock:
            self._viewports.clear()
            self._targets.clear()
            self._shakes.clear()
            self._bounds.clear()
            self._effects.clear()
            self._snapshots.clear()
            self._spring_states.clear()
            self._total_cameras_created = 0
            self._total_shakes_started = 0
            self._total_effects_applied = 0


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------

def get_camera_system() -> EngineCameraSystem:
    """Return the singleton EngineCameraSystem instance."""
    return EngineCameraSystem.get_instance()