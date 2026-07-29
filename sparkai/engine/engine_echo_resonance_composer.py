"""
SparkLabs Engine - Echo Resonance Composer

The EngineEchoResonanceComposer models how significant events in the game
world emit resonant echoes that propagate through time and space, interfere
with each other, achieve resonance lock, and ultimately decay into the
world's echo memory.

Events in a world are not isolated detonations that vanish at the moment
of their occurrence - they emit echoes. A king's betrayal does not end
when the throne is usurped; its echo propagates forward, coloring every
subsequent political interaction with suspicion. A hero's sacrifice does
not end with their death; its echo resonates with future acts of courage,
amplifying them. The world does not forget - it rings.

The composer treats the world as a resonance medium through which event-
echoes propagate. Each echo has:
  - A source event (the king's betrayal, the hero's sacrifice)
  - A frequency (how rapidly it cycles through influence - fast echoes
    affect immediate reactions; slow echoes shape cultural memory)
  - An amplitude (how strong its influence is)
  - A phase (where it is in its cycle)

When two echoes collide, they interfere:
  - Constructive interference: aligned echoes amplify each other,
    producing resonant locks that powerfully shape future events
  - Destructive interference: opposing echoes cancel each other,
    producing dead zones where certain influences cannot reach
  - Beat patterns: slightly misaligned echoes produce oscillating
    influence that waxes and wanes over time

Resonance lock occurs when echoes constructively reinforce into a
standing wave - a persistent pattern of influence that shapes events
long after the source echoes have decayed. The fallen kingdom's betrayal
becomes a standing wave of distrust that shapes politics for generations,
until a counter-event of sufficient magnitude destructively interferes.

The composer models five forces:
  - Emission: events emit echoes with frequency, amplitude, and phase
  - Propagation: echoes spread through the world's resonance medium
  - Interference: colliding echoes constructively or destructively combine
  - Resonance: reinforced echoes achieve standing-wave lock
  - Decay: echoes lose amplitude and eventually fade into echo memory

This produces a world where the past is not dead matter but active
resonance, where events have afterlives that shape the present, and
where players can learn to read the world's echo field to anticipate
the deep patterns shaping their reality.

Architecture:
  EMIT     ->  PROPAGATE ->  INTERFERE ->  RESONATE  ->  DECAY
  (events   (echoes      (colliding    (constructive (echoes lose
   emit      propagate    echoes        interference   amplitude,
   echoes    through      produce       achieves       fading into
   into the  the world's  constructive/ standing-wave   echo memory;
   field)    medium)      destructive    lock that      standing
                        interference)  shapes events)  waves persist)

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

class EchoPhase(Enum):
    """Phases of the echo resonance composition cycle."""
    EMIT = "emit"             # events emit echoes into the field
    PROPAGATE = "propagate"   # echoes propagate through the medium
    INTERFERE = "interfere"   # colliding echoes interfere
    RESONATE = "resonate"     # reinforced echoes achieve standing-wave lock
    DECAY = "decay"           # echoes lose amplitude and fade


class EchoFrequency(Enum):
    """How rapidly an echo cycles through influence."""
    INSTANT = "instant"       # immediate reactions (seconds to minutes)
    RAPID = "rapid"           # short-term (minutes to hours)
    DAILY = "daily"           # circadian (days)
    SEASONAL = "seasonal"     # yearly cycles
    GENERATIONAL = "generational"  # spans generations
    ETERNAL = "eternal"       # mythic timescales


class EchoValence(Enum):
    """The emotional/moral coloring of an echo."""
    GLORIOUS = "glorious"     # triumph, heroism, victory
    TRAGIC = "tragic"         # loss, sacrifice, fall
    OMINOUS = "ominous"       # dread, warning, foreshadow
    JOYFUL = "joyful"         # celebration, union, birth
    WRATHFUL = "wrathful"     # anger, vengeance, fury
    MOURNFUL = "mournful"     # grief, lament, absence
    MYSTIC = "mystic"         # wonder, awe, revelation
    TENSE = "tense"           # anxiety, suspense, anticipation


class InterferenceType(Enum):
    """Types of interference between colliding echoes."""
    CONSTRUCTIVE = "constructive"  # aligned echoes amplify
    DESTRUCTIVE = "destructive"    # opposing echoes cancel
    BEAT = "beat"                   # misaligned echoes produce oscillation
    NULL = "null"                   # no significant interaction


class EchoState(Enum):
    """State of an echo in its lifecycle."""
    EMITTED = "emitted"       # just emitted, full amplitude
    PROPAGATING = "propagating"  # spreading through medium
    INTERFERING = "interfering"  # currently colliding with others
    LOCKED = "locked"          # achieved resonance standing-wave
    WANING = "waning"          # losing amplitude
    FADED = "faded"            # decayed into echo memory
    CANCELLED = "cancelled"    # destructively cancelled


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class EchoEvent:
    """A significant event that emits an echo into the resonance field."""
    event_id: str
    label: str
    description: str
    frequency: EchoFrequency
    valence: EchoValence
    amplitude: float = 0.7         # initial strength (0.0-1.0)
    phase: float = 0.0             # current phase (0.0-2*pi)
    x: float = 0.5                 # spatial position (0.0-1.0)
    y: float = 0.5
    radius: float = 0.0            # how far it has propagated
    state: EchoState = EchoState.EMITTED
    emitted_at: float = field(default_factory=time.time)
    last_phase_update: float = field(default_factory=time.time)
    interference_count: int = 0
    resonance_locks: int = 0
    parent_event: Optional[str] = None  # if this echo was spawned by another


@dataclass
class InterferenceEvent:
    """A record of two echoes interfering."""
    interference_id: str
    echo_a: str
    echo_b: str
    type: InterferenceType
    resulting_amplitude: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class StandingWave:
    """A resonance lock - a persistent standing wave pattern."""
    wave_id: str
    valence: EchoValence
    frequency: EchoFrequency
    amplitude: float              # current standing amplitude
    contributing_echoes: List[str] = field(default_factory=list)
    spatial_extent: float = 0.5   # how widely the wave extends
    locked_at: float = field(default_factory=time.time)
    stability: float = 0.7        # how resistant to disruption
    disruptions: int = 0


@dataclass
class EchoMemory:
    """A faded echo preserved in the world's echo memory."""
    memory_id: str
    source_event: str
    valence: EchoValence
    peak_amplitude: float
    duration_cycles: int
    resonance_locks_achieved: int
    interferences_participated: int
    faded_at: float = field(default_factory=time.time)


