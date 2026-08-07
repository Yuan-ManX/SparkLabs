"""
SparkLabs Engine - Dynamical Systems Attractor

The DynamicalSystemsAttractor models the game-world state space as a
dynamical attractor landscape. Each registered landscape is a vector
field over a set of named dimensions; embedded in the field are
attractors (stable nodes, stable cycles, saddles, repellers, strange
attractors) that pull the world state toward themselves. A perturbation
nudges the state along a trajectory; the trajectory is traced under
the field, the basin it is converging toward is identified, bifurcation
thresholds are checked, and the state finally settles into a new
equilibrium.

By steering the world state toward or away from attractor basins the
engine produces emergent narrative and world equilibria: stable
attractors become enduring outcomes, bifurcation crossings become
regime changes, and strange attractors become ongoing oscillations
that never quite settle.

Architecture:
  PERTURB    ->  TRACE     ->  BASIN      ->  BIFURCATE  ->  SETTLE
  (a pertur-   (the state    (which       (does the       (the state
   bation is   traces a      attractor    trajectory      settles into
   applied     trajectory    basin is     cross a         its new
   to the      under the     identified)  bifurcation?)   equilibrium)
   state)      field)

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

class AttractorDynamicsPhase(Enum):
    """Phases of the dynamical attractor cycle."""
    PERTURB = "perturb"        # a perturbation is applied to the state vector
    TRACE = "trace"            # the state traces a trajectory under the field
    BASIN = "basin"            # the converging attractor basin is identified
    BIFURCATE = "bifurcate"    # bifurcation / regime-change crossings are detected
    SETTLE = "settle"          # the state settles into its new equilibrium


class AttractorKind(Enum):
    """The kind of an attractor embedded in a landscape."""
    STABLE_NODE = "stable_node"      # pulls trajectories inward to a point
    STABLE_CYCLE = "stable_cycle"    # pulls trajectories inward to a limit cycle
    SADDLE = "saddle"                # attracts along one axis, repels along another
    REPELLOR = "repellor"            # pushes trajectories outward
    STRANGE = "strange"              # trajectories orbit chaotically without settling


class BifurcationKind(Enum):
    """The kind of bifurcation a trajectory may cross."""
    NONE = "none"                    # no bifurcation this cycle
    SADDLE_NODE = "saddle_node"      # a stable node and saddle collide and vanish
    PITCHFORK = "pitchfork"          # one equilibrium splits into three (or vice versa)
    TRANSCRITICAL = "transcritical"  # two equilibria exchange stability
    HOPF = "hopf"                    # a fixed point spawns a limit cycle


class BasinShape(Enum):
    """The shape of an attractor's basin of attraction."""
    LOCAL = "local"                  # a small, well-contained basin
    GLOBAL = "global"                # the basin covers most of the landscape
    FRACTAL = "fractal"              # a fragmented, interleaved basin
    NONE = "none"                    # no basin (repellor or uninitialized)


class PerturbationKind(Enum):
    """The kind of perturbation applied to a state vector."""
    IMPULSE = "impulse"              # a sharp, brief shove
    DRIFT = "drift"                  # a slow, sustained lean
    SHOCK = "shock"                  # a large, possibly destabilizing blow
    NUDGE = "nudge"                  # a small corrective touch


class TrajectoryState(Enum):
    """The state of a traced trajectory."""
    DIVERGING = "diverging"          # moving away from all attractors
    CONVERGING = "converging"        # moving toward an attractor
    ORBITING = "orbiting"            # circling an attractor without settling
    SETTLED = "settled"              # reached an equilibrium
    BIFURCATED = "bifurcated"        # crossed a bifurcation, regime changed


class LandscapeVitality(Enum):
    """The overall vitality of the dynamical attractor ecosystem."""
    DORMANT = "dormant"              # few landscapes, little motion
    FLOWING = "flowing"              # healthy convergence and settling
    TURBULENT = "turbulent"          # many diverging trajectories
    BIFURCATING = "bifurcating"      # frequent regime changes
    COLLAPSED = "collapsed"          # most trajectories diverge without settling


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Attractor:
    """An attractor embedded in a landscape's vector field."""
    attractor_id: str
    kind: AttractorKind
    position: Dict[str, float] = field(default_factory=dict)  # named-dim -> coordinate
    strength: float = 0.5               # 0.0-1.0, how hard it pulls
    stability: float = 0.5              # 0.0-1.0, how resists perturbation
    basin_radius: float = 0.3           # 0.0-1.0, radius of basin
    basin_shape: BasinShape = BasinShape.LOCAL


