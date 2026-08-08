"""
SparkLabs Engine - Causal Timeline Weaver

The EngineCausalTimelineWeaver weaves a causal timeline of events.
Every consequential thing that happens in the world has causes behind
it and effects ahead of it; this engine maintains the chain by recording
each event, linking it to its causes, and tracing its effects forward.
As the timeline grows, the weaver detects causal threads (chains of
events that share a common root cause), identifies feedback loops (an
effect that circles back to cause its own cause), and flags orphan
events (effects with no recorded cause). The output is a queryable
causal history that lets the engine answer "why did this happen?" and
"what will this lead to?" - the backbone of a world where consequences
feel real.

Architecture:
  RECORD  ->  LINK   ->  TRACE  ->  PRUNE  ->  EMIT
  (accept    (resolve    (detect     (retire     (emit the
   new        cause to    threads,    stale       current
   events     effect      loops,      edges,      causal map
   with       edges,      orphans)    compact     for downstream
   declared   validate                the         queries)
   causes)    temporal                timeline)
              order)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class WeaverPhase(Enum):
    """Phases of the causal timeline weave cycle."""
    RECORD = "record"      # accept new events with their declared causes
    LINK = "link"          # resolve cause to effect edges, validate ordering
    TRACE = "trace"        # detect threads, loops, and orphans
    PRUNE = "prune"        # retire stale edges and collapsed threads
    EMIT = "emit"          # emit the current causal map for queries


class EventKind(Enum):
    """The kind of event recorded on the timeline."""
    ACTION = "action"                # an agent did something
    DECISION = "decision"            # a choice was made
    OCCURRENCE = "occurrence"        # something happened in the world
    REACTION = "reaction"            # a response to a prior event
    TURNING_POINT = "turning_point"  # the trajectory of the timeline shifted
    CATALYST = "catalyst"            # the seed cause of a new thread


class LinkStrength(Enum):
    """How strongly a cause pulls its effect into being."""
    DIRECT = "direct"        # the sole, immediate cause
    STRONG = "strong"        # a primary cause
    MODERATE = "moderate"    # a contributing cause
    WEAK = "weak"            # a minor cause
    TENUOUS = "tenuous"      # a barely-there cause


class ThreadState(Enum):
    """State of a causal thread (a chain sharing one root cause)."""
    GROWING = "growing"      # gaining new members this cycle
    STABLE = "stable"        # unchanged
    DECAYING = "decaying"    # no new members for several cycles
    COLLAPSED = "collapsed"  # retired, ready to be pruned
    ORPHAN = "orphan"        # the thread root has no recorded cause


class LoopState(Enum):
    """State of a detected feedback loop."""
    FORMING = "forming"          # first time the cycle was seen
    CLOSED = "closed"            # the cycle is confirmed
    REINFORCING = "reinforcing"  # the cycle persists across cycles
    DAMPED = "damped"            # the cycle is fading
    BROKEN = "broken"            # the cycle was severed


class WeaverState(Enum):
    """Operating state of the weaver between and during cycles."""
    RECORDING = "recording"
    LINKING = "linking"
    TRACING = "tracing"
    PRUNING = "pruning"
    EMITTED = "emitted"
    SATURATED = "saturated"


class WeaverVitality(Enum):
    """Overall vitality of the causal timeline ecosystem."""
    SILENT = "silent"          # no events yet
    FLOWING = "flowing"        # a healthy, simple timeline
    BRAIDED = "braided"        # many organized threads
    TANGLED = "tangled"        # too many loops or orphans
    OVERGROWN = "overgrown"    # timeline at capacity


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TimelineEvent:
    """A single event recorded on the causal timeline."""
    event_id: str
    kind: EventKind
    description: str
    cause_ids: List[str] = field(default_factory=list)
    effect_ids: List[str] = field(default_factory=list)
    link_strengths: Dict[str, LinkStrength] = field(default_factory=dict)
    region: str = ""
    timestamp: float = field(default_factory=time.time)
    note: str = ""


@dataclass
class CausalThread:
    """A chain of events sharing one root cause."""
    thread_id: str
    root_event_id: str
    member_event_ids: List[str] = field(default_factory=list)
    state: ThreadState = ThreadState.GROWING
    depth: int = 0
    note: str = ""


@dataclass
class FeedbackLoop:
    """A cycle in the cause to effect graph."""
    loop_id: str
    member_event_ids: List[str] = field(default_factory=list)
    state: LoopState = LoopState.FORMING
    intensity: float = 0.5            # 0.0-1.0
    note: str = ""


@dataclass
class WeaverCycleResult:
    """Summary of a single weave cycle, emitted by the EMIT phase."""
    cycle_count: int
    phase: str
    threads_traced: int
    loops_detected: int
    orphans_flagged: int
    edges_pruned: int
    mean_timeline_depth: float
    emitted_at: float


# =============================================================================
# Weaver
# =============================================================================

class EngineCausalTimelineWeaver:
    """
    Thread-safe singleton orchestrating the causal timeline weave.

    Usage:
        weaver = EngineCausalTimelineWeaver.get_instance()
        weaver.record_event("e1", kind="catalyst", description="the well ran dry",
                            cause_ids=[], region="village")
        weaver.record_event("e2", kind="occurrence", description="villagers quarrel",
                            cause_ids=["e1"], region="village",
                            link_strengths={"e1": "direct"})
        weaver.cycle()
        causal_map = weaver.get_causal_map()
    """

    _instance: Optional["EngineCausalTimelineWeaver"] = None
    _instance_lock = threading.Lock()
    _global_lock = threading.RLock()

    # Tuning constants
    _MAX_EVENTS = 500
    _MAX_THREADS = 128
    _MAX_LOOPS = 32
    _MAX_CAUSES_PER_EVENT = 8
    _MAX_EVENTS_LOG = 200
    _DECAY_THRESHOLD = 0.1
    _EDGE_DECAY_FACTOR = 0.95
    _STALE_THREAD_CYCLES = 3
    _COLLAPSE_THREAD_CYCLES = 8
    _DEFAULT_LINK_STRENGTH = LinkStrength.MODERATE

    def __init__(self) -> None:
        self._events: Dict[str, TimelineEvent] = {}
        self._threads: Dict[str, CausalThread] = {}
        self._loops: Dict[str, FeedbackLoop] = {}
        self._orphans: Set[str] = set()
        self._pending_event_ids: Deque[str] = deque()
        self._edge_weights: Dict[Tuple[str, str], float] = {}
        self._thread_last_growth: Dict[str, int] = {}
        self._prev_loop_signatures: Set[frozenset] = set()
        self._loop_signatures_seen: Set[frozenset] = set()
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=self._MAX_EVENTS_LOG)
        self._cycle_count: int = 0
        self._current_phase: WeaverPhase = WeaverPhase.RECORD
        self._state: WeaverState = WeaverState.RECORDING
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineCausalTimelineWeaver":
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
            "events_recorded": 0,
            "links_resolved": 0,
            "threads_traced": 0,
            "loops_detected": 0,
            "orphans_flagged": 0,
            "edges_pruned": 0,
            "mean_timeline_depth": 0.0,
            "last_cycle_at": 0.0,
            "uptime_started_at": time.time(),
            "last_cycle_time_ms": 0.0,
            "vitality": WeaverVitality.SILENT.value,
            "current_state": self._state.value,
        }

    def _update_stats(self, **kwargs: Any) -> None:
        self._stats.update(kwargs)
        self._stats["mean_timeline_depth"] = self._compute_mean_depth()
        self._stats["vitality"] = self._derive_vitality().value
        self._stats["current_state"] = self._state.value

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "event": event_type,
            "payload": payload,
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        })

    def _compute_mean_depth(self) -> float:
        if not self._threads:
            return 0.0
        return sum(t.depth for t in self._threads.values()) / len(self._threads)

    def _derive_vitality(self) -> WeaverVitality:
        n_events = len(self._events)
        n_threads = len(self._threads)
        n_loops = len(self._loops)
        n_orphans = len(self._orphans)
        if n_events == 0:
            return WeaverVitality.SILENT
        if n_events >= self._MAX_EVENTS:
            return WeaverVitality.OVERGROWN
        if n_loops >= 5 or n_orphans >= 10:
            return WeaverVitality.TANGLED
        if n_threads >= 4:
            return WeaverVitality.BRAIDED
        return WeaverVitality.FLOWING

    # -------------------------------------------------------------------------
    # Event Intake
    # -------------------------------------------------------------------------

    def record_event(self, event_id: str, kind: Union[str, EventKind],
                     description: str, cause_ids: Optional[List[str]] = None,
                     region: str = "",
                     link_strengths: Optional[Dict[str, Any]] = None,
                     note: str = "") -> Dict[str, Any]:
        """Record a new event on the causal timeline."""
        with self._global_lock:
            if event_id in self._events:
                return {"error": f"Event already exists: {event_id}"}
            # Normalize the event kind.
            if isinstance(kind, EventKind):
                event_kind = kind
            else:
                try:
                    event_kind = EventKind(str(kind).lower())
                except ValueError:
                    return {"error": f"Invalid kind: {kind}"}
            # Normalize cause ids and enforce the per-event cap.
            causes = list(cause_ids or [])
            if len(causes) > self._MAX_CAUSES_PER_EVENT:
                causes = causes[: self._MAX_CAUSES_PER_EVENT]
            # Normalize link strengths into the LinkStrength enum.
            parsed_strengths: Dict[str, LinkStrength] = {}
            if link_strengths:
                for cid, sval in link_strengths.items():
                    if cid not in causes:
                        continue
                    if isinstance(sval, LinkStrength):
                        parsed_strengths[cid] = sval
                    else:
                        try:
                            parsed_strengths[cid] = LinkStrength(str(sval).lower())
                        except ValueError:
                            parsed_strengths[cid] = self._DEFAULT_LINK_STRENGTH
            event = TimelineEvent(
                event_id=event_id,
                kind=event_kind,
                description=description,
                cause_ids=causes,
                effect_ids=[],
                link_strengths=parsed_strengths,
                region=region,
                timestamp=time.time(),
                note=note,
            )
            self._events[event_id] = event
            # Enforce the global event cap by dropping the oldest event.
            if len(self._events) > self._MAX_EVENTS:
                oldest_id = min(
                    self._events, key=lambda eid: self._events[eid].timestamp
                )
                self._remove_event_links(oldest_id)
                self._events.pop(oldest_id, None)
            self._pending_event_ids.append(event_id)
            self._stats["events_recorded"] = self._stats.get("events_recorded", 0) + 1
            self._record_event("event_recorded", {
                "event_id": event_id,
                "kind": event_kind.value,
                "region": region,
            })
            return {
                "event_id": event_id,
                "kind": event_kind.value,
                "description": description,
                "cause_ids": causes,
                "region": region,
                "link_strengths": {cid: s.value for cid, s in parsed_strengths.items()},
                "note": note,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single causal weave cycle through all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: List[Dict[str, Any]] = []
            self._state = WeaverState.RECORDING
            self._current_phase = WeaverPhase.RECORD
            phase_outputs.append(self._phase_record())
            self._state = WeaverState.LINKING
            self._current_phase = WeaverPhase.LINK
            phase_outputs.append(self._phase_link())
            self._state = WeaverState.TRACING
            self._current_phase = WeaverPhase.TRACE
            phase_outputs.append(self._phase_trace())
            self._state = WeaverState.PRUNING
            self._current_phase = WeaverPhase.PRUNE
            phase_outputs.append(self._phase_prune())
            self._state = WeaverState.EMITTED
            self._current_phase = WeaverPhase.EMIT
            phase_outputs.append(self._phase_emit())
            self._cycle_count += 1
            if len(self._events) >= self._MAX_EVENTS:
                self._state = WeaverState.SATURATED
            self._stats["cycles_completed"] = self._cycle_count
            self._stats["last_cycle_at"] = time.time()
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._current_phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_record(self) -> Dict[str, Any]:
        """Record phase: confirm newly recorded events into the timeline."""
        committed = len(self._pending_event_ids)
        pending_orphans = 0
        for eid in list(self._pending_event_ids):
            event = self._events.get(eid)
            if event is None:
                continue
            # An event with declared causes that are not yet present is a
            # pending orphan; it may resolve once its causes arrive.
            if event.cause_ids and not any(cid in self._events for cid in event.cause_ids):
                pending_orphans += 1
        self._record_event("phase_record", {
            "committed": committed,
            "pending_orphans": pending_orphans,
        })
        return {
            "phase": WeaverPhase.RECORD.value,
            "committed": committed,
            "pending_orphans": pending_orphans,
        }

    def _phase_link(self) -> Dict[str, Any]:
        """Link phase: resolve cause to effect edges for newly recorded events."""
        links_resolved = 0
        temporal_violations = 0
        new_event_ids: List[str] = []
        while self._pending_event_ids:
            new_event_ids.append(self._pending_event_ids.popleft())
        for eid in new_event_ids:
            event = self._events.get(eid)
            if event is None:
                continue
            for cid in event.cause_ids:
                if cid not in self._events:
                    continue
                cause = self._events[cid]
                if eid not in cause.effect_ids:
                    cause.effect_ids.append(eid)
                    links_resolved += 1
                # Attach a default link strength if none was declared.
                if cid not in event.link_strengths:
                    event.link_strengths[cid] = self._DEFAULT_LINK_STRENGTH
                strength = event.link_strengths.get(cid, self._DEFAULT_LINK_STRENGTH)
                self._edge_weights[(cid, eid)] = self._strength_weight(strength)
                # Validate temporal ordering: a cause cannot follow its effect.
                if cause.timestamp > event.timestamp:
                    temporal_violations += 1
        self._stats["links_resolved"] = self._stats.get("links_resolved", 0) + links_resolved
        self._record_event("phase_link", {
            "links_resolved": links_resolved,
            "temporal_violations": temporal_violations,
        })
        return {
            "phase": WeaverPhase.LINK.value,
            "links_resolved": links_resolved,
            "temporal_violations": temporal_violations,
        }

    def _phase_trace(self) -> Dict[str, Any]:
        """Trace phase: detect causal threads, feedback loops, and orphans."""
        # Orphans: events with declared causes where every cause is missing.
        orphans: Set[str] = set()
        for event in self._events.values():
            if event.cause_ids and not any(cid in self._events for cid in event.cause_ids):
                orphans.add(event.event_id)
        self._orphans = orphans

        # Threads: group events by their causal root (first valid cause chain).
        root_groups: Dict[str, List[str]] = {}
        for eid in self._events:
            root = self._find_root(eid)
            root_groups.setdefault(root, []).append(eid)

        new_threads: Dict[str, CausalThread] = {}
        for root_id, members in root_groups.items():
            # A real thread needs at least two events in its chain.
            if len(members) < 2:
                continue
            thread_id = f"thread_{root_id}"
            member_set = set(members)
            depth = self._chain_depth(root_id, member_set)
            prev = self._threads.get(thread_id)
            prev_count = len(prev.member_event_ids) if prev else 0
            if len(members) > prev_count:
                self._thread_last_growth[thread_id] = self._cycle_count
            last_growth = self._thread_last_growth.get(thread_id, self._cycle_count)
            root_event = self._events.get(root_id)
            root_is_orphan = (
                root_event is not None
                and root_event.cause_ids
                and not any(cid in self._events for cid in root_event.cause_ids)
            )
            if root_is_orphan:
                state = ThreadState.ORPHAN
            elif self._cycle_count - last_growth > self._COLLAPSE_THREAD_CYCLES:
                state = ThreadState.COLLAPSED
            elif self._cycle_count - last_growth > self._STALE_THREAD_CYCLES:
                state = ThreadState.DECAYING
            elif len(members) > prev_count:
                state = ThreadState.GROWING
            else:
                state = ThreadState.STABLE
            new_threads[thread_id] = CausalThread(
                thread_id=thread_id,
                root_event_id=root_id,
                member_event_ids=sorted(members),
                state=state,
                depth=depth,
                note=f"thread rooted at {root_id} with {len(members)} events",
            )
        # Enforce the thread cap by keeping the deepest threads.
        if len(new_threads) > self._MAX_THREADS:
            kept = sorted(new_threads.values(), key=lambda t: t.depth, reverse=True)
            new_threads = {t.thread_id: t for t in kept[: self._MAX_THREADS]}
        self._threads = new_threads

        # Loops: find strongly connected components in the cause to effect graph.
        sccs = self._detect_loops()
        current_signatures: Set[frozenset] = set()
        new_loops: Dict[str, FeedbackLoop] = {}
        for idx, scc in enumerate(sccs):
            signature = frozenset(scc)
            current_signatures.add(signature)
            intensity = self._estimate_loop_intensity(scc)
            if signature in self._prev_loop_signatures:
                loop_state = LoopState.REINFORCING
            elif intensity < 0.3:
                loop_state = LoopState.DAMPED
            elif signature not in self._loop_signatures_seen:
                loop_state = LoopState.FORMING
            else:
                loop_state = LoopState.CLOSED
            loop_id = f"loop_{self._cycle_count}_{idx}"
            new_loops[loop_id] = FeedbackLoop(
                loop_id=loop_id,
                member_event_ids=sorted(scc),
                state=loop_state,
                intensity=intensity,
                note=f"loop of {len(scc)} events",
            )
        if len(new_loops) > self._MAX_LOOPS:
            kept = sorted(new_loops.values(), key=lambda l: l.intensity, reverse=True)
            new_loops = {l.loop_id: l for l in kept[: self._MAX_LOOPS]}
        self._loops = new_loops
        self._loop_signatures_seen.update(current_signatures)

        self._stats["threads_traced"] = len(self._threads)
        self._stats["loops_detected"] = len(self._loops)
        self._stats["orphans_flagged"] = len(self._orphans)
        self._record_event("phase_trace", {
            "threads_traced": len(self._threads),
            "loops_detected": len(self._loops),
            "orphans_flagged": len(self._orphans),
        })
        return {
            "phase": WeaverPhase.TRACE.value,
            "threads_traced": len(self._threads),
            "loops_detected": len(self._loops),
            "orphans_flagged": len(self._orphans),
        }

    def _phase_prune(self) -> Dict[str, Any]:
        """Prune phase: decay stale edges, retire collapsed threads, compact."""
        edges_pruned = 0
        # Decay every edge weight; retire edges that fall below the threshold.
        stale: List[Tuple[str, str]] = []
        for edge, weight in list(self._edge_weights.items()):
            decayed = weight * self._EDGE_DECAY_FACTOR
            self._edge_weights[edge] = decayed
            if decayed < self._DECAY_THRESHOLD:
                stale.append(edge)
        for cause_id, effect_id in stale:
            self._edge_weights.pop((cause_id, effect_id), None)
            cause = self._events.get(cause_id)
            if cause and effect_id in cause.effect_ids:
                cause.effect_ids.remove(effect_id)
                edges_pruned += 1
            effect = self._events.get(effect_id)
            if effect:
                effect.link_strengths.pop(cause_id, None)

        # Retire collapsed threads.
        collapsed: List[str] = [
            tid for tid, t in self._threads.items()
            if t.state == ThreadState.COLLAPSED
        ]
        for tid in collapsed:
            self._threads.pop(tid, None)
            self._thread_last_growth.pop(tid, None)

        # Count loops that were present last cycle but are gone this cycle.
        current_loop_sigs = {
            frozenset(l.member_event_ids) for l in self._loops.values()
        }
        loops_broken = len(self._prev_loop_signatures - current_loop_sigs)
        self._prev_loop_signatures = current_loop_sigs

        # Compact the timeline if it exceeds the event cap.
        events_capped = 0
        if len(self._events) > self._MAX_EVENTS:
            ordered = sorted(self._events.values(), key=lambda e: e.timestamp)
            while len(self._events) > self._MAX_EVENTS and ordered:
                oldest = ordered.pop(0)
                self._remove_event_links(oldest.event_id)
                self._events.pop(oldest.event_id, None)
                events_capped += 1

        self._stats["edges_pruned"] = self._stats.get("edges_pruned", 0) + edges_pruned
        self._record_event("phase_prune", {
            "edges_pruned": edges_pruned,
            "threads_collapsed": len(collapsed),
            "loops_broken": loops_broken,
            "events_capped": events_capped,
        })
        return {
            "phase": WeaverPhase.PRUNE.value,
            "edges_pruned": edges_pruned,
            "threads_collapsed": len(collapsed),
            "loops_broken": loops_broken,
            "events_capped": events_capped,
        }

    def _phase_emit(self) -> Dict[str, Any]:
        """Emit phase: publish the current causal map for downstream queries."""
        causal_map = self.get_causal_map()
        cycle_result = WeaverCycleResult(
            cycle_count=self._cycle_count,
            phase=WeaverPhase.EMIT.value,
            threads_traced=len(self._threads),
            loops_detected=len(self._loops),
            orphans_flagged=len(self._orphans),
            edges_pruned=self._stats.get("edges_pruned", 0),
            mean_timeline_depth=self._compute_mean_depth(),
            emitted_at=time.time(),
        )
        self._record_event("phase_emit", {
            "threads": len(self._threads),
            "loops": len(self._loops),
            "orphans": len(self._orphans),
        })
        return {
            "phase": WeaverPhase.EMIT.value,
            "causal_map": causal_map,
            "cycle_result": asdict(cycle_result),
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _strength_weight(self, strength: LinkStrength) -> float:
        """Map a link strength to an edge weight used for decay tracking."""
        return {
            LinkStrength.DIRECT: 1.0,
            LinkStrength.STRONG: 0.85,
            LinkStrength.MODERATE: 0.65,
            LinkStrength.WEAK: 0.4,
            LinkStrength.TENUOUS: 0.2,
        }.get(strength, 0.5)

    def _remove_event_links(self, event_id: str) -> None:
        """Strip an event out of every edge it participates in."""
        event = self._events.get(event_id)
        if event:
            for cid in list(event.cause_ids):
                self._edge_weights.pop((cid, event_id), None)
                cause = self._events.get(cid)
                if cause and event_id in cause.effect_ids:
                    cause.effect_ids.remove(event_id)
            for eid in list(event.effect_ids):
                self._edge_weights.pop((event_id, eid), None)
                effect = self._events.get(eid)
                if effect:
                    effect.link_strengths.pop(event_id, None)

    def _find_root(self, event_id: str) -> str:
        """Walk the first valid cause chain backward to the root event."""
        visited: Set[str] = set()
        current = event_id
        while True:
            if current in visited:
                return current  # cycle in the cause chain; treat as root
            visited.add(current)
            event = self._events.get(current)
            if event is None or not event.cause_ids:
                return current
            next_id: Optional[str] = None
            for cid in event.cause_ids:
                if cid in self._events:
                    next_id = cid
                    break
            if next_id is None:
                return current  # orphan; no recorded cause exists
            current = next_id

    def _chain_depth(self, root_id: str, members: Set[str]) -> int:
        """Measure the longest forward chain from a root within a thread."""
        memo: Dict[str, int] = {}

        def dfs(node: str, visiting: Set[str]) -> int:
            if node in memo:
                return memo[node]
            if node in visiting:
                return 0  # cycle guard
            visiting.add(node)
            max_child = 0
            event = self._events.get(node)
            if event:
                for eid in event.effect_ids:
                    if eid in members:
                        depth = dfs(eid, visiting)
                        if depth > max_child:
                            max_child = depth
            visiting.discard(node)
            memo[node] = 1 + max_child
            return 1 + max_child

        if root_id not in members:
            return 0
        return dfs(root_id, set())

    def _detect_loops(self) -> List[List[str]]:
        """Find strongly connected components (cycles) in the cause graph."""
        index_counter = [0]
        stack: List[str] = []
        index: Dict[str, int] = {}
        lowlink: Dict[str, int] = {}
        on_stack: Dict[str, bool] = {}
        sccs: List[List[str]] = []

        def strongconnect(v: str) -> None:
            index[v] = index_counter[0]
            lowlink[v] = index_counter[0]
            index_counter[0] += 1
            stack.append(v)
            on_stack[v] = True
            event = self._events.get(v)
            successors = list(event.effect_ids) if event else []
            for w in successors:
                if w not in self._events:
                    continue
                if w not in index:
                    strongconnect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif on_stack.get(w):
                    lowlink[v] = min(lowlink[v], index[w])
            if lowlink[v] == index[v]:
                component: List[str] = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    component.append(w)
                    if w == v:
                        break
                # A component of size > 1 is a cycle; a self loop counts too.
                if len(component) > 1:
                    sccs.append(component)
                elif len(component) == 1:
                    node = component[0]
                    ev = self._events.get(node)
                    if ev and node in ev.effect_ids:
                        sccs.append(component)

        for vid in list(self._events.keys()):
            if vid not in index:
                strongconnect(vid)
        return sccs

    def _estimate_loop_intensity(self, members: List[str]) -> float:
        """Estimate the intensity of a feedback loop from its shape."""
        base = max(0.1, 1.0 - 0.15 * (len(members) - 2))
        # A small jitter so that equal-length loops are not perfectly tied.
        return max(0.05, min(1.0, base * (0.85 + 0.3 * random.random())))

    def _thread_dict(self, thread: CausalThread) -> Dict[str, Any]:
        return {
            "thread_id": thread.thread_id,
            "root_event_id": thread.root_event_id,
            "member_event_ids": list(thread.member_event_ids),
            "state": thread.state.value,
            "depth": thread.depth,
            "note": thread.note,
        }

    def _loop_dict(self, loop: FeedbackLoop) -> Dict[str, Any]:
        return {
            "loop_id": loop.loop_id,
            "member_event_ids": list(loop.member_event_ids),
            "state": loop.state.value,
            "intensity": loop.intensity,
            "note": loop.note,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_event(self, event_id: str) -> Dict[str, Any]:
        with self._global_lock:
            event = self._events.get(event_id)
            if event is None:
                return {"error": f"Event not found: {event_id}"}
            return {
                "event_id": event.event_id,
                "kind": event.kind.value,
                "description": event.description,
                "cause_ids": list(event.cause_ids),
                "effect_ids": list(event.effect_ids),
                "link_strengths": {
                    cid: s.value for cid, s in event.link_strengths.items()
                },
                "region": event.region,
                "timestamp": event.timestamp,
                "note": event.note,
            }

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        with self._global_lock:
            thread = self._threads.get(thread_id)
            if thread is None:
                return {"error": f"Thread not found: {thread_id}"}
            return self._thread_dict(thread)

    def get_causal_map(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "events_count": len(self._events),
                "threads": [self._thread_dict(t) for t in self._threads.values()],
                "loops": [self._loop_dict(l) for l in self._loops.values()],
                "orphans": sorted(self._orphans),
                "mean_timeline_depth": self._compute_mean_depth(),
                "vitality": self._derive_vitality().value,
            }

    def get_status(self) -> Dict[str, Any]:
        with self._global_lock:
            return {
                "phase": self._current_phase.value,
                "state": self._state.value,
                "cycle_count": self._cycle_count,
                "events": len(self._events),
                "threads": len(self._threads),
                "loops": len(self._loops),
                "orphans": len(self._orphans),
                "stats": dict(self._stats),
            }

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Seed synthetic events then run multiple weave cycles."""
        with self._global_lock:
            self._seed_synthetic_events()
            results: List[Dict[str, Any]] = []
            for _ in range(max(1, cycles)):
                results.append(self.cycle())
            return {
                "cycles_run": len(results),
                "results": results,
                "final_status": self.get_status(),
            }

    def _seed_synthetic_events(self) -> None:
        """Seed a small synthetic timeline with a chain and a feedback loop."""
        seed_events: List[Tuple[str, EventKind, str, List[str], str, Dict[str, str], str]] = [
            ("sim_ev1", EventKind.CATALYST, "the dam cracked",
             [], "sim_river", {}, "drought begins"),
            ("sim_ev2", EventKind.OCCURRENCE, "floods rush downstream",
             ["sim_ev1"], "sim_river", {"sim_ev1": "direct"}, "waters rise"),
            ("sim_ev3", EventKind.REACTION, "villagers flee the banks",
             ["sim_ev2"], "sim_village", {"sim_ev2": "strong"}, "exodus"),
            ("sim_ev4", EventKind.DECISION, "engineers commission a levee",
             ["sim_ev2"], "sim_river", {"sim_ev2": "moderate"}, "countermeasure"),
            ("sim_ev5", EventKind.TURNING_POINT, "the new levee holds",
             ["sim_ev4"], "sim_river", {"sim_ev4": "direct"}, "tide turns"),
            ("sim_ev6", EventKind.OCCURRENCE, "the floodwaters recede",
             ["sim_ev5", "sim_ev3"], "sim_river",
             {"sim_ev5": "strong", "sim_ev3": "weak"}, "recovery"),
            ("sim_ev7", EventKind.OCCURRENCE, "the temple bell tolls",
             ["sim_ev8"], "sim_temple", {"sim_ev8": "direct"}, "a loop forms"),
            ("sim_ev8", EventKind.OCCURRENCE, "the temple ward fades",
             ["sim_ev7"], "sim_temple", {"sim_ev7": "direct"}, "the loop closes"),
        ]
        for eid, kind, desc, causes, region, strengths, note in seed_events:
            if eid not in self._events:
                self.record_event(
                    eid, kind=kind, description=desc, cause_ids=causes,
                    region=region, link_strengths=strengths, note=note,
                )

    def reset(self) -> Dict[str, Any]:
        with self._global_lock:
            self._events.clear()
            self._threads.clear()
            self._loops.clear()
            self._orphans.clear()
            self._pending_event_ids.clear()
            self._edge_weights.clear()
            self._thread_last_growth.clear()
            self._prev_loop_signatures.clear()
            self._loop_signatures_seen.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._current_phase = WeaverPhase.RECORD
            self._state = WeaverState.RECORDING
            self._init_stats()
            return {"reset": True}

