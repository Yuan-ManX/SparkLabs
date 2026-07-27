"""
SparkLabs Agent - Music Conductor

The AgentMusicConductor is the adaptive music intelligence of the AI-native
game engine. It listens to scene context, narrative tension, player emotions,
and frame architect directives to generate real-time music directives:
tempo, key, mode, intensity, layer activation, and transition style.

Architecture:
  Scene Signals --> LISTEN --> ASSESS --> COMPOSE --> DIRECT --> TRANSITION
  (narrative,     (gather     (evaluate    (select       (emit music     (manage
   intensity,      signals)    emotional   music          directives)     layer
   emotion,                    context)    strategy)                      fades)

The conductor manages:
  - Tempo (60-180 BPM) based on scene intensity
  - Musical key and mode (major/minor/-modal) based on emotion
  - Dynamic layering: base, rhythm, melody, tension, stinger
  - Intensity curves that follow pacing rhythm
  - Smooth transitions between musical states

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class MusicalKey(Enum):
    """Musical keys."""
    C = "C"
    C_SHARP = "C#"
    D = "D"
    D_SHARP = "D#"
    E = "E"
    F = "F"
    F_SHARP = "F#"
    G = "G"
    G_SHARP = "G#"
    A = "A"
    A_SHARP = "A#"
    B = "B"


class MusicalMode(Enum):
    """Musical modes / scales."""
    MAJOR = "major"
    MINOR = "minor"
    DORIAN = "dorian"
    PHRYGIAN = "phrygian"
    LYDIAN = "lydian"
    MIXOLYDIAN = "mixolydian"
    LOCRIAN = "locrian"
    PENTATONIC_MAJOR = "pentatonic_major"
    PENTATONIC_MINOR = "pentatonic_minor"
    WHOLE_TONE = "whole_tone"


class MusicLayer(Enum):
    """Dynamic music layers that can be activated/deactivated."""
    BASE = "base"           # ambient pad / drone
    RHYTHM = "rhythm"       # percussion / beat
    MELODY = "melody"       # lead melody
    HARMONY = "harmony"     # chords / accompaniment
    TENSION = "tension"     # dissonant layer for stress
    STINGER = "stinger"     # short accent for events
    COUNTER = "counter"     # counter-melody


class MusicTransition(Enum):
    """Transition types between musical states."""
    CROSSFADE = "crossfade"
    FILTER_SWEEP = "filter_sweep"
    ADDITIVE = "additive"       # add layers one by one
    SUBTRACTIVE = "subtractive"  # remove layers one by one
    CUT = "cut"
    RISER = "riser"             # build-up then drop
    REVERSE = "reverse"         # play in reverse briefly


class ConductorPhase(Enum):
    """Phases of the music conductor cycle."""
    LISTEN = "listen"
    ASSESS = "assess"
    COMPOSE = "compose"
    DIRECT = "direct"
    TRANSITION = "transition"


class EmotionalValence(Enum):
    """Emotional valence for music selection."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class MusicDirective:
    """A single music directive emitted by the conductor."""
    directive_id: str
    tempo_bpm: int
    key: MusicalKey
    mode: MusicalMode
    intensity: float  # 0.0 = silent, 1.0 = max
    active_layers: List[MusicLayer]
    transition: MusicTransition
    layer_volumes: Dict[str, float]  # layer name -> volume 0-1
    valence: EmotionalValence
    rationale: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConductorStats:
    """Statistics for the music conductor."""
    total_cycles: int = 0
    total_directives_emitted: int = 0
    total_transitions: int = 0
    total_layer_changes: int = 0
    avg_tempo: float = 120.0
    avg_intensity: float = 0.3
    most_used_key: str = "C"
    most_used_mode: str = "major"
    last_cycle_time_ms: float = 0.0
    active: bool = False


@dataclass
class MusicContext:
    """Input context for music decisions."""
    scene_intensity: float = 0.0  # 0.0 = calm, 1.0 = chaotic
    narrative_tension: float = 0.2
    emotional_context: str = "neutral"
    pacing_phase: str = "calm"
    is_combat: bool = False
    is_dialogue: bool = False
    is_exploration: bool = True
    is_boss_fight: bool = False
    is_cutscene: bool = False
    player_health: float = 1.0
    time_of_day: str = "day"


# =============================================================================
# Agent Music Conductor
# =============================================================================

