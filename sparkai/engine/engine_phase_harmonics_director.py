"""
SparkLabs Engine - Phase Harmonics Director

The EnginePhaseHarmonicsDirector models how the various phases of the
game world - time of day, weather, emotional atmosphere, social mood,
narrative tension, and ambient energy - form harmonic relationships
that can be in-tune (producing coherent world-states) or discordant
(producing tension and instability).

A game world is not a collection of independent systems running in
parallel - it is a harmonic field where phases resonate with or against
each other. Dawn and hope resonate harmoniously; a storm and joy are
discordant. When the world's phases are in harmony, the world feels
coherent and settled; when they are discordant, the world feels tense
and on the verge of change.

The director treats each phase dimension as an oscillator with its own
frequency and amplitude:
  - Temporal: time of day (dawn, noon, dusk, midnight)
  - Atmospheric: weather (clear, clouded, storm, mist)
  - Emotional: ambient mood (hopeful, tense, melancholic, euphoric)
  - Social: crowd temperament (calm, restless, festive, hostile)
  - Narrative: story tension (rising, peaking, falling, dormant)
  - Vital: ambient life energy (low, moderate, high, overflowing)

When phases with compatible frequencies align, they produce consonance -
the world-state becomes coherent and stable. When incompatible phases
collide, they produce dissonance - the world-state becomes unstable and
primed for transition.

The director models five forces:
  - Tuning: phases are tuned to their base frequencies each cycle
  - Resonance: compatible phases resonate, amplifying each other
  - Modulation: external events modulate phase frequencies/amplitudes
  - Harmonization: resonating phases harmonize into a coherent chord
  - Dissolution: disharmonious combinations dissolve back to base states

This produces a world where the overall feel emerges from the harmonic
interaction of its phases, where a sunny festival morning feels
fundamentally different from a stormy tense midnight, and where the
world's overall state shapes what kinds of events are likely to occur.

Architecture:
  TUNE     ->  RESONATE  ->  MODULATE  ->  HARMONIZE ->  DISSOLVE
  (phases   (compatible   (external    (resonant    (disharmonious
   tuned to  phases        events       phases form   combinations
   base      resonate,     modulate     a coherent    dissolve back
   frequency amplifying    phase        chord that    to base
   each       each other)  frequencies) shapes the    states,
   cycle)                                world-state)  creating
                                                       space for new
                                                       harmony)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class HarmonicsPhase(Enum):
    """Phases of the phase harmonics cycle."""
    TUNE = "tune"               # phases tuned to base frequencies
    RESONATE = "resonate"       # compatible phases resonate
    MODULATE = "modulate"       # events modulate phase frequencies
    HARMONIZE = "harmonize"     # resonant phases form coherent chords
    DISSOLVE = "dissolve"       # disharmony dissolves back to base


class PhaseDimension(Enum):
    """Dimensions of the world's phase state."""
    TEMPORAL = "temporal"       # time of day
    ATMOSPHERIC = "atmospheric"  # weather
    EMOTIONAL = "emotional"     # ambient mood
    SOCIAL = "social"           # crowd temperament
    NARRATIVE = "narrative"     # story tension
    VITAL = "vital"             # ambient life energy


class HarmonicRelation(Enum):
    """How two phases relate harmonically."""
    CONSONANT = "consonant"     # in-tune, amplifying
    DISSONANT = "dissonant"     # out-of-tune, destabilizing
    NEUTRAL = "neutral"         # no significant interaction
    COMPLEMENTARY = "complementary"  # different but enhancing


class ChordState(Enum):
    """State of a harmonic chord (world-state)."""
    FORMING = "forming"         # chord is assembling
    COHERENT = "coherent"       # stable, harmonious chord
    TENSE = "tense"             # mostly consonant with some dissonance
    DISCORDANT = "discordant"   # mostly dissonant, unstable
    DISSOLVING = "dissolving"   # chord is breaking apart
    ABSENT = "absent"           # no chord active


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PhaseOscillator:
    """A single phase dimension oscillating at its own frequency."""
    dimension: PhaseDimension
    frequency: float = 0.5        # oscillation rate (0.0-1.0)
    amplitude: float = 0.5        # current strength (0.0-1.0)
    phase: float = 0.0            # current phase angle (0.0-2*pi)
    base_frequency: float = 0.5   # tuned base frequency
    base_amplitude: float = 0.5   # tuned base amplitude
    modulation_depth: float = 0.0  # how much it's being modulated
    modulation_source: str = ""   # what's modulating it
    last_updated: float = field(default_factory=time.time)


