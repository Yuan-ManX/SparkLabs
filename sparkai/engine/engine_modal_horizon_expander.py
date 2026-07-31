"""
SparkLabs Engine - Modal Horizon Expander

The EngineModalHorizonExpander treats the game world as a space of
possible world-states, not just the actual one. Around every tension
point in the world there is a fan of candidate alternative worlds the
world could branch into. Most of those candidates are incoherent
against the world's constraints; a few cohere, firm up, and open as
accessible modal horizons - branches the world could step into without
breaking its own laws. Inconsistent or stale horizons close, so the
modal fan never becomes an undifferentiated blur.

This is distinct from collapsing possibilities into one (that is the
work of the possibility collapse theater), from tending the substrate
field that underlies the world (reality substrate), and from diffusing
probability across states (probability mist). The expander's job is to
map and maintain the *reachable modal horizon* - the set of
consistency-checked alternative world-states the world can branch into
on its next move.

Architecture:
  ENUMERATE  ->  PROBE       ->  STABILIZE  ->  OPEN       ->  CLOSE
  (candidate    (each          (consistent     (sufficiently    (inconsistent
   possible-     candidate      candidates       stable           or stale
   worlds are    is probed      firm up;         candidates       horizons are
   enumerated    against the    unstable ones    are opened as    closed so the
   from the      world's        weaken)          accessible       modal fan
   world's       constraints)                    modal horizons)  stays crisp)
   tension
   points)

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

class ModalHorizonPhase(Enum):
    """Phases of the modal horizon expansion cycle."""
    ENUMERATE = "enumerate"    # candidate possible-worlds are enumerated from tensions
    PROBE = "probe"            # each candidate is probed against the world's constraints
    STABILIZE = "stabilize"    # consistent candidates firm up; unstable ones weaken
    OPEN = "open"              # sufficiently stable candidates open as accessible horizons
    CLOSE = "close"            # inconsistent or stale horizons are closed


class CandidateOrigin(Enum):
    """Where a candidate possible-world was enumerated from."""
    TENSION = "tension"        # grown from a tension point in the actual world
    DIVERGENCE = "divergence"  # grown from a fork where the world could split
    OPPORTUNITY = "opportunity"  # grown from an opening in the world
    RESIDUAL = "residual"      # left over from a previously closed horizon


class ConsistencyVerdict(Enum):
    """How a candidate possible-world fares against the world's constraints."""
    CONSISTENT = "consistent"      # coheres with all probed constraints
    PARTIAL = "partial"            # coheres with some, fails others
    INCONSISTENT = "inconsistent"  # violates the world's laws
    UNKNOWN = "unknown"            # not yet probed


class HorizonState(Enum):
    """Lifecycle state of an individual possible-world candidate."""
    CANDIDATE = "candidate"  # enumerated, not yet probed
    PROBING = "probing"      # currently being probed against constraints
    STABLE = "stable"        # firmed up after probing, awaiting opening
    OPEN = "open"            # opened as an accessible modal horizon
    CLOSED = "closed"        # closed due to inconsistency or staleness


class HorizonAccessibility(Enum):
    """How reachable an opened horizon is from the actual world."""
    REACHABLE = "reachable"      # the world can branch into it directly
    CONDITIONAL = "conditional"  # reachable only if some condition holds
    UNREACHABLE = "unreachable"  # no consistent path leads to it


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class WorldConstraint:
    """A law or invariant the world enforces on candidate possible-worlds."""
    constraint_id: str
    label: str
    weight: float = 0.5               # 0.0-1.0, how heavily it bears on consistency
    created_at: float = field(default_factory=time.time)


@dataclass
class PossibleWorldCandidate:
    """A candidate possible-world enumerated from the actual world's tensions."""
    candidate_id: str
    origin: CandidateOrigin
    source_tension: str               # the tension id this candidate was grown from
    description: str = ""
    consistency_score: float = 0.0    # 0.0-1.0, how well it coheres with constraints
    stability: float = 0.0            # 0.0-1.0, how firmly it has settled
    verdict: ConsistencyVerdict = ConsistencyVerdict.UNKNOWN
    state: HorizonState = HorizonState.CANDIDATE
    accessibility: HorizonAccessibility = HorizonAccessibility.CONDITIONAL
    probe_depth: int = 0              # how many probe passes have run
    stale_cycles: int = 0             # how many cycles since the candidate last moved
    opened_at: Optional[float] = None
    closed_at: Optional[float] = None
    close_reason: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class ModalHorizonWorld:
    """Per-world modal horizon ecosystem state."""
    world_id: str
    tensions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    constraints: Dict[str, WorldConstraint] = field(default_factory=dict)
    candidates: Dict[str, PossibleWorldCandidate] = field(default_factory=dict)
    open_horizons: Dict[str, PossibleWorldCandidate] = field(default_factory=dict)
    accessibility: Dict[str, HorizonAccessibility] = field(default_factory=dict)
    total_enumerated: int = 0
    total_probed: int = 0
    total_stabilized: int = 0
    total_opened: int = 0
    total_closed: int = 0