@dataclass
class AttractorLandscape:
    """A dynamical landscape: dimensions, attractors, and the live state."""
    landscape_id: str
    dimensions: List[str] = field(default_factory=list)
    attractors: Dict[str, Attractor] = field(default_factory=dict)
    state_vector: Dict[str, float] = field(default_factory=dict)
    bifurcation_params: Dict[str, float] = field(default_factory=dict)
    pending_perturbations: List["Perturbation"] = field(default_factory=list)
    active_trajectory: Optional["Trajectory"] = None
    last_basin_attractor_id: Optional[str] = None
    last_bifurcation: BifurcationKind = BifurcationKind.NONE
    total_perturbations: int = 0
    total_trajectories: int = 0
    total_bifurcations: int = 0
    total_settled: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class Perturbation:
    """A perturbation applied to a landscape's state vector."""
    perturbation_id: str
    landscape_id: str
    kind: PerturbationKind
    vector: Dict[str, float] = field(default_factory=dict)
    magnitude: float = 0.3
    created_at: float = field(default_factory=time.time)


@dataclass
class TrajectoryPoint:
    """A single point along a traced trajectory."""
    step: int
    state: Dict[str, float] = field(default_factory=dict)
    velocity: Dict[str, float] = field(default_factory=dict)


@dataclass
class Trajectory:
    """A trajectory traced through a landscape under its vector field."""
    trajectory_id: str
    landscape_id: str
    points: List[TrajectoryPoint] = field(default_factory=list)
    state: TrajectoryState = TrajectoryState.DIVERGING
    target_attractor_id: Optional[str] = None
    convergence: float = 0.0          # 0.0-1.0, how strongly converging
    bifurcations_crossed: int = 0
    started_at: float = field(default_factory=time.time)
    settled_at: Optional[float] = None


# =============================================================================
# Dynamical Systems Attractor
# =============================================================================

