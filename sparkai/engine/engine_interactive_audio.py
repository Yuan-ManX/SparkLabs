"""
SparkLabs Engine - Interactive Audio Engine

Layered music and sound system where audio stems, playlists, and
synchronized transitions respond to game state changes. Supports
dynamic layering, cross-fading, and state-driven transitions for
adaptive audio experiences.

Architecture:
  InteractiveAudio
    |-- AudioStem (individual audio layer with intensity range and musical properties)
    |-- AudioPlaylist (ordered collection of stems with shuffle and crossfade support)
    |-- AudioTransition (configured transition between stems triggered by state)
    |-- AudioStateMap (mapping from game state keys to playlist/transition behavior)
    |-- AudioConfig (global audio settings: volumes, spatial, doppler)

Audio Features:
  - LAYERING: multiple simultaneous stems organized by audio layer category
  - PLAYLISTS: sequential or shuffled stem playback with crossfade transitions
  - STATE_MAP: game state keys drive playlist selection and intensity changes
  - TRANSITIONS: crossfade, immediate, gate, beat-matched, bar-aligned transitions
  - MIXING: per-layer volume control with solo/mute capability
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AudioLayer(Enum):
    """Classification of an audio stem by its musical role in the mix."""
    MELODY = "melody"
    HARMONY = "harmony"
    BASS = "bass"
    PERCUSSION = "percussion"
    AMBIENT = "ambient"
    FX = "fx"
    VOICE = "voice"
    PAD = "pad"


class TransitionType(Enum):
    """Strategy for transitioning between audio stems in a playlist."""
    CROSSFADE = "crossfade"
    IMMEDIATE = "immediate"
    GATE = "gate"
    BEAT_MATCHED = "beat_matched"
    BAR_ALIGNED = "bar_aligned"
    FADE_OUT_IN = "fade_out_in"


class PlaybackState(Enum):
    """Current playback status of an audio playlist or stem."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    FADING_IN = "fading_in"
    FADING_OUT = "fading_out"
    TRANSITIONING = "transitioning"


class IntensityLevel(Enum):
    """Intensity tier for audio stems and state-driven music layering."""
    AMBIENT = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    PEAK = 4


class AudioCategory(Enum):
    """Broad category classification for audio content grouping."""
    MUSIC = "music"
    SFX = "sfx"
    DIALOGUE = "dialogue"
    AMBIENCE = "ambience"
    UI = "ui"


@dataclass
class AudioStem:
    """Individual audio layer with volume, pitch, looping, and intensity range."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    layer: AudioLayer = AudioLayer.AMBIENT
    audio_source: str = ""
    volume: float = 1.0
    pitch: float = 1.0
    loops: bool = True
    solo_mute: bool = False
    intensity_range: tuple = (0, 4)
    bpm: float = 120.0
    key: str = "C"
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "layer": self.layer.value,
            "audio_source": self.audio_source,
            "volume": round(self.volume, 3),
            "pitch": round(self.pitch, 2),
            "loops": self.loops,
            "solo_mute": self.solo_mute,
            "intensity_range": list(self.intensity_range),
            "bpm": self.bpm,
            "key": self.key,
            "created_at": self.created_at,
        }


@dataclass
class AudioPlaylist:
    """Ordered collection of stems with playback state and crossfade settings."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    stems: List[str] = field(default_factory=list)
    current_stem_index: int = 0
    shuffle: bool = False
    crossfade_duration: float = 2.0
    state: PlaybackState = PlaybackState.STOPPED
    category: AudioCategory = AudioCategory.MUSIC
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "stem_count": len(self.stems),
            "stems": list(self.stems),
            "current_stem_index": self.current_stem_index,
            "shuffle": self.shuffle,
            "crossfade_duration": round(self.crossfade_duration, 2),
            "state": self.state.value,
            "category": self.category.value,
            "created_at": self.created_at,
        }


