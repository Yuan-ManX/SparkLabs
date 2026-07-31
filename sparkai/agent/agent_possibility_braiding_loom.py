"""
SparkLabs Agent - Possibility Braiding Loom

The AgentPossibilityBraidingLoom models how an agent weaves multiple
counterfactual possibility threads into a braided landscape of what
could be. An agent that only tracks one future is brittle; an agent
that holds many futures at once, braided where they cross, can adapt
when reality picks one.

Each possibility thread is an alternative continuation anchored to a
shared ground state. The loom grounds threads in current reality,
diverges them into alternative branches, braids them together where
their outcomes interact, converges the braid toward the most coherent
possibility, and integrates the lesson into the agent's expectational
model - sharpening which futures the agent treats as live.

Architecture:
  GROUND    ->  DIVERGE   ->  BRAID     ->  CONVERGE  ->  INTEGRATE
  (threads   (each thread  (interacting   (the braid   (the converged
   are        branches      threads are    condenses    possibility
   anchored   into          woven where    toward the   folds into
   to the     alternative   they cross)    most         the agent's
   current    continuations)               coherent     expectations)
   reality)                                possibility)

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

class PossibilityPhase(Enum):
    """Phases of the possibility braiding cycle."""
    GROUND = "ground"          # threads are anchored to current reality
    DIVERGE = "diverge"        # each thread branches into alternatives
    BRAID = "braid"            # interacting threads are woven together
    CONVERGE = "converge"      # the braid condenses toward coherence
    INTEGRATE = "integrate"    # the converged thread folds into expectations


class ThreadValence(Enum):
    """The affective charge of a possibility thread."""
    HOPED = "hoped"            # a future the agent wants
    FEARED = "feared"          # a future the agent dreads
    EXPECTED = "expected"      # a future the agent treats as default
    WILDCARD = "wildcard"      # a future the agent treats as unlikely


class BraidRelation(Enum):
    """How two possibility threads relate where they cross."""
    REINFORCING = "reinforcing"  # both threads push the same outcome
    CONFLICTING = "conflicting"  # threads push opposite outcomes
    ORTHOGONAL = "orthogonal"    # threads touch but do not interact
    ENABLING = "enabling"        # one thread makes the other more likely


class ThreadState(Enum):
    """State of an individual possibility thread."""
    PENDING = "pending"        # introduced, not yet grounded
    GROUNDED = "grounded"      # anchored to the current state
    DIVERGED = "diverged"      # branched into alternatives
    BRAIDED = "braided"        # woven with crossing threads
    CONVERGED = "converged"    # condensed toward coherence
    INTEGRATED = "integrated"  # folded into the agent's expectations


class ExpectationalStance(Enum):
    """The overall shape of an agent's expectational model."""
    NARROW = "narrow"          # few live futures, brittle
    PLURAL = "plural"          # many live futures, adaptive
    ANXIOUS = "anxious"        # feared futures dominate
    OPTIMISTIC = "optimistic"  # hoped futures dominate
    PRAGMATIC = "pragmatic"    # expected futures dominate
    UNFORMED = "unformed"      # insufficient braiding yet


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PossibilityThread:
    """A single counterfactual possibility thread."""
    thread_id: str
    label: str
    valence: ThreadValence
    grounding: str = ""                   # the state it is anchored to
    branch_description: str = ""          # the alternative continuation
    plausibility: float = 0.5             # 0.0-1.0, how likely
    coherence: float = 0.0                # 0.0-1.0, how self-consistent
    braid_strength: float = 0.0           # 0.0-1.0, how woven with others
    state: ThreadState = ThreadState.PENDING
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None


@dataclass
class BraidCrossing:
    """A point where two threads cross and are woven together."""
    crossing_id: str
    thread_a_id: str
    thread_b_id: str
    relation: BraidRelation
    note: str = ""
    weight: float = 0.3                   # 0.0-1.0, how strongly they cross


@dataclass
class ExpectationalModel:
    """The agent's accumulated model of which futures are live."""
    total_threads: int = 0
    valence_weights: Dict[ThreadValence, float] = field(default_factory=dict)
    avg_plausibility: float = 0.5
    dominant_valence: ThreadValence = ThreadValence.EXPECTED
    openness: float = 0.5                 # 0.0-1.0, how many futures are live
    signature: str = ""                   # a phrase describing the stance


