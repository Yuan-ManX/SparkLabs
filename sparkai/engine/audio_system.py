"""
SparkLabs Engine - Audio System

Centralized audio source management with 3D spatial positioning,
volume control, and playback state tracking. Designed for
AI-generated game sound effects and background music.

Architecture:
  AudioSystem
    |-- AudioSource (clip reference, position, volume, loop)
    |-- AudioChannel (group volume control: master/sfx/music/voice)
    |-- SpatialMixer (3D panning based on listener position)
    |-- PlaybackController (play/pause/stop/resume)

Channels:
  - master: Overall volume
  - sfx: Sound effects
  - music: Background music
  - voice: Dialogue/narration
  - ambient: Environmental sounds

Usage:
    audio = AudioSystem()
    source_id = audio.create_source("explosion",
        clip_name="boom.wav", channel="sfx", volume=0.8,
    )
    audio.set_listener_position(100, 200)
    audio.play("explosion")
    audio.set_master_volume(0.7)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class AudioChannel(Enum):
    MASTER = "master"
    SFX = "sfx"
    MUSIC = "music"
    VOICE = "voice"
    AMBIENT = "ambient"


@dataclass
class AudioSource:
    source_id: str = ""
    clip_name: str = ""
    channel: AudioChannel = AudioChannel.SFX
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    volume: float = 1.0
    pitch: float = 1.0
    pan: float = 0.5
    looping: bool = False
    spatial: bool = True
    spatial_blend: float = 1.0
    max_distance: float = 100.0
    min_distance: float = 1.0
    state: PlaybackState = PlaybackState.STOPPED
    playback_time: float = 0.0
    priority: int = 128
    metadata: Dict[str, Any] = field(default_factory=dict)


class AudioSystem:
    """
    Audio management system for game sound.

    Provides source-based audio with 3D spatial positioning,
    channel-based volume grouping, and listener awareness.
    Uses a virtual audio model — actual output delegated to
    platform-specific backends.

    Usage:
        audio = AudioSystem()
        
        # Create and play an explosion
        audio.create_source("expl_1", "explosion.wav", channel=AudioChannel.SFX)
        audio.play("expl_1")
        
        # Position-based 3D audio
        audio.set_listener_position(100, 200, 0)
        audio.set_source_position("ambient_river", 50, 180, 0)
        
        # Channel control
        audio.set_channel_volume(AudioChannel.MUSIC, 0.5)
        audio.mute_channel(AudioChannel.SFX, False)
    """

    def __init__(self, max_sources: int = 256):
        self._max_sources = max_sources
        self._sources: Dict[str, AudioSource] = {}
        self._channel_volumes: Dict[AudioChannel, float] = {
            ch: 1.0 for ch in AudioChannel
        }
        self._channel_muted: Dict[AudioChannel, bool] = {
            ch: False for ch in AudioChannel
        }
        self._listener_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._listener_forward: Tuple[float, float, float] = (0.0, 0.0, -1.0)
        self._listener_up: Tuple[float, float, float] = (0.0, 1.0, 0.0)
        self._clips_registry: Dict[str, Any] = {}
        self._play_count: int = 0
        self._stop_count: int = 0

    def create_source(
        self,
        source_id: str,
        clip_name: str = "",
        channel: AudioChannel = AudioChannel.SFX,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        volume: float = 1.0,
        looping: bool = False,
        spatial: bool = True,
        priority: int = 128,
        **kwargs,
    ) -> AudioSource:
        source = AudioSource(
            source_id=source_id,
            clip_name=clip_name,
            channel=channel,
            position=position,
            volume=volume,
            looping=looping,
            spatial=spatial,
            priority=priority,
            **kwargs,
        )
        self._sources[source_id] = source
        return source

    def get_source(self, source_id: str) -> Optional[AudioSource]:
        return self._sources.get(source_id)

    def remove_source(self, source_id: str) -> bool:
        source = self._sources.pop(source_id, None)
        if source:
            source.state = PlaybackState.STOPPED
            return True
        return False

    def play(self, source_id: str) -> bool:
        source = self._sources.get(source_id)
        if not source or self._channel_muted.get(source.channel, False):
            return False
        source.state = PlaybackState.PLAYING
        source.playback_time = 0.0
        self._play_count += 1
        return True

    def pause(self, source_id: str) -> bool:
        source = self._sources.get(source_id)
        if source and source.state == PlaybackState.PLAYING:
            source.state = PlaybackState.PAUSED
            return True
        return False

    def resume(self, source_id: str) -> bool:
        source = self._sources.get(source_id)
        if source and source.state == PlaybackState.PAUSED:
            source.state = PlaybackState.PLAYING
            return True
        return False

    def stop(self, source_id: str) -> bool:
        source = self._sources.get(source_id)
        if source and source.state != PlaybackState.STOPPED:
            source.state = PlaybackState.STOPPED
            source.playback_time = 0.0
            self._stop_count += 1
            return True
        return False

    def stop_all(self, channel: Optional[AudioChannel] = None) -> int:
        count = 0
        for source in self._sources.values():
            if channel is None or source.channel == channel:
                if source.state != PlaybackState.STOPPED:
                    source.state = PlaybackState.STOPPED
                    source.playback_time = 0.0
                    count += 1
        return count

    def set_source_position(
        self, source_id: str, x: float, y: float, z: float = 0.0,
    ) -> bool:
        source = self._sources.get(source_id)
        if source:
            source.position = (x, y, z)
            if source.spatial:
                source.pan = self._compute_pan(
                    source.position, self._listener_position,
                )
            return True
        return False

    def set_listener_position(self, x: float, y: float, z: float = 0.0) -> None:
        self._listener_position = (x, y, z)
        for source in self._sources.values():
            if source.spatial:
                source.pan = self._compute_pan(
                    source.position, self._listener_position,
                )

    def set_channel_volume(self, channel: AudioChannel, volume: float) -> None:
        self._channel_volumes[channel] = max(0.0, min(1.0, volume))

    def get_channel_volume(self, channel: AudioChannel) -> float:
        return self._channel_volumes.get(channel, 1.0)

    def mute_channel(self, channel: AudioChannel, muted: bool = True) -> None:
        self._channel_muted[channel] = muted
        if muted:
            for source in self._sources.values():
                if source.channel == channel:
                    source.state = PlaybackState.STOPPED

    def is_channel_muted(self, channel: AudioChannel) -> bool:
        return self._channel_muted.get(channel, False)

    def get_effective_volume(self, source: AudioSource) -> float:
        base = source.volume
        ch_vol = self._channel_volumes.get(source.channel, 1.0)
        master_vol = self._channel_volumes.get(AudioChannel.MASTER, 1.0)
        return base * ch_vol * master_vol

    @staticmethod
    def get_state_string(source_id: str) -> str:
        return source_id  # simplified

    def get_playing_count(self, channel: Optional[AudioChannel] = None) -> int:
        if channel:
            return sum(
                1 for s in self._sources.values()
                if s.state == PlaybackState.PLAYING and s.channel == channel
            )
        return sum(
            1 for s in self._sources.values()
            if s.state == PlaybackState.PLAYING
        )

    def get_stats(self) -> dict:
        return {
            "sources": len(self._sources),
            "playing": self.get_playing_count(),
            "paused": sum(
                1 for s in self._sources.values()
                if s.state == PlaybackState.PAUSED
            ),
            "play_count": self._play_count,
            "stop_count": self._stop_count,
            "channels_muted": {
                ch.value: muted
                for ch, muted in self._channel_muted.items()
            },
            "max_sources": self._max_sources,
        }

    def clear(self) -> None:
        for source in self._sources.values():
            source.state = PlaybackState.STOPPED
        self._sources.clear()
        self._play_count = 0
        self._stop_count = 0

    @staticmethod
    def _compute_pan(
        source_pos: Tuple[float, float, float],
        listener_pos: Tuple[float, float, float],
    ) -> float:
        dx = source_pos[0] - listener_pos[0]
        max_dist = 50.0
        pan = 0.5 + (dx / max_dist) * 0.5
        return max(0.0, min(1.0, pan))


_global_audio_system: Optional[AudioSystem] = None


def get_audio_system() -> AudioSystem:
    global _global_audio_system
    if _global_audio_system is None:
        _global_audio_system = AudioSystem()
    return _global_audio_system
