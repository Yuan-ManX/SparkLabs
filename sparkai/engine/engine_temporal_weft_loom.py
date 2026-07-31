"""
SparkLabs Engine - Temporal Weft Loom

The EngineTemporalWeftLoom models time as a woven fabric where different
threads can flow at different rates, tangle with each other, or align
into synchronized moments. In a game world, time is not a single uniform
river - it is a loom with many threads, and the weaver (the engine) must
manage their tension, alignment, and occasional unraveling.

Each region, character, and subsystem can have its own temporal thread.
A mystical forest might flow slower than the bustling city. A time-lost
ruin might run backwards. Two bonded characters might experience aligned
time, where moments of importance happen simultaneously for both. When
threads tangle, cause and effect can loop or reverse - the engine must
detect and either resolve or embrace these tangles.

The loom also models temporal tension: the pull between different time
rates. High tension can cause "temporal fraying" where events become
unstable, or "temporal darning" where the engine repairs the fabric by
pulling threads back into alignment. This creates a dynamic temporal
landscape where time itself is a gameplay element.

Architecture:
  WARP     ->  WEFT      ->  TENSION    ->  DARN     ->  UNRAVEL
  (thread    (cross-       (measure       (repair      (allow old
   the       thread        and adjust     frayed       threads to
   vertical  connections   tension        sections     come loose
   time      between       between        by pulling   and dissolve
   threads   threads)      threads)       them tight)   into potential)

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
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class LoomPhase(Enum):
    """Phases of the temporal weft cycle."""
    WARP = "warp"                 # thread vertical time threads
    WEFT = "weft"                 # cross-thread connections between threads
    TENSION = "tension"           # measure and adjust tension
    DARN = "darn"                 # repair frayed sections
    UNRAVEL = "unravel"           # allow old threads to come loose


class ThreadDirection(Enum):
    """Direction of temporal flow."""
    FORWARD = "forward"           # normal time flow
    REVERSE = "reverse"           # backwards time
    STATIC = "static"             # frozen time
    LOOP = "loop"                 # repeating time
    BRANCHING = "branching"       # splitting into parallel timelines


class ThreadState(Enum):
    """State of a temporal thread."""
    STABLE = "stable"             # flowing smoothly
    TAUT = "taut"                 # under high tension
    SLACK = "slack"               # under low tension, drifting
    FRAYED = "frayed"             # edges unraveling
    TANGLED = "tangled"           # knotted with other threads
    SEVERED = "severed"           # cut, no longer flowing


class TangleType(Enum):
    """Types of temporal tangles that can form."""
    CAUSAL_LOOP = "causal_loop"           # cause becomes its own effect
    PARADOX = "paradox"                   # contradiction in timeline
    ECHO = "echo"                         # event repeating across threads
    PREMONITION = "premonition"           # future event rippling backward
    DEJA_VU = "deja_vu"                   # past event recurring


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TemporalThread:
    """A single thread of time in the world."""
    thread_id: str
    label: str
    region: str
    direction: ThreadDirection = ThreadDirection.FORWARD
    state: ThreadState = ThreadState.STABLE
    flow_rate: float = 1.0          # multiplier on global time (1.0 = normal)
    position: float = 0.0           # current temporal position
    tension: float = 0.3            # 0.0-1.0
    entropy: float = 0.0            # 0.0-1.0: disorder accumulated
    created_at: float = field(default_factory=time.time)
    last_woven: float = field(default_factory=time.time)
    cross_threads: Set[str] = field(default_factory=set)
    significant_events: int = 0


@dataclass
class WeftConnection:
    """A cross-connection between two temporal threads."""
    weft_id: str
    thread_a: str
    thread_b: str
    alignment: float = 0.5          # 0.0-1.0: how synchronized
    strength: float = 0.3           # 0.0-1.0: bond strength
    resonance: float = 0.0          # 0.0-1.0: shared significant moments
    bidirectional: bool = True


@dataclass
class TemporalTangle:
    """A detected tangle in the temporal fabric."""
    tangle_id: str
    tangle_type: TangleType
    thread_ids: List[str]
    severity: float                 # 0.0-1.0
    resolved: bool = False
    resolution: str = ""            # "smoothed", "embraced", "severed"
    description: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class SignificantMoment:
    """A moment of temporal significance recorded on the loom."""
    moment_id: str
    thread_id: str
    label: str
    importance: float               # 0.0-1.0
    temporal_position: float
    echoed_to: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# Engine
# =============================================================================

class EngineTemporalWeftLoom:
    """
    Thread-safe singleton for the temporal weft loom.

    Usage:
        loom = EngineTemporalWeftLoom.get_instance()
        loom.spawn_thread("t_forest", "Mystic Forest", "forest",
                          ThreadDirection.FORWARD, flow_rate=0.5)
        loom.spawn_thread("t_city", "Bustling City", "city",
                          ThreadDirection.FORWARD, flow_rate=1.5)
        loom.weave_weft("t_forest", "t_city", alignment=0.3, strength=0.4)
        loom.record_moment("m_1", "t_forest", "Ancient Awakens", 0.9)
        loom.cycle()
    """

    _instance: Optional["EngineTemporalWeftLoom"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._threads: Dict[str, TemporalThread] = {}
        self._wefts: Dict[str, WeftConnection] = {}
        self._tangles: Deque[TemporalTangle] = deque(maxlen=100)
        self._moments: Deque[SignificantMoment] = deque(maxlen=200)
        self._phase: LoomPhase = LoomPhase.WARP
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_threads": 0,
            "total_wefts": 0,
            "total_tangles": 0,
            "total_moments": 0,
            "stable_threads": 0,
            "frayed_threads": 0,
            "tangled_threads": 0,
            "resolved_tangles": 0,
            "avg_tension": 0.0,
            "avg_flow_rate": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineTemporalWeftLoom":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Thread Management
    # -------------------------------------------------------------------------

    def spawn_thread(
        self,
        thread_id: str,
        label: str,
        region: str,
        direction: ThreadDirection = ThreadDirection.FORWARD,
        flow_rate: float = 1.0,
    ) -> Dict[str, Any]:
        """Spawn a new temporal thread."""
        with self._global_lock:
            if thread_id in self._threads:
                return {"error": f"Thread already exists: {thread_id}"}
            thread = TemporalThread(
                thread_id=thread_id,
                label=label,
                region=region,
                direction=direction,
                flow_rate=max(0.01, flow_rate),
            )
            self._threads[thread_id] = thread
            self._stats["total_threads"] = len(self._threads)
            self._record_event("thread_spawned", {
                "thread_id": thread_id, "region": region, "direction": direction.value,
            })
            return {
                "thread_id": thread_id,
                "label": label,
                "region": region,
                "direction": direction.value,
                "flow_rate": thread.flow_rate,
            }

    def remove_thread(self, thread_id: str) -> Dict[str, Any]:
        """Remove a temporal thread."""
        with self._global_lock:
            if thread_id not in self._threads:
                return {"error": f"Thread not found: {thread_id}"}
            # Remove weft connections
            to_remove = [
                wid for wid, w in self._wefts.items()
                if w.thread_a == thread_id or w.thread_b == thread_id
            ]
            for wid in to_remove:
                other = self._wefts[wid].thread_b if self._wefts[wid].thread_a == thread_id else self._wefts[wid].thread_a
                if other in self._threads:
                    self._threads[other].cross_threads.discard(thread_id)
                del self._wefts[wid]
            del self._threads[thread_id]
            self._stats["total_threads"] = len(self._threads)
            self._stats["total_wefts"] = len(self._wefts)
            return {"removed": thread_id, "removed_wefts": len(to_remove)}

    def list_threads(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all temporal threads."""
        with self._global_lock:
            return [self._summarize_thread(t) for t in list(self._threads.values())[:limit]]

    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get full details of a temporal thread."""
        with self._global_lock:
            t = self._threads.get(thread_id)
            if t is None:
                return None
            return {
                "thread_id": t.thread_id,
                "label": t.label,
                "region": t.region,
                "direction": t.direction.value,
                "state": t.state.value,
                "flow_rate": t.flow_rate,
                "position": round(t.position, 4),
                "tension": round(t.tension, 4),
                "entropy": round(t.entropy, 4),
                "significant_events": t.significant_events,
                "cross_threads": list(t.cross_threads),
            }

    # -------------------------------------------------------------------------
    # Weft Management
    # -------------------------------------------------------------------------

    def weave_weft(
        self,
        thread_a: str,
        thread_b: str,
        alignment: float = 0.5,
        strength: float = 0.3,
        bidirectional: bool = True,
    ) -> Dict[str, Any]:
        """Weave a weft connection between two threads."""
        with self._global_lock:
            if thread_a not in self._threads:
                return {"error": f"Thread not found: {thread_a}"}
            if thread_b not in self._threads:
                return {"error": f"Thread not found: {thread_b}"}
            if thread_a == thread_b:
                return {"error": "Cannot weave a thread to itself"}
            weft_id = f"weft_{thread_a}_{thread_b}_{int(time.time() * 1000) % 100000}"
            weft = WeftConnection(
                weft_id=weft_id,
                thread_a=thread_a,
                thread_b=thread_b,
                alignment=max(0.0, min(1.0, alignment)),
                strength=max(0.0, min(1.0, strength)),
                bidirectional=bidirectional,
            )
            self._wefts[weft_id] = weft
            self._threads[thread_a].cross_threads.add(thread_b)
            self._threads[thread_b].cross_threads.add(thread_a)
            self._stats["total_wefts"] = len(self._wefts)
            self._record_event("weft_woven", {
                "weft_id": weft_id, "thread_a": thread_a, "thread_b": thread_b,
            })
            return {
                "weft_id": weft_id,
                "thread_a": thread_a,
                "thread_b": thread_b,
                "alignment": weft.alignment,
                "strength": weft.strength,
            }

    def list_wefts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all weft connections."""
        with self._global_lock:
            return [
                {
                    "weft_id": w.weft_id,
                    "thread_a": w.thread_a,
                    "thread_b": w.thread_b,
                    "alignment": round(w.alignment, 4),
                    "strength": round(w.strength, 4),
                    "resonance": round(w.resonance, 4),
                    "bidirectional": w.bidirectional,
                }
                for w in list(self._wefts.values())[:limit]
            ]

    # -------------------------------------------------------------------------
    # Moment Recording
    # -------------------------------------------------------------------------

    def record_moment(
        self,
        moment_id: str,
        thread_id: str,
        label: str,
        importance: float = 0.5,
    ) -> Dict[str, Any]:
        """Record a significant moment on a temporal thread."""
        with self._global_lock:
            if thread_id not in self._threads:
                return {"error": f"Thread not found: {thread_id}"}
            thread = self._threads[thread_id]
            moment = SignificantMoment(
                moment_id=moment_id,
                thread_id=thread_id,
                label=label,
                importance=max(0.0, min(1.0, importance)),
                temporal_position=thread.position,
            )
            self._moments.append(moment)
            thread.significant_events += 1
            self._stats["total_moments"] = len(self._moments)
            self._record_event("moment_recorded", {
                "moment_id": moment_id, "thread_id": thread_id, "importance": importance,
            })
            return {
                "moment_id": moment_id,
                "thread_id": thread_id,
                "label": label,
                "importance": moment.importance,
                "temporal_position": round(moment.temporal_position, 4),
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single temporal weft cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = LoomPhase.WARP
            phase_outputs["warp"] = self._phase_warp()
            self._phase = LoomPhase.WEFT
            phase_outputs["weft"] = self._phase_weft()
            self._phase = LoomPhase.TENSION
            phase_outputs["tension"] = self._phase_tension()
            self._phase = LoomPhase.DARN
            phase_outputs["darn"] = self._phase_darn()
            self._phase = LoomPhase.UNRAVEL
            phase_outputs["unravel"] = self._phase_unravel()
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

    def _phase_warp(self) -> Dict[str, Any]:
        """WARP: advance each thread according to its flow rate and direction."""
        warped = 0
        for thread in self._threads.values():
            if thread.state == ThreadState.SEVERED:
                continue
            # Advance position based on flow rate and direction
            if thread.direction == ThreadDirection.FORWARD:
                thread.position += thread.flow_rate
            elif thread.direction == ThreadDirection.REVERSE:
                thread.position -= thread.flow_rate
            elif thread.direction == ThreadDirection.STATIC:
                pass  # No movement
            elif thread.direction == ThreadDirection.LOOP:
                thread.position += thread.flow_rate
                # Loop back after reaching a threshold
                if thread.position > 100.0:
                    thread.position = 0.0
            elif thread.direction == ThreadDirection.BRANCHING:
                thread.position += thread.flow_rate * 0.5
                # Branching threads accumulate entropy faster
                thread.entropy = min(1.0, thread.entropy + 0.01)
            thread.last_woven = time.time()
            warped += 1
        return {"warped": warped}

    def _phase_weft(self) -> Dict[str, Any]:
        """WEFT: cross-threads pull each other toward alignment."""
        reinforced = 0
        echoed = 0
        for weft in self._wefts.values():
            ta = self._threads.get(weft.thread_a)
            tb = self._threads.get(weft.thread_b)
            if ta is None or tb is None:
                continue
            if ta.state == ThreadState.SEVERED or tb.state == ThreadState.SEVERED:
                continue
            # Aligned threads influence each other's flow rate
            pull = weft.alignment * weft.strength * 0.1
            avg_rate = (ta.flow_rate + tb.flow_rate) / 2.0
            ta.flow_rate = ta.flow_rate * (1 - pull) + avg_rate * pull
            tb.flow_rate = tb.flow_rate * (1 - pull) + avg_rate * pull
            reinforced += 1
            # Check for echo: significant moments on one thread affect the other
            recent_moments = [
                m for m in self._moments
                if m.thread_id in (weft.thread_a, weft.thread_b)
                and m.moment_id not in m.echoed_to
            ]
            for moment in recent_moments[-5:]:
                if moment.importance > 0.6 and weft.resonance > 0.3:
                    # Echo the moment to the other thread
                    target_thread = weft.thread_b if moment.thread_id == weft.thread_a else weft.thread_a
                    echo_id = f"echo_{moment.moment_id}_{target_thread}"
                    target = self._threads.get(target_thread)
                    if target:
                        echo_moment = SignificantMoment(
                            moment_id=echo_id,
                            thread_id=target_thread,
                            label=f"Echo: {moment.label}",
                            importance=moment.importance * weft.resonance,
                            temporal_position=target.position,
                            echoed_to=[moment.moment_id],
                        )
                        self._moments.append(echo_moment)
                        moment.echoed_to.append(echo_id)
                        echoed += 1
            # Increase resonance from shared moments
            weft.resonance = min(1.0, weft.resonance + 0.01)
        self._stats["total_moments"] = len(self._moments)
        return {"reinforced": reinforced, "echoed": echoed}

    def _phase_tension(self) -> Dict[str, Any]:
        """TENSION: measure and adjust tension between threads."""
        adjusted = 0
        tangles_detected = 0
        for weft in self._wefts.values():
            ta = self._threads.get(weft.thread_a)
            tb = self._threads.get(weft.thread_b)
            if ta is None or tb is None:
                continue
            # Tension arises from flow rate differences
            rate_diff = abs(ta.flow_rate - tb.flow_rate)
            # Tension also from direction conflicts
            if ta.direction != tb.direction and ta.direction != ThreadDirection.STATIC and tb.direction != ThreadDirection.STATIC:
                rate_diff += 0.5
            # Update tension on threads
            base_tension = rate_diff * weft.strength * 0.3
            ta.tension = min(1.0, ta.tension * 0.9 + base_tension * 0.1)
            tb.tension = min(1.0, tb.tension * 0.9 + base_tension * 0.1)
            # State transitions based on tension
            if ta.tension > 0.7 and ta.state == ThreadState.STABLE:
                ta.state = ThreadState.TAUT
            elif ta.tension < 0.3 and ta.state == ThreadState.TAUT:
                ta.state = ThreadState.STABLE
            elif ta.tension < 0.1 and ta.state == ThreadState.STABLE:
                ta.state = ThreadState.SLACK
            if tb.tension > 0.7 and tb.state == ThreadState.STABLE:
                tb.state = ThreadState.TAUT
            elif tb.tension < 0.3 and tb.state == ThreadState.TAUT:
                tb.state = ThreadState.STABLE
            elif tb.tension < 0.1 and tb.state == ThreadState.STABLE:
                tb.state = ThreadState.SLACK
            # Detect tangles when tension is very high
            if ta.tension > 0.8 and tb.tension > 0.8:
                tangle_type = random.choice(list(TangleType))
                tangle = TemporalTangle(
                    tangle_id=f"tangle_{weft.weft_id}_{int(time.time() * 1000) % 100000}",
                    tangle_type=tangle_type,
                    thread_ids=[weft.thread_a, weft.thread_b],
                    severity=(ta.tension + tb.tension) / 2.0,
                    description=f"{tangle_type.value} between {weft.thread_a} and {weft.thread_b}",
                )
                self._tangles.append(tangle)
                tangles_detected += 1
                ta.state = ThreadState.TANGLED
                tb.state = ThreadState.TANGLED
                # Attempt resolution
                self._resolve_tangle(tangle, ta, tb)
            adjusted += 1
        self._stats["total_tangles"] = len(self._tangles)
        return {"adjusted": adjusted, "tangles_detected": tangles_detected}

    def _resolve_tangle(self, tangle: TemporalTangle, ta: TemporalThread, tb: TemporalThread) -> None:
        """Attempt to resolve a temporal tangle."""
        resolve_chance = 0.4 + (1.0 - tangle.severity) * 0.3
        if random.random() < resolve_chance:
            # Smoothed: tension reduced, threads realign
            tangle.resolved = True
            tangle.resolution = "smoothed"
            ta.tension = max(0.0, ta.tension * 0.3)
            tb.tension = max(0.0, tb.tension * 0.3)
            ta.state = ThreadState.STABLE
            tb.state = ThreadState.STABLE
            self._stats["resolved_tangles"] += 1
        elif random.random() < 0.3:
            # Embraced: tangle becomes a feature, threads remain tangled but stable
            tangle.resolved = True
            tangle.resolution = "embraced"
            ta.state = ThreadState.STABLE
            tb.state = ThreadState.STABLE
            ta.entropy = min(1.0, ta.entropy + 0.1)
            tb.entropy = min(1.0, tb.entropy + 0.1)
            self._stats["resolved_tangles"] += 1
        else:
            # Severed: weft connection cut to save the threads
            tangle.resolved = True
            tangle.resolution = "severed"
            ta.state = ThreadState.FRAYED
            tb.state = ThreadState.FRAYED
            ta.tension = max(0.0, ta.tension * 0.5)
            tb.tension = max(0.0, tb.tension * 0.5)
            self._stats["resolved_tangles"] += 1

    def _phase_darn(self) -> Dict[str, Any]:
        """DARN: repair frayed sections by pulling threads back toward stability."""
        darned = 0
        for thread in self._threads.values():
            if thread.state == ThreadState.FRAYED:
                # Darning reduces entropy and restores stability
                thread.entropy = max(0.0, thread.entropy - 0.05)
                if thread.entropy < 0.3:
                    thread.state = ThreadState.STABLE
                    darned += 1
            elif thread.state == ThreadState.SLACK:
                # Slack threads are gently pulled taut
                thread.tension = min(1.0, thread.tension + 0.05)
                if thread.tension > 0.15:
                    thread.state = ThreadState.STABLE
                    darned += 1
            elif thread.state == ThreadState.TANGLED:
                # Tangled threads slowly untangle if tension is low
                if thread.tension < 0.4:
                    thread.state = ThreadState.STABLE
                    darned += 1
        return {"darned": darned}

    def _phase_unravel(self) -> Dict[str, Any]:
        """UNRAVEL: allow old, low-tension threads to accumulate entropy and dissolve."""
        unraveled = 0
        for thread in self._threads.values():
            if thread.state == ThreadState.SEVERED:
                continue
            # All threads slowly accumulate entropy
            thread.entropy = min(1.0, thread.entropy + 0.002)
            # High-entropy threads with low tension become frayed
            if thread.entropy > 0.7 and thread.tension < 0.2 and thread.state == ThreadState.STABLE:
                thread.state = ThreadState.FRAYED
                unraveled += 1
        return {"unraveled": unraveled}

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get global loom status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_threads": len(self._threads),
                "total_wefts": len(self._wefts),
                "total_tangles": len(self._tangles),
                "total_moments": len(self._moments),
                "stats": dict(self._stats),
            }

    def get_tangles(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent temporal tangles."""
        with self._global_lock:
            return [
                {
                    "tangle_id": t.tangle_id,
                    "tangle_type": t.tangle_type.value,
                    "thread_ids": t.thread_ids,
                    "severity": round(t.severity, 4),
                    "resolved": t.resolved,
                    "resolution": t.resolution,
                    "description": t.description,
                }
                for t in list(self._tangles)[-limit:]
            ]

    def get_moments(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent significant moments."""
        with self._global_lock:
            return [
                {
                    "moment_id": m.moment_id,
                    "thread_id": m.thread_id,
                    "label": m.label,
                    "importance": round(m.importance, 4),
                    "temporal_position": round(m.temporal_position, 4),
                    "echoed_to": m.echoed_to,
                }
                for m in list(self._moments)[-limit:]
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent loom events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire loom."""
        with self._global_lock:
            n_threads = len(self._threads)
            n_wefts = len(self._wefts)
            self._threads.clear()
            self._wefts.clear()
            self._tangles.clear()
            self._moments.clear()
            self._phase = LoomPhase.WARP
            self._cycle_count = 0
            self._events_log.clear()
            self._stats = {
                "total_threads": 0,
                "total_wefts": 0,
                "total_tangles": 0,
                "total_moments": 0,
                "stable_threads": 0,
                "frayed_threads": 0,
                "tangled_threads": 0,
                "resolved_tangles": 0,
                "avg_tension": 0.0,
                "avg_flow_rate": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "cleared_threads": n_threads, "cleared_wefts": n_wefts}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        """Update aggregate statistics."""
        threads = list(self._threads.values())
        self._stats["stable_threads"] = sum(1 for t in threads if t.state == ThreadState.STABLE)
        self._stats["frayed_threads"] = sum(1 for t in threads if t.state == ThreadState.FRAYED)
        self._stats["tangled_threads"] = sum(1 for t in threads if t.state == ThreadState.TANGLED)
        if threads:
            self._stats["avg_tension"] = sum(t.tension for t in threads) / len(threads)
            self._stats["avg_flow_rate"] = sum(t.flow_rate for t in threads) / len(threads)
        else:
            self._stats["avg_tension"] = 0.0
            self._stats["avg_flow_rate"] = 0.0

    def _summarize_thread(self, t: TemporalThread) -> Dict[str, Any]:
        """Summarize a thread for listing."""
        return {
            "thread_id": t.thread_id,
            "label": t.label,
            "region": t.region,
            "direction": t.direction.value,
            "state": t.state.value,
            "flow_rate": round(t.flow_rate, 4),
            "position": round(t.position, 4),
            "tension": round(t.tension, 4),
            "entropy": round(t.entropy, 4),
            "cross_thread_count": len(t.cross_threads),
            "significant_events": t.significant_events,
        }

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a loom event."""
        self._events_log.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