@dataclass
class HarmonicRelationRecord:
    """A record of harmonic relation between two phases."""
    relation_id: str
    phase_a: PhaseDimension
    phase_b: PhaseDimension
    relation: HarmonicRelation
    strength: float               # how strong the relation is (0.0-1.0)
    timestamp: float = field(default_factory=time.time)


@dataclass
class WorldChord:
    """A coherent chord formed by harmonizing phases."""
    chord_id: str
    contributing_phases: List[PhaseDimension] = field(default_factory=list)
    state: ChordState = ChordState.FORMING
    coherence: float = 0.5        # how coherent the chord is (0.0-1.0)
    dissonance: float = 0.0       # accumulated dissonance (0.0-1.0)
    dominant_valence: str = ""    # the overall feel
    formed_at: float = field(default_factory=time.time)
    stability: float = 0.5        # how stable against disruption
    cycles_active: int = 0


@dataclass
class ModulationEvent:
    """An external event that modulates phase frequencies."""
    event_id: str
    source: str                   # what caused the modulation
    target_dimension: PhaseDimension
    frequency_shift: float        # how much frequency changed
    amplitude_shift: float        # how much amplitude changed
    duration: int = 3             # how many cycles it lasts
    applied_at: float = field(default_factory=time.time)


# =============================================================================
# Phase Harmonics Director
# =============================================================================

