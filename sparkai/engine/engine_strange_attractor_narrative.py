"""
SparkLabs Engine - Strange Attractor Narrative"""

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

class TrajectoryPhase(Enum):
    """Phases of the strange attractor narrative cycle."""
    POLL = "poll"                # poll attractor states (their current pull strength)
    DERIVE = "derive"            # compute trajectory derivatives (force toward each attractor)
    INTEGRATE = "integrate"      # integrate the flow over time (apply velocity, damp inertia)
    TRANSITION = "transition"    # detect basin transitions (which attractor now dominates)
    EMIT = "emit"                # emit trajectory snapshot with basin weights and projected course


class BasinArchetype(Enum):
    """The archetypal narrative basins a trajectory can be drawn toward."""
    REDEMPTION = "redemption"        # the quest for atonement
    FALL = "fall"                    # the descent into ruin
    ASCENT = "ascent"                # the climb toward power or grace
    RETURN = "return"                # the homecoming
    CONVERGENCE = "convergence"      # threads meeting
    DISPERSION = "dispersion"        # threads flying apart


class FlowRegime(Enum):
    """How turbulent the trajectory's flow over the landscape is."""
    LAMINAR = "laminar"          # smooth, single-basin pull
    TURBULENT = "turbulent"      # competing pulls, oscillating
    CHAOTIC = "chaotic"          # sensitive to initial conditions
    STUCK = "stuck"              # no attractor dominates


class BasinTransition(Enum):
    """Whether and how a trajectory is transitioning between basins this cycle."""
    NONE = "none"                # no transition this cycle
    APPROACHING = "approaching"  # nearing a new basin
    CROSSING = "crossing"        # mid-transition
    SETTLING = "settling"        # recently arrived in new basin


class TrajectoryState(Enum):
    """State of an individual narrative trajectory within the cycle."""
    RAW = "raw"                      # registered but not yet polled
    POLLED = "polled"                # attractor states read
    DERIVED = "derived"              # derivatives computed
    INTEGRATED = "integrated"        # flow integrated
    SNAPSHOTTED = "snapshotted"      # trajectory snapshot emitted


class Vitality(Enum):
    """Overall vitality of the strange attractor narrative ecosystem."""
    DORMANT = "dormant"
    STIRRING = "stirring"
    FLOWING = "flowing"
    SURGING = "surging"
    SATURATED = "saturated"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AttractorWeight:
    """The pull a single attractor exerts on a trajectory."""
    archetype: BasinArchetype
    pull_strength: float = 0.3       # 0.0-1.0, current pull
    target_pull: float = 0.3         # 0.0-1.0, where pull is drifting toward


@dataclass
class NarrativeTrajectory:
    """A narrative trajectory flowing over the attractor landscape."""
    trajectory_id: str
    entity_id: str
    trajectory_label: str
    attractor_weights: List[AttractorWeight] = field(default_factory=list)
    current_basin: BasinArchetype = BasinArchetype.CONVERGENCE
    basin_history: List[str] = field(default_factory=list)
    position: float = 0.0            # abstract 1D position on the narrative landscape
    velocity: float = 0.0            # rate of position change
    inertia: float = 0.4             # 0.0-1.0, resistance to force changes
    flow_regime: FlowRegime = FlowRegime.LAMINAR
    last_transition: BasinTransition = BasinTransition.NONE
    state: TrajectoryState = TrajectoryState.RAW
    vitality: Vitality = Vitality.DORMANT
    created_at: float = field(default_factory=time.time)
    last_snapshotted_at: float = 0.0
    note: str = ""


# =============================================================================
# Resolver
# =============================================================================