class AgentMusicConductor:
    """
    Singleton agent that generates adaptive music directives.

    The conductor runs a 5-phase cycle:
      1. LISTEN     - Gather scene signals (intensity, emotion, pacing)
      2. ASSESS     - Evaluate emotional valence and musical needs
      3. COMPOSE    - Select tempo, key, mode, and layer strategy
      4. DIRECT     - Emit a structured music directive
      5. TRANSITION - Manage smooth layer transitions

    The conductor responds to the Temporal Director's pacing phase,
    the Story Director's narrative tension, and the Frame Architect's
    scene intensity to create a cohesive audio experience.
    """

    _instance: Optional["AgentMusicConductor"] = None
    _instance_lock = threading.Lock()

    # Tempo mapping by pacing phase
    PACING_TEMPO: Dict[str, Tuple[int, int]] = {
        "calm": (70, 90),
        "building": (90, 120),
        "climax": (130, 170),
        "release": (100, 120),
        "rest": (60, 80),
    }

    # Mode selection by emotional context
    EMOTION_MODE_MAP: Dict[str, List[MusicalMode]] = {
        "neutral": [MusicalMode.MAJOR, MusicalMode.DORIAN, MusicalMode.PENTATONIC_MAJOR],
        "tense": [MusicalMode.MINOR, MusicalMode.PHRYGIAN, MusicalMode.LOCRIAN],
        "joyful": [MusicalMode.MAJOR, MusicalMode.LYDIAN, MusicalMode.PENTATONIC_MAJOR],
        "sad": [MusicalMode.MINOR, MusicalMode.DORIAN, MusicalMode.PENTATONIC_MINOR],
        "fearful": [MusicalMode.MINOR, MusicalMode.LOCRIAN, MusicalMode.WHOLE_TONE],
    }

    # Key selection by time of day
    TIME_KEY_MAP: Dict[str, List[MusicalKey]] = {
        "dawn": [MusicalKey.C, MusicalKey.G, MusicalKey.D],
        "day": [MusicalKey.C, MusicalKey.G, MusicalKey.F, MusicalKey.D],
        "dusk": [MusicalKey.A, MusicalKey.E, MusicalKey.D],
        "night": [MusicalKey.D, MusicalKey.G, MusicalKey.A, MusicalKey.E],
    }

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stats = ConductorStats()
        self._directive_history: Deque[MusicDirective] = deque(maxlen=100)
        self._current_directive: Optional[MusicDirective] = None
        self._context = MusicContext()
        self._cycle_count: int = 0
        self._last_cycle_at: float = 0.0
        self._cycle_interval_s: float = 2.0
        self._active: bool = False
        self._key_usage: Dict[str, int] = {}
        self._mode_usage: Dict[str, int] = {}
        self._layer_states: Dict[MusicLayer, float] = {
            layer: 0.0 for layer in MusicLayer
        }
        # Base layer always on at low volume
        self._layer_states[MusicLayer.BASE] = 0.3

    @classmethod
    def get_instance(cls) -> "AgentMusicConductor":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Phase 1: LISTEN - Gather signals
    # -------------------------------------------------------------------------

    def update_context(self, scene_intensity: Optional[float] = None,
                       narrative_tension: Optional[float] = None,
                       emotional_context: Optional[str] = None,
                       pacing_phase: Optional[str] = None,
                       is_combat: Optional[bool] = None,
                       is_dialogue: Optional[bool] = None,
                       is_exploration: Optional[bool] = None,
                       is_boss_fight: Optional[bool] = None,
                       is_cutscene: Optional[bool] = None,
                       player_health: Optional[float] = None,
                       time_of_day: Optional[str] = None) -> Dict[str, Any]:
        """Update the music context. Returns the updated context."""
        with self._lock:
            ctx = self._context
            if scene_intensity is not None:
                ctx.scene_intensity = max(0.0, min(1.0, float(scene_intensity)))
            if narrative_tension is not None:
                ctx.narrative_tension = max(0.0, min(1.0, float(narrative_tension)))
            if emotional_context is not None:
                ctx.emotional_context = emotional_context
            if pacing_phase is not None:
                ctx.pacing_phase = pacing_phase
            if is_combat is not None:
                ctx.is_combat = bool(is_combat)
            if is_dialogue is not None:
                ctx.is_dialogue = bool(is_dialogue)
            if is_exploration is not None:
                ctx.is_exploration = bool(is_exploration)
            if is_boss_fight is not None:
                ctx.is_boss_fight = bool(is_boss_fight)
            if is_cutscene is not None:
                ctx.is_cutscene = bool(is_cutscene)
            if player_health is not None:
                ctx.player_health = max(0.0, min(1.0, float(player_health)))
            if time_of_day is not None:
                ctx.time_of_day = time_of_day
            return self._context_to_dict(ctx)

    # -------------------------------------------------------------------------
    # Phase 2: ASSESS - Evaluate emotional valence
    # -------------------------------------------------------------------------

    def _assess_valence(self, ctx: MusicContext) -> EmotionalValence:
        """Determine the emotional valence from context."""
        if ctx.emotional_context in ("joyful",):
            return EmotionalValence.POSITIVE
        if ctx.emotional_context in ("sad", "fearful"):
            return EmotionalValence.NEGATIVE
        if ctx.emotional_context == "tense":
            # Tense can be positive (excitement) or negative (fear)
            if ctx.player_health > 0.5:
                return EmotionalValence.MIXED
            return EmotionalValence.NEGATIVE
        return EmotionalValence.NEUTRAL

    def _calculate_intensity(self, ctx: MusicContext) -> float:
        """Calculate the target music intensity (0.0-1.0)."""
        score = 0.0
        score += ctx.scene_intensity * 0.30
        score += ctx.narrative_tension * 0.25
        if ctx.is_combat:
            score += 0.20
        if ctx.is_boss_fight:
            score += 0.15
        score += (1.0 - ctx.player_health) * 0.10
        if ctx.is_cutscene:
            score = max(score, 0.4)  # cutscenes always have some music
        return min(1.0, score)

    # -------------------------------------------------------------------------
    # Phase 3: COMPOSE - Select music strategy
    # -------------------------------------------------------------------------

    def _select_tempo(self, ctx: MusicContext, intensity: float) -> int:
        """Select tempo in BPM based on pacing phase and intensity."""
        phase_key = ctx.pacing_phase if ctx.pacing_phase in self.PACING_TEMPO else "calm"
        tempo_range = self.PACING_TEMPO[phase_key]
        # Bias toward upper range with higher intensity
        bias = intensity
        tempo = int(tempo_range[0] + (tempo_range[1] - tempo_range[0]) * bias)
        # Boss fights push tempo up
        if ctx.is_boss_fight:
            tempo = min(180, tempo + 15)
        # Dialogue pulls tempo down
        if ctx.is_dialogue:
            tempo = max(60, tempo - 20)
        return tempo

    def _select_key(self, ctx: MusicContext) -> MusicalKey:
        """Select musical key based on time of day."""
        time_key = ctx.time_of_day if ctx.time_of_day in self.TIME_KEY_MAP else "day"
        keys = self.TIME_KEY_MAP[time_key]
        return random.choice(keys)

    def _select_mode(self, ctx: MusicContext) -> MusicalMode:
        """Select musical mode based on emotional context."""
        emotion = ctx.emotional_context if ctx.emotional_context in self.EMOTION_MODE_MAP else "neutral"
        modes = self.EMOTION_MODE_MAP[emotion]
        return random.choice(modes)

    def _select_layers(self, ctx: MusicContext, intensity: float) -> List[MusicLayer]:
        """Select which music layers should be active."""
        layers: List[MusicLayer] = [MusicLayer.BASE]

        if intensity > 0.15:
            layers.append(MusicLayer.RHYTHM)
        if intensity > 0.30:
            layers.append(MusicLayer.HARMONY)
        if intensity > 0.45:
            layers.append(MusicLayer.MELODY)
        if intensity > 0.60 or ctx.is_combat:
            layers.append(MusicLayer.TENSION)
        if ctx.is_boss_fight:
            layers.append(MusicLayer.COUNTER)
        if intensity > 0.75:
            layers.append(MusicLayer.STINGER)

        # Dialogue: reduce layers for clarity
        if ctx.is_dialogue:
            layers = [l for l in layers if l not in (MusicLayer.MELODY, MusicLayer.COUNTER, MusicLayer.STINGER)]

        return layers

    def _select_transition(self, prev_directive: Optional[MusicDirective],
                           curr_intensity: float, prev_intensity: float) -> MusicTransition:
        """Select transition type based on intensity change."""
        if prev_directive is None:
            return MusicTransition.CROSSFADE

        if abs(curr_intensity - prev_intensity) < 0.05:
            return MusicTransition.CROSSFADE

        if curr_intensity > prev_intensity:
            # Building up
            if curr_intensity - prev_intensity > 0.3:
                return MusicTransition.RISER
            return MusicTransition.ADDITIVE
        else:
            # Cooling down
            if prev_intensity - curr_intensity > 0.3:
                return MusicTransition.FILTER_SWEEP
            return MusicTransition.SUBTRACTIVE

    def _calculate_layer_volumes(self, layers: List[MusicLayer],
                                  intensity: float, ctx: MusicContext) -> Dict[str, float]:
        """Calculate volume for each active layer."""
        volumes: Dict[str, float] = {}
        for layer in MusicLayer:
            if layer in layers:
                if layer == MusicLayer.BASE:
                    volumes[layer.value] = round(0.3 + intensity * 0.2, 2)
                elif layer == MusicLayer.RHYTHM:
                    volumes[layer.value] = round(0.4 + intensity * 0.4, 2)
                elif layer == MusicLayer.MELODY:
                    volumes[layer.value] = round(0.3 + intensity * 0.3, 2)
                elif layer == MusicLayer.HARMONY:
                    volumes[layer.value] = round(0.2 + intensity * 0.3, 2)
                elif layer == MusicLayer.TENSION:
                    volumes[layer.value] = round(0.3 + intensity * 0.5, 2)
                elif layer == MusicLayer.STINGER:
                    volumes[layer.value] = round(0.5 + intensity * 0.3, 2)
                elif layer == MusicLayer.COUNTER:
                    volumes[layer.value] = round(0.2 + intensity * 0.2, 2)
            else:
                volumes[layer.value] = 0.0
        # Dialogue reduces all non-base volumes
        if ctx.is_dialogue:
            for k in volumes:
                if k != MusicLayer.BASE.value:
                    volumes[k] = round(volumes[k] * 0.5, 2)
        return volumes

    def _build_rationale(self, tempo: int, key: MusicalKey, mode: MusicalMode,
                          intensity: float, layers: List[MusicLayer],
                          ctx: MusicContext) -> str:
        """Build a human-readable rationale."""
        parts: List[str] = []
        parts.append(f"tempo={tempo}bpm")
        parts.append(f"key={key.value} {mode.value}")
        parts.append(f"intensity={round(intensity, 2)}")
        parts.append(f"pacing={ctx.pacing_phase}")
        if ctx.is_combat:
            parts.append("combat")
        if ctx.is_boss_fight:
            parts.append("boss")
        if ctx.is_dialogue:
            parts.append("dialogue")
        if ctx.is_cutscene:
            parts.append("cutscene")
        parts.append(f"layers={len(layers)}")
        return ", ".join(parts)

    # -------------------------------------------------------------------------
    # Phase 4: DIRECT - Emit directive
    # -------------------------------------------------------------------------

    def _compose_directive(self, ctx: MusicContext) -> MusicDirective:
        """Compose a complete music directive from context."""
        intensity = self._calculate_intensity(ctx)
        tempo = self._select_tempo(ctx, intensity)
        key = self._select_key(ctx)
        mode = self._select_mode(ctx)
        layers = self._select_layers(ctx, intensity)

        prev_intensity = 0.0
        if self._current_directive:
            prev_intensity = self._calculate_intensity_from_directive(self._current_directive)

        transition = self._select_transition(self._current_directive, intensity, prev_intensity)
        volumes = self._calculate_layer_volumes(layers, intensity, ctx)
        valence = self._assess_valence(ctx)
        rationale = self._build_rationale(tempo, key, mode, intensity, layers, ctx)

        directive = MusicDirective(
            directive_id=f"music_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
            tempo_bpm=tempo,
            key=key,
            mode=mode,
            intensity=round(intensity, 3),
            active_layers=layers,
            transition=transition,
            layer_volumes=volumes,
            valence=valence,
            rationale=rationale,
        )

        # Track usage
        self._key_usage[key.value] = self._key_usage.get(key.value, 0) + 1
        self._mode_usage[mode.value] = self._mode_usage.get(mode.value, 0) + 1

        return directive

    def _calculate_intensity_from_directive(self, d: MusicDirective) -> float:
        """Extract the intensity from a directive."""
        return d.intensity

    # -------------------------------------------------------------------------
    # Phase 5: TRANSITION - Manage layer fades
    # -------------------------------------------------------------------------

    def _apply_transition(self, directive: MusicDirective,
                          prev_directive: Optional[MusicDirective]) -> None:
        """Apply transition logic and update layer states."""
        if prev_directive is None:
            # First directive: fade in all layers
            for layer in directive.active_layers:
                self._layer_states[layer] = directive.layer_volumes.get(layer.value, 0.5)
            return

        # Track layer changes
        prev_layers = set(prev_directive.active_layers)
        curr_layers = set(directive.active_layers)
        added = curr_layers - prev_layers
        removed = prev_layers - curr_layers

        self._stats.total_layer_changes += len(added) + len(removed)

        if directive.transition == MusicTransition.CUT:
            # Instant switch
            for layer in MusicLayer:
                self._layer_states[layer] = directive.layer_volumes.get(layer.value, 0.0)
        elif directive.transition == MusicTransition.ADDITIVE:
            # Add new layers, keep existing
            for layer in curr_layers:
                self._layer_states[layer] = directive.layer_volumes.get(layer.value, 0.5)
            for layer in removed:
                self._layer_states[layer] = 0.0
        elif directive.transition == MusicTransition.SUBTRACTIVE:
            # Remove layers gradually
            for layer in curr_layers:
                self._layer_states[layer] = directive.layer_volumes.get(layer.value, 0.5)
            for layer in removed:
                self._layer_states[layer] = 0.0
        else:
            # Crossfade / default
            for layer in MusicLayer:
                self._layer_states[layer] = directive.layer_volumes.get(layer.value, 0.0)

        if directive.transition != MusicTransition.CROSSFADE:
            self._stats.total_transitions += 1

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single music conductor cycle.

        Phases: LISTEN -> ASSESS -> COMPOSE -> DIRECT -> TRANSITION
        """
        start_time = time.time()
        with self._lock:
            self._active = True
            phase = ConductorPhase.LISTEN

            # Phase 1: LISTEN - context is already up to date
            ctx = self._context

            # Phase 2: ASSESS
            phase = ConductorPhase.ASSESS
            valence = self._assess_valence(ctx)
            intensity = self._calculate_intensity(ctx)

            # Phase 3: COMPOSE
            phase = ConductorPhase.COMPOSE
            directive = self._compose_directive(ctx)

            # Phase 4: DIRECT
            phase = ConductorPhase.DIRECT
            self._apply_transition(directive, self._current_directive)

            # Phase 5: TRANSITION
            phase = ConductorPhase.TRANSITION

            # Store directive
            self._current_directive = directive
            self._directive_history.append(directive)
            self._stats.total_directives_emitted += 1

            # Update stats
            self._cycle_count += 1
            self._stats.total_cycles = self._cycle_count
            self._stats.avg_tempo = (
                (self._stats.avg_tempo * (self._cycle_count - 1) + directive.tempo_bpm)
                / self._cycle_count
            )
            self._stats.avg_intensity = (
                (self._stats.avg_intensity * (self._cycle_count - 1) + intensity)
                / self._cycle_count
            )
            self._stats.most_used_key = max(self._key_usage, key=self._key_usage.get) if self._key_usage else "C"
            self._stats.most_used_mode = max(self._mode_usage, key=self._mode_usage.get) if self._mode_usage else "major"
            self._stats.active = True
            self._last_cycle_at = time.time()
            self._stats.last_cycle_time_ms = (time.time() - start_time) * 1000

            return {
                "phase": phase.value,
                "intensity": round(intensity, 3),
                "valence": valence.value,
                "directive": self._directive_to_dict(directive),
                "layer_states": {k.value: round(v, 2) for k, v in self._layer_states.items()},
                "cycle": self._cycle_count,
            }

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the music conductor."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "current_context": self._context_to_dict(self._context),
                "current_directive": self._directive_to_dict(self._current_directive) if self._current_directive else None,
                "layer_states": {k.value: round(v, 2) for k, v in self._layer_states.items()},
                "stats": {
                    "total_cycles": self._stats.total_cycles,
                    "total_directives_emitted": self._stats.total_directives_emitted,
                    "total_transitions": self._stats.total_transitions,
                    "total_layer_changes": self._stats.total_layer_changes,
                    "avg_tempo": round(self._stats.avg_tempo, 1),
                    "avg_intensity": round(self._stats.avg_intensity, 3),
                    "most_used_key": self._stats.most_used_key,
                    "most_used_mode": self._stats.most_used_mode,
                    "last_cycle_time_ms": round(self._stats.last_cycle_time_ms, 2),
                    "active": self._stats.active,
                },
            }

    def get_directives(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent music directives."""
        with self._lock:
            history = list(self._directive_history)
            if limit > 0:
                history = history[-limit:]
            return [self._directive_to_dict(d) for d in reversed(history)]

    def get_current_directive(self) -> Optional[Dict[str, Any]]:
        """Get the current active music directive."""
        with self._lock:
            return self._directive_to_dict(self._current_directive) if self._current_directive else None

    def get_layer_states(self) -> Dict[str, Any]:
        """Get the current state of all music layers."""
        with self._lock:
            return {
                "layers": {k.value: round(v, 2) for k, v in self._layer_states.items()},
                "active_count": sum(1 for v in self._layer_states.values() if v > 0.01),
            }

    def get_distribution(self) -> Dict[str, Any]:
        """Get the distribution of keys and modes used."""
        with self._lock:
            total_keys = sum(self._key_usage.values()) or 1
            total_modes = sum(self._mode_usage.values()) or 1
            return {
                "key_usage": dict(self._key_usage),
                "mode_usage": dict(self._mode_usage),
                "key_percentages": {k: round(v / total_keys * 100, 1) for k, v in self._key_usage.items()},
                "mode_percentages": {k: round(v / total_modes * 100, 1) for k, v in self._mode_usage.items()},
            }

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles with simulated context changes."""
        with self._lock:
            emotions = ["neutral", "tense", "joyful", "sad", "fearful"]
            phases = ["calm", "building", "climax", "release", "rest"]
            times = ["dawn", "day", "dusk", "night"]

            for _ in range(cycles):
                self.update_context(
                    scene_intensity=random.uniform(0, 1),
                    narrative_tension=random.uniform(0, 1),
                    emotional_context=random.choice(emotions),
                    pacing_phase=random.choice(phases),
                    is_combat=random.choice([True, False, False]),
                    is_dialogue=random.choice([True, False, False, False]),
                    is_boss_fight=random.choice([True, False, False, False, False]),
                    is_cutscene=random.choice([True, False, False, False]),
                    player_health=random.uniform(0.2, 1.0),
                    time_of_day=random.choice(times),
                )
                self.run_cycle()

            return {
                "cycles_run": cycles,
                "directives_emitted": cycles,
                "final_tempo": self._current_directive.tempo_bpm if self._current_directive else 0,
                "final_intensity": round(self._stats.avg_intensity, 3),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the music conductor to initial state."""
        with self._lock:
            self._stats = ConductorStats()
            self._directive_history.clear()
            self._current_directive = None
            self._context = MusicContext()
            self._cycle_count = 0
            self._last_cycle_at = 0.0
            self._active = False
            self._key_usage.clear()
            self._mode_usage.clear()
            self._layer_states = {layer: 0.0 for layer in MusicLayer}
            self._layer_states[MusicLayer.BASE] = 0.3
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _context_to_dict(self, ctx: MusicContext) -> Dict[str, Any]:
        return {
            "scene_intensity": round(ctx.scene_intensity, 3),
            "narrative_tension": round(ctx.narrative_tension, 3),
            "emotional_context": ctx.emotional_context,
            "pacing_phase": ctx.pacing_phase,
            "is_combat": ctx.is_combat,
            "is_dialogue": ctx.is_dialogue,
            "is_exploration": ctx.is_exploration,
            "is_boss_fight": ctx.is_boss_fight,
            "is_cutscene": ctx.is_cutscene,
            "player_health": round(ctx.player_health, 3),
            "time_of_day": ctx.time_of_day,
        }

    def _directive_to_dict(self, d: MusicDirective) -> Dict[str, Any]:
        return {
            "directive_id": d.directive_id,
            "tempo_bpm": d.tempo_bpm,
            "key": d.key.value,
            "mode": d.mode.value,
            "intensity": d.intensity,
            "active_layers": [l.value for l in d.active_layers],
            "transition": d.transition.value,
            "layer_volumes": d.layer_volumes,
            "valence": d.valence.value,
            "rationale": d.rationale,
            "timestamp": d.timestamp,
        }
