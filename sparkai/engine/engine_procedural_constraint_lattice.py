"""
SparkLabs Engine - Procedural Constraint Lattice"""

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

class LatticePhase(Enum):
    """Phases of the procedural constraint lattice cycle."""
    ASSERT = "assert"        # accept a constraint into the lattice
    WIRE = "wire"            # connect nodes with edges, detect immediate conflicts
    EVALUATE = "evaluate"    # compute satisfiable placements per pending request
    RELAX = "relax"          # offer relaxation candidates for unsatisfiable requests
    COMMIT = "commit"        # record accepted placements as new facts


class ConstraintType(Enum):
    """The kind of rule a lattice node expresses."""
    CARDINALITY = "cardinality"  # exactly N of a target in a region
    DISTANCE = "distance"        # min or max spacing between placements
    EXCLUSION = "exclusion"      # two targets cannot coexist
    PRECEDENCE = "precedence"    # A must be satisfied before B
    BOUND = "bound"              # a placement value must fall in a range
    COVERAGE = "coverage"        # a region must be covered by a target


class ConstraintState(Enum):
    """State of an individual lattice node."""
    ASSERTED = "asserted"      # accepted into the lattice, not yet wired
    WIRED = "wired"            # edges resolved, awaiting activation
    ACTIVE = "active"          # currently constraining generation
    CONFLICTED = "conflicted"  # in direct conflict with another node
    RELAXED = "relaxed"        # softened to unblock a request
    VIOLATED = "violated"      # a committed fact broke this constraint
    RETIRED = "retired"        # no longer in effect


class ConflictKind(Enum):
    """The kind of conflict the lattice detects."""
    DIRECT = "direct"              # two rules contradict each other outright
    PRECEDENCE_CYCLE = "precedence_cycle"  # precedence edges form a cycle
    OVER_CONSTRAINED = "over_constrained"  # no placement can satisfy the lattice
    PARTIAL = "partial"            # some placements blocked, others remain


class LatticeState(Enum):
    """Overall state of the lattice engine."""
    IDLE = "idle"            # nothing in flight
    WIRING = "wiring"        # edges being resolved
    EVALUATING = "evaluating"  # requests being evaluated
    RELAXING = "relaxing"    # relaxation candidates being prepared
    COMMITTED = "committed"  # a cycle has committed its facts
    DEADLOCKED = "deadlocked"  # no request can be satisfied without relaxation


class LatticeVitality(Enum):
    """The overall vitality of the constraint lattice."""
    EMPTY = "empty"          # no constraints asserted yet
    COHERENT = "coherent"    # constraints align, requests resolve cleanly
    TENSE = "tense"          # some conflicts detected, still resolvable
    CONFLICTED = "conflicted"  # multiple unresolved conflicts
    DEADLOCKED = "deadlocked"  # lattice cannot make progress


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class LatticeNode:
    """A single constraint held as a node in the lattice."""
    node_id: str
    constraint_type: ConstraintType
    spec: Dict[str, Any] = field(default_factory=dict)
    state: ConstraintState = ConstraintState.ASSERTED
    region: str = ""
    note: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class LatticeEdge:
    """An edge between two lattice nodes."""
    from_id: str
    to_id: str
    edge_kind: str = "precedence"   # "precedence" or "exclusion"
    note: str = ""


@dataclass
class GenerationRequest:
    """A generator asking the lattice what it can place."""
    request_id: str
    region: str
    candidate_placements: List[str] = field(default_factory=list)
    satisfiable: List[str] = field(default_factory=list)
    note: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class RelaxationCandidate:
    """A proposed softening of constraints that would unblock a request."""
    request_id: str
    node_ids_to_relax: List[str] = field(default_factory=list)
    unblocks_count: int = 0
    cost: float = 0.0
    note: str = ""


@dataclass
class LatticeCycleResult:
    """Holder for a single lattice cycle's outcome."""
    cycle_count: int
    phase: str
    phase_outputs: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Lattice
# =============================================================================

