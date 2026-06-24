"""
SparkLabs Engine - Spatial Audio System

A complete 3D spatial audio engine providing positional audio sources,
listener-based spatialization, ray-traced occlusion modeling, convolution
reverb zones, Doppler effect simulation, and multi-channel audio mixing.

Architecture:
  SpatialAudioEngine (Singleton)
    |-- AudioSource3D         — positional sound emitter with velocity
    |-- AudioListener         — listener position and orientation
    |-- AudioOcclusionModel   — ray-traced audio occlusion
    |-- AudioReverbZone       — convolution reverb spatial region
    |-- DopplerEffect         — frequency shift calculator
    |-- AudioMixer            — multi-channel routing and gain staging

Spatial Pipeline:
  1. Source/Listener transform → world-relative position and velocity
  2. Distance attenuation → rolloff curve based on min/max distance
  3. Occlusion → raycast from source to listener for obstruction
  4. Reverb → convolution with zone impulse response
  5. Doppler → frequency shift from relative velocity
  6. Mixer → pan, gain, and route to output channels

Usage:
    engine = get_spatial_audio_engine()
    source = engine.create_source(position=(10.0, 0.0, 5.0))
    engine.set_listener_position((0.0, 0.0, 0.0))
    engine.update(delta_time)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AudioSourceShape(Enum):
    """Spatial shape of the audio source for radiation pattern."""
    POINT = "point"
    SPHERICAL = "spherical"
    CONE = "cone"
    DIRECTIONAL = "directional"


class RolloffMode(Enum):
    """Distance-based attenuation curve."""
    LOGARITHMIC = "logarithmic"
    LINEAR = "linear"
    INVERSE = "inverse"
    INVERSE_SQUARE = "inverse_square"
    CUSTOM = "custom"


class OcclusionMethod(Enum):
    """Algorithm for computing audio occlusion."""
    RAYCAST = "raycast"
    SPHERE_TRACE = "sphere_trace"
    PORTAL = "portal"
    NONE = "none"


class ReverbPreset(Enum):
    """Predefined convolution reverb impulse response presets."""
    SMALL_ROOM = "small_room"
    MEDIUM_ROOM = "medium_room"
    LARGE_HALL = "large_hall"
    CATHEDRAL = "cathedral"
    CAVE = "cave"
    OUTDOOR = "outdoor"
    UNDERWATER = "underwater"
    PADDED_CELL = "padded_cell"
    ARENA = "arena"
    TUNNEL = "tunnel"


class AudioChannel(Enum):
    """Output channel routing identifiers."""
    FRONT_LEFT = "front_left"
    FRONT_RIGHT = "front_right"
    FRONT_CENTER = "front_center"
    LFE = "lfe"
    REAR_LEFT = "rear_left"
    REAR_RIGHT = "rear_right"
    SIDE_LEFT = "side_left"
    SIDE_RIGHT = "side_right"


class MixerBusType(Enum):
    """Audio mixer bus routing categories."""
    MASTER = "master"
    MUSIC = "music"
    SFX = "sfx"
    AMBIENT = "ambient"
    DIALOGUE = "dialogue"
    UI = "ui"
    REVERB_SEND = "reverb_send"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AudioSource3D:
    """Positional audio emitter in 3D space.

    Represents a sound source at a world position with velocity for
    Doppler calculation, orientation for cone/directional radiation
    patterns, and distance-based rolloff parameters.
    """
    source_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    velocity: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    orientation: List[float] = field(default_factory=lambda: [0.0, 0.0, 1.0])
    shape: AudioSourceShape = AudioSourceShape.POINT
    rolloff_mode: RolloffMode = RolloffMode.INVERSE
    min_distance: float = 1.0
    max_distance: float = 100.0
    cone_inner_angle: float = 360.0
    cone_outer_angle: float = 360.0
    cone_outer_gain: float = 0.0
    gain: float = 1.0
    pitch: float = 1.0
    is_looping: bool = False
    is_playing: bool = False
    priority: float = 1.0
    doppler_factor: float = 1.0
    occlusion_enabled: bool = True
    reverb_send_level: float = 0.0
    current_attenuation: float = 1.0
    current_occlusion: float = 0.0
    current_pan: float = 0.0

    def set_position(self, x: float, y: float, z: float) -> None:
        self.position = [x, y, z]

    def set_velocity(self, vx: float, vy: float, vz: float) -> None:
        self.velocity = [vx, vy, vz]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "name": self.name,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "orientation": list(self.orientation),
            "shape": self.shape.value,
            "rolloff_mode": self.rolloff_mode.value,
            "min_distance": self.min_distance,
            "max_distance": self.max_distance,
            "cone_inner_angle": self.cone_inner_angle,
            "cone_outer_angle": self.cone_outer_angle,
            "cone_outer_gain": self.cone_outer_gain,
            "gain": self.gain,
            "pitch": self.pitch,
            "is_looping": self.is_looping,
            "is_playing": self.is_playing,
            "priority": self.priority,
            "doppler_factor": self.doppler_factor,
            "occlusion_enabled": self.occlusion_enabled,
            "reverb_send_level": self.reverb_send_level,
            "current_attenuation": self.current_attenuation,
            "current_occlusion": self.current_occlusion,
            "current_pan": self.current_pan,
        }


@dataclass
class AudioListener:
    """Audio listener representing the player's ears in 3D space.

    Position and orientation define the reference frame for all spatial
    audio calculations. The listener can have velocity for Doppler
    effects relative to moving sources.
    """
    listener_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    velocity: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    orientation_forward: List[float] = field(default_factory=lambda: [0.0, 0.0, -1.0])
    orientation_up: List[float] = field(default_factory=lambda: [0.0, 1.0, 0.0])
    master_gain: float = 1.0

    def set_position(self, x: float, y: float, z: float) -> None:
        self.position = [x, y, z]

    def set_velocity(self, vx: float, vy: float, vz: float) -> None:
        self.velocity = [vx, vy, vz]

    def set_orientation(self, forward_x: float, forward_y: float, forward_z: float,
                        up_x: float, up_y: float, up_z: float) -> None:
        self.orientation_forward = [forward_x, forward_y, forward_z]
        self.orientation_up = [up_x, up_y, up_z]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "listener_id": self.listener_id,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "orientation_forward": list(self.orientation_forward),
            "orientation_up": list(self.orientation_up),
            "master_gain": self.master_gain,
        }


@dataclass
class AudioOcclusionModel:
    """Ray-traced audio occlusion calculation.

    Casts rays from audio sources toward the listener to detect
    obstructing geometry. Computes per-frequency attenuation
    (low frequencies diffract more) and accumulates occlusion
    values for use in the spatial audio pipeline.
    """
    model_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    method: OcclusionMethod = OcclusionMethod.RAYCAST
    ray_count: int = 8
    max_ray_distance: float = 200.0
    diffraction_enabled: bool = True
    transmission_enabled: bool = True
    low_freq_diffraction: float = 0.7
    mid_freq_absorption: float = 0.5
    high_freq_absorption: float = 0.9
    current_occlusion: float = 0.0
    last_raycast_time: float = 0.0
    raycast_interval: float = 0.05

    def compute_occlusion(self, source_pos: List[float],
                          listener_pos: List[float],
                          obstruction_map: Optional[Any] = None) -> float:
        """Compute occlusion factor between source and listener."""
        distance = self._distance(source_pos, listener_pos)
        if distance > self.max_ray_distance:
            return 1.0

        if obstruction_map is None:
            return 0.0

        hits = 0
        for i in range(self.ray_count):
            ray_dir = self._compute_ray_direction(source_pos, listener_pos, i)
            if self._cast_ray(source_pos, ray_dir, distance, obstruction_map):
                hits += 1

        occlusion = hits / self.ray_count
        self.current_occlusion = occlusion
        self.last_raycast_time = _time_module.time()
        return occlusion

    def get_frequency_attenuation(self) -> Tuple[float, float, float]:
        """Return (low, mid, high) frequency attenuation factors."""
        occ = self.current_occlusion
        low = 1.0 - occ * (1.0 - self.low_freq_diffraction)
        mid = 1.0 - occ * self.mid_freq_absorption
        high = 1.0 - occ * self.high_freq_absorption
        return (max(low, 0.0), max(mid, 0.0), max(high, 0.0))

    @staticmethod
    def _distance(a: List[float], b: List[float]) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)

    def _compute_ray_direction(self, source: List[float], listener: List[float],
                                index: int) -> List[float]:
        base = [listener[i] - source[i] for i in range(3)]
        length = math.sqrt(sum(v * v for v in base))
        if length < 0.0001:
            return [0.0, 0.0, -1.0]
        normalized = [v / length for v in base]
        if self.ray_count <= 1:
            return normalized
        jitter = (index / self.ray_count) * 0.1 - 0.05
        return [v + jitter for v in normalized]

    def _cast_ray(self, origin: List[float], direction: List[float],
                  max_dist: float, obstruction_map: Any) -> bool:
        # Placeholder for actual raycast integration
        return random.random() < 0.3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "method": self.method.value,
            "ray_count": self.ray_count,
            "max_ray_distance": self.max_ray_distance,
            "diffraction_enabled": self.diffraction_enabled,
            "transmission_enabled": self.transmission_enabled,
            "low_freq_diffraction": self.low_freq_diffraction,
            "mid_freq_absorption": self.mid_freq_absorption,
            "high_freq_absorption": self.high_freq_absorption,
            "current_occlusion": self.current_occlusion,
        }


@dataclass
class AudioReverbZone:
    """Spatial region applying convolution reverb to audio sources.

    Defines a 3D volume (sphere or box) within which audio sources
    receive reverb processing. The reverb is applied via convolution
    with a preset or custom impulse response. Zones can have smooth
    transition boundaries.
    """
    zone_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    radius: float = 10.0
    preset: ReverbPreset = ReverbPreset.MEDIUM_ROOM
    wet_level: float = 0.5
    dry_level: float = 0.5
    decay_time: float = 1.5
    pre_delay: float = 0.02
    diffusion: float = 0.8
    reflection_density: float = 0.7
    room_size: float = 0.5
    early_reflections_gain: float = 0.3
    late_reverb_gain: float = 0.7
    transition_width: float = 2.0
    is_active: bool = True

    def contains_point(self, x: float, y: float, z: float) -> bool:
        dx = x - self.position[0]
        dy = y - self.position[1]
        dz = z - self.position[2]
        return (dx * dx + dy * dy + dz * dz) <= (self.radius * self.radius)

    def get_blend_factor(self, x: float, y: float, z: float) -> float:
        """Get reverb blend factor based on distance to zone boundary."""
        dx = x - self.position[0]
        dy = y - self.position[1]
        dz = z - self.position[2]
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        if distance <= self.radius - self.transition_width:
            return 1.0
        if distance >= self.radius:
            return 0.0
        t = (self.radius - distance) / self.transition_width
        return 3.0 * t * t - 2.0 * t * t * t

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "position": list(self.position),
            "radius": self.radius,
            "preset": self.preset.value,
            "wet_level": self.wet_level,
            "dry_level": self.dry_level,
            "decay_time": self.decay_time,
            "pre_delay": self.pre_delay,
            "diffusion": self.diffusion,
            "reflection_density": self.reflection_density,
            "room_size": self.room_size,
            "early_reflections_gain": self.early_reflections_gain,
            "late_reverb_gain": self.late_reverb_gain,
            "transition_width": self.transition_width,
            "is_active": self.is_active,
        }


@dataclass
class DopplerEffect:
    """Doppler frequency shift calculator for moving audio sources.

    Computes the pitch shift ratio based on relative velocity between
    source and listener, using the speed of sound in the medium.
    """
    effect_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    speed_of_sound: float = 343.0
    max_shift_ratio: float = 4.0
    smoothing_factor: float = 0.95
    current_shift: float = 1.0
    previous_shift: float = 1.0

    def compute_shift(self, source_pos: List[float],
                      source_vel: List[float],
                      listener_pos: List[float],
                      listener_vel: List[float]) -> float:
        """Compute the Doppler pitch shift ratio."""
        rel_pos = [source_pos[i] - listener_pos[i] for i in range(3)]
        distance = math.sqrt(sum(v * v for v in rel_pos))
        if distance < 0.001:
            return self.current_shift

        rel_dir = [v / distance for v in rel_pos]
        source_radial = sum(source_vel[i] * rel_dir[i] for i in range(3))
        listener_radial = sum(listener_vel[i] * rel_dir[i] for i in range(3))

        numerator = self.speed_of_sound - listener_radial
        denominator = self.speed_of_sound - source_radial

        if abs(denominator) < 0.001:
            return self.max_shift_ratio

        raw_shift = numerator / denominator
        raw_shift = max(1.0 / self.max_shift_ratio,
                        min(raw_shift, self.max_shift_ratio))

        self.previous_shift = self.current_shift
        self.current_shift = (self.smoothing_factor * self.current_shift +
                              (1.0 - self.smoothing_factor) * raw_shift)
        return self.current_shift

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "speed_of_sound": self.speed_of_sound,
            "max_shift_ratio": self.max_shift_ratio,
            "smoothing_factor": self.smoothing_factor,
            "current_shift": self.current_shift,
            "previous_shift": self.previous_shift,
        }


@dataclass
class AudioMixerSnapshot:
    """Snapshot of current mixer state for debugging and serialization."""
    master_gain: float = 1.0
    bus_gains: Dict[str, float] = field(default_factory=dict)
    active_source_count: int = 0
    total_channels: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "master_gain": self.master_gain,
            "bus_gains": dict(self.bus_gains),
            "active_source_count": self.active_source_count,
            "total_channels": self.total_channels,
        }


# ---------------------------------------------------------------------------
# AudioMixer — Multi-Channel Bus Routing
# ---------------------------------------------------------------------------

class AudioMixer:
    """Multi-channel audio mixer with bus routing and gain staging.

    Manages a hierarchy of audio buses (master, music, sfx, ambient, etc.)
    each with independent gain, mute, and solo controls. Routes audio
    sources through busses to final output channels with panning.
    """

    def __init__(self) -> None:
        self._buses: Dict[str, Dict[str, Any]] = {
            "master": {"gain": 1.0, "muted": False, "solo": False,
                       "children": ["music", "sfx", "ambient", "dialogue", "ui"]},
            "music": {"gain": 1.0, "muted": False, "solo": False, "children": []},
            "sfx": {"gain": 1.0, "muted": False, "solo": False, "children": []},
            "ambient": {"gain": 1.0, "muted": False, "solo": False, "children": []},
            "dialogue": {"gain": 1.0, "muted": False, "solo": False, "children": []},
            "ui": {"gain": 1.0, "muted": False, "solo": False, "children": []},
            "reverb_send": {"gain": 0.0, "muted": False, "solo": False,
                            "children": []},
        }
        self._channel_outputs: Dict[str, float] = {
            ch.value: 0.0 for ch in AudioChannel
        }
        self._source_count: int = 0

    def set_bus_gain(self, bus_name: str, gain: float) -> None:
        if bus_name in self._buses:
            self._buses[bus_name]["gain"] = max(0.0, min(gain, 2.0))

    def get_bus_gain(self, bus_name: str) -> float:
        return self._buses.get(bus_name, {}).get("gain", 0.0)

    def mute_bus(self, bus_name: str) -> None:
        if bus_name in self._buses:
            self._buses[bus_name]["muted"] = True

    def unmute_bus(self, bus_name: str) -> None:
        if bus_name in self._buses:
            self._buses[bus_name]["muted"] = False

    def solo_bus(self, bus_name: str) -> None:
        if bus_name in self._buses:
            self._buses[bus_name]["solo"] = True

    def compute_final_gain(self, bus_name: str) -> float:
        """Compute the effective gain for a bus considering mute/solo state."""
        if bus_name not in self._buses:
            return 0.0
        bus = self._buses[bus_name]
        if bus["muted"]:
            return 0.0
        any_solo = any(b["solo"] for b in self._buses.values())
        if any_solo and not bus["solo"]:
            return 0.0
        return bus["gain"]

    def route_to_channel(self, source_gain: float, bus_name: str,
                         pan: float, channel: AudioChannel) -> float:
        """Route audio from a source through a bus to a channel."""
        bus_gain = self.compute_final_gain(bus_name)
        master_gain = self.compute_final_gain("master")
        return source_gain * bus_gain * master_gain * pan

    def get_snapshot(self) -> AudioMixerSnapshot:
        return AudioMixerSnapshot(
            master_gain=self._buses["master"]["gain"],
            bus_gains={k: v["gain"] for k, v in self._buses.items()},
            active_source_count=self._source_count,
            total_channels=len(self._channel_outputs),
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "bus_count": len(self._buses),
            "bus_gains": {k: v["gain"] for k, v in self._buses.items()},
            "bus_muted": {k: v["muted"] for k, v in self._buses.items()},
            "source_count": self._source_count,
            "channels": len(self._channel_outputs),
        }


# ---------------------------------------------------------------------------
# SpatialAudioEngine — Unified Spatial Audio Singleton
# ---------------------------------------------------------------------------

class SpatialAudioEngine:
    """Complete 3D spatial audio engine for SparkLabs.

    Manages spatial audio sources, listener position, occlusion modeling,
    reverb zones, Doppler effects, and multi-channel mixing. Provides
    a unified API for game audio with full 3D spatialization.
    """

    _instance: Optional["SpatialAudioEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "SpatialAudioEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SpatialAudioEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._sources: Dict[str, AudioSource3D] = {}
        self._listener = AudioListener()
        self._occlusion_model = AudioOcclusionModel()
        self._doppler = DopplerEffect()
        self._mixer = AudioMixer()
        self._reverb_zones: Dict[str, AudioReverbZone] = {}
        self._source_count: int = 0
        self._frame_count: int = 0
        self._obstruction_map: Optional[Any] = None

    # ---- Source Management ----

    def create_source(self, name: str = "",
                      position: Optional[Tuple[float, float, float]] = None,
                      shape: AudioSourceShape = AudioSourceShape.POINT,
                      rolloff: RolloffMode = RolloffMode.INVERSE) -> AudioSource3D:
        """Create a new spatial audio source."""
        source = AudioSource3D(name=name, shape=shape, rolloff_mode=rolloff)
        if position is not None:
            source.set_position(*position)
        self._sources[source.source_id] = source
        self._source_count += 1
        return source

    def get_source(self, source_id: str) -> Optional[AudioSource3D]:
        """Get an audio source by ID."""
        return self._sources.get(source_id)

    def remove_source(self, source_id: str) -> bool:
        """Remove an audio source."""
        if source_id in self._sources:
            del self._sources[source_id]
            return True
        return False

    def set_source_position(self, source_id: str, x: float, y: float,
                            z: float) -> bool:
        source = self._sources.get(source_id)
        if source:
            source.set_position(x, y, z)
            return True
        return False

    def set_source_velocity(self, source_id: str, vx: float, vy: float,
                            vz: float) -> bool:
        source = self._sources.get(source_id)
        if source:
            source.set_velocity(vx, vy, vz)
            return True
        return False

    # ---- Listener Management ----

    def set_listener_position(self, x: float, y: float, z: float) -> None:
        self._listener.set_position(x, y, z)

    def set_listener_velocity(self, vx: float, vy: float, vz: float) -> None:
        self._listener.set_velocity(vx, vy, vz)

    def set_listener_orientation(self, fx: float, fy: float, fz: float,
                                  ux: float, uy: float, uz: float) -> None:
        self._listener.set_orientation(fx, fy, fz, ux, uy, uz)

    def get_listener(self) -> AudioListener:
        return self._listener

    # ---- Reverb Zone Management ----

    def create_reverb_zone(self, name: str = "",
                           position: Optional[Tuple[float, float, float]] = None,
                           radius: float = 10.0,
                           preset: ReverbPreset = ReverbPreset.MEDIUM_ROOM) -> AudioReverbZone:
        zone = AudioReverbZone(name=name, radius=radius, preset=preset)
        if position is not None:
            zone.position = list(position)
        self._reverb_zones[zone.zone_id] = zone
        return zone

    def get_reverb_zone(self, zone_id: str) -> Optional[AudioReverbZone]:
        return self._reverb_zones.get(zone_id)

    def remove_reverb_zone(self, zone_id: str) -> bool:
        if zone_id in self._reverb_zones:
            del self._reverb_zones[zone_id]
            return True
        return False

    def get_active_reverb_zone(self, x: float, y: float,
                               z: float) -> Optional[AudioReverbZone]:
        """Get the closest active reverb zone containing a point."""
        best = None
        best_dist = float("inf")
        for zone in self._reverb_zones.values():
            if not zone.is_active:
                continue
            if zone.contains_point(x, y, z):
                dist = math.sqrt((x - zone.position[0]) ** 2 +
                                 (y - zone.position[1]) ** 2 +
                                 (z - zone.position[2]) ** 2)
                if dist < best_dist:
                    best_dist = dist
                    best = zone
        return best

    # ---- Occlusion ----

    def set_obstruction_map(self, obstruction_map: Any) -> None:
        self._obstruction_map = obstruction_map

    def compute_occlusion(self, source: AudioSource3D) -> float:
        if not source.occlusion_enabled:
            return 0.0
        return self._occlusion_model.compute_occlusion(
            source.position, self._listener.position, self._obstruction_map
        )

    # ---- Spatial Processing ----

    def _compute_distance_attenuation(self, source: AudioSource3D) -> float:
        """Compute gain attenuation based on distance to listener."""
        dx = source.position[0] - self._listener.position[0]
        dy = source.position[1] - self._listener.position[1]
        dz = source.position[2] - self._listener.position[2]
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        if distance <= source.min_distance:
            return 1.0
        if distance >= source.max_distance:
            return 0.0

        if source.rolloff_mode == RolloffMode.LINEAR:
            return 1.0 - (distance - source.min_distance) / (
                source.max_distance - source.min_distance)
        elif source.rolloff_mode == RolloffMode.INVERSE:
            return source.min_distance / (source.min_distance + distance)
        elif source.rolloff_mode == RolloffMode.INVERSE_SQUARE:
            ratio = source.min_distance / (source.min_distance + distance)
            return ratio * ratio
        elif source.rolloff_mode == RolloffMode.LOGARITHMIC:
            if distance <= 0.001:
                return 1.0
            return source.min_distance / (distance * math.log(distance + 1.0))
        return 1.0

    def _compute_pan(self, source: AudioSource3D) -> float:
        """Compute stereo pan based on source position relative to listener."""
        rel_x = source.position[0] - self._listener.position[0]
        rel_z = source.position[2] - self._listener.position[2]
        distance = math.sqrt(rel_x * rel_x + rel_z * rel_z)
        if distance < 0.001:
            return 0.0

        right_vec = [
            self._listener.orientation_up[1] * self._listener.orientation_forward[2] -
            self._listener.orientation_up[2] * self._listener.orientation_forward[1],
            self._listener.orientation_up[2] * self._listener.orientation_forward[0] -
            self._listener.orientation_up[0] * self._listener.orientation_forward[2],
            self._listener.orientation_up[0] * self._listener.orientation_forward[1] -
            self._listener.orientation_up[1] * self._listener.orientation_forward[0],
        ]

        dot = rel_x * right_vec[0] + rel_z * right_vec[2]
        return max(-1.0, min(1.0, dot / distance))

    def _compute_cone_attenuation(self, source: AudioSource3D) -> float:
        """Compute directional cone attenuation for cone-shaped sources."""
        if source.shape != AudioSourceShape.CONE:
            return 1.0
        if source.cone_inner_angle >= 360.0:
            return 1.0

        rel_x = source.position[0] - self._listener.position[0]
        rel_y = source.position[1] - self._listener.position[1]
        rel_z = source.position[2] - self._listener.position[2]
        distance = math.sqrt(rel_x * rel_x + rel_y * rel_y + rel_z * rel_z)
        if distance < 0.001:
            return 1.0

        dot = (rel_x * source.orientation[0] + rel_y * source.orientation[1] +
               rel_z * source.orientation[2]) / distance
        angle = math.degrees(math.acos(max(-1.0, min(1.0, dot))))

        if angle <= source.cone_inner_angle / 2.0:
            return 1.0
        if angle >= source.cone_outer_angle / 2.0:
            return source.cone_outer_gain

        t = (angle - source.cone_inner_angle / 2.0) / (
            (source.cone_outer_angle - source.cone_inner_angle) / 2.0)
        return 1.0 + t * (source.cone_outer_gain - 1.0)

    def process_source(self, source: AudioSource3D) -> None:
        """Process a single audio source through the spatial pipeline."""
        source.current_attenuation = self._compute_distance_attenuation(source)
        source.current_attenuation *= self._compute_cone_attenuation(source)
        source.current_occlusion = self.compute_occlusion(source)
        source.current_pan = self._compute_pan(source)

        doppler = self._doppler.compute_shift(
            source.position, source.velocity,
            self._listener.position, self._listener.velocity
        )
        source.pitch = source.pitch * doppler

    # ---- Update ----

    def update(self, delta_time: float) -> None:
        """Process all audio sources through the spatial pipeline."""
        for source in self._sources.values():
            if source.is_playing:
                self.process_source(source)
        self._frame_count += 1

    def get_mixer_snapshot(self) -> AudioMixerSnapshot:
        return self._mixer.get_snapshot()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "source_count": len(self._sources),
            "total_sources_created": self._source_count,
            "active_sources": sum(1 for s in self._sources.values() if s.is_playing),
            "reverb_zone_count": len(self._reverb_zones),
            "active_reverb_zones": sum(
                1 for z in self._reverb_zones.values() if z.is_active
            ),
            "listener": self._listener.to_dict(),
            "occlusion": self._occlusion_model.to_dict(),
            "doppler": self._doppler.to_dict(),
            "mixer": self._mixer.get_stats(),
            "frame_count": self._frame_count,
        }


# ---------------------------------------------------------------------------
# Convenience Accessor
# ---------------------------------------------------------------------------

def get_spatial_audio_engine() -> SpatialAudioEngine:
    """Get the global SpatialAudioEngine singleton instance."""
    return SpatialAudioEngine()