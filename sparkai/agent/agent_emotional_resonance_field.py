"""
SparkLabs Agent - Emotional Resonance Field

The AgentEmotionalResonanceField models NPC emotions as acoustic wave
phenomena rather than discrete states. Each emotion is a frequency that
an NPC emits continuously, and these frequencies propagate through the
social fabric like sound through a medium.

This acoustic metaphor captures emotional dynamics that discrete models
miss: emotions don't just "spread" - they interfere with each other,
form harmonics, create dissonance, and resonate when frequencies align.
Two NPCs feeling joy at the same frequency create a resonance cascade
that amplifies the emotion beyond what either could feel alone. A NPC
feeling anger (sharp, irregular frequency) near one feeling calm (low,
steady frequency) creates dissonance that builds tension.

Core concepts:
  - FREQUENCY    : each emotion type has a characteristic frequency
  - AMPLITUDE    : the intensity of the emotional wave (0.0-1.0)
  - RESONANCE    : when frequencies align, amplitudes multiply
  - DISSONANCE   : when frequencies clash, tension accumulates
  - HARMONICS    : complex emotions formed by frequency combinations
  - DAMPING      : emotional energy dissipates over time
  - COUPLING     : social bonds determine wave transfer efficiency

Emotion frequencies (Hz metaphor):
  JOY       = 528 Hz  (bright, expansive)
  SADNESS   = 174 Hz  (low, heavy)
  ANGER     = 220 Hz  (sharp, piercing)
  FEAR      = 285 Hz  (irregular, tense)
  CALM      = 396 Hz  (steady, grounded)
  EXCITEMENT= 639 Hz  (rapid, energetic)
  LOVE      = 852 Hz  (warm, enveloping)
  DISGUST   = 333 Hz  (grating, repulsive)

Wave interference types:
  CONSTRUCTIVE  : aligned frequencies amplify each other
  DESTRUCTIVE   : opposing frequencies cancel each other
  BEAT          : close frequencies create oscillating intensity
  HARMONIC      : integer-ratio frequencies form stable chords

Architecture:
  EMIT      ->  PROPAGATE  ->  RESONATE   ->  DAMPEN   ->  BALANCE
  (NPCs        (waves travel   (interference    (energy     (field
   emit         through social   patterns form    dissipates  reaches
   emotional    network)         and cascade)     over time)  equilibrium
   waves)                                          or shifts)

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
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class EmotionType(Enum):
    """Core emotion types with characteristic frequencies."""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    CALM = "calm"
    EXCITEMENT = "excitement"
    LOVE = "love"
    DISGUST = "disgust"


class ResonancePhase(Enum):
    """Phases of the resonance field cycle."""
    EMIT = "emit"
    PROPAGATE = "propagate"
    RESONATE = "resonate"
    DAMPEN = "dampen"
    BALANCE = "balance"


class InterferenceType(Enum):
    """Types of wave interference between emotional frequencies."""
    CONSTRUCTIVE = "constructive"    # aligned frequencies amplify
    DESTRUCTIVE = "destructive"      # opposing frequencies cancel
    BEAT = "beat"                    # close frequencies oscillate
    HARMONIC = "harmonic"            # integer-ratio frequencies form chords
    NEUTRAL = "neutral"              # no significant interaction


class ResonanceEvent(Enum):
    """Events that can occur during resonance."""
    CASCADE = "cascade"              # resonance amplification cascade
    CANCELLATION = "cancellation"    # destructive interference
    CHORD_FORMED = "chord_formed"    # harmonic chord created
    DISSONANCE_PEAK = "dissonance_peak"  # maximum tension reached
    FIELD_SHIFT = "field_shift"      # dominant emotion changed


# =============================================================================
# Emotion Frequency Table
# =============================================================================

# Characteristic frequencies for each emotion type (in metaphorical Hz)
EMOTION_FREQUENCIES: Dict[EmotionType, float] = {
    EmotionType.JOY: 528.0,
    EmotionType.SADNESS: 174.0,
    EmotionType.ANGER: 220.0,
    EmotionType.FEAR: 285.0,
    EmotionType.CALM: 396.0,
    EmotionType.EXCITEMENT: 639.0,
    EmotionType.LOVE: 852.0,
    EmotionType.DISGUST: 333.0,
}

# Emotion compatibility matrix for interference calculation
# (emotion_a, emotion_b) -> (interference_type, strength)
EMOTION_INTERFERENCE: Dict[Tuple[EmotionType, EmotionType], Tuple[InterferenceType, float]] = {
    (EmotionType.JOY, EmotionType.LOVE): (InterferenceType.HARMONIC, 0.8),
    (EmotionType.JOY, EmotionType.EXCITEMENT): (InterferenceType.CONSTRUCTIVE, 0.7),
    (EmotionType.JOY, EmotionType.SADNESS): (InterferenceType.DESTRUCTIVE, 0.6),
    (EmotionType.JOY, EmotionType.CALM): (InterferenceType.BEAT, 0.3),
    (EmotionType.JOY, EmotionType.ANGER): (InterferenceType.DESTRUCTIVE, 0.5),
    (EmotionType.SADNESS, EmotionType.FEAR): (InterferenceType.CONSTRUCTIVE, 0.4),
    (EmotionType.SADNESS, EmotionType.CALM): (InterferenceType.HARMONIC, 0.5),
    (EmotionType.SADNESS, EmotionType.LOVE): (InterferenceType.BEAT, 0.3),
    (EmotionType.ANGER, EmotionType.FEAR): (InterferenceType.CONSTRUCTIVE, 0.6),
    (EmotionType.ANGER, EmotionType.DISGUST): (InterferenceType.CONSTRUCTIVE, 0.5),
    (EmotionType.ANGER, EmotionType.CALM): (InterferenceType.DESTRUCTIVE, 0.7),
    (EmotionType.FEAR, EmotionType.EXCITEMENT): (InterferenceType.BEAT, 0.4),
    (EmotionType.CALM, EmotionType.LOVE): (InterferenceType.HARMONIC, 0.6),
    (EmotionType.CALM, EmotionType.EXCITEMENT): (InterferenceType.DESTRUCTIVE, 0.4),
    (EmotionType.EXCITEMENT, EmotionType.LOVE): (InterferenceType.CONSTRUCTIVE, 0.5),
    (EmotionType.DISGUST, EmotionType.FEAR): (InterferenceType.CONSTRUCTIVE, 0.3),
    (EmotionType.DISGUST, EmotionType.LOVE): (InterferenceType.DESTRUCTIVE, 0.6),
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class EmotionalWave:
    """A single emotional wave emitted by an NPC."""
    wave_id: str
    npc_id: str
    emotion: EmotionType
    frequency: float
    amplitude: float              # 0.0-1.0, intensity of the wave
    phase: float                  # wave phase in radians
    timestamp: float
    # How far this wave has propagated (hop count)
    propagation_hops: int = 0
    # Whether this wave is still active
    active: bool = True


@dataclass
class SocialCoupling:
    """A social bond between two NPCs that determines wave transfer."""
    source_id: str
    target_id: str
    coupling_strength: float      # 0.0-1.0, how efficiently waves transfer
    # Whether the coupling amplifies or dampens
    is_amplifier: bool = True


@dataclass
class ResonanceInteraction:
    """A recorded interference between two emotional waves."""
    interaction_id: str
    wave_a_id: str
    wave_b_id: str
    npc_a_id: str
    npc_b_id: str
    emotion_a: EmotionType
    emotion_b: EmotionType
    interference: InterferenceType
    strength: float
    # Resulting amplitude change
    amplitude_delta: float
    timestamp: float


@dataclass
class EmotionalChord:
    """A stable harmonic combination of multiple emotions."""
    chord_id: str
    npc_id: str
    emotions: List[EmotionType]
    # The dominant frequency of the chord
    root_frequency: float
    # Chord harmony score (0.0-1.0)
    harmony: float
    # How stable the chord is
    stability: float
    timestamp: float


@dataclass
class NPCEmotionalState:
    """The emotional resonance state of a single NPC."""
    npc_id: str
    # Active emotional frequencies being emitted
    active_emotions: Dict[EmotionType, float]  # emotion -> amplitude
    # Dominant emotion (highest amplitude)
    dominant_emotion: Optional[EmotionType] = None
    # Emotional tension from dissonance (0.0-1.0)
    dissonance_level: float = 0.0
    # Emotional harmony from constructive interference (0.0-1.0)
    harmony_level: float = 0.0
    # Resonance factor (how much the NPC's emotions are being amplified)
    resonance_factor: float = 1.0
    # Couplings to other NPCs
    couplings: List[SocialCoupling] = field(default_factory=list)
    # Active chords
    chords: List[EmotionalChord] = field(default_factory=list)
    # Total waves emitted
    waves_emitted: int = 0
    # Total interactions experienced
    interactions_received: int = 0
    last_updated: float = field(default_factory=time.time)


@dataclass
class ResonanceFieldStats:
    """Aggregate statistics for the resonance field."""
    total_npcs: int = 0
    total_waves_emitted: int = 0
    total_interactions: int = 0
    total_cascades: int = 0
    total_cancellations: int = 0
    total_chords_formed: int = 0
    total_field_shifts: int = 0
    avg_dissonance: float = 0.0
    avg_harmony: float = 0.0
    avg_resonance: float = 1.0
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Agent Emotional Resonance Field
# =============================================================================

class AgentEmotionalResonanceField:
    """
    Singleton agent that models NPC emotions as acoustic resonance fields
    where emotional frequencies propagate, interfere, and form harmonics.

    The field runs a 5-phase cycle:
      1. EMIT       - NPCs emit emotional waves at their characteristic frequencies
      2. PROPAGATE  - Waves travel through the social network via couplings
      3. RESONATE   - Wave interference creates resonance, dissonance, and chords
      4. DAMPEN     - Emotional energy dissipates over time
      5. BALANCE    - The field reaches equilibrium or undergoes a shift

    The acoustic metaphor ensures emotional dynamics feel organic: emotions
    don't flip like switches, they resonate and interfere like sound waves
    in a shared medium.
    """

    _instance: Optional["AgentEmotionalResonanceField"] = None
    _instance_lock = threading.Lock()

    # Configuration
    MAX_NPCS = 200
    MAX_ACTIVE_WAVES = 500
    MAX_INTERACTION_HISTORY = 200
    MAX_CHORD_HISTORY = 100
    MAX_CASCADE_DEPTH = 3
    MAX_COUPLINGS_PER_NPC = 10
    # Wave amplitude decay per propagation hop
    PROPAGATION_DECAY = 0.15
    # Natural damping per cycle
    NATURAL_DAMPING = 0.05
    # Minimum amplitude for a wave to remain active
    MIN_AMPLITUDE = 0.02
    # Maximum amplitude
    MAX_AMPLITUDE = 1.0
    # Resonance amplification factor
    RESONANCE_GAIN = 0.2
    # Dissonance accumulation rate
    DISSONANCE_RATE = 0.1
    # Dissonance decay rate
    DISSONANCE_DECAY = 0.03
    # Harmony decay rate
    HARMONY_DECAY = 0.04
    # Chord formation threshold (harmony must exceed this)
    CHORD_THRESHOLD = 0.6
    # Field shift threshold (dominant emotion must change by this much)
    FIELD_SHIFT_THRESHOLD = 0.15

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._npcs: Dict[str, NPCEmotionalState] = {}
        self._active_waves: Deque[EmotionalWave] = deque(maxlen=self.MAX_ACTIVE_WAVES)
        self._interaction_history: Deque[ResonanceInteraction] = deque(
            maxlen=self.MAX_INTERACTION_HISTORY
        )
        self._chord_history: Deque[EmotionalChord] = deque(
            maxlen=self.MAX_CHORD_HISTORY
        )
        self._stats = ResonanceFieldStats()
        self._cycle_count: int = 0
        self._active: bool = False

    @classmethod
    def get_instance(cls) -> "AgentEmotionalResonanceField":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # NPC Management
    # -------------------------------------------------------------------------

    def register_npc(self, npc_id: str,
                     initial_emotions: Optional[Dict[str, float]] = None,
                     ) -> Dict[str, Any]:
        """Register a new NPC in the resonance field."""
        with self._lock:
            if npc_id in self._npcs:
                return {"error": f"NPC already registered: {npc_id}"}
            if len(self._npcs) >= self.MAX_NPCS:
                return {"error": "Maximum NPCs reached"}

            state = NPCEmotionalState(npc_id=npc_id, active_emotions={})

            # Set initial emotional frequencies
            if initial_emotions:
                for emo_str, amp in initial_emotions.items():
                    try:
                        emo = EmotionType(emo_str)
                        amplitude = max(0.0, min(self.MAX_AMPLITUDE, float(amp)))
                        if amplitude > 0:
                            state.active_emotions[emo] = amplitude
                    except (ValueError, TypeError):
                        continue

            # If no emotions set, seed with a default calm state
            if not state.active_emotions:
                state.active_emotions[EmotionType.CALM] = 0.3

            # Determine dominant emotion
            if state.active_emotions:
                state.dominant_emotion = max(
                    state.active_emotions, key=state.active_emotions.get
                )

            self._npcs[npc_id] = state
            self._stats.total_npcs = len(self._npcs)
            return self._npc_to_dict(state)

    def get_npc(self, npc_id: str) -> Dict[str, Any]:
        """Get the emotional state of an NPC."""
        with self._lock:
            state = self._npcs.get(npc_id)
            if state is None:
                return {"error": f"NPC not found: {npc_id}"}
            return self._npc_to_dict(state)

    def list_npcs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List NPCs in the resonance field."""
        with self._lock:
            results = [self._npc_to_dict(s) for s in self._npcs.values()]
            results.sort(key=lambda d: d.get("last_updated", 0), reverse=True)
            return results[:limit]

    def remove_npc(self, npc_id: str) -> Dict[str, Any]:
        """Remove an NPC from the field."""
        with self._lock:
            if npc_id not in self._npcs:
                return {"removed": False}
            # Remove couplings pointing to this NPC
            for s in self._npcs.values():
                s.couplings = [c for c in s.couplings if c.target_id != npc_id]
            del self._npcs[npc_id]
            self._stats.total_npcs = len(self._npcs)
            return {"removed": True, "npc_id": npc_id}

    # -------------------------------------------------------------------------
    # Social Coupling Management
    # -------------------------------------------------------------------------

    def couple_npcs(self, source_id: str, target_id: str,
                    coupling_strength: float = 0.5,
                    is_amplifier: bool = True) -> Dict[str, Any]:
        """Create a social coupling between two NPCs."""
        with self._lock:
            source = self._npcs.get(source_id)
            if source is None:
                return {"error": f"Source NPC not found: {source_id}"}
            if target_id not in self._npcs:
                return {"error": f"Target NPC not found: {target_id}"}
            if source_id == target_id:
                return {"error": "Cannot couple NPC to itself"}
            if len(source.couplings) >= self.MAX_COUPLINGS_PER_NPC:
                return {"error": "Maximum couplings reached for source NPC"}

            # Check if coupling already exists
            for c in source.couplings:
                if c.target_id == target_id:
                    c.coupling_strength = max(0.0, min(1.0, coupling_strength))
                    c.is_amplifier = is_amplifier
                    return {"coupling": self._coupling_to_dict(c)}

            coupling = SocialCoupling(
                source_id=source_id,
                target_id=target_id,
                coupling_strength=max(0.0, min(1.0, coupling_strength)),
                is_amplifier=is_amplifier,
            )
            source.couplings.append(coupling)
            return {"coupling": self._coupling_to_dict(coupling)}

    def uncouple_npcs(self, source_id: str, target_id: str) -> Dict[str, Any]:
        """Remove a social coupling between two NPCs."""
        with self._lock:
            source = self._npcs.get(source_id)
            if source is None:
                return {"error": f"Source NPC not found: {source_id}"}
            original_len = len(source.couplings)
            source.couplings = [c for c in source.couplings if c.target_id != target_id]
            removed = original_len - len(source.couplings)
            return {"removed": removed, "source_id": source_id, "target_id": target_id}

    def get_couplings(self, npc_id: str) -> Dict[str, Any]:
        """Get all couplings for an NPC."""
        with self._lock:
            state = self._npcs.get(npc_id)
            if state is None:
                return {"error": f"NPC not found: {npc_id}"}
            return {
                "npc_id": npc_id,
                "couplings": [self._coupling_to_dict(c) for c in state.couplings],
                "total": len(state.couplings),
            }

    # -------------------------------------------------------------------------
    # Emotion Emission
    # -------------------------------------------------------------------------

    def emit_emotion(self, npc_id: str, emotion: str,
                     amplitude: float = 0.5) -> Dict[str, Any]:
        """Emit an emotional wave from an NPC."""
        with self._lock:
            state = self._npcs.get(npc_id)
            if state is None:
                return {"error": f"NPC not found: {npc_id}"}
            try:
                emo = EmotionType(emotion)
            except ValueError:
                return {"error": f"Unknown emotion: {emotion}"}

            amp = max(0.0, min(self.MAX_AMPLITUDE, float(amplitude)))
            freq = EMOTION_FREQUENCIES.get(emo, 400.0)

            # Create the wave
            wave = EmotionalWave(
                wave_id=f"wave_{npc_id}_{emo.value}_{int(time.time() * 1000)}",
                npc_id=npc_id,
                emotion=emo,
                frequency=freq,
                amplitude=amp,
                phase=random.uniform(0, 2 * math.pi),
                timestamp=time.time(),
            )
            self._active_waves.append(wave)
            state.waves_emitted += 1

            # Update NPC's active emotions
            state.active_emotions[emo] = amp

            # Recompute dominant emotion
            state.dominant_emotion = max(
                state.active_emotions, key=state.active_emotions.get
            )
            state.last_updated = time.time()

            return {
                "wave_id": wave.wave_id,
                "npc_id": npc_id,
                "emotion": emo.value,
                "frequency": freq,
                "amplitude": amp,
            }

    # -------------------------------------------------------------------------
    # Resonance Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single resonance field cycle.

        Phases: EMIT -> PROPAGATE -> RESONATE -> DAMPEN -> BALANCE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: EMIT - NPCs naturally emit their active emotions
            phase = ResonancePhase.EMIT
            emit_info = self._emit_phase()

            # Phase 2: PROPAGATE - Waves travel through couplings
            phase = ResonancePhase.PROPAGATE
            propagate_info = self._propagate_phase()

            # Phase 3: RESONATE - Interference patterns form
            phase = ResonancePhase.RESONATE
            resonate_info = self._resonate_phase()

            # Phase 4: DAMPEN - Energy dissipates
            phase = ResonancePhase.DAMPEN
            dampen_info = self._dampen_phase()

            # Phase 5: BALANCE - Field reaches equilibrium or shifts
            phase = ResonancePhase.BALANCE
            balance_info = self._balance_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "emit": emit_info,
                "propagate": propagate_info,
                "resonate": resonate_info,
                "dampen": dampen_info,
                "balance": balance_info,
                "total_npcs": len(self._npcs),
                "active_waves": len(self._active_waves),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _emit_phase(self) -> Dict[str, Any]:
        """Phase 1: NPCs emit waves for their active emotions."""
        emitted = 0
        for npc_id, state in self._npcs.items():
            for emo, amp in list(state.active_emotions.items()):
                if amp < self.MIN_AMPLITUDE:
                    continue
                # Only emit with some probability to avoid wave explosion
                if random.random() < 0.3:
                    freq = EMOTION_FREQUENCIES.get(emo, 400.0)
                    wave = EmotionalWave(
                        wave_id=f"wave_{npc_id}_{emo.value}_{int(time.time()*1000)}_{random.randint(0,999)}",
                        npc_id=npc_id,
                        emotion=emo,
                        frequency=freq,
                        amplitude=amp,
                        phase=random.uniform(0, 2 * math.pi),
                        timestamp=time.time(),
                    )
                    self._active_waves.append(wave)
                    state.waves_emitted += 1
                    emitted += 1
        self._stats.total_waves_emitted += emitted
        return {"waves_emitted": emitted, "total_active": len(self._active_waves)}

    def _propagate_phase(self) -> Dict[str, Any]:
        """Phase 2: Waves propagate through social couplings."""
        propagated = 0
        new_waves: List[EmotionalWave] = []

        for wave in list(self._active_waves):
            if not wave.active or wave.propagation_hops >= self.MAX_CASCADE_DEPTH:
                continue
            source = self._npcs.get(wave.npc_id)
            if source is None:
                continue

            for coupling in source.couplings:
                target_state = self._npcs.get(coupling.target_id)
                if target_state is None:
                    continue

                # Calculate transferred amplitude
                transfer_factor = coupling.coupling_strength
                if not coupling.is_amplifier:
                    transfer_factor = -transfer_factor

                new_amp = wave.amplitude * transfer_factor * (1.0 - self.PROPAGATION_DECAY)
                new_amp = abs(new_amp)

                if new_amp < self.MIN_AMPLITUDE:
                    continue

                # Create propagated wave
                propagated_wave = EmotionalWave(
                    wave_id=f"wave_{coupling.target_id}_{wave.emotion.value}_{int(time.time()*1000)}_{random.randint(0,999)}",
                    npc_id=coupling.target_id,
                    emotion=wave.emotion,
                    frequency=wave.frequency,
                    amplitude=min(self.MAX_AMPLITUDE, new_amp),
                    phase=wave.phase + random.uniform(-0.5, 0.5),
                    timestamp=time.time(),
                    propagation_hops=wave.propagation_hops + 1,
                )
                new_waves.append(propagated_wave)
                propagated += 1

                # Update target NPC's emotional state
                current = target_state.active_emotions.get(wave.emotion, 0.0)
                # Constructive if amplifier, destructive if dampener
                if coupling.is_amplifier:
                    target_state.active_emotions[wave.emotion] = min(
                        self.MAX_AMPLITUDE, current + new_amp * 0.1
                    )
                else:
                    target_state.active_emotions[wave.emotion] = max(
                        0.0, current - new_amp * 0.1
                    )

                target_state.interactions_received += 1

        for w in new_waves:
            self._active_waves.append(w)

        return {"waves_propagated": propagated, "total_active": len(self._active_waves)}

    def _resonate_phase(self) -> Dict[str, Any]:
        """Phase 3: Wave interference creates resonance, dissonance, and chords."""
        interactions: List[ResonanceInteraction] = []
        cascades = 0
        cancellations = 0
        chords_formed = 0

        # Group active waves by NPC
        waves_by_npc: Dict[str, List[EmotionalWave]] = {}
        for w in self._active_waves:
            if w.active:
                waves_by_npc.setdefault(w.npc_id, []).append(w)

        for npc_id, waves in waves_by_npc.items():
            state = self._npcs.get(npc_id)
            if state is None:
                continue

            # Check all pairs of waves at the same NPC
            for i in range(len(waves)):
                for j in range(i + 1, len(waves)):
                    w_a = waves[i]
                    w_b = waves[j]

                    # Look up interference type
                    key = tuple(sorted([w_a.emotion, w_b.emotion], key=lambda e: e.value))
                    interference_info = EMOTION_INTERFERENCE.get(
                        (key[0], key[1])
                    ) or EMOTION_INTERFERENCE.get(
                        (key[1], key[0])
                    )

                    if interference_info is None:
                        continue

                    interference_type, strength = interference_info

                    # Calculate amplitude delta
                    if interference_type == InterferenceType.CONSTRUCTIVE:
                        delta = strength * self.RESONANCE_GAIN * min(
                            w_a.amplitude, w_b.amplitude
                        )
                        state.harmony_level = min(
                            1.0, state.harmony_level + delta * 0.1
                        )
                        if strength > 0.6:
                            cascades += 1
                            self._stats.total_cascades += 1
                    elif interference_type == InterferenceType.DESTRUCTIVE:
                        delta = -strength * self.RESONANCE_GAIN * min(
                            w_a.amplitude, w_b.amplitude
                        )
                        state.dissonance_level = min(
                            1.0, state.dissonance_level + strength * self.DISSONANCE_RATE
                        )
                        if strength > 0.5:
                            cancellations += 1
                            self._stats.total_cancellations += 1
                    elif interference_type == InterferenceType.BEAT:
                        delta = strength * 0.05 * math.sin(time.time())
                    elif interference_type == InterferenceType.HARMONIC:
                        delta = strength * self.RESONANCE_GAIN * 0.5
                        state.harmony_level = min(
                            1.0, state.harmony_level + delta * 0.15
                        )
                    else:
                        delta = 0.0

                    # Apply delta to both waves
                    w_a.amplitude = max(
                        self.MIN_AMPLITUDE,
                        min(self.MAX_AMPLITUDE, w_a.amplitude + delta)
                    )
                    w_b.amplitude = max(
                        self.MIN_AMPLITUDE,
                        min(self.MAX_AMPLITUDE, w_b.amplitude + delta)
                    )

                    # Record interaction
                    interaction = ResonanceInteraction(
                        interaction_id=f"int_{int(time.time()*1000)}_{random.randint(0,9999)}",
                        wave_a_id=w_a.wave_id,
                        wave_b_id=w_b.wave_id,
                        npc_a_id=w_a.npc_id,
                        npc_b_id=w_b.npc_id,
                        emotion_a=w_a.emotion,
                        emotion_b=w_b.emotion,
                        interference=interference_type,
                        strength=strength,
                        amplitude_delta=delta,
                        timestamp=time.time(),
                    )
                    interactions.append(interaction)

            # Check for chord formation
            if state.harmony_level > self.CHORD_THRESHOLD:
                active_emos = [
                    e for e, a in state.active_emotions.items()
                    if a > self.MIN_AMPLITUDE
                ]
                if len(active_emos) >= 2:
                    chord = EmotionalChord(
                        chord_id=f"chord_{npc_id}_{int(time.time()*1000)}",
                        npc_id=npc_id,
                        emotions=active_emos[:4],
                        root_frequency=EMOTION_FREQUENCIES.get(active_emos[0], 400.0),
                        harmony=state.harmony_level,
                        stability=min(1.0, state.harmony_level * 0.8),
                        timestamp=time.time(),
                    )
                    state.chords.append(chord)
                    self._chord_history.append(chord)
                    chords_formed += 1
                    self._stats.total_chords_formed += 1

        # Store interactions
        for inter in interactions:
            self._interaction_history.append(inter)
        self._stats.total_interactions += len(interactions)

        return {
            "interactions": len(interactions),
            "cascades": cascades,
            "cancellations": cancellations,
            "chords_formed": chords_formed,
        }

    def _dampen_phase(self) -> Dict[str, Any]:
        """Phase 4: Emotional energy dissipates over time."""
        damped = 0
        for wave in list(self._active_waves):
            wave.amplitude -= self.NATURAL_DAMPING
            if wave.amplitude < self.MIN_AMPLITUDE:
                wave.active = False
                damped += 1

        # Remove inactive waves
        self._active_waves = deque(
            (w for w in self._active_waves if w.active),
            maxlen=self.MAX_ACTIVE_WAVES
        )

        # Dampen NPC emotional states
        for state in self._npcs.values():
            for emo in list(state.active_emotions.keys()):
                state.active_emotions[emo] = max(
                    0.0, state.active_emotions[emo] - self.NATURAL_DAMPING * 0.5
                )
                if state.active_emotions[emo] < self.MIN_AMPLITUDE:
                    del state.active_emotions[emo]

            # Decay dissonance and harmony
            state.dissonance_level = max(
                0.0, state.dissonance_level - self.DISSONANCE_DECAY
            )
            state.harmony_level = max(
                0.0, state.harmony_level - self.HARMONY_DECAY
            )

            # Update dominant emotion
            if state.active_emotions:
                state.dominant_emotion = max(
                    state.active_emotions, key=state.active_emotions.get
                )
            else:
                state.dominant_emotion = None

        return {"waves_damped": damped, "remaining_active": len(self._active_waves)}

    def _balance_phase(self) -> Dict[str, Any]:
        """Phase 5: The field reaches equilibrium or undergoes shifts."""
        shifts = 0
        for npc_id, state in self._npcs.items():
            old_dominant = state.dominant_emotion
            if state.active_emotions:
                new_dominant = max(
                    state.active_emotions, key=state.active_emotions.get
                )
                if old_dominant != new_dominant:
                    old_amp = state.active_emotions.get(old_dominant, 0.0) if old_dominant else 0.0
                    new_amp = state.active_emotions.get(new_dominant, 0.0)
                    if abs(new_amp - old_amp) > self.FIELD_SHIFT_THRESHOLD:
                        shifts += 1
                        self._stats.total_field_shifts += 1
                    state.dominant_emotion = new_dominant
            else:
                state.dominant_emotion = None

            # Compute resonance factor
            if state.harmony_level > 0:
                state.resonance_factor = 1.0 + state.harmony_level * 0.5
            elif state.dissonance_level > 0:
                state.resonance_factor = 1.0 - state.dissonance_level * 0.3
            else:
                state.resonance_factor = 1.0

        return {"field_shifts": shifts, "total_npcs": len(self._npcs)}

    # -------------------------------------------------------------------------
    # Simulation and Status
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles in sequence and seed sample data if empty."""
        with self._lock:
            # Seed sample NPCs if field is empty
            if not self._npcs:
                self._seed_sample_data()

            last_cycle: Optional[Dict[str, Any]] = None
            for _ in range(cycles):
                # Randomly emit emotions during simulation
                if self._npcs and random.random() < 0.4:
                    npc_id = random.choice(list(self._npcs.keys()))
                    emo = random.choice(list(EmotionType))
                    self.emit_emotion(npc_id, emo.value, random.uniform(0.3, 0.8))
                last_cycle = self.run_cycle()

            return {
                "cycles_run": cycles,
                "last_cycle": last_cycle,
                "final_stats": self._stats_to_dict(),
                "status": self.get_status(),
            }

    def _seed_sample_data(self) -> None:
        """Seed the field with sample NPCs and couplings."""
        sample_npcs = [
            ("npc_hero", {"joy": 0.4, "excitement": 0.3}),
            ("npc_mentor", {"calm": 0.5, "love": 0.2}),
            ("npc_rival", {"anger": 0.4, "fear": 0.2}),
            ("npc_ally", {"joy": 0.3, "love": 0.3}),
            ("npc_villain", {"anger": 0.5, "disgust": 0.3}),
        ]
        for npc_id, emotions in sample_npcs:
            self.register_npc(npc_id, emotions)

        # Create couplings
        self.couple_npcs("npc_hero", "npc_mentor", 0.7, True)
        self.couple_npcs("npc_hero", "npc_ally", 0.8, True)
        self.couple_npcs("npc_hero", "npc_rival", 0.5, False)
        self.couple_npcs("npc_rival", "npc_villain", 0.6, True)
        self.couple_npcs("npc_mentor", "npc_ally", 0.4, True)

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the resonance field."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "total_npcs": len(self._npcs),
                "active_waves": len(self._active_waves),
                "stats": self._stats_to_dict(),
            }

    def get_interactions(self, npc_id: Optional[str] = None,
                         limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent resonance interactions."""
        with self._lock:
            results = []
            for inter in self._interaction_history:
                if npc_id and inter.npc_a_id != npc_id and inter.npc_b_id != npc_id:
                    continue
                results.append(self._interaction_to_dict(inter))
            return results[:limit]

    def get_chords(self, npc_id: Optional[str] = None,
                   limit: int = 20) -> List[Dict[str, Any]]:
        """Get emotional chords."""
        with self._lock:
            results = []
            for chord in self._chord_history:
                if npc_id and chord.npc_id != npc_id:
                    continue
                results.append(self._chord_to_dict(chord))
            return results[:limit]

    def reset(self) -> Dict[str, Any]:
        """Reset the resonance field to initial state."""
        with self._lock:
            self._npcs.clear()
            self._active_waves.clear()
            self._interaction_history.clear()
            self._chord_history.clear()
            self._stats = ResonanceFieldStats()
            self._cycle_count = 0
            self._active = False
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Serialization Helpers
    # -------------------------------------------------------------------------

    def _update_avg_metrics(self) -> None:
        if not self._npcs:
            self._stats.avg_dissonance = 0.0
            self._stats.avg_harmony = 0.0
            self._stats.avg_resonance = 1.0
            return
        self._stats.avg_dissonance = round(
            sum(s.dissonance_level for s in self._npcs.values()) / len(self._npcs), 4
        )
        self._stats.avg_harmony = round(
            sum(s.harmony_level for s in self._npcs.values()) / len(self._npcs), 4
        )
        self._stats.avg_resonance = round(
            sum(s.resonance_factor for s in self._npcs.values()) / len(self._npcs), 4
        )

    def _stats_to_dict(self) -> Dict[str, Any]:
        return {
            "total_npcs": self._stats.total_npcs,
            "total_waves_emitted": self._stats.total_waves_emitted,
            "total_interactions": self._stats.total_interactions,
            "total_cascades": self._stats.total_cascades,
            "total_cancellations": self._stats.total_cancellations,
            "total_chords_formed": self._stats.total_chords_formed,
            "total_field_shifts": self._stats.total_field_shifts,
            "avg_dissonance": self._stats.avg_dissonance,
            "avg_harmony": self._stats.avg_harmony,
            "avg_resonance": self._stats.avg_resonance,
            "last_cycle_time_ms": self._stats.last_cycle_time_ms,
            "active": self._stats.active,
        }

    def _npc_to_dict(self, state: NPCEmotionalState) -> Dict[str, Any]:
        return {
            "npc_id": state.npc_id,
            "active_emotions": {
                e.value: round(a, 4) for e, a in state.active_emotions.items()
            },
            "dominant_emotion": state.dominant_emotion.value if state.dominant_emotion else None,
            "dissonance_level": round(state.dissonance_level, 4),
            "harmony_level": round(state.harmony_level, 4),
            "resonance_factor": round(state.resonance_factor, 4),
            "coupling_count": len(state.couplings),
            "chord_count": len(state.chords),
            "waves_emitted": state.waves_emitted,
            "interactions_received": state.interactions_received,
            "last_updated": state.last_updated,
        }

    def _coupling_to_dict(self, c: SocialCoupling) -> Dict[str, Any]:
        return {
            "source_id": c.source_id,
            "target_id": c.target_id,
            "coupling_strength": c.coupling_strength,
            "is_amplifier": c.is_amplifier,
        }

    def _interaction_to_dict(self, inter: ResonanceInteraction) -> Dict[str, Any]:
        return {
            "interaction_id": inter.interaction_id,
            "wave_a_id": inter.wave_a_id,
            "wave_b_id": inter.wave_b_id,
            "npc_a_id": inter.npc_a_id,
            "npc_b_id": inter.npc_b_id,
            "emotion_a": inter.emotion_a.value,
            "emotion_b": inter.emotion_b.value,
            "interference": inter.interference.value,
            "strength": round(inter.strength, 4),
            "amplitude_delta": round(inter.amplitude_delta, 4),
            "timestamp": inter.timestamp,
        }

    def _chord_to_dict(self, chord: EmotionalChord) -> Dict[str, Any]:
        return {
            "chord_id": chord.chord_id,
            "npc_id": chord.npc_id,
            "emotions": [e.value for e in chord.emotions],
            "root_frequency": chord.root_frequency,
            "harmony": round(chord.harmony, 4),
            "stability": round(chord.stability, 4),
            "timestamp": chord.timestamp,
        }
