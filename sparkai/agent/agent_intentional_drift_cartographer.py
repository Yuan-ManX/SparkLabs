"""
SparkLabs Agent - Intentional Drift Cartographer

An agent's intentions are not fixed points; they wander. Over time the
position of an intention - the spot where the agent currently aims -
shifts in response to fresh evidence, fatigue, distraction, or
refinement. Some of this wandering is the agent doing its job well: an
exploratory drift opens new ground, a progressive drift converges on
the goal. Some of it is the agent quietly losing the plot: an erosive
drift erodes the goal until nothing is left, an oscillatory drift
thrashes without ever settling, a stuck drift freezes in place.

The AgentIntentionalDriftCartographer watches each tracked intention
wander. It records where the intention sits each cycle, fits a drift
pattern to the recent track, projects where the pattern is carrying
the intention, intercepts the intentions whose projected path is
destructive, and resonates with the productive ones by feeding their
drift back into the model so refinement can compound.

Architecture:
  TRACK      ->  MODEL     ->  PREDICT   ->  INTERCEPT  ->  RESONATE
  (log the     (fit a drift  (project      (intentions        (productive
   current     pattern to    where the     whose projected    drift is fed
   position    each          intention     drift is           back into the
   of each     intention's   is heading)   destructive        intention model,
   tracked     recent                      are caught before  so refinement
   intention)  track)                      they derail)       compounds)

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

class IntentionalDriftPhase(Enum):
    """Phases of the intentional drift cycle."""
    TRACK = "track"            # log the current position of each tracked intention
    MODEL = "model"            # fit a drift pattern to each intention's recent track
    PREDICT = "predict"        # project where each intention is heading
    INTERCEPT = "intercept"    # intercept intentions whose predicted drift is destructive
    RESONATE = "resonate"      # feed productive drift back into the intention model


class DriftKind(Enum):
    """The shape of an intention's drift over its recent track."""
    PROGRESSIVE = "progressive"    # the intention is converging on its goal
    EXPLORATORY = "exploratory"    # the intention is wandering productively
    EROSIVE = "erosive"            # the intention is losing fidelity toward its goal
    OSCILLATORY = "oscillatory"    # the intention is thrashing without settling
    STUCK = "stuck"                # the intention is not moving at all


class DriftValence(Enum):
    """Whether a drift is helping, hurting, or neither."""
    PRODUCTIVE = "productive"      # the drift is moving the intention toward its goal
    DESTRUCTIVE = "destructive"    # the drift is moving the intention away from its goal
    NEUTRAL = "neutral"            # the drift is neither clearly helping nor hurting


class IntentionState(Enum):
    """State of an individual tracked intention."""
    ANCHORED = "anchored"          # the intention is holding its position with high fidelity
    TRACKING = "tracking"          # the intention is being logged but no drift pattern yet
    DRIFTING = "drifting"          # the intention has a fitted drift pattern
    INTERCEPTED = "intercepted"    # the intention's destructive drift has been caught
    RESONATING = "resonating"      # the intention's productive drift is being amplified
    LOST = "lost"                  # the intention has drifted past the point of recovery


class CartographerStance(Enum):
    """How eagerly the cartographer intercepts destructive drift."""
    PERMISSIVE = "permissive"      # only the most destructive drift is intercepted
    VIGILANT = "vigilant"          # moderate interception threshold
    STRICT = "strict"              # any drift toward destructive is intercepted


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class IntentionTrack:
    """A single logged position of an intention at one moment in time."""
    intention_id: str
    goal_label: str
    position: float = 0.5                  # 0.0-1.0, where the intention currently sits
    fidelity: float = 0.7                  # 0.0-1.0, how aligned the position is with the goal
    drift_kind: DriftKind = DriftKind.STUCK
    drift_valence: DriftValence = DriftValence.NEUTRAL
    timestamp: float = field(default_factory=time.time)


@dataclass
class DriftModel:
    """A fitted drift pattern for a single intention."""
    intention_id: str
    kind: DriftKind = DriftKind.STUCK
    valence: DriftValence = DriftValence.NEUTRAL
    velocity: float = 0.0                  # position delta per track, signed
    predicted_position: float = 0.5        # 0.0-1.0, where the intention is heading
    confidence: float = 0.0                # 0.0-1.0, how reliable the model is