@dataclass
class AudioTransition:
    """Configured transition between two stems triggered by a game state."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    playlist_id: str = ""
    from_stem_id: str = ""
    to_stem_id: str = ""
    transition_type: TransitionType = TransitionType.CROSSFADE
    duration_ms: float = 1000.0
    trigger_state: str = ""
    beat_offset: int = 0
    bar_count: int = 1
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "playlist_id": self.playlist_id,
            "from_stem_id": self.from_stem_id,
            "to_stem_id": self.to_stem_id,
            "transition_type": self.transition_type.value,
            "duration_ms": self.duration_ms,
            "trigger_state": self.trigger_state,
            "beat_offset": self.beat_offset,
            "bar_count": self.bar_count,
            "created_at": self.created_at,
        }


@dataclass
class AudioStateMap:
    """Mapping from a game state key to a playlist, with intensity and conditions."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    game_state_key: str = ""
    playlist_id: str = ""
    transition_id: str = ""
    intensity: IntensityLevel = IntensityLevel.MEDIUM
    priority: int = 0
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "game_state_key": self.game_state_key,
            "playlist_id": self.playlist_id,
            "transition_id": self.transition_id,
            "intensity": self.intensity.value,
            "priority": self.priority,
            "condition_count": len(self.conditions),
            "conditions": dict(self.conditions),
            "created_at": self.created_at,
        }


