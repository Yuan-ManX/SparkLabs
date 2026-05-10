"""
SparkLabs Engine - Dynamic Music System

Adaptive audio layering that responds to gameplay states
in real-time. Manages multi-track music composition with
intensity-based crossfading, stem control, tempo modulation,
and event-driven transitions. Music intensity, instrumentation,
and rhythm dynamically shift based on player actions, combat
state, exploration zones, and narrative progression.

Architecture:
  DynamicMusicSystem
    |-- TrackLayer (individual instrument/melody stems)
    |-- IntensityController (gradual intensity modulation)
    |-- StateTransition (crossfade between musical states)
    |-- TempoEngine (BPM modulation for pacing)
    |-- EventTrigger (gameplay event to music effect mapping)
    |-- StingerQueue (one-shot musical accents)

Music Layers:
  - AMBIENT: atmospheric pads, environmental sounds
  - RHYTHM: percussion, bass, rhythmic foundation
  - MELODY: lead instruments, thematic content
  - HARMONY: chord progressions, pads, strings
  - INTENSITY: additional layers for tension/stress
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class MusicState(Enum):
    AMBIENT = "ambient"
    EXPLORING = "exploring"
    TENSION = "tension"
    COMBAT_LOW = "combat_low"
    COMBAT_HIGH = "combat_high"
    BOSS = "boss"
    VICTORY = "victory"
    DEFEAT = "defeat"
    MENU = "menu"
    CUTSCENE = "cutscene"


class MusicLayer(Enum):
    AMBIENT = "ambient"
    RHYTHM = "rhythm"
    MELODY = "melody"
    HARMONY = "harmony"
    INTENSITY = "intensity"
    BASS = "bass"


class StingerType(Enum):
    DISCOVERY = "discovery"
    DANGER = "danger"
    ACHIEVEMENT = "achievement"
    DEATH = "death"
    LEVEL_UP = "level_up"


class TransitionType(Enum):
    CROSSFADE = "crossfade"
    IMMEDIATE = "immediate"
    STEM_FADE = "stem_fade"
    STINGER_BRIDGE = "stinger_bridge"


@dataclass
class TrackLayerConfig:
    layer_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    layer_type: MusicLayer = MusicLayer.AMBIENT
    asset_path: str = ""
    volume: float = 1.0
    is_looping: bool = True
    bpm: float = 120.0
    start_offset: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "type": self.layer_type.value,
            "volume": self.volume,
            "bpm": self.bpm,
            "looping": self.is_looping,
        }


@dataclass
class MusicStateConfig:
    state: MusicState
    active_layers: Dict[MusicLayer, float] = field(default_factory=dict)
    target_bpm: float = 120.0
    transition_duration: float = 2.0
    transition_type: TransitionType = TransitionType.CROSSFADE
    stinger_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "active_layers": {k.value: v for k, v in self.active_layers.items()},
            "target_bpm": self.target_bpm,
            "transition_type": self.transition_type.value,
        }


DEFAULT_STATE_CONFIGS: Dict[MusicState, MusicStateConfig] = {
    MusicState.AMBIENT: MusicStateConfig(
        MusicState.AMBIENT, {MusicLayer.AMBIENT: 1.0}, 60.0, 3.0, TransitionType.CROSSFADE),
    MusicState.EXPLORING: MusicStateConfig(
        MusicState.EXPLORING, {MusicLayer.AMBIENT: 0.8, MusicLayer.MELODY: 0.6, MusicLayer.RHYTHM: 0.3}, 90.0, 2.0, TransitionType.CROSSFADE),
    MusicState.TENSION: MusicStateConfig(
        MusicState.TENSION, {MusicLayer.AMBIENT: 0.9, MusicLayer.BASS: 0.7, MusicLayer.INTENSITY: 0.5}, 100.0, 1.5, TransitionType.STEM_FADE),
    MusicState.COMBAT_LOW: MusicStateConfig(
        MusicState.COMBAT_LOW, {MusicLayer.RHYTHM: 1.0, MusicLayer.BASS: 1.0, MusicLayer.INTENSITY: 0.6, MusicLayer.MELODY: 0.4}, 130.0, 1.0, TransitionType.STEM_FADE),
    MusicState.COMBAT_HIGH: MusicStateConfig(
        MusicState.COMBAT_HIGH, {MusicLayer.RHYTHM: 1.0, MusicLayer.BASS: 1.0, MusicLayer.INTENSITY: 1.0, MusicLayer.MELODY: 0.8, MusicLayer.HARMONY: 0.6}, 150.0, 0.8, TransitionType.STEM_FADE),
    MusicState.BOSS: MusicStateConfig(
        MusicState.BOSS, {MusicLayer.RHYTHM: 1.0, MusicLayer.BASS: 1.0, MusicLayer.MELODY: 1.0, MusicLayer.HARMONY: 1.0, MusicLayer.INTENSITY: 1.0}, 160.0, 0.5, TransitionType.IMMEDIATE),
    MusicState.VICTORY: MusicStateConfig(
        MusicState.VICTORY, {MusicLayer.MELODY: 1.0, MusicLayer.HARMONY: 0.8, MusicLayer.RHYTHM: 0.6}, 120.0, 1.5, TransitionType.STINGER_BRIDGE),
    MusicState.MENU: MusicStateConfig(
        MusicState.MENU, {MusicLayer.AMBIENT: 0.5, MusicLayer.MELODY: 0.7}, 80.0, 2.0, TransitionType.CROSSFADE),
}


class DynamicMusicSystem:
    _instance: Optional[DynamicMusicSystem] = None

    @classmethod
    def get_instance(cls) -> DynamicMusicSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._layers: Dict[str, TrackLayerConfig] = {}
        self._current_state: MusicState = MusicState.AMBIENT
        self._previous_state: Optional[MusicState] = None
        self._current_bpm: float = 120.0
        self._target_bpm: float = 120.0
        self._transition_progress: float = 1.0
        self._transition_duration: float = 0.0
        self._state_change_count: int = 0
        self._stinger_history: List[Dict[str, Any]] = []

    def register_layer(self, layer: TrackLayerConfig) -> str:
        self._layers[layer.layer_id] = layer
        return layer.layer_id

    def set_state(self, new_state: MusicState, immediate: bool = False):
        if new_state == self._current_state:
            return
        self._previous_state = self._current_state
        self._current_state = new_state
        config = DEFAULT_STATE_CONFIGS.get(new_state, DEFAULT_STATE_CONFIGS[MusicState.AMBIENT])
        self._target_bpm = config.target_bpm
        self._transition_duration = 0.0 if immediate else config.transition_duration
        self._transition_progress = 0.0
        self._state_change_count += 1

    def trigger_stinger(self, stinger_type: StingerType, position: float = 0.0):
        self._stinger_history.append({
            "type": stinger_type.value,
            "position": position,
            "timestamp": time.time(),
        })
        if len(self._stinger_history) > 20:
            self._stinger_history = self._stinger_history[-20:]

    def get_layer_volumes(self) -> Dict[str, float]:
        config = DEFAULT_STATE_CONFIGS.get(self._current_state)
        if config is None:
            return {}
        volumes = {}
        for layer in self._layers.values():
            target_volume = config.active_layers.get(layer.layer_type, 0.0)
            if self._transition_progress < 1.0:
                prev_config = DEFAULT_STATE_CONFIGS.get(self._previous_state) if self._previous_state else None
                prev_volume = prev_config.active_layers.get(layer.layer_type, 0.0) if prev_config else 0.0
                t = min(1.0, self._transition_progress)
                volumes[layer.layer_id] = prev_volume + (target_volume - prev_volume) * t
            else:
                volumes[layer.layer_id] = target_volume
        return volumes

    def update(self, delta_time: float) -> Dict[str, Any]:
        dt = max(0.001, delta_time)
        if self._transition_progress < 1.0:
            self._transition_progress += dt / max(0.001, self._transition_duration)

        bpm_smoothing = 3.0
        self._current_bpm += (self._target_bpm - self._current_bpm) * dt * bpm_smoothing

        return {
            "state": self._current_state.value,
            "bpm": round(self._current_bpm, 1),
            "transition": round(self._transition_progress, 2),
            "layer_volumes": self.get_layer_volumes(),
        }

    def get_current_config(self) -> Optional[MusicStateConfig]:
        return DEFAULT_STATE_CONFIGS.get(self._current_state)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "current_state": self._current_state.value,
            "target_bpm": self._target_bpm,
            "current_bpm": round(self._current_bpm, 1),
            "registered_layers": len(self._layers),
            "state_changes": self._state_change_count,
            "transition_progress": round(self._transition_progress, 2),
        }


def get_dynamic_music() -> DynamicMusicSystem:
    return DynamicMusicSystem.get_instance()