# =============================================================================
# Expander
# =============================================================================

class EngineModalHorizonExpander:
    """
    Thread-safe singleton orchestrating modal horizon expansion.

    Usage:
        expander = EngineModalHorizonExpander.get_instance()
        expander.register_world("alpha")
        expander.add_constraint("alpha", "law_identity", "identities persist", 0.8)
        expander.introduce_tension("alpha", "t1", CandidateOrigin.TENSION,
                                   "a faction splits", 0.6)
        expander.cycle()
        state = expander.get_world_state("alpha")
    """

    _instance: Optional["EngineModalHorizonExpander"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _ENUMERATE_PER_CYCLE = 3            # candidates enumerated per world per cycle
    _PROBE_DEPTH = 2                    # probe passes before a verdict firms up
    _STABILIZE_THRESHOLD = 0.5          # consistency needed to count as stable
    _OPEN_THRESHOLD = 0.6               # stability needed to open as a horizon
    _CLOSE_STALENESS_CYCLES = 4         # cycles without movement before closing
    _MAX_CANDIDATES_PER_WORLD = 40
    _MAX_OPEN_HORIZONS_PER_WORLD = 12
    _MAX_WORLDS = 30
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._worlds: Dict[str, ModalHorizonWorld] = {}
        self._phase: ModalHorizonPhase = ModalHorizonPhase.ENUMERATE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineModalHorizonExpander":
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
            "total_worlds": 0,
            "total_tensions": 0,
            "total_constraints": 0,
            "total_enumerated": 0,
            "total_probed": 0,
            "total_stabilized": 0,
            "total_opened": 0,
            "total_closed": 0,
            "open_horizons": 0,
            "avg_consistency": 0.0,
            "avg_stability": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._worlds:
            return
        consistencies: List[float] = []
        stabilities: List[float] = []
        open_horizons = 0
        total_constraints = 0
        total_tensions = 0
        for world in self._worlds.values():
            open_horizons += len(world.open_horizons)
            total_constraints += len(world.constraints)
            total_tensions += len(world.tensions)
            for cand in world.candidates.values():
                if cand.state == HorizonState.CLOSED:
                    continue
                consistencies.append(cand.consistency_score)
                stabilities.append(cand.stability)
        self._stats["total_worlds"] = len(self._worlds)
        self._stats["total_constraints"] = total_constraints
        self._stats["total_tensions"] = total_tensions
        self._stats["open_horizons"] = open_horizons
        self._stats["avg_consistency"] = (
            sum(consistencies) / len(consistencies) if consistencies else 0.0
        )
        self._stats["avg_stability"] = (
            sum(stabilities) / len(stabilities) if stabilities else 0.0
        )

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # World Management
    # -------------------------------------------------------------------------

    def register_world(self, world_id: str) -> Dict[str, Any]:
        """Register a new world for modal horizon expansion."""
        with self._global_lock:
            if len(self._worlds) >= self._MAX_WORLDS and world_id not in self._worlds:
                return {"error": f"World cap reached ({self._MAX_WORLDS})"}
            if world_id in self._worlds:
                return {"error": f"World already registered: {world_id}"}
            world = ModalHorizonWorld(world_id=world_id)
            self._worlds[world_id] = world
            self._record_event("world_registered", {"world_id": world_id})
            return {
                "world_id": world_id,
                "candidates": 0,
                "open_horizons": 0,
            }

    def remove_world(self, world_id: str) -> Dict[str, Any]:
        with self._global_lock:
            world = self._worlds.pop(world_id, None)
            if world is None:
                return {"error": f"World not found: {world_id}"}
            self._record_event("world_removed", {"world_id": world_id})
            return {
                "removed": world_id,
                "cleared_candidates": len(world.candidates),
                "cleared_horizons": len(world.open_horizons),
            }

    def add_constraint(self, world_id: str, constraint_id: str,
                       label: str, weight: float = 0.5) -> Dict[str, Any]:
        """Add a world constraint that candidate possible-worlds are probed against."""
        with self._global_lock:
            world = self._worlds.get(world_id)
            if world is None:
                return {"error": f"World not found: {world_id}"}
            constraint = WorldConstraint(
                constraint_id=constraint_id,
                label=label,
                weight=max(0.0, min(1.0, weight)),
            )
            world.constraints[constraint_id] = constraint
            self._record_event("constraint_added", {
                "world_id": world_id,
                "constraint_id": constraint_id,
                "label": label,
                "weight": constraint.weight,
            })
            return {
                "world_id": world_id,
                "constraint_id": constraint_id,
                "label": constraint.label,
                "weight": constraint.weight,
            }

    def introduce_tension(self, world_id: str, tension_id: str,
                          origin: CandidateOrigin, description: str = "",
                          magnitude: float = 0.5) -> Dict[str, Any]:
        """Introduce a tension point that seeds candidate possible-worlds in ENUMERATE."""
        with self._global_lock:
            world = self._worlds.get(world_id)
            if world is None:
                return {"error": f"World not found: {world_id}"}
            if tension_id in world.tensions:
                return {"error": f"Tension already exists: {tension_id}"}
            tension = {
                "tension_id": tension_id,
                "origin": origin.value,
                "description": description,
                "magnitude": max(0.0, min(1.0, magnitude)),
                "processed": False,
                "introduced_at": time.time(),
            }
            world.tensions[tension_id] = tension
            self._stats["total_tensions"] += 1
            self._record_event("tension_introduced", {
                "world_id": world_id,
                "tension_id": tension_id,
                "origin": origin.value,
                "magnitude": tension["magnitude"],
            })
            return {
                "world_id": world_id,
                "tension_id": tension_id,
                "origin": origin.value,
                "magnitude": tension["magnitude"],
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single modal horizon expansion cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = ModalHorizonPhase.ENUMERATE
            phase_outputs["enumerate"] = self._phase_enumerate()
            self._phase = ModalHorizonPhase.PROBE
            phase_outputs["probe"] = self._phase_probe()
            self._phase = ModalHorizonPhase.STABILIZE
            phase_outputs["stabilize"] = self._phase_stabilize()
            self._phase = ModalHorizonPhase.OPEN
            phase_outputs["open"] = self._phase_open()
            self._phase = ModalHorizonPhase.CLOSE
            phase_outputs["close"] = self._phase_close()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_enumerate(self) -> Dict[str, Any]:
        """Enumerate phase: grow candidate possible-worlds from unprocessed tensions."""
        enumerated = 0
        for world in self._worlds.values():
            unprocessed = [
                t for t in world.tensions.values() if not t["processed"]
            ]
            # Even with no fresh tensions, residual divergence can spawn candidates.
            if not unprocessed and world.candidates:
                unprocessed = [{
                    "tension_id": f"divergence_{self._cycle_count}",
                    "origin": CandidateOrigin.DIVERGENCE.value,
                    "description": "a fork where the world could split",
                    "magnitude": 0.3,
                    "processed": False,
                    "introduced_at": time.time(),
                }]
            # Bound candidates enumerated per world per cycle.
            slots = max(0, self._ENUMERATE_PER_CYCLE)
            for tension in unprocessed[:slots]:
                if len(world.candidates) >= self._MAX_CANDIDATES_PER_WORLD:
                    break
                origin = CandidateOrigin(tension["origin"])
                candidate = self._synthesize_candidate(
                    world_id=world.world_id,
                    tension=tension,
                    origin=origin,
                )
                world.candidates[candidate.candidate_id] = candidate
                world.total_enumerated += 1
                self._stats["total_enumerated"] += 1
                enumerated += 1
                # Mark the source tension as processed so it does not re-seed.
                if tension["tension_id"] in world.tensions:
                    world.tensions[tension["tension_id"]]["processed"] = True
            # Residual candidates from previously closed horizons occasionally re-emerge.
            if len(world.candidates) < self._MAX_CANDIDATES_PER_WORLD and random.random() < 0.2:
                residual = self._synthesize_candidate(
                    world_id=world.world_id,
                    tension={
                        "tension_id": f"residual_{self._cycle_count}_{world.world_id}",
                        "origin": CandidateOrigin.RESIDUAL.value,
                        "description": "a horizon the world left half-formed",
                        "magnitude": 0.25,
                        "processed": True,
                        "introduced_at": time.time(),
                    },
                    origin=CandidateOrigin.RESIDUAL,
                )
                world.candidates[residual.candidate_id] = residual
                world.total_enumerated += 1
                self._stats["total_enumerated"] += 1
                enumerated += 1
        self._record_event("phase_enumerate", {"enumerated": enumerated})
        return {"enumerated": enumerated}

    def _phase_probe(self) -> Dict[str, Any]:
        """Probe phase: score each candidate's consistency against the world's constraints."""
        probed = 0
        for world in self._worlds.values():
            if not world.constraints:
                # With no constraints on record, all candidates stay unknown.
                continue
            for candidate in world.candidates.values():
                if candidate.state in (HorizonState.OPEN, HorizonState.CLOSED):
                    continue
                candidate.state = HorizonState.PROBING
                score, verdict = self._probe_consistency(world, candidate)
                candidate.consistency_score = score
                candidate.verdict = verdict
                candidate.probe_depth += 1
                probed += 1
                world.total_probed += 1
                self._stats["total_probed"] += 1
        self._record_event("phase_probe", {"probed": probed})
        return {"probed": probed}

    def _phase_stabilize(self) -> Dict[str, Any]:
        """Stabilize phase: consistent candidates firm up; unstable ones weaken."""
        stabilized = 0
        weakened = 0
        for world in self._worlds.values():
            for candidate in world.candidates.values():
                if candidate.state in (HorizonState.OPEN, HorizonState.CLOSED):
                    continue
                # Stability climbs toward consistency, falls away from it.
                if candidate.verdict == ConsistencyVerdict.CONSISTENT:
                    candidate.stability = min(
                        1.0, candidate.stability + candidate.consistency_score * 0.3
                    )
                    if candidate.probe_depth >= self._PROBE_DEPTH:
                        candidate.state = HorizonState.STABLE
                        stabilized += 1
                        world.total_stabilized += 1
                        self._stats["total_stabilized"] += 1
                elif candidate.verdict == ConsistencyVerdict.PARTIAL:
                    candidate.stability = min(
                        1.0, candidate.stability + candidate.consistency_score * 0.15
                    )
                else:
                    candidate.stability = max(
                        0.0, candidate.stability - 0.2
                    )
                    weakened += 1
                candidate.stale_cycles += 1
        self._record_event("phase_stabilize", {
            "stabilized": stabilized,
            "weakened": weakened,
        })
        return {"stabilized": stabilized, "weakened": weakened}

    def _phase_open(self) -> Dict[str, Any]:
        """Open phase: sufficiently stable candidates open as accessible modal horizons."""
        opened = 0
        for world in self._worlds.values():
            if len(world.open_horizons) >= self._MAX_OPEN_HORIZONS_PER_WORLD:
                continue
            for candidate in list(world.candidates.values()):
                if candidate.state != HorizonState.STABLE:
                    continue
                if candidate.stability < self._OPEN_THRESHOLD:
                    continue
                if len(world.open_horizons) >= self._MAX_OPEN_HORIZONS_PER_WORLD:
                    break
                candidate.state = HorizonState.OPEN
                candidate.opened_at = time.time()
                candidate.stale_cycles = 0
                candidate.accessibility = self._derive_accessibility(candidate)
                world.open_horizons[candidate.candidate_id] = candidate
                world.accessibility[candidate.candidate_id] = candidate.accessibility
                world.total_opened += 1
                self._stats["total_opened"] += 1
                opened += 1
        self._record_event("phase_open", {"opened": opened})
        return {"opened": opened}

    def _phase_close(self) -> Dict[str, Any]:
        """Close phase: inconsistent or stale horizons are closed."""
        closed = 0
        for world in self._worlds.values():
            for candidate in list(world.candidates.values()):
                if candidate.state == HorizonState.CLOSED:
                    continue
                should_close = False
                reason = ""
                # Inconsistent candidates are closed outright.
                if (candidate.verdict == ConsistencyVerdict.INCONSISTENT
                        and candidate.stability <= 0.05):
                    should_close = True
                    reason = "inconsistent"
                # Open horizons that have gone stale are closed to keep the fan crisp.
                elif (candidate.state == HorizonState.OPEN
                      and candidate.stale_cycles >= self._CLOSE_STALENESS_CYCLES):
                    should_close = True
                    reason = "stale"
                # Unopened candidates that never reached stability are pruned.
                elif (candidate.state in (HorizonState.PROBING, HorizonState.STABLE)
                      and candidate.stale_cycles >= self._CLOSE_STALENESS_CYCLES + 2
                      and candidate.stability < self._STABILIZE_THRESHOLD):
                    should_close = True
                    reason = "unstable"
                if not should_close:
                    continue
                candidate.state = HorizonState.CLOSED
                candidate.closed_at = time.time()
                candidate.close_reason = reason
                world.open_horizons.pop(candidate.candidate_id, None)
                world.accessibility.pop(candidate.candidate_id, None)
                world.total_closed += 1
                self._stats["total_closed"] += 1
                closed += 1
        self._record_event("phase_close", {"closed": closed})
        return {"closed": closed}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _synthesize_candidate(self, world_id: str, tension: Dict[str, Any],
                              origin: CandidateOrigin) -> PossibleWorldCandidate:
        """Synthesize a fresh candidate possible-world from a tension point."""
        magnitude = float(tension.get("magnitude", 0.5))
        # The candidate's opening consistency seed is pulled up by the tension's
        # magnitude - sharper tensions tend to grow more coherent alternatives.
        seed = 0.3 + magnitude * 0.3 + random.uniform(-0.05, 0.05)
        seed = max(0.0, min(1.0, seed))
        candidate_id = (
            f"pwc_{world_id}_{tension['tension_id']}_{self._cycle_count}_"
            f"{random.randint(1000, 9999)}"
        )
        return PossibleWorldCandidate(
            candidate_id=candidate_id,
            origin=origin,
            source_tension=tension["tension_id"],
            description=tension.get("description", ""),
            consistency_score=seed,
            stability=seed * 0.5,
            verdict=ConsistencyVerdict.UNKNOWN,
            state=HorizonState.CANDIDATE,
            accessibility=HorizonAccessibility.CONDITIONAL,
        )

    def _probe_consistency(self, world: ModalHorizonWorld,
                           candidate: PossibleWorldCandidate) -> tuple:
        """Probe a candidate against the world's constraints and return (score, verdict)."""
        if not world.constraints:
            return candidate.consistency_score, ConsistencyVerdict.UNKNOWN
        weighted_total = 0.0
        satisfied = 0.0
        for constraint in world.constraints.values():
            # Each constraint casts a noisy vote on whether the candidate
            # coheres with it; the constraint's weight decides how much the
            # vote counts toward the overall consistency score.
            probe_noise = random.uniform(-0.1, 0.1)
            vote = candidate.consistency_score + probe_noise
            weighted_total += constraint.weight
            if vote >= self._STABILIZE_THRESHOLD:
                satisfied += constraint.weight
        score = satisfied / weighted_total if weighted_total > 0 else 0.0
        score = max(0.0, min(1.0, score))
        return score, self._classify_verdict(score, weighted_total)

    def _classify_verdict(self, score: float, total_weight: float) -> ConsistencyVerdict:
        """Classify a candidate's consistency score into a verdict."""
        if total_weight <= 0:
            return ConsistencyVerdict.UNKNOWN
        if score >= 0.75:
            return ConsistencyVerdict.CONSISTENT
        if score >= self._STABILIZE_THRESHOLD:
            return ConsistencyVerdict.PARTIAL
        return ConsistencyVerdict.INCONSISTENT

    def _derive_accessibility(self, candidate: PossibleWorldCandidate) -> HorizonAccessibility:
        """Derive how reachable an opened horizon is from the actual world."""
        # Higher stability and consistency open a direct path; middling values
        # leave the horizon reachable only under conditions; low values close it off.
        reach = (candidate.stability + candidate.consistency_score) / 2.0
        if reach >= self._OPEN_THRESHOLD + 0.15:
            return HorizonAccessibility.REACHABLE
        if reach >= self._OPEN_THRESHOLD - 0.1:
            return HorizonAccessibility.CONDITIONAL
        return HorizonAccessibility.UNREACHABLE

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "worlds": len(self._worlds),
                "stats": dict(self._stats),
            }

    def get_world_state(self, world_id: str) -> Dict[str, Any]:
        with self._global_lock:
            world = self._worlds.get(world_id)
            if world is None:
                return {"error": f"World not found: {world_id}"}
            return {
                "world_id": world_id,
                "tensions_count": len(world.tensions),
                "constraints_count": len(world.constraints),
                "candidates_count": len(world.candidates),
                "open_horizons_count": len(world.open_horizons),
                "total_enumerated": world.total_enumerated,
                "total_probed": world.total_probed,
                "total_stabilized": world.total_stabilized,
                "total_opened": world.total_opened,
                "total_closed": world.total_closed,
            }

    def get_candidates(self, world_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            world = self._worlds.get(world_id)
            if world is None:
                return {"error": f"World not found: {world_id}"}
            candidates = sorted(
                world.candidates.values(),
                key=lambda c: c.created_at,
                reverse=True,
            )[:limit]
            return {
                "world_id": world_id,
                "candidates": [
                    {
                        "candidate_id": c.candidate_id,
                        "origin": c.origin.value,
                        "source_tension": c.source_tension,
                        "description": c.description,
                        "consistency_score": c.consistency_score,
                        "stability": c.stability,
                        "verdict": c.verdict.value,
                        "state": c.state.value,
                        "accessibility": c.accessibility.value,
                        "probe_depth": c.probe_depth,
                        "stale_cycles": c.stale_cycles,
                    }
                    for c in candidates
                ],
            }

    def get_open_horizons(self, world_id: str, limit: int = 12) -> Dict[str, Any]:
        with self._global_lock:
            world = self._worlds.get(world_id)
            if world is None:
                return {"error": f"World not found: {world_id}"}
            horizons = sorted(
                world.open_horizons.values(),
                key=lambda c: c.opened_at or c.created_at,
                reverse=True,
            )[:limit]
            return {
                "world_id": world_id,
                "horizons": [
                    {
                        "candidate_id": c.candidate_id,
                        "origin": c.origin.value,
                        "source_tension": c.source_tension,
                        "description": c.description,
                        "consistency_score": c.consistency_score,
                        "stability": c.stability,
                        "accessibility": c.accessibility.value,
                        "opened_at": c.opened_at,
                        "stale_cycles": c.stale_cycles,
                    }
                    for c in horizons
                ],
            }

    def get_constraints(self, world_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            world = self._worlds.get(world_id)
            if world is None:
                return {"error": f"World not found: {world_id}"}
            constraints = sorted(
                world.constraints.values(),
                key=lambda c: c.created_at,
                reverse=True,
            )[:limit]
            return {
                "world_id": world_id,
                "constraints": [
                    {
                        "constraint_id": c.constraint_id,
                        "label": c.label,
                        "weight": c.weight,
                        "created_at": c.created_at,
                    }
                    for c in constraints
                ],
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Simulation & Reset
    # -------------------------------------------------------------------------

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic worlds and run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_worlds()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_worlds(self) -> None:
        """Seed a small synthetic set of worlds with constraints and tensions."""
        seed_worlds = ["sim_alpha", "sim_beta", "sim_gamma"]
        for world_id in seed_worlds:
            if world_id not in self._worlds:
                self.register_world(world_id)
        # Constraints per world.
        seed_constraints = [
            ("sim_alpha", "law_identity", "identities persist across branches", 0.8),
            ("sim_alpha", "law_causality", "effects follow their causes", 0.7),
            ("sim_beta", "law_economy", "value cannot appear from nothing", 0.6),
            ("sim_beta", "law_trust", "alliances decay under betrayal", 0.5),
            ("sim_gamma", "law_geometry", "regions keep their adjacency", 0.7),
        ]
        for world_id, cid, label, weight in seed_constraints:
            world = self._worlds.get(world_id)
            if world is None or cid in world.constraints:
                continue
            self.add_constraint(world_id, cid, label, weight)
        # Tensions per world.
        seed_tensions = [
            ("sim_alpha", "sim_t1", CandidateOrigin.TENSION,
             "a faction questions its leader", 0.7),
            ("sim_alpha", "sim_t2", CandidateOrigin.OPPORTUNITY,
             "a new trade route is possible", 0.5),
            ("sim_beta", "sim_t3", CandidateOrigin.TENSION,
             "a debt cannot be paid", 0.6),
            ("sim_beta", "sim_t4", CandidateOrigin.DIVERGENCE,
             "two heirs claim the same seat", 0.8),
            ("sim_gamma", "sim_t5", CandidateOrigin.TENSION,
             "a region drifts toward autonomy", 0.4),
        ]
        for world_id, tid, origin, desc, mag in seed_tensions:
            world = self._worlds.get(world_id)
            if world is None or tid in world.tensions:
                continue
            self.introduce_tension(world_id, tid, origin, desc, mag)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._worlds.clear()
            self._events_log.clear()
            self._phase = ModalHorizonPhase.ENUMERATE
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
