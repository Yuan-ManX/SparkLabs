"""
SparkLabs Engine - AI-Driven Audio Management System

Runtime audio engine providing sound effect playback, music streaming,
spatial audio positioning, and dynamic mixing. Manages audio assets
through a priority-based pool with channel routing, voice stealing,
and automatic fade transitions.

Architecture:
  AudioSystemEngine
    |-- AssetRegistry — audio asset catalog with metadata and tags
    |-- InstanceManager — active playback instance lifecycle tracking
    |-- ChannelRouter — category-based audio channel routing
    |-- MixerEngine — multi-channel mixing with effects and master volume
    |-- Spatializer — 3D distance-based attenuation and stereo panning

Audio Features:
  - SFX: one-shot and looping sound effects with pitch/volume variation
  - MUSIC: playlist streaming with smooth crossfade transitions
  - SPATIAL: distance-based attenuation and stereo panning
  - MIXING: master, music, sfx, voice, and ambient volume channels
  - VOICE_STEALING: priority-based instance eviction when max channels reached
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AudioCategory(Enum):
    """Classification of audio content by semantic type for routing."""
    SFX = "sfx"
    MUSIC = "music"
    AMBIENT = "ambient"
    VOICE = "voice"
    UI = "ui"
    FOOTSTEP = "footstep"
    WEAPON = "weapon"
    ENVIRONMENT = "environment"
    VEHICLE = "vehicle"
    MAGIC = "magic"


class AudioPriority(Enum):
    """Playback priority for voice stealing. ALWAYS-priority instances cannot be evicted."""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3
    ALWAYS = 4


class PlaybackMode(Enum):
    """Playback behavior determining how an audio asset repeats."""
    ONCE = "once"
    LOOP = "loop"
    PING_PONG = "ping_pong"
    RANDOM = "random"
    SEQUENTIAL = "sequential"


class InstanceState(Enum):
    """Runtime state of an audio playback instance."""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    FADING_IN = "fading_in"
    FADING_OUT = "fading_out"
    STOPPED = "stopped"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AudioAsset:
    """Audio asset definition with metadata and playback parameters."""
    asset_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: AudioCategory = AudioCategory.SFX
    file_path: str = ""
    duration: float = 1.0
    volume: float = 1.0
    pitch: float = 1.0
    priority: AudioPriority = AudioPriority.MEDIUM
    playback_mode: PlaybackMode = PlaybackMode.ONCE
    is_3d: bool = False
    spatial_blend: float = 0.0
    min_distance: float = 10.0
    max_distance: float = 500.0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id, "name": self.name,
            "category": self.category.value, "file_path": self.file_path,
            "duration": self.duration, "volume": self.volume,
            "pitch": self.pitch, "priority": self.priority.name,
            "playback_mode": self.playback_mode.value, "is_3d": self.is_3d,
            "spatial_blend": self.spatial_blend,
            "min_distance": self.min_distance, "max_distance": self.max_distance,
            "tags": self.tags,
        }


@dataclass
class AudioInstance:
    """Runtime playback instance tracking state, position, and fade transitions."""
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    asset_id: str = ""
    state: InstanceState = InstanceState.IDLE
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    volume: float = 1.0
    pitch: float = 1.0
    is_looping: bool = False
    started_at: float = 0.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    channel_id: str = ""
    elapsed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id, "asset_id": self.asset_id,
            "state": self.state.value, "position": list(self.position),
            "volume": round(self.volume, 3), "pitch": round(self.pitch, 3),
            "is_looping": self.is_looping, "started_at": round(self.started_at, 3),
            "fade_in": self.fade_in, "fade_out": self.fade_out,
            "channel_id": self.channel_id, "elapsed": round(self.elapsed, 3),
        }


@dataclass
class AudioChannel:
    """Audio output channel for category-based routing with volume and mute control."""
    channel_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: AudioCategory = AudioCategory.SFX
    volume: float = 1.0
    is_muted: bool = False
    effects: List[str] = field(default_factory=list)
    priority: AudioPriority = AudioPriority.MEDIUM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id, "name": self.name,
            "category": self.category.value, "volume": round(self.volume, 3),
            "is_muted": self.is_muted, "effects": self.effects,
            "priority": self.priority.name,
        }


@dataclass
class AudioMixer:
    """Audio mixer with master volume, sub-channels, and effects chain."""
    mixer_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    master_volume: float = 1.0
    channels: List[str] = field(default_factory=list)
    effects: List[Dict[str, Any]] = field(default_factory=list)
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mixer_id": self.mixer_id, "name": self.name,
            "master_volume": round(self.master_volume, 3),
            "channels": self.channels, "effects": self.effects,
            "is_active": self.is_active,
        }


# ---------------------------------------------------------------------------
# Default Channel Presets
# ---------------------------------------------------------------------------

_DEFAULT_CHANNEL_CONFIGS: List[Dict[str, Any]] = [
    {"name": "Master", "category": "sfx", "volume": 1.0},
    {"name": "Music", "category": "music", "volume": 0.8},
    {"name": "SFX", "category": "sfx", "volume": 1.0},
    {"name": "Ambient", "category": "ambient", "volume": 0.7},
    {"name": "Voice", "category": "voice", "volume": 1.0},
    {"name": "UI", "category": "ui", "volume": 0.9},
    {"name": "Footsteps", "category": "footstep", "volume": 0.6},
    {"name": "Weapons", "category": "weapon", "volume": 1.0},
    {"name": "Environment", "category": "environment", "volume": 0.8},
    {"name": "Vehicles", "category": "vehicle", "volume": 0.85},
    {"name": "Magic", "category": "magic", "volume": 1.0},
]

# Active state set used for counting and filtering
_ACTIVE_STATES = frozenset({
    InstanceState.PLAYING, InstanceState.PAUSED,
    InstanceState.FADING_IN, InstanceState.FADING_OUT,
})


# ---------------------------------------------------------------------------
# AudioSystemEngine — Thread-Safe Singleton
# ---------------------------------------------------------------------------

class AudioSystemEngine:
    """AI-driven audio management system for the SparkLabs game engine.

    Manages the complete audio pipeline including asset loading, instance
    playback, spatial positioning, channel routing, and multi-channel
    mixing with effects. Provides priority-based voice stealing, automatic
    fade transitions, and distance-based 3D attenuation.

    Usage:
        audio = get_audio_system()
        asset = audio.load_asset("explosion", AudioCategory.SFX,
                                  "sounds/explosion.wav", 2.5)
        instance = audio.play(asset.asset_id, (100.0, 50.0, 0.0), 1.0, 1.0, False)
        audio.stop(instance.instance_id)
    """

    _instance: Optional["AudioSystemEngine"] = None
    _lock = threading.RLock()

    _MAX_INSTANCES_PER_CATEGORY: int = 32
    _MAX_TOTAL_INSTANCES: int = 256

    def __new__(cls) -> "AudioSystemEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AudioSystemEngine":
        return cls()

    def _initialize(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._assets: Dict[str, AudioAsset] = {}
        self._instances: Dict[str, AudioInstance] = {}
        self._channels: Dict[str, AudioChannel] = {}
        self._mixers: Dict[str, AudioMixer] = {}
        self._listener_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._total_play_count: int = 0
        self._total_stop_count: int = 0
        self._creation_time: float = time.time()
        self._play_history: deque = deque(maxlen=100)
        self._initialized: bool = True
        self._seed_default_channels()

    def _seed_default_channels(self) -> None:
        for cfg in _DEFAULT_CHANNEL_CONFIGS:
            try:
                cat = AudioCategory(cfg["category"])
            except ValueError:
                cat = AudioCategory.SFX
            channel = AudioChannel(name=cfg["name"], category=cat, volume=cfg["volume"])
            self._channels[channel.channel_id] = channel

    # ------------------------------------------------------------------
    # Spatial Audio
    # ------------------------------------------------------------------

    def _calculate_attenuation(
        self, source_pos: Tuple[float, float, float],
        min_dist: float, max_dist: float,
    ) -> float:
        """Compute distance-based volume attenuation using inverse distance clamping."""
        lx, ly, lz = self._listener_position
        sx, sy, sz = source_pos
        distance = math.sqrt((lx - sx) ** 2 + (ly - sy) ** 2 + (lz - sz) ** 2)
        if distance <= min_dist:
            return 1.0
        if distance >= max_dist:
            return 0.0
        normalized = (distance - min_dist) / (max_dist - min_dist)
        return 1.0 / (1.0 + normalized * 4.0)

    def set_listener_position(self, x: float, y: float, z: float) -> None:
        with self._lock:
            self._listener_position = (x, y, z)

    # ------------------------------------------------------------------
    # Asset Management
    # ------------------------------------------------------------------

    def load_asset(
        self,
        name: str,
        category: AudioCategory,
        file_path: str,
        duration: float = 1.0,
        volume: float = 1.0,
        pitch: float = 1.0,
        priority: AudioPriority = AudioPriority.MEDIUM,
        playback_mode: PlaybackMode = PlaybackMode.ONCE,
        is_3d: bool = False,
        tags: Optional[List[str]] = None,
    ) -> AudioAsset:
        """Register a new audio asset in the system."""
        with self._lock:
            asset = AudioAsset(
                name=name, category=category, file_path=file_path,
                duration=max(0.01, duration),
                volume=max(0.0, min(1.0, volume)),
                pitch=max(0.1, min(3.0, pitch)),
                priority=priority, playback_mode=playback_mode,
                is_3d=is_3d, spatial_blend=1.0 if is_3d else 0.0,
                min_distance=5.0, max_distance=500.0, tags=tags or [],
            )
            self._assets[asset.asset_id] = asset
            return asset

    def get_asset(self, asset_id: str) -> Optional[AudioAsset]:
        with self._lock:
            return self._assets.get(asset_id)

    def list_assets_by_category(self, category: AudioCategory) -> List[AudioAsset]:
        with self._lock:
            return [a for a in self._assets.values() if a.category == category]

    def unload_asset(self, asset_id: str) -> bool:
        """Remove an audio asset. Fails if any active instance references it."""
        with self._lock:
            if asset_id not in self._assets:
                return False
            if any(i.asset_id == asset_id and i.state in _ACTIVE_STATES
                   for i in self._instances.values()):
                return False
            del self._assets[asset_id]
            return True

    # ------------------------------------------------------------------
    # Instance Playback
    # ------------------------------------------------------------------

    def _get_channel_for_category(
        self, category: AudioCategory
    ) -> Optional[AudioChannel]:
        for channel in self._channels.values():
            if channel.category == category:
                return channel
        return None

    def _count_active_in_category(self, category: AudioCategory) -> int:
        count = 0
        for inst in self._instances.values():
            if inst.state not in _ACTIVE_STATES:
                continue
            asset = self._assets.get(inst.asset_id)
            if asset and asset.category == category:
                count += 1
        return count

    def _count_total_active(self) -> int:
        return sum(1 for i in self._instances.values() if i.state in _ACTIVE_STATES)

    def _perform_voice_stealing(
        self, category: AudioCategory, required_priority: AudioPriority,
    ) -> Optional[AudioInstance]:
        """Evict the lowest-priority active instance in the same category.

        ALWAYS-priority instances are never evicted. Only instances with
        strictly lower priority than the required priority are candidates.
        """
        candidates: List[AudioInstance] = []
        for inst in self._instances.values():
            if inst.state not in (InstanceState.PLAYING, InstanceState.FADING_IN):
                continue
            asset = self._assets.get(inst.asset_id)
            if asset is None or asset.category != category:
                continue
            if asset.priority.value >= AudioPriority.ALWAYS.value:
                continue
            if asset.priority.value < required_priority.value:
                candidates.append(inst)
        if not candidates:
            return None
        candidates.sort(key=lambda i: self._assets.get(
            i.asset_id, AudioAsset()).priority.value)
        victim = candidates[0]
        victim.state = InstanceState.STOPPED
        return victim

    def play(
        self,
        asset_id: str,
        position: Optional[Tuple[float, float, float]] = None,
        volume: float = 1.0,
        pitch: float = 1.0,
        loop: bool = False,
    ) -> Optional[AudioInstance]:
        """Start playback of an audio asset.

        Handles 3D spatial positioning with distance-based attenuation,
        priority-based voice stealing when instance limits are reached,
        automatic channel routing, and a brief fade-in transition.
        """
        with self._lock:
            asset = self._assets.get(asset_id)
            if asset is None:
                return None

            volume = max(0.0, min(1.0, volume))
            pitch = max(0.1, min(3.0, pitch))
            pos = position or (0.0, 0.0, 0.0)

            # Total instance limit check with voice stealing
            if self._count_total_active() >= self._MAX_TOTAL_INSTANCES:
                self._perform_voice_stealing(asset.category, asset.priority)
                if self._count_total_active() >= self._MAX_TOTAL_INSTANCES:
                    return None

            # Per-category limit check with voice stealing
            if self._count_active_in_category(asset.category) >= self._MAX_INSTANCES_PER_CATEGORY:
                self._perform_voice_stealing(asset.category, asset.priority)
                if self._count_active_in_category(asset.category) >= self._MAX_INSTANCES_PER_CATEGORY:
                    return None

            channel = self._get_channel_for_category(asset.category)
            channel_id = channel.channel_id if channel else ""

            now = time.time()
            instance = AudioInstance(
                asset_id=asset_id, state=InstanceState.FADING_IN,
                position=pos, volume=volume, pitch=pitch,
                is_looping=loop, started_at=now,
                fade_in=0.05, fade_out=0.1, channel_id=channel_id, elapsed=0.0,
            )
            self._instances[instance.instance_id] = instance
            self._total_play_count += 1
            self._play_history.append({
                "asset_id": asset_id, "asset_name": asset.name,
                "category": asset.category.value, "timestamp": now,
            })
            return instance

    def stop(self, instance_id: str) -> Optional[AudioInstance]:
        """Stop playback with a brief fade-out transition."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance is None or instance.state == InstanceState.STOPPED:
                return instance
            instance.state = InstanceState.FADING_OUT
            instance.fade_out = 0.1
            instance.elapsed = 0.0
            self._total_stop_count += 1
            return instance

    def pause(self, instance_id: str) -> Optional[AudioInstance]:
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance and instance.state in (InstanceState.PLAYING, InstanceState.FADING_IN):
                instance.state = InstanceState.PAUSED
            return instance

    def resume(self, instance_id: str) -> Optional[AudioInstance]:
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance and instance.state == InstanceState.PAUSED:
                instance.state = InstanceState.FADING_IN
                instance.fade_in = 0.03
                instance.elapsed = 0.0
            return instance

    def set_volume(self, instance_id: str, volume: float) -> Optional[AudioInstance]:
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance:
                instance.volume = max(0.0, min(1.0, volume))
            return instance

    def set_position(
        self, instance_id: str, position: Tuple[float, float, float],
    ) -> Optional[AudioInstance]:
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance:
                instance.position = position
            return instance

    def get_active_instances(self) -> List[AudioInstance]:
        """Get all instances in PLAYING, FADING_IN, FADING_OUT, or PAUSED states."""
        with self._lock:
            return [i for i in self._instances.values() if i.state in _ACTIVE_STATES]

    # ------------------------------------------------------------------
    # Playback Convenience
    # ------------------------------------------------------------------

    def play_random_from_category(
        self,
        category: AudioCategory,
        position: Optional[Tuple[float, float, float]] = None,
        volume: float = 1.0,
    ) -> Optional[AudioInstance]:
        """Select a random asset from the given category and play it."""
        with self._lock:
            assets = self.list_assets_by_category(category)
            if not assets:
                return None
            asset = random.choice(assets)
            return self.play(
                asset_id=asset.asset_id, position=position, volume=volume,
                pitch=asset.pitch + random.uniform(-0.05, 0.05),
                loop=asset.playback_mode == PlaybackMode.LOOP,
            )

    # ------------------------------------------------------------------
    # Channel Management
    # ------------------------------------------------------------------

    def create_channel(
        self, name: str, category: AudioCategory, volume: float = 1.0,
    ) -> AudioChannel:
        """Create a new audio channel for category-based routing."""
        with self._lock:
            channel = AudioChannel(
                name=name, category=category,
                volume=max(0.0, min(1.0, volume)),
            )
            self._channels[channel.channel_id] = channel
            return channel

    def set_channel_volume(
        self, channel_id: str, volume: float
    ) -> Optional[AudioChannel]:
        with self._lock:
            channel = self._channels.get(channel_id)
            if channel:
                channel.volume = max(0.0, min(1.0, volume))
            return channel

    def mute_channel(self, channel_id: str) -> Optional[AudioChannel]:
        """Toggle mute state of an audio channel."""
        with self._lock:
            channel = self._channels.get(channel_id)
            if channel:
                channel.is_muted = not channel.is_muted
            return channel

    # ------------------------------------------------------------------
    # Mixer Management
    # ------------------------------------------------------------------

    def create_mixer(self, name: str, master_volume: float = 1.0) -> AudioMixer:
        """Create a new audio mixer including all currently registered channels."""
        with self._lock:
            mixer = AudioMixer(
                name=name, master_volume=max(0.0, min(1.0, master_volume)),
                channels=list(self._channels.keys()), effects=[], is_active=True,
            )
            self._mixers[mixer.mixer_id] = mixer
            return mixer

    def set_master_volume(
        self, mixer_id: str, volume: float
    ) -> Optional[AudioMixer]:
        with self._lock:
            mixer = self._mixers.get(mixer_id)
            if mixer:
                mixer.master_volume = max(0.0, min(1.0, volume))
            return mixer

    def add_mixer_effect(
        self, mixer_id: str, effect_name: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[AudioMixer]:
        """Add an audio effect to a mixer's effects chain (e.g. "reverb", "echo")."""
        with self._lock:
            mixer = self._mixers.get(mixer_id)
            if mixer is None:
                return None
            mixer.effects.append({
                "name": effect_name, "parameters": parameters or {},
                "added_at": time.time(),
            })
            return mixer

    # ------------------------------------------------------------------
    # Update Loop
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.016) -> None:
        """Advance the audio system by one frame.

        Processes fade-in/fade-out transitions, advances playback elapsed
        time, checks for completion on non-looping instances, and removes
        expired instances.
        """
        dt = max(0.0, delta_time)
        with self._lock:
            expired: List[str] = []
            for iid, instance in self._instances.items():
                if instance.state == InstanceState.FADING_IN:
                    instance.elapsed += dt
                    if instance.elapsed >= instance.fade_in:
                        instance.state = InstanceState.PLAYING
                        instance.elapsed = 0.0
                elif instance.state == InstanceState.FADING_OUT:
                    instance.elapsed += dt
                    if instance.elapsed >= instance.fade_out:
                        instance.state = InstanceState.STOPPED
                        expired.append(iid)
                elif instance.state == InstanceState.PLAYING:
                    asset = self._assets.get(instance.asset_id)
                    if asset is None:
                        instance.state = InstanceState.STOPPED
                        expired.append(iid)
                        continue
                    instance.elapsed += dt
                    if not instance.is_looping and instance.elapsed >= asset.duration:
                        instance.state = InstanceState.FADING_OUT
                        instance.elapsed = 0.0
                elif instance.state == InstanceState.PAUSED:
                    pass
            for iid in expired:
                del self._instances[iid]

    def get_effective_volume(self, instance_id: str) -> float:
        """Compute effective volume combining instance volume, spatial attenuation,
        channel volume, mute state, and fade transitions."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance is None or instance.state not in _ACTIVE_STATES:
                return 0.0

            effective = instance.volume
            if instance.state == InstanceState.FADING_IN:
                progress = min(1.0, instance.elapsed / max(instance.fade_in, 0.001))
                effective *= progress
            elif instance.state == InstanceState.FADING_OUT:
                progress = min(1.0, instance.elapsed / max(instance.fade_out, 0.001))
                effective *= (1.0 - progress)

            asset = self._assets.get(instance.asset_id)
            if asset and asset.is_3d:
                effective *= self._calculate_attenuation(
                    instance.position, asset.min_distance, asset.max_distance)

            channel = self._channels.get(instance.channel_id)
            if channel:
                if channel.is_muted:
                    return 0.0
                effective *= channel.volume

            return max(0.0, min(1.0, effective))

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the audio system."""
        with self._lock:
            active = self.get_active_instances()

            instances_by_state: Dict[str, int] = {}
            for state in InstanceState:
                count = sum(1 for i in self._instances.values() if i.state == state)
                if count > 0:
                    instances_by_state[state.value] = count

            instances_by_category: Dict[str, int] = {}
            for inst in active:
                asset = self._assets.get(inst.asset_id)
                if asset:
                    cat = asset.category.value
                    instances_by_category[cat] = instances_by_category.get(cat, 0) + 1

            assets_by_category: Dict[str, int] = {}
            for a in self._assets.values():
                cat = a.category.value
                assets_by_category[cat] = assets_by_category.get(cat, 0) + 1

            return {
                "total_assets": len(self._assets),
                "assets_by_category": assets_by_category,
                "total_instances": len(self._instances),
                "active_instances": len(active),
                "instances_by_state": instances_by_state,
                "instances_by_category": instances_by_category,
                "total_channels": len(self._channels),
                "total_mixers": len(self._mixers),
                "total_plays": self._total_play_count,
                "total_stops": self._total_stop_count,
                "max_instances_per_category": self._MAX_INSTANCES_PER_CATEGORY,
                "max_total_instances": self._MAX_TOTAL_INSTANCES,
                "listener_position": list(self._listener_position),
                "uptime_seconds": round(time.time() - self._creation_time, 1),
                "recent_plays": list(self._play_history)[-10:],
            }

    # ------------------------------------------------------------------
    # Backward Compatibility
    # ------------------------------------------------------------------

    def register_asset(
        self, name: str, category: str = "sfx", duration: float = 1.0,
        size_kb: float = 100.0, is_streaming: bool = False,
        is_looping: bool = False, priority: str = "MEDIUM",
    ) -> AudioAsset:
        """Legacy method: register an asset with string-based category and priority."""
        try:
            cat = AudioCategory(category.lower())
        except ValueError:
            cat = AudioCategory.SFX
        try:
            pri = AudioPriority[priority.upper()]
        except KeyError:
            pri = AudioPriority.MEDIUM
        return self.load_asset(
            name=name, category=cat, file_path="",
            duration=duration, volume=1.0, pitch=1.0,
            priority=pri, playback_mode=PlaybackMode.LOOP if is_looping else PlaybackMode.ONCE,
            is_3d=False, tags=[],
        )

    def get_mixer_state(self) -> Dict[str, Any]:
        """Legacy method: return mixer state summary."""
        return self.get_stats()


# ---------------------------------------------------------------------------
# Global Accessor
# ---------------------------------------------------------------------------

def get_audio_system() -> AudioSystemEngine:
    """Get the global AudioSystemEngine singleton instance."""
    return AudioSystemEngine.get_instance()


# Backward-compatible alias for modules importing the old class name.
GameAudioSystem = AudioSystemEngine