class EngineProceduralConstraintLattice:
    """
    Thread-safe singleton orchestrating a procedural constraint lattice.

    Usage:
        lattice = EngineProceduralConstraintLattice.get_instance()
        lattice.assert_constraint("n1", constraint_type="cardinality",
                                  spec={"target": "landmark", "count": 1},
                                  region="village", note="one landmark")
        lattice.submit_request("r1", region="village",
                               candidate_placements=["landmark_A", "landmark_B"])
        result = lattice.cycle()
        state = lattice.get_status()
    """

    _instance: Optional["EngineProceduralConstraintLattice"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Tuning constants and hard caps.
    _MAX_NODES = 128
    _MAX_EDGES = 256
    _MAX_REQUESTS = 200
    _MAX_FACTS = 500
    _MAX_EVENTS = 200
    _RELAX_MAX_CANDIDATES = 5
    _EVAL_MAX_PLACEMENTS = 64

    def __init__(self) -> None:
        self._nodes: Dict[str, LatticeNode] = {}
        self._edges: List[LatticeEdge] = []
        self._requests: Deque[GenerationRequest] = deque()
        self._facts: Dict[str, Dict[str, Any]] = {}
        self._relaxation_candidates: List[RelaxationCandidate] = []
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._cycle_count: int = 0
        self._current_phase: LatticePhase = LatticePhase.ASSERT
        self._state: LatticeState = LatticeState.IDLE
        self._uptime_started_at: float = time.time()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineProceduralConstraintLattice":
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
            "constraints_asserted": 0,
            "edges_wired": 0,
            "requests_evaluated": 0,
            "conflicts_detected": 0,
            "relaxations_offered": 0,
            "facts_committed": 0,
            "mean_satisfiable_ratio": 0.0,
            "last_cycle_at": 0.0,
            "uptime_started_at": self._uptime_started_at,
            "vitality": LatticeVitality.EMPTY.value,
        }

    def _update_stats(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if key in self._stats:
                if isinstance(value, (int, float)) and isinstance(
                    self._stats[key], (int, float)
                ) and key not in ("mean_satisfiable_ratio", "last_cycle_at",
                                  "uptime_started_at", "vitality"):
                    self._stats[key] = self._stats[key] + value
                else:
                    self._stats[key] = value
            else:
                self._stats[key] = value

    def _derive_vitality(self) -> LatticeVitality:
        if not self._nodes:
            return LatticeVitality.EMPTY
        conflicted = sum(
            1 for n in self._nodes.values()
            if n.state == ConstraintState.CONFLICTED
        )
        relaxed = sum(
            1 for n in self._nodes.values()
            if n.state == ConstraintState.RELAXED
        )
        if self._state == LatticeState.DEADLOCKED:
            return LatticeVitality.DEADLOCKED
        if conflicted >= 2:
            return LatticeVitality.CONFLICTED
        if conflicted >= 1 or relaxed >= 1:
            return LatticeVitality.TENSE
        return LatticeVitality.COHERENT

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Public Intake
    # -------------------------------------------------------------------------

    def assert_constraint(self, node_id: str, constraint_type: str,
                          spec: Optional[Dict[str, Any]] = None,
                          region: str = "", note: str = "") -> Dict[str, Any]:
        """Accept a new constraint assertion into the lattice."""
        with self._global_lock:
            if node_id in self._nodes:
                return {"error": f"Constraint already exists: {node_id}"}
            if len(self._nodes) >= self._MAX_NODES:
                # Drop the oldest retired node to make room.
                retired = [nid for nid, n in self._nodes.items()
                           if n.state == ConstraintState.RETIRED]
                if retired:
                    self._nodes.pop(retired[0], None)
                else:
                    return {"error": "Lattice node cap reached"}
            try:
                ctype = ConstraintType(constraint_type)
            except ValueError:
                return {"error": f"Invalid constraint_type: {constraint_type}"}
            node = LatticeNode(
                node_id=node_id,
                constraint_type=ctype,
                spec=dict(spec or {}),
                state=ConstraintState.ASSERTED,
                region=region,
                note=note,
            )
            self._nodes[node_id] = node
            self._update_stats(constraints_asserted=1)
            self._record_event("constraint_asserted", {
                "node_id": node_id,
                "constraint_type": ctype.value,
                "region": region,
            })
            return {
                "node_id": node_id,
                "constraint_type": ctype.value,
                "state": node.state.value,
                "region": region,
            }

    def submit_request(self, request_id: str, region: str,
                       candidate_placements: List[str],
                       note: str = "") -> Dict[str, Any]:
        """Submit a generation request for the lattice to evaluate."""
        with self._global_lock:
            # Reject duplicate request ids in flight.
            if any(r.request_id == request_id for r in self._requests):
                return {"error": f"Request already in flight: {request_id}"}
            if len(self._requests) >= self._MAX_REQUESTS:
                # Drop the oldest request to make room.
                self._requests.popleft()
            placements = list(candidate_placements)[: self._EVAL_MAX_PLACEMENTS]
            req = GenerationRequest(
                request_id=request_id,
                region=region,
                candidate_placements=placements,
                satisfiable=[],
                note=note,
            )
            self._requests.append(req)
            self._record_event("request_submitted", {
                "request_id": request_id,
                "region": region,
                "candidate_count": len(placements),
            })
            return {
                "request_id": request_id,
                "region": region,
                "candidate_count": len(placements),
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single lattice cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            self._cycle_count += 1
            phase_outputs: List[Dict[str, Any]] = []

            self._current_phase = LatticePhase.ASSERT
            self._state = LatticeState.WIRING
            phase_outputs.append(self._phase_assert())

            self._current_phase = LatticePhase.WIRE
            phase_outputs.append(self._phase_wire())

            self._current_phase = LatticePhase.EVALUATE
            self._state = LatticeState.EVALUATING
            phase_outputs.append(self._phase_evaluate())

            self._current_phase = LatticePhase.RELAX
            self._state = LatticeState.RELAXING
            phase_outputs.append(self._phase_relax())

            self._current_phase = LatticePhase.COMMIT
            self._state = LatticeState.COMMITTED
            phase_outputs.append(self._phase_commit())

            elapsed_ms = (time.time() - t0) * 1000.0
            self._update_stats(
                cycles_completed=1,
                last_cycle_at=time.time(),
            )
            self._stats["vitality"] = self._derive_vitality().value
            self._stats["last_cycle_time_ms"] = elapsed_ms
            self._stats["nodes"] = len(self._nodes)
            self._stats["edges"] = len(self._edges)
            self._stats["pending_requests"] = len(self._requests)
            self._stats["facts"] = len(self._facts)
            self._stats["lattice_state"] = self._state.value
            self._stats["current_phase"] = self._current_phase.value

            return {
                "cycle_count": self._cycle_count,
                "phase": self._current_phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_assert(self) -> Dict[str, Any]:
        """Assert phase: validate freshly asserted nodes against existing ones."""
        validated = 0
        direct_conflicts = 0
        # Move asserted nodes toward wired state, flagging direct contradictions.
        for node in self._nodes.values():
            if node.state != ConstraintState.ASSERTED:
                continue
            contradiction = self._find_direct_contradiction(node)
            if contradiction is not None:
                node.state = ConstraintState.CONFLICTED
                direct_conflicts += 1
                self._record_event("conflict_direct", {
                    "node_id": node.node_id,
                    "against": contradiction,
                    "region": node.region,
                })
            else:
                node.state = ConstraintState.WIRED
                validated += 1
        self._update_stats(conflicts_detected=direct_conflicts)
        self._record_event("phase_assert", {
            "validated": validated,
            "direct_conflicts": direct_conflicts,
        })
        return {
            "phase": LatticePhase.ASSERT.value,
            "validated": validated,
            "direct_conflicts": direct_conflicts,
        }

    def _phase_wire(self) -> Dict[str, Any]:
        """Wire phase: connect nodes with precedence and exclusion edges."""
        edges_wired = 0
        cycles_detected = 0
        new_edges: List[LatticeEdge] = []
        active_count = 0

        for node in self._nodes.values():
            if node.state != ConstraintState.WIRED:
                continue
            # Precedence: a BOUND or COVERAGE node precedes a CARDINALITY node
            # on the same region (you must know the bounds before you count).
            for other in self._nodes.values():
                if other.node_id == node.node_id:
                    continue
                if other.state in (ConstraintState.RETIRED,
                                   ConstraintState.VIOLATED):
                    continue
                if self._should_precede(other, node):
                    if not self._edge_exists(other.node_id, node.node_id,
                                             "precedence"):
                        new_edges.append(LatticeEdge(
                            from_id=other.node_id,
                            to_id=node.node_id,
                            edge_kind="precedence",
                            note="bound/coverage precedes cardinality",
                        ))
                        edges_wired += 1
                if self._should_exclude(other, node):
                    if not self._edge_exists(other.node_id, node.node_id,
                                             "exclusion"):
                        new_edges.append(LatticeEdge(
                            from_id=other.node_id,
                            to_id=node.node_id,
                            edge_kind="exclusion",
                            note="mutually exclusive targets in region",
                        ))
                        edges_wired += 1

        # Cap edges to avoid runaway growth.
        for edge in new_edges:
            if len(self._edges) >= self._MAX_EDGES:
                break
            self._edges.append(edge)

        cycles_detected = self._detect_precedence_cycles()
        # Promote wired nodes to active unless they are in a precedence cycle.
        cycle_nodes = self._nodes_in_precedence_cycles()
        for node in self._nodes.values():
            if node.state == ConstraintState.WIRED:
                if node.node_id in cycle_nodes:
                    node.state = ConstraintState.CONFLICTED
                else:
                    node.state = ConstraintState.ACTIVE
                    active_count += 1

        self._update_stats(edges_wired=edges_wired,
                           conflicts_detected=cycles_detected)
        self._record_event("phase_wire", {
            "edges_wired": edges_wired,
            "cycles_detected": cycles_detected,
            "active": active_count,
        })
        return {
            "phase": LatticePhase.WIRE.value,
            "edges_wired": edges_wired,
            "cycles_detected": cycles_detected,
            "active": active_count,
        }

    def _phase_evaluate(self) -> Dict[str, Any]:
        """Evaluate phase: compute satisfiable placements per pending request."""
        evaluated = 0
        ratios: List[float] = []
        blocked_requests = 0
        for req in self._requests:
            satisfiable = self._compute_satisfiable(req)
            req.satisfiable = satisfiable
            ratio = (
                len(satisfiable) / len(req.candidate_placements)
                if req.candidate_placements else 0.0
            )
            ratios.append(ratio)
            evaluated += 1
            if not satisfiable:
                blocked_requests += 1
            self._record_event("request_evaluated", {
                "request_id": req.request_id,
                "region": req.region,
                "candidates": len(req.candidate_placements),
                "satisfiable": len(satisfiable),
                "ratio": ratio,
            })
        mean_ratio = sum(ratios) / len(ratios) if ratios else 0.0
        self._update_stats(
            requests_evaluated=evaluated,
            mean_satisfiable_ratio=mean_ratio,
        )
        if blocked_requests > 0 and not any(
            r.satisfiable for r in self._requests
        ):
            self._state = LatticeState.DEADLOCKED
        self._record_event("phase_evaluate", {
            "evaluated": evaluated,
            "mean_satisfiable_ratio": mean_ratio,
            "blocked_requests": blocked_requests,
        })
        return {
            "phase": LatticePhase.EVALUATE.value,
            "evaluated": evaluated,
            "mean_satisfiable_ratio": mean_ratio,
            "blocked_requests": blocked_requests,
        }

    def _phase_relax(self) -> Dict[str, Any]:
        """Relax phase: offer relaxation candidates for blocked requests."""
        candidates: List[RelaxationCandidate] = []
        for req in self._requests:
            if req.satisfiable:
                continue
            cand = self._build_relaxation_candidates(req)
            candidates.extend(cand)
        # Keep only the cheapest few candidates overall.
        candidates.sort(key=lambda c: (c.cost, -c.unblocks_count))
        candidates = candidates[: self._RELAX_MAX_CANDIDATES]
        self._relaxation_candidates = candidates
        self._update_stats(relaxations_offered=len(candidates))
        self._record_event("phase_relax", {
            "relaxations_offered": len(candidates),
        })
        return {
            "phase": LatticePhase.RELAX.value,
            "relaxations_offered": len(candidates),
            "candidates": [
                {
                    "request_id": c.request_id,
                    "node_ids_to_relax": list(c.node_ids_to_relax),
                    "unblocks_count": c.unblocks_count,
                    "cost": c.cost,
                    "note": c.note,
                }
                for c in candidates
            ],
        }

    def _phase_commit(self) -> Dict[str, Any]:
        """Commit phase: record satisfiable placements as new facts."""
        facts_committed = 0
        committed_requests: List[GenerationRequest] = []
        # For each request that has satisfiable placements, commit the first
        # one as a new fact that further constrains the lattice.
        for req in self._requests:
            if not req.satisfiable:
                continue
            placement = req.satisfiable[0]
            fact_id = f"fact_{req.request_id}_{self._cycle_count}"
            if len(self._facts) >= self._MAX_FACTS:
                # Drop the oldest fact to make room.
                oldest = next(iter(self._facts), None)
                if oldest is not None:
                    self._facts.pop(oldest, None)
            self._facts[fact_id] = {
                "fact_id": fact_id,
                "request_id": req.request_id,
                "region": req.region,
                "placement": placement,
                "committed_at": time.time(),
            }
            facts_committed += 1
            committed_requests.append(req)
            self._record_event("fact_committed", {
                "fact_id": fact_id,
                "request_id": req.request_id,
                "region": req.region,
                "placement": placement,
            })
            # Check whether the new fact violates any active constraints.
            self._mark_violations(placement, req.region)

        # Remove committed requests from the queue.
        for req in committed_requests:
            try:
                self._requests.remove(req)
            except ValueError:
                pass

        self._update_stats(facts_committed=facts_committed)
        self._record_event("phase_commit", {
            "facts_committed": facts_committed,
            "remaining_requests": len(self._requests),
        })
        return {
            "phase": LatticePhase.COMMIT.value,
            "facts_committed": facts_committed,
            "remaining_requests": len(self._requests),
            "satisfiable_surface": self._satisfiable_surface(),
        }

    # -------------------------------------------------------------------------
    # Internal Helpers - Assertion
    # -------------------------------------------------------------------------

    def _find_direct_contradiction(self, node: LatticeNode) -> Optional[str]:
        """Find an existing node that directly contradicts the given one."""
        for other in self._nodes.values():
            if other.node_id == node.node_id:
                continue
            if other.state in (ConstraintState.RETIRED,):
                continue
            # Two cardinality constraints on the same target in the same region
            # with different counts directly contradict each other.
            if (node.constraint_type == ConstraintType.CARDINALITY
                    and other.constraint_type == ConstraintType.CARDINALITY
                    and node.region == other.region
                    and node.spec.get("target") == other.spec.get("target")
                    and node.spec.get("count") != other.spec.get("count")):
                return other.node_id
            # Two exclusion constraints on the same pair in the same region.
            if (node.constraint_type == ConstraintType.EXCLUSION
                    and other.constraint_type == ConstraintType.EXCLUSION
                    and node.region == other.region
                    and self._same_pair(node.spec, other.spec)):
                return other.node_id
        return None

    @staticmethod
    def _same_pair(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        """Whether two exclusion specs describe the same target pair."""
        a_pair = {a.get("a"), a.get("b")}
        b_pair = {b.get("a"), b.get("b")}
        return a_pair == b_pair and None not in a_pair

    # -------------------------------------------------------------------------
    # Internal Helpers - Wiring
    # -------------------------------------------------------------------------

    @staticmethod
    def _should_precede(a: LatticeNode, b: LatticeNode) -> bool:
        """Whether node a should precede node b in the lattice."""
        if a.region and b.region and a.region != b.region:
            return False
        # BOUND and COVERAGE precede CARDINALITY on the same target.
        if a.constraint_type in (ConstraintType.BOUND,
                                 ConstraintType.COVERAGE):
            if b.constraint_type == ConstraintType.CARDINALITY:
                return a.spec.get("target") == b.spec.get("target")
        return False

    @staticmethod
    def _should_exclude(a: LatticeNode, b: LatticeNode) -> bool:
        """Whether two nodes are mutually exclusive in the same region."""
        if a.region and b.region and a.region != b.region:
            return False
        if a.constraint_type != ConstraintType.EXCLUSION:
            return False
        if b.constraint_type != ConstraintType.EXCLUSION:
            return False
        # Only flag exclusions on overlapping but not identical pairs.
        if EngineProceduralConstraintLattice._same_pair(a.spec, b.spec):
            return False
        a_pair = {a.spec.get("a"), a.spec.get("b")}
        b_pair = {b.spec.get("a"), b.spec.get("b")}
        return bool(a_pair & b_pair) and a_pair != b_pair

    def _edge_exists(self, from_id: str, to_id: str, edge_kind: str) -> bool:
        for edge in self._edges:
            if (edge.from_id == from_id and edge.to_id == to_id
                    and edge.edge_kind == edge_kind):
                return True
        return False

    def _detect_precedence_cycles(self) -> int:
        """Count strongly-connected components of size > 1 in precedence graph."""
        adj: Dict[str, List[str]] = {}
        for edge in self._edges:
            if edge.edge_kind != "precedence":
                continue
            adj.setdefault(edge.from_id, []).append(edge.to_id)
        visited: set = set()
        cycles = 0
        for start in list(adj.keys()):
            if start in visited:
                continue
            stack = [(start, [start])]
            while stack:
                node, path = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                for nxt in adj.get(node, []):
                    if nxt in path:
                        cycles += 1
                        break
                    stack.append((nxt, path + [nxt]))
        return cycles

    def _nodes_in_precedence_cycles(self) -> set:
        """Return the set of node ids that participate in a precedence cycle."""
        adj: Dict[str, List[str]] = {}
        for edge in self._edges:
            if edge.edge_kind != "precedence":
                continue
            adj.setdefault(edge.from_id, []).append(edge.to_id)
        in_cycle: set = set()
        for start in list(adj.keys()):
            stack = [(start, [start])]
            while stack:
                node, path = stack.pop()
                for nxt in adj.get(node, []):
                    if nxt in path:
                        # All nodes from nxt onward in path are in the cycle.
                        idx = path.index(nxt)
                        for n in path[idx:]:
                            in_cycle.add(n)
                        in_cycle.add(nxt)
                        break
                    stack.append((nxt, path + [nxt]))
        return in_cycle

    # -------------------------------------------------------------------------
    # Internal Helpers - Evaluation
    # -------------------------------------------------------------------------

    def _compute_satisfiable(self, req: GenerationRequest) -> List[str]:
        """Compute which candidate placements remain satisfiable."""
        active_nodes = [
            n for n in self._nodes.values()
            if n.state in (ConstraintState.ACTIVE, ConstraintState.RELAXED)
            and (not n.region or n.region == req.region)
        ]
        satisfiable: List[str] = []
        for placement in req.candidate_placements:
            if self._placement_ok(placement, req.region, active_nodes):
                satisfiable.append(placement)
        return satisfiable

    def _placement_ok(self, placement: str, region: str,
                      active_nodes: List[LatticeNode]) -> bool:
        """Check whether a single placement satisfies all active constraints."""
        # Count existing facts for the same placement target in this region.
        region_facts = [
            f for f in self._facts.values()
            if f.get("region") == region
        ]
        for node in active_nodes:
            if node.constraint_type == ConstraintType.CARDINALITY:
                target = node.spec.get("target", "")
                count = int(node.spec.get("count", 0))
                # If the placement matches the cardinality target, count it
                # against the cap; one more would exceed the limit.
                if placement.startswith(target) or placement == target:
                    current = sum(
                        1 for f in region_facts
                        if f.get("placement", "").startswith(target)
                        or f.get("placement", "") == target
                    )
                    if current >= count:
                        return False
            elif node.constraint_type == ConstraintType.EXCLUSION:
                a = node.spec.get("a", "")
                b = node.spec.get("b", "")
                # If the placement matches one side, the other side must not
                # already be present in the region.
                if placement == a or placement.startswith(a):
                    if any(f.get("placement") == b
                           or f.get("placement", "").startswith(b)
                           for f in region_facts):
                        return False
                if placement == b or placement.startswith(b):
                    if any(f.get("placement") == a
                           or f.get("placement", "").startswith(a)
                           for f in region_facts):
                        return False
            elif node.constraint_type == ConstraintType.BOUND:
                # Bound checks a numeric suffix on the placement string.
                target = node.spec.get("target", "")
                low = node.spec.get("min")
                high = node.spec.get("max")
                if placement.startswith(target):
                    suffix = placement[len(target):].strip("_")
                    try:
                        value = float(suffix) if suffix else 0.0
                    except ValueError:
                        value = 0.0
                    if low is not None and value < float(low):
                        return False
                    if high is not None and value > float(high):
                        return False
            elif node.constraint_type == ConstraintType.PRECEDENCE:
                # The placement must not be the "after" target if the "before"
                # target has not yet been placed in the region.
                before = node.spec.get("before", "")
                after = node.spec.get("after", "")
                if placement == after or placement.startswith(after):
                    if not any(f.get("placement") == before
                               or f.get("placement", "").startswith(before)
                               for f in region_facts):
                        return False
            elif node.constraint_type == ConstraintType.COVERAGE:
                # Coverage requires at least one placement of the target in
                # the region; it never blocks a placement, only demands one.
                pass
            elif node.constraint_type == ConstraintType.DISTANCE:
                # Distance is enforced by suffix index difference.
                target = node.spec.get("target", "")
                min_dist = node.spec.get("min", 0)
                if placement.startswith(target):
                    suffix = placement[len(target):].strip("_")
                    try:
                        value = int(suffix) if suffix else 0
                    except ValueError:
                        value = 0
                    for f in region_facts:
                        fp = f.get("placement", "")
                        if not fp.startswith(target):
                            continue
                        fsuffix = fp[len(target):].strip("_")
                        try:
                            fvalue = int(fsuffix) if fsuffix else 0
                        except ValueError:
                            fvalue = 0
                        if abs(value - fvalue) < int(min_dist):
                            return False
        return True

    # -------------------------------------------------------------------------
    # Internal Helpers - Relaxation
    # -------------------------------------------------------------------------

    def _build_relaxation_candidates(
        self, req: GenerationRequest
    ) -> List[RelaxationCandidate]:
        """Build relaxation candidates for a blocked request."""
        candidates: List[RelaxationCandidate] = []
        active_nodes = [
            n for n in self._nodes.values()
            if n.state in (ConstraintState.ACTIVE, ConstraintState.RELAXED)
            and (not n.region or n.region == req.region)
        ]
        # For each active node, compute how many placements it blocks and
        # the cost of relaxing it (loosening the spec by one unit).
        for node in active_nodes:
            unblocked = 0
            for placement in req.candidate_placements:
                without = [n for n in active_nodes if n.node_id != node.node_id]
                if not self._placement_ok(placement, req.region, without):
                    continue
                if not self._placement_ok(placement, req.region, active_nodes):
                    unblocked += 1
            if unblocked <= 0:
                continue
            cost = self._relaxation_cost(node)
            candidates.append(RelaxationCandidate(
                request_id=req.request_id,
                node_ids_to_relax=[node.node_id],
                unblocks_count=unblocked,
                cost=cost,
                note=f"relax {node.constraint_type.value} on "
                     f"{node.spec.get('target', '?')}",
            ))
        # Also consider relaxing pairs of nodes together when single
        # relaxations do not unblock anything.
        if not candidates and len(active_nodes) >= 2:
            for i in range(len(active_nodes)):
                for j in range(i + 1, len(active_nodes)):
                    pair = [active_nodes[i], active_nodes[j]]
                    without = [n for n in active_nodes
                               if n.node_id not in
                               {pair[0].node_id, pair[1].node_id}]
                    unblocked = sum(
                        1 for p in req.candidate_placements
                        if self._placement_ok(p, req.region, without)
                        and not self._placement_ok(p, req.region, active_nodes)
                    )
                    if unblocked > 0:
                        candidates.append(RelaxationCandidate(
                            request_id=req.request_id,
                            node_ids_to_relax=[pair[0].node_id,
                                               pair[1].node_id],
                            unblocks_count=unblocked,
                            cost=self._relaxation_cost(pair[0])
                                 + self._relaxation_cost(pair[1]),
                            note="relax pair to unblock request",
                        ))
        return candidates

    @staticmethod
    def _relaxation_cost(node: LatticeNode) -> float:
        """Estimate the cost of relaxing a single node."""
        # Cardinality and exclusion are expensive to relax; bounds are cheap.
        weights = {
            ConstraintType.CARDINALITY: 0.8,
            ConstraintType.EXCLUSION: 0.7,
            ConstraintType.PRECEDENCE: 0.5,
            ConstraintType.DISTANCE: 0.4,
            ConstraintType.COVERAGE: 0.3,
            ConstraintType.BOUND: 0.2,
        }
        return weights.get(node.constraint_type, 0.5)

    # -------------------------------------------------------------------------
    # Internal Helpers - Commit
    # -------------------------------------------------------------------------

    def _mark_violations(self, placement: str, region: str) -> None:
        """Mark any active nodes that the new fact violates."""
        for node in self._nodes.values():
            if node.state != ConstraintState.ACTIVE:
                continue
            if node.region and node.region != region:
                continue
            if node.constraint_type == ConstraintType.CARDINALITY:
                target = node.spec.get("target", "")
                count = int(node.spec.get("count", 0))
                if placement == target or placement.startswith(target):
                    current = sum(
                        1 for f in self._facts.values()
                        if f.get("region") == region
                        and (f.get("placement") == target
                             or f.get("placement", "").startswith(target))
                    )
                    if current > count:
                        node.state = ConstraintState.VIOLATED
                        self._record_event("constraint_violated", {
                            "node_id": node.node_id,
                            "placement": placement,
                            "region": region,
                        })

    def _satisfiable_surface(self) -> Dict[str, Any]:
        """Summarize the current satisfiable surface across pending requests."""
        surface: List[Dict[str, Any]] = []
        for req in self._requests:
            surface.append({
                "request_id": req.request_id,
                "region": req.region,
                "candidate_count": len(req.candidate_placements),
                "satisfiable_count": len(req.satisfiable),
                "satisfiable": list(req.satisfiable),
            })
        return {
            "pending_requests": len(self._requests),
            "requests": surface,
            "facts": len(self._facts),
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_node(self, node_id: str) -> Dict[str, Any]:
        with self._global_lock:
            node = self._nodes.get(node_id)
            if node is None:
                return {"error": f"Node not found: {node_id}"}
            return {
                "node_id": node.node_id,
                "constraint_type": node.constraint_type.value,
                "spec": dict(node.spec),
                "state": node.state.value,
                "region": node.region,
                "note": node.note,
                "created_at": node.created_at,
                "incoming_edges": [
                    {"from_id": e.from_id, "kind": e.edge_kind}
                    for e in self._edges if e.to_id == node_id
                ],
                "outgoing_edges": [
                    {"to_id": e.to_id, "kind": e.edge_kind}
                    for e in self._edges if e.from_id == node_id
                ],
            }

    def get_lattice(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "constraint_type": n.constraint_type.value,
                        "state": n.state.value,
                        "region": n.region,
                        "spec": dict(n.spec),
                        "note": n.note,
                    }
                    for n in self._nodes.values()
                ],
                "edges": [
                    {
                        "from_id": e.from_id,
                        "to_id": e.to_id,
                        "edge_kind": e.edge_kind,
                        "note": e.note,
                    }
                    for e in self._edges
                ],
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
                "fact_count": len(self._facts),
                "pending_request_count": len(self._requests),
            }

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._current_phase.value,
                "lattice_state": self._state.value,
                "cycle_count": self._cycle_count,
                "nodes": len(self._nodes),
                "edges": len(self._edges),
                "pending_requests": len(self._requests),
                "facts": len(self._facts),
                "vitality": self._derive_vitality().value,
                "stats": dict(self._stats),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic constraints and requests, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_constraints()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_constraints(self) -> None:
        """Seed a small synthetic lattice with varied constraint types."""
        seed_constraints = [
            ("sim_n1", "cardinality",
             {"target": "landmark", "count": 1}, "sim_village",
             "exactly one landmark"),
            ("sim_n2", "cardinality",
             {"target": "settlement", "count": 2}, "sim_village",
             "two settlements"),
            ("sim_n3", "distance",
             {"target": "settlement", "min": 3}, "sim_village",
             "settlements spaced apart"),
            ("sim_n4", "exclusion",
             {"a": "dungeon_fire", "b": "dungeon_ice"}, "sim_village",
             "no two dungeons share a boss theme"),
            ("sim_n5", "bound",
             {"target": "tower", "min": 1, "max": 5}, "sim_village",
             "tower height in range"),
            ("sim_n6", "precedence",
             {"before": "landmark", "after": "dungeon_fire"}, "sim_village",
             "landmark must precede dungeon"),
            ("sim_n7", "coverage",
             {"target": "road"}, "sim_village",
             "region must be covered by roads"),
        ]
        for node_id, ctype, spec, region, note in seed_constraints:
            if node_id not in self._nodes:
                self.assert_constraint(node_id, constraint_type=ctype,
                                       spec=spec, region=region, note=note)
        # Seed a couple of generation requests.
        seed_requests = [
            ("sim_r1", "sim_village",
             ["landmark_A", "landmark_B", "settlement_1", "settlement_5",
              "dungeon_fire", "tower_3"]),
            ("sim_r2", "sim_village",
             ["landmark_C", "settlement_2", "dungeon_ice", "tower_7",
              "road_A"]),
        ]
        for request_id, region, placements in seed_requests:
            if not any(r.request_id == request_id for r in self._requests):
                self.submit_request(request_id, region=region,
                                    candidate_placements=placements)

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._nodes.clear()
            self._edges.clear()
            self._requests.clear()
            self._facts.clear()
            self._relaxation_candidates.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._current_phase = LatticePhase.ASSERT
            self._state = LatticeState.IDLE
            self._uptime_started_at = time.time()
            self._init_stats()
            return {"reset": True}