class DynamicalSystemsAttractor:
    """
    Thread-safe singleton orchestrating a dynamical attractor landscape
    over the game-world state space.

    Usage:
        engine = DynamicalSystemsAttractor.get_instance()
        engine.register_landscape("world_main", dimensions=["tension", "momentum"])
        engine.cycle()
        snap = engine.get_landscape("world_main")
    """

    _instance: Optional["DynamicalSystemsAttractor"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _MAX_LANDSCAPES = 50
    _MAX_EVENTS = 200
    _TRACE_STEPS = 6                  # steps traced per cycle
    _TRACE_STEP_SIZE = 0.15           # how far each step moves
    _CONVERGENCE_THRESHOLD = 0.7      # convergence above this is "settling"
    _BIFURCATION_THRESHOLD = 0.75     # state param above this risks bifurcation
    _SETTLE_SNAP_FACTOR = 0.4         # how much settle pulls state to attractor
    _VITALITY_TURBULENT_THRESHOLD = 4

    def __init__(self) -> None:
        self._landscapes: Dict[str, AttractorLandscape] = {}
        self._phase: AttractorDynamicsPhase = AttractorDynamicsPhase.PERTURB
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "DynamicalSystemsAttractor":
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
            "total_landscapes": 0,
            "total_perturbations": 0,
            "total_trajectories": 0,
            "total_bifurcations": 0,
            "total_settled": 0,
            "open_trajectories": 0,
            "avg_convergence": 0.0,
            "vitality": LandscapeVitality.DORMANT.value,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self, **kwargs: Any) -> None:
        # Merge any explicit overrides first.
        for k, v in kwargs.items():
            self._stats[k] = v
        # Recompute derived stats from the current landscape registry.
        open_trajectories = 0
        convergences: List[float] = []
        for landscape in self._landscapes.values():
            traj = landscape.active_trajectory
            if traj is not None and traj.state in (
                TrajectoryState.CONVERGING, TrajectoryState.ORBITING,
                TrajectoryState.DIVERGING,
            ):
                open_trajectories += 1
                convergences.append(traj.convergence)
        self._stats["total_landscapes"] = len(self._landscapes)
        self._stats["open_trajectories"] = open_trajectories
        self._stats["avg_convergence"] = (
            sum(convergences) / len(convergences) if convergences else 0.0
        )
        self._stats["vitality"] = self._derive_vitality().value

    def _derive_vitality(self) -> LandscapeVitality:
        open_trajs = self._stats.get("open_trajectories", 0)
        bifurcations = self._stats.get("total_bifurcations", 0)
        settled = self._stats.get("total_settled", 0)
        if open_trajs >= self._VITALITY_TURBULENT_THRESHOLD and settled == 0:
            return LandscapeVitality.TURBULENT
        if bifurcations > 0 and bifurcations >= max(1, settled):
            return LandscapeVitality.BIFURCATING
        total_finished = settled + bifurcations
        if total_finished > 0 and settled / total_finished < 0.3:
            return LandscapeVitality.COLLAPSED
        if open_trajs == 0 and total_finished == 0:
            return LandscapeVitality.DORMANT
        return LandscapeVitality.FLOWING

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Landscape Management
    # -------------------------------------------------------------------------

    def register_landscape(
        self,
        landscape_id: str,
        dimensions: List[str],
        attractors: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Register a new attractor landscape."""
        with self._global_lock:
            if landscape_id in self._landscapes:
                return {"error": f"Landscape already registered: {landscape_id}"}
            if not dimensions:
                return {"error": "Landscape must declare at least one dimension"}
            if len(self._landscapes) >= self._MAX_LANDSCAPES:
                # Drop the oldest landscape to make room.
                oldest_id = min(
                    self._landscapes,
                    key=lambda lid: self._landscapes[lid].created_at,
                )
                self._landscapes.pop(oldest_id, None)
            landscape = AttractorLandscape(
                landscape_id=landscape_id,
                dimensions=list(dimensions),
                state_vector={d: 0.0 for d in dimensions},
                bifurcation_params={d: self._BIFURCATION_THRESHOLD for d in dimensions},
            )
            # Seed attractors supplied by the caller.
            for spec in attractors or []:
                attr = self._build_attractor(spec, dimensions)
                if attr is not None:
                    landscape.attractors[attr.attractor_id] = attr
            # If no attractors were supplied, synthesize one stable node.
            if not landscape.attractors:
                seed_id = f"{landscape_id}_seed_node"
                landscape.attractors[seed_id] = Attractor(
                    attractor_id=seed_id,
                    kind=AttractorKind.STABLE_NODE,
                    position={d: 0.0 for d in dimensions},
                    strength=0.6,
                    stability=0.6,
                    basin_radius=0.4,
                    basin_shape=BasinShape.LOCAL,
                )
            self._landscapes[landscape_id] = landscape
            self._record_event("landscape_registered", {
                "landscape_id": landscape_id,
                "dimensions": list(dimensions),
                "attractors": list(landscape.attractors.keys()),
            })
            return {
                "landscape_id": landscape_id,
                "dimensions": list(landscape.dimensions),
                "attractors": list(landscape.attractors.keys()),
                "state_vector": dict(landscape.state_vector),
            }

    def _build_attractor(
        self, spec: Dict[str, Any], dimensions: List[str],
    ) -> Optional[Attractor]:
        attractor_id = spec.get("attractor_id") or spec.get("id")
        if not attractor_id:
            return None
        kind_raw = spec.get("kind", "stable_node")
        try:
            kind = AttractorKind(kind_raw)
        except ValueError:
            kind = AttractorKind.STABLE_NODE
        position = {d: float(spec.get("position", {}).get(d, 0.0)) for d in dimensions}
        shape_raw = spec.get("basin_shape", "local")
        try:
            shape = BasinShape(shape_raw)
        except ValueError:
            shape = BasinShape.LOCAL
        return Attractor(
            attractor_id=attractor_id,
            kind=kind,
            position=position,
            strength=max(0.0, min(1.0, float(spec.get("strength", 0.5)))),
            stability=max(0.0, min(1.0, float(spec.get("stability", 0.5)))),
            basin_radius=max(0.0, min(1.0, float(spec.get("basin_radius", 0.3)))),
            basin_shape=shape,
        )

    def submit_perturbation(
        self,
        landscape_id: str,
        perturbation_vector: Dict[str, float],
        magnitude: float = 0.3,
        kind: PerturbationKind = PerturbationKind.IMPULSE,
    ) -> Dict[str, Any]:
        """Queue a perturbation to be applied on the next PERTURB phase."""
        with self._global_lock:
            landscape = self._landscapes.get(landscape_id)
            if landscape is None:
                return {"error": f"Landscape not found: {landscape_id}"}
            vector = {d: float(perturbation_vector.get(d, 0.0)) for d in landscape.dimensions}
            pert = Perturbation(
                perturbation_id=f"pert_{landscape_id}_{landscape.total_perturbations}_{self._cycle_count}",
                landscape_id=landscape_id,
                kind=kind,
                vector=vector,
                magnitude=max(0.0, min(1.0, magnitude)),
            )
            landscape.pending_perturbations.append(pert)
            self._stats["total_perturbations"] += 1
            landscape.total_perturbations += 1
            self._record_event("perturbation_submitted", {
                "landscape_id": landscape_id,
                "perturbation_id": pert.perturbation_id,
                "kind": kind.value,
                "magnitude": pert.magnitude,
            })
            return {
                "landscape_id": landscape_id,
                "perturbation_id": pert.perturbation_id,
                "kind": kind.value,
                "magnitude": pert.magnitude,
                "vector": dict(vector),
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single dynamical attractor cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = AttractorDynamicsPhase.PERTURB
            phase_outputs.append(self._phase_perturb())
            self._phase = AttractorDynamicsPhase.TRACE
            phase_outputs.append(self._phase_trace())
            self._phase = AttractorDynamicsPhase.BASIN
            phase_outputs.append(self._phase_basin())
            self._phase = AttractorDynamicsPhase.BIFURCATE
            phase_outputs.append(self._phase_bifurcate())
            self._phase = AttractorDynamicsPhase.SETTLE
            phase_outputs.append(self._phase_settle())
            self._cycle_count += 1
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_perturb(self) -> Dict[str, Any]:
        """Perturb phase: apply queued (or synthesized) perturbations to each landscape."""
        applied = 0
        synthesized = 0
        for landscape in self._landscapes.values():
            # If no perturbation is queued, synthesize a small drift so the
            # landscape keeps evolving.
            if not landscape.pending_perturbations:
                vector = {d: random.uniform(-0.3, 0.3) for d in landscape.dimensions}
                pert = Perturbation(
                    perturbation_id=f"pert_{landscape.landscape_id}_syn_{self._cycle_count}",
                    landscape_id=landscape.landscape_id,
                    kind=random.choice(list(PerturbationKind)),
                    vector=vector,
                    magnitude=random.uniform(0.1, 0.3),
                )
                landscape.pending_perturbations.append(pert)
                synthesized += 1
            # Apply all queued perturbations to the state vector.
            while landscape.pending_perturbations:
                pert = landscape.pending_perturbations.pop(0)
                for dim in landscape.dimensions:
                    delta = pert.vector.get(dim, 0.0) * pert.magnitude
                    landscape.state_vector[dim] = self._clamp(
                        landscape.state_vector[dim] + delta
                    )
                applied += 1
                self._record_event("perturbation_applied", {
                    "landscape_id": landscape.landscape_id,
                    "perturbation_id": pert.perturbation_id,
                    "kind": pert.kind.value,
                    "magnitude": pert.magnitude,
                })
        self._record_event("phase_perturb", {
            "applied": applied,
            "synthesized": synthesized,
        })
        return {
            "phase": AttractorDynamicsPhase.PERTURB.value,
            "applied": applied,
            "synthesized": synthesized,
        }

    def _phase_trace(self) -> Dict[str, Any]:
        """Trace phase: step each landscape's state under its vector field."""
        traced = 0
        for landscape in self._landscapes.values():
            start_state = dict(landscape.state_vector)
            points: List[TrajectoryPoint] = [
                TrajectoryPoint(
                    step=0,
                    state=dict(start_state),
                    velocity={d: 0.0 for d in landscape.dimensions},
                )
            ]
            current = dict(start_state)
            for step_idx in range(1, self._TRACE_STEPS + 1):
                velocity = self._field_velocity(landscape, current)
                next_state = {
                    d: self._clamp(current[d] + velocity.get(d, 0.0) * self._TRACE_STEP_SIZE)
                    for d in landscape.dimensions
                }
                points.append(TrajectoryPoint(
                    step=step_idx,
                    state=dict(next_state),
                    velocity=dict(velocity),
                ))
                current = next_state
            trajectory = Trajectory(
                trajectory_id=f"traj_{landscape.landscape_id}_{self._cycle_count}",
                landscape_id=landscape.landscape_id,
                points=points,
                state=TrajectoryState.DIVERGING,
            )
            landscape.active_trajectory = trajectory
            landscape.total_trajectories += 1
            self._stats["total_trajectories"] += 1
            traced += 1
        self._record_event("phase_trace", {"traced": traced})
        return {
            "phase": AttractorDynamicsPhase.TRACE.value,
            "traced": traced,
            "steps": self._TRACE_STEPS,
        }

    def _phase_basin(self) -> Dict[str, Any]:
        """Basin phase: identify which attractor basin each trajectory converges toward."""
        identified = 0
        for landscape in self._landscapes.values():
            traj = landscape.active_trajectory
            if traj is None or not traj.points:
                continue
            target_id, convergence = self._identify_basin(landscape, traj)
            traj.target_attractor_id = target_id
            traj.convergence = convergence
            if target_id is not None:
                if convergence >= self._CONVERGENCE_THRESHOLD:
                    traj.state = TrajectoryState.CONVERGING
                elif convergence > 0.2:
                    traj.state = TrajectoryState.ORBITING
                else:
                    traj.state = TrajectoryState.DIVERGING
                landscape.last_basin_attractor_id = target_id
                identified += 1
            else:
                traj.state = TrajectoryState.DIVERGING
        self._record_event("phase_basin", {"identified": identified})
        return {
            "phase": AttractorDynamicsPhase.BASIN.value,
            "identified": identified,
        }

    def _phase_bifurcate(self) -> Dict[str, Any]:
        """Bifurcate phase: detect bifurcation / regime-change crossings."""
        crossed = 0
        events: List[Dict[str, Any]] = []
        for landscape in self._landscapes.values():
            traj = landscape.active_trajectory
            if traj is None or not traj.points:
                continue
            # A bifurcation is suspected when a state coordinate exceeds its
            # bifurcation parameter and the trajectory is not converging.
            kind = BifurcationKind.NONE
            for dim in landscape.dimensions:
                value = abs(traj.points[-1].state.get(dim, 0.0))
                threshold = landscape.bifurcation_params.get(
                    dim, self._BIFURCATION_THRESHOLD
                )
                if value >= threshold and traj.state != TrajectoryState.CONVERGING:
                    kind = self._classify_bifurcation(landscape, dim, value)
                    break
            if kind != BifurcationKind.NONE:
                traj.bifurcations_crossed += 1
                traj.state = TrajectoryState.BIFURCATED
                landscape.last_bifurcation = kind
                landscape.total_bifurcations += 1
                self._stats["total_bifurcations"] += 1
                crossed += 1
                events.append({
                    "landscape_id": landscape.landscape_id,
                    "kind": kind.value,
                })
                self._record_event("bifurcation_crossed", {
                    "landscape_id": landscape.landscape_id,
                    "kind": kind.value,
                    "trajectory_id": traj.trajectory_id,
                })
            else:
                landscape.last_bifurcation = BifurcationKind.NONE
        self._record_event("phase_bifurcate", {"crossed": crossed})
        return {
            "phase": AttractorDynamicsPhase.BIFURCATE.value,
            "crossed": crossed,
            "events": events,
        }

    def _phase_settle(self) -> Dict[str, Any]:
        """Settle phase: snap the state toward its basin and emit a snapshot."""
        settled = 0
        snapshots: List[Dict[str, Any]] = []
        for landscape in self._landscapes.values():
            traj = landscape.active_trajectory
            if traj is None:
                continue
            if traj.state == TrajectoryState.BIFURCATED:
                # Bifurcated trajectories do not settle; the state keeps its
                # traced endpoint to reflect the regime change.
                traj.settled_at = None
                snapshots.append(self._landscape_snapshot(landscape, settled=False))
                continue
            target_id = traj.target_attractor_id
            if target_id is not None and traj.convergence >= self._CONVERGENCE_THRESHOLD:
                target = landscape.attractors.get(target_id)
                if target is not None:
                    # Snap the live state toward the target attractor position.
                    for dim in landscape.dimensions:
                        target_pos = target.position.get(dim, 0.0)
                        current = landscape.state_vector.get(dim, 0.0)
                        landscape.state_vector[dim] = self._clamp(
                            current + (target_pos - current) * self._SETTLE_SNAP_FACTOR
                        )
                    traj.state = TrajectoryState.SETTLED
                    traj.settled_at = time.time()
                    landscape.total_settled += 1
                    self._stats["total_settled"] += 1
                    settled += 1
            snapshots.append(self._landscape_snapshot(
                landscape, settled=(traj.state == TrajectoryState.SETTLED)
            ))
        self._record_event("phase_settle", {"settled": settled})
        return {
            "phase": AttractorDynamicsPhase.SETTLE.value,
            "settled": settled,
            "snapshots": snapshots,
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    def _field_velocity(
        self, landscape: AttractorLandscape, state: Dict[str, float],
    ) -> Dict[str, float]:
        """Compute the vector field velocity at a state, summed across attractors."""
        velocity = {d: 0.0 for d in landscape.dimensions}
        for attractor in landscape.attractors.values():
            # Distance from the state to the attractor position.
            distance = self._euclidean_distance(state, attractor.position, landscape.dimensions)
            # Pull strength falls off with distance and grows with attractor strength.
            pull = attractor.strength / (1.0 + distance * 4.0)
            if attractor.kind == AttractorKind.REPELLOR:
                pull = -pull
            elif attractor.kind == AttractorKind.STRANGE:
                # Strange attractors pull only half as hard; their swirl comes later.
                pull = pull * 0.5
            for idx, dim in enumerate(landscape.dimensions):
                target_pos = attractor.position.get(dim, 0.0)
                current = state.get(dim, 0.0)
                direction = target_pos - current
                sign = 1.0
                if attractor.kind == AttractorKind.SADDLE and idx > 0:
                    # Saddles attract along the first axis, repel along the rest.
                    sign = -1.0
                if attractor.kind == AttractorKind.STRANGE:
                    # Tangential swirl: alternate the direction sign per axis.
                    direction = -direction if idx % 2 == 0 else direction
                velocity[dim] += sign * pull * direction
        return velocity

    @staticmethod
    def _euclidean_distance(
        a: Dict[str, float], b: Dict[str, float], dimensions: List[str],
    ) -> float:
        if not dimensions:
            return 0.0
        total = 0.0
        for dim in dimensions:
            diff = a.get(dim, 0.0) - b.get(dim, 0.0)
            total += diff * diff
        return math.sqrt(total / len(dimensions))

    def _identify_basin(
        self, landscape: AttractorLandscape, trajectory: Trajectory,
    ) -> Tuple[Optional[str], float]:
        """Identify which attractor basin a trajectory is converging toward."""
        if not trajectory.points or not landscape.attractors:
            return None, 0.0
        start = trajectory.points[0].state
        end = trajectory.points[-1].state
        best_id: Optional[str] = None
        best_score = 0.0
        for attractor in landscape.attractors.values():
            if attractor.kind == AttractorKind.REPELLOR:
                continue
            start_dist = self._euclidean_distance(start, attractor.position, landscape.dimensions)
            end_dist = self._euclidean_distance(end, attractor.position, landscape.dimensions)
            # Convergence: did the trajectory get closer to this attractor?
            approach = max(0.0, start_dist - end_dist)
            # And is it within the basin radius?
            within_basin = end_dist <= attractor.basin_radius
            score = attractor.strength * (approach + (0.2 if within_basin else 0.0))
            if score > best_score:
                best_score = score
                best_id = attractor.attractor_id
        # Normalize the convergence to a 0.0-1.0 range.
        convergence = max(0.0, min(1.0, best_score))
        return best_id, convergence

    def _classify_bifurcation(
        self, landscape: AttractorLandscape, dim: str, value: float,
    ) -> BifurcationKind:
        """Classify the kind of bifurcation a crossing represents."""
        attractor_count = len(landscape.attractors)
        if attractor_count >= 3:
            return BifurcationKind.PITCHFORK
        if attractor_count == 2:
            return BifurcationKind.TRANSCRITICAL
        # Strong overshoots look like a Hopf limit-cycle birth.
        if value >= 0.95:
            return BifurcationKind.HOPF
        return BifurcationKind.SADDLE_NODE

    def _landscape_snapshot(
        self, landscape: AttractorLandscape, settled: bool,
    ) -> Dict[str, Any]:
        traj = landscape.active_trajectory
        return {
            "landscape_id": landscape.landscape_id,
            "state_vector": dict(landscape.state_vector),
            "trajectory_state": traj.state.value if traj is not None else None,
            "target_attractor_id": (
                traj.target_attractor_id if traj is not None else None
            ),
            "convergence": traj.convergence if traj is not None else 0.0,
            "settled": settled,
            "last_bifurcation": landscape.last_bifurcation.value,
            "last_basin_attractor_id": landscape.last_basin_attractor_id,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "landscapes": len(self._landscapes),
                "stats": dict(self._stats),
            }

    def get_landscapes(self) -> List[Dict[str, Any]]:
        with self._global_lock:
            return [self._landscape_summary(l) for l in self._landscapes.values()]

    def get_landscape(self, landscape_id: str) -> Dict[str, Any]:
        with self._global_lock:
            landscape = self._landscapes.get(landscape_id)
            if landscape is None:
                return {"error": f"Landscape not found: {landscape_id}"}
            return self._landscape_summary(landscape)

    def _landscape_summary(self, landscape: AttractorLandscape) -> Dict[str, Any]:
        traj = landscape.active_trajectory
        return {
            "landscape_id": landscape.landscape_id,
            "dimensions": list(landscape.dimensions),
            "state_vector": dict(landscape.state_vector),
            "attractors": [
                {
                    "attractor_id": a.attractor_id,
                    "kind": a.kind.value,
                    "position": dict(a.position),
                    "strength": a.strength,
                    "stability": a.stability,
                    "basin_radius": a.basin_radius,
                    "basin_shape": a.basin_shape.value,
                }
                for a in landscape.attractors.values()
            ],
            "active_trajectory": (
                {
                    "trajectory_id": traj.trajectory_id,
                    "state": traj.state.value,
                    "target_attractor_id": traj.target_attractor_id,
                    "convergence": traj.convergence,
                    "points": len(traj.points),
                    "bifurcations_crossed": traj.bifurcations_crossed,
                }
                if traj is not None
                else None
            ),
            "last_basin_attractor_id": landscape.last_basin_attractor_id,
            "last_bifurcation": landscape.last_bifurcation.value,
            "total_perturbations": landscape.total_perturbations,
            "total_trajectories": landscape.total_trajectories,
            "total_bifurcations": landscape.total_bifurcations,
            "total_settled": landscape.total_settled,
            "created_at": landscape.created_at,
        }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic landscapes and run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_landscapes()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_landscapes(self) -> None:
        """Seed a small synthetic set of attractor landscapes."""
        # A two-dimensional tension/momentum landscape with a stable node and saddle.
        if "sim_world_main" not in self._landscapes:
            self.register_landscape(
                "sim_world_main",
                dimensions=["tension", "momentum"],
                attractors=[
                    {
                        "attractor_id": "sim_calm",
                        "kind": "stable_node",
                        "position": {"tension": 0.2, "momentum": 0.2},
                        "strength": 0.7,
                        "stability": 0.7,
                        "basin_radius": 0.5,
                        "basin_shape": "global",
                    },
                    {
                        "attractor_id": "sim_strife",
                        "kind": "saddle",
                        "position": {"tension": 0.8, "momentum": 0.5},
                        "strength": 0.4,
                        "stability": 0.3,
                        "basin_radius": 0.3,
                        "basin_shape": "local",
                    },
                ],
            )
        # A three-dimensional landscape with a strange attractor.
        if "sim_world_strange" not in self._landscapes:
            self.register_landscape(
                "sim_world_strange",
                dimensions=["flux", "spin", "drift"],
                attractors=[
                    {
                        "attractor_id": "sim_vortex",
                        "kind": "strange",
                        "position": {"flux": 0.5, "spin": 0.5, "drift": 0.5},
                        "strength": 0.6,
                        "stability": 0.2,
                        "basin_radius": 0.6,
                        "basin_shape": "fractal",
                    },
                ],
            )
        # A single-dimension landscape teetering near a bifurcation.
        if "sim_world_edge" not in self._landscapes:
            self.register_landscape(
                "sim_world_edge",
                dimensions=["balance"],
                attractors=[
                    {
                        "attractor_id": "sim_tipping",
                        "kind": "stable_node",
                        "position": {"balance": 0.1},
                        "strength": 0.5,
                        "stability": 0.4,
                        "basin_radius": 0.4,
                        "basin_shape": "local",
                    },
                ],
            )
            # Push the edge landscape's state near the bifurcation threshold.
            edge = self._landscapes.get("sim_world_edge")
            if edge is not None:
                edge.state_vector["balance"] = 0.6

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._landscapes.clear()
            self._events_log.clear()
            self._phase = AttractorDynamicsPhase.PERTURB
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
