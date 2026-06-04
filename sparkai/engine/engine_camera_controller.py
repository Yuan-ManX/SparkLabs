"""
SparkLabs Engine - Camera Controller

Comprehensive camera orchestration system for dynamic viewport
management. Provides smooth tracking, multi-target framing,
cinematic transitions, boundary clamping, shake effects,
and intelligent auto-framing for gameplay and cutscenes.

Architecture:
  EngineCameraController (Singleton)
    |-- Camera Target Tracker (single/multi-target following)
    |-- Cinematic Sequencer (smooth dolly/pan/zoom transitions)
    |-- Boundary Manager (viewport clamping and dead zones)
    |-- Shake Engine (procedural camera shake with profiles)
    |-- Auto-Frame Calculator (intelligent scene framing)
    |-- Zoom Controller (orthographic/perspective zoom levels)
    |-- Look-Ahead Predictor (velocity-based target anticipation)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CameraMode(Enum):
    FREE = "free"
    FOLLOW = "follow"
    FRAME_TARGET = "frame_target"
    CINEMATIC = "cinematic"
    TOP_DOWN = "top_down"
    SIDE_SCROLLER = "side_scroller"
    ISOMETRIC = "isometric"
    FIRST_PERSON = "first_person"


class CameraProjection(Enum):
    ORTHOGRAPHIC = "orthographic"
    PERSPECTIVE = "perspective"


class FollowStyle(Enum):
    LERP = "lerp"
    SPRING = "spring"
    SNAP = "snap"
    PREDICTIVE = "predictive"
    SMOOTH_DAMP = "smooth_damp"


class ShakeProfile(Enum):
    EXPLOSION = "explosion"
    EARTHQUAKE = "earthquake"
    IMPACT = "impact"
    ENGINE_RUMBLE = "engine_rumble"
    HANDHELD = "handheld"
    DRAMATIC = "dramatic"
    SUBTLE = "subtle"


class TransitionType(Enum):
    CUT = "cut"
    LERP = "lerp"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    ELASTIC = "elastic"
    BOUNCE = "bounce"


class DeadZoneShape(Enum):
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    CROSS = "cross"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class CameraTarget:
    """A target the camera can follow or frame."""
    target_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    weight: float = 1.0
    is_active: bool = True
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "z": round(self.z, 3),
            "vx": round(self.vx, 3),
            "vy": round(self.vy, 3),
            "weight": self.weight,
            "is_active": self.is_active,
            "label": self.label,
        }


@dataclass
class CameraConfig:
    """Configuration for a camera instance."""
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "Main Camera"
    mode: CameraMode = CameraMode.FOLLOW
    projection: CameraProjection = CameraProjection.ORTHOGRAPHIC
    follow_style: FollowStyle = FollowStyle.SMOOTH_DAMP
    follow_speed: float = 5.0
    follow_offset_x: float = 0.0
    follow_offset_y: float = 0.0
    zoom: float = 1.0
    min_zoom: float = 0.1
    max_zoom: float = 10.0
    zoom_speed: float = 8.0
    rotation: float = 0.0
    viewport_width: float = 1920.0
    viewport_height: float = 1080.0
    dead_zone_width: float = 100.0
    dead_zone_height: float = 80.0
    dead_zone_shape: DeadZoneShape = DeadZoneShape.RECTANGLE
    boundary_left: float = float("-inf")
    boundary_right: float = float("inf")
    boundary_top: float = float("-inf")
    boundary_bottom: float = float("inf")
    look_ahead_factor: float = 0.3
    look_ahead_max: float = 200.0
    spring_stiffness: float = 100.0
    spring_damping: float = 15.0
    smooth_time: float = 0.2
    prediction_time: float = 0.15

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "name": self.name,
            "mode": self.mode.value,
            "projection": self.projection.value,
            "follow_style": self.follow_style.value,
            "follow_speed": self.follow_speed,
            "zoom": self.zoom,
            "rotation": self.rotation,
            "viewport": f"{self.viewport_width}x{self.viewport_height}",
        }


@dataclass
class CameraState:
    """Runtime camera state."""
    x: float = 0.0
    y: float = 0.0
    z: float = 10.0
    zoom: float = 1.0
    rotation: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    is_shaking: bool = False
    shake_intensity: float = 0.0
    shake_offset_x: float = 0.0
    shake_offset_y: float = 0.0
    transition_progress: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "zoom": round(self.zoom, 3),
            "rotation": round(self.rotation, 3),
            "is_shaking": self.is_shaking,
        }


@dataclass
class ShakeConfig:
    """Configuration for a camera shake effect."""
    profile: ShakeProfile = ShakeProfile.IMPACT
    intensity: float = 1.0
    duration: float = 0.5
    frequency: float = 20.0
    decay: float = 0.9
    roughness: float = 0.5
    directional_bias_x: float = 0.0
    directional_bias_y: float = 0.0
    max_offset: float = 50.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile.value,
            "intensity": self.intensity,
            "duration": self.duration,
            "frequency": self.frequency,
        }


@dataclass
class CinematicKeyframe:
    """A keyframe for cinematic camera sequences."""
    keyframe_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    time: float = 0.0
    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0
    rotation: float = 0.0
    transition: TransitionType = TransitionType.EASE_IN_OUT
    hold_duration: float = 0.0
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyframe_id": self.keyframe_id,
            "time": self.time,
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "zoom": self.zoom,
            "transition": self.transition.value,
            "label": self.label,
        }


@dataclass
class CinematicSequence:
    """A sequence of cinematic camera keyframes."""
    sequence_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "Cinematic Sequence"
    keyframes: List[CinematicKeyframe] = field(default_factory=list)
    is_looping: bool = False
    total_duration: float = 0.0
    is_playing: bool = False
    current_time: float = 0.0
    current_keyframe_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "name": self.name,
            "keyframe_count": len(self.keyframes),
            "is_looping": self.is_looping,
            "total_duration": round(self.total_duration, 3),
            "is_playing": self.is_playing,
            "keyframes": [kf.to_dict() for kf in self.keyframes],
        }


# ---------------------------------------------------------------------------
# Shake Profiles Presets
# ---------------------------------------------------------------------------

SHAKE_PRESETS: Dict[ShakeProfile, Dict[str, float]] = {
    ShakeProfile.EXPLOSION: {
        "intensity": 1.5, "duration": 0.8, "frequency": 35.0,
        "decay": 0.85, "roughness": 0.8, "max_offset": 80.0,
    },
    ShakeProfile.EARTHQUAKE: {
        "intensity": 0.8, "duration": 3.0, "frequency": 10.0,
        "decay": 0.95, "roughness": 0.9, "max_offset": 40.0,
    },
    ShakeProfile.IMPACT: {
        "intensity": 1.0, "duration": 0.3, "frequency": 25.0,
        "decay": 0.7, "roughness": 0.5, "max_offset": 30.0,
    },
    ShakeProfile.ENGINE_RUMBLE: {
        "intensity": 0.3, "duration": 999.0, "frequency": 40.0,
        "decay": 1.0, "roughness": 0.3, "max_offset": 5.0,
    },
    ShakeProfile.HANDHELD: {
        "intensity": 0.15, "duration": 999.0, "frequency": 12.0,
        "decay": 1.0, "roughness": 0.6, "max_offset": 8.0,
    },
    ShakeProfile.DRAMATIC: {
        "intensity": 0.6, "duration": 1.5, "frequency": 15.0,
        "decay": 0.88, "roughness": 0.4, "max_offset": 25.0,
    },
    ShakeProfile.SUBTLE: {
        "intensity": 0.1, "duration": 0.5, "frequency": 30.0,
        "decay": 0.9, "roughness": 0.2, "max_offset": 3.0,
    },
}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class EngineCameraController:
    """Singleton camera orchestration system."""

    _instance: Optional["EngineCameraController"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EngineCameraController":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._cameras: Dict[str, CameraConfig] = {}
        self._camera_states: Dict[str, CameraState] = {}
        self._targets: Dict[str, CameraTarget] = {}
        self._camera_targets: Dict[str, Set[str]] = {}
        self._shake_configs: Dict[str, ShakeConfig] = {}
        self._sequences: Dict[str, CinematicSequence] = {}
        self._perlin_offsets: Dict[str, Tuple[float, float]] = {}
        self._active_camera_id: str = ""

    @classmethod
    def get_instance(cls) -> "EngineCameraController":
        return cls()

    # -- Camera Management ---------------------------------------------------

    def create_camera(self, name: str = "Main Camera", **kwargs) -> CameraConfig:
        with self._lock:
            config = CameraConfig(name=name, **kwargs)
            self._cameras[config.config_id] = config
            state = CameraState(x=0.0, y=0.0, zoom=config.zoom)
            self._camera_states[config.config_id] = state
            self._camera_targets[config.config_id] = set()
            if not self._active_camera_id:
                self._active_camera_id = config.config_id
            return config

    def get_camera(self, camera_id: str) -> Optional[CameraConfig]:
        return self._cameras.get(camera_id)

    def get_state(self, camera_id: str) -> Optional[CameraState]:
        return self._camera_states.get(camera_id)

    def set_active(self, camera_id: str) -> bool:
        with self._lock:
            if camera_id in self._cameras:
                self._active_camera_id = camera_id
                return True
            return False

    def get_active_camera(self) -> Optional[CameraConfig]:
        return self._cameras.get(self._active_camera_id)

    def list_cameras(self) -> List[CameraConfig]:
        return list(self._cameras.values())

    def remove_camera(self, camera_id: str) -> bool:
        with self._lock:
            if camera_id in self._cameras:
                del self._cameras[camera_id]
                self._camera_states.pop(camera_id, None)
                self._camera_targets.pop(camera_id, None)
                self._shake_configs.pop(camera_id, None)
                if self._active_camera_id == camera_id:
                    self._active_camera_id = next(iter(self._cameras), "")
                return True
            return False

    # -- Target Management ---------------------------------------------------

    def add_target(self, x: float = 0.0, y: float = 0.0,
                   weight: float = 1.0, label: str = "") -> CameraTarget:
        with self._lock:
            target = CameraTarget(x=x, y=y, weight=weight, label=label)
            self._targets[target.target_id] = target
            return target

    def update_target(self, target_id: str, x: float = None, y: float = None,
                      vx: float = None, vy: float = None) -> bool:
        with self._lock:
            target = self._targets.get(target_id)
            if target is None:
                return False
            if x is not None:
                target.x = x
            if y is not None:
                target.y = y
            if vx is not None:
                target.vx = vx
            if vy is not None:
                target.vy = vy
            return True

    def attach_target_to_camera(self, camera_id: str, target_id: str) -> bool:
        with self._lock:
            if camera_id not in self._cameras:
                return False
            if target_id not in self._targets:
                return False
            self._camera_targets[camera_id].add(target_id)
            return True

    def detach_target_from_camera(self, camera_id: str, target_id: str) -> bool:
        with self._lock:
            tset = self._camera_targets.get(camera_id)
            if tset and target_id in tset:
                tset.discard(target_id)
                return True
            return False

    def get_targets_for_camera(self, camera_id: str) -> List[CameraTarget]:
        tset = self._camera_targets.get(camera_id, set())
        return [self._targets[tid] for tid in tset if tid in self._targets]

    # -- Shake System --------------------------------------------------------

    def start_shake(self, camera_id: str, profile: ShakeProfile = ShakeProfile.IMPACT,
                    intensity: float = 1.0, duration: Optional[float] = None) -> bool:
        with self._lock:
            if camera_id not in self._cameras:
                return False
            preset = SHAKE_PRESETS.get(profile, SHAKE_PRESETS[ShakeProfile.IMPACT])
            config = ShakeConfig(
                profile=profile,
                intensity=intensity * preset["intensity"],
                duration=duration if duration is not None else preset["duration"],
                frequency=preset["frequency"],
                decay=preset["decay"],
                roughness=preset["roughness"],
                max_offset=preset["max_offset"],
            )
            self._shake_configs[camera_id] = config
            self._perlin_offsets[camera_id] = (
                random.uniform(0.0, 100.0),
                random.uniform(0.0, 100.0),
            )
            state = self._camera_states.get(camera_id)
            if state:
                state.is_shaking = True
                state.shake_intensity = config.intensity
            return True

    def stop_shake(self, camera_id: str) -> bool:
        with self._lock:
            self._shake_configs.pop(camera_id, None)
            state = self._camera_states.get(camera_id)
            if state:
                state.is_shaking = False
                state.shake_intensity = 0.0
                state.shake_offset_x = 0.0
                state.shake_offset_y = 0.0
            return True

    # -- Cinematic Sequences -------------------------------------------------

    def create_sequence(self, name: str = "Sequence",
                        is_looping: bool = False) -> CinematicSequence:
        with self._lock:
            seq = CinematicSequence(name=name, is_looping=is_looping)
            self._sequences[seq.sequence_id] = seq
            return seq

    def add_keyframe(self, sequence_id: str, time: float, x: float, y: float,
                     zoom: float = 1.0, transition: TransitionType = TransitionType.EASE_IN_OUT,
                     label: str = "") -> Optional[CinematicKeyframe]:
        with self._lock:
            seq = self._sequences.get(sequence_id)
            if seq is None:
                return None
            kf = CinematicKeyframe(time=time, x=x, y=y, zoom=zoom,
                                   transition=transition, label=label)
            seq.keyframes.append(kf)
            seq.keyframes.sort(key=lambda k: k.time)
            if seq.keyframes:
                seq.total_duration = seq.keyframes[-1].time
            return kf

    def play_sequence(self, sequence_id: str) -> bool:
        with self._lock:
            seq = self._sequences.get(sequence_id)
            if seq is None:
                return False
            seq.is_playing = True
            seq.current_time = 0.0
            seq.current_keyframe_index = 0
            return True

    def stop_sequence(self, sequence_id: str) -> bool:
        with self._lock:
            seq = self._sequences.get(sequence_id)
            if seq is None:
                return False
            seq.is_playing = False
            return True

    def get_sequence(self, sequence_id: str) -> Optional[CinematicSequence]:
        return self._sequences.get(sequence_id)

    def list_sequences(self) -> List[CinematicSequence]:
        return list(self._sequences.values())

    # -- Perlin Noise Helper -------------------------------------------------

    @staticmethod
    def _perlin_noise(x: float, y: float, seed: int = 0) -> float:
        """Simple value-noise approximation with smooth interpolation."""
        ix, iy = int(math.floor(x)), int(math.floor(y))
        fx, fy = x - ix, y - iy
        fx = fx * fx * (3.0 - 2.0 * fx)
        fy = fy * fy * (3.0 - 2.0 * fy)

        def _hash(px: int, py: int) -> float:
            h = (px * 374761393 + py * 668265263 + seed * 1274126177) & 0x7FFFFFFF
            return (h % 10000) / 10000.0

        n00 = _hash(ix, iy)
        n10 = _hash(ix + 1, iy)
        n01 = _hash(ix, iy + 1)
        n11 = _hash(ix + 1, iy + 1)
        nx0 = n00 + (n10 - n00) * fx
        nx1 = n01 + (n11 - n01) * fx
        return (nx0 + (nx1 - nx0) * fy) * 2.0 - 1.0

    # -- Tick / Update -------------------------------------------------------

    def tick(self, delta_time: float) -> CameraState:
        """Advance camera simulation by delta_time seconds."""
        with self._lock:
            active_id = self._active_camera_id
            config = self._cameras.get(active_id)
            if not config:
                return CameraState()

            state = self._camera_states.get(active_id)
            if not state:
                return CameraState()

            # Compute weighted centroid of attached targets
            targets = self.get_targets_for_camera(active_id)
            if targets and config.mode != CameraMode.FREE:
                active_targets = [t for t in targets if t.is_active]
                if active_targets:
                    total_weight = sum(t.weight for t in active_targets) or 1.0
                    centroid_x = sum(t.x * t.weight for t in active_targets) / total_weight
                    centroid_y = sum(t.y * t.weight for t in active_targets) / total_weight
                    avg_vx = sum(t.vx * t.weight for t in active_targets) / total_weight
                    avg_vy = sum(t.vy * t.weight for t in active_targets) / total_weight

                    # Look-ahead for predictive following
                    look_ahead_x = min(max(avg_vx * config.look_ahead_factor,
                                           -config.look_ahead_max), config.look_ahead_max)
                    look_ahead_y = min(max(avg_vy * config.look_ahead_factor,
                                           -config.look_ahead_max), config.look_ahead_max)

                    target_x = centroid_x + look_ahead_x + config.follow_offset_x
                    target_y = centroid_y + look_ahead_y + config.follow_offset_y
                else:
                    target_x, target_y = state.target_x, state.target_y
            else:
                target_x, target_y = state.target_x, state.target_y

            state.target_x = target_x
            state.target_y = target_y

            # Follow logic
            if config.mode in (CameraMode.FOLLOW, CameraMode.FRAME_TARGET):
                if config.follow_style == FollowStyle.SMOOTH_DAMP:
                    new_x, new_y = state.x, state.y
                    new_vx = state.velocity_x = (target_x - state.x) / max(config.smooth_time, 0.001)
                    new_vy = state.velocity_y = (target_y - state.y) / max(config.smooth_time, 0.001)
                    new_x += new_vx * delta_time
                    new_y += new_vy * delta_time
                elif config.follow_style == FollowStyle.SPRING:
                    force_x = (target_x - state.x) * config.spring_stiffness
                    force_y = (target_y - state.y) * config.spring_stiffness
                    state.velocity_x += force_x * delta_time
                    state.velocity_y += force_y * delta_time
                    state.velocity_x *= (1.0 - config.spring_damping * delta_time)
                    state.velocity_y *= (1.0 - config.spring_damping * delta_time)
                    new_x = state.x + state.velocity_x * delta_time
                    new_y = state.y + state.velocity_y * delta_time
                else:
                    t = min(config.follow_speed * delta_time, 1.0)
                    new_x = state.x + (target_x - state.x) * t
                    new_y = state.y + (target_y - state.y) * t

                # Dead zone
                if config.dead_zone_shape == DeadZoneShape.RECTANGLE:
                    dx, dy = new_x - target_x, new_y - target_y
                    if abs(dx) < config.dead_zone_width * 0.5:
                        new_x = target_x
                    if abs(dy) < config.dead_zone_height * 0.5:
                        new_y = target_y
                elif config.dead_zone_shape == DeadZoneShape.CIRCLE:
                    dist = math.hypot(new_x - target_x, new_y - target_y)
                    dz_radius = min(config.dead_zone_width, config.dead_zone_height) * 0.5
                    if dist < dz_radius:
                        new_x, new_y = target_x, target_y

                state.x = new_x
                state.y = new_y

            # Boundary clamping
            if config.boundary_left > float("-inf"):
                state.x = max(state.x, config.boundary_left)
            if config.boundary_right < float("inf"):
                state.x = min(state.x, config.boundary_right)
            if config.boundary_top > float("-inf"):
                state.y = max(state.y, config.boundary_top)
            if config.boundary_bottom < float("inf"):
                state.y = min(state.y, config.boundary_bottom)

            # Shake processing
            shake = self._shake_configs.get(active_id)
            if shake and state.is_shaking:
                offsets = self._perlin_offsets.get(active_id, (0.0, 0.0))
                elapsed = _time_module.time()
                noise_x = self._perlin_noise(elapsed * shake.frequency, offsets[0])
                noise_y = self._perlin_noise(elapsed * shake.frequency, offsets[1])
                shake_offset = shake.intensity * shake.max_offset
                state.shake_offset_x = noise_x * shake_offset
                state.shake_offset_y = noise_y * shake_offset
                shake.intensity *= shake.decay ** (delta_time * 60.0)
                state.shake_intensity = shake.intensity
                if shake.intensity < 0.001 and shake.duration < 999.0:
                    self.stop_shake(active_id)

            # Cinematic sequence processing
            for seq_id, seq in list(self._sequences.items()):
                if seq.is_playing:
                    seq.current_time += delta_time
                    keys = seq.keyframes
                    if seq.current_time >= seq.total_duration:
                        if seq.is_looping:
                            seq.current_time %= seq.total_duration
                            seq.current_keyframe_index = 0
                        else:
                            seq.is_playing = False
                            seq.current_time = seq.total_duration
                    # Find active keyframe pair
                    for i in range(len(keys) - 1):
                        if keys[i].time <= seq.current_time <= keys[i + 1].time:
                            seq.current_keyframe_index = i
                            t_range = keys[i + 1].time - keys[i].time
                            t = (seq.current_time - keys[i].time) / max(t_range, 0.001)
                            state.x = keys[i].x + (keys[i + 1].x - keys[i].x) * t
                            state.y = keys[i].y + (keys[i + 1].y - keys[i].y) * t
                            state.zoom = keys[i].zoom + (keys[i + 1].zoom - keys[i].zoom) * t
                            break

            return state

    def get_system_stats(self) -> Dict[str, Any]:
        """Return system-wide statistics."""
        active_cam = self.get_active_camera()
        active_state = self._camera_states.get(self._active_camera_id)
        return {
            "camera_count": len(self._cameras),
            "target_count": len(self._targets),
            "sequence_count": len(self._sequences),
            "active_camera": active_cam.name if active_cam else "none",
            "active_shaking": active_state.is_shaking if active_state else False,
            "shake_intensity": active_state.shake_intensity if active_state else 0.0,
        }


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_camera_controller() -> EngineCameraController:
    return EngineCameraController.get_instance()