# =============================================================================
# Echo Resonance Composer
# =============================================================================

class EngineEchoResonanceComposer:
    """
    Thread-safe singleton orchestrating echo resonance composition.

    Usage:
        composer = EngineEchoResonanceComposer.get_instance()
        composer.emit_echo("e_betrayal", "The King's Betrayal",
                          "The king murdered his sworn brother",
                          EchoFrequency.GENERATIONAL, EchoValence.OMINOUS,
                          amplitude=0.9, x=0.4, y=0.5)
        composer.emit_echo("e_sacrifice", "The Hero's Sacrifice",
                          "The hero gave their life for the kingdom",
                          EchoFrequency.GENERATIONAL, EchoValence.GLORIOUS,
                          amplitude=0.85, x=0.6, y=0.5)
        composer.cycle()
    """

    _instance: Optional["EngineEchoResonanceComposer"] = None
    _lock = threading.RLock()

    # Frequency to propagation rate mapping (per cycle)
    _FREQUENCY_RATES = {
        EchoFrequency.INSTANT: 0.4,
        EchoFrequency.RAPID: 0.3,
        EchoFrequency.DAILY: 0.2,
        EchoFrequency.SEASONAL: 0.12,
        EchoFrequency.GENERATIONAL: 0.06,
        EchoFrequency.ETERNAL: 0.03,
    }
    # Frequency to phase advance per cycle
    _FREQUENCY_PHASE = {
        EchoFrequency.INSTANT: 1.2,
        EchoFrequency.RAPID: 0.8,
        EchoFrequency.DAILY: 0.4,
        EchoFrequency.SEASONAL: 0.2,
        EchoFrequency.GENERATIONAL: 0.08,
        EchoFrequency.ETERNAL: 0.03,
    }
    # Decay rate per cycle (modified by frequency)
    _DECAY_BASE = 0.04
    # Distance threshold for interference
    _INTERFERENCE_DISTANCE = 0.35
    # Resonance lock amplitude threshold
    _RESONANCE_THRESHOLD = 0.65
    # Valence affinity matrix (1.0 = perfect constructive, -1.0 = perfect destructive)
    _VALENCE_AFFINITY = {
        (EchoValence.GLORIOUS, EchoValence.GLORIOUS): 1.0,
        (EchoValence.TRAGIC, EchoValence.TRAGIC): 0.8,
        (EchoValence.OMINOUS, EchoValence.OMINOUS): 1.0,
        (EchoValence.JOYFUL, EchoValence.JOYFUL): 1.0,
        (EchoValence.WRATHFUL, EchoValence.WRATHFUL): 0.9,
        (EchoValence.MOURNFUL, EchoValence.MOURNFUL): 0.85,
        (EchoValence.MYSTIC, EchoValence.MYSTIC): 1.0,
        (EchoValence.TENSE, EchoValence.TENSE): 0.9,
        (EchoValence.GLORIOUS, EchoValence.TRAGIC): -0.6,
        (EchoValence.GLORIOUS, EchoValence.WRATHFUL): -0.4,
        (EchoValence.JOYFUL, EchoValence.MOURNFUL): -0.7,
        (EchoValence.JOYFUL, EchoValence.TENSE): -0.5,
        (EchoValence.OMINOUS, EchoValence.JOYFUL): -0.5,
        (EchoValence.MYSTIC, EchoValence.WRATHFUL): -0.3,
        (EchoValence.TENSE, EchoValence.MOURNFUL): 0.3,
        (EchoValence.TRAGIC, EchoValence.MOURNFUL): 0.6,
    }

    def __init__(self) -> None:
        self._echoes: Dict[str, EchoEvent] = {}
        self._interferences: Deque[InterferenceEvent] = deque(maxlen=300)
        self._standing_waves: Dict[str, StandingWave] = {}
        self._memory: Deque[EchoMemory] = deque(maxlen=200)
        self._phase: EchoPhase = EchoPhase.EMIT
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {
            "total_echoes_emitted": 0,
            "active_echoes": 0,
            "total_interferences": 0,
            "constructive_interferences": 0,
            "destructive_interferences": 0,
            "beat_interferences": 0,
            "total_standing_waves": 0,
            "active_standing_waves": 0,
            "total_memory_entries": 0,
            "avg_amplitude": 0.0,
            "avg_radius": 0.0,
            "faded_echoes": 0,
            "cancelled_echoes": 0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineEchoResonanceComposer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Echo Management
    # -------------------------------------------------------------------------

    def emit_echo(
        self,
        event_id: str,
        label: str,
        description: str,
        frequency: EchoFrequency,
        valence: EchoValence,
        amplitude: float = 0.7,
        x: float = 0.5,
        y: float = 0.5,
        phase: float = 0.0,
        parent_event: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Emit a new echo into the resonance field."""
        with self._global_lock:
            if event_id in self._echoes:
                return {"error": f"Echo already exists: {event_id}"}
            echo = EchoEvent(
                event_id=event_id,
                label=label,
                description=description,
                frequency=frequency,
                valence=valence,
                amplitude=max(0.0, min(1.0, amplitude)),
                phase=phase % (2 * math.pi),
                x=max(0.0, min(1.0, x)),
                y=max(0.0, min(1.0, y)),
                state=EchoState.EMITTED,
                parent_event=parent_event,
            )
            self._echoes[event_id] = echo
            self._stats["total_echoes_emitted"] += 1
            self._record_event("echo_emitted", {
                "event_id": event_id,
                "label": label,
                "frequency": frequency.value,
                "valence": valence.value,
                "amplitude": echo.amplitude,
            })
            return {
                "event_id": event_id,
                "label": label,
                "frequency": frequency.value,
                "valence": valence.value,
                "amplitude": echo.amplitude,
                "phase": echo.phase,
                "state": echo.state.value,
            }

    def get_echo(self, event_id: str) -> Dict[str, Any]:
        """Get a specific echo by ID."""
        with self._global_lock:
            e = self._echoes.get(event_id)
            if e is None:
                return {"error": f"Echo not found: {event_id}"}
            return self._serialize_echo(e)

    def get_all_echoes(self) -> List[Dict[str, Any]]:
        """Get all active echoes."""
        with self._global_lock:
            return [self._serialize_echo(e) for e in self._echoes.values()]

    def get_standing_waves(self) -> List[Dict[str, Any]]:
        """Get all standing waves."""
        with self._global_lock:
            return [self._serialize_wave(w) for w in self._standing_waves.values()]

    def get_interferences(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent interference events."""
        with self._global_lock:
            events = list(self._interferences)[-limit:]
            return [
                {
                    "interference_id": i.interference_id,
                    "echo_a": i.echo_a,
                    "echo_b": i.echo_b,
                    "type": i.type.value,
                    "resulting_amplitude": i.resulting_amplitude,
                    "timestamp": i.timestamp,
                }
                for i in events
            ]

    def get_memory(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get faded echo memory entries."""
        with self._global_lock:
            entries = list(self._memory)[-limit:]
            return [
                {
                    "memory_id": m.memory_id,
                    "source_event": m.source_event,
                    "valence": m.valence.value,
                    "peak_amplitude": m.peak_amplitude,
                    "duration_cycles": m.duration_cycles,
                    "resonance_locks_achieved": m.resonance_locks_achieved,
                    "interferences_participated": m.interferences_participated,
                    "faded_at": m.faded_at,
                }
                for m in entries
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the composer."""
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
        """Reset the entire composer."""
        with self._global_lock:
            self._echoes.clear()
            self._interferences.clear()
            self._standing_waves.clear()
            self._memory.clear()
            self._phase = EchoPhase.EMIT
            self._cycle_count = 0
            self._events_log.clear()
            self._init_stats()
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single echo resonance composition cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = EchoPhase.EMIT
            phase_outputs["emit"] = self._phase_emit()
            self._phase = EchoPhase.PROPAGATE
            phase_outputs["propagate"] = self._phase_propagate()
            self._phase = EchoPhase.INTERFERE
            phase_outputs["interfere"] = self._phase_interfere()
            self._phase = EchoPhase.RESONATE
            phase_outputs["resonate"] = self._phase_resonate()
            self._phase = EchoPhase.DECAY
            phase_outputs["decay"] = self._phase_decay()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_emit(self) -> Dict[str, Any]:
        """Emission phase: recently emitted echoes begin propagating."""
        transitioned = 0
        for echo in self._echoes.values():
            if echo.state == EchoState.EMITTED:
                echo.state = EchoState.PROPAGATING
                transitioned += 1
        return {
            "echoes_propagating_started": transitioned,
            "active_echoes": len(self._echoes),
        }

    def _phase_propagate(self) -> Dict[str, Any]:
        """Propagation phase: echoes spread and advance their phase."""
        propagated = 0
        for echo in self._echoes.values():
            if echo.state in (EchoState.FADED, EchoState.CANCELLED):
                continue
            rate = self._FREQUENCY_RATES.get(echo.frequency, 0.1)
            echo.radius = min(1.5, echo.radius + rate)
            phase_advance = self._FREQUENCY_PHASE.get(echo.frequency, 0.1)
            echo.phase = (echo.phase + phase_advance) % (2 * math.pi)
            echo.last_phase_update = time.time()
            if echo.state == EchoState.INTERFERING:
                # return to propagating after interference
                echo.state = EchoState.PROPAGATING
            propagated += 1
        return {
            "echoes_propagated": propagated,
            "avg_radius": (
                sum(e.radius for e in self._echoes.values()) / len(self._echoes)
                if self._echoes else 0.0
            ),
        }

    def _phase_interfere(self) -> Dict[str, Any]:
        """Interference phase: colliding echoes interact."""
        constructive = 0
        destructive = 0
        beat = 0
        echoes_list = list(self._echoes.values())
        for i in range(len(echoes_list)):
            for j in range(i + 1, len(echoes_list)):
                a = echoes_list[i]
                b = echoes_list[j]
                if a.state in (EchoState.FADED, EchoState.CANCELLED):
                    continue
                if b.state in (EchoState.FADED, EchoState.CANCELLED):
                    continue
                # check spatial overlap using propagation radii
                distance = math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)
                if distance > a.radius + b.radius:
                    continue
                if distance > self._INTERFERENCE_DISTANCE + max(a.radius, b.radius) * 0.3:
                    continue
                # compute interference
                affinity = self._VALENCE_AFFINITY.get(
                    (a.valence, b.valence),
                    self._VALENCE_AFFINITY.get((b.valence, a.valence), 0.0),
                )
                phase_diff = abs(a.phase - b.phase)
                phase_alignment = math.cos(phase_diff)
                # combined interference score
                interference_score = affinity * 0.6 + phase_alignment * 0.4
                amp_a = a.amplitude
                amp_b = b.amplitude
                if interference_score > 0.3:
                    # constructive
                    new_amp = min(1.0, (amp_a + amp_b) * 0.7 * (1.0 + interference_score * 0.3))
                    a.amplitude = new_amp
                    b.amplitude = new_amp
                    a.state = EchoState.INTERFERING
                    b.state = EchoState.INTERFERING
                    a.interference_count += 1
                    b.interference_count += 1
                    itype = InterferenceType.CONSTRUCTIVE
                    constructive += 1
                elif interference_score < -0.3:
                    # destructive
                    new_amp = max(0.0, (amp_a + amp_b) * 0.3 * (1.0 + interference_score * 0.5))
                    a.amplitude = new_amp
                    b.amplitude = new_amp
                    if new_amp < 0.1:
                        a.state = EchoState.CANCELLED
                        b.state = EchoState.CANCELLED
                    else:
                        a.state = EchoState.INTERFERING
                        b.state = EchoState.INTERFERING
                    a.interference_count += 1
                    b.interference_count += 1
                    itype = InterferenceType.DESTRUCTIVE
                    destructive += 1
                else:
                    # beat pattern - mild oscillation
                    new_amp_a = max(0.0, min(1.0, amp_a + 0.1 * interference_score))
                    new_amp_b = max(0.0, min(1.0, amp_b + 0.1 * interference_score))
                    a.amplitude = new_amp_a
                    b.amplitude = new_amp_b
                    itype = InterferenceType.BEAT
                    beat += 1
                # record interference
                int_id = f"int_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
                self._interferences.append(InterferenceEvent(
                    interference_id=int_id,
                    echo_a=a.event_id,
                    echo_b=b.event_id,
                    type=itype,
                    resulting_amplitude=new_amp if itype != InterferenceType.BEAT else (new_amp_a + new_amp_b) / 2,
                ))
        self._stats["constructive_interferences"] += constructive
        self._stats["destructive_interferences"] += destructive
        self._stats["beat_interferences"] += beat
        self._stats["total_interferences"] = len(self._interferences)
        return {
            "constructive": constructive,
            "destructive": destructive,
            "beat": beat,
        }

    def _phase_resonate(self) -> Dict[str, Any]:
        """Resonance phase: high-amplitude echoes form standing waves."""
        locks_formed = 0
        locks_reinforced = 0
        # find echoes with sufficient amplitude to form standing waves
        candidates = [
            e for e in self._echoes.values()
            if e.amplitude >= self._RESONANCE_THRESHOLD
            and e.state not in (EchoState.FADED, EchoState.CANCELLED, EchoState.LOCKED)
        ]
        # group by valence and frequency for resonance potential
        groups: Dict[Tuple[EchoValence, EchoFrequency], List[EchoEvent]] = {}
        for e in candidates:
            key = (e.valence, e.frequency)
            groups.setdefault(key, []).append(e)
        for (valence, freq), group in groups.items():
            if len(group) < 1:
                continue
            # check if a standing wave already exists for this group
            existing_wave = None
            for w in self._standing_waves.values():
                if w.valence == valence and w.frequency == freq:
                    existing_wave = w
                    break
            if existing_wave:
                # reinforce existing wave
                for e in group:
                    if e.event_id not in existing_wave.contributing_echoes:
                        existing_wave.contributing_echoes.append(e.event_id)
                    e.state = EchoState.LOCKED
                    e.resonance_locks += 1
                avg_amp = sum(self._echoes[eid].amplitude for eid in existing_wave.contributing_echoes if eid in self._echoes) / max(1, len(existing_wave.contributing_echoes))
                existing_wave.amplitude = min(1.0, avg_amp)
                existing_wave.stability = min(1.0, existing_wave.stability + 0.02)
                locks_reinforced += 1
            else:
                # form new standing wave
                wave_id = f"sw_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
                contributing = [e.event_id for e in group]
                avg_amp = sum(e.amplitude for e in group) / len(group)
                # compute spatial extent
                xs = [e.x for e in group]
                ys = [e.y for e in group]
                extent = max(
                    max(xs) - min(xs) if len(xs) > 1 else 0.5,
                    max(ys) - min(ys) if len(ys) > 1 else 0.5,
                ) + 0.2
                wave = StandingWave(
                    wave_id=wave_id,
                    contributing_echoes=contributing,
                    valence=valence,
                    frequency=freq,
                    amplitude=avg_amp,
                    spatial_extent=min(1.0, extent),
                    stability=0.7,
                )
                self._standing_waves[wave_id] = wave
                for e in group:
                    e.state = EchoState.LOCKED
                    e.resonance_locks += 1
                locks_formed += 1
                self._record_event("standing_wave_formed", {
                    "wave_id": wave_id,
                    "valence": valence.value,
                    "frequency": freq.value,
                    "amplitude": avg_amp,
                    "contributors": len(contributing),
                })
        return {
            "standing_waves_formed": locks_formed,
            "standing_waves_reinforced": locks_reinforced,
            "total_active_waves": len(self._standing_waves),
        }

    def _phase_decay(self) -> Dict[str, Any]:
        """Decay phase: echoes lose amplitude and fade into memory."""
        faded = 0
        cancelled = 0
        to_remove: List[str] = []
        for echo in self._echoes.values():
            if echo.state in (EchoState.FADED, EchoState.CANCELLED):
                continue
            # decay rate modified by frequency (eternal echoes decay slowest)
            freq_decay_mod = {
                EchoFrequency.INSTANT: 3.0,
                EchoFrequency.RAPID: 2.0,
                EchoFrequency.DAILY: 1.2,
                EchoFrequency.SEASONAL: 0.7,
                EchoFrequency.GENERATIONAL: 0.3,
                EchoFrequency.ETERNAL: 0.1,
            }.get(echo.frequency, 1.0)
            decay = self._DECAY_BASE * freq_decay_mod
            echo.amplitude = max(0.0, echo.amplitude - decay)
            if echo.state == EchoState.LOCKED:
                # locked echoes decay slower
                echo.amplitude = max(0.0, echo.amplitude + decay * 0.5)
            if echo.amplitude < 0.05:
                # fade into memory
                echo.state = EchoState.FADED
                mem_id = f"mem_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
                self._memory.append(EchoMemory(
                    memory_id=mem_id,
                    source_event=echo.event_id,
                    valence=echo.valence,
                    peak_amplitude=echo.amplitude,
                    duration_cycles=self._cycle_count,
                    resonance_locks_achieved=echo.resonance_locks,
                    interferences_participated=echo.interference_count,
                ))
                faded += 1
                to_remove.append(echo.event_id)
            elif echo.state == EchoState.CANCELLED and echo.amplitude < 0.01:
                cancelled += 1
                to_remove.append(echo.event_id)
        # remove faded echoes from active set, but keep them in memory log
        for eid in to_remove:
            self._echoes.pop(eid, None)
        # also decay standing waves
        waves_to_remove = []
        for wid, wave in self._standing_waves.items():
            wave.amplitude = max(0.0, wave.amplitude - self._DECAY_BASE * 0.3)
            if wave.amplitude < 0.1:
                wave.disruptions += 1
            if wave.amplitude < 0.05 or wave.disruptions >= 5:
                waves_to_remove.append(wid)
        for wid in waves_to_remove:
            self._standing_waves.pop(wid, None)
        self._stats["faded_echoes"] += faded
        self._stats["cancelled_echoes"] += cancelled
        self._stats["total_memory_entries"] = len(self._memory)
        return {
            "echoes_faded": faded,
            "echoes_cancelled": cancelled,
            "standing_waves_decayed": len(waves_to_remove),
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        self._stats["active_echoes"] = len(self._echoes)
        self._stats["active_standing_waves"] = len(self._standing_waves)
        if self._echoes:
            self._stats["avg_amplitude"] = sum(e.amplitude for e in self._echoes.values()) / len(self._echoes)
            self._stats["avg_radius"] = sum(e.radius for e in self._echoes.values()) / len(self._echoes)
        else:
            self._stats["avg_amplitude"] = 0.0
            self._stats["avg_radius"] = 0.0

    def _serialize_echo(self, e: EchoEvent) -> Dict[str, Any]:
        return {
            "event_id": e.event_id,
            "label": e.label,
            "description": e.description,
            "frequency": e.frequency.value,
            "valence": e.valence.value,
            "amplitude": e.amplitude,
            "phase": e.phase,
            "x": e.x,
            "y": e.y,
            "radius": e.radius,
            "state": e.state.value,
            "emitted_at": e.emitted_at,
            "interference_count": e.interference_count,
            "resonance_locks": e.resonance_locks,
            "parent_event": e.parent_event,
        }

    def _serialize_wave(self, w: StandingWave) -> Dict[str, Any]:
        return {
            "wave_id": w.wave_id,
            "contributing_echoes": list(w.contributing_echoes),
            "valence": w.valence.value,
            "frequency": w.frequency.value,
            "amplitude": w.amplitude,
            "spatial_extent": w.spatial_extent,
            "locked_at": w.locked_at,
            "stability": w.stability,
            "disruptions": w.disruptions,
        }

    def _init_stats(self) -> None:
        self._stats = {
            "total_echoes_emitted": 0,
            "active_echoes": 0,
            "total_interferences": 0,
            "constructive_interferences": 0,
            "destructive_interferences": 0,
            "beat_interferences": 0,
            "total_standing_waves": 0,
            "active_standing_waves": 0,
            "total_memory_entries": 0,
            "avg_amplitude": 0.0,
            "avg_radius": 0.0,
            "faded_echoes": 0,
            "cancelled_echoes": 0,
            "last_cycle_time_ms": 0.0,
        }

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
