"""
SparkLabs Engine - Spatiotemporal Rhythm Sequencer"""

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

class SequencerPhase(Enum):
    """Phases of the spatiotemporal rhythm cycle."""
    REGISTER = "register"    # accept and validate rhythm definitions
    LAYER = "layer"          # superpose rhythms into a composite waveform
    DETECT = "detect"        # find crests and troughs in the near-future window
    SCHEDULE = "schedule"    # emit timed events at detected moments
    SETTLE = "settle"        # dampen jitter and record the settled map


class RhythmKind(Enum):
    """The kind of rhythm being registered."""
    DIURNAL = "diurnal"          # day/night cycle
    TIDAL = "tidal"              # tide
    SOCIAL = "social"            # crowd bustle
    PATROL = "patrol"            # NPC beats
    CALENDRICAL = "calendrical"  # festival/seasonal
    CARDIAC = "cardiac"          # heartbeat-like tension
    LUNAR = "lunar"              # lunar cycle


class InterferenceType(Enum):
    """How rhythms interfere at a given moment."""
    CONSTRUCTIVE = "constructive"  # rhythms align, amplitude sums
    DESTRUCTIVE = "destructive"    # rhythms cancel, amplitude near zero
    PARTIAL = "partial"            # some alignment, some cancellation
    NEUTRAL = "neutral"            # low activity overall


class EventMoment(Enum):
    """The character of a scheduled moment."""
    CREST = "crest"      # peak, fire events
    TROUGH = "trough"    # rest, sparse
    RISING = "rising"    # building toward a crest
    FALLING = "falling"  # easing away from a crest


class SequencerState(Enum):
    """Operational state of the sequencer."""
    IDLE = "idle"
    LAYERING = "layering"
    DETECTING = "detecting"
    SCHEDULING = "scheduling"
    SETTLED = "settled"
    SATURATED = "saturated"


class SequencerVitality(Enum):
    """Overall vitality of the rhythm ecosystem."""
    SILENT = "silent"            # no rhythms registered
    PULSING = "pulsing"          # some activity, not yet synced
    SYNCED = "synced"            # healthy constructive interference
    CACOPHONOUS = "cacophonous"  # too many conflicting rhythms
    OVERDRIVEN = "overdriven"    # amplitudes pushed too high


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Rhythm:
    """A single rhythmic wave registered with the sequencer."""
    rhythm_id: str
    kind: RhythmKind
    region: str
    period_units: float = 24.0          # length of one full cycle in time units
    phase_offset: float = 0.0           # 0.0-1.0, where in the cycle it starts
    amplitude: float = 0.5              # 0.0-1.0, how strong the rhythm is
    note: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class CompositeWave:
    """The superposed waveform for a single region."""
    region: str
    samples: List[Tuple[float, float]] = field(default_factory=list)  # (time_offset, value)
    dominant_rhythms: List[str] = field(default_factory=list)
    note: str = ""


@dataclass
class ScheduledMoment:
    """A single moment scheduled by the sequencer."""
    region: str
    time_offset: float
    moment: EventMoment = EventMoment.CREST
    value: float = 0.0
    contributing_rhythms: List[str] = field(default_factory=list)
    note: str = ""


@dataclass
class SequencerCycleResult:
    """Summary of a single sequencer cycle (also returned as dict by cycle())."""
    cycle_count: int = 0
    phase: str = "settle"
    phase_outputs: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Sequencer
# =============================================================================

