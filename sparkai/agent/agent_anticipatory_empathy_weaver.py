"""
SparkLabs Agent - Anticipatory Empathy Weaver

The AgentAnticipatoryEmpathyWeaver weaves empathy toward the *future* emotional
states of other agents, not their present ones. Ordinary empathy mirrors what
another agent feels right now; anticipatory empathy models where that agent's
affect is heading and prepares a response calibrated to the destination rather
than the departure point.

A response tuned to the present tends to arrive one step behind; a response
tuned to the anticipated future tends to arrive already shaped to meet the
agent where they will be. When reality diverges from the projection, the
weaver recalibrates its projection model so the next anticipation lands closer.

Architecture:
  INTERPRET    ->  ANTICIPATE   ->  RESONATE   ->  RESPOND      ->  RECALIBRATE
  (read another  (project where   (weave an      (prepare a        (when reality
   agent's        their emotion    anticipatory   response tuned    diverges from
   current        is heading)      empathy        to the            the projection,
   trajectory)                     thread toward  anticipated,      the projection
                                  that future)    not present,      model is tuned
                                                  state)            to land closer
                                                                    next cycle->...)

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

class AnticipatoryEmpathyPhase(Enum):
    """Phases of the anticipatory empathy cycle."""
    INTERPRET = "interpret"        # read another agent's current emotional trajectory
    ANTICIPATE = "anticipate"      # project where their emotion is heading
    RESONATE = "resonate"          # weave an anticipatory empathy thread toward the future
    RESPOND = "respond"            # prepare a response calibrated to the anticipated state
    RECALIBRATE = "recalibrate"    # when reality diverges, tune the projection model


class EmotionalTrajectory(Enum):
    """The direction an agent's affect is moving."""
    RISING = "rising"              # valence climbing, arousal building
    FALLING = "falling"            # valence dropping, arousal fading
    PLATEAU = "plateau"            # holding steady
    OSCILLATING = "oscillating"    # swinging back and forth
    SPIKING = "spiking"            # sharp upward burst


class AnticipationValence(Enum):
    """The emotional coloring of the anticipated future."""
    HOPEFUL = "hopeful"            # the projected future leans bright
    DREADFUL = "dreadful"          # the projected future leans dark
    TENDER = "tender"              # the projected future leans soft and close
    WARY = "wary"                  # the projected future leans uncertain


class EmpathyThreadState(Enum):
    """Lifecycle of an anticipatory empathy thread."""
    PENDING = "pending"            # thread created, not yet woven
    INTERPRETED = "interpreted"    # source trajectory read
    ANTICIPATED = "anticipated"    # future projected
    RESONATING = "resonating"      # thread woven toward the future
    RESPONDED = "responded"        # response prepared
    RECALIBRATED = "recalibrated"  # projection model adjusted after drift


class ProjectionConfidence(Enum):
    """How much trust the weaver places in its own projection."""
    FRAGILE = "fragile"            # too little data to project firmly
    TENTATIVE = "tentative"        # a projection exists but drift is high
    STABLE = "stable"              # projection tracks reality within tolerance
    CONFIDENT = "confident"        # projection has held across several cycles


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class EmotionalReading:
    """A single reading of another agent's current affect."""
    reading_id: str
    target_agent_id: str
    valence: float = 0.5                  # 0.0-1.0, unpleasant to pleasant
    arousal: float = 0.5                  # 0.0-1.0, calm to activated
    trajectory: EmotionalTrajectory = EmotionalTrajectory.PLATEAU
    confidence: float = 0.5               # 0.0-1.0, how reliable the reading is
    timestamp: float = field(default_factory=time.time)


@dataclass
class AnticipatedFuture:
    """A projection of another agent's future affect."""
    future_id: str
    target_agent_id: str
    projected_valence: float = 0.5        # 0.0-1.0
    projected_arousal: float = 0.5        # 0.0-1.0
    horizon_cycles: int = 3               # how many cycles ahead this projects
    valence: AnticipationValence = AnticipationValence.WARY
    confidence: ProjectionConfidence = ProjectionConfidence.FRAGILE
    created_at: float = field(default_factory=time.time)