@dataclass
class PossibilityAgent:
    """Per-agent possibility braiding state."""
    agent_id: str
    threads: Dict[str, PossibilityThread] = field(default_factory=dict)
    crossings: List[BraidCrossing] = field(default_factory=list)
    model: ExpectationalModel = field(default_factory=ExpectationalModel)
    stance: ExpectationalStance = ExpectationalStance.UNFORMED
    braiding_tolerance: float = 0.5       # 0.0-1.0, comfort with ambiguity
    total_grounded: int = 0
    total_diverged: int = 0
    total_braided: int = 0
    total_converged: int = 0
    total_integrated: int = 0


# =============================================================================
# Loom
# =============================================================================

class AgentPossibilityBraidingLoom:
    """
    Thread-safe singleton orchestrating possibility braiding for agents.

    Usage:
        loom = AgentPossibilityBraidingLoom.get_instance()
        loom.register_agent("strategist")
        loom.introduce_thread("strategist", "t1", "Alliance holds",
                              ThreadValence.HOPED, plausibility=0.6)
        loom.introduce_thread("strategist", "t2", "Alliance fractures",
                              ThreadValence.FEARED, plausibility=0.4)
        loom.cycle()
        state = loom.get_agent_state("strategist")
    """

    _instance: Optional["AgentPossibilityBraidingLoom"] = None
    _instance_lock = threading.Lock()

    # Tuning constants
    _DIVERGE_BRANCH_COUNT = 2             # branches per grounded thread
    _BRAID_CROSSING_THRESHOLD = 0.3       # plausibility needed to braid
    _CONVERGE_COHERENCE_GAIN = 0.18       # coherence gained per reinforcing crossing
    _CONVERGE_TENSION_GAIN = 0.12         # coherence lost per conflicting crossing
    _INTEGRATE_STANCE_THRESHOLD = 4       # integrated threads needed to form stance
    _MAX_THREADS_PER_AGENT = 80
    _MAX_CROSSINGS_PER_AGENT = 120
    _MAX_EVENTS = 200

    def __init__(self) -> None:
        self._agents: Dict[str, PossibilityAgent] = {}
        self._phase: PossibilityPhase = PossibilityPhase.GROUND
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentPossibilityBraidingLoom":
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
            "total_agents": 0,
            "total_threads": 0,
            "total_grounded": 0,
            "total_diverged": 0,
            "total_braided": 0,
            "total_converged": 0,
            "total_integrated": 0,
            "formed_stances": 0,
            "avg_plausibility": 0.0,
            "avg_coherence": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        if not self._agents:
            return
        plausibilities: List[float] = []
        coherences: List[float] = []
        for agent in self._agents.values():
            for thread in agent.threads.values():
                if thread.state == ThreadState.INTEGRATED:
                    plausibilities.append(thread.plausibility)
                    coherences.append(thread.coherence)
        n = len(self._agents)
        self._stats["total_agents"] = n
        self._stats["formed_stances"] = sum(
            1 for a in self._agents.values() if a.stance != ExpectationalStance.UNFORMED
        )
        self._stats["avg_plausibility"] = (
            sum(plausibilities) / len(plausibilities) if plausibilities else 0.0
        )
        self._stats["avg_coherence"] = (
            sum(coherences) / len(coherences) if coherences else 0.0
        )

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str,
                       braiding_tolerance: float = 0.5) -> Dict[str, Any]:
        """Register a new agent for possibility braiding."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            agent = PossibilityAgent(
                agent_id=agent_id,
                braiding_tolerance=max(0.0, min(1.0, braiding_tolerance)),
            )
            self._agents[agent_id] = agent
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "stance": agent.stance.value,
                "braiding_tolerance": agent.braiding_tolerance,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.pop(agent_id, None)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            self._record_event("agent_removed", {"agent_id": agent_id})
            return {
                "removed": agent_id,
                "cleared_threads": len(agent.threads),
                "cleared_crossings": len(agent.crossings),
            }

    # -------------------------------------------------------------------------
    # Thread Intake
    # -------------------------------------------------------------------------

    def introduce_thread(self, agent_id: str, thread_id: str, label: str,
                         valence: ThreadValence, plausibility: float = 0.5,
                         grounding: str = "") -> Dict[str, Any]:
        """Introduce a new possibility thread for an agent."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            if thread_id in agent.threads:
                return {"error": f"Thread already exists: {thread_id}"}
            thread = PossibilityThread(
                thread_id=thread_id,
                label=label,
                valence=valence,
                plausibility=max(0.0, min(1.0, plausibility)),
                grounding=grounding,
            )
            agent.threads[thread_id] = thread
            if len(agent.threads) > self._MAX_THREADS_PER_AGENT:
                oldest = min(agent.threads, key=lambda tid: agent.threads[tid].created_at)
                agent.threads.pop(oldest, None)
            self._stats["total_threads"] += 1
            self._record_event("thread_introduced", {
                "agent_id": agent_id,
                "thread_id": thread_id,
                "valence": valence.value,
                "plausibility": thread.plausibility,
            })
            return {
                "agent_id": agent_id,
                "thread_id": thread_id,
                "valence": valence.value,
                "state": thread.state.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single possibility braiding cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = PossibilityPhase.GROUND
            phase_outputs["ground"] = self._phase_ground()
            self._phase = PossibilityPhase.DIVERGE
            phase_outputs["diverge"] = self._phase_diverge()
            self._phase = PossibilityPhase.BRAID
            phase_outputs["braid"] = self._phase_braid()
            self._phase = PossibilityPhase.CONVERGE
            phase_outputs["converge"] = self._phase_converge()
            self._phase = PossibilityPhase.INTEGRATE
            phase_outputs["integrate"] = self._phase_integrate()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_ground(self) -> Dict[str, Any]:
        """Ground phase: pending threads are anchored to the current reality."""
        grounded = 0
        for agent in self._agents.values():
            for thread in agent.threads.values():
                if thread.state != ThreadState.PENDING:
                    continue
                # Threads without an explicit grounding inherit a default anchor.
                if not thread.grounding:
                    thread.grounding = "the current state of affairs"
                # Plausibility is sharpened toward the agent's tolerance band.
                if thread.plausibility < 0.1:
                    thread.plausibility = 0.1
                thread.state = ThreadState.GROUNDED
                agent.total_grounded += 1
                grounded += 1
        self._stats["total_grounded"] += grounded
        self._record_event("phase_ground", {"grounded": grounded})
        return {"grounded": grounded}

    def _phase_diverge(self) -> Dict[str, Any]:
        """Diverge phase: each grounded thread branches into alternative descriptions."""
        diverged = 0
        for agent in self._agents.values():
            for thread in agent.threads.values():
                if thread.state != ThreadState.GROUNDED:
                    continue
                # Compose a branch description colored by the thread's valence.
                thread.branch_description = self._compose_branch(thread)
                # Divergence wobbles plausibility based on the agent's tolerance.
                wobble = (random.random() - 0.5) * (1.0 - agent.braiding_tolerance) * 0.4
                thread.plausibility = max(0.0, min(1.0, thread.plausibility + wobble))
                thread.state = ThreadState.DIVERGED
                agent.total_diverged += 1
                diverged += 1
        self._stats["total_diverged"] += diverged
        self._record_event("phase_diverge", {"diverged": diverged})
        return {"diverged": diverged}

    def _phase_braid(self) -> Dict[str, Any]:
        """Braid phase: crossing threads are woven together."""
        braided = 0
        crossings_added = 0
        for agent in self._agents.values():
            # Pairwise scan of diverged threads within this agent.
            diverged_threads = [
                t for t in agent.threads.values() if t.state == ThreadState.DIVERGED
            ]
            for i in range(len(diverged_threads)):
                for j in range(i + 1, len(diverged_threads)):
                    a = diverged_threads[i]
                    b = diverged_threads[j]
                    if a.plausibility < self._BRAID_CROSSING_THRESHOLD and \
                       b.plausibility < self._BRAID_CROSSING_THRESHOLD:
                        continue
                    relation, weight, note = self._classify_crossing(a, b)
                    if relation == BraidRelation.ORTHOGONAL and weight < 0.2:
                        continue
                    crossing = BraidCrossing(
                        crossing_id=f"cross_{a.thread_id}_{b.thread_id}_{self._cycle_count}",
                        thread_a_id=a.thread_id,
                        thread_b_id=b.thread_id,
                        relation=relation,
                        note=note,
                        weight=weight,
                    )
                    agent.crossings.append(crossing)
                    crossings_added += 1
                    # Each thread gains braid strength from the crossing.
                    a.braid_strength = min(1.0, a.braid_strength + weight * 0.3)
                    b.braid_strength = min(1.0, b.braid_strength + weight * 0.3)
            # Trim crossings to the cap, dropping the oldest.
            if len(agent.crossings) > self._MAX_CROSSINGS_PER_AGENT:
                agent.crossings = agent.crossings[-self._MAX_CROSSINGS_PER_AGENT:]
            # Mark all diverged threads as braided.
            for thread in diverged_threads:
                thread.state = ThreadState.BRAIDED
                agent.total_braided += 1
                braided += 1
        self._stats["total_braided"] += braided
        self._record_event("phase_braid", {
            "braided": braided,
            "crossings_added": crossings_added,
        })
        return {"braided": braided, "crossings_added": crossings_added}

    def _phase_converge(self) -> Dict[str, Any]:
        """Converge phase: braided threads condense toward coherence."""
        converged = 0
        for agent in self._agents.values():
            # Build a lookup of crossings per thread for this agent.
            crossing_map: Dict[str, List[BraidCrossing]] = {}
            for crossing in agent.crossings:
                crossing_map.setdefault(crossing.thread_a_id, []).append(crossing)
                crossing_map.setdefault(crossing.thread_b_id, []).append(crossing)
            for thread in agent.threads.values():
                if thread.state != ThreadState.BRAIDED:
                    continue
                coherence = 0.3  # base coherence
                for crossing in crossing_map.get(thread.thread_id, []):
                    if crossing.relation == BraidRelation.REINFORCING:
                        coherence += self._CONVERGE_COHERENCE_GAIN * crossing.weight
                    elif crossing.relation == BraidRelation.CONFLICTING:
                        coherence -= self._CONVERGE_TENSION_GAIN * crossing.weight
                    elif crossing.relation == BraidRelation.ENABLING:
                        coherence += self._CONVERGE_COHERENCE_GAIN * 0.5 * crossing.weight
                thread.coherence = max(0.0, min(1.0, coherence))
                # Threads with no crossings converge by their own plausibility.
                if thread.braid_strength == 0.0:
                    thread.coherence = max(0.0, min(1.0, 0.3 + thread.plausibility * 0.4))
                thread.state = ThreadState.CONVERGED
                agent.total_converged += 1
                converged += 1
        self._stats["total_converged"] += converged
        self._record_event("phase_converge", {"converged": converged})
        return {"converged": converged}

    def _phase_integrate(self) -> Dict[str, Any]:
        """Integrate phase: converged threads fold into the expectational model."""
        integrated = 0
        for agent in self._agents.values():
            model = agent.model
            for thread in list(agent.threads.values()):
                if thread.state != ThreadState.CONVERGED:
                    continue
                model.total_threads += 1
                model.valence_weights[thread.valence] = (
                    model.valence_weights.get(thread.valence, 0.0)
                    + thread.plausibility * (0.5 + thread.coherence * 0.5)
                )
                thread.state = ThreadState.INTEGRATED
                thread.resolved_at = time.time()
                agent.total_integrated += 1
                integrated += 1
            # Recompute the model aggregates.
            if model.valence_weights:
                model.dominant_valence = max(
                    model.valence_weights, key=lambda v: model.valence_weights[v]
                )
                total_weight = sum(model.valence_weights.values())
                model.avg_plausibility = (
                    total_weight / model.total_threads if model.total_threads else 0.5
                )
                # Openness: how evenly distributed the valence weights are.
                if total_weight > 0:
                    shares = [w / total_weight for w in model.valence_weights.values()]
                    model.openness = 1.0 - max(shares)
                else:
                    model.openness = 0.5
                model.signature = self._derive_signature(agent)
            # Once enough threads integrate, derive the stance.
            if model.total_threads >= self._INTEGRATE_STANCE_THRESHOLD:
                agent.stance = self._derive_stance(agent)
        self._stats["total_integrated"] += integrated
        self._record_event("phase_integrate", {"integrated": integrated})
        return {"integrated": integrated}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _compose_branch(self, thread: PossibilityThread) -> str:
        """Compose a branch description colored by the thread's valence."""
        templates = {
            ThreadValence.HOPED: f"if all goes well: {thread.label} (grounded in {thread.grounding})",
            ThreadValence.FEARED: f"if things go wrong: {thread.label} (grounded in {thread.grounding})",
            ThreadValence.EXPECTED: f"as things stand: {thread.label} (grounded in {thread.grounding})",
            ThreadValence.WILDCARD: f"out of left field: {thread.label} (grounded in {thread.grounding})",
        }
        return templates.get(thread.valence, thread.label)

    def _classify_crossing(self, a: PossibilityThread,
                           b: PossibilityThread) -> tuple:
        """Classify how two threads relate where they cross."""
        # Same valence and similar plausibility -> reinforcing.
        if a.valence == b.valence:
            diff = abs(a.plausibility - b.plausibility)
            if diff < 0.25:
                weight = 0.5 + (1.0 - diff) * 0.4
                return (BraidRelation.REINFORCING, min(1.0, weight),
                        "both threads push the same future")
        # Opposite valence with overlapping grounding -> conflicting.
        opposites = {
            (ThreadValence.HOPED, ThreadValence.FEARED),
            (ThreadValence.FEARED, ThreadValence.HOPED),
        }
        if (a.valence, b.valence) in opposites and a.grounding == b.grounding:
            weight = 0.4 + min(a.plausibility, b.plausibility) * 0.4
            return (BraidRelation.CONFLICTING, min(1.0, weight),
                    "the hoped and feared futures collide on the same ground")
        # One wildcard with a high-plausibility thread -> enabling.
        if ThreadValence.WILDCARD in (a.valence, b.valence):
            weight = 0.3 + min(a.plausibility, b.plausibility) * 0.3
            return (BraidRelation.ENABLING, min(1.0, weight),
                    "the wildcard unlocks the other thread")
        # Default: orthogonal.
        weight = 0.2 + min(a.plausibility, b.plausibility) * 0.2
        return (BraidRelation.ORTHOGONAL, min(1.0, weight),
                "the threads touch but do not truly interact")

    def _derive_signature(self, agent: PossibilityAgent) -> str:
        """Derive a signature phrase for the agent's expectational model."""
        model = agent.model
        if not model.valence_weights:
            return "no signature yet"
        top = model.dominant_valence
        if model.openness > 0.6:
            openness_phrase = "open"
        elif model.openness > 0.3:
            openness_phrase = "settled"
        else:
            openness_phrase = "narrow"
        return f"{openness_phrase} {top.value} landscape"

    def _derive_stance(self, agent: PossibilityAgent) -> ExpectationalStance:
        """Derive the agent's overall expectational stance."""
        model = agent.model
        if model.total_threads < self._INTEGRATE_STANCE_THRESHOLD:
            return ExpectationalStance.UNFORMED
        top = model.dominant_valence
        # Low openness -> narrow regardless of valence.
        if model.openness < 0.2:
            return ExpectationalStance.NARROW
        # High openness -> plural.
        if model.openness > 0.55:
            return ExpectationalStance.PLURAL
        # Mid openness: stance follows the dominant valence.
        mapping = {
            ThreadValence.HOPED: ExpectationalStance.OPTIMISTIC,
            ThreadValence.FEARED: ExpectationalStance.ANXIOUS,
            ThreadValence.EXPECTED: ExpectationalStance.PRAGMATIC,
            ThreadValence.WILDCARD: ExpectationalStance.PLURAL,
        }
        return mapping.get(top, ExpectationalStance.PRAGMATIC)

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "stance": agent.stance.value,
                "braiding_tolerance": agent.braiding_tolerance,
                "total_grounded": agent.total_grounded,
                "total_diverged": agent.total_diverged,
                "total_braided": agent.total_braided,
                "total_converged": agent.total_converged,
                "total_integrated": agent.total_integrated,
                "model": {
                    "total_threads": agent.model.total_threads,
                    "valence_weights": {
                        v.value: w for v, w in agent.model.valence_weights.items()
                    },
                    "avg_plausibility": agent.model.avg_plausibility,
                    "dominant_valence": agent.model.dominant_valence.value,
                    "openness": agent.model.openness,
                    "signature": agent.model.signature,
                },
                "crossings_count": len(agent.crossings),
            }

    def get_thread(self, agent_id: str, thread_id: str) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            thread = agent.threads.get(thread_id)
            if thread is None:
                return {"error": f"Thread not found: {thread_id}"}
            return {
                "thread_id": thread.thread_id,
                "label": thread.label,
                "valence": thread.valence.value,
                "grounding": thread.grounding,
                "branch_description": thread.branch_description,
                "plausibility": thread.plausibility,
                "coherence": thread.coherence,
                "braid_strength": thread.braid_strength,
                "state": thread.state.value,
                "created_at": thread.created_at,
                "resolved_at": thread.resolved_at,
            }

    def get_threads(self, agent_id: str, limit: int = 20) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            threads = sorted(
                agent.threads.values(),
                key=lambda t: t.created_at,
                reverse=True,
            )[:limit]
            return {
                "agent_id": agent_id,
                "threads": [
                    {
                        "thread_id": t.thread_id,
                        "label": t.label,
                        "valence": t.valence.value,
                        "state": t.state.value,
                        "plausibility": t.plausibility,
                        "coherence": t.coherence,
                    }
                    for t in threads
                ],
            }

    def get_crossings(self, agent_id: str, limit: int = 30) -> Dict[str, Any]:
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            crossings = agent.crossings[-limit:]
            return {
                "agent_id": agent_id,
                "crossings": [
                    {
                        "crossing_id": c.crossing_id,
                        "thread_a_id": c.thread_a_id,
                        "thread_b_id": c.thread_b_id,
                        "relation": c.relation.value,
                        "weight": c.weight,
                        "note": c.note,
                    }
                    for c in crossings
                ],
            }

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "agents": len(self._agents),
                "stats": dict(self._stats),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic agents and threads, then run multiple cycles."""
        with self._global_lock:
            self._seed_synthetic_agents()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_agents(self) -> None:
        """Seed a small synthetic cast of agents with distinct braiding styles."""
        seed_agents = [
            ("sim_strategist", 0.6),
            ("sim_pessimist", 0.3),
            ("sim_dreamer", 0.8),
        ]
        for agent_id, tolerance in seed_agents:
            if agent_id in self._agents:
                continue
            self.register_agent(agent_id, braiding_tolerance=tolerance)
        # Seed shared possibility threads for each agent.
        seed_threads = [
            ("sim_t1", "the alliance holds", ThreadValence.HOPED, 0.6, "the treaty"),
            ("sim_t2", "the alliance fractures", ThreadValence.FEARED, 0.4, "the treaty"),
            ("sim_t3", "a third party intervenes", ThreadValence.WILDCARD, 0.2, "the border"),
            ("sim_t4", "trade resumes as expected", ThreadValence.EXPECTED, 0.7, "the market"),
            ("sim_t5", "trade collapses", ThreadValence.FEARED, 0.3, "the market"),
            ("sim_t6", "a new faction rises", ThreadValence.WILDCARD, 0.25, "the frontier"),
        ]
        for agent_id, _ in seed_agents:
            agent = self._agents.get(agent_id)
            if agent is None:
                continue
            for tid, label, valence, plausibility, grounding in seed_threads:
                if tid not in agent.threads:
                    self.introduce_thread(
                        agent_id, tid, label, valence,
                        plausibility=plausibility, grounding=grounding,
                    )

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._agents.clear()
            self._events_log.clear()
            self._phase = PossibilityPhase.GROUND
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}
