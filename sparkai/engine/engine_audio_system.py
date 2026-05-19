"""
SparkLabs Engine - Audio System

Runtime audio engine providing sound effect playback, music streaming,
spatial audio positioning, and dynamic mixing. Manages audio assets
through a priority-based pool and supports real-time parameter modulation.

Architecture:
  AudioSystem
    |-- SoundPool (preloaded sound effect buffer management)
    |-- MusicStreamer (background music playback and crossfading)
    |-- Spatializer (3D positional audio based on listener location)
    |-- Mixer (volume groups, ducking, and effect chains)
    |-- AssetCache (priority-based audio asset loading and eviction)

Audio Features:
  - SFX: one-shot and looping sound effects with pitch/volume variation
  - MUSIC: playlist streaming with smooth crossfade transitions
  - SPATIAL: distance-based attenuation and stereo panning
  - MIXING: master, music, sfx, voice, and ambient volume channels
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AudioChannel(Enum):
    MASTER = "master"
    MUSIC = "music"
    SFX = "sfx"
    VOICE = "voice"
    AMBIENT = "ambient"
    UI = "ui"


class PlaybackState(Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPING = "stopping"
    CROSSFADING = "crossfading"


class SpatialModel(Enum):
    NONE = "none"
    LINEAR = "linear"
    INVERSE = "inverse"
    EXPONENTIAL = "exponential"


class AudioPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class AudioAsset:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: AudioChannel = AudioChannel.SFX
    duration_seconds: float = 1.0
    size_kb: float = 100.0
    is_streaming: bool = False
    is_looping: bool = False
    priority: AudioPriority = AudioPriority.MEDIUM
    loaded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "duration_seconds": self.duration_seconds,
            "size_kb": self.size_kb,
            "is_streaming": self.is_streaming,
            "is_looping": self.is_looping,
            "priority": self.priority.name,
            "loaded": self.loaded,
        }


@dataclass
class SoundInstance:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    asset_id: str = ""
    volume: float = 1.0
    pitch: float = 1.0
    pan: float = 0.0
    spatial_position: Optional[Tuple[float, float, float]] = None
    spatial_model: SpatialModel = SpatialModel.NONE
    min_distance: float = 10.0
    max_distance: float = 500.0
    state: PlaybackState = PlaybackState.IDLE
    elapsed: float = 0.0
    channel: AudioChannel = AudioChannel.SFX

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "volume": round(self.volume, 2),
            "pitch": round(self.pitch, 2),
            "pan": round(self.pan, 2),
            "spatial_position": (list(self.spatial_position)
                                  if self.spatial_position else None),
            "spatial_model": self.spatial_model.value,
            "min_distance": self.min_distance,
            "max_distance": self.max_distance,
            "state": self.state.value,
            "elapsed": round(self.elapsed, 3),
            "channel": self.channel.value,
        }


@dataclass
class MixerChannel:
    name: AudioChannel = AudioChannel.MASTER
    volume: float = 1.0
    is_muted: bool = False
    active_instances: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name.value,
            "volume": round(self.volume, 2),
            "is_muted": self.is_muted,
            "active_instances": self.active_instances,
        }


@dataclass
class MusicTrack:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    duration_seconds: float = 120.0
    bpm: float = 120.0
    loop_start: float = 0.0
    loop_end: float = 0.0
    state: PlaybackState = PlaybackState.IDLE
    volume: float = 0.7
    position: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "duration_seconds": self.duration_seconds,
            "bpm": self.bpm,
            "loop_start": self.loop_start,
            "loop_end": self.loop_end,
            "state": self.state.value,
            "volume": self.volume,
            "position": self.position,
        }


class GameAudioSystem:
    """Runtime audio engine for game sound and music."""

    _instance: Optional["GameAudioSystem"] = None
    _lock = threading.RLock()

    _DEFAULT_MUSIC_TRACKS = [
        {"name": "Menu Theme", "duration": 180.0, "bpm": 100.0},
        {"name": "Gameplay Loop", "duration": 240.0, "bpm": 140.0},
        {"name": "Boss Battle", "duration": 200.0, "bpm": 170.0},
        {"name": "Ambient Exploration", "duration": 300.0, "bpm": 60.0},
        {"name": "Victory Fanfare", "duration": 30.0, "bpm": 120.0},
    ]

    def __init__(self) -> None:
        self._assets: Dict[str, AudioAsset] = {}
        self._instances: Dict[str, SoundInstance] = {}
        self._mixer: Dict[AudioChannel, MixerChannel] = {
            ch: MixerChannel(name=ch) for ch in AudioChannel
        }
        self._music_tracks: Dict[str, MusicTrack] = {}
        self._current_track: Optional[MusicTrack] = None
        self._next_track: Optional[MusicTrack] = None
        self._crossfade_progress: float = 0.0
        self._crossfade_duration: float = 2.0
        self._listener_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._total_memory_kb: float = 0.0
        self._max_memory_kb: float = 256 * 1024
        self._master_volume: float = 1.0

    @classmethod
    def get_instance(cls) -> "GameAudioSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Asset Management ----

    def register_asset(self,
                       name: str,
                       category: str = "sfx",
                       duration: float = 1.0,
                       size_kb: float = 100.0,
                       is_streaming: bool = False,
                       is_looping: bool = False,
                       priority: str = "MEDIUM") -> AudioAsset:
        try:
            ch = AudioChannel(category.lower())
        except ValueError:
            ch = AudioChannel.SFX
        try:
            pri = AudioPriority[priority.upper()]
        except KeyError:
            pri = AudioPriority.MEDIUM
        asset = AudioAsset(
            name=name,
            category=ch,
            duration_seconds=duration,
            size_kb=size_kb,
            is_streaming=is_streaming,
            is_looping=is_looping,
            priority=pri,
            loaded=True,
        )
        self._assets[asset.id] = asset
        self._total_memory_kb += size_kb
        return asset

    def get_asset(self, asset_id: str) -> Optional[AudioAsset]:
        return self._assets.get(asset_id)

    def list_assets(self,
                    category: Optional[str] = None) -> List[AudioAsset]:
        assets = list(self._assets.values())
        if category:
            try:
                ch = AudioChannel(category.lower())
                return [a for a in assets if a.category == ch]
            except ValueError:
                return []
        return assets

    def unload_asset(self, asset_id: str) -> bool:
        asset = self._assets.get(asset_id)
        if asset is None:
            return False
        if any(i.asset_id == asset_id and i.state == PlaybackState.PLAYING
               for i in self._instances.values()):
            return False
        self._total_memory_kb -= asset.size_kb
        del self._assets[asset_id]
        return True

    # ---- Sound Playback ----

    def play_sfx(self,
                 asset_id: str,
                 volume: float = 1.0,
                 pitch: float = 1.0,
                 pan: float = 0.0,
                 position: Optional[Tuple[float, float, float]] = None,
                 spatial: str = "none",
                 min_dist: float = 10.0,
                 max_dist: float = 500.0) -> Optional[SoundInstance]:
        asset = self._assets.get(asset_id)
        if asset is None:
            return None
        try:
            model = SpatialModel(spatial.lower())
        except ValueError:
            model = SpatialModel.NONE
        instance = SoundInstance(
            asset_id=asset_id,
            volume=max(0.0, min(1.0, volume)),
            pitch=max(0.1, min(3.0, pitch)),
            pan=max(-1.0, min(1.0, pan)),
            spatial_position=position,
            spatial_model=model,
            min_distance=min_dist,
            max_distance=max_dist,
            state=PlaybackState.PLAYING,
            channel=asset.category,
        )
        self._instances[instance.id] = instance
        ch = self._mixer.get(asset.category)
        if ch:
            ch.active_instances += 1
        return instance

    def stop_instance(self, instance_id: str) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.state = PlaybackState.IDLE
        ch = self._mixer.get(instance.channel)
        if ch:
            ch.active_instances = max(0, ch.active_instances - 1)
        return True

    def get_sound_instance(self, instance_id: str) -> Optional[SoundInstance]:
        return self._instances.get(instance_id)

    def list_active_instances(self) -> List[SoundInstance]:
        return [i for i in self._instances.values()
                if i.state == PlaybackState.PLAYING]

    # ---- Spatial Audio ----

    def set_listener_position(self,
                              x: float,
                              y: float,
                              z: float) -> None:
        self._listener_position = (x, y, z)

    def get_listener_position(self) -> Tuple[float, float, float]:
        return self._listener_position

    @staticmethod
    def calculate_spatial_volume(
            listener: Tuple[float, float, float],
            source: Tuple[float, float, float],
            model: SpatialModel,
            min_dist: float,
            max_dist: float) -> float:
        dx = listener[0] - source[0]
        dy = listener[1] - source[1]
        dz = listener[2] - source[2]
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        if distance <= min_dist:
            return 1.0
        if distance >= max_dist:
            return 0.0
        normalized = (distance - min_dist) / (max_dist - min_dist)
        if model == SpatialModel.LINEAR:
            return 1.0 - normalized
        elif model == SpatialModel.INVERSE:
            return 1.0 / (1.0 + normalized * 4.0)
        elif model == SpatialModel.EXPONENTIAL:
            return math.exp(-normalized * 3.0)
        return 1.0

    # ---- Music System ----

    def register_music_track(self,
                              name: str,
                              duration: float = 120.0,
                              bpm: float = 120.0,
                              loop_start: float = 0.0,
                              loop_end: float = 0.0) -> MusicTrack:
        track = MusicTrack(
            name=name,
            duration_seconds=duration,
            bpm=bpm,
            loop_start=loop_start,
            loop_end=loop_end or duration,
        )
        self._music_tracks[track.id] = track
        return track

    def seed_default_tracks(self) -> List[MusicTrack]:
        tracks = []
        for t in self._DEFAULT_MUSIC_TRACKS:
            track = self.register_music_track(**t)
            tracks.append(track)
        return tracks

    def play_music(self,
                   track_id: str,
                   volume: float = 0.7,
                   crossfade: float = 2.0) -> Optional[MusicTrack]:
        track = self._music_tracks.get(track_id)
        if track is None:
            return None

        if self._current_track is not None and crossfade > 0:
            self._next_track = track
            self._next_track.volume = volume
            self._next_track.state = PlaybackState.CROSSFADING
            self._current_track.state = PlaybackState.CROSSFADING
            self._crossfade_progress = 0.0
            self._crossfade_duration = crossfade
        else:
            if self._current_track is not None:
                self._current_track.state = PlaybackState.IDLE
            self._current_track = track
            self._current_track.volume = volume
            self._current_track.state = PlaybackState.PLAYING

        return track

    def stop_music(self, fade_out: float = 1.0) -> None:
        if self._current_track is not None:
            self._current_track.state = PlaybackState.STOPPING
        self._next_track = None

    def update_music(self, delta_time: float) -> None:
        if self._current_track is None:
            return

        if self._current_track.state == PlaybackState.PLAYING:
            self._current_track.position += delta_time
            loop_end = self._current_track.loop_end or self._current_track.duration_seconds
            if self._current_track.position >= loop_end:
                if self._current_track.loop_start > 0 or self._current_track.loop_end > 0:
                    self._current_track.position = self._current_track.loop_start
                else:
                    self._current_track.state = PlaybackState.IDLE

        elif self._current_track.state == PlaybackState.CROSSFADING and self._next_track is not None:
            self._crossfade_progress += delta_time
            t = min(1.0, self._crossfade_progress / self._crossfade_duration)
            self._current_track.volume = max(0.0, self._current_track.volume * (1.0 - t))
            self._next_track.volume = min(self._next_track.volume, t)
            if self._crossfade_progress >= self._crossfade_duration:
                self._current_track.state = PlaybackState.IDLE
                self._current_track = self._next_track
                self._current_track.state = PlaybackState.PLAYING
                self._next_track = None
                self._crossfade_progress = 0.0

    def get_music_track(self, track_id: str) -> Optional[MusicTrack]:
        return self._music_tracks.get(track_id)

    def list_music_tracks(self) -> List[MusicTrack]:
        return list(self._music_tracks.values())

    # ---- Mixer ----

    def set_channel_volume(self,
                           channel: str,
                           volume: float) -> bool:
        try:
            ch = AudioChannel(channel.lower())
        except ValueError:
            return False
        mixer_ch = self._mixer.get(ch)
        if mixer_ch is None:
            return False
        mixer_ch.volume = max(0.0, min(1.0, volume))
        return True

    def mute_channel(self, channel: str) -> bool:
        try:
            ch = AudioChannel(channel.lower())
        except ValueError:
            return False
        mixer_ch = self._mixer.get(ch)
        if mixer_ch is None:
            return False
        mixer_ch.is_muted = not mixer_ch.is_muted
        return True

    def get_mixer_state(self) -> Dict[str, Any]:
        channels = [c.to_dict() for c in self._mixer.values()]
        return {
            "master_volume": self._master_volume,
            "channels": channels,
            "active_instances": len(self.list_active_instances()),
            "current_track": self._current_track.name if self._current_track else None,
        }

    # ---- Update Loop ----

    def tick(self, delta_time: float = 0.016) -> None:
        self.update_music(delta_time)

        expired: List[str] = []
        for iid, instance in self._instances.items():
            if instance.state != PlaybackState.PLAYING:
                continue
            instance.elapsed += delta_time
            if instance.spatial_model != SpatialModel.NONE and instance.spatial_position:
                spatial_vol = self.calculate_spatial_volume(
                    self._listener_position,
                    instance.spatial_position,
                    instance.spatial_model,
                    instance.min_distance,
                    instance.max_distance,
                )
                effective_vol = instance.volume * spatial_vol
            else:
                effective_vol = instance.volume

            ch = self._mixer.get(instance.channel)
            if ch and (ch.is_muted or ch.volume <= 0.01):
                effective_vol = 0.0

            asset = self._assets.get(instance.asset_id)
            if asset and instance.elapsed >= asset.duration_seconds:
                instance.state = PlaybackState.IDLE
                expired.append(iid)
                if ch:
                    ch.active_instances = max(0, ch.active_instances - 1)

        for iid in expired:
            del self._instances[iid]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_assets": len(self._assets),
            "loaded_memory_kb": round(self._total_memory_kb, 1),
            "max_memory_kb": self._max_memory_kb,
            "memory_usage_pct": round(self._total_memory_kb / self._max_memory_kb * 100, 1)
                if self._max_memory_kb > 0 else 0,
            "active_instances": sum(
                1 for i in self._instances.values()
                if i.state == PlaybackState.PLAYING
            ),
            "total_instances": len(self._instances),
            "music_tracks": len(self._music_tracks),
            "current_track": self._current_track.name if self._current_track else None,
            "default_presets": len(self._DEFAULT_MUSIC_TRACKS),
        }


def get_audio_system() -> GameAudioSystem:
    return GameAudioSystem.get_instance()