@dataclass
class AudioConfig:
    """Global audio configuration with master, channel volumes, and spatial settings."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    master_volume: float = 1.0
    music_volume: float = 0.8
    sfx_volume: float = 1.0
    dialogue_volume: float = 1.0
    ambience_volume: float = 0.7
    spatial_audio_enabled: bool = False
    doppler_enabled: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "master_volume": round(self.master_volume, 3),
            "music_volume": round(self.music_volume, 3),
            "sfx_volume": round(self.sfx_volume, 3),
            "dialogue_volume": round(self.dialogue_volume, 3),
            "ambience_volume": round(self.ambience_volume, 3),
            "spatial_audio_enabled": self.spatial_audio_enabled,
            "doppler_enabled": self.doppler_enabled,
            "created_at": self.created_at,
        }


class InteractiveAudio:
    """Layered music and sound system with state-driven transitions and dynamic mixing."""

    _instance: Optional["InteractiveAudio"] = None
    _lock = threading.RLock()

    _DEFAULT_CONFIGS = [
        {"name": "Default Mix", "master_volume": 1.0, "music_volume": 0.8,
         "sfx_volume": 1.0, "dialogue_volume": 1.0, "ambience_volume": 0.7},
        {"name": "Combat Mix", "master_volume": 1.0, "music_volume": 0.9,
         "sfx_volume": 1.0, "dialogue_volume": 0.6, "ambience_volume": 0.4},
        {"name": "Cinematic Mix", "master_volume": 1.0, "music_volume": 1.0,
         "sfx_volume": 0.5, "dialogue_volume": 0.9, "ambience_volume": 0.6},
        {"name": "Exploration Mix", "master_volume": 1.0, "music_volume": 0.6,
         "sfx_volume": 0.8, "dialogue_volume": 0.7, "ambience_volume": 1.0},
        {"name": "Menu Mix", "master_volume": 0.8, "music_volume": 0.7,
         "sfx_volume": 0.9, "dialogue_volume": 0.0, "ambience_volume": 0.3},
    ]

    def __init__(self) -> None:
        self._stems: Dict[str, AudioStem] = {}
        self._playlists: Dict[str, AudioPlaylist] = {}
        self._transitions: Dict[str, AudioTransition] = {}
        self._state_maps: Dict[str, AudioStateMap] = {}
        self._configs: Dict[str, AudioConfig] = {}
        self._active_config_id: Optional[str] = None
        self._game_state: Dict[str, Any] = {}
        self._layer_solos: Dict[str, Optional[AudioLayer]] = {}
        self._transition_progress: Dict[str, float] = {}
        self._fade_progress: Dict[str, float] = {}
        self._beat_accumulator: Dict[str, float] = {}
        self._active_state_map: Optional[str] = None
        self._tick_count: int = 0
        self._total_transitions_triggered: int = 0
        self._total_stems_created: int = 0
        self._total_playlists_created: int = 0

    @classmethod
    def get_instance(cls) -> "InteractiveAudio":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _current_time(self) -> float:
        return _time_module.time()

    def _volume_for_layer(self,
                           playlist_id: str,
                           layer: AudioLayer,
                           base_volume: float) -> float:
        config = self._get_active_config()
        solo_layer = self._layer_solos.get(playlist_id)
        if solo_layer is not None:
            if layer != solo_layer:
                return 0.0
        if config is None:
            return base_volume
        effective = base_volume * config.master_volume
        stem = None
        playlist = self._playlists.get(playlist_id)
        if playlist and playlist.current_stem_index < len(playlist.stems):
            current_stem_id = playlist.stems[playlist.current_stem_index]
            stem = self._stems.get(current_stem_id)
        if stem is not None:
            if stem.layer == AudioLayer.VOICE:
                effective *= config.dialogue_volume
            elif stem.layer in (AudioLayer.AMBIENT, AudioLayer.PAD):
                effective *= config.ambience_volume
            elif stem.layer in (AudioLayer.FX, AudioLayer.VOICE):
                effective *= config.sfx_volume
            else:
                effective *= config.music_volume
        return max(0.0, min(1.0, effective))

    def _get_active_config(self) -> Optional[AudioConfig]:
        if self._active_config_id is None:
            return None
        return self._configs.get(self._active_config_id)

    def _resolve_transition_timing(self,
                                    transition: AudioTransition,
                                    playlist: AudioPlaylist) -> float:
        effective_ms = transition.duration_ms
        if transition.transition_type == TransitionType.BEAT_MATCHED:
            stem = self._stems.get(transition.from_stem_id)
            if stem and stem.bpm > 0:
                beat_duration_ms = (60.0 / stem.bpm) * 1000.0
                effective_ms = beat_duration_ms * max(1, transition.beat_offset)
        elif transition.transition_type == TransitionType.BAR_ALIGNED:
            stem = self._stems.get(transition.from_stem_id)
            if stem and stem.bpm > 0:
                bar_duration_ms = (60.0 / stem.bpm) * 4.0 * 1000.0
                effective_ms = bar_duration_ms * max(1, transition.bar_count)
        return max(50.0, effective_ms)

    def _advance_playlist_stem(self, playlist: AudioPlaylist) -> Optional[str]:
        if not playlist.stems:
            return None
        if playlist.shuffle:
            import random
            available = [s for i, s in enumerate(playlist.stems) if i != playlist.current_stem_index]
            if available:
                new_index = playlist.stems.index(random.choice(available))
            else:
                new_index = 0
        else:
            new_index = (playlist.current_stem_index + 1) % len(playlist.stems)
        playlist.current_stem_index = new_index
        return playlist.stems[new_index] if playlist.stems else None

    def _evaluate_state_maps(self) -> None:
        candidates: List[tuple] = []
        for state_map in self._state_maps.values():
            if self._check_conditions(state_map.conditions):
                candidates.append((state_map.priority, state_map))
        if not candidates:
            return
        candidates.sort(key=lambda x: x[0], reverse=True)
        best = candidates[0][1]
        if best.id != self._active_state_map:
            self._active_state_map = best.id
            playlist = self._playlists.get(best.playlist_id)
            if playlist is not None and playlist.state == PlaybackState.STOPPED:
                self.start_playlist(best.playlist_id)
            if best.transition_id:
                self.trigger_transition(best.playlist_id, best.transition_id)

    def _check_conditions(self, conditions: Dict[str, Any]) -> bool:
        if not conditions:
            return True
        for key, expected in conditions.items():
            current = self._game_state.get(key)
            if current != expected:
                return False
        return True

    def _handle_transition_tick(self,
                                 playlist_id: str,
                                 transition_id: str,
                                 delta_time: float) -> None:
        if playlist_id not in self._transition_progress:
            self._transition_progress[playlist_id] = 0.0

        transition = self._transitions.get(transition_id)
        if transition is None:
            return

        playlist = self._playlists.get(playlist_id)
        if playlist is None:
            return

        effective_ms = self._resolve_transition_timing(transition, playlist)
        progress_delta = (delta_time * 1000.0) / max(0.001, effective_ms)
        self._transition_progress[playlist_id] += progress_delta

        t = min(1.0, self._transition_progress[playlist_id])

        if transition.transition_type in (TransitionType.CROSSFADE,
                                           TransitionType.FADE_OUT_IN):
            from_stem = self._stems.get(transition.from_stem_id)
            to_stem = self._stems.get(transition.to_stem_id)

            if transition.transition_type == TransitionType.CROSSFADE:
                if from_stem is not None:
                    from_stem.volume = max(0.0, from_stem.volume * (1.0 - t))
                if to_stem is not None:
                    to_stem.volume = min(1.0, to_stem.volume + t * 0.5)
            elif transition.transition_type == TransitionType.FADE_OUT_IN:
                half_point = 0.5
                if t < half_point:
                    if from_stem is not None:
                        from_stem.volume = max(0.0, from_stem.volume * (1.0 - t / half_point))
                else:
                    if from_stem is not None:
                        from_stem.volume = 0.0
                    if to_stem is not None:
                        local_t = (t - half_point) / half_point
                        to_stem.volume = min(1.0, to_stem.volume + local_t * 0.5)

        elif transition.transition_type == TransitionType.GATE:
            if t >= 0.5:
                from_stem = self._stems.get(transition.from_stem_id)
                to_stem = self._stems.get(transition.to_stem_id)
                if from_stem is not None:
                    from_stem.volume = 0.0
                if to_stem is not None:
                    to_stem.volume = min(1.0, to_stem.volume + 0.3)

        if t >= 1.0:
            self._complete_transition(playlist_id, transition)

    def _complete_transition(self,
                              playlist_id: str,
                              transition: AudioTransition) -> None:
        playlist = self._playlists.get(playlist_id)
        if playlist is None:
            return

        target_stem = self._stems.get(transition.to_stem_id)
        if target_stem is not None:
            for i, sid in enumerate(playlist.stems):
                if sid == transition.to_stem_id:
                    playlist.current_stem_index = i
                    break

        playlist.state = PlaybackState.PLAYING
        self._transition_progress.pop(playlist_id, None)

    # ---- Stem Management ----

    def create_stem(self,
                    name: str,
                    layer: str,
                    audio_source: str,
                    volume: float = 1.0,
                    bpm: float = 120.0,
                    key: str = "C") -> AudioStem:
        try:
            layer_enum = AudioLayer(layer.lower())
        except ValueError:
            layer_enum = AudioLayer.AMBIENT

        stem = AudioStem(
            name=name,
            layer=layer_enum,
            audio_source=audio_source,
            volume=max(0.0, min(1.0, volume)),
            bpm=max(1.0, bpm),
            key=key,
        )
        self._stems[stem.id] = stem
        self._total_stems_created += 1
        return stem

    def get_stem(self, stem_id: str) -> Optional[AudioStem]:
        return self._stems.get(stem_id)

    def list_stems(self,
                   layer: Optional[str] = None) -> List[AudioStem]:
        stems = list(self._stems.values())
        if layer:
            try:
                layer_enum = AudioLayer(layer.lower())
                return [s for s in stems if s.layer == layer_enum]
            except ValueError:
                return []
        return stems

    def remove_stem(self, stem_id: str) -> bool:
        if stem_id not in self._stems:
            return False
        del self._stems[stem_id]
        for playlist in self._playlists.values():
            if stem_id in playlist.stems:
                playlist.stems.remove(stem_id)
        transitions_to_remove = [
            tid for tid, t in self._transitions.items()
            if t.from_stem_id == stem_id or t.to_stem_id == stem_id
        ]
        for tid in transitions_to_remove:
            del self._transitions[tid]
        return True

    # ---- Playlist Management ----

    def create_playlist(self,
                        name: str,
                        stems: List[str],
                        category: str = "music",
                        crossfade_duration: float = 2.0) -> AudioPlaylist:
        try:
            cat_enum = AudioCategory(category.lower())
        except ValueError:
            cat_enum = AudioCategory.MUSIC

        valid_stems = [s for s in stems if s in self._stems]
        playlist = AudioPlaylist(
            name=name,
            stems=valid_stems,
            crossfade_duration=max(0.01, crossfade_duration),
            category=cat_enum,
        )
        self._playlists[playlist.id] = playlist
        self._total_playlists_created += 1
        return playlist

    def get_playlist(self, playlist_id: str) -> Optional[AudioPlaylist]:
        return self._playlists.get(playlist_id)

    def list_playlists(self,
                       category: Optional[str] = None) -> List[AudioPlaylist]:
        playlists = list(self._playlists.values())
        if category:
            try:
                cat_enum = AudioCategory(category.lower())
                return [p for p in playlists if p.category == cat_enum]
            except ValueError:
                return []
        return playlists

    def remove_playlist(self, playlist_id: str) -> bool:
        if playlist_id not in self._playlists:
            return False
        del self._playlists[playlist_id]
        self._layer_solos.pop(playlist_id, None)
        self._transition_progress.pop(playlist_id, None)
        transitions_to_remove = [
            tid for tid, t in self._transitions.items()
            if t.playlist_id == playlist_id
        ]
        for tid in transitions_to_remove:
            del self._transitions[tid]
        return True

    def add_stem_to_playlist(self,
                              playlist_id: str,
                              stem_id: str) -> bool:
        playlist = self._playlists.get(playlist_id)
        if playlist is None or stem_id not in self._stems:
            return False
        if stem_id not in playlist.stems:
            playlist.stems.append(stem_id)
        return True

    def remove_stem_from_playlist(self,
                                   playlist_id: str,
                                   stem_id: str) -> bool:
        playlist = self._playlists.get(playlist_id)
        if playlist is None or stem_id not in playlist.stems:
            return False
        playlist.stems.remove(stem_id)
        return True

    # ---- Transition Management ----

    def add_transition(self,
                       playlist_id: str,
                       from_stem_id: str,
                       to_stem_id: str,
                       transition_type: str = "crossfade",
                       duration_ms: float = 1000.0,
                       trigger_state: str = "") -> AudioTransition:
        try:
            tt_enum = TransitionType(transition_type.lower())
        except ValueError:
            tt_enum = TransitionType.CROSSFADE

        transition = AudioTransition(
            playlist_id=playlist_id,
            from_stem_id=from_stem_id,
            to_stem_id=to_stem_id,
            transition_type=tt_enum,
            duration_ms=max(50.0, duration_ms),
            trigger_state=trigger_state,
        )
        self._transitions[transition.id] = transition
        return transition

    def get_transition(self, transition_id: str) -> Optional[AudioTransition]:
        return self._transitions.get(transition_id)

    def list_transitions(self,
                         playlist_id: Optional[str] = None) -> List[AudioTransition]:
        transitions = list(self._transitions.values())
        if playlist_id:
            return [t for t in transitions if t.playlist_id == playlist_id]
        return transitions

    def remove_transition(self, transition_id: str) -> bool:
        if transition_id not in self._transitions:
            return False
        del self._transitions[transition_id]
        return True

    # ---- State Map Management ----

    def create_state_map(self,
                         name: str,
                         game_state_key: str,
                         playlist_id: str,
                         intensity: str = "MEDIUM") -> AudioStateMap:
        try:
            int_enum = IntensityLevel[intensity.upper()]
        except KeyError:
            int_enum = IntensityLevel.MEDIUM

        state_map = AudioStateMap(
            name=name,
            game_state_key=game_state_key,
            playlist_id=playlist_id,
            intensity=int_enum,
        )
        self._state_maps[state_map.id] = state_map
        return state_map

    def get_state_map(self, state_map_id: str) -> Optional[AudioStateMap]:
        return self._state_maps.get(state_map_id)

    def list_state_maps(self) -> List[AudioStateMap]:
        return list(self._state_maps.values())

    def set_state_map_conditions(self,
                                  state_map_id: str,
                                  conditions: Dict[str, Any]) -> bool:
        state_map = self._state_maps.get(state_map_id)
        if state_map is None:
            return False
        state_map.conditions = dict(conditions)
        return True

    # ---- Config Management ----

    def create_config(self,
                      name: str,
                      master_volume: float = 1.0,
                      music_volume: float = 0.8,
                      sfx_volume: float = 1.0,
                      dialogue_volume: float = 1.0,
                      ambience_volume: float = 0.7,
                      spatial_audio_enabled: bool = False,
                      doppler_enabled: bool = False) -> AudioConfig:
        config = AudioConfig(
            name=name,
            master_volume=max(0.0, min(1.0, master_volume)),
            music_volume=max(0.0, min(1.0, music_volume)),
            sfx_volume=max(0.0, min(1.0, sfx_volume)),
            dialogue_volume=max(0.0, min(1.0, dialogue_volume)),
            ambience_volume=max(0.0, min(1.0, ambience_volume)),
            spatial_audio_enabled=spatial_audio_enabled,
            doppler_enabled=doppler_enabled,
        )
        self._configs[config.id] = config
        return config

    def seed_default_configs(self) -> List[AudioConfig]:
        configs = []
        for c in self._DEFAULT_CONFIGS:
            config = self.create_config(**c)
            configs.append(config)
        return configs

    def apply_config(self, config_id: str) -> bool:
        if config_id not in self._configs:
            return False
        self._active_config_id = config_id
        return True

    def get_config(self, config_id: str) -> Optional[AudioConfig]:
        return self._configs.get(config_id)

    def list_configs(self) -> List[AudioConfig]:
        return list(self._configs.values())

    # ---- Playback Control ----

    def start_playlist(self,
                       playlist_id: str,
                       start_stem_id: Optional[str] = None) -> bool:
        playlist = self._playlists.get(playlist_id)
        if playlist is None or not playlist.stems:
            return False

        if start_stem_id and start_stem_id in playlist.stems:
            playlist.current_stem_index = playlist.stems.index(start_stem_id)
        else:
            playlist.current_stem_index = 0

        current_stem_id = playlist.stems[playlist.current_stem_index]
        stem = self._stems.get(current_stem_id)
        if stem is not None:
            stem.volume = max(0.01, stem.volume)

        playlist.state = PlaybackState.PLAYING
        return True

    def stop_playlist(self,
                      playlist_id: str,
                      fade_out_ms: float = 500.0) -> bool:
        playlist = self._playlists.get(playlist_id)
        if playlist is None:
            return False

        if fade_out_ms > 0 and playlist.state == PlaybackState.PLAYING:
            playlist.state = PlaybackState.FADING_OUT
            self._fade_progress[playlist_id] = 0.0
            return True

        playlist.state = PlaybackState.STOPPED
        self._fade_progress.pop(playlist_id, None)
        return True

    def pause_playlist(self, playlist_id: str) -> bool:
        playlist = self._playlists.get(playlist_id)
        if playlist is None or playlist.state != PlaybackState.PLAYING:
            return False
        playlist.state = PlaybackState.PAUSED
        return True

    def resume_playlist(self, playlist_id: str) -> bool:
        playlist = self._playlists.get(playlist_id)
        if playlist is None or playlist.state != PlaybackState.PAUSED:
            return False
        playlist.state = PlaybackState.PLAYING
        return True

    # ---- Transitions ----

    def trigger_transition(self,
                           playlist_id: str,
                           transition_id: str) -> bool:
        playlist = self._playlists.get(playlist_id)
        transition = self._transitions.get(transition_id)
        if playlist is None or transition is None:
            return False
        if transition.playlist_id != playlist_id:
            return False

        playlist.state = PlaybackState.TRANSITIONING
        self._transition_progress[playlist_id] = 0.0
        self._total_transitions_triggered += 1
        return True

    def crossfade_to_stem(self,
                           playlist_id: str,
                           target_stem_id: str,
                           duration_ms: float = 1000.0) -> bool:
        playlist = self._playlists.get(playlist_id)
        if playlist is None:
            return False
        if target_stem_id not in playlist.stems:
            return False
        if not playlist.stems:
            return False

        current_stem_id = playlist.stems[playlist.current_stem_index]
        transition = self.add_transition(
            playlist_id=playlist_id,
            from_stem_id=current_stem_id,
            to_stem_id=target_stem_id,
            transition_type="crossfade",
            duration_ms=duration_ms,
        )
        return self.trigger_transition(playlist_id, transition.id)

    # ---- Game State Integration ----

    def update_game_state(self,
                           state_key: str,
                           new_value: Any) -> None:
        self._game_state[state_key] = new_value
        self._evaluate_state_maps()

    def get_game_state(self,
                        state_key: str) -> Optional[Any]:
        return self._game_state.get(state_key)

    def remove_game_state(self, state_key: str) -> None:
        self._game_state.pop(state_key, None)

    # ---- Layer Control ----

    def set_layer_volume(self,
                          playlist_id: str,
                          layer: str,
                          volume: float) -> bool:
        try:
            layer_enum = AudioLayer(layer.lower())
        except ValueError:
            return False
        playlist = self._playlists.get(playlist_id)
        if playlist is None:
            return False
        for stem_id in playlist.stems:
            stem = self._stems.get(stem_id)
            if stem is not None and stem.layer == layer_enum:
                stem.volume = max(0.0, min(1.0, volume))
        return True

    def solo_layer(self,
                    playlist_id: str,
                    layer: str) -> bool:
        try:
            layer_enum = AudioLayer(layer.lower())
        except ValueError:
            return False
        if playlist_id not in self._playlists:
            return False
        self._layer_solos[playlist_id] = layer_enum
        return True

    def unsolo_layer(self, playlist_id: str) -> bool:
        if playlist_id not in self._layer_solos:
            return False
        del self._layer_solos[playlist_id]
        return True

    def mute_layer(self,
                    playlist_id: str,
                    layer: str) -> bool:
        try:
            layer_enum = AudioLayer(layer.lower())
        except ValueError:
            return False
        playlist = self._playlists.get(playlist_id)
        if playlist is None:
            return False
        for stem_id in playlist.stems:
            stem = self._stems.get(stem_id)
            if stem is not None and stem.layer == layer_enum:
                stem.solo_mute = True
        return True

    def unmute_layer(self,
                      playlist_id: str,
                      layer: str) -> bool:
        try:
            layer_enum = AudioLayer(layer.lower())
        except ValueError:
            return False
        playlist = self._playlists.get(playlist_id)
        if playlist is None:
            return False
        for stem_id in playlist.stems:
            stem = self._stems.get(stem_id)
            if stem is not None and stem.layer == layer_enum:
                stem.solo_mute = False
        return True

    # ---- Playback Status ----

    def get_playback_status(self,
                             playlist_id: str) -> Dict[str, Any]:
        playlist = self._playlists.get(playlist_id)
        if playlist is None:
            return {"error": "playlist not found"}

        current_stem_id = None
        current_stem_name = None
        if playlist.stems and playlist.current_stem_index < len(playlist.stems):
            current_stem_id = playlist.stems[playlist.current_stem_index]
            stem = self._stems.get(current_stem_id)
            current_stem_name = stem.name if stem else None

        active_transition = None
        if playlist_id in self._transition_progress:
            active_transition = round(self._transition_progress[playlist_id], 3)

        stem_states = []
        for stem_id in playlist.stems:
            stem = self._stems.get(stem_id)
            if stem is not None:
                stem_states.append({
                    "id": stem.id,
                    "name": stem.name,
                    "layer": stem.layer.value,
                    "volume": round(stem.volume, 3),
                    "solo_mute": stem.solo_mute,
                })

        return {
            "playlist_id": playlist.id,
            "playlist_name": playlist.name,
            "state": playlist.state.value,
            "category": playlist.category.value,
            "current_stem_id": current_stem_id,
            "current_stem_name": current_stem_name,
            "current_stem_index": playlist.current_stem_index,
            "total_stems": len(playlist.stems),
            "crossfade_duration": round(playlist.crossfade_duration, 2),
            "shuffle": playlist.shuffle,
            "active_transition_progress": active_transition,
            "soloed_layer": (self._layer_solos.get(playlist_id).value
                              if self._layer_solos.get(playlist_id) else None),
            "stem_states": stem_states,
        }

    def get_audio_stats(self) -> Dict[str, Any]:
        layer_distribution: Dict[str, int] = {}
        for stem in self._stems.values():
            key = stem.layer.value
            layer_distribution[key] = layer_distribution.get(key, 0) + 1

        category_distribution: Dict[str, int] = {}
        for playlist in self._playlists.values():
            key = playlist.category.value
            category_distribution[key] = category_distribution.get(key, 0) + 1

        playing_count = sum(
            1 for p in self._playlists.values()
            if p.state == PlaybackState.PLAYING
        )
        paused_count = sum(
            1 for p in self._playlists.values()
            if p.state == PlaybackState.PAUSED
        )
        transitioning_count = sum(
            1 for p in self._playlists.values()
            if p.state in (PlaybackState.TRANSITIONING,
                           PlaybackState.FADING_IN,
                           PlaybackState.FADING_OUT)
        )

        config = self._get_active_config()

        return {
            "total_stems": len(self._stems),
            "total_stems_created": self._total_stems_created,
            "layer_distribution": layer_distribution,
            "total_playlists": len(self._playlists),
            "total_playlists_created": self._total_playlists_created,
            "category_distribution": category_distribution,
            "total_transitions": len(self._transitions),
            "total_transitions_triggered": self._total_transitions_triggered,
            "total_state_maps": len(self._state_maps),
            "total_configs": len(self._configs),
            "active_config": config.name if config else None,
            "playlists_playing": playing_count,
            "playlists_paused": paused_count,
            "playlists_transitioning": transitioning_count,
            "game_state_keys": list(self._game_state.keys()),
            "active_state_map": self._active_state_map,
            "master_volume": round(config.master_volume, 3) if config else 1.0,
            "spatial_audio": config.spatial_audio_enabled if config else False,
            "doppler": config.doppler_enabled if config else False,
            "tick_count": self._tick_count,
            "default_config_count": len(self._DEFAULT_CONFIGS),
        }

    # ---- Update Loop ----

    def tick(self, delta_time: float = 0.016) -> None:
        self._tick_count += 1
        dt = max(0.001, delta_time)

        fade_complete: List[str] = []
        for playlist_id, progress in list(self._fade_progress.items()):
            playlist = self._playlists.get(playlist_id)
            if playlist is None or playlist.state != PlaybackState.FADING_OUT:
                fade_complete.append(playlist_id)
                continue
            self._fade_progress[playlist_id] = progress + dt
            if self._fade_progress[playlist_id] >= 1.0:
                playlist.state = PlaybackState.STOPPED
                fade_complete.append(playlist_id)
        for pid in fade_complete:
            self._fade_progress.pop(pid, None)

        transition_complete: List[str] = []
        for playlist_id in list(self._transition_progress.keys()):
            playlist = self._playlists.get(playlist_id)
            if playlist is None or playlist.state != PlaybackState.TRANSITIONING:
                transition_complete.append(playlist_id)
                continue

            active_transition = None
            for t in self._transitions.values():
                if (t.playlist_id == playlist_id
                        and playlist_id in self._transition_progress
                        and self._transition_progress[playlist_id] < 1.0):
                    active_transition = t
                    break

            if active_transition is not None:
                self._handle_transition_tick(playlist_id, active_transition.id, dt)

        for pid in transition_complete:
            self._transition_progress.pop(pid, None)

        for playlist_id, playlist in self._playlists.items():
            if playlist.state != PlaybackState.PLAYING:
                continue
            if playlist_id in self._transition_progress:
                continue
            current_stem = None
            if (playlist.stems
                    and playlist.current_stem_index < len(playlist.stems)):
                stem_id = playlist.stems[playlist.current_stem_index]
                current_stem = self._stems.get(stem_id)
            if current_stem is not None and current_stem.bpm > 0:
                beat_seconds = 60.0 / current_stem.bpm
                acc = self._beat_accumulator.get(playlist_id, 0.0) + dt
                self._beat_accumulator[playlist_id] = acc
                if acc >= beat_seconds * current_stem.loops * 8:
                    self._beat_accumulator[playlist_id] = 0.0
                    next_stem_id = self._advance_playlist_stem(playlist)
                    if next_stem_id is not None:
                        auto_transition = self.add_transition(
                            playlist_id=playlist_id,
                            from_stem_id=stem_id,
                            to_stem_id=next_stem_id,
                            transition_type="crossfade",
                            duration_ms=playlist.crossfade_duration * 1000.0,
                        )
                        self.trigger_transition(playlist_id, auto_transition.id)

    # ---- Reset ----

    def reset(self) -> None:
        with self._lock:
            self._stems.clear()
            self._playlists.clear()
            self._transitions.clear()
            self._state_maps.clear()
            self._configs.clear()
            self._active_config_id = None
            self._game_state.clear()
            self._layer_solos.clear()
            self._transition_progress.clear()
            self._fade_progress.clear()
            self._beat_accumulator.clear()
            self._active_state_map = None
            self._tick_count = 0
            self._total_transitions_triggered = 0
            self._total_stems_created = 0
            self._total_playlists_created = 0

    def get_stats(self) -> Dict[str, Any]:
        active_transitions = sum(
            1 for p in self._playlists.values()
            if p.state in (
                PlaybackState.TRANSITIONING,
                PlaybackState.FADING_IN,
                PlaybackState.FADING_OUT,
            )
        )

        return {
            "total_stems": len(self._stems),
            "playlist_count": len(self._playlists),
            "active_transitions": active_transitions,
            "state_count": len(self._state_maps),
        }


def get_interactive_audio() -> InteractiveAudio:
    return InteractiveAudio.get_instance()