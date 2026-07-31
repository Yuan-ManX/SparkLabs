"""
SparkLabs Agent - Narrative Momentum Governor

The AgentNarrativeMomentumGovernor treats narrative momentum as a physical
quantity. A story has velocity (how fast its tension is changing beat over
beat) and mass (how much narrative material has piled up). Their product is
momentum. Momentum builds toward a climax, plateaus, recedes, or stalls.

A story with too little momentum stalls and the audience disengages; a story
with too much momentum overshoots and exhausts the audience. The governor
senses the current narrative velocity, accumulates momentum from it, steers
that momentum toward or away from a climax by emitting pacing directives,
releases the accumulated momentum in a controlled burst when a climax
threshold is crossed, and resets stagnation by injecting a perturbation when
the momentum has been near zero for too long.

Architecture:
  SENSE       ->  ACCUMULATE  ->  STEER       ->  RELEASE     ->  RESET
  (read the     (mass x          (steer the      (when the      (if momentum
   narrative     velocity =       momentum        climax          has been
   velocity      momentum         toward or       threshold is    near zero
   from recent   accumulates      away from a     crossed,        too long,
   beats)        over cycles)     climax target)  release it in   inject a
                                                 a burst)        perturbation)

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
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class NarrativeMomentumPhase(Enum):
    """Phases of the narrative momentum cycle."""
    SENSE = "sense"            # read the current narrative velocity
    ACCUMULATE = "accumulate"  # mass x velocity = momentum, accumulated over time
    STEER = "steer"            # steer the momentum toward or away from a climax
    RELEASE = "release"        # release accumulated momentum in a controlled burst
    RESET = "reset"            # reset stagnation by injecting a perturbation


class MomentumRegime(Enum):
    """The current regime the narrative momentum is in."""
    BUILDING = "building"      # momentum rising toward a climax
    PEAKING = "peaking"        # momentum near or above the climax threshold
    PLATEAU = "plateau"        # momentum present but neither rising nor falling
    RECEDING = "receding"      # momentum falling away from a climax
    STAGNANT = "stagnant"      # momentum near zero for too long


class SteerDirective(Enum):
    """The directive the governor emits to steer the narrative momentum."""
    ACCELERATE = "accelerate"  # push momentum higher
    HOLD = "hold"              # keep momentum where it is
    DECELERATE = "decelerate"  # bleed momentum lower
    PERTURB = "perturb"        # inject a perturbation to break a stall


class ReleaseShape(Enum):
    """The shape a momentum release takes when the climax threshold is crossed."""
    CRESCENDO = "crescendo"    # a sharp rising peak that snaps over the top
    CADENCE = "cadence"        # a measured, rhythmic release
    DENOUEMENT = "denouement"  # a gentle taper after the peak
    ABRUPT = "abrupt"          # a hard cut while momentum is already falling


class GovernorTarget(Enum):
    """What the governor is steering the narrative momentum toward."""
    CLIMAX = "climax"          # build and release toward a climax
    COOLDOWN = "cooldown"      # bleed momentum down and hold low
    EXPLORATION = "exploration"  # wander with gentle, non-peaking momentum
    CONVERGENCE = "convergence"  # accelerate toward a convergent resolution


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NarrativeBeat:
    """A single narrative beat sensed by the governor."""
    beat_id: str
    tension_delta: float = 0.0          # signed: positive=rising, negative=falling
    weight: float = 0.5                 # 0.0-1.0, how much this beat counts
    timestamp: float = field(default_factory=time.time)


@dataclass
class MomentumReading:
    """A snapshot of the narrative momentum at one cycle."""
    velocity: float = 0.0
    mass: float = 0.0
    momentum: float = 0.0
    regime: MomentumRegime = MomentumRegime.STAGNANT
    cycle: int = 0


@dataclass
class SteerDecision:
    """A pacing directive emitted by the governor to steer momentum."""
    decision_id: str
    directive: SteerDirective
    target: GovernorTarget
    rationale: str = ""
    intensity: float = 0.0             # 0.0-1.0, how hard to push
    created_at: float = field(default_factory=time.time)


@dataclass
class NarrativeMomentumState:
    """Per-story narrative momentum state."""
    story_id: str
    beats: Deque[NarrativeBeat] = field(default_factory=deque)
    readings: List[MomentumReading] = field(default_factory=list)
    decisions: List[SteerDecision] = field(default_factory=list)
    regime: MomentumRegime = MomentumRegime.STAGNANT
    target: GovernorTarget = GovernorTarget.CLIMAX
    stagnation_cycles: int = 0
    release_count: int = 0
    perturbation_count: int = 0
    current_velocity: float = 0.0
    current_mass: float = 0.0
    current_momentum: float = 0.0
    total_beats_logged: int = 0
    total_decisions_emitted: int = 0


# =============================================================================
# Governor
# =============================================================================

class AgentNarrativeMomentumGovernor:
    """
    Thread-safe singleton governing narrative momentum as a physics-like
    quantity.

    Usage:
        gov = AgentNarrativeMomentumGovernor.get_instance()
        gov.register_story("story_1", GovernorTarget.CLIMAX)
        gov.log_beat("story_1", "b1", tension_delta=0.2, weight=0.7)
        gov.cycle()
        state = gov.get_story_state("story_1")
    """

    _instance: Optional["AgentNarrativeMomentumGovernor"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _SENSE_WINDOW = 6                  # how many recent beats inform velocity
    _ACCUMULATE_MASS_BASE = 0.5        # baseline narrative mass
    _STEER_INTENSITY_MAX = 0.8         # cap on steer directive intensity
    _RELEASE_CLIMAX_THRESHOLD = 0.7    # momentum needed to trigger a release
    _RESET_STAGNATION_CYCLES = 3       # near-zero cycles before a perturbation
    _MAX_BEATS_PER_STORY = 80
    _MAX_DECISIONS_PER_STORY = 60
    _MAX_STORIES = 30
    _MAX_EVENTS = 200
    _MAX_READINGS_PER_STORY = 100

    def __init__(self) -> None:
        self._stories: Dict[str, NarrativeMomentumState] = {}
        self._phase: NarrativeMomentumPhase = NarrativeMomentumPhase.SENSE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentNarrativeMomentumGovernor":
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
            "total_stories": 0,           # current count of registered stories
            "total_beats": 0,             # cumulative beats logged
            "total_decisions": 0,         # cumulative steer decisions emitted
            "total_releases": 0,          # cumulative momentum releases
            "total_perturbations": 0,     # cumulative perturbation injections
            "open_stories": 0,
            "avg_velocity": 0.0,
            "avg_momentum": 0.0,
            "dominant_regime": MomentumRegime.STAGNANT.value,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._stories:
            self._stats["total_stories"] = 0
            self._stats["open_stories"] = 0
            self._stats["avg_velocity"] = 0.0
            self._stats["avg_momentum"] = 0.0
            self._stats["dominant_regime"] = MomentumRegime.STAGNANT.value
            return
        velocities: List[float] = []
        momenta: List[float] = []
        regime_counts: Dict[str, int] = {}
        for state in self._stories.values():
            velocities.append(state.current_velocity)
            momenta.append(state.current_momentum)
            regime_counts[state.regime.value] = (
                regime_counts.get(state.regime.value, 0) + 1
            )
        self._stats["total_stories"] = len(self._stories)
        self._stats["open_stories"] = len(self._stories)
        self._stats["avg_velocity"] = (
            sum(velocities) / len(velocities) if velocities else 0.0
        )
        self._stats["avg_momentum"] = (
            sum(momenta) / len(momenta) if momenta else 0.0
        )
        if regime_counts:
            self._stats["dominant_regime"] = max(
                regime_counts, key=lambda k: regime_counts[k]
            )

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Story Management
    # -------------------------------------------------------------------------

    def register_story(self, story_id: str,
                       target: GovernorTarget = GovernorTarget.CLIMAX) -> Dict[str, Any]:
        """Register a new story for narrative momentum governance."""
        with self._global_lock:
            if story_id in self._stories:
                return {"error": f"Story already registered: {story_id}"}
            if len(self._stories) >= self._MAX_STORIES:
                return {"error": f"Story cap reached ({self._MAX_STORIES})"}
            state = NarrativeMomentumState(story_id=story_id, target=target)
            state.beats = deque(maxlen=self._MAX_BEATS_PER_STORY)
            self._stories[story_id] = state
            self._record_event("story_registered", {
                "story_id": story_id,
                "target": target.value,
            })
            return {
                "story_id": story_id,
                "target": target.value,
                "beats": 0,
            }

    def remove_story(self, story_id: str) -> Dict[str, Any]:
        """Remove a registered story."""
        with self._global_lock:
            state = self._stories.pop(story_id, None)
            if state is None:
                return {"error": f"Story not found: {story_id}"}
            self._record_event("story_removed", {"story_id": story_id})
            return {
                "removed": story_id,
                "cleared_beats": len(state.beats),
                "cleared_decisions": len(state.decisions),
                "cleared_readings": len(state.readings),
            }

    def set_target(self, story_id: str, target: GovernorTarget) -> Dict[str, Any]:
        """Change the steering target for a story."""
        with self._global_lock:
            state = self._stories.get(story_id)
            if state is None:
                return {"error": f"Story not found: {story_id}"}
            previous = state.target
            state.target = target
            self._record_event("target_set", {
                "story_id": story_id,
                "previous_target": previous.value,
                "new_target": target.value,
            })
            return {
                "story_id": story_id,
                "previous_target": previous.value,
                "new_target": target.value,
            }

    # -------------------------------------------------------------------------
    # Beat Intake
    # -------------------------------------------------------------------------

    def log_beat(self, story_id: str, beat_id: str,
                 tension_delta: float, weight: float = 0.5) -> Dict[str, Any]:
        """Log a narrative beat for a story.

        tension_delta is signed: positive means tension is rising, negative
        means tension is falling. weight is 0.0-1.0 and scales how much the
        beat contributes to the sensed velocity.
        """
        with self._global_lock:
            state = self._stories.get(story_id)
            if state is None:
                return {"error": f"Story not found: {story_id}"}
            if any(b.beat_id == beat_id for b in state.beats):
                return {"error": f"Beat already exists: {beat_id}"}
            beat = NarrativeBeat(
                beat_id=beat_id,
                tension_delta=float(tension_delta),
                weight=max(0.0, min(1.0, float(weight))),
            )
            state.beats.append(beat)
            state.total_beats_logged += 1
            self._stats["total_beats"] += 1
            self._record_event("beat_logged", {
                "story_id": story_id,
                "beat_id": beat_id,
                "tension_delta": beat.tension_delta,
                "weight": beat.weight,
            })
            return {
                "story_id": story_id,
                "beat_id": beat_id,
                "tension_delta": beat.tension_delta,
                "weight": beat.weight,
                "beats_in_window": len(state.beats),
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single narrative momentum cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = NarrativeMomentumPhase.SENSE
            phase_outputs["sense"] = self._phase_sense()
            self._phase = NarrativeMomentumPhase.ACCUMULATE
            phase_outputs["accumulate"] = self._phase_accumulate()
            self._phase = NarrativeMomentumPhase.STEER
            phase_outputs["steer"] = self._phase_steer()
            self._phase = NarrativeMomentumPhase.RELEASE
            phase_outputs["release"] = self._phase_release()
            self._phase = NarrativeMomentumPhase.RESET
            phase_outputs["reset"] = self._phase_reset()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_sense(self) -> Dict[str, Any]:
        """Sense phase: read the current narrative velocity from recent beats."""
        sensed = 0
        for state in self._stories.values():
            velocity = self._compute_velocity(state)
            state.current_velocity = velocity
            sensed += 1
        self._record_event("phase_sense", {"sensed": sensed})
        return {"sensed": sensed}

    def _phase_accumulate(self) -> Dict[str, Any]:
        """Accumulate phase: mass x velocity = momentum, accumulated over time."""
        accumulated = 0
        for state in self._stories.values():
            # Mass grows with how much narrative material has piled up in the
            # sense window, so a story with more beats is harder to redirect.
            recent_count = min(len(state.beats), self._SENSE_WINDOW)
            mass = self._ACCUMULATE_MASS_BASE + (
                recent_count / self._SENSE_WINDOW
            ) * 0.5
            momentum = mass * state.current_velocity
            state.current_mass = mass
            state.current_momentum = momentum
            # Track stagnation: near-zero momentum and velocity for too long.
            if abs(momentum) < 0.05 and abs(state.current_velocity) < 0.05:
                state.stagnation_cycles += 1
            else:
                state.stagnation_cycles = 0
            state.regime = self._classify_regime(
                state.current_velocity, momentum, state.stagnation_cycles
            )
            reading = MomentumReading(
                velocity=state.current_velocity,
                mass=mass,
                momentum=momentum,
                regime=state.regime,
                cycle=self._cycle_count,
            )
            state.readings.append(reading)
            if len(state.readings) > self._MAX_READINGS_PER_STORY:
                state.readings = state.readings[-self._MAX_READINGS_PER_STORY:]
            accumulated += 1
        self._record_event("phase_accumulate", {"accumulated": accumulated})
        return {"accumulated": accumulated}

    def _phase_steer(self) -> Dict[str, Any]:
        """Steer phase: emit a pacing directive based on the regime vs target."""
        decisions_emitted = 0
        for state in self._stories.values():
            directive, rationale, intensity = self._choose_directive(
                state.regime, state.target, state.current_momentum
            )
            decision = SteerDecision(
                decision_id=f"steer_{state.story_id}_{self._cycle_count}",
                directive=directive,
                target=state.target,
                rationale=rationale,
                intensity=intensity,
            )
            state.decisions.append(decision)
            if len(state.decisions) > self._MAX_DECISIONS_PER_STORY:
                state.decisions = state.decisions[-self._MAX_DECISIONS_PER_STORY:]
            state.total_decisions_emitted += 1
            self._stats["total_decisions"] += 1
            decisions_emitted += 1
            self._record_event("phase_steer", {
                "story_id": state.story_id,
                "directive": directive.value,
                "target": state.target.value,
                "intensity": intensity,
                "rationale": rationale,
            })
        return {"decisions_emitted": decisions_emitted}

    def _phase_release(self) -> Dict[str, Any]:
        """Release phase: spend accumulated momentum in a controlled burst."""
        released = 0
        for state in self._stories.values():
            # A release fires when momentum crosses the climax threshold and
            # the story is actually being steered toward a climax or convergence.
            if state.current_momentum < self._RELEASE_CLIMAX_THRESHOLD:
                continue
            if state.target not in (GovernorTarget.CLIMAX,
                                    GovernorTarget.CONVERGENCE):
                continue
            shape = self._shape_release(
                state.current_momentum, state.current_velocity
            )
            spent = state.current_momentum
            # The burst spends most of the accumulated momentum; a residue
            # remains as the falling action carries the story forward.
            state.current_momentum *= 0.15
            state.current_velocity *= 0.3
            state.release_count += 1
            released += 1
            self._record_event("phase_release", {
                "story_id": state.story_id,
                "shape": shape.value,
                "momentum_spent": spent,
                "remaining_momentum": state.current_momentum,
            })
        self._stats["total_releases"] += released
        return {"released": released}

    def _phase_reset(self) -> Dict[str, Any]:
        """Reset phase: inject a perturbation when stagnation persists."""
        perturbed = 0
        for state in self._stories.values():
            if state.stagnation_cycles < self._RESET_STAGNATION_CYCLES:
                continue
            # Inject a perturbation beat to break the stall. The delta is
            # chosen to nudge the story out of its near-zero velocity.
            delta = random.choice([-0.25, 0.25, 0.3, -0.2])
            beat = NarrativeBeat(
                beat_id=f"perturb_{state.story_id}_{self._cycle_count}",
                tension_delta=delta,
                weight=0.7,
            )
            state.beats.append(beat)
            state.stagnation_cycles = 0
            state.perturbation_count += 1
            perturbed += 1
            self._record_event("phase_reset", {
                "story_id": state.story_id,
                "perturbation_delta": delta,
            })
        self._stats["total_perturbations"] += perturbed
        return {"perturbed": perturbed}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _compute_velocity(self, state: NarrativeMomentumState) -> float:
        """Compute the narrative velocity as the weighted mean of recent
        tension deltas."""
        recent = list(state.beats)[-self._SENSE_WINDOW:]
        if not recent:
            return 0.0
        weight_sum = sum(b.weight for b in recent)
        if weight_sum <= 0.0:
            return 0.0
        return sum(b.tension_delta * b.weight for b in recent) / weight_sum

    def _classify_regime(self, velocity: float, momentum: float,
                         stagnation_cycles: int) -> MomentumRegime:
        """Classify the current narrative momentum regime."""
        if stagnation_cycles >= self._RESET_STAGNATION_CYCLES:
            return MomentumRegime.STAGNANT
        if abs(momentum) < 0.05 and abs(velocity) < 0.05:
            return MomentumRegime.STAGNANT
        if momentum >= self._RELEASE_CLIMAX_THRESHOLD:
            return MomentumRegime.PEAKING
        if velocity < -0.05:
            return MomentumRegime.RECEDING
        if velocity > 0.12 and momentum > 0.1:
            return MomentumRegime.BUILDING
        if abs(velocity) < 0.08:
            return MomentumRegime.PLATEAU
        return MomentumRegime.BUILDING

    def _choose_directive(self, regime: MomentumRegime,
                          target: GovernorTarget,
                          momentum: float) -> tuple:
        """Choose a steer directive based on the regime and the target.

        Returns a (directive, rationale, intensity) tuple.
        """
        max_int = self._STEER_INTENSITY_MAX
        if target == GovernorTarget.CLIMAX:
            if regime == MomentumRegime.PEAKING:
                return (SteerDirective.HOLD,
                        "momentum near climax, hold for release",
                        min(max_int, momentum * 0.5))
            if regime == MomentumRegime.STAGNANT:
                return (SteerDirective.PERTURB,
                        "stagnation, perturb to restart momentum",
                        max_int * 0.6)
            if regime == MomentumRegime.RECEDING:
                return (SteerDirective.ACCELERATE,
                        "momentum receding from climax, push back up",
                        max_int)
            if regime == MomentumRegime.PLATEAU:
                return (SteerDirective.ACCELERATE,
                        "plateau, accelerate toward climax",
                        max_int * 0.7)
            return (SteerDirective.ACCELERATE,
                    "building, keep accelerating toward climax",
                    max_int * 0.5)
        if target == GovernorTarget.COOLDOWN:
            if regime in (MomentumRegime.BUILDING, MomentumRegime.PEAKING):
                return (SteerDirective.DECELERATE,
                        "cooldown, bleed momentum down",
                        max_int * 0.8)
            return (SteerDirective.HOLD,
                    "cooldown, hold low momentum",
                    max_int * 0.3)
        if target == GovernorTarget.EXPLORATION:
            if regime == MomentumRegime.PEAKING:
                return (SteerDirective.DECELERATE,
                        "exploration, avoid peaking",
                        max_int * 0.6)
            if regime == MomentumRegime.STAGNANT:
                return (SteerDirective.PERTURB,
                        "exploration stalled, perturb gently",
                        max_int * 0.5)
            return (SteerDirective.HOLD,
                    "exploration, hold gentle momentum",
                    max_int * 0.3)
        # CONVERGENCE
        if regime == MomentumRegime.STAGNANT:
            return (SteerDirective.PERTURB,
                    "convergence stalled, perturb to restart",
                    max_int * 0.6)
        if regime in (MomentumRegime.PLATEAU, MomentumRegime.RECEDING):
            return (SteerDirective.ACCELERATE,
                    "convergence, accelerate toward resolution",
                    max_int * 0.7)
        return (SteerDirective.HOLD,
                "convergence, hold course toward resolution",
                max_int * 0.4)

    def _shape_release(self, momentum: float, velocity: float) -> ReleaseShape:
        """Choose the shape a momentum release takes from how sharp the peak is."""
        if velocity > 0.3:
            return ReleaseShape.CRESCENDO
        if velocity < -0.1:
            return ReleaseShape.ABRUPT
        if abs(velocity) < 0.1:
            return ReleaseShape.CADENCE
        return ReleaseShape.DENOUEMENT

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "stories": len(self._stories),
                "stats": dict(self._stats),
            }

    def get_story_state(self, story_id: str) -> Dict[str, Any]:
        with self._global_lock:
            state = self._stories.get(story_id)
            if state is None:
                return {"error": f"Story not found: {story_id}"}
            return {
                "story_id": story_id,
                "target": state.target.value,
                "regime": state.regime.value,
                "current_velocity": state.current_velocity,
                "current_mass": state.current_mass,
                "current_momentum": state.current_momentum,
                "stagnation_cycles": state.stagnation_cycles,
                "release_count": state.release_count,
                "perturbation_count": state.perturbation_count,
                "beats_count": len(state.beats),
                "decisions_count": len(state.decisions),
                "readings_count": len(state.readings),
                "total_beats_logged": state.total_beats_logged,
                "total_decisions_emitted": state.total_decisions_emitted,
            }

    def get_beats(self, story_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            state = self._stories.get(story_id)
            if state is None:
                return {"error": f"Story not found: {story_id}"}
            beats = list(state.beats)[-limit:]
            return {
                "story_id": story_id,
                "beats": [
                    {
                        "beat_id": b.beat_id,
                        "tension_delta": b.tension_delta,
                        "weight": b.weight,
                        "timestamp": b.timestamp,
                    }
                    for b in beats
                ],
            }

    def get_decisions(self, story_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            state = self._stories.get(story_id)
            if state is None:
                return {"error": f"Story not found: {story_id}"}
            decisions = state.decisions[-limit:]
            return {
                "story_id": story_id,
                "decisions": [
                    {
                        "decision_id": d.decision_id,
                        "directive": d.directive.value,
                        "target": d.target.value,
                        "rationale": d.rationale,
                        "intensity": d.intensity,
                        "created_at": d.created_at,
                    }
                    for d in decisions
                ],
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Simulation / Reset
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic stories and beats, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_stories()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_stories(self) -> None:
        """Seed a small synthetic set of stories with distinct momentum profiles."""
        seeds = [
            ("sim_build", GovernorTarget.CLIMAX, [
                ("sim_build_b1", 0.15, 0.6),
                ("sim_build_b2", 0.20, 0.7),
                ("sim_build_b3", 0.25, 0.8),
            ]),
            ("sim_stagnant", GovernorTarget.CLIMAX, [
                ("sim_stag_b1", 0.01, 0.3),
                ("sim_stag_b2", -0.01, 0.3),
                ("sim_stag_b3", 0.0, 0.3),
            ]),
            ("sim_explore", GovernorTarget.EXPLORATION, [
                ("sim_exp_b1", 0.10, 0.5),
                ("sim_exp_b2", -0.05, 0.4),
            ]),
        ]
        for story_id, target, beats in seeds:
            if story_id not in self._stories:
                self.register_story(story_id, target)
            for beat_id, delta, weight in beats:
                state = self._stories.get(story_id)
                if state is None:
                    continue
                if not any(b.beat_id == beat_id for b in state.beats):
                    self.log_beat(story_id, beat_id, delta, weight)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._stories.clear()
            self._events_log.clear()
            self._phase = NarrativeMomentumPhase.SENSE
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