class StrangeAttractorNarrative:
    """
    Thread-safe singleton that flows narrative trajectories over a
    dynamical landscape of competing strange attractors.

    Usage:
        engine = StrangeAttractorNarrative.get_instance()
        engine.register_trajectory(
            entity_id="char::protagonist",
            trajectory_label="The Protagonist Arc",
        )
        engine.cycle()
        info = engine.get_trajectory(trajectory_id)
    """

    _instance: Optional["StrangeAttractorNarrative"] = None
    _instance_lock = threading.Lock()

    _MAX_TRAJECTORIES = 60
    _MAX_EVENTS = 200
    _MAX_BASIN_HISTORY = 12

    # Tuning constants
    _INERTIA_DEFAULT = 0.4
    _DAMPING = 0.85
    _PULL_DECAY = 0.95
    _TRANSITION_THRESHOLD = 0.45

    def __init__(self) -> None:
        # Internal dict keyed by entity_id, NOT by trajectory_id.
        self._trajectories: Dict[str, NarrativeTrajectory] = {}
        self._phase: TrajectoryPhase = TrajectoryPhase.POLL
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "StrangeAttractorNarrative":
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
            "uptime_started_at": time.time(),
            "trajectories_registered": 0,
            "phase_runs": 0,
            "attractors_polled": 0,
            "derivatives_computed": 0,
            "flows_integrated": 0,
            "basin_transitions": 0,
            "snapshots_emitted": 0,
            "events_recorded": 0,
        }

    def _update_stats(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if key not in self._stats:
                # Ignore unknown keys to keep callers simple.
                continue
            current = self._stats[key]
            if isinstance(current, (int, float)) and isinstance(value, (int, float)):
                self._stats[key] = current + value
            else:
                self._stats[key] = value

    def _record_event(self, event_type: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload or {},
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })
        self._stats["events_recorded"] += 1

    # -------------------------------------------------------------------------
    # Trajectory Management
    # -------------------------------------------------------------------------

    def register_trajectory(
        self,
        entity_id: str,
        trajectory_label: str,
        attractor_weights: Optional[Dict[str, float]] = None,
        inertia: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Register a new narrative trajectory on the attractor landscape."""
        with self._global_lock:
            if entity_id in self._trajectories:
                return {"error": f"Trajectory already registered for entity: {entity_id}"}
            if len(self._trajectories) >= self._MAX_TRAJECTORIES:
                return {"error": f"Trajectory cap reached ({self._MAX_TRAJECTORIES})"}

            trajectory_id = f"traj_{entity_id}_{int(time.time() * 1000)}_{random.randint(100, 999)}"

            # Resolve attractor weights: caller-supplied dict is converted to
            # AttractorWeight objects; otherwise synthesize default pulls.
            if attractor_weights is not None:
                weights: List[AttractorWeight] = []
                # Always include every archetype so the landscape is complete;
                # caller-supplied pulls override the synthesized baseline.
                supplied = {str(k).lower(): float(v) for k, v in attractor_weights.items()}
                for archetype in BasinArchetype:
                    raw_pull = supplied.get(archetype.value, 0.0)
                    pull = max(0.0, min(1.0, raw_pull))
                    weights.append(AttractorWeight(
                        archetype=archetype,
                        pull_strength=pull,
                        target_pull=pull,
                    ))
                # If the caller supplied no nonzero pulls at all, fall back to
                # a synthesized baseline so the trajectory has somewhere to go.
                if all(w.pull_strength <= 0.0 for w in weights):
                    weights = self._synthesize_default_weights()
            else:
                weights = self._synthesize_default_weights()

            # Inertia clamps to [0.0, 1.0]; default otherwise.
            if inertia is None:
                resolved_inertia = self._INERTIA_DEFAULT
            else:
                resolved_inertia = max(0.0, min(1.0, float(inertia)))

            # The current basin is whichever archetype pulls hardest.
            current_basin = max(weights, key=lambda w: w.pull_strength).archetype

            trajectory = NarrativeTrajectory(
                trajectory_id=trajectory_id,
                entity_id=entity_id,
                trajectory_label=trajectory_label,
                attractor_weights=weights,
                current_basin=current_basin,
                basin_history=[current_basin.value],
                position=0.0,
                velocity=0.0,
                inertia=resolved_inertia,
                flow_regime=FlowRegime.LAMINAR,
                last_transition=BasinTransition.NONE,
                state=TrajectoryState.RAW,
                vitality=Vitality.DORMANT,
                created_at=time.time(),
                last_snapshotted_at=0.0,
                note="",
            )
            self._trajectories[entity_id] = trajectory
            self._update_stats(trajectories_registered=1)
            self._record_event("trajectory_registered", {
                "trajectory_id": trajectory_id,
                "entity_id": entity_id,
                "trajectory_label": trajectory_label,
                "current_basin": current_basin.value,
                "inertia": resolved_inertia,
                "attractor_count": len(weights),
            })
            return {
                "trajectory_id": trajectory_id,
                "entity_id": entity_id,
                "trajectory_label": trajectory_label,
                "current_basin": current_basin.value,
                "attractor_count": len(weights),
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single strange attractor narrative cycle through all five phases."""
        with self._global_lock:
            # Seed synthetic trajectories on the very first cycle if none exist.
            if not self._trajectories and self._cycle_count == 0:
                self._seed_synthetic_trajectories()

            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = TrajectoryPhase.POLL
            phase_outputs.append(self._phase_poll())
            self._phase = TrajectoryPhase.DERIVE
            phase_outputs.append(self._phase_derive())
            self._phase = TrajectoryPhase.INTEGRATE
            phase_outputs.append(self._phase_integrate())
            self._phase = TrajectoryPhase.TRANSITION
            phase_outputs.append(self._phase_transition())
            self._phase = TrajectoryPhase.EMIT
            phase_outputs.append(self._phase_emit())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_poll(self) -> Dict[str, Any]:
        """Poll phase: drift each attractor's pull toward its target with perturbation."""
        polled = 0
        total_pull = 0.0
        pull_samples = 0
        for trajectory in self._trajectories.values():
            if trajectory.state != TrajectoryState.RAW:
                continue
            for weight in trajectory.attractor_weights:
                # Drift the current pull toward the target by 10% of the gap,
                # then apply a small random perturbation so the landscape
                # never quite settles.
                gap = weight.target_pull - weight.pull_strength
                weight.pull_strength += gap * 0.1
                weight.pull_strength += random.uniform(-0.02, 0.02)
                weight.pull_strength = max(0.0, min(1.0, weight.pull_strength))
                # The target itself slowly decays so attractors do not pull
                # forever; new target_pulls are seeded by transitions.
                weight.target_pull = max(0.0, min(1.0, weight.target_pull * self._PULL_DECAY))
                total_pull += weight.pull_strength
                pull_samples += 1
            trajectory.state = TrajectoryState.POLLED
            polled += 1
        avg_pull = (total_pull / pull_samples) if pull_samples > 0 else 0.0
        self._update_stats(phase_runs=1, attractors_polled=pull_samples)
        self._record_event("phase_poll", {"polled": polled, "avg_pull": avg_pull})
        return {"phase": "poll", "polled": polled, "avg_pull": avg_pull}

    def _phase_derive(self) -> Dict[str, Any]:
        """Derive phase: compute net force on each trajectory from its attractor pulls."""
        derived = 0
        total_force = 0.0
        for trajectory in self._trajectories.values():
            if trajectory.state != TrajectoryState.POLLED:
                continue
            force = 0.0
            for weight in trajectory.attractor_weights:
                direction_sign = self._archetype_direction(weight.archetype)
                force += weight.pull_strength * direction_sign
            # Velocity accumulates the force, damped by inertia.
            trajectory.velocity = (
                trajectory.velocity * self._DAMPING + force * (1.0 - trajectory.inertia)
            )
            trajectory.state = TrajectoryState.DERIVED
            derived += 1
            total_force += force
        avg_force = (total_force / derived) if derived > 0 else 0.0
        self._update_stats(phase_runs=1, derivatives_computed=derived)
        self._record_event("phase_derive", {"derived": derived, "avg_force": avg_force})
        return {"phase": "derive", "derived": derived, "avg_force": avg_force}

    def _phase_integrate(self) -> Dict[str, Any]:
        """Integrate phase: apply velocity to position and classify the flow regime."""
        integrated = 0
        for trajectory in self._trajectories.values():
            if trajectory.state != TrajectoryState.DERIVED:
                continue
            trajectory.position += trajectory.velocity
            trajectory.flow_regime = self._classify_flow_regime(trajectory)
            trajectory.state = TrajectoryState.INTEGRATED
            integrated += 1
        self._update_stats(phase_runs=1, flows_integrated=integrated)
        self._record_event("phase_integrate", {"integrated": integrated})
        return {"phase": "integrate", "integrated": integrated}

    def _phase_transition(self) -> Dict[str, Any]:
        """Transition phase: detect when a new attractor begins to dominate."""
        transitioned = 0
        for trajectory in self._trajectories.values():
            if trajectory.state != TrajectoryState.INTEGRATED:
                continue
            # Rank attractors by current pull strength.
            ranked = sorted(
                trajectory.attractor_weights,
                key=lambda w: w.pull_strength,
                reverse=True,
            )
            top = ranked[0] if ranked else None
            second = ranked[1] if len(ranked) > 1 else None
            if top is None:
                trajectory.last_transition = BasinTransition.NONE
            elif top.archetype != trajectory.current_basin:
                top_pull = top.pull_strength
                second_pull = second.pull_strength if second else 0.0
                margin = top_pull - second_pull
                if top_pull >= self._TRANSITION_THRESHOLD and margin > 0.1:
                    # Classify the transition by how strongly the new basin pulls.
                    if top_pull > 0.8:
                        trajectory.last_transition = BasinTransition.SETTLING
                    elif top_pull >= 0.6:
                        trajectory.last_transition = BasinTransition.CROSSING
                    else:
                        trajectory.last_transition = BasinTransition.APPROACHING
                    trajectory.current_basin = top.archetype
                    trajectory.basin_history.append(top.archetype.value)
                    if len(trajectory.basin_history) > self._MAX_BASIN_HISTORY:
                        trajectory.basin_history = \
                            trajectory.basin_history[-self._MAX_BASIN_HISTORY:]
                    # Seed a fresh target_pull on the new dominant attractor so
                    # the basin has somewhere to drift toward from here.
                    top.target_pull = max(top_pull, random.uniform(0.4, 0.7))
                    transitioned += 1
                else:
                    trajectory.last_transition = BasinTransition.NONE
            else:
                trajectory.last_transition = BasinTransition.NONE
            trajectory.state = TrajectoryState.SNAPSHOTTED
        self._update_stats(phase_runs=1, basin_transitions=transitioned)
        self._record_event("phase_transition", {"transitioned": transitioned})
        return {"phase": "transition", "transitioned": transitioned}

    def _phase_emit(self) -> Dict[str, Any]:
        """Emit phase: snapshot each trajectory and refresh its vitality."""
        emitted = 0
        for trajectory in self._trajectories.values():
            if trajectory.state != TrajectoryState.SNAPSHOTTED:
                continue
            trajectory.last_snapshotted_at = time.time()
            trajectory.vitality = self._derive_vitality()
            trajectory.state = TrajectoryState.RAW  # ready for the next cycle
            emitted += 1
        self._update_stats(phase_runs=1, snapshots_emitted=emitted)
        self._record_event("phase_emit", {"emitted": emitted})
        return {"phase": "emit", "emitted": emitted}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _archetype_direction(self, archetype: BasinArchetype) -> int:
        """Direction sign for an archetype on the 1D narrative landscape.

        Advancing archetypes push the trajectory forward; regressing
        archetypes push it backward; RETURN is neutral because the
        homecoming neither advances nor regresses the story.
        """
        if archetype in (BasinArchetype.ASCENT, BasinArchetype.REDEMPTION,
                         BasinArchetype.CONVERGENCE):
            return 1
        if archetype in (BasinArchetype.FALL, BasinArchetype.DISPERSION):
            return -1
        return 0  # RETURN is neutral

    def _classify_flow_regime(self, trajectory: NarrativeTrajectory) -> FlowRegime:
        """Classify how turbulent a trajectory's flow is from its pulls."""
        if abs(trajectory.velocity) < 0.05:
            return FlowRegime.STUCK
        pulls = [w.pull_strength for w in trajectory.attractor_weights]
        strong_count = sum(1 for p in pulls if p > 0.4)
        moderate_count = sum(1 for p in pulls if p > 0.3)
        if strong_count >= 2:
            return FlowRegime.TURBULENT
        if moderate_count >= 3:
            return FlowRegime.CHAOTIC
        return FlowRegime.LAMINAR

    def _synthesize_default_weights(self) -> List[AttractorWeight]:
        """Synthesize a default set of attractor weights across all archetypes."""
        weights: List[AttractorWeight] = []
        for archetype in BasinArchetype:
            pull = random.uniform(0.1, 0.4)
            weights.append(AttractorWeight(
                archetype=archetype,
                pull_strength=pull,
                target_pull=pull,
            ))
        return weights

    def _derive_vitality(self) -> Vitality:
        """Overall ecosystem vitality from trajectory population."""
        count = len(self._trajectories)
        if count == 0:
            return Vitality.DORMANT
        if count <= 2:
            return Vitality.STIRRING
        if count <= 7:
            return Vitality.FLOWING
        if count <= 12:
            return Vitality.SURGING
        return Vitality.SATURATED

    def _trajectory_to_dict(self, trajectory: NarrativeTrajectory) -> Dict[str, Any]:
        return {
            "trajectory_id": trajectory.trajectory_id,
            "entity_id": trajectory.entity_id,
            "trajectory_label": trajectory.trajectory_label,
            "current_basin": trajectory.current_basin.value,
            "basin_history": list(trajectory.basin_history),
            "position": trajectory.position,
            "velocity": trajectory.velocity,
            "inertia": trajectory.inertia,
            "flow_regime": trajectory.flow_regime.value,
            "last_transition": trajectory.last_transition.value,
            "state": trajectory.state.value,
            "vitality": trajectory.vitality.value,
            "attractor_weights": [
                {
                    "archetype": w.archetype.value,
                    "pull_strength": w.pull_strength,
                    "target_pull": w.target_pull,
                }
                for w in trajectory.attractor_weights
            ],
            "created_at": trajectory.created_at,
            "last_snapshotted_at": trajectory.last_snapshotted_at,
            "note": trajectory.note,
        }

    def _trajectory_summary(self, trajectory: NarrativeTrajectory) -> Dict[str, Any]:
        return {
            "trajectory_id": trajectory.trajectory_id,
            "entity_id": trajectory.entity_id,
            "trajectory_label": trajectory.trajectory_label,
            "current_basin": trajectory.current_basin.value,
            "flow_regime": trajectory.flow_regime.value,
            "state": trajectory.state.value,
            "vitality": trajectory.vitality.value,
            "attractor_count": len(trajectory.attractor_weights),
        }

    # -------------------------------------------------------------------------
    # Synthetic Seeding
    # -------------------------------------------------------------------------

    def _seed_synthetic_trajectories(self) -> None:
        """Seed ~3 synthetic trajectories biased toward distinct basins."""
        seeds = [
            (
                "traj::protagonist_arc",
                "The Protagonist Arc",
                {"redemption": 0.7, "ascent": 0.4, "return": 0.3,
                 "convergence": 0.2, "fall": 0.1, "dispersion": 0.05},
            ),
            (
                "traj::antagonist_arc",
                "The Antagonist Arc",
                {"fall": 0.75, "dispersion": 0.5, "ascent": 0.3,
                 "redemption": 0.1, "return": 0.1, "convergence": 0.1},
            ),
            (
                "traj::side_character_arc",
                "The Side Character Arc",
                {"convergence": 0.65, "return": 0.45, "redemption": 0.3,
                 "ascent": 0.2, "fall": 0.15, "dispersion": 0.1},
            ),
        ]
        for entity_id, label, weights in seeds:
            if len(self._trajectories) >= self._MAX_TRAJECTORIES:
                break
            if entity_id in self._trajectories:
                continue
            self.register_trajectory(
                entity_id=entity_id,
                trajectory_label=label,
                attractor_weights=weights,
            )

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "trajectories": len(self._trajectories),
                "vitality": self._derive_vitality().value,
                "stats": dict(self._stats),
            }

    def get_trajectories(self, limit: int = 50) -> Dict[str, Any]:
        with self._global_lock:
            trajectories = sorted(
                self._trajectories.values(),
                key=lambda t: t.created_at,
                reverse=True,
            )[:limit]
            return {
                "count": len(trajectories),
                "trajectories": [self._trajectory_summary(t) for t in trajectories],
            }

    def get_trajectory(self, trajectory_id: str) -> Dict[str, Any]:
        # The internal dict is keyed by entity_id, not trajectory_id, so we
        # do a fallback search across values matching on trajectory_id.
        with self._global_lock:
            for trajectory in self._trajectories.values():
                if trajectory.trajectory_id == trajectory_id:
                    return self._trajectory_to_dict(trajectory)
            return {
                "error": f"Trajectory not found: {trajectory_id}",
                "trajectory_id": trajectory_id,
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic trajectories if empty, then run multiple cycles."""
        with self._global_lock:
            if not self._trajectories:
                self._seed_synthetic_trajectories()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._trajectories.clear()
            self._events_log.clear()
            self._phase = TrajectoryPhase.POLL
            self._cycle_count = 0
            self._init_stats()
            return {
                "reset": True,
                "uptime_started_at": self._stats["uptime_started_at"],
            }
