"""
SparkLabs Engine - Scene Transition System

Smooth scene transition management providing blend effects, configurable
easing curves, and scene preloading for seamless gameplay flow. Supports
sequenced multi-step transitions and real-time loading progress tracking.

Architecture:
  SceneTransitionSystem
    |-- TransitionConfig (effect, duration, easing, and scene pair definition)
    |-- TransitionEvent (active transition runtime state with progress)
    |-- TransitionSequence (ordered chain of configs with auto-advance)
    |-- LoadingProgress (per-transition resource loading progress)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TransitionEffect(Enum):
    FADE = "fade"
    CROSSFADE = "crossfade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    WIPE = "wipe"
    CUSTOM = "custom"


class TransitionState(Enum):
    IDLE = "idle"
    PRELOADING = "preloading"
    TRANSITIONING = "transitioning"
    COMPLETE = "complete"
    FAILED = "failed"


class EasingFunction(Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"


@dataclass
class TransitionConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_scene: str = ""
    to_scene: str = ""
    effect: TransitionEffect = TransitionEffect.FADE
    duration: float = 0.5
    easing: EasingFunction = EasingFunction.EASE_IN_OUT
    preload_assets: bool = True
    auto_unload_from: bool = True
    mask_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    custom_shader: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_scene": self.from_scene,
            "to_scene": self.to_scene,
            "effect": self.effect.value,
            "duration": round(self.duration, 3),
            "easing": self.easing.value,
            "preload_assets": self.preload_assets,
            "auto_unload_from": self.auto_unload_from,
            "mask_color": list(self.mask_color),
            "custom_shader": self.custom_shader,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass
class TransitionEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    config_id: str = ""
    state: TransitionState = TransitionState.IDLE
    progress: float = 0.0
    elapsed: float = 0.0
    from_scene: str = ""
    to_scene: str = ""
    effect: TransitionEffect = TransitionEffect.FADE
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    error_message: str = ""
    sequence_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "config_id": self.config_id,
            "state": self.state.value,
            "progress": round(self.progress, 4),
            "elapsed": round(self.elapsed, 3),
            "from_scene": self.from_scene,
            "to_scene": self.to_scene,
            "effect": self.effect.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
            "sequence_id": self.sequence_id,
        }


@dataclass
class TransitionSequence:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    config_ids: List[str] = field(default_factory=list)
    current_index: int = 0
    auto_advance: bool = True
    looping: bool = False
    is_active: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "config_ids": list(self.config_ids),
            "current_index": self.current_index,
            "auto_advance": self.auto_advance,
            "looping": self.looping,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


@dataclass
class LoadingProgress:
    event_id: str = ""
    total_assets: int = 0
    loaded_assets: int = 0
    current_asset: str = ""
    percent: float = 0.0
    estimated_remaining: float = 0.0
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "total_assets": self.total_assets,
            "loaded_assets": self.loaded_assets,
            "current_asset": self.current_asset,
            "percent": round(self.percent, 2),
            "estimated_remaining": round(self.estimated_remaining, 2),
            "updated_at": self.updated_at,
        }


class SceneTransitionSystem:
    """Smooth scene transition manager with blend effects and loading management."""

    _instance: Optional["SceneTransitionSystem"] = None
    _lock = threading.RLock()

    MAX_CONFIGS = 1000
    MAX_SEQUENCES = 200
    MAX_HISTORY = 500
    MAX_ACTIVE_TRANSITIONS = 16

    # ---- Easing curves ----

    _EASING_PRESETS: Dict[str, Dict[str, Any]] = {
        "fade": {
            "maskable": True,
            "slide_direction": None,
            "uses_zoom": False,
            "default_duration": 0.4,
        },
        "crossfade": {
            "maskable": False,
            "slide_direction": None,
            "uses_zoom": False,
            "default_duration": 0.6,
        },
        "slide_left": {
            "maskable": True,
            "slide_direction": (-1.0, 0.0),
            "uses_zoom": False,
            "default_duration": 0.5,
        },
        "slide_right": {
            "maskable": True,
            "slide_direction": (1.0, 0.0),
            "uses_zoom": False,
            "default_duration": 0.5,
        },
        "slide_up": {
            "maskable": True,
            "slide_direction": (0.0, -1.0),
            "uses_zoom": False,
            "default_duration": 0.5,
        },
        "slide_down": {
            "maskable": True,
            "slide_direction": (0.0, 1.0),
            "uses_zoom": False,
            "default_duration": 0.5,
        },
        "zoom_in": {
            "maskable": False,
            "slide_direction": None,
            "uses_zoom": True,
            "default_duration": 0.4,
        },
        "zoom_out": {
            "maskable": False,
            "slide_direction": None,
            "uses_zoom": True,
            "default_duration": 0.4,
        },
        "wipe": {
            "maskable": True,
            "slide_direction": None,
            "uses_zoom": False,
            "default_duration": 0.5,
        },
        "custom": {
            "maskable": False,
            "slide_direction": None,
            "uses_zoom": False,
            "default_duration": 0.5,
        },
    }

    def __init__(self) -> None:
        self._configs: Dict[str, TransitionConfig] = {}
        self._events: Dict[str, TransitionEvent] = {}
        self._sequences: Dict[str, TransitionSequence] = {}
        self._loading_progress: Dict[str, LoadingProgress] = {}
        self._history: List[TransitionEvent] = []
        self._active_event_ids: List[str] = []
        self._total_transitions: int = 0
        self._total_sequences_run: int = 0
        self._preload_cache: Dict[str, List[str]] = {}

    @classmethod
    def get_instance(cls) -> "SceneTransitionSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Configuration ----

    def configure_transition(
        self,
        from_scene: str,
        to_scene: str,
        effect: str = "fade",
        duration: float = 0.5,
        easing: str = "ease_in_out",
        preload_assets: bool = True,
        auto_unload_from: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TransitionConfig:
        try:
            te = TransitionEffect(effect.lower())
        except ValueError:
            te = TransitionEffect.FADE
        try:
            ef = EasingFunction(easing.lower())
        except ValueError:
            ef = EasingFunction.EASE_IN_OUT

        preset = self._EASING_PRESETS.get(te.value, {})
        resolved_duration = duration if duration > 0 else preset.get("default_duration", 0.5)

        config = TransitionConfig(
            from_scene=from_scene,
            to_scene=to_scene,
            effect=te,
            duration=max(0.05, min(30.0, resolved_duration)),
            easing=ef,
            preload_assets=preload_assets,
            auto_unload_from=auto_unload_from,
            metadata=metadata or {},
        )

        if len(self._configs) >= self.MAX_CONFIGS:
            oldest_id = next(iter(self._configs.keys()))
            del self._configs[oldest_id]

        self._configs[config.id] = config
        return config

    def get_config(self, config_id: str) -> Optional[TransitionConfig]:
        return self._configs.get(config_id)

    def remove_config(self, config_id: str) -> bool:
        if config_id not in self._configs:
            return False
        for evt in self._events.values():
            if evt.config_id == config_id and evt.state in (
                TransitionState.PRELOADING,
                TransitionState.TRANSITIONING,
            ):
                return False
        del self._configs[config_id]
        return True

    # ---- Transition Execution ----

    def start_transition(self, config_id: str) -> Optional[TransitionEvent]:
        config = self._configs.get(config_id)
        if config is None:
            return None

        if len(self._active_event_ids) >= self.MAX_ACTIVE_TRANSITIONS:
            return None

        event = TransitionEvent(
            config_id=config_id,
            state=TransitionState.IDLE,
            from_scene=config.from_scene,
            to_scene=config.to_scene,
            effect=config.effect,
            elapsed=0.0,
            progress=0.0,
        )

        if config.preload_assets:
            event.state = TransitionState.PRELOADING
            self._init_loading_progress(event.id, config.to_scene)
        else:
            event.state = TransitionState.TRANSITIONING

        self._events[event.id] = event
        self._active_event_ids.append(event.id)
        self._total_transitions += 1

        return event

    def complete_transition(self, event_id: str) -> bool:
        event = self._events.get(event_id)
        if event is None:
            return False
        if event.state == TransitionState.COMPLETE:
            return True

        event.state = TransitionState.COMPLETE
        event.progress = 1.0
        event.completed_at = time.time()

        self._remove_from_active(event_id)
        self._push_to_history(event)

        config = self._configs.get(event.config_id)
        if config and config.auto_unload_from and config.from_scene in self._preload_cache:
            del self._preload_cache[config.from_scene]

        if event.sequence_id:
            self._advance_sequence(event.sequence_id, event_id)

        return True

    def cancel_transition(self, event_id: str) -> bool:
        event = self._events.get(event_id)
        if event is None:
            return False
        if event.state in (TransitionState.COMPLETE, TransitionState.FAILED):
            return False

        event.state = TransitionState.FAILED
        event.progress = 0.0
        event.error_message = "cancelled by user"
        event.completed_at = time.time()

        self._remove_from_active(event_id)
        self._push_to_history(event)
        self._loading_progress.pop(event_id, None)

        return True

    def fail_transition(self, event_id: str, error_message: str = "") -> bool:
        event = self._events.get(event_id)
        if event is None:
            return False

        event.state = TransitionState.FAILED
        event.error_message = error_message or "unknown error"
        event.completed_at = time.time()

        self._remove_from_active(event_id)
        self._push_to_history(event)
        self._loading_progress.pop(event_id, None)

        return True

    # ---- Loading Progress ----

    def update_progress(
        self,
        event_id: str,
        loaded_assets: int,
        total_assets: int = 0,
        current_asset: str = "",
    ) -> Optional[LoadingProgress]:
        event = self._events.get(event_id)
        if event is None:
            return None
        if event.state != TransitionState.PRELOADING:
            return self._loading_progress.get(event_id)

        total = total_assets if total_assets > 0 else loaded_assets
        safe_total = max(1, total)
        percent = min(1.0, loaded_assets / safe_total)

        lp = self._loading_progress.get(event_id)
        if lp is None:
            lp = LoadingProgress(event_id=event_id)
            self._loading_progress[event_id] = lp

        lp.loaded_assets = loaded_assets
        lp.total_assets = safe_total
        lp.current_asset = current_asset
        lp.percent = percent
        lp.updated_at = time.time()

        if lp.loaded_assets > 0 and lp.total_assets > 0:
            elapsed = time.time() - event.started_at
            rate = lp.loaded_assets / max(0.001, elapsed)
            remaining = safe_total - lp.loaded_assets
            lp.estimated_remaining = remaining / max(0.001, rate)

        event.progress = percent

        if percent >= 1.0:
            event.state = TransitionState.TRANSITIONING
            event.elapsed = 0.0
            event.started_at = time.time()

        return lp

    # ---- Sequence Management ----

    def create_sequence(
        self,
        name: str = "",
        steps: Optional[List[Dict[str, Any]]] = None,
        auto_advance: bool = True,
        looping: bool = False,
    ) -> TransitionSequence:
        if len(self._sequences) >= self.MAX_SEQUENCES:
            oldest_id = next(iter(self._sequences.keys()))
            del self._sequences[oldest_id]

        sequence = TransitionSequence(
            name=name or f"sequence_{len(self._sequences) + 1}",
            auto_advance=auto_advance,
            looping=looping,
        )

        for step in (steps or []):
            config = self.configure_transition(
                from_scene=step.get("from_scene", ""),
                to_scene=step.get("to_scene", ""),
                effect=step.get("effect", "fade"),
                duration=step.get("duration", 0.3),
                easing=step.get("easing", "ease_in_out"),
            )
            sequence.config_ids.append(config.id)

        self._sequences[sequence.id] = sequence
        return sequence

    def add_step_to_sequence(
        self,
        sequence_id: str,
        from_scene: str,
        to_scene: str,
        effect: str = "fade",
        duration: float = 0.3,
        easing: str = "ease_in_out",
    ) -> Optional[TransitionConfig]:
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            return None

        config = self.configure_transition(
            from_scene=from_scene,
            to_scene=to_scene,
            effect=effect,
            duration=duration,
            easing=easing,
        )
        sequence.config_ids.append(config.id)
        return config

    def remove_step_from_sequence(
        self, sequence_id: str, step_index: int,
    ) -> bool:
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            return False
        if step_index < 0 or step_index >= len(sequence.config_ids):
            return False
        config_id = sequence.config_ids.pop(step_index)
        self._configs.pop(config_id, None)
        return True

    def start_sequence(self, sequence_id: str) -> Optional[TransitionEvent]:
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            return None
        if not sequence.config_ids:
            return None

        sequence.is_active = True
        sequence.current_index = 0
        self._total_sequences_run += 1

        config_id = sequence.config_ids[0]
        event = self.start_transition(config_id)
        if event:
            event.sequence_id = sequence_id

        return event

    def stop_sequence(self, sequence_id: str) -> bool:
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            return False
        sequence.is_active = False
        sequence.current_index = 0

        for evt in list(self._events.values()):
            if evt.sequence_id == sequence_id:
                self.cancel_transition(evt.id)

        return True

    # ---- Effect Preview ----

    def preview_effect(
        self,
        effect_name: str,
        preview_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            te = TransitionEffect(effect_name.lower())
        except ValueError:
            return {"error": f"unknown_effect", "effect": effect_name}

        preset = self._EASING_PRESETS.get(te.value, {})
        context = preview_context or {}

        preview = {
            "effect": te.value,
            "category": self._classify_effect(te),
            "maskable": preset.get("maskable", False),
            "slide_direction": preset.get("slide_direction"),
            "uses_zoom": preset.get("uses_zoom", False),
            "default_duration": preset.get("default_duration", 0.5),
            "supported_easing": [
                EasingFunction.LINEAR.value,
                EasingFunction.EASE_IN.value,
                EasingFunction.EASE_OUT.value,
                EasingFunction.EASE_IN_OUT.value,
                EasingFunction.BOUNCE.value,
                EasingFunction.ELASTIC.value,
            ],
            "preview_frames": self._generate_preview_frames(
                te, context.get("frame_count", 16),
            ),
            "metadata": dict(context),
        }

        return preview

    def _classify_effect(self, effect: TransitionEffect) -> str:
        if effect in (TransitionEffect.FADE, TransitionEffect.CROSSFADE):
            return "blend"
        if effect in (
            TransitionEffect.SLIDE_LEFT,
            TransitionEffect.SLIDE_RIGHT,
            TransitionEffect.SLIDE_UP,
            TransitionEffect.SLIDE_DOWN,
        ):
            return "slide"
        if effect in (TransitionEffect.ZOOM_IN, TransitionEffect.ZOOM_OUT):
            return "zoom"
        if effect == TransitionEffect.WIPE:
            return "wipe"
        return "custom"

    def _generate_preview_frames(
        self, effect: TransitionEffect, frame_count: int,
    ) -> List[Dict[str, Any]]:
        frames: List[Dict[str, Any]] = []
        for i in range(max(4, min(60, frame_count))):
            t = i / max(1, frame_count - 1)
            val = self._ease_value(t, EasingFunction.EASE_IN_OUT)
            frames.append({
                "frame": i,
                "t": round(t, 3),
                "value": round(val, 4),
            })
        return frames

    # ---- Easing Computation ----

    def _ease_value(
        self, t: float, easing: EasingFunction,
    ) -> float:
        t = max(0.0, min(1.0, t))

        if easing == EasingFunction.LINEAR:
            return t
        if easing == EasingFunction.EASE_IN:
            return t * t
        if easing == EasingFunction.EASE_OUT:
            return 1.0 - (1.0 - t) * (1.0 - t)
        if easing == EasingFunction.EASE_IN_OUT:
            if t < 0.5:
                return 2.0 * t * t
            return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0
        if easing == EasingFunction.BOUNCE:
            return self._bounce_ease(t)
        if easing == EasingFunction.ELASTIC:
            return self._elastic_ease(t)
        return t

    @staticmethod
    def _bounce_ease(t: float) -> float:
        n1 = 7.5625
        d1 = 2.75
        if t < 1.0 / d1:
            return n1 * t * t
        if t < 2.0 / d1:
            t2 = t - 1.5 / d1
            return n1 * t2 * t2 + 0.75
        if t < 2.5 / d1:
            t3 = t - 2.25 / d1
            return n1 * t3 * t3 + 0.9375
        t4 = t - 2.625 / d1
        return n1 * t4 * t4 + 0.984375

    @staticmethod
    def _elastic_ease(t: float) -> float:
        if t == 0.0 or t == 1.0:
            return t
        c4 = (2.0 * math.pi) / 3.0
        return -(2.0 ** (10.0 * t - 10.0)) * math.sin((t * 10.0 - 10.75) * c4)

    def compute_transition_value(
        self, event_id: str, delta_time: float,
    ) -> Optional[Dict[str, Any]]:
        event = self._events.get(event_id)
        if event is None:
            return None
        if event.state != TransitionState.TRANSITIONING:
            return {
                "event_id": event_id,
                "value": 1.0 if event.state == TransitionState.COMPLETE else 0.0,
                "state": event.state.value,
            }

        config = self._configs.get(event.config_id)
        if config is None:
            return None

        event.elapsed += delta_time
        duration = max(0.001, config.duration)
        t = min(1.0, event.elapsed / duration)
        value = self._ease_value(t, config.easing)
        event.progress = value

        if t >= 1.0:
            self.complete_transition(event_id)

        return {
            "event_id": event_id,
            "value": round(value, 4),
            "t": round(t, 4),
            "elapsed": round(event.elapsed, 3),
            "duration": config.duration,
            "easing": config.easing.value,
            "state": event.state.value,
        }

    # ---- Query Methods ----

    def get_active_transitions(self) -> List[TransitionEvent]:
        return [self._events[eid] for eid in self._active_event_ids if eid in self._events]

    def get_transition_history(self, limit: int = 20) -> List[TransitionEvent]:
        return self._history[-max(1, min(self.MAX_HISTORY, limit)):]

    def get_event(self, event_id: str) -> Optional[TransitionEvent]:
        return self._events.get(event_id)

    def get_sequence(self, sequence_id: str) -> Optional[TransitionSequence]:
        return self._sequences.get(sequence_id)

    def get_loading_progress(
        self, event_id: str,
    ) -> Optional[LoadingProgress]:
        return self._loading_progress.get(event_id)

    def list_sequences(self) -> List[TransitionSequence]:
        return list(self._sequences.values())

    def list_configs(self) -> List[TransitionConfig]:
        return list(self._configs.values())

    # ---- Stats ----

    def get_stats(self) -> Dict[str, Any]:
        effect_counts: Dict[str, int] = {}
        for evt in self._history[-200:]:
            ef = evt.effect.value
            effect_counts[ef] = effect_counts.get(ef, 0) + 1

        return {
            "total_configs": len(self._configs),
            "total_events": len(self._events),
            "total_sequences": len(self._sequences),
            "active_transitions": len(self._active_event_ids),
            "max_active_transitions": self.MAX_ACTIVE_TRANSITIONS,
            "total_transitions_run": self._total_transitions,
            "total_sequences_run": self._total_sequences_run,
            "history_size": len(self._history),
            "loading_progress_count": len(self._loading_progress),
            "recent_effect_counts": effect_counts,
            "preloaded_scenes": list(self._preload_cache.keys()),
        }

    # ---- Lifecycle ----

    def reset(self) -> None:
        for event_id in list(self._active_event_ids):
            self.cancel_transition(event_id)
        self._configs.clear()
        self._events.clear()
        self._sequences.clear()
        self._loading_progress.clear()
        self._history.clear()
        self._active_event_ids.clear()
        self._preload_cache.clear()
        self._total_transitions = 0
        self._total_sequences_run = 0

    # ---- Internal Helpers ----

    def _init_loading_progress(
        self, event_id: str, scene_name: str,
    ) -> None:
        asset_count = len(self._preload_cache.get(scene_name, []))
        lp = LoadingProgress(
            event_id=event_id,
            total_assets=max(1, asset_count),
        )
        self._loading_progress[event_id] = lp

    def _remove_from_active(self, event_id: str) -> None:
        if event_id in self._active_event_ids:
            self._active_event_ids.remove(event_id)

    def _push_to_history(self, event: TransitionEvent) -> None:
        self._history.append(event)
        while len(self._history) > self.MAX_HISTORY:
            self._history.pop(0)

    def _advance_sequence(
        self, sequence_id: str, completed_event_id: str,
    ) -> None:
        sequence = self._sequences.get(sequence_id)
        if sequence is None or not sequence.is_active:
            return
        if not sequence.auto_advance:
            return

        sequence.current_index += 1

        if sequence.current_index >= len(sequence.config_ids):
            if sequence.looping:
                sequence.current_index = 0
            else:
                sequence.is_active = False
                return

        next_config_id = sequence.config_ids[sequence.current_index]
        event = self.start_transition(next_config_id)
        if event:
            event.sequence_id = sequence_id

    def preload_scene_assets(
        self, scene_name: str, asset_ids: List[str],
    ) -> None:
        self._preload_cache[scene_name] = list(asset_ids)

    def clear_preload_cache(self, scene_name: str = "") -> None:
        if scene_name:
            self._preload_cache.pop(scene_name, None)
        else:
            self._preload_cache.clear()


def get_scene_transition() -> SceneTransitionSystem:
    return SceneTransitionSystem.get_instance()