"""
SparkLabs Engine - Audio Layering Engine

Dynamic audio mix system providing crossfade transitions, priority-based
ducking, and spatial positioning for real-time game audio layering.
Manages audio layers through mix presets and rule-based volume modulation
across music, ambient, SFX, UI, voice, and master channels.

Architecture:
  AudioLayeringEngine
    |-- LayerRegistry (catalog of named audio layers with type and spatial data)
    |-- PresetManager (mix presets storing layer volume configurations)
    |-- RuleProcessor (source-target mix rules: duck, reduce, mute, crossfade, passthrough)
    |-- EventScheduler (crossfade and ducking events with time-based interpolation)
    |-- SpatialRouter (3D positional audio routing with stereo/surround/HRTF models)

Audio Layering Features:
  - CROSSFADE: smooth volume transition between two layers over time
  - DUCKING: temporary volume reduction on a target when a trigger layer is active
  - SPATIAL: per-layer 3D positioning with stereo panning and distance modeling
  - PRESETS: named configurations of layer volumes for scene-specific mixing
  - MASTER: global volume control affecting all downstream layers
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AudioLayerType(Enum):
    """Classification of audio layer by content type for priority grouping."""
    MUSIC = "music"
    AMBIENT = "ambient"
    SFX = "sfx"
    UI = "ui"
    VOICE = "voice"
    MASTER = "master"


class MixRule(Enum):
    """Volume interaction rule between a source layer and a target layer."""
    DUCK = "duck"
    REDUCE = "reduce"
    MUTE = "mute"
    CROSSFADE = "crossfade"
    PASSTHROUGH = "passthrough"


class SpatialModel(Enum):
    """Spatial audio rendering model for layer positioning."""
    STEREO = "stereo"
    SURROUND = "surround"
    THREE_D = "3d"
    HRTF = "hrtf"


@dataclass
class AudioLayer:
    """Named audio layer with volume, pan, pitch, and spatial positioning."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    layer_type: AudioLayerType = AudioLayerType.MUSIC
    volume: float = 1.0
    pan: float = 0.0
    pitch: float = 1.0
    spatial_x: float = 0.0
    spatial_y: float = 0.0
    spatial_z: float = 0.0
    spatial_model: SpatialModel = SpatialModel.STEREO
    is_muted: bool = False
    is_soloed: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "layer_type": self.layer_type.value,
            "volume": round(self.volume, 3),
            "pan": round(self.pan, 2),
            "pitch": round(self.pitch, 2),
            "spatial_x": round(self.spatial_x, 2),
            "spatial_y": round(self.spatial_y, 2),
            "spatial_z": round(self.spatial_z, 2),
            "spatial_model": self.spatial_model.value,
            "is_muted": self.is_muted,
            "is_soloed": self.is_soloed,
            "created_at": self.created_at,
        }


@dataclass
class MixPreset:
    """Named collection of layer volume settings for scene-specific audio mixing."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    layers: Dict[str, float] = field(default_factory=dict)
    mix_rules: List[Dict[str, Any]] = field(default_factory=list)
    is_active: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "layer_count": len(self.layers),
            "layers": dict(self.layers),
            "rule_count": len(self.mix_rules),
            "mix_rules": [dict(r) for r in self.mix_rules],
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


@dataclass
class AudioMixerChannel:
    """Virtual mixer channel bridging a layer to the output bus."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    volume: float = 1.0
    target_volume: float = 1.0
    transition_speed: float = 2.0
    is_muted: bool = False
    layer_type: AudioLayerType = AudioLayerType.MUSIC
    active_layers: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "volume": round(self.volume, 3),
            "target_volume": round(self.target_volume, 3),
            "transition_speed": round(self.transition_speed, 1),
            "is_muted": self.is_muted,
            "layer_type": self.layer_type.value,
            "active_layers": self.active_layers,
        }