@dataclass
class InterceptionRecord:
    """A record of one interception of destructive drift."""
    intention_id: str
    reason: str = ""
    severity: float = 0.5                  # 0.0-1.0
    corrective_note: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class IntentionMap:
    """Per-intention cartographer state: tracks, model, interceptions, stats."""
    intention_id: str
    goal_label: str
    tracks: Deque[IntentionTrack] = field(default_factory=lambda: deque(maxlen=60))
    model: Optional[DriftModel] = None
    interceptions: List[InterceptionRecord] = field(default_factory=list)
    state: IntentionState = IntentionState.TRACKING
    last_position: float = 0.5
    last_fidelity: float = 0.7
    total_tracks: int = 0
    total_interceptions: int = 0
    total_resonances: int = 0
    resonance_boost: float = 0.0           # accumulated productive-drift feedback
    registered_at: float = field(default_factory=time.time)


# =============================================================================
# Cartographer
# =============================================================================

class AgentIntentionalDriftCartographer:
    """
    Thread-safe singleton that maps how an agent's own intentions drift
    over time.

    Usage:
        cartographer = AgentIntentionalDriftCartographer.get_instance()
        cartographer.register_intention("i1", "reach the summit", 0.5)
        cartographer.log_track("i1", "t1", 0.55, 0.72)
        cartographer.cycle()
        state = cartographer.get_intention_state("i1")
    """

    _instance: Optional["AgentIntentionalDriftCartographer"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _TRACK_WINDOW = 10                     # how many recent tracks the model fits
    _PREDICT_HORIZON = 3                   # how many steps ahead to project
    _INTERCEPT_DESTRUCTIVE_THRESHOLD = 0.5  # valence score above which we intercept
    _RESONATE_GAIN = 0.15                  # how much productive drift feeds back
    _MAX_TRACKS_PER_INTENTION = 60
    _MAX_INTENTIONS = 40
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._intentions: Dict[str, IntentionMap] = {}
        self._phase: IntentionalDriftPhase = IntentionalDriftPhase.TRACK
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()
        self._stance: CartographerStance = CartographerStance.VIGILANT

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentIntentionalDriftCartographer":
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
            "total_intentions": 0,
            "total_tracks": 0,
            "total_interceptions": 0,
            "total_resonances": 0,
            "drifting_intentions": 0,
            "intercepted_intentions": 0,
            "resonating_intentions": 0,
            "lost_intentions": 0,
            "avg_velocity": 0.0,
            "avg_confidence": 0.0,
            "destructive_ratio": 0.0,
            "stance": self._stance.value if hasattr(self, "_stance") else CartographerStance.VIGILANT.value,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._intentions:
            self._stats["total_intentions"] = 0
            self._stats["drifting_intentions"] = 0
            self._stats["intercepted_intentions"] = 0
            self._stats["resonating_intentions"] = 0
            self._stats["lost_intentions"] = 0
            self._stats["avg_velocity"] = 0.0
            self._stats["avg_confidence"] = 0.0
            self._stats["destructive_ratio"] = 0.0
            self._stats["stance"] = self._stance.value
            return
        velocities: List[float] = []
        confidences: List[float] = []
        destructive = 0
        with_models = 0
        drifting = 0
        intercepted = 0
        resonating = 0
        lost = 0
        for imap in self._intentions.values():
            if imap.state == IntentionState.DRIFTING:
                drifting += 1
            elif imap.state == IntentionState.INTERCEPTED:
                intercepted += 1
            elif imap.state == IntentionState.RESONATING:
                resonating += 1
            elif imap.state == IntentionState.LOST:
                lost += 1
            if imap.model is not None:
                with_models += 1
                velocities.append(imap.model.velocity)
                confidences.append(imap.model.confidence)
                if imap.model.valence == DriftValence.DESTRUCTIVE:
                    destructive += 1
        self._stats["total_intentions"] = len(self._intentions)
        self._stats["drifting_intentions"] = drifting
        self._stats["intercepted_intentions"] = intercepted
        self._stats["resonating_intentions"] = resonating
        self._stats["lost_intentions"] = lost
        self._stats["avg_velocity"] = (
            sum(velocities) / len(velocities) if velocities else 0.0
        )
        self._stats["avg_confidence"] = (
            sum(confidences) / len(confidences) if confidences else 0.0
        )
        self._stats["destructive_ratio"] = (
            destructive / with_models if with_models else 0.0
        )
        self._stats["stance"] = self._stance.value

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Intention Management
    # -------------------------------------------------------------------------

    def register_intention(self, intention_id: str, goal_label: str,
                           initial_position: float = 0.5) -> Dict[str, Any]:
        """Register a new intention for the cartographer to track."""
        with self._global_lock:
            if intention_id in self._intentions:
                return {"error": f"Intention already registered: {intention_id}"}
            if len(self._intentions) >= self._MAX_INTENTIONS:
                return {"error": f"Max intentions reached: {self._MAX_INTENTIONS}"}
            position = max(0.0, min(1.0, initial_position))
            imap = IntentionMap(
                intention_id=intention_id,
                goal_label=goal_label,
                last_position=position,
                last_fidelity=0.7,
            )
            imap.tracks = deque(maxlen=self._MAX_TRACKS_PER_INTENTION)
            self._intentions[intention_id] = imap
            self._record_event("intention_registered", {
                "intention_id": intention_id,
                "goal_label": goal_label,
                "initial_position": position,
            })
            return {
                "intention_id": intention_id,
                "goal_label": goal_label,
                "initial_position": position,
            }

    def remove_intention(self, intention_id: str) -> Dict[str, Any]:
        """Stop tracking an intention."""
        with self._global_lock:
            imap = self._intentions.pop(intention_id, None)
            if imap is None:
                return {"error": f"Intention not found: {intention_id}"}
            self._record_event("intention_removed", {
                "intention_id": intention_id,
                "cleared_tracks": len(imap.tracks),
                "cleared_interceptions": len(imap.interceptions),
            })
            return {
                "removed": intention_id,
                "cleared_tracks": len(imap.tracks),
                "cleared_interceptions": len(imap.interceptions),
            }

    def set_stance(self, stance: CartographerStance) -> Dict[str, Any]:
        """Set how eagerly the cartographer intercepts destructive drift."""
        with self._global_lock:
            self._stance = stance
            self._stats["stance"] = stance.value
            self._record_event("stance_set", {"stance": stance.value})
            return {"stance": stance.value}

    # -------------------------------------------------------------------------
    # Track Intake
    # -------------------------------------------------------------------------

    def log_track(self, intention_id: str, track_id: str,
                  position: float, fidelity: float = 0.7) -> Dict[str, Any]:
        """Log a single track of where an intention currently sits."""
        with self._global_lock:
            imap = self._intentions.get(intention_id)
            if imap is None:
                return {"error": f"Intention not found: {intention_id}"}
            # Reject duplicate track ids within the intention.
            if any(getattr(t, "track_id", None) == track_id for t in imap.tracks):
                return {"error": f"Track already exists: {track_id}"}
            position = max(0.0, min(1.0, position))
            fidelity = max(0.0, min(1.0, fidelity))
            # Provisionally classify this single track's kind and valence
            # using the previous track as a reference point.
            prev_position = imap.last_position
            prev_fidelity = imap.last_fidelity
            drift_kind = self._fit_drift_kind_single(prev_position, position,
                                                    prev_fidelity, fidelity)
            drift_valence = self._classify_valence_single(drift_kind, prev_fidelity,
                                                         fidelity)
            track = IntentionTrack(
                intention_id=intention_id,
                goal_label=imap.goal_label,
                position=position,
                fidelity=fidelity,
                drift_kind=drift_kind,
                drift_valence=drift_valence,
            )
            # Attach the track_id to the track for deduplication.
            track.__dict__["track_id"] = track_id
            imap.tracks.append(track)
            imap.last_position = position
            imap.last_fidelity = fidelity
            imap.total_tracks += 1
            self._stats["total_tracks"] = self._stats.get("total_tracks", 0) + 1
            # A freshly tracked intention that has more than one sample is
            # considered to be drifting until the model says otherwise.
            if imap.state == IntentionState.TRACKING and len(imap.tracks) >= 2:
                imap.state = IntentionState.DRIFTING
            self._record_event("track_logged", {
                "intention_id": intention_id,
                "track_id": track_id,
                "position": position,
                "fidelity": fidelity,
                "drift_kind": drift_kind.value,
                "drift_valence": drift_valence.value,
            })
            return {
                "intention_id": intention_id,
                "track_id": track_id,
                "position": position,
                "fidelity": fidelity,
                "drift_kind": drift_kind.value,
                "drift_valence": drift_valence.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single intentional drift cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = IntentionalDriftPhase.TRACK
            phase_outputs["track"] = self._phase_track()
            self._phase = IntentionalDriftPhase.MODEL
            phase_outputs["model"] = self._phase_model()
            self._phase = IntentionalDriftPhase.PREDICT
            phase_outputs["predict"] = self._phase_predict()
            self._phase = IntentionalDriftPhase.INTERCEPT
            phase_outputs["intercept"] = self._phase_intercept()
            self._phase = IntentionalDriftPhase.RESONATE
            phase_outputs["resonate"] = self._phase_resonate()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_track(self) -> Dict[str, Any]:
        """Track phase: confirm each intention's current position into its map.

        Tracks are appended by log_track between cycles; here we confirm the
        most recent track for each intention and refresh its anchored state
        when fidelity is high enough that the intention is effectively
        holding its ground.
        """
        confirmed = 0
        for imap in self._intentions.values():
            if not imap.tracks:
                continue
            latest = imap.tracks[-1]
            imap.last_position = latest.position
            imap.last_fidelity = latest.fidelity
            # An intention with very high fidelity and tiny recent movement
            # is anchored rather than drifting.
            if latest.fidelity >= 0.9 and imap.state in (
                IntentionState.TRACKING, IntentionState.DRIFTING,
                IntentionState.RESONATING,
            ):
                if imap.model is not None and abs(imap.model.velocity) < 0.02:
                    imap.state = IntentionState.ANCHORED
            confirmed += 1
        self._record_event("phase_track", {"confirmed": confirmed})
        return {"confirmed": confirmed}

    def _phase_model(self) -> Dict[str, Any]:
        """Model phase: fit a drift pattern to each intention's recent track."""
        modeled = 0
        for imap in self._intentions.values():
            if len(imap.tracks) < 2:
                continue
            window = list(imap.tracks)[-self._TRACK_WINDOW:]
            positions = [t.position for t in window]
            fidelities = [t.fidelity for t in window]
            kind = self._fit_drift_kind(positions, fidelities)
            valence = self._classify_valence(kind, fidelities)
            velocity = self._estimate_velocity(positions)
            confidence = self._estimate_confidence(window, kind)
            model = DriftModel(
                intention_id=imap.intention_id,
                kind=kind,
                valence=valence,
                velocity=velocity,
                predicted_position=max(0.0, min(1.0,
                    positions[-1] + velocity * self._PREDICT_HORIZON)),
                confidence=confidence,
            )
            imap.model = model
            # Promote the intention's state based on the fitted model.
            if imap.state == IntentionState.INTERCEPTED:
                pass  # interception state is sticky until resonate clears it
            elif valence == DriftValence.PRODUCTIVE and confidence > 0.4:
                imap.state = IntentionState.RESONATING
            elif imap.state == IntentionState.ANCHORED and abs(velocity) > 0.05:
                imap.state = IntentionState.DRIFTING
            elif imap.state in (IntentionState.TRACKING, IntentionState.ANCHORED,
                                IntentionState.DRIFTING, IntentionState.RESONATING):
                imap.state = IntentionState.DRIFTING
            modeled += 1
        self._record_event("phase_model", {"modeled": modeled})
        return {"modeled": modeled}

    def _phase_predict(self) -> Dict[str, Any]:
        """Predict phase: project where each intention is heading."""
        predicted = 0
        for imap in self._intentions.values():
            if imap.model is None:
                continue
            model = imap.model
            # Re-project from the latest known position so the prediction
            # stays current even if the model was fitted last cycle.
            base = imap.last_position
            projected = base + model.velocity * self._PREDICT_HORIZON
            model.predicted_position = max(0.0, min(1.0, projected))
            # If the projected path falls outside the recoverable band and
            # the valence is destructive, the intention is on its way to
            # being lost.
            if (model.valence == DriftValence.DESTRUCTIVE
                    and model.confidence > 0.5
                    and (model.predicted_position <= 0.05
                         or model.predicted_position >= 0.95)
                    and imap.state != IntentionState.INTERCEPTED):
                imap.state = IntentionState.LOST
            predicted += 1
        self._record_event("phase_predict", {"predicted": predicted})
        return {"predicted": predicted}

    def _phase_intercept(self) -> Dict[str, Any]:
        """Intercept phase: catch intentions whose predicted drift is destructive."""
        intercepted = 0
        for imap in self._intentions.values():
            if imap.model is None:
                continue
            if not self._should_intercept(imap):
                continue
            severity = self._intercept_severity(imap.model)
            reason = self._intercept_reason(imap.model)
            corrective_note = self._intercept_corrective_note(imap)
            record = InterceptionRecord(
                intention_id=imap.intention_id,
                reason=reason,
                severity=severity,
                corrective_note=corrective_note,
            )
            imap.interceptions.append(record)
            # Cap the interception history so it does not grow unbounded.
            if len(imap.interceptions) > 30:
                imap.interceptions = imap.interceptions[-30:]
            imap.total_interceptions += 1
            imap.state = IntentionState.INTERCEPTED
            intercepted += 1
            self._stats["total_interceptions"] = (
                self._stats.get("total_interceptions", 0) + 1
            )
        self._record_event("phase_intercept", {"intercepted": intercepted})
        return {"intercepted": intercepted}

    def _phase_resonate(self) -> Dict[str, Any]:
        """Resonate phase: feed productive drift back into the intention model."""
        resonated = 0
        for imap in self._intentions.values():
            if imap.model is None:
                continue
            model = imap.model
            # Productive drift feeds back into the intention's resonance boost.
            if model.valence == DriftValence.PRODUCTIVE and model.confidence > 0.3:
                gain = self._RESONATE_GAIN * model.confidence
                imap.resonance_boost = min(1.0, imap.resonance_boost + gain)
                imap.total_resonances += 1
                # A resonating intention that was previously intercepted has
                # recovered; let it drift again.
                if imap.state == IntentionState.INTERCEPTED:
                    imap.state = IntentionState.RESONATING
                elif imap.state == IntentionState.LOST:
                    # Lost intentions can be pulled back if productive drift
                    # is strong enough.
                    if imap.resonance_boost >= 0.4:
                        imap.state = IntentionState.RESONATING
                else:
                    imap.state = IntentionState.RESONATING
                resonated += 1
                self._stats["total_resonances"] = (
                    self._stats.get("total_resonances", 0) + 1
                )
            elif imap.state == IntentionState.INTERCEPTED:
                # Intercepted intentions slowly decay their resonance boost
                # so the model does not get stuck amplifying a caught drift.
                imap.resonance_boost = max(0.0, imap.resonance_boost - 0.05)
        self._record_event("phase_resonate", {"resonated": resonated})
        return {"resonated": resonated}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _fit_drift_kind_single(self, prev_pos: float, cur_pos: float,
                               prev_fid: float, cur_fid: float) -> DriftKind:
        """Classify the drift kind of a single track relative to its predecessor."""
        delta = cur_pos - prev_pos
        fid_delta = cur_fid - prev_fid
        if abs(delta) < 0.02 and abs(fid_delta) < 0.02:
            return DriftKind.STUCK
        if fid_delta > 0.03 and abs(delta) < 0.15:
            return DriftKind.PROGRESSIVE
        if fid_delta < -0.03:
            return DriftKind.EROSIVE
        if abs(delta) >= 0.15:
            return DriftKind.EXPLORATORY
        return DriftKind.OSCILLATORY

    def _classify_valence_single(self, kind: DriftKind, prev_fid: float,
                                 cur_fid: float) -> DriftValence:
        """Classify the valence of a single track."""
        if kind == DriftKind.PROGRESSIVE:
            return DriftValence.PRODUCTIVE
        if kind == DriftKind.EROSIVE:
            return DriftValence.DESTRUCTIVE
        if kind == DriftKind.EXPLORATORY:
            # Exploratory drift is productive when fidelity holds, destructive
            # when it slips.
            return DriftValence.PRODUCTIVE if cur_fid >= prev_fid else DriftValence.DESTRUCTIVE
        if kind == DriftKind.OSCILLATORY:
            return DriftValence.NEUTRAL
        # Stuck drift is neutral unless fidelity is collapsing.
        if cur_fid < prev_fid - 0.05:
            return DriftValence.DESTRUCTIVE
        return DriftValence.NEUTRAL

    def _fit_drift_kind(self, positions: List[float],
                        fidelities: List[float]) -> DriftKind:
        """Fit a drift kind to a window of positions and fidelities."""
        if len(positions) < 2:
            return DriftKind.STUCK
        deltas = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]
        mean_delta = sum(deltas) / len(deltas)
        sign_changes = sum(
            1 for i in range(len(deltas) - 1)
            if deltas[i] * deltas[i + 1] < 0
        )
        fid_delta = fidelities[-1] - fidelities[0]
        # Stuck: nearly no movement.
        if all(abs(d) < 0.02 for d in deltas):
            return DriftKind.STUCK
        # Oscillatory: the direction flips more than once.
        if sign_changes >= 2:
            return DriftKind.OSCILLATORY
        # Erosive: fidelity is dropping over the window.
        if fid_delta < -0.05:
            return DriftKind.EROSIVE
        # Progressive: small steady movement with rising fidelity.
        if abs(mean_delta) < 0.15 and fid_delta > 0.02:
            return DriftKind.PROGRESSIVE
        # Exploratory: large movement that is not clearly erosive.
        if any(abs(d) >= 0.15 for d in deltas):
            return DriftKind.EXPLORATORY
        return DriftKind.PROGRESSIVE if mean_delta > 0 else DriftKind.EROSIVE

    def _classify_valence(self, kind: DriftKind,
                          fidelities: List[float]) -> DriftValence:
        """Classify the valence of a fitted drift kind over a fidelity window."""
        if not fidelities:
            return DriftValence.NEUTRAL
        fid_delta = fidelities[-1] - fidelities[0]
        if kind == DriftKind.PROGRESSIVE:
            return DriftValence.PRODUCTIVE
        if kind == DriftKind.EROSIVE:
            return DriftValence.DESTRUCTIVE
        if kind == DriftKind.OSCILLATORY:
            return DriftValence.NEUTRAL
        if kind == DriftKind.STUCK:
            # Stuck is destructive only if fidelity is decaying.
            return DriftValence.DESTRUCTIVE if fid_delta < -0.05 else DriftValence.NEUTRAL
        # Exploratory: productive if fidelity is at least holding.
        if fid_delta >= -0.02:
            return DriftValence.PRODUCTIVE
        return DriftValence.DESTRUCTIVE

    def _estimate_velocity(self, positions: List[float]) -> float:
        """Estimate signed per-track velocity from a window of positions."""
        if len(positions) < 2:
            return 0.0
        deltas = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]
        # Weight recent deltas more heavily so the velocity tracks the latest drift.
        weight_total = 0.0
        weighted_sum = 0.0
        n = len(deltas)
        for i, d in enumerate(deltas):
            w = (i + 1) / n
            weighted_sum += d * w
            weight_total += w
        return weighted_sum / weight_total if weight_total > 0 else 0.0

    def _estimate_confidence(self, window: List[IntentionTrack],
                             kind: DriftKind) -> float:
        """Estimate how reliable a fitted drift model is."""
        if len(window) < 2:
            return 0.0
        positions = [t.position for t in window]
        deltas = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]
        mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
        variance = sum((d - mean_delta) ** 2 for d in deltas) / len(deltas) if deltas else 0.0
        # Lower variance means higher confidence.
        confidence = max(0.0, min(1.0, 1.0 - variance * 20.0))
        # Stuck drifts are confident about being stuck.
        if kind == DriftKind.STUCK:
            confidence = min(1.0, confidence + 0.2)
        # More samples means more confidence, up to a ceiling.
        confidence = min(1.0, confidence + len(window) * 0.02)
        return confidence

    def _project_drift(self, model: DriftModel, steps: int) -> float:
        """Project a drift model forward by a number of steps."""
        if model is None:
            return 0.5
        projected = model.predicted_position + model.velocity * max(0, steps - self._PREDICT_HORIZON)
        return max(0.0, min(1.0, projected))

    def _should_intercept(self, imap: IntentionMap) -> bool:
        """Decide whether an intention's destructive drift should be intercepted."""
        model = imap.model
        if model is None:
            return False
        if model.valence != DriftValence.DESTRUCTIVE:
            return False
        # Stance controls the effective threshold.
        if self._stance == CartographerStance.PERMISSIVE:
            threshold = self._INTERCEPT_DESTRUCTIVE_THRESHOLD + 0.2
        elif self._stance == CartographerStance.STRICT:
            threshold = self._INTERCEPT_DESTRUCTIVE_THRESHOLD - 0.2
        else:
            threshold = self._INTERCEPT_DESTRUCTIVE_THRESHOLD
        # Score the destructive drift by confidence and how far the projected
        # position is from the recoverable band.
        score = model.confidence
        if model.predicted_position <= 0.1 or model.predicted_position >= 0.9:
            score += 0.2
        if imap.state == IntentionState.LOST:
            score += 0.2
        return score >= threshold

    def _intercept_severity(self, model: DriftModel) -> float:
        """Score the severity of an intercepted destructive drift."""
        severity = model.confidence * 0.7
        if model.predicted_position <= 0.1 or model.predicted_position >= 0.9:
            severity += 0.3
        return max(0.0, min(1.0, severity))

    def _intercept_reason(self, model: DriftModel) -> str:
        """Compose a short reason for an interception."""
        return (
            f"destructive {model.kind.value} drift "
            f"(velocity={model.velocity:.3f}, "
            f"predicted={model.predicted_position:.3f}, "
            f"confidence={model.confidence:.2f})"
        )

    def _intercept_corrective_note(self, imap: IntentionMap) -> str:
        """Compose a short corrective note for an intercepted intention."""
        return (
            f"intention '{imap.goal_label}' is drifting destructively; "
            f"re-anchor toward fidelity {imap.last_fidelity:.2f}"
        )

    def _apply_resonance(self, imap: IntentionMap) -> float:
        """Apply the accumulated resonance boost to an intention's position."""
        if imap.resonance_boost <= 0.0:
            return imap.last_position
        # Productive resonance nudges the intention toward higher fidelity
        # along the direction of the model's velocity.
        if imap.model is None:
            return imap.last_position
        nudge = imap.resonance_boost * 0.1
        if imap.model.velocity >= 0:
            new_pos = min(1.0, imap.last_position + nudge)
        else:
            new_pos = max(0.0, imap.last_position - nudge)
        return new_pos

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "intentions": len(self._intentions),
                "stance": self._stance.value,
                "stats": dict(self._stats),
            }

    def get_intention_state(self, intention_id: str) -> Dict[str, Any]:
        with self._global_lock:
            imap = self._intentions.get(intention_id)
            if imap is None:
                return {"error": f"Intention not found: {intention_id}"}
            model = imap.model
            return {
                "intention_id": imap.intention_id,
                "goal_label": imap.goal_label,
                "state": imap.state.value,
                "last_position": imap.last_position,
                "last_fidelity": imap.last_fidelity,
                "tracks_count": len(imap.tracks),
                "interceptions_count": len(imap.interceptions),
                "total_tracks": imap.total_tracks,
                "total_interceptions": imap.total_interceptions,
                "total_resonances": imap.total_resonances,
                "resonance_boost": imap.resonance_boost,
                "model": ({
                    "kind": model.kind.value,
                    "valence": model.valence.value,
                    "velocity": model.velocity,
                    "predicted_position": model.predicted_position,
                    "confidence": model.confidence,
                } if model is not None else None),
                "registered_at": imap.registered_at,
            }

    def get_tracks(self, intention_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            imap = self._intentions.get(intention_id)
            if imap is None:
                return {"error": f"Intention not found: {intention_id}"}
            tracks = list(imap.tracks)[-limit:]
            return {
                "intention_id": intention_id,
                "tracks": [
                    {
                        "track_id": getattr(t, "track_id", None),
                        "position": t.position,
                        "fidelity": t.fidelity,
                        "drift_kind": t.drift_kind.value,
                        "drift_valence": t.drift_valence.value,
                        "timestamp": t.timestamp,
                    }
                    for t in tracks
                ],
            }

    def get_model(self, intention_id: str) -> Dict[str, Any]:
        with self._global_lock:
            imap = self._intentions.get(intention_id)
            if imap is None:
                return {"error": f"Intention not found: {intention_id}"}
            model = imap.model
            if model is None:
                return {
                    "intention_id": intention_id,
                    "model": None,
                    "interceptions": [
                        {
                            "reason": r.reason,
                            "severity": r.severity,
                            "corrective_note": r.corrective_note,
                            "created_at": r.created_at,
                        }
                        for r in imap.interceptions[-10:]
                    ],
                }
            return {
                "intention_id": intention_id,
                "model": {
                    "kind": model.kind.value,
                    "valence": model.valence.value,
                    "velocity": model.velocity,
                    "predicted_position": model.predicted_position,
                    "confidence": model.confidence,
                },
                "interceptions": [
                    {
                        "reason": r.reason,
                        "severity": r.severity,
                        "corrective_note": r.corrective_note,
                        "created_at": r.created_at,
                    }
                    for r in imap.interceptions[-10:]
                ],
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Simulation
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic intentions and tracks, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_intentions()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                # Between cycles, add a fresh track to each intention so the
                # drift models have new evidence to fit on each pass.
                self._seed_synthetic_tracks()
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_intentions(self) -> None:
        """Seed a handful of synthetic intentions with distinct drift profiles."""
        seed_intentions = [
            ("sim_progressive", "converge on the summit", 0.45),
            ("sim_erosive", "hold the perimeter", 0.55),
            ("sim_exploratory", "survey the ruins", 0.5),
            ("sim_oscillatory", "guard the caravan", 0.5),
        ]
        for intention_id, goal_label, position in seed_intentions:
            if intention_id not in self._intentions:
                self.register_intention(intention_id, goal_label, position)
        # Seed a few initial tracks per intention so the first cycle has
        # something to model.
        self._seed_synthetic_tracks()

    def _seed_synthetic_tracks(self) -> None:
        """Add one fresh track per intention, biased toward its drift profile."""
        profiles = {
            "sim_progressive": lambda p, f: (
                max(0.0, min(1.0, p + random.uniform(0.03, 0.08))),
                max(0.0, min(1.0, f + random.uniform(0.02, 0.06))),
            ),
            "sim_erosive": lambda p, f: (
                max(0.0, min(1.0, p - random.uniform(0.02, 0.06))),
                max(0.0, min(1.0, f - random.uniform(0.04, 0.09))),
            ),
            "sim_exploratory": lambda p, f: (
                max(0.0, min(1.0, p + random.uniform(-0.15, 0.15))),
                max(0.0, min(1.0, f + random.uniform(-0.02, 0.03))),
            ),
            "sim_oscillatory": lambda p, f: (
                max(0.0, min(1.0, p + (1.0 if random.random() < 0.5 else -1.0)
                              * random.uniform(0.08, 0.15))),
                max(0.0, min(1.0, f + random.uniform(-0.02, 0.02))),
            ),
        }
        for intention_id, profile_fn in profiles.items():
            imap = self._intentions.get(intention_id)
            if imap is None:
                continue
            new_pos, new_fid = profile_fn(imap.last_position, imap.last_fidelity)
            track_id = f"sim_t_{intention_id}_{imap.total_tracks + 1}"
            if any(getattr(t, "track_id", None) == track_id for t in imap.tracks):
                continue
            self.log_track(intention_id, track_id, new_pos, new_fid)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._intentions.clear()
            self._events_log.clear()
            self._phase = IntentionalDriftPhase.TRACK
            self._cycle_count = 0
            self._stance = CartographerStance.VIGILANT
            self._init_stats()
            return {"reset": True}
