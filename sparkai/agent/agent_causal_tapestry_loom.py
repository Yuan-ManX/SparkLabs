"""
SparkLabs Agent - Causal Tapestry Loom

The AgentCausalTapestryLoom models agent causal reasoning as a weaving
process. Events in the game world are not isolated; they are connected
by causal threads. Agents spin these threads from observations, dye them
with emotional and contextual meaning, weave them into a tapestry of
understanding, mend gaps in their causal model, and unravel stale
threads that no longer hold.

This goes beyond simple event logging. The loom constructs a living
causal graph where agents can:
  - Trace WHY something happened by following threads backward
  - Predict WHAT will happen by projecting threads forward
  - Identify gaps in their understanding (unwoven regions)
  - Detect contradictions (threads that cross and conflict)
  - Form hypotheses about hidden causes (virtual threads)

Architecture:
  SPIN     ->  DYE       ->  WEAVE     ->  MEND      ->  UNRAVEL
  (extract    (color       (interlace    (fill gaps    (release
   causal      threads      threads       in the        threads
   threads     with         into a        causal        that no
   from raw    context      cohesive      model with    longer
   events)     and          tapestry)     hypotheses)   hold)

Thread properties:
  - strength    : confidence in the causal link (0.0-1.0)
  - valence     : emotional coloring (-1.0 to 1.0)
  - salience    : how noticeable this thread is (0.0-1.0)
  - tense       : past (observed) / present (active) / future (predicted)
  - spin_count  : how many times this thread has been reinforced

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
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class TapestryPhase(Enum):
    """Phases of the causal tapestry cycle."""
    SPIN = "spin"            # extract causal threads from events
    DYE = "dye"              # color threads with context and emotion
    WEAVE = "weave"          # interlace threads into a cohesive model
    MEND = "mend"            # fill gaps with hypotheses
    UNRAVEL = "unravel"      # release stale or broken threads


class ThreadTense(Enum):
    """Temporal tense of a causal thread."""
    PAST = "past"            # observed cause-effect
    PRESENT = "present"      # actively unfolding
    FUTURE = "future"        # predicted outcome


class ThreadType(Enum):
    """Nature of the causal connection."""
    DIRECT = "direct"            # A directly causes B
    CONTRIBUTING = "contributing"  # A contributes to B among other factors
    ENABLING = "enabling"        # A enables B but does not cause it alone
    INHIBITING = "inhibiting"    # A prevents or reduces B
    CORRELATIVE = "correlative"  # A and B co-occur without clear direction
    VIRTUAL = "virtual"          # hypothesized hidden cause


class WeavePattern(Enum):
    """How threads are organized in the tapestry."""
    LINEAR = "linear"            # simple chain A -> B -> C
    BRANCHING = "branching"      # one cause, multiple effects
    CONVERGING = "converging"    # multiple causes, one effect
    LOOP = "loop"                # circular causality
    MESH = "mesh"                # complex interconnected web


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CausalThread:
    """A single causal link between two events."""
    thread_id: str
    source_event: str           # the cause event ID
    target_event: str           # the effect event ID
    thread_type: ThreadType
    tense: ThreadTense = ThreadTense.PAST
    strength: float = 0.5       # confidence in the link (0.0-1.0)
    valence: float = 0.0        # emotional coloring (-1.0 to 1.0)
    salience: float = 0.5       # noteworthiness (0.0-1.0)
    spin_count: int = 1         # how many times reinforced
    description: str = ""
    created_at: float = field(default_factory=time.time)
    last_reinforced: float = field(default_factory=time.time)
    dye_tags: List[str] = field(default_factory=list)  # contextual tags


@dataclass
class CausalEvent:
    """An event node in the causal graph."""
    event_id: str
    label: str
    domain: str                 # e.g., "combat", "social", "narrative"
    timestamp: float = field(default_factory=time.time)
    properties: Dict[str, Any] = field(default_factory=dict)
    incoming_threads: List[str] = field(default_factory=list)
    outgoing_threads: List[str] = field(default_factory=list)


@dataclass
class WeaveRegion:
    """A cluster of interconnected threads forming a pattern."""
    region_id: str
    label: str
    pattern: WeavePattern
    thread_ids: Set[str] = field(default_factory=set)
    event_ids: Set[str] = field(default_factory=set)
    coherence: float = 0.5      # how internally consistent (0.0-1.0)
    created_at: float = field(default_factory=time.time)


@dataclass
class CausalGap:
    """A gap in the causal model that needs mending."""
    gap_id: str
    source_event: str           # we know this happened
    target_event: str           # and this happened, but no link
    gap_type: str               # "missing_link", "contradiction", "unexplained"
    severity: float = 0.5
    mended: bool = False
    hypothesis: Optional[str] = None  # virtual thread to fill the gap


@dataclass
class AgentTapestry:
    """Per-agent causal tapestry."""
    agent_id: str
    events: Dict[str, CausalEvent] = field(default_factory=dict)
    threads: Dict[str, CausalThread] = field(default_factory=dict)
    regions: Dict[str, WeaveRegion] = field(default_factory=dict)
    gaps: Dict[str, CausalGap] = field(default_factory=dict)
    total_threads_spun: int = 0
    total_gaps_mended: int = 0
    total_unraveled: int = 0
    last_cycle_time: float = 0.0


# =============================================================================
# Engine
# =============================================================================

class AgentCausalTapestryLoom:
    """
    Thread-safe singleton orchestrating causal reasoning across agents.

    Usage:
        loom = AgentCausalTapestryLoom.get_instance()
        loom.register_agent("hero_1")
        loom.observe_event("hero_1", "evt_battle", "Battle Started", "combat")
        loom.spin_thread("hero_1", "th_1", "evt_battle", "evt_victory",
                         ThreadType.DIRECT, strength=0.8)
        loom.dye_thread("hero_1", "th_1", valence=0.7, tags=["victory", "glory"])
        loom.weave("hero_1")
        loom.cycle()
    """

    _instance: Optional["AgentCausalTapestryLoom"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._tapestries: Dict[str, AgentTapestry] = {}
        self._phase: TapestryPhase = TapestryPhase.SPIN
        self._cycle_count: int = 0
        self._events: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_agents": 0,
            "total_events": 0,
            "total_threads": 0,
            "total_regions": 0,
            "total_gaps": 0,
            "total_gaps_mended": 0,
            "total_unraveled": 0,
            "avg_tapestry_coherence": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentCausalTapestryLoom":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Registration
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str) -> Dict[str, Any]:
        """Register a new agent with an empty tapestry."""
        with self._global_lock:
            if agent_id in self._tapestries:
                return {"error": f"Agent already registered: {agent_id}"}
            self._tapestries[agent_id] = AgentTapestry(agent_id=agent_id)
            self._stats["total_agents"] = len(self._tapestries)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {"agent_id": agent_id, "events": 0, "threads": 0}

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent's tapestry."""
        with self._global_lock:
            if agent_id not in self._tapestries:
                return {"error": f"Agent not found: {agent_id}"}
            t = self._tapestries.pop(agent_id)
            self._stats["total_agents"] = len(self._tapestries)
            self._record_event("agent_removed", {"agent_id": agent_id})
            return {"removed": agent_id, "threads": len(t.threads)}

    # -------------------------------------------------------------------------
    # Event Observation
    # -------------------------------------------------------------------------

    def observe_event(
        self,
        agent_id: str,
        event_id: str,
        label: str,
        domain: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record an event in an agent's causal tapestry."""
        with self._global_lock:
            t = self._tapestries.get(agent_id)
            if t is None:
                return {"error": f"Agent not found: {agent_id}"}
            if event_id in t.events:
                return {"error": f"Event already exists: {event_id}"}
            event = CausalEvent(
                event_id=event_id,
                label=label,
                domain=domain,
                properties=properties or {},
            )
            t.events[event_id] = event
            self._stats["total_events"] = sum(
                len(tp.events) for tp in self._tapestries.values()
            )
            return {
                "event_id": event_id,
                "label": label,
                "domain": domain,
            }

    # -------------------------------------------------------------------------
    # Thread Spinning
    # -------------------------------------------------------------------------

    def spin_thread(
        self,
        agent_id: str,
        thread_id: str,
        source_event: str,
        target_event: str,
        thread_type: ThreadType,
        strength: float = 0.5,
        valence: float = 0.0,
        salience: float = 0.5,
        description: str = "",
        tense: ThreadTense = ThreadTense.PAST,
    ) -> Dict[str, Any]:
        """Spin a new causal thread linking two events."""
        with self._global_lock:
            t = self._tapestries.get(agent_id)
            if t is None:
                return {"error": f"Agent not found: {agent_id}"}
            if thread_id in t.threads:
                return {"error": f"Thread already exists: {thread_id}"}
            if source_event not in t.events:
                return {"error": f"Source event not found: {source_event}"}
            if target_event not in t.events:
                return {"error": f"Target event not found: {target_event}"}
            thread = CausalThread(
                thread_id=thread_id,
                source_event=source_event,
                target_event=target_event,
                thread_type=thread_type,
                tense=tense,
                strength=max(0.0, min(1.0, strength)),
                valence=max(-1.0, min(1.0, valence)),
                salience=max(0.0, min(1.0, salience)),
                description=description,
            )
            t.threads[thread_id] = thread
            t.events[source_event].outgoing_threads.append(thread_id)
            t.events[target_event].incoming_threads.append(thread_id)
            t.total_threads_spun += 1
            self._stats["total_threads"] = sum(
                len(tp.threads) for tp in self._tapestries.values()
            )
            self._record_event("thread_spun", {
                "agent_id": agent_id,
                "thread_id": thread_id,
                "source": source_event,
                "target": target_event,
                "type": thread_type.value,
            })
            return {
                "thread_id": thread_id,
                "source_event": source_event,
                "target_event": target_event,
                "thread_type": thread_type.value,
                "strength": thread.strength,
            }

    # -------------------------------------------------------------------------
    # Thread Dyeing
    # -------------------------------------------------------------------------

    def dye_thread(
        self,
        agent_id: str,
        thread_id: str,
        valence: Optional[float] = None,
        salience: Optional[float] = None,
        tags: Optional[List[str]] = None,
        strength_boost: float = 0.0,
    ) -> Dict[str, Any]:
        """Apply emotional and contextual coloring to a thread."""
        with self._global_lock:
            t = self._tapestries.get(agent_id)
            if t is None:
                return {"error": f"Agent not found: {agent_id}"}
            thread = t.threads.get(thread_id)
            if thread is None:
                return {"error": f"Thread not found: {thread_id}"}
            if valence is not None:
                thread.valence = max(-1.0, min(1.0, valence))
            if salience is not None:
                thread.salience = max(0.0, min(1.0, salience))
            if tags:
                thread.dye_tags.extend(tags)
            if strength_boost:
                thread.strength = min(1.0, thread.strength + strength_boost)
                thread.spin_count += 1
                thread.last_reinforced = time.time()
            return {
                "thread_id": thread_id,
                "valence": thread.valence,
                "salience": thread.salience,
                "dye_tags": thread.dye_tags,
                "strength": thread.strength,
                "spin_count": thread.spin_count,
            }

    # -------------------------------------------------------------------------
    # Weaving
    # -------------------------------------------------------------------------

    def weave(self, agent_id: str) -> Dict[str, Any]:
        """Interlace threads into weave regions (causal patterns)."""
        with self._global_lock:
            t = self._tapestries.get(agent_id)
            if t is None:
                return {"error": f"Agent not found: {agent_id}"}
            # Detect patterns: find clusters of connected events
            visited: Set[str] = set()
            new_regions: List[WeaveRegion] = []
            for event_id in t.events:
                if event_id in visited:
                    continue
                cluster_events: Set[str] = set()
                cluster_threads: Set[str] = set()
                self._bfs_collect(t, event_id, visited, cluster_events, cluster_threads)
                if len(cluster_threads) < 2:
                    continue
                pattern = self._detect_pattern(cluster_events, cluster_threads, t)
                region_id = f"region_{agent_id}_{len(t.regions) + len(new_regions)}"
                region = WeaveRegion(
                    region_id=region_id,
                    label=f"Cluster of {len(cluster_events)} events",
                    pattern=pattern,
                    thread_ids=cluster_threads,
                    event_ids=cluster_events,
                    coherence=self._compute_coherence(cluster_threads, t),
                )
                new_regions.append(region)
            # Replace old regions with freshly woven ones
            old_count = len(t.regions)
            t.regions = {r.region_id: r for r in new_regions}
            self._stats["total_regions"] = sum(
                len(tp.regions) for tp in self._tapestries.values()
            )
            self._record_event("woven", {
                "agent_id": agent_id,
                "regions": len(new_regions),
                "old_regions": old_count,
            })
            return {
                "agent_id": agent_id,
                "regions_woven": len(new_regions),
                "patterns": [r.pattern.value for r in new_regions],
            }

    def _bfs_collect(
        self,
        tapestry: AgentTapestry,
        start: str,
        visited: Set[str],
        events: Set[str],
        threads: Set[str],
    ) -> None:
        """BFS to collect all connected events and threads."""
        queue = [start]
        while queue:
            eid = queue.pop(0)
            if eid in visited:
                continue
            visited.add(eid)
            events.add(eid)
            event = tapestry.events.get(eid)
            if event is None:
                continue
            for tid in event.outgoing_threads + event.incoming_threads:
                if tid in threads:
                    continue
                threads.add(tid)
                thread = tapestry.threads.get(tid)
                if thread is None:
                    continue
                neighbor = thread.target_event if thread.source_event == eid else thread.source_event
                if neighbor not in visited:
                    queue.append(neighbor)

    def _detect_pattern(
        self,
        events: Set[str],
        threads: Set[str],
        tapestry: AgentTapestry,
    ) -> WeavePattern:
        """Detect the weave pattern of a cluster."""
        # Count in/out degrees
        in_degrees: Dict[str, int] = {e: 0 for e in events}
        out_degrees: Dict[str, int] = {e: 0 for e in events}
        for tid in threads:
            thread = tapestry.threads.get(tid)
            if thread is None:
                continue
            out_degrees[thread.source_event] = out_degrees.get(thread.source_event, 0) + 1
            in_degrees[thread.target_event] = in_degrees.get(thread.target_event, 0) + 1
        # Check for loops
        if self._has_cycle(events, threads, tapestry):
            return WeavePattern.LOOP
        # Multiple causes converging on one effect
        multi_in = sum(1 for d in in_degrees.values() if d > 1)
        # One cause branching to multiple effects
        multi_out = sum(1 for d in out_degrees.values() if d > 1)
        if multi_in > 0 and multi_out > 0:
            return WeavePattern.MESH
        if multi_in > 0:
            return WeavePattern.CONVERGING
        if multi_out > 0:
            return WeavePattern.BRANCHING
        return WeavePattern.LINEAR

    def _has_cycle(
        self,
        events: Set[str],
        threads: Set[str],
        tapestry: AgentTapestry,
    ) -> bool:
        """Check if the subgraph has a cycle using DFS."""
        adj: Dict[str, List[str]] = {e: [] for e in events}
        for tid in threads:
            thread = tapestry.threads.get(tid)
            if thread is None:
                continue
            if thread.source_event in adj:
                adj[thread.source_event].append(thread.target_event)
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {e: WHITE for e in events}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for neighbor in adj.get(node, []):
                if color.get(neighbor, WHITE) == GRAY:
                    return True
                if color.get(neighbor, WHITE) == WHITE:
                    if dfs(neighbor):
                        return True
            color[node] = BLACK
            return False

        for e in events:
            if color[e] == WHITE:
                if dfs(e):
                    return True
        return False

    def _compute_coherence(self, thread_ids: Set[str], tapestry: AgentTapestry) -> float:
        """Compute internal coherence of a weave region."""
        if not thread_ids:
            return 0.0
        total_strength = 0.0
        total_salience = 0.0
        count = 0
        for tid in thread_ids:
            thread = tapestry.threads.get(tid)
            if thread is None:
                continue
            total_strength += thread.strength
            total_salience += thread.salience
            count += 1
        if count == 0:
            return 0.0
        avg_strength = total_strength / count
        avg_salience = total_salience / count
        return max(0.0, min(1.0, avg_strength * 0.6 + avg_salience * 0.4))

    # -------------------------------------------------------------------------
    # Mending (Gap Detection and Hypothesis Formation)
    # -------------------------------------------------------------------------

    def mend(self, agent_id: str) -> Dict[str, Any]:
        """Detect gaps in the causal model and form hypotheses."""
        with self._global_lock:
            t = self._tapestries.get(agent_id)
            if t is None:
                return {"error": f"Agent not found: {agent_id}"}
            gaps_found = 0
            gaps_mended = 0
            # Find events with no incoming threads (unexplained causes)
            for event_id, event in t.events.items():
                if not event.incoming_threads and len(t.events) > 1:
                    gap_id = f"gap_{agent_id}_{event_id}_{len(t.gaps)}"
                    gap = CausalGap(
                        gap_id=gap_id,
                        source_event="unknown",
                        target_event=event_id,
                        gap_type="unexplained",
                        severity=0.6,
                    )
                    # Form a hypothesis: find a likely cause
                    hypothesis = self._form_hypothesis(t, event_id)
                    if hypothesis:
                        gap.hypothesis = hypothesis
                        gap.mended = True
                        gaps_mended += 1
                        # Create a virtual thread
                        virt_id = f"virt_{agent_id}_{event_id}_{len(t.threads)}"
                        virt_thread = CausalThread(
                            thread_id=virt_id,
                            source_event=hypothesis,
                            target_event=event_id,
                            thread_type=ThreadType.VIRTUAL,
                            tense=ThreadTense.PAST,
                            strength=0.3,
                            salience=0.4,
                            description=f"Hypothesized cause for {event.label}",
                        )
                        t.threads[virt_id] = virt_thread
                        t.events[event_id].incoming_threads.append(virt_id)
                    t.gaps[gap_id] = gap
                    gaps_found += 1
            # Detect contradictions: threads with conflicting valence to same event
            for event_id, event in t.events.items():
                if len(event.incoming_threads) < 2:
                    continue
                valences = []
                for tid in event.incoming_threads:
                    thread = t.threads.get(tid)
                    if thread:
                        valences.append(thread.valence)
                if valences and max(valences) > 0.5 and min(valences) < -0.5:
                    gap_id = f"contradiction_{agent_id}_{event_id}_{len(t.gaps)}"
                    gap = CausalGap(
                        gap_id=gap_id,
                        source_event=event_id,
                        target_event=event_id,
                        gap_type="contradiction",
                        severity=0.8,
                    )
                    t.gaps[gap_id] = gap
                    gaps_found += 1
            t.total_gaps_mended += gaps_mended
            self._stats["total_gaps"] = sum(len(tp.gaps) for tp in self._tapestries.values())
            self._stats["total_gaps_mended"] = sum(
                tp.total_gaps_mended for tp in self._tapestries.values()
            )
            self._record_event("mended", {
                "agent_id": agent_id,
                "gaps_found": gaps_found,
                "gaps_mended": gaps_mended,
            })
            return {
                "agent_id": agent_id,
                "gaps_found": gaps_found,
                "gaps_mended": gaps_mended,
                "total_gaps": len(t.gaps),
            }

    def _form_hypothesis(self, tapestry: AgentTapestry, target_event: str) -> Optional[str]:
        """Form a hypothesis about the hidden cause of an event."""
        target = tapestry.events.get(target_event)
        if target is None:
            return None
        # Find an event in the same domain that occurred earlier
        candidates = [
            e for e in tapestry.events.values()
            if e.event_id != target_event
            and e.domain == target.domain
            and e.timestamp < target.timestamp
            and e.outgoing_threads
        ]
        if not candidates:
            # Fall back to any earlier event
            candidates = [
                e for e in tapestry.events.values()
                if e.event_id != target_event and e.timestamp < target.timestamp
            ]
        if not candidates:
            return None
        # Pick the most salient candidate
        best = max(candidates, key=lambda e: e.timestamp)
        return best.event_id

    # -------------------------------------------------------------------------
    # Unraveling (Stale Thread Removal)
    # -------------------------------------------------------------------------

    def unravel(self, agent_id: str, max_age: float = 3600.0) -> Dict[str, Any]:
        """Unravel stale or weak threads that no longer hold."""
        with self._global_lock:
            t = self._tapestries.get(agent_id)
            if t is None:
                return {"error": f"Agent not found: {agent_id}"}
            now = time.time()
            to_remove: List[str] = []
            for tid, thread in t.threads.items():
                age = now - thread.last_reinforced
                if age > max_age and thread.strength < 0.3:
                    to_remove.append(tid)
                elif thread.strength < 0.1:
                    to_remove.append(tid)
            for tid in to_remove:
                thread = t.threads[tid]
                # Clean up event references
                src = t.events.get(thread.source_event)
                if src and tid in src.outgoing_threads:
                    src.outgoing_threads.remove(tid)
                tgt = t.events.get(thread.target_event)
                if tgt and tid in tgt.incoming_threads:
                    tgt.incoming_threads.remove(tid)
                del t.threads[tid]
            t.total_unraveled += len(to_remove)
            self._stats["total_unraveled"] = sum(
                tp.total_unraveled for tp in self._tapestries.values()
            )
            self._stats["total_threads"] = sum(
                len(tp.threads) for tp in self._tapestries.values()
            )
            self._record_event("unraveled", {
                "agent_id": agent_id,
                "threads_removed": len(to_remove),
            })
            return {
                "agent_id": agent_id,
                "threads_unraveled": len(to_remove),
                "remaining_threads": len(t.threads),
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single tapestry cycle across all agents."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            # SPIN: no-op (threads spun via API)
            self._phase = TapestryPhase.SPIN
            phase_outputs["spin"] = {"agents": len(self._tapestries)}
            # DYE: auto-dye based on event properties
            self._phase = TapestryPhase.DYE
            phase_outputs["dye"] = self._phase_dye()
            # WEAVE: rebuild regions
            self._phase = TapestryPhase.WEAVE
            weave_results = {}
            for agent_id in self._tapestries:
                weave_results[agent_id] = self.weave(agent_id)
            phase_outputs["weave"] = {
                "agents_woven": len(weave_results),
                "total_regions": sum(
                    r.get("regions_woven", 0) for r in weave_results.values()
                ),
            }
            # MEND: detect and fill gaps
            self._phase = TapestryPhase.MEND
            mend_results = {}
            for agent_id in self._tapestries:
                mend_results[agent_id] = self.mend(agent_id)
            phase_outputs["mend"] = {
                "agents_mended": len(mend_results),
                "total_gaps_found": sum(
                    r.get("gaps_found", 0) for r in mend_results.values()
                ),
                "total_gaps_mended": sum(
                    r.get("gaps_mended", 0) for r in mend_results.values()
                ),
            }
            # UNRAVEL: remove stale threads
            self._phase = TapestryPhase.UNRAVEL
            unravel_results = {}
            for agent_id in self._tapestries:
                unravel_results[agent_id] = self.unravel(agent_id, max_age=999999.0)
            phase_outputs["unravel"] = {
                "agents_unraveled": len(unravel_results),
                "total_unraveled": sum(
                    r.get("threads_unraveled", 0) for r in unravel_results.values()
                ),
            }
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles."""
        if cycles < 1 or cycles > 1000:
            return {"error": "cycles must be 1-1000"}
        for _ in range(cycles):
            self.cycle()
        return {
            "cycles_run": cycles,
            "final_phase": self._phase.value,
            "stats": dict(self._stats),
        }

    def _phase_dye(self) -> Dict[str, Any]:
        """Auto-dye threads based on event domain heuristics."""
        dyed = 0
        domain_valence = {
            "combat": -0.2,
            "social": 0.2,
            "narrative": 0.1,
            "exploration": 0.3,
            "economy": 0.0,
        }
        for t in self._tapestries.values():
            for thread in t.threads.values():
                if thread.dye_tags:
                    continue
                src = t.events.get(thread.source_event)
                if src and src.domain in domain_valence:
                    base = domain_valence[src.domain]
                    thread.valence = max(-1.0, min(1.0, thread.valence + base * 0.3))
                    thread.dye_tags.append(src.domain)
                    dyed += 1
        return {"auto_dyed": dyed}

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get global loom status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_agents": len(self._tapestries),
                "stats": dict(self._stats),
            }

    def get_tapestry(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get full tapestry details for an agent."""
        with self._global_lock:
            t = self._tapestries.get(agent_id)
            if t is None:
                return None
            return {
                "agent_id": agent_id,
                "total_events": len(t.events),
                "total_threads": len(t.threads),
                "total_regions": len(t.regions),
                "total_gaps": len(t.gaps),
                "total_spun": t.total_threads_spun,
                "total_mended": t.total_gaps_mended,
                "total_unraveled": t.total_unraveled,
                "events": [
                    {
                        "event_id": e.event_id,
                        "label": e.label,
                        "domain": e.domain,
                        "incoming": len(e.incoming_threads),
                        "outgoing": len(e.outgoing_threads),
                    }
                    for e in list(t.events.values())[:20]
                ],
                "threads": [
                    {
                        "thread_id": th.thread_id,
                        "source": th.source_event,
                        "target": th.target_event,
                        "type": th.thread_type.value,
                        "tense": th.tense.value,
                        "strength": th.strength,
                        "valence": th.valence,
                        "salience": th.salience,
                        "spin_count": th.spin_count,
                        "dye_tags": th.dye_tags,
                    }
                    for th in list(t.threads.values())[:30]
                ],
                "regions": [
                    {
                        "region_id": r.region_id,
                        "label": r.label,
                        "pattern": r.pattern.value,
                        "thread_count": len(r.thread_ids),
                        "event_count": len(r.event_ids),
                        "coherence": r.coherence,
                    }
                    for r in t.regions.values()
                ],
            }

    def get_regions(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get weave regions for an agent."""
        with self._global_lock:
            t = self._tapestries.get(agent_id)
            if t is None:
                return []
            return [
                {
                    "region_id": r.region_id,
                    "label": r.label,
                    "pattern": r.pattern.value,
                    "thread_count": len(r.thread_ids),
                    "event_count": len(r.event_ids),
                    "coherence": r.coherence,
                }
                for r in t.regions.values()
            ]

    def get_gaps(self, agent_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get causal gaps for an agent."""
        with self._global_lock:
            t = self._tapestries.get(agent_id)
            if t is None:
                return []
            return [
                {
                    "gap_id": g.gap_id,
                    "source": g.source_event,
                    "target": g.target_event,
                    "gap_type": g.gap_type,
                    "severity": g.severity,
                    "mended": g.mended,
                    "hypothesis": g.hypothesis,
                }
                for g in list(t.gaps.values())[:limit]
            ]

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent loom events."""
        with self._global_lock:
            return list(self._events)[-limit:]

    def list_agents(self) -> List[str]:
        """List all registered agent IDs."""
        with self._global_lock:
            return list(self._tapestries.keys())

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire loom."""
        with self._global_lock:
            n = len(self._tapestries)
            self._tapestries.clear()
            self._phase = TapestryPhase.SPIN
            self._cycle_count = 0
            self._events.clear()
            self._stats = {
                "total_agents": 0,
                "total_events": 0,
                "total_threads": 0,
                "total_regions": 0,
                "total_gaps": 0,
                "total_gaps_mended": 0,
                "total_unraveled": 0,
                "avg_tapestry_coherence": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            self._record_event("loom_reset", {"cleared_agents": n})
            return {"reset": True, "cleared_agents": n}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        """Recompute aggregate statistics."""
        total_coherence = 0.0
        count = 0
        for t in self._tapestries.values():
            for r in t.regions.values():
                total_coherence += r.coherence
                count += 1
        if count > 0:
            self._stats["avg_tapestry_coherence"] = total_coherence / count

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a loom event."""
        self._events.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