class EngineSpatiotemporalRhythmSequencer:
    """
    Thread-safe singleton orchestrating spatiotemporal rhythm sequencing.

    Usage:
        seq = EngineSpatiotemporalRhythmSequencer.get_instance()
        seq.register_rhythm("daynight", "diurnal", "village",
                            period_units=24, phase_offset=0.0, amplitude=0.8)
        result = seq.cycle()
        wave = seq.get_wave("village")
        schedule = seq.get_schedule()
    """

    _instance: Optional["EngineSpatiotemporalRhythmSequencer"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Tuning constants
    _MAX_RHYTHMS = 64
    _MAX_REGIONS = 32
    _MAX_SAMPLES = 128
    _MAX_SCHEDULE = 200
    _MAX_EVENTS = 200
    _CREST_THRESHOLD = 0.7
    _TROUGH_THRESHOLD = 0.2
    _NEAR_FUTURE_WINDOW = 24.0          # time units to look ahead
    _SETTLE_MERGE_DISTANCE = 0.5        # min time gap between scheduled moments
    _SATURATION_RHYTHM_COUNT = 48       # rhythms before saturation
    _VITALITY_OVERDRIVE_AMPLITUDE = 0.9

    def __init__(self) -> None:
        self._rhythms: Dict[str, Rhythm] = {}
        self._waves: Dict[str, CompositeWave] = {}
        self._schedule: Deque[ScheduledMoment] = deque(maxlen=self._MAX_SCHEDULE)
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._cycle_count: int = 0
        self._current_phase: SequencerPhase = SequencerPhase.REGISTER
        self._state: SequencerState = SequencerState.IDLE
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineSpatiotemporalRhythmSequencer":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    def _init_stats(self) -> None:
        self._stats = {
            "cycles_completed": 0,
            "rhythms_registered": 0,
            "waves_layered": 0,
            "crests_detected": 0,
            "troughs_detected": 0,
            "events_scheduled": 0,
            "constructive_events": 0,
            "destructive_events": 0,
            "mean_amplitude": 0.0,
            "last_cycle_at": 0.0,
            "uptime_started_at": time.time(),
        }

    def _update_stats(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            self._stats[key] = value
        # Recompute mean amplitude from registered rhythms.
        if self._rhythms:
            self._stats["mean_amplitude"] = (
                sum(r.amplitude for r in self._rhythms.values())
                / len(self._rhythms)
            )
        else:
            self._stats["mean_amplitude"] = 0.0
        self._stats["rhythms_registered"] = len(self._rhythms)
        self._stats["waves_layered"] = len(self._waves)
        self._stats["events_scheduled"] = len(self._schedule)

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Public: Rhythm Registration
    # -------------------------------------------------------------------------

    def register_rhythm(self, rhythm_id: str, kind: str, region: str,
                        period_units: float = 24.0, phase_offset: float = 0.0,
                        amplitude: float = 0.5, note: str = "") -> Dict[str, Any]:
        """Register a new rhythm with the sequencer."""
        with self._global_lock:
            if rhythm_id in self._rhythms:
                return {"error": f"Rhythm already registered: {rhythm_id}"}
            if len(self._rhythms) >= self._MAX_RHYTHMS:
                return {"error": f"Maximum rhythms reached: {self._MAX_RHYTHMS}"}
            try:
                kind_enum = RhythmKind(kind)
            except ValueError:
                return {"error": f"Invalid kind: {kind}"}
            rhythm = Rhythm(
                rhythm_id=rhythm_id,
                kind=kind_enum,
                region=region,
                period_units=max(0.001, period_units),
                phase_offset=max(0.0, min(1.0, phase_offset)),
                amplitude=max(0.0, min(1.0, amplitude)),
                note=note,
            )
            self._rhythms[rhythm_id] = rhythm
            self._stats["rhythms_registered"] = len(self._rhythms)
            self._record_event("rhythm_registered", {
                "rhythm_id": rhythm_id,
                "kind": kind_enum.value,
                "region": region,
                "period_units": rhythm.period_units,
                "phase_offset": rhythm.phase_offset,
                "amplitude": rhythm.amplitude,
            })
            return {
                "rhythm_id": rhythm_id,
                "kind": kind_enum.value,
                "region": region,
                "period_units": rhythm.period_units,
                "phase_offset": rhythm.phase_offset,
                "amplitude": rhythm.amplitude,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single spatiotemporal rhythm cycle through all five phases."""
        with self._global_lock:
            self._cycle_count += 1
            phase_outputs: List[Dict[str, Any]] = []

            self._current_phase = SequencerPhase.REGISTER
            self._state = SequencerState.IDLE
            out_register = self._phase_register()
            out_register["phase"] = SequencerPhase.REGISTER.value
            phase_outputs.append(out_register)

            self._current_phase = SequencerPhase.LAYER
            self._state = SequencerState.LAYERING
            out_layer = self._phase_layer()
            out_layer["phase"] = SequencerPhase.LAYER.value
            phase_outputs.append(out_layer)

            self._current_phase = SequencerPhase.DETECT
            self._state = SequencerState.DETECTING
            out_detect = self._phase_detect()
            out_detect["phase"] = SequencerPhase.DETECT.value
            phase_outputs.append(out_detect)

            self._current_phase = SequencerPhase.SCHEDULE
            self._state = SequencerState.SCHEDULING
            out_schedule = self._phase_schedule()
            out_schedule["phase"] = SequencerPhase.SCHEDULE.value
            phase_outputs.append(out_schedule)

            self._current_phase = SequencerPhase.SETTLE
            self._state = SequencerState.SETTLED
            out_settle = self._phase_settle()
            out_settle["phase"] = SequencerPhase.SETTLE.value
            phase_outputs.append(out_settle)

            self._stats["cycles_completed"] = self._cycle_count
            self._update_stats(last_cycle_at=time.time())
            if len(self._rhythms) >= self._SATURATION_RHYTHM_COUNT:
                self._state = SequencerState.SATURATED
            return {
                "cycle_count": self._cycle_count,
                "phase": self._current_phase.value,
                "state": self._state.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_register(self) -> Dict[str, Any]:
        """Register phase: validate all registered rhythms."""
        valid = 0
        invalid = 0
        regions_seen: set = set()
        for rhythm in self._rhythms.values():
            ok, reason = self._validate_rhythm(rhythm)
            if ok:
                valid += 1
                regions_seen.add(rhythm.region)
            else:
                invalid += 1
                logger.warning("Invalid rhythm %s: %s", rhythm.rhythm_id, reason)
        self._record_event("phase_register", {
            "valid": valid,
            "invalid": invalid,
            "regions": len(regions_seen),
        })
        return {
            "valid": valid,
            "invalid": invalid,
            "regions": len(regions_seen),
        }

    def _phase_layer(self) -> Dict[str, Any]:
        """Layer phase: superpose all active rhythms per region into a composite wave."""
        regions = self._collect_regions()
        waves_layered = 0
        for region in regions:
            wave = self._compute_composite_wave(region)
            self._waves[region] = wave
            waves_layered += 1
        self._record_event("phase_layer", {
            "waves_layered": waves_layered,
            "regions": len(regions),
        })
        return {
            "waves_layered": waves_layered,
            "regions": len(regions),
        }

    def _phase_detect(self) -> Dict[str, Any]:
        """Detect phase: find crests and troughs in each region's composite wave."""
        crests_total = 0
        troughs_total = 0
        constructive = 0
        destructive = 0
        detected: List[Dict[str, Any]] = []
        for region, wave in self._waves.items():
            crests, troughs = self._find_extrema(wave)
            crests_total += len(crests)
            troughs_total += len(troughs)
            for idx in crests:
                itype = self._classify_interference(wave, idx)
                if itype == InterferenceType.CONSTRUCTIVE:
                    constructive += 1
                elif itype == InterferenceType.DESTRUCTIVE:
                    destructive += 1
                detected.append({
                    "region": region,
                    "index": idx,
                    "time_offset": wave.samples[idx][0],
                    "value": wave.samples[idx][1],
                    "kind": "crest",
                    "interference": itype.value,
                })
            for idx in troughs:
                itype = self._classify_interference(wave, idx)
                if itype == InterferenceType.CONSTRUCTIVE:
                    constructive += 1
                elif itype == InterferenceType.DESTRUCTIVE:
                    destructive += 1
                detected.append({
                    "region": region,
                    "index": idx,
                    "time_offset": wave.samples[idx][0],
                    "value": wave.samples[idx][1],
                    "kind": "trough",
                    "interference": itype.value,
                })
        self._stats["crests_detected"] = crests_total
        self._stats["troughs_detected"] = troughs_total
        self._stats["constructive_events"] = constructive
        self._stats["destructive_events"] = destructive
        self._record_event("phase_detect", {
            "crests": crests_total,
            "troughs": troughs_total,
            "constructive": constructive,
            "destructive": destructive,
        })
        return {
            "crests": crests_total,
            "troughs": troughs_total,
            "constructive": constructive,
            "destructive": destructive,
            "detected": detected[:50],
        }

    def _phase_schedule(self) -> Dict[str, Any]:
        """Schedule phase: emit timed events at crests and mark troughs as rest."""
        scheduled = 0
        for region, wave in self._waves.items():
            crests, troughs = self._find_extrema(wave)
            rhythms = [r.rhythm_id for r in self._rhythms.values()
                       if r.region == region]
            for idx in crests:
                moment = ScheduledMoment(
                    region=region,
                    time_offset=wave.samples[idx][0],
                    moment=EventMoment.CREST,
                    value=wave.samples[idx][1],
                    contributing_rhythms=list(rhythms),
                    note="peak moment, fire events",
                )
                self._schedule.append(moment)
                scheduled += 1
            for idx in troughs:
                moment = ScheduledMoment(
                    region=region,
                    time_offset=wave.samples[idx][0],
                    moment=EventMoment.TROUGH,
                    value=wave.samples[idx][1],
                    contributing_rhythms=list(rhythms),
                    note="rest moment, sparse activity",
                )
                self._schedule.append(moment)
                scheduled += 1
            # Add a small number of rising/falling transition moments.
            self._add_transition_moments(wave, rhythms)
        # Trim schedule to cap.
        while len(self._schedule) > self._MAX_SCHEDULE:
            self._schedule.popleft()
        self._record_event("phase_schedule", {"scheduled": scheduled})
        return {"scheduled": scheduled}

    def _phase_settle(self) -> Dict[str, Any]:
        """Settle phase: dampen jitter, smooth the schedule, record the settled map."""
        merged = self._merge_close_moments()
        vitality = self._derive_vitality()
        self._record_event("phase_settle", {
            "merged": merged,
            "vitality": vitality.value,
            "schedule_size": len(self._schedule),
            "regions": len(self._waves),
        })
        return {
            "merged": merged,
            "vitality": vitality.value,
            "schedule_size": len(self._schedule),
            "regions": len(self._waves),
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _validate_rhythm(self, rhythm: Rhythm) -> Tuple[bool, str]:
        """Validate a rhythm definition."""
        if rhythm.period_units <= 0:
            return False, "period_units must be positive"
        if not (0.0 <= rhythm.phase_offset <= 1.0):
            return False, "phase_offset must be in [0.0, 1.0]"
        if not (0.0 <= rhythm.amplitude <= 1.0):
            return False, "amplitude must be in [0.0, 1.0]"
        return True, ""

    def _collect_regions(self) -> List[str]:
        """Collect all distinct regions from registered rhythms, capped."""
        regions = sorted({r.region for r in self._rhythms.values()})
        return regions[: self._MAX_REGIONS]

    def _compute_composite_wave(self, region: str) -> CompositeWave:
        """Compute the composite waveform for a region by superposing its rhythms."""
        rhythms = [r for r in self._rhythms.values() if r.region == region]
        samples: List[Tuple[float, float]] = []
        n = self._MAX_SAMPLES
        for i in range(n):
            t = (i / max(1, n - 1)) * self._NEAR_FUTURE_WINDOW
            total = 0.0
            max_possible = 0.0
            for r in rhythms:
                if r.period_units <= 0:
                    continue
                phase = (t / r.period_units - r.phase_offset) % 1.0
                contribution = r.amplitude * math.sin(2.0 * math.pi * phase)
                total += contribution
                max_possible += r.amplitude
            value = total / max_possible if max_possible > 0 else 0.0
            samples.append((round(t, 4), round(value, 6)))
        dominant = sorted(rhythms, key=lambda r: r.amplitude, reverse=True)[:3]
        return CompositeWave(
            region=region,
            samples=samples,
            dominant_rhythms=[r.rhythm_id for r in dominant],
            note=f"composite of {len(rhythms)} rhythms over "
                 f"{self._NEAR_FUTURE_WINDOW} units",
        )

    def _find_extrema(self, wave: CompositeWave) -> Tuple[List[int], List[int]]:
        """Find crest and trough sample indices in a composite wave."""
        crests: List[int] = []
        troughs: List[int] = []
        samples = wave.samples
        for i in range(1, len(samples) - 1):
            prev_v = samples[i - 1][1]
            curr_v = samples[i][1]
            next_v = samples[i + 1][1]
            # Crest: local maximum above the crest threshold.
            if curr_v > prev_v and curr_v > next_v and curr_v >= self._CREST_THRESHOLD:
                crests.append(i)
            # Trough: local minimum at or below the trough threshold.
            elif (curr_v < prev_v and curr_v < next_v
                  and curr_v <= self._TROUGH_THRESHOLD):
                troughs.append(i)
        return crests, troughs

    def _classify_interference(self, wave: CompositeWave,
                               idx: int) -> InterferenceType:
        """Classify the interference type at a given sample index."""
        samples = wave.samples
        if not samples or idx < 0 or idx >= len(samples):
            return InterferenceType.NEUTRAL
        curr_v = samples[idx][1]
        region = wave.region
        rhythms = [r for r in self._rhythms.values() if r.region == region]
        if not rhythms:
            return InterferenceType.NEUTRAL
        t = samples[idx][0]
        contributions: List[float] = []
        for r in rhythms:
            if r.period_units <= 0:
                continue
            phase = (t / r.period_units - r.phase_offset) % 1.0
            contributions.append(r.amplitude * math.sin(2.0 * math.pi * phase))
        if not contributions:
            return InterferenceType.NEUTRAL
        max_possible = sum(abs(c) for c in contributions)
        actual = abs(sum(contributions))
        if max_possible == 0:
            return InterferenceType.NEUTRAL
        # alignment: 1.0 means perfectly in phase, 0.0 means fully cancelled.
        alignment = actual / max_possible
        if alignment >= 0.8 and abs(curr_v) >= self._CREST_THRESHOLD:
            return InterferenceType.CONSTRUCTIVE
        if alignment <= 0.3:
            return InterferenceType.DESTRUCTIVE
        if alignment >= 0.6:
            return InterferenceType.PARTIAL
        return InterferenceType.NEUTRAL

    def _add_transition_moments(self, wave: CompositeWave,
                                rhythms: List[str]) -> None:
        """Add a few RISING and FALLING moments between extrema."""
        samples = wave.samples
        if len(samples) < 3:
            return
        step = max(1, len(samples) // 8)
        for i in range(step, len(samples) - step, step):
            curr_v = samples[i][1]
            next_v = samples[min(i + step, len(samples) - 1)][1]
            if self._TROUGH_THRESHOLD < abs(curr_v) < self._CREST_THRESHOLD:
                if next_v > curr_v:
                    self._schedule.append(ScheduledMoment(
                        region=wave.region,
                        time_offset=samples[i][0],
                        moment=EventMoment.RISING,
                        value=curr_v,
                        contributing_rhythms=list(rhythms),
                        note="building toward a crest",
                    ))
                elif next_v < curr_v:
                    self._schedule.append(ScheduledMoment(
                        region=wave.region,
                        time_offset=samples[i][0],
                        moment=EventMoment.FALLING,
                        value=curr_v,
                        contributing_rhythms=list(rhythms),
                        note="easing away from a crest",
                    ))

    def _merge_close_moments(self) -> int:
        """Merge scheduled moments that are too close in time within a region."""
        if len(self._schedule) < 2:
            return 0
        moments = list(self._schedule)
        moments.sort(key=lambda m: (m.region, m.time_offset))
        merged: List[ScheduledMoment] = []
        for m in moments:
            if merged:
                last = merged[-1]
                if (last.region == m.region
                        and abs(m.time_offset - last.time_offset)
                        < self._SETTLE_MERGE_DISTANCE):
                    # Keep the stronger moment when merging.
                    if abs(m.value) > abs(last.value):
                        merged[-1] = m
                    continue
            merged.append(m)
        removed = len(self._schedule) - len(merged)
        self._schedule.clear()
        self._schedule.extend(merged)
        return removed

    def _derive_vitality(self) -> SequencerVitality:
        """Derive the overall vitality of the rhythm ecosystem."""
        if not self._rhythms:
            return SequencerVitality.SILENT
        mean_amp = self._stats.get("mean_amplitude", 0.0)
        count = len(self._rhythms)
        constructive = self._stats.get("constructive_events", 0)
        destructive = self._stats.get("destructive_events", 0)
        if mean_amp >= self._VITALITY_OVERDRIVE_AMPLITUDE:
            return SequencerVitality.OVERDRIVEN
        if count >= self._SATURATION_RHYTHM_COUNT:
            return SequencerVitality.CACOPHONOUS
        if destructive > constructive and destructive > 0:
            return SequencerVitality.CACOPHONOUS
        if constructive > 0:
            return SequencerVitality.SYNCED
        return SequencerVitality.PULSING

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_wave(self, region: str) -> Dict[str, Any]:
        """Get the composite wave for a region."""
        with self._global_lock:
            wave = self._waves.get(region)
            if wave is None:
                return {"error": f"No wave for region: {region}"}
            return {
                "region": wave.region,
                "samples": wave.samples,
                "dominant_rhythms": wave.dominant_rhythms,
                "note": wave.note,
            }

    def get_schedule(self, limit: int = 50) -> Dict[str, Any]:
        """Get the scheduled moments (most recent first up to limit)."""
        with self._global_lock:
            moments = list(self._schedule)[-limit:]
            return {
                "count": len(self._schedule),
                "moments": [
                    {
                        "region": m.region,
                        "time_offset": m.time_offset,
                        "moment": m.moment.value,
                        "value": m.value,
                        "contributing_rhythms": m.contributing_rhythms,
                        "note": m.note,
                    }
                    for m in moments
                ],
            }

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the sequencer."""
        with self._global_lock:
            return {
                "phase": self._current_phase.value,
                "state": self._state.value,
                "cycle_count": self._cycle_count,
                "rhythms": len(self._rhythms),
                "regions": len(self._waves),
                "schedule_size": len(self._schedule),
                "stats": dict(self._stats),
            }

    def get_rhythms(self) -> Dict[str, Any]:
        """Get all registered rhythms."""
        with self._global_lock:
            return {
                "count": len(self._rhythms),
                "rhythms": [
                    {
                        "rhythm_id": r.rhythm_id,
                        "kind": r.kind.value,
                        "region": r.region,
                        "period_units": r.period_units,
                        "phase_offset": r.phase_offset,
                        "amplitude": r.amplitude,
                        "note": r.note,
                        "created_at": r.created_at,
                    }
                    for r in self._rhythms.values()
                ],
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the recent events log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Simulation and Reset
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic rhythms and run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_rhythms()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_rhythms(self) -> None:
        """Seed a small synthetic world with distinct rhythms across regions."""
        seed_rhythms = [
            ("sim_diurnal", "diurnal", "sim_village", 24.0, 0.0, 0.8, "day/night"),
            ("sim_market", "social", "sim_village", 6.0, 0.25, 0.5, "market bustle"),
            ("sim_patrol", "patrol", "sim_village", 4.0, 0.5, 0.4, "guard patrol"),
            ("sim_tide", "tidal", "sim_harbor", 12.0, 0.1, 0.6, "tide"),
            ("sim_lunar", "lunar", "sim_harbor", 28.0, 0.3, 0.3, "lunar pull"),
            ("sim_festival", "calendrical", "sim_capital", 48.0, 0.0, 0.7, "festival"),
            ("sim_cardiac", "cardiac", "sim_capital", 1.0, 0.5, 0.5, "tension beat"),
        ]
        for rhythm_id, kind, region, period, phase, amp, note in seed_rhythms:
            if rhythm_id not in self._rhythms:
                self.register_rhythm(
                    rhythm_id, kind, region,
                    period_units=period, phase_offset=phase,
                    amplitude=amp, note=note,
                )

    def reset(self) -> Dict[str, Any]:
        """Reset the sequencer to its initial state."""
        with self._global_lock:
            self._rhythms.clear()
            self._waves.clear()
            self._schedule.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._current_phase = SequencerPhase.REGISTER
            self._state = SequencerState.IDLE
            self._init_stats()
            return {"reset": True}