class EnginePhaseHarmonicsDirector:
    """
    Thread-safe singleton orchestrating phase harmonics across the world.

    Usage:
        director = EnginePhaseHarmonicsDirector.get_instance()
        director.tune_phase(PhaseDimension.TEMPORAL, frequency=0.8, amplitude=0.7)
        director.tune_phase(PhaseDimension.EMOTIONAL, frequency=0.6, amplitude=0.8)
        director.modulate(PhaseDimension.NARRATIVE, freq_shift=0.3, amp_shift=0.2,
                         source="boss_encounter")
        director.cycle()
    """

    _instance: Optional["EnginePhaseHarmonicsDirector"] = None
    _lock = threading.RLock()

    # Base affinity matrix: how compatible two phase dimensions are
    _DIMENSION_AFFINITY = {
        (PhaseDimension.TEMPORAL, PhaseDimension.EMOTIONAL): 0.7,
        (PhaseDimension.TEMPORAL, PhaseDimension.VITAL): 0.6,
        (PhaseDimension.ATMOSPHERIC, PhaseDimension.EMOTIONAL): 0.8,
        (PhaseDimension.ATMOSPHERIC, PhaseDimension.SOCIAL): 0.6,
        (PhaseDimension.EMOTIONAL, PhaseDimension.SOCIAL): 0.85,
        (PhaseDimension.EMOTIONAL, PhaseDimension.NARRATIVE): 0.75,
        (PhaseDimension.SOCIAL, PhaseDimension.NARRATIVE): 0.7,
        (PhaseDimension.NARRATIVE, PhaseDimension.VITAL): 0.5,
        (PhaseDimension.TEMPORAL, PhaseDimension.ATMOSPHERIC): 0.4,
        (PhaseDimension.TEMPORAL, PhaseDimension.NARRATIVE): 0.3,
        (PhaseDimension.ATMOSPHERIC, PhaseDimension.NARRATIVE): 0.55,
        (PhaseDimension.SOCIAL, PhaseDimension.VITAL): 0.65,
    }
    # Phase advance per cycle
    _PHASE_ADVANCE_BASE = 0.15
    # Coherence threshold for chord formation
    _CHORD_FORMATION_THRESHOLD = 0.55
    # Dissonance threshold for dissolution
    _DISSOLUTION_THRESHOLD = 0.7

    def __init__(self) -> None:
        self._oscillators: Dict[PhaseDimension, PhaseOscillator] = {
            dim: PhaseOscillator(dimension=dim) for dim in PhaseDimension
        }
        self._relations: Deque[HarmonicRelationRecord] = deque(maxlen=200)
        self._chords: Dict[str, WorldChord] = {}
        self._active_chord: Optional[WorldChord] = None
        self._modulations: Deque[ModulationEvent] = deque(maxlen=100)
        self._phase: HarmonicsPhase = HarmonicsPhase.TUNE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {
            "total_cycles": 0,
            "total_chords_formed": 0,
            "total_modulations": 0,
            "active_chord_state": "absent",
            "active_chord_coherence": 0.0,
            "active_chord_dissonance": 0.0,
            "avg_frequency": 0.0,
            "avg_amplitude": 0.0,
            "consonant_relations": 0,
            "dissonant_relations": 0,
            "neutral_relations": 0,
            "complementary_relations": 0,
            "chords_dissolved": 0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EnginePhaseHarmonicsDirector":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Phase Management
    # -------------------------------------------------------------------------

    def tune_phase(
        self,
        dimension: PhaseDimension,
        frequency: float = 0.5,
        amplitude: float = 0.5,
        phase: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Tune a phase oscillator to a new base frequency and amplitude."""
        with self._global_lock:
            osc = self._oscillators[dimension]
            osc.base_frequency = max(0.0, min(1.0, frequency))
            osc.base_amplitude = max(0.0, min(1.0, amplitude))
            osc.frequency = osc.base_frequency
            osc.amplitude = osc.base_amplitude
            if phase is not None:
                osc.phase = phase % (2 * math.pi)
            osc.last_updated = time.time()
            self._record_event("phase_tuned", {
                "dimension": dimension.value,
                "frequency": osc.frequency,
                "amplitude": osc.amplitude,
            })
            return {
                "dimension": dimension.value,
                "frequency": osc.frequency,
                "amplitude": osc.amplitude,
                "phase": osc.phase,
            }

    def modulate(
        self,
        dimension: PhaseDimension,
        freq_shift: float = 0.0,
        amp_shift: float = 0.0,
        source: str = "",
        duration: int = 3,
    ) -> Dict[str, Any]:
        """Apply an external modulation to a phase."""
        with self._global_lock:
            osc = self._oscillators[dimension]
            osc.frequency = max(0.0, min(1.0, osc.frequency + freq_shift))
            osc.amplitude = max(0.0, min(1.0, osc.amplitude + amp_shift))
            osc.modulation_depth = min(1.0, abs(freq_shift) + abs(amp_shift))
            osc.modulation_source = source
            event_id = f"mod_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
            self._modulations.append(ModulationEvent(
                event_id=event_id,
                source=source,
                target_dimension=dimension,
                frequency_shift=freq_shift,
                amplitude_shift=amp_shift,
                duration=duration,
            ))
            self._stats["total_modulations"] = len(self._modulations)
            self._record_event("phase_modulated", {
                "dimension": dimension.value,
                "freq_shift": freq_shift,
                "amp_shift": amp_shift,
                "source": source,
            })
            return {
                "event_id": event_id,
                "dimension": dimension.value,
                "new_frequency": osc.frequency,
                "new_amplitude": osc.amplitude,
                "modulation_depth": osc.modulation_depth,
                "source": source,
            }

    def get_phase_state(self, dimension: Optional[PhaseDimension] = None) -> Dict[str, Any]:
        """Get the state of one or all phase oscillators."""
        with self._global_lock:
            if dimension is not None:
                osc = self._oscillators[dimension]
                return {
                    "dimension": osc.dimension.value,
                    "frequency": osc.frequency,
                    "amplitude": osc.amplitude,
                    "phase": osc.phase,
                    "base_frequency": osc.base_frequency,
                    "base_amplitude": osc.base_amplitude,
                    "modulation_depth": osc.modulation_depth,
                    "modulation_source": osc.modulation_source,
                }
            return {
                "phases": [
                    {
                        "dimension": osc.dimension.value,
                        "frequency": osc.frequency,
                        "amplitude": osc.amplitude,
                        "phase": osc.phase,
                        "base_frequency": osc.base_frequency,
                        "base_amplitude": osc.base_amplitude,
                        "modulation_depth": osc.modulation_depth,
                    }
                    for osc in self._oscillators.values()
                ]
            }

    def get_active_chord(self) -> Dict[str, Any]:
        """Get the currently active chord."""
        with self._global_lock:
            if self._active_chord is None:
                return {"active_chord": None}
            return self._serialize_chord(self._active_chord)

    def get_all_chords(self) -> List[Dict[str, Any]]:
        """Get all chords (active and historical)."""
        with self._global_lock:
            return [self._serialize_chord(c) for c in self._chords.values()]

    def get_relations(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Get recent harmonic relations."""
        with self._global_lock:
            rels = list(self._relations)[-limit:]
            return [
                {
                    "relation_id": r.relation_id,
                    "phase_a": r.phase_a.value,
                    "phase_b": r.phase_b.value,
                    "relation": r.relation.value,
                    "strength": r.strength,
                }
                for r in rels
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the director."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple cycles and return the final status."""
        with self._global_lock:
            for _ in range(max(1, cycles)):
                self.cycle()
            return self.get_status()

    def reset(self) -> Dict[str, Any]:
        """Reset the entire director."""
        with self._global_lock:
            for dim in PhaseDimension:
                self._oscillators[dim] = PhaseOscillator(dimension=dim)
            self._relations.clear()
            self._chords.clear()
            self._active_chord = None
            self._modulations.clear()
            self._phase = HarmonicsPhase.TUNE
            self._cycle_count = 0
            self._events_log.clear()
            self._init_stats()
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single phase harmonics cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = HarmonicsPhase.TUNE
            phase_outputs["tune"] = self._phase_tune()
            self._phase = HarmonicsPhase.RESONATE
            phase_outputs["resonate"] = self._phase_resonate()
            self._phase = HarmonicsPhase.MODULATE
            phase_outputs["modulate"] = self._phase_modulate()
            self._phase = HarmonicsPhase.HARMONIZE
            phase_outputs["harmonize"] = self._phase_harmonize()
            self._phase = HarmonicsPhase.DISSOLVE
            phase_outputs["dissolve"] = self._phase_dissolve()
            self._cycle_count += 1
            self._stats["total_cycles"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_tune(self) -> Dict[str, Any]:
        """Tuning phase: oscillators advance and drift toward base."""
        advanced = 0
        for osc in self._oscillators.values():
            # advance phase
            osc.phase = (osc.phase + self._PHASE_ADVANCE_BASE * (0.5 + osc.frequency)) % (2 * math.pi)
            # drift toward base frequency/amplitude (modulations decay)
            drift_rate = 0.05
            osc.frequency += (osc.base_frequency - osc.frequency) * drift_rate
            osc.amplitude += (osc.base_amplitude - osc.amplitude) * drift_rate
            osc.modulation_depth = max(0.0, osc.modulation_depth - 0.03)
            if osc.modulation_depth < 0.01:
                osc.modulation_source = ""
            advanced += 1
        return {
            "oscillators_advanced": advanced,
            "avg_frequency": sum(o.frequency for o in self._oscillators.values()) / len(self._oscillators),
            "avg_amplitude": sum(o.amplitude for o in self._oscillators.values()) / len(self._oscillators),
        }

    def _phase_resonate(self) -> Dict[str, Any]:
        """Resonance phase: compatible phases amplify each other."""
        consonant = 0
        dissonant = 0
        neutral = 0
        complementary = 0
        oscs = list(self._oscillators.values())
        for i in range(len(oscs)):
            for j in range(i + 1, len(oscs)):
                a = oscs[i]
                b = oscs[j]
                # get affinity
                affinity = self._DIMENSION_AFFINITY.get(
                    (a.dimension, b.dimension),
                    self._DIMENSION_AFFINITY.get((b.dimension, a.dimension), 0.3),
                )
                # phase alignment
                phase_diff = abs(a.phase - b.phase)
                alignment = (math.cos(phase_diff) + 1) / 2  # 0.0 to 1.0
                # combined harmonic score
                harmonic_score = affinity * 0.5 + alignment * 0.5
                # determine relation type
                if harmonic_score > 0.6:
                    rel_type = HarmonicRelation.CONSONANT
                    # amplify both
                    amp_boost = 0.03 * harmonic_score
                    a.amplitude = min(1.0, a.amplitude + amp_boost)
                    b.amplitude = min(1.0, b.amplitude + amp_boost)
                    consonant += 1
                elif harmonic_score < 0.3:
                    rel_type = HarmonicRelation.DISSONANT
                    # dampen both
                    amp_decay = 0.02 * (1 - harmonic_score)
                    a.amplitude = max(0.0, a.amplitude - amp_decay)
                    b.amplitude = max(0.0, b.amplitude - amp_decay)
                    dissonant += 1
                elif affinity > 0.6 and alignment < 0.4:
                    rel_type = HarmonicRelation.COMPLEMENTARY
                    complementary += 1
                else:
                    rel_type = HarmonicRelation.NEUTRAL
                    neutral += 1
                # record relation
                rel_id = f"rel_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
                self._relations.append(HarmonicRelationRecord(
                    relation_id=rel_id,
                    phase_a=a.dimension,
                    phase_b=b.dimension,
                    relation=rel_type,
                    strength=harmonic_score,
                ))
        return {
            "consonant": consonant,
            "dissonant": dissonant,
            "neutral": neutral,
            "complementary": complementary,
            "total_relations": consonant + dissonant + neutral + complementary,
        }

    def _phase_modulate(self) -> Dict[str, Any]:
        """Modulation phase: apply active modulations and decay them."""
        applied = 0
        expired = 0
        remaining = []
        for mod in self._modulations:
            if mod.duration <= 0:
                expired += 1
                continue
            osc = self._oscillators[mod.target_dimension]
            # continuous modulation effect (diminishing)
            effect_strength = mod.duration / 3.0  # weaker as it expires
            osc.frequency = max(0.0, min(1.0, osc.frequency + mod.frequency_shift * 0.1 * effect_strength))
            osc.amplitude = max(0.0, min(1.0, osc.amplitude + mod.amplitude_shift * 0.1 * effect_strength))
            mod.duration -= 1
            applied += 1
            if mod.duration > 0:
                remaining.append(mod)
        # rebuild modulations deque
        self._modulations.clear()
        for m in remaining:
            self._modulations.append(m)
        return {
            "modulations_applied": applied,
            "modulations_expired": expired,
            "active_modulations": len(self._modulations),
        }

    def _phase_harmonize(self) -> Dict[str, Any]:
        """Harmonization phase: consonant phases form coherent chords."""
        # compute overall coherence from recent relations
        recent = list(self._relations)[-15:]
        if not recent:
            return {"chord_formed": False, "reason": "no relations"}
        consonant_count = sum(1 for r in recent if r.relation == HarmonicRelation.CONSONANT)
        dissonant_count = sum(1 for r in recent if r.relation == HarmonicRelation.DISSONANT)
        total = len(recent)
        coherence = consonant_count / total if total else 0.0
        dissonance = dissonant_count / total if total else 0.0
        # find contributing phases (those with high amplitude)
        contributing = [
            osc.dimension for osc in self._oscillators.values()
            if osc.amplitude > 0.4
        ]
        chord_formed = False
        chord_reinforced = False
        # check if we should form or reinforce a chord
        if coherence > self._CHORD_FORMATION_THRESHOLD and len(contributing) >= 3:
            if self._active_chord and self._active_chord.state in (ChordState.COHERENT, ChordState.TENSE, ChordState.FORMING):
                # reinforce existing chord
                self._active_chord.coherence = min(1.0, self._active_chord.coherence + 0.03)
                self._active_chord.dissonance = max(0.0, self._active_chord.dissonance - 0.02)
                self._active_chord.cycles_active += 1
                self._active_chord.stability = min(1.0, self._active_chord.stability + 0.02)
                # update state
                if self._active_chord.dissonance > 0.4:
                    self._active_chord.state = ChordState.TENSE
                else:
                    self._active_chord.state = ChordState.COHERENT
                # determine dominant valence
                self._active_chord.dominant_valence = self._compute_dominant_valence()
                chord_reinforced = True
            else:
                # form new chord
                chord_id = f"chord_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
                chord = WorldChord(
                    chord_id=chord_id,
                    contributing_phases=contributing,
                    state=ChordState.FORMING,
                    coherence=coherence,
                    dissonance=dissonance,
                    dominant_valence=self._compute_dominant_valence(),
                    stability=0.5,
                )
                self._chords[chord_id] = chord
                self._active_chord = chord
                chord_formed = True
                self._stats["total_chords_formed"] += 1
                self._record_event("chord_formed", {
                    "chord_id": chord_id,
                    "contributing_phases": [p.value for p in contributing],
                    "coherence": coherence,
                    "dissonance": dissonance,
                })
        elif self._active_chord:
            # chord exists but coherence is dropping
            self._active_chord.dissonance = min(1.0, self._active_chord.dissonance + 0.05)
            self._active_chord.coherence = max(0.0, self._active_chord.coherence - 0.03)
            if self._active_chord.dissonance > 0.5:
                self._active_chord.state = ChordState.TENSE
            if self._active_chord.dissonance > 0.7:
                self._active_chord.state = ChordState.DISCORDANT
        return {
            "chord_formed": chord_formed,
            "chord_reinforced": chord_reinforced,
            "coherence": coherence,
            "dissonance": dissonance,
            "contributing_phases": [p.value for p in contributing],
            "active_chord_state": self._active_chord.state.value if self._active_chord else "absent",
        }

    def _phase_dissolve(self) -> Dict[str, Any]:
        """Dissolution phase: highly dissonant chords dissolve."""
        dissolved = 0
        if self._active_chord:
            if self._active_chord.dissonance > self._DISSOLUTION_THRESHOLD:
                self._active_chord.state = ChordState.DISSOLVING
                self._record_event("chord_dissolved", {
                    "chord_id": self._active_chord.chord_id,
                    "final_dissonance": self._active_chord.dissonance,
                    "cycles_active": self._active_chord.cycles_active,
                })
                self._active_chord = None
                dissolved += 1
                self._stats["chords_dissolved"] += 1
            elif self._active_chord.cycles_active > 0 and self._active_chord.cycles_active % 10 == 0:
                # long-lasting chord slowly fades
                self._active_chord.stability = max(0.0, self._active_chord.stability - 0.05)
                if self._active_chord.stability < 0.1:
                    self._active_chord.state = ChordState.DISSOLVING
                    self._active_chord = None
                    dissolved += 1
                    self._stats["chords_dissolved"] += 1
        return {
            "chords_dissolved": dissolved,
            "active_chord_present": self._active_chord is not None,
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _compute_dominant_valence(self) -> str:
        """Compute the dominant valence from current phase states."""
        total_amp = sum(o.amplitude for o in self._oscillators.values())
        if total_amp < 0.1:
            return "neutral"
        # weight by amplitude
        temporal_w = self._oscillators[PhaseDimension.TEMPORAL].amplitude
        emotional_w = self._oscillators[PhaseDimension.EMOTIONAL].amplitude
        narrative_w = self._oscillators[PhaseDimension.NARRATIVE].amplitude
        vital_w = self._oscillators[PhaseDimension.VITAL].amplitude
        if narrative_w > 0.6 and emotional_w > 0.6:
            return "intense"
        elif vital_w > 0.6 and temporal_w > 0.5:
            return "vibrant"
        elif emotional_w > 0.6:
            return "emotional"
        elif narrative_w > 0.6:
            return "dramatic"
        elif temporal_w > 0.6:
            return "rhythmic"
        else:
            return "balanced"

    def _serialize_chord(self, c: WorldChord) -> Dict[str, Any]:
        return {
            "chord_id": c.chord_id,
            "contributing_phases": [p.value for p in c.contributing_phases],
            "state": c.state.value,
            "coherence": c.coherence,
            "dissonance": c.dissonance,
            "dominant_valence": c.dominant_valence,
            "formed_at": c.formed_at,
            "stability": c.stability,
            "cycles_active": c.cycles_active,
        }

    def _update_stats(self) -> None:
        freqs = [o.frequency for o in self._oscillators.values()]
        amps = [o.amplitude for o in self._oscillators.values()]
        self._stats["avg_frequency"] = sum(freqs) / len(freqs) if freqs else 0.0
        self._stats["avg_amplitude"] = sum(amps) / len(amps) if amps else 0.0
        # count relation types
        recent = list(self._relations)[-15:]
        self._stats["consonant_relations"] = sum(1 for r in recent if r.relation == HarmonicRelation.CONSONANT)
        self._stats["dissonant_relations"] = sum(1 for r in recent if r.relation == HarmonicRelation.DISSONANT)
        self._stats["neutral_relations"] = sum(1 for r in recent if r.relation == HarmonicRelation.NEUTRAL)
        self._stats["complementary_relations"] = sum(1 for r in recent if r.relation == HarmonicRelation.COMPLEMENTARY)
        if self._active_chord:
            self._stats["active_chord_state"] = self._active_chord.state.value
            self._stats["active_chord_coherence"] = self._active_chord.coherence
            self._stats["active_chord_dissonance"] = self._active_chord.dissonance
        else:
            self._stats["active_chord_state"] = "absent"
            self._stats["active_chord_coherence"] = 0.0
            self._stats["active_chord_dissonance"] = 0.0

    def _init_stats(self) -> None:
        self._stats = {
            "total_cycles": 0,
            "total_chords_formed": 0,
            "total_modulations": 0,
            "active_chord_state": "absent",
            "active_chord_coherence": 0.0,
            "active_chord_dissonance": 0.0,
            "avg_frequency": 0.0,
            "avg_amplitude": 0.0,
            "consonant_relations": 0,
            "dissonant_relations": 0,
            "neutral_relations": 0,
            "complementary_relations": 0,
            "chords_dissolved": 0,
            "last_cycle_time_ms": 0.0,
        }

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
