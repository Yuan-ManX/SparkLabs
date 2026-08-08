"""
SparkLabs Engine - Causality Cascade Simulator

The CausalityCascadeSimulator models how a small perturbation at one
event ripples through the causal dependency graph of the timeline. A
nudge introduced at a source event propagates along cause->effect
edges, splitting into alternative consequence branches at each hop.
The further a ripple travels from its origin the more it is damped,
so distant consequences fade - but the branching factor can still
produce a wide envelope of small effects. The surviving ripples fold
into a single cascade signature that is emitted back onto the
timeline as a cascade envelope.

The butterfly effect here is not a single dramatic consequence but
the aggregate reshuffling produced by many small, damped, branching
ripples - a cascade signature that captures how one event rewrites
the shape of what comes after.

Architecture:
  PROPAGATE  ->  BRANCH     ->  DAMPEN     ->  ACCUMULATE  ->  EMIT
  (a seed      (the wavefront    (each ripple     (the surviving      (the cascade
   perturbs    splits into       loses energy     ripples fold into    envelope is
   the graph   alternative       with causal      a single signature)  released onto
   as a wave)  consequence       distance)                              the timeline)
              paths)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import hashlib
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

class CascadeSimPhase(Enum):
    """Phases of the causality cascade cycle."""
    PROPAGATE = "propagate"      # a perturbation radiates through the causal graph
    BRANCH = "branch"            # the wavefront splits into alternative paths
    DAMPEN = "dampen"            # ripples lose energy with causal distance
    ACCUMULATE = "accumulate"    # surviving ripples fold into a signature
    EMIT = "emit"                # the cascade envelope is released onto the timeline


class PerturbationKind(Enum):
    """The kind of perturbation introduced at a source event."""
    NUDGE = "nudge"              # a small push, ripples stay local
    SHOVE = "shove"              # a moderate push, ripples travel several hops
    SHOCK = "shock"              # a large push, ripples reach the graph rim
    TREMOR = "tremor"            # a faint push, ripples die out quickly


class BranchPolarity(Enum):
    """How a branched consequence path relates to its parent ripple."""
    AMPLIFYING = "amplifying"    # the branch swells the consequence
    DAMPING = "damping"          # the branch softens the consequence
    NEUTRAL = "neutral"          # the branch holds the consequence steady
    INVERTING = "inverting"      # the branch reverses the consequence


class RippleRelation(Enum):
    """How a propagated ripple relates to its source."""
    DIRECT = "direct"            # a single hop from the source event
    INDIRECT = "indirect"        # multiple hops from the source event
    CONVERGENT = "convergent"    # the target is reached via multiple paths
    DIVERGENT = "divergent"      # the source fans out to many targets


class CascadeState(Enum):
    """State of an in-flight cascade as it moves through the cycle."""
    SEEDED = "seeded"            # perturbation queued, no ripples yet
    PROPAGATING = "propagating"  # ripples are radiating through the graph
    BRANCHED = "branched"        # alternative paths have been split off
    DAMPENED = "dampened"        # weak ripples have been dropped
    ACCUMULATED = "accumulated"  # surviving ripples folded into a signature
    EMITTED = "emitted"          # the envelope has been released


class CascadeVitality(Enum):
    """The overall vitality of the cascade ecosystem."""
    DORMANT = "dormant"          # no cascades, no pending perturbations
    RIPPLING = "rippling"        # a healthy flow of cascades
    SURGING = "surging"          # perturbations piling up faster than they emit
    SATURATED = "saturated"      # the cascade store is full
    COLLAPSED = "collapsed"      # cascades exist but their magnitudes have faded


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CausalEvent:
    """An event in the causal dependency graph."""
    event_id: str
    causes: List[str] = field(default_factory=list)   # event_ids that lead into this one
    effects: List[str] = field(default_factory=list)  # event_ids this one leads into
    strength: float = 0.5                              # 0.0-1.0, intrinsic weight
    created_at: float = field(default_factory=time.time)


@dataclass
class Perturbation:
    """A perturbation queued for propagation from a source event."""
    perturbation_id: str
    source_event_id: str
    strength: float = 0.5                  # 0.0-1.0
    kind: PerturbationKind = PerturbationKind.NUDGE
    created_at: float = field(default_factory=time.time)


@dataclass
class PropagatedRipple:
    """A ripple radiated outward from a perturbation along a cause->effect edge."""
    ripple_id: str
    cascade_id: str
    source_event_id: str                   # the event the ripple arrived from
    target_event_id: str                   # the event the ripple arrives at
    intensity: float = 0.3                 # 0.0-1.0
    distance: int = 1                      # hops from the perturbation origin
    relation: RippleRelation = RippleRelation.DIRECT
    path: List[str] = field(default_factory=list)  # the chain of events traversed


@dataclass
class BranchPath:
    """An alternative consequence path split off from a ripple."""
    branch_id: str
    cascade_id: str
    parent_ripple_id: str
    polarity: BranchPolarity
    magnitude: float = 0.3                 # 0.0-1.0
    label: str = ""


@dataclass
class CascadeSignature:
    """The folded signature of all surviving ripples and branches."""
    cascade_id: str
    source_event_id: str
    total_magnitude: float = 0.0
    ripple_count: int = 0
    branch_count: int = 0
    surviving_ripple_count: int = 0
    surviving_branch_count: int = 0
    max_distance: int = 0
    fingerprint: str = ""


@dataclass
class CascadeEnvelope:
    """A cascade signature packaged for emission onto the timeline."""
    cascade_id: str
    source_event_id: str
    signature: CascadeSignature
    emitted_at: float = field(default_factory=time.time)
    note: str = ""


# =============================================================================
# Simulator
# =============================================================================

class CausalityCascadeSimulator:
    """
    Thread-safe singleton orchestrating causality cascade simulation.

    Usage:
        sim = CausalityCascadeSimulator.get_instance()
        sim.register_event("e1", causes=[], effects=["e2", "e3"], strength=0.6)
        sim.cycle()
        cascades = sim.get_cascades()
    """

    _instance: Optional["CausalityCascadeSimulator"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _PROPAGATE_DECAY = 0.75             # intensity lost per hop
    _PROPAGATE_MAX_HOPS = 4             # how far a ripple radiates
    _BRANCH_FACTOR = 2                  # max branches per ripple
    _DAMPEN_DISTANCE_FACTOR = 0.85      # per-hop damping multiplier
    _DAMPEN_THRESHOLD = 0.05            # below this, ripples/branches are dropped
    _MAX_EVENTS = 200                   # events log cap
    _MAX_CASCADES = 50                  # stored cascade envelope cap
    _MAX_RIPPLES_PER_CASCADE = 100
    _MAX_BRANCHES_PER_CASCADE = 120
    _VITALITY_SURGE_PENDING = 5         # pending perturbations before surge

    def __init__(self) -> None:
        self._events: Dict[str, CausalEvent] = {}
        self._pending: Deque[Perturbation] = deque()
        self._cascades: Dict[str, CascadeEnvelope] = {}
        self._active_cascade_id: Optional[str] = None
        self._active_source_event_id: Optional[str] = None
        self._active_state: CascadeState = CascadeState.SEEDED
        self._active_ripples: List[PropagatedRipple] = []
        self._active_branches: List[BranchPath] = []
        self._active_signature: Optional[CascadeSignature] = None
        self._phase: CascadeSimPhase = CascadeSimPhase.PROPAGATE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "CausalityCascadeSimulator":
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
            "total_events_registered": 0,
            "total_perturbations": 0,
            "total_ripples": 0,
            "total_branches": 0,
            "total_damped": 0,
            "total_dropped": 0,
            "total_cascades": 0,
            "active_cascades": 0,
            "avg_cascade_magnitude": 0.0,
            "max_cascade_distance": 0,
            "vitality": CascadeVitality.DORMANT.value,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self, **kwargs: Any) -> None:
        # Apply any explicit stat overrides passed by the caller.
        for key, value in kwargs.items():
            self._stats[key] = value
        # Recompute derived stats from the stored cascade envelopes.
        magnitudes: List[float] = [
            env.signature.total_magnitude for env in self._cascades.values()
        ]
        max_distances: List[int] = [
            env.signature.max_distance for env in self._cascades.values()
        ]
        self._stats["total_cascades"] = len(self._cascades)
        self._stats["active_cascades"] = 1 if self._active_cascade_id else 0
        self._stats["avg_cascade_magnitude"] = (
            sum(magnitudes) / len(magnitudes) if magnitudes else 0.0
        )
        self._stats["max_cascade_distance"] = max(max_distances) if max_distances else 0
        self._stats["vitality"] = self._derive_vitality().value

    def _derive_vitality(self) -> CascadeVitality:
        cascade_count = len(self._cascades)
        pending = len(self._pending)
        if cascade_count == 0 and pending == 0:
            return CascadeVitality.DORMANT
        if cascade_count >= self._MAX_CASCADES:
            return CascadeVitality.SATURATED
        avg_mag = self._stats.get("avg_cascade_magnitude", 0.0)
        if cascade_count > 0 and avg_mag < self._DAMPEN_THRESHOLD:
            return CascadeVitality.COLLAPSED
        if pending >= self._VITALITY_SURGE_PENDING or cascade_count >= self._MAX_CASCADES // 2:
            return CascadeVitality.SURGING
        return CascadeVitality.RIPPLING

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Event Registration
    # -------------------------------------------------------------------------

    def register_event(self, event_id: str, causes: List[str],
                       effects: List[str], strength: float = 0.5) -> Dict[str, Any]:
        """Register a causal event and queue a perturbation for it."""
        with self._global_lock:
            if event_id in self._events:
                return {"error": f"Event already registered: {event_id}"}
            event = CausalEvent(
                event_id=event_id,
                causes=list(causes),
                effects=list(effects),
                strength=max(0.0, min(1.0, strength)),
            )
            self._events[event_id] = event
            self._stats["total_events_registered"] += 1
            # Registering an event kicks the graph: queue a perturbation from it.
            self._inject_perturbation(event_id, strength=event.strength)
            self._record_event("event_registered", {
                "event_id": event_id,
                "causes": list(causes),
                "effects": list(effects),
                "strength": event.strength,
            })
            return {
                "event_id": event_id,
                "causes": list(causes),
                "effects": list(effects),
                "strength": event.strength,
                "perturbation_queued": True,
            }

    def _inject_perturbation(self, event_id: str, strength: float = 0.5) -> None:
        """Queue a perturbation originating from a registered event."""
        kind = self._classify_perturbation(strength)
        perturbation = Perturbation(
            perturbation_id=f"pert_{event_id}_{self._cycle_count}_{len(self._pending)}",
            source_event_id=event_id,
            strength=max(0.0, min(1.0, strength)),
            kind=kind,
        )
        self._pending.append(perturbation)
        self._stats["total_perturbations"] += 1

    def _classify_perturbation(self, strength: float) -> PerturbationKind:
        if strength >= 0.7:
            return PerturbationKind.SHOCK
        if strength >= 0.45:
            return PerturbationKind.SHOVE
        if strength >= 0.2:
            return PerturbationKind.NUDGE
        return PerturbationKind.TREMOR

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single causality cascade cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._phase = CascadeSimPhase.PROPAGATE
            phase_outputs.append(self._phase_propagate())
            self._phase = CascadeSimPhase.BRANCH
            phase_outputs.append(self._phase_branch())
            self._phase = CascadeSimPhase.DAMPEN
            phase_outputs.append(self._phase_dampen())
            self._phase = CascadeSimPhase.ACCUMULATE
            phase_outputs.append(self._phase_accumulate())
            self._phase = CascadeSimPhase.EMIT
            phase_outputs.append(self._phase_emit())
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

    def _phase_propagate(self) -> Dict[str, Any]:
        """Propagate phase: dequeue a perturbation and radiate ripples through the graph."""
        # Reset the active cascade slot.
        self._active_cascade_id = None
        self._active_source_event_id = None
        self._active_ripples = []
        self._active_branches = []
        self._active_signature = None
        self._active_state = CascadeState.SEEDED

        if not self._pending:
            self._record_event("phase_propagate", {"ripples": 0, "reason": "no_pending"})
            return {
                "phase": "propagate",
                "ripples_propagated": 0,
                "source_event_id": None,
            }

        perturbation = self._pending.popleft()
        cascade_id = f"cascade_{perturbation.source_event_id}_{self._cycle_count}"
        self._active_cascade_id = cascade_id
        self._active_source_event_id = perturbation.source_event_id
        self._active_state = CascadeState.PROPAGATING

        # Breadth-first propagation along cause->effect edges.
        ripples: List[PropagatedRipple] = []
        visited: Dict[str, int] = {perturbation.source_event_id: 0}
        frontier: Deque[Tuple[str, float, int, List[str]]] = deque([
            (perturbation.source_event_id, perturbation.strength, 0,
             [perturbation.source_event_id])
        ])

        while frontier and len(ripples) < self._MAX_RIPPLES_PER_CASCADE:
            event_id, intensity, distance, path = frontier.popleft()
            if distance >= self._PROPAGATE_MAX_HOPS:
                continue
            event = self._events.get(event_id)
            if event is None:
                continue
            for effect_id in event.effects:
                if effect_id not in self._events:
                    continue
                new_intensity = intensity * self._PROPAGATE_DECAY
                new_distance = distance + 1
                new_path = path + [effect_id]
                relation = self._classify_ripple(new_distance, event)
                ripple = PropagatedRipple(
                    ripple_id=f"ripple_{cascade_id}_{effect_id}_{new_distance}_{len(ripples)}",
                    cascade_id=cascade_id,
                    source_event_id=event_id,
                    target_event_id=effect_id,
                    intensity=max(0.0, min(1.0, new_intensity)),
                    distance=new_distance,
                    relation=relation,
                    path=new_path,
                )
                ripples.append(ripple)
                self._stats["total_ripples"] += 1
                # Continue radiating from this effect if we have not seen it closer.
                if effect_id not in visited or visited[effect_id] > new_distance:
                    visited[effect_id] = new_distance
                    frontier.append((effect_id, new_intensity, new_distance, new_path))

        self._active_ripples = ripples
        self._record_event("phase_propagate", {
            "cascade_id": cascade_id,
            "source_event_id": perturbation.source_event_id,
            "perturbation_kind": perturbation.kind.value,
            "ripples": len(ripples),
        })
        return {
            "phase": "propagate",
            "cascade_id": cascade_id,
            "source_event_id": perturbation.source_event_id,
            "perturbation_kind": perturbation.kind.value,
            "ripples_propagated": len(ripples),
        }

    def _phase_branch(self) -> Dict[str, Any]:
        """Branch phase: split each ripple into alternative consequence paths."""
        if not self._active_cascade_id:
            self._record_event("phase_branch", {"branches": 0, "reason": "no_active_cascade"})
            return {"phase": "branch", "branches_created": 0}

        cascade_id = self._active_cascade_id
        polarities = list(BranchPolarity)
        branches: List[BranchPath] = []
        for ripple in self._active_ripples:
            if len(branches) >= self._MAX_BRANCHES_PER_CASCADE:
                break
            # Each ripple spawns between 0 and _BRANCH_FACTOR branches.
            branch_count = random.randint(0, self._BRANCH_FACTOR)
            chosen = random.sample(polarities, min(branch_count, len(polarities)))
            for polarity in chosen:
                magnitude = self._branch_magnitude(ripple, polarity)
                branch = BranchPath(
                    branch_id=f"branch_{ripple.ripple_id}_{polarity.value}_{len(branches)}",
                    cascade_id=cascade_id,
                    parent_ripple_id=ripple.ripple_id,
                    polarity=polarity,
                    magnitude=magnitude,
                    label=self._branch_label(polarity),
                )
                branches.append(branch)
                self._stats["total_branches"] += 1

        self._active_branches = branches
        self._active_state = CascadeState.BRANCHED
        self._record_event("phase_branch", {
            "cascade_id": cascade_id,
            "branches": len(branches),
        })
        return {
            "phase": "branch",
            "cascade_id": cascade_id,
            "branches_created": len(branches),
        }

    def _phase_dampen(self) -> Dict[str, Any]:
        """Dampen phase: shrink ripples and branches by causal distance, drop the weak."""
        if not self._active_cascade_id:
            self._record_event("phase_dampen", {"damped": 0, "dropped": 0, "reason": "no_active_cascade"})
            return {"phase": "dampen", "damped": 0, "dropped": 0}

        damped = 0
        dropped = 0

        # Dampen ripples by their distance from the origin.
        surviving_ripples: List[PropagatedRipple] = []
        for ripple in self._active_ripples:
            factor = self._DAMPEN_DISTANCE_FACTOR ** ripple.distance
            ripple.intensity = ripple.intensity * factor
            if ripple.intensity < self._DAMPEN_THRESHOLD:
                dropped += 1
                continue
            surviving_ripples.append(ripple)
            damped += 1

        # Dampen branches by their parent ripple's distance.
        ripple_by_id = {r.ripple_id: r for r in self._active_ripples}
        surviving_branches: List[BranchPath] = []
        for branch in self._active_branches:
            parent = ripple_by_id.get(branch.parent_ripple_id)
            distance = parent.distance if parent is not None else 1
            factor = self._DAMPEN_DISTANCE_FACTOR ** distance
            branch.magnitude = branch.magnitude * factor
            if branch.magnitude < self._DAMPEN_THRESHOLD:
                dropped += 1
                continue
            surviving_branches.append(branch)
            damped += 1

        self._active_ripples = surviving_ripples
        self._active_branches = surviving_branches
        self._active_state = CascadeState.DAMPENED
        self._stats["total_damped"] += damped
        self._stats["total_dropped"] += dropped
        self._record_event("phase_dampen", {
            "cascade_id": self._active_cascade_id,
            "damped": damped,
            "dropped": dropped,
        })
        return {
            "phase": "dampen",
            "cascade_id": self._active_cascade_id,
            "damped": damped,
            "dropped": dropped,
        }

    def _phase_accumulate(self) -> Dict[str, Any]:
        """Accumulate phase: fold surviving ripples and branches into a cascade signature."""
        if not self._active_cascade_id:
            self._record_event("phase_accumulate", {"reason": "no_active_cascade"})
            return {"phase": "accumulate", "signature": None}

        total_magnitude = (
            sum(r.intensity for r in self._active_ripples)
            + sum(b.magnitude for b in self._active_branches)
        )
        max_distance = max((r.distance for r in self._active_ripples), default=0)

        # Build a deterministic fingerprint from the surviving ripple paths.
        path_tokens = sorted(":".join(r.path) for r in self._active_ripples)
        digest = hashlib.sha256("|".join(path_tokens).encode("utf-8")).hexdigest()
        fingerprint = digest[:8]

        signature = CascadeSignature(
            cascade_id=self._active_cascade_id,
            source_event_id=self._active_source_event_id or "",
            total_magnitude=total_magnitude,
            ripple_count=len(self._active_ripples),
            branch_count=len(self._active_branches),
            surviving_ripple_count=len(self._active_ripples),
            surviving_branch_count=len(self._active_branches),
            max_distance=max_distance,
            fingerprint=fingerprint,
        )
        self._active_signature = signature
        self._active_state = CascadeState.ACCUMULATED

        self._record_event("phase_accumulate", {
            "cascade_id": self._active_cascade_id,
            "total_magnitude": total_magnitude,
            "fingerprint": fingerprint,
        })
        return {
            "phase": "accumulate",
            "cascade_id": self._active_cascade_id,
            "signature": {
                "cascade_id": signature.cascade_id,
                "source_event_id": signature.source_event_id,
                "total_magnitude": signature.total_magnitude,
                "ripple_count": signature.ripple_count,
                "branch_count": signature.branch_count,
                "max_distance": signature.max_distance,
                "fingerprint": signature.fingerprint,
            },
        }

    def _phase_emit(self) -> Dict[str, Any]:
        """Emit phase: package the signature into a cascade envelope on the timeline."""
        if not self._active_cascade_id or self._active_signature is None:
            self._record_event("phase_emit", {"emitted": False, "reason": "no_active_signature"})
            return {"phase": "emit", "emitted": False, "envelope_id": None}

        signature = self._active_signature
        envelope = CascadeEnvelope(
            cascade_id=self._active_cascade_id,
            source_event_id=signature.source_event_id,
            signature=signature,
            emitted_at=time.time(),
            note=self._envelope_note(signature),
        )
        self._cascades[envelope.cascade_id] = envelope
        # Cap the stored cascade envelopes.
        if len(self._cascades) > self._MAX_CASCADES:
            oldest_id = min(
                self._cascades,
                key=lambda cid: self._cascades[cid].emitted_at,
            )
            self._cascades.pop(oldest_id, None)

        self._active_state = CascadeState.EMITTED
        self._record_event("phase_emit", {
            "cascade_id": envelope.cascade_id,
            "fingerprint": signature.fingerprint,
            "total_magnitude": signature.total_magnitude,
        })

        result = {
            "phase": "emit",
            "emitted": True,
            "envelope_id": envelope.cascade_id,
            "cascade_id": envelope.cascade_id,
            "fingerprint": signature.fingerprint,
        }

        # Clear the active cascade slot for the next cycle.
        self._active_cascade_id = None
        self._active_source_event_id = None
        self._active_ripples = []
        self._active_branches = []
        self._active_signature = None
        self._active_state = CascadeState.SEEDED

        return result

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _classify_ripple(self, distance: int, source_event: CausalEvent) -> RippleRelation:
        """Classify how a ripple relates to its source."""
        if distance <= 1:
            # A one-hop ripple is direct unless the source fans out widely.
            if len(source_event.effects) >= 3:
                return RippleRelation.DIVERGENT
            return RippleRelation.DIRECT
        # Multi-hop ripples are indirect unless the target is reached via many causes.
        # We approximate convergence by the number of causes of the source event.
        if len(source_event.causes) >= 2:
            return RippleRelation.CONVERGENT
        return RippleRelation.INDIRECT

    def _branch_magnitude(self, ripple: PropagatedRipple,
                          polarity: BranchPolarity) -> float:
        """Derive a branch's magnitude from its parent ripple and polarity."""
        base = ripple.intensity
        if polarity == BranchPolarity.AMPLIFYING:
            return max(0.0, min(1.0, base * 1.2))
        if polarity == BranchPolarity.DAMPING:
            return max(0.0, min(1.0, base * 0.6))
        if polarity == BranchPolarity.INVERTING:
            return max(0.0, min(1.0, base * 0.8))
        return max(0.0, min(1.0, base))

    def _branch_label(self, polarity: BranchPolarity) -> str:
        return {
            BranchPolarity.AMPLIFYING: "the consequence swells",
            BranchPolarity.DAMPING: "the consequence softens",
            BranchPolarity.NEUTRAL: "the consequence holds",
            BranchPolarity.INVERTING: "the consequence reverses",
        }.get(polarity, "")

    def _envelope_note(self, signature: CascadeSignature) -> str:
        return (
            f"cascade {signature.cascade_id} from {signature.source_event_id} "
            f"with magnitude {signature.total_magnitude:.3f} across "
            f"{signature.max_distance} hops"
        )

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "events_registered": len(self._events),
                "pending_perturbations": len(self._pending),
                "cascades": len(self._cascades),
                "active_cascade_id": self._active_cascade_id,
                "active_state": self._active_state.value,
                "stats": dict(self._stats),
            }

    def get_cascades(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._global_lock:
            envelopes = sorted(
                self._cascades.values(),
                key=lambda e: e.emitted_at,
                reverse=True,
            )[:limit]
            return [self._envelope_to_dict(e) for e in envelopes]

    def get_cascade(self, cascade_id: str) -> Dict[str, Any]:
        with self._global_lock:
            envelope = self._cascades.get(cascade_id)
            if envelope is None:
                return {"error": f"Cascade not found: {cascade_id}"}
            return self._envelope_to_dict(envelope)

    def _envelope_to_dict(self, envelope: CascadeEnvelope) -> Dict[str, Any]:
        sig = envelope.signature
        return {
            "cascade_id": envelope.cascade_id,
            "source_event_id": envelope.source_event_id,
            "emitted_at": envelope.emitted_at,
            "note": envelope.note,
            "signature": {
                "total_magnitude": sig.total_magnitude,
                "ripple_count": sig.ripple_count,
                "branch_count": sig.branch_count,
                "surviving_ripple_count": sig.surviving_ripple_count,
                "surviving_branch_count": sig.surviving_branch_count,
                "max_distance": sig.max_distance,
                "fingerprint": sig.fingerprint,
            },
        }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed a synthetic causal graph and run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_events()
            # Ensure enough perturbations are queued so every cycle has work.
            event_ids = list(self._events.keys())
            while len(self._pending) < cycles and event_ids:
                source = random.choice(event_ids)
                self._inject_perturbation(source, strength=random.uniform(0.4, 0.8))
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_completed": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_events(self) -> None:
        """Seed a small synthetic causal graph with a branching structure."""
        # The graph fans out from sim_a and converges again at sim_i.
        seed_events: List[Tuple[str, List[str], List[str], float, str]] = [
            ("sim_a", [], ["sim_b", "sim_e"], 0.6, "the seed"),
            ("sim_b", ["sim_a"], ["sim_c", "sim_f"], 0.5, "first echo"),
            ("sim_c", ["sim_b"], ["sim_d", "sim_g"], 0.5, "second echo"),
            ("sim_d", ["sim_c"], ["sim_h"], 0.4, "third echo"),
            ("sim_e", ["sim_a"], ["sim_g"], 0.4, "side channel"),
            ("sim_f", ["sim_b"], ["sim_h"], 0.3, "fork"),
            ("sim_g", ["sim_c", "sim_e"], ["sim_i"], 0.4, "convergence"),
            ("sim_h", ["sim_d", "sim_f"], ["sim_i"], 0.3, "late fork"),
            ("sim_i", ["sim_g", "sim_h"], [], 0.2, "the rim"),
        ]
        for event_id, causes, effects, strength, _note in seed_events:
            if event_id not in self._events:
                self.register_event(event_id, causes, effects, strength=strength)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._events.clear()
            self._pending.clear()
            self._cascades.clear()
            self._active_cascade_id = None
            self._active_source_event_id = None
            self._active_ripples = []
            self._active_branches = []
            self._active_signature = None
            self._active_state = CascadeState.SEEDED
            self._phase = CascadeSimPhase.PROPAGATE
            self._cycle_count = 0
            self._events_log.clear()
            self._init_stats()
            return {"reset": True}