@dataclass
class EmpathyThread:
    """An anticipatory empathy thread woven toward a projected future."""
    thread_id: str
    target_agent_id: str
    anticipated_future_id: str
    valence: AnticipationValence = AnticipationValence.WARY
    state: EmpathyThreadState = EmpathyThreadState.PENDING
    resonance_strength: float = 0.0       # 0.0-1.0, how strongly woven
    prepared_response: str = ""
    calibration_drift: float = 0.0        # 0.0-1.0, divergence from reality
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class EmpathyTargetState:
    """Per-target anticipatory empathy state."""
    target_agent_id: str
    readings: List[EmotionalReading] = field(default_factory=list)
    anticipated_futures: Dict[str, AnticipatedFuture] = field(default_factory=dict)
    threads: Dict[str, EmpathyThread] = field(default_factory=dict)
    projection_bias: float = 0.0          # learned correction applied to projections
    total_readings: int = 0
    total_anticipated: int = 0
    total_threads_woven: int = 0
    total_responses_prepared: int = 0
    total_recalibrations: int = 0


# =============================================================================
# Weaver
# =============================================================================

class AgentAnticipatoryEmpathyWeaver:
    """
    Thread-safe singleton orchestrating anticipatory empathy.

    Usage:
        weaver = AgentAnticipatoryEmpathyWeaver.get_instance()
        weaver.register_target("npc_42")
        weaver.record_reading("npc_42", "r1", 0.3, 0.8, EmotionalTrajectory.FALLING)
        weaver.cycle()
        state = weaver.get_target_state("npc_42")
    """

    _instance: Optional["AgentAnticipatoryEmpathyWeaver"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _ANTICIPATE_HORIZON_DEFAULT = 3        # cycles ahead to project by default
    _RESONANCE_STRENGTH_BASE = 0.3         # baseline resonance for a fresh thread
    _RECALIBRATE_DRIFT_THRESHOLD = 0.3     # drift above this triggers recalibration
    _MAX_READINGS_PER_TARGET = 50
    _MAX_THREADS_PER_TARGET = 40
    _MAX_TARGETS = 30
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._targets: Dict[str, EmpathyTargetState] = {}
        self._phase: AnticipatoryEmpathyPhase = AnticipatoryEmpathyPhase.INTERPRET
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentAnticipatoryEmpathyWeaver":
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
            "total_targets": 0,
            "total_readings": 0,
            "total_anticipated": 0,
            "total_threads_woven": 0,
            "total_responses_prepared": 0,
            "total_recalibrations": 0,
            "active_threads": 0,
            "avg_resonance_strength": 0.0,
            "avg_calibration_drift": 0.0,
            "projection_confidence": ProjectionConfidence.FRAGILE.value,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._targets:
            return
        resonance_values: List[float] = []
        drift_values: List[float] = []
        active_threads = 0
        for target in self._targets.values():
            for thread in target.threads.values():
                if thread.state in (EmpathyThreadState.RESONATING,
                                    EmpathyThreadState.RESPONDED,
                                    EmpathyThreadState.RECALIBRATED):
                    active_threads += 1
                    resonance_values.append(thread.resonance_strength)
                    drift_values.append(thread.calibration_drift)
        self._stats["total_targets"] = len(self._targets)
        self._stats["active_threads"] = active_threads
        self._stats["avg_resonance_strength"] = (
            sum(resonance_values) / len(resonance_values) if resonance_values else 0.0
        )
        self._stats["avg_calibration_drift"] = (
            sum(drift_values) / len(drift_values) if drift_values else 0.0
        )
        # Derive overall projection confidence from drift and data volume.
        self._stats["projection_confidence"] = self._derive_projection_confidence().value

    def _derive_projection_confidence(self) -> ProjectionConfidence:
        total_readings = self._stats.get("total_readings", 0)
        avg_drift = self._stats.get("avg_calibration_drift", 0.0)
        active_threads = self._stats.get("active_threads", 0)
        if total_readings < 3 or active_threads == 0:
            return ProjectionConfidence.FRAGILE
        if avg_drift > self._RECALIBRATE_DRIFT_THRESHOLD:
            return ProjectionConfidence.TENTATIVE
        if avg_drift < self._RECALIBRATE_DRIFT_THRESHOLD * 0.5 and total_readings >= 10:
            return ProjectionConfidence.CONFIDENT
        return ProjectionConfidence.STABLE

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Target Management
    # -------------------------------------------------------------------------

    def register_target(self, target_id: str) -> Dict[str, Any]:
        """Register a new target agent for anticipatory empathy."""
        with self._global_lock:
            if target_id in self._targets:
                return {"error": f"Target already registered: {target_id}"}
            if len(self._targets) >= self._MAX_TARGETS:
                return {"error": f"Max targets reached: {self._MAX_TARGETS}"}
            target = EmpathyTargetState(target_agent_id=target_id)
            self._targets[target_id] = target
            self._record_event("target_registered", {"target_agent_id": target_id})
            return {
                "target_agent_id": target_id,
                "registered": True,
            }

    def remove_target(self, target_id: str) -> Dict[str, Any]:
        with self._global_lock:
            target = self._targets.pop(target_id, None)
            if target is None:
                return {"error": f"Target not found: {target_id}"}
            self._record_event("target_removed", {"target_agent_id": target_id})
            return {
                "removed": target_id,
                "cleared_readings": len(target.readings),
                "cleared_futures": len(target.anticipated_futures),
                "cleared_threads": len(target.threads),
            }

    # -------------------------------------------------------------------------
    # Reading Intake
    # -------------------------------------------------------------------------

    def record_reading(self, target_id: str, reading_id: str,
                       valence: float, arousal: float,
                       trajectory: EmotionalTrajectory) -> Dict[str, Any]:
        """Record a fresh emotional reading for a target agent."""
        with self._global_lock:
            target = self._targets.get(target_id)
            if target is None:
                return {"error": f"Target not found: {target_id}"}
            if any(r.reading_id == reading_id for r in target.readings):
                return {"error": f"Reading already exists: {reading_id}"}
            reading = EmotionalReading(
                reading_id=reading_id,
                target_agent_id=target_id,
                valence=max(0.0, min(1.0, valence)),
                arousal=max(0.0, min(1.0, arousal)),
                trajectory=trajectory,
                confidence=self._estimate_reading_confidence(target),
            )
            target.readings.append(reading)
            if len(target.readings) > self._MAX_READINGS_PER_TARGET:
                target.readings = target.readings[-self._MAX_READINGS_PER_TARGET:]
            target.total_readings += 1
            self._stats["total_readings"] += 1
            self._record_event("reading_recorded", {
                "target_agent_id": target_id,
                "reading_id": reading_id,
                "valence": reading.valence,
                "arousal": reading.arousal,
                "trajectory": trajectory.value,
            })
            return {
                "target_agent_id": target_id,
                "reading_id": reading_id,
                "valence": reading.valence,
                "arousal": reading.arousal,
                "trajectory": trajectory.value,
                "confidence": reading.confidence,
            }

    def _estimate_reading_confidence(self, target: EmpathyTargetState) -> float:
        """Estimate confidence in a reading based on how much history exists."""
        # More history means the weaver trusts its own readings more.
        base = 0.4
        history_bonus = min(0.4, len(target.readings) * 0.02)
        return max(0.0, min(1.0, base + history_bonus))

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single anticipatory empathy cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = AnticipatoryEmpathyPhase.INTERPRET
            phase_outputs["interpret"] = self._phase_interpret()
            self._phase = AnticipatoryEmpathyPhase.ANTICIPATE
            phase_outputs["anticipate"] = self._phase_anticipate()
            self._phase = AnticipatoryEmpathyPhase.RESONATE
            phase_outputs["resonate"] = self._phase_resonate()
            self._phase = AnticipatoryEmpathyPhase.RESPOND
            phase_outputs["respond"] = self._phase_respond()
            self._phase = AnticipatoryEmpathyPhase.RECALIBRATE
            phase_outputs["recalibrate"] = self._phase_recalibrate()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_interpret(self) -> Dict[str, Any]:
        """Interpret phase: read each target's most recent emotional trajectory."""
        interpreted = 0
        for target in self._targets.values():
            if not target.readings:
                continue
            # Mark any pending threads as having their source trajectory read.
            for thread in target.threads.values():
                if thread.state == EmpathyThreadState.PENDING:
                    thread.state = EmpathyThreadState.INTERPRETED
                    thread.updated_at = time.time()
            interpreted += 1
        self._record_event("phase_interpret", {"interpreted": interpreted})
        return {"interpreted": interpreted}

    def _phase_anticipate(self) -> Dict[str, Any]:
        """Anticipate phase: project where each target's affect is heading."""
        anticipated = 0
        for target in self._targets.values():
            if not target.readings:
                continue
            future = self._project_future(target)
            if future is None:
                continue
            target.anticipated_futures[future.future_id] = future
            # Move interpreted threads into the anticipated state.
            for thread in target.threads.values():
                if thread.state == EmpathyThreadState.INTERPRETED:
                    thread.anticipated_future_id = future.future_id
                    thread.valence = future.valence
                    thread.state = EmpathyThreadState.ANTICIPATED
                    thread.updated_at = time.time()
            target.total_anticipated += 1
            anticipated += 1
        self._stats["total_anticipated"] += anticipated
        self._record_event("phase_anticipate", {"anticipated": anticipated})
        return {"anticipated": anticipated}

    def _phase_resonate(self) -> Dict[str, Any]:
        """Resonate phase: weave anticipatory empathy threads toward projected futures."""
        woven = 0
        for target in self._targets.values():
            if not target.anticipated_futures:
                continue
            # Pick the most recent anticipated future for this target.
            latest_future = max(
                target.anticipated_futures.values(),
                key=lambda f: f.created_at,
            )
            # Weave a fresh thread only if no active thread targets this future.
            already_woven = any(
                t.anticipated_future_id == latest_future.future_id
                and t.state in (EmpathyThreadState.RESONATING,
                                EmpathyThreadState.RESPONDED,
                                EmpathyThreadState.RECALIBRATED)
                for t in target.threads.values()
            )
            if not already_woven:
                thread = self._weave_thread(target.target_agent_id, latest_future)
                target.threads[thread.thread_id] = thread
                target.total_threads_woven += 1
                woven += 1
            # Move any anticipated threads into the resonating state.
            for thread in target.threads.values():
                if thread.state == EmpathyThreadState.ANTICIPATED:
                    thread.state = EmpathyThreadState.RESONATING
                    thread.resonance_strength = self._RESONANCE_STRENGTH_BASE
                    thread.updated_at = time.time()
        self._stats["total_threads_woven"] += woven
        self._record_event("phase_resonate", {"woven": woven})
        return {"woven": woven}

    def _phase_respond(self) -> Dict[str, Any]:
        """Respond phase: prepare a response calibrated to the anticipated future."""
        prepared = 0
        for target in self._targets.values():
            for thread in target.threads.values():
                if thread.state != EmpathyThreadState.RESONATING:
                    continue
                future = target.anticipated_futures.get(thread.anticipated_future_id)
                if future is None:
                    continue
                response = self._prepare_response(future, thread)
                thread.prepared_response = response
                thread.state = EmpathyThreadState.RESPONDED
                thread.updated_at = time.time()
                target.total_responses_prepared += 1
                prepared += 1
        self._stats["total_responses_prepared"] += prepared
        self._record_event("phase_respond", {"prepared": prepared})
        return {"prepared": prepared}

    def _phase_recalibrate(self) -> Dict[str, Any]:
        """Recalibrate phase: measure drift and tune the projection model."""
        recalibrated = 0
        for target in self._targets.values():
            if not target.readings or not target.threads:
                continue
            latest = target.readings[-1]
            for thread in list(target.threads.values()):
                if thread.state != EmpathyThreadState.RESPONDED:
                    continue
                future = target.anticipated_futures.get(thread.anticipated_future_id)
                if future is None:
                    continue
                drift = self._measure_drift(latest, future)
                thread.calibration_drift = drift
                if drift > self._RECALIBRATE_DRIFT_THRESHOLD:
                    # Tune the projection bias to push the next projection
                    # toward where reality actually landed.
                    correction = (latest.valence - future.projected_valence) * 0.3
                    target.projection_bias = max(
                        -0.5, min(0.5, target.projection_bias + correction)
                    )
                    future.confidence = ProjectionConfidence.TENTATIVE
                    thread.state = EmpathyThreadState.RECALIBRATED
                    thread.updated_at = time.time()
                    target.total_recalibrations += 1
                    recalibrated += 1
                else:
                    # Projection held; let confidence climb toward confident.
                    if future.confidence == ProjectionConfidence.TENTATIVE:
                        future.confidence = ProjectionConfidence.STABLE
                    elif future.confidence == ProjectionConfidence.STABLE:
                        future.confidence = ProjectionConfidence.CONFIDENT
                    thread.state = EmpathyThreadState.RECALIBRATED
                    thread.updated_at = time.time()
        self._stats["total_recalibrations"] += recalibrated
        self._record_event("phase_recalibrate", {"recalibrated": recalibrated})
        return {"recalibrated": recalibrated}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _project_future(self, target: EmpathyTargetState) -> Optional[AnticipatedFuture]:
        """Project a target's future affect from its recent readings."""
        readings = target.readings
        if not readings:
            return None
        latest = readings[-1]
        # Project based on the latest trajectory. The bias is a learned
        # correction accumulated from past recalibrations.
        bias = target.projection_bias
        if latest.trajectory == EmotionalTrajectory.RISING:
            projected_valence = min(1.0, latest.valence + 0.15 + bias)
            projected_arousal = min(1.0, latest.arousal + 0.10)
        elif latest.trajectory == EmotionalTrajectory.FALLING:
            projected_valence = max(0.0, latest.valence - 0.15 + bias)
            projected_arousal = max(0.0, latest.arousal - 0.10)
        elif latest.trajectory == EmotionalTrajectory.SPIKING:
            projected_valence = min(1.0, latest.valence + 0.25 + bias)
            projected_arousal = 1.0
        elif latest.trajectory == EmotionalTrajectory.OSCILLATING:
            # Oscillation dampens toward the midpoint over the horizon.
            projected_valence = 0.5 + (latest.valence - 0.5) * 0.5 + bias
            projected_arousal = min(1.0, latest.arousal + 0.05)
        else:  # PLATEAU
            projected_valence = max(0.0, min(1.0, latest.valence + bias))
            projected_arousal = latest.arousal
        valence = self._classify_valence(projected_valence, projected_arousal)
        confidence = self._classify_confidence(target)
        return AnticipatedFuture(
            future_id=f"future_{target.target_agent_id}_{self._cycle_count}",
            target_agent_id=target.target_agent_id,
            projected_valence=projected_valence,
            projected_arousal=projected_arousal,
            horizon_cycles=self._ANTICIPATE_HORIZON_DEFAULT,
            valence=valence,
            confidence=confidence,
        )

    def _classify_valence(self, valence: float, arousal: float) -> AnticipationValence:
        """Classify the emotional coloring of a projected future."""
        if valence >= 0.65 and arousal <= 0.6:
            return AnticipationValence.TENDER
        if valence >= 0.55:
            return AnticipationValence.HOPEFUL
        if valence <= 0.35 and arousal >= 0.6:
            return AnticipationValence.DREADFUL
        if valence <= 0.45:
            return AnticipationValence.DREADFUL
        return AnticipationValence.WARY

    def _classify_confidence(self, target: EmpathyTargetState) -> ProjectionConfidence:
        """Classify how much trust to place in a fresh projection."""
        if len(target.readings) < 3:
            return ProjectionConfidence.FRAGILE
        drift_estimate = abs(target.projection_bias)
        if drift_estimate > self._RECALIBRATE_DRIFT_THRESHOLD:
            return ProjectionConfidence.TENTATIVE
        if drift_estimate < self._RECALIBRATE_DRIFT_THRESHOLD * 0.5:
            return ProjectionConfidence.CONFIDENT
        return ProjectionConfidence.STABLE

    def _weave_thread(self, target_id: str,
                      future: AnticipatedFuture) -> EmpathyThread:
        """Weave a fresh anticipatory empathy thread toward a projected future."""
        # Resonance strength scales with projection confidence.
        confidence_weight = {
            ProjectionConfidence.FRAGILE: 0.2,
            ProjectionConfidence.TENTATIVE: 0.3,
            ProjectionConfidence.STABLE: 0.5,
            ProjectionConfidence.CONFIDENT: 0.7,
        }.get(future.confidence, self._RESONANCE_STRENGTH_BASE)
        resonance = max(0.0, min(1.0,
            self._RESONANCE_STRENGTH_BASE + confidence_weight))
        return EmpathyThread(
            thread_id=f"thread_{target_id}_{future.future_id}_{self._cycle_count}",
            target_agent_id=target_id,
            anticipated_future_id=future.future_id,
            valence=future.valence,
            state=EmpathyThreadState.PENDING,
            resonance_strength=resonance,
            prepared_response="",
            calibration_drift=0.0,
        )

    def _prepare_response(self, future: AnticipatedFuture,
                          thread: EmpathyThread) -> str:
        """Prepare a response calibrated to the anticipated, not present, state."""
        # The response is shaped to meet the agent where they will be, not where
        # they are. Each anticipated valence calls for a different posture.
        if future.valence == AnticipationValence.HOPEFUL:
            return (f"await {future.target_agent_id} at the bright edge "
                    f"of their trajectory; meet rising hope with shared momentum")
        if future.valence == AnticipationValence.DREADFUL:
            return (f"hold space for {future.target_agent_id} before the dread "
                    f"lands; prepare a steadying presence calibrated to the fall")
        if future.valence == AnticipationValence.TENDER:
            return (f"soften toward {future.target_agent_id}; the projected "
                    f"future leans close and quiet, meet it gently")
        # WARY
        return (f"stay ready for {future.target_agent_id}; the projected future "
                f"is uncertain, hold a flexible stance until it clarifies")

    def _measure_drift(self, reading: EmotionalReading,
                       future: AnticipatedFuture) -> float:
        """Measure how far reality has diverged from an earlier projection."""
        # Drift is the average distance between the projected affect and the
        # realized affect, scaled to 0.0-1.0.
        valence_gap = abs(reading.valence - future.projected_valence)
        arousal_gap = abs(reading.arousal - future.projected_arousal)
        return max(0.0, min(1.0, (valence_gap + arousal_gap) / 2.0))

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "targets": len(self._targets),
                "stats": dict(self._stats),
            }

    def get_target_state(self, target_id: str) -> Dict[str, Any]:
        with self._global_lock:
            target = self._targets.get(target_id)
            if target is None:
                return {"error": f"Target not found: {target_id}"}
            return {
                "target_agent_id": target_id,
                "readings_count": len(target.readings),
                "anticipated_futures_count": len(target.anticipated_futures),
                "threads_count": len(target.threads),
                "projection_bias": target.projection_bias,
                "total_readings": target.total_readings,
                "total_anticipated": target.total_anticipated,
                "total_threads_woven": target.total_threads_woven,
                "total_responses_prepared": target.total_responses_prepared,
                "total_recalibrations": target.total_recalibrations,
            }

    def get_threads(self, target_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            target = self._targets.get(target_id)
            if target is None:
                return {"error": f"Target not found: {target_id}"}
            threads = sorted(
                target.threads.values(),
                key=lambda t: t.created_at,
                reverse=True,
            )[:limit]
            return {
                "target_agent_id": target_id,
                "threads": [
                    {
                        "thread_id": t.thread_id,
                        "anticipated_future_id": t.anticipated_future_id,
                        "valence": t.valence.value,
                        "state": t.state.value,
                        "resonance_strength": t.resonance_strength,
                        "prepared_response": t.prepared_response,
                        "calibration_drift": t.calibration_drift,
                        "created_at": t.created_at,
                        "updated_at": t.updated_at,
                    }
                    for t in threads
                ],
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Simulation / Reset
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic targets and readings, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_targets()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_targets(self) -> None:
        """Seed a small synthetic set of targets with distinct trajectories."""
        seed_targets = [
            ("sim_orphan", "sim_r1", 0.2, 0.7, EmotionalTrajectory.FALLING),
            ("sim_healer", "sim_r2", 0.6, 0.4, EmotionalTrajectory.RISING),
            ("sim_exile", "sim_r3", 0.3, 0.6, EmotionalTrajectory.OSCILLATING),
            ("sim_champion", "sim_r4", 0.8, 0.9, EmotionalTrajectory.SPIKING),
        ]
        for target_id, reading_id, valence, arousal, trajectory in seed_targets:
            if target_id not in self._targets:
                self.register_target(target_id)
            target = self._targets.get(target_id)
            if target is None:
                continue
            if not any(r.reading_id == reading_id for r in target.readings):
                self.record_reading(target_id, reading_id, valence, arousal, trajectory)
            # Add a second reading for some targets to give projection history.
            second_id = reading_id + "_b"
            if not any(r.reading_id == second_id for r in target.readings):
                self.record_reading(
                    target_id, second_id,
                    max(0.0, min(1.0, valence + random.uniform(-0.1, 0.1))),
                    max(0.0, min(1.0, arousal + random.uniform(-0.1, 0.1))),
                    trajectory,
                )

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._targets.clear()
            self._events_log.clear()
            self._phase = AnticipatoryEmpathyPhase.INTERPRET
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