@dataclass
class AudioMixEvent:
    """Time-based audio mixing event for crossfade or ducking transitions."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = "crossfade"
    from_layer_id: str = ""
    to_layer_id: str = ""
    duration: float = 1.0
    progress: float = 0.0
    amount: float = 0.5
    hold_ms: float = 500.0
    release_ms: float = 300.0
    started_at: float = field(default_factory=time.time)
    is_complete: bool = False
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "from_layer_id": self.from_layer_id,
            "to_layer_id": self.to_layer_id,
            "duration": round(self.duration, 2),
            "progress": round(self.progress, 3),
            "amount": round(self.amount, 2),
            "hold_ms": round(self.hold_ms, 1),
            "release_ms": round(self.release_ms, 1),
            "started_at": self.started_at,
            "is_complete": self.is_complete,
            "is_active": self.is_active,
        }


class AudioLayeringEngine:
    """Dynamic audio mix system with crossfade, priority ducking, and spatial positioning."""

    _instance: Optional["AudioLayeringEngine"] = None
    _lock = threading.RLock()

    _DEFAULT_PRESETS = [
        {"name": "Default Mix", "description": "Standard balanced audio mix"},
        {"name": "Combat Heavy", "description": "SFX-forward mix for combat scenes"},
        {"name": "Ambient Focus", "description": "Ambient-forward mix for exploration"},
        {"name": "Cinematic", "description": "Music-forward mix for cutscenes"},
        {"name": "UI Only", "description": "Minimal mix focusing on interface sounds"},
    ]

    def __init__(self) -> None:
        self._layers: Dict[str, AudioLayer] = {}
        self._presets: Dict[str, MixPreset] = {}
        self._mix_rules: Dict[str, Dict[str, MixRule]] = {}
        self._mix_events: Dict[str, AudioMixEvent] = {}
        self._channels: Dict[AudioLayerType, AudioMixerChannel] = {}
        self._active_preset_id: Optional[str] = None
        self._master_volume: float = 1.0
        self._listener_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._tick_count: int = 0
        self._total_events_processed: int = 0
        self._total_presets_applied: int = 0

    @classmethod
    def get_instance(cls) -> "AudioLayeringEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Layer Management ----

    def create_layer(self,
                     name: str,
                     layer_type: str = "music",
                     volume: float = 1.0,
                     pan: float = 0.0,
                     pitch: float = 1.0) -> AudioLayer:
        try:
            lt = AudioLayerType(layer_type.lower())
        except ValueError:
            lt = AudioLayerType.MUSIC

        layer = AudioLayer(
            name=name,
            layer_type=lt,
            volume=max(0.0, min(1.0, volume)),
            pan=max(-1.0, min(1.0, pan)),
            pitch=max(0.1, min(4.0, pitch)),
        )
        self._layers[layer.id] = layer

        if lt not in self._channels:
            self._channels[lt] = AudioMixerChannel(
                name=f"{lt.value.capitalize()} Channel",
                layer_type=lt,
            )
        self._channels[lt].active_layers += 1

        return layer

    def get_layer(self, layer_id: str) -> Optional[AudioLayer]:
        return self._layers.get(layer_id)

    def list_layers(self,
                    layer_type: Optional[str] = None) -> List[AudioLayer]:
        layers = list(self._layers.values())
        if layer_type:
            try:
                lt = AudioLayerType(layer_type.lower())
                return [l for l in layers if l.layer_type == lt]
            except ValueError:
                return []
        return layers

    def remove_layer(self, layer_id: str) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False
        lt = layer.layer_type
        del self._layers[layer_id]

        ch = self._channels.get(lt)
        if ch:
            ch.active_layers = max(0, ch.active_layers - 1)

        for preset in self._presets.values():
            preset.layers.pop(layer_id, None)

        self._mix_rules.pop(layer_id, None)
        for rules in self._mix_rules.values():
            rules.pop(layer_id, None)

        return True

    # ---- Preset Management ----

    def create_mix_preset(self,
                          name: str,
                          description: str = "") -> MixPreset:
        preset = MixPreset(name=name, description=description)
        self._presets[preset.id] = preset
        return preset

    def add_layer_to_preset(self,
                            preset_id: str,
                            layer_id: str,
                            volume: float = 1.0) -> bool:
        preset = self._presets.get(preset_id)
        if preset is None:
            return False
        if layer_id not in self._layers:
            return False
        preset.layers[layer_id] = max(0.0, min(1.0, volume))
        return True

    def remove_layer_from_preset(self,
                                  preset_id: str,
                                  layer_id: str) -> bool:
        preset = self._presets.get(preset_id)
        if preset is None:
            return False
        if layer_id in preset.layers:
            del preset.layers[layer_id]
            return True
        return False

    def get_preset(self, preset_id: str) -> Optional[MixPreset]:
        return self._presets.get(preset_id)

    def list_presets(self) -> List[MixPreset]:
        return list(self._presets.values())

    def seed_default_presets(self) -> List[MixPreset]:
        presets = []
        for p in self._DEFAULT_PRESETS:
            preset = self.create_mix_preset(**p)
            presets.append(preset)
        return presets

    # ---- Mix Rules ----

    def set_mix_rule(self,
                     source_layer_id: str,
                     target_layer_id: str,
                     rule: str = "duck",
                     amount: float = 0.5) -> MixRule:
        try:
            rule_enum = MixRule(rule.lower())
        except ValueError:
            rule_enum = MixRule.DUCK

        if source_layer_id not in self._mix_rules:
            self._mix_rules[source_layer_id] = {}
        self._mix_rules[source_layer_id][target_layer_id] = rule_enum

        for preset in self._presets.values():
            preset.mix_rules.append({
                "source_layer_id": source_layer_id,
                "target_layer_id": target_layer_id,
                "rule": rule_enum.value,
                "amount": round(max(0.0, min(1.0, amount)), 2),
            })

        return rule_enum

    def get_mix_rule(self,
                     source_layer_id: str,
                     target_layer_id: str) -> Optional[MixRule]:
        source_rules = self._mix_rules.get(source_layer_id, {})
        return source_rules.get(target_layer_id)

    def clear_mix_rules(self) -> None:
        self._mix_rules.clear()

    # ---- Preset Application ----

    def apply_preset(self, preset_id: str) -> bool:
        preset = self._presets.get(preset_id)
        if preset is None:
            return False

        for old_preset in self._presets.values():
            old_preset.is_active = False

        for layer_id, volume in preset.layers.items():
            layer = self._layers.get(layer_id)
            if layer is not None:
                layer.volume = max(0.0, min(1.0, volume))

        preset.is_active = True
        self._active_preset_id = preset_id
        self._total_presets_applied += 1
        return True

    # ---- Crossfade ----

    def crossfade_layers(self,
                         from_layer_id: str,
                         to_layer_id: str,
                         duration: float = 1.0) -> AudioMixEvent:
        from_layer = self._layers.get(from_layer_id)
        to_layer = self._layers.get(to_layer_id)

        event = AudioMixEvent(
            event_type="crossfade",
            from_layer_id=from_layer_id,
            to_layer_id=to_layer_id,
            duration=max(0.01, duration),
            amount=0.0,
        )

        if to_layer is not None:
            to_layer.volume = 0.0

        self._mix_events[event.id] = event
        self._total_events_processed += 1
        return event

    # ---- Ducking ----

    def duck_layer(self,
                   target_layer_id: str,
                   trigger_layer_id: str,
                   reduction: float = 0.5,
                   hold_ms: float = 500.0,
                   release_ms: float = 300.0) -> bool:
        target_layer = self._layers.get(target_layer_id)
        if target_layer is None:
            return False

        event = AudioMixEvent(
            event_type="duck",
            to_layer_id=target_layer_id,
            from_layer_id=trigger_layer_id,
            amount=max(0.0, min(1.0, reduction)),
            hold_ms=max(0.0, hold_ms),
            release_ms=max(1.0, release_ms),
        )

        target_layer.volume = target_layer.volume * (1.0 - event.amount)

        self._mix_events[event.id] = event
        self._total_events_processed += 1
        return True

    # ---- Spatial Positioning ----

    def set_spatial_position(self,
                              layer_id: str,
                              x: float = 0.0,
                              y: float = 0.0,
                              z: float = 0.0) -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False
        layer.spatial_x = x
        layer.spatial_y = y
        layer.spatial_z = z
        self._recompute_spatial_pan(layer)
        return True

    def set_spatial_model(self,
                           layer_id: str,
                           model: str = "stereo") -> bool:
        layer = self._layers.get(layer_id)
        if layer is None:
            return False
        try:
            layer.spatial_model = SpatialModel(model.lower())
        except ValueError:
            layer.spatial_model = SpatialModel.STEREO
        return True

    def set_listener_position(self,
                               x: float,
                               y: float,
                               z: float) -> None:
        self._listener_position = (x, y, z)
        for layer in self._layers.values():
            if layer.spatial_model != SpatialModel.STEREO:
                self._recompute_spatial_pan(layer)

    def _recompute_spatial_pan(self, layer: AudioLayer) -> None:
        if layer.spatial_model == SpatialModel.STEREO:
            return

        lx, ly, lz = self._listener_position
        dx = layer.spatial_x - lx
        dy = layer.spatial_y - ly
        dz = layer.spatial_z - lz
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        if layer.spatial_model == SpatialModel.HRTF:
            pan = math.atan2(dx, abs(dz) + 0.001) / (math.pi * 0.5)
            layer.pan = max(-1.0, min(1.0, pan))
        elif layer.spatial_model == SpatialModel.THREE_D:
            pan = dx / max(distance, 0.001)
            layer.pan = max(-1.0, min(1.0, pan))
        elif layer.spatial_model == SpatialModel.SURROUND:
            pan = dx / max(distance, 0.001)
            layer.pan = max(-1.0, min(1.0, pan))

    # ---- Master Volume ----

    def set_master_volume(self, volume: float) -> None:
        self._master_volume = max(0.0, min(1.0, volume))

    # ---- Active Mix State ----

    def get_active_mix(self) -> Dict[str, Any]:
        active_preset = None
        if self._active_preset_id:
            active_preset = self._presets.get(self._active_preset_id)

        layers_state = []
        for layer in self._layers.values():
            rules_for_layer: Dict[str, str] = {}
            for src_id, targets in self._mix_rules.items():
                if layer.id in targets:
                    rules_for_layer[src_id] = targets[layer.id].value

            layers_state.append({
                "id": layer.id,
                "name": layer.name,
                "type": layer.layer_type.value,
                "volume": round(layer.volume, 3),
                "effective_volume": round(layer.volume * self._master_volume, 3),
                "pan": round(layer.pan, 2),
                "is_muted": layer.is_muted,
                "active_rules": rules_for_layer,
            })

        active_events = []
        for event in self._mix_events.values():
            if event.is_active and not event.is_complete:
                active_events.append({
                    "id": event.id,
                    "type": event.event_type,
                    "from": event.from_layer_id,
                    "to": event.to_layer_id,
                    "progress": round(event.progress, 3),
                })

        return {
            "master_volume": round(self._master_volume, 3),
            "active_preset": active_preset.name if active_preset else None,
            "active_preset_id": self._active_preset_id,
            "total_layers": len(self._layers),
            "layers": layers_state,
            "active_events": active_events,
            "active_event_count": len(active_events),
        }

    # ---- Update Loop ----

    def tick(self, delta_time: float = 0.016) -> None:
        self._tick_count += 1

        completed: List[str] = []
        for event_id, event in self._mix_events.items():
            if event.is_complete or not event.is_active:
                continue

            event.progress += delta_time / max(0.001, event.duration)

            if event.event_type == "crossfade":
                self._tick_crossfade(event, delta_time)
            elif event.event_type == "duck":
                self._tick_duck(event, delta_time)

            if event.progress >= 1.0:
                event.is_complete = True
                event.is_active = False
                completed.append(event_id)

        for event_id in completed:
            self._mix_events.pop(event_id, None)

        for ch in self._channels.values():
            diff = ch.target_volume - ch.volume
            if abs(diff) > 0.001:
                ch.volume += diff * min(1.0, delta_time * ch.transition_speed)

    def _tick_crossfade(self, event: AudioMixEvent, delta_time: float) -> None:
        from_layer = self._layers.get(event.from_layer_id)
        to_layer = self._layers.get(event.to_layer_id)

        t = min(1.0, event.progress)

        if from_layer is not None:
            from_layer.volume = max(0.0, from_layer.volume * (1.0 - t))

        if to_layer is not None:
            from_vol = 0.0
            if from_layer is not None:
                from_vol = from_layer.volume
            to_layer.volume = min(1.0, to_layer.volume + t * (1.0 - from_vol))

    def _tick_duck(self, event: AudioMixEvent, delta_time: float) -> None:
        target_layer = self._layers.get(event.to_layer_id)
        if target_layer is None:
            return

        progress_ms = event.progress * event.duration * 1000.0

        if progress_ms < event.hold_ms:
            return

        release_progress = (progress_ms - event.hold_ms) / max(1.0, event.release_ms)
        release_t = min(1.0, release_progress)

        original_volume = target_layer.volume / max(0.01, 1.0 - event.amount)
        target_layer.volume = original_volume * (1.0 - event.amount * (1.0 - release_t))
        target_layer.volume = max(0.0, min(1.0, target_layer.volume))

    # ---- Channel Management ----

    def get_channel(self, layer_type: str) -> Optional[AudioMixerChannel]:
        try:
            lt = AudioLayerType(layer_type.lower())
        except ValueError:
            return None
        return self._channels.get(lt)

    def list_channels(self) -> List[AudioMixerChannel]:
        return list(self._channels.values())

    def set_channel_volume(self,
                            layer_type: str,
                            volume: float) -> bool:
        ch = self.get_channel(layer_type)
        if ch is None:
            return False
        ch.target_volume = max(0.0, min(1.0, volume))
        return True

    # ---- Stats ----

    def get_stats(self) -> Dict[str, Any]:
        type_counts: Dict[str, int] = {}
        for layer in self._layers.values():
            lt = layer.layer_type.value
            type_counts[lt] = type_counts.get(lt, 0) + 1

        total_rules = sum(len(targets) for targets in self._mix_rules.values())
        active_events = sum(
            1 for e in self._mix_events.values()
            if e.is_active and not e.is_complete
        )

        layers_per_channel = {}
        for lt, ch in self._channels.items():
            layers_per_channel[lt.value] = ch.active_layers

        return {
            "total_layers": len(self._layers),
            "layer_type_distribution": type_counts,
            "total_presets": len(self._presets),
            "active_preset": self._active_preset_id,
            "total_mix_rules": total_rules,
            "total_events_processed": self._total_events_processed,
            "active_events": active_events,
            "total_events": len(self._mix_events),
            "total_channels": len(self._channels),
            "layers_per_channel": layers_per_channel,
            "master_volume": round(self._master_volume, 3),
            "total_presets_applied": self._total_presets_applied,
            "tick_count": self._tick_count,
            "default_preset_count": len(self._DEFAULT_PRESETS),
            "listener_position": list(self._listener_position),
        }

    # ---- Reset ----

    def reset(self) -> None:
        with self._lock:
            self._layers.clear()
            self._presets.clear()
            self._mix_rules.clear()
            self._mix_events.clear()
            self._channels.clear()
            self._active_preset_id = None
            self._master_volume = 1.0
            self._listener_position = (0.0, 0.0, 0.0)
            self._tick_count = 0
            self._total_events_processed = 0
            self._total_presets_applied = 0


def get_audio_layering() -> AudioLayeringEngine:
    return AudioLayeringEngine.get_instance()