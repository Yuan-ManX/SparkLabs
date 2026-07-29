"""
SparkLabs Engine - Kinetic Narrative Forge

The EngineKineticNarrativeForge models how narrative events carry kinetic
energy - momentum that builds, accelerates, deflects, collides, and
tempers into coherent story direction. A story is not a static sequence
of plot points; it is a dynamic system where events have mass and
velocity, where narrative momentum accumulates and drives the story
forward, and where the collision of competing story threads produces
dramatic sparks.

A story with no momentum stalls; a story with too much momentum
careens out of control. The forge treats narrative as a physical
system: events have mass (importance/weight), velocity (narrative
direction), and momentum (mass times velocity). When two story threads
collide, their momenta interact - they may merge into a stronger
thread, deflect into new directions, or shatter into fragments.

The forge models five forces:
  - Igniting: narrative events are ignited with initial kinetic energy,
    establishing their mass (dramatic weight) and velocity (direction)
  - Accelerating: as events accumulate, narrative momentum accelerates -
    the story builds toward climax
  - Deflecting: when narrative threads encounter obstacles, they
    deflect - branching into new story directions
  - Colliding: when two narrative threads meet, they collide -
    producing dramatic sparks, mergers, or shattering
  - Tempering: raw narrative momentum is tempered into coherent
    direction - the story's trajectory stabilizes

This produces stories with genuine narrative physics - where a slow
build of small events accumulates into unstoppable momentum, where a
sudden collision of story threads creates explosive dramatic energy,
and where the story's direction emerges from the interaction of
competing narrative forces rather than from a predetermined plot.

Architecture:
  IGNITE     ->  ACCELERATE  ->  DEFLECT   ->  COLLIDE   ->  TEMPER
  (narrative   (accumulated    (threads      (competing     (raw
   events       events          encounter     threads        momentum
   ignited      accelerate      obstacles     collide -      tempered
   with mass    the story       and branch    mergers,       into
   and          toward          into new      sparks, or     coherent
   velocity)    climax)         directions)   shattering)    direction)

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

class ForgePhase(Enum):
    """Phases of the kinetic narrative forge cycle."""
    IGNITE = "ignite"           # ignite events with kinetic energy
    ACCELERATE = "accelerate"   # accumulate narrative momentum
    DEFLECT = "deflect"         # branch threads around obstacles
    COLLIDE = "collide"         # collide competing threads
    TEMPER = "temper"           # temper momentum into direction


class NarrativeMass(Enum):
    """The dramatic weight/mass of a narrative event."""
    TRIVIAL = "trivial"         # minor, low impact
    MINOR = "minor"             # small but noticeable
    MODERATE = "moderate"       # meaningful contribution
    MAJOR = "major"             # significant turning point
    CRITICAL = "critical"       # story-defining moment
    CATASTROPHIC = "catastrophic"  # world-altering event


class ThreadState(Enum):
    """State of a narrative thread."""
    IGNITED = "ignited"         # just started, has initial energy
    ACCELERATING = "accelerating"  # gaining momentum
    DEFLECTED = "deflected"     # changed direction by obstacle
    COLLIDING = "colliding"     # currently colliding with another thread
    MERGED = "merged"           # merged into another thread
    SHATTERED = "shattered"     # broken into fragments
    TEMPERED = "tempered"       # stabilized into coherent direction
    DORMANT = "dormant"         # lost all momentum


class CollisionOutcome(Enum):
    """Outcome of a narrative thread collision."""
    MERGER = "merger"           # threads merge into one stronger thread
    SPARK = "spark"             # collision produces dramatic energy
    SHATTER = "shatter"         # one or both threads shatter
    DEFLECTION = "deflection"   # threads bounce off each other
    ANNIHILATION = "annihilation"  # both threads cancel out


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NarrativeEvent:
    """A narrative event with kinetic energy."""
    event_id: str
    label: str
    mass: NarrativeMass
    velocity: float             # narrative direction (0-1 scale)
    momentum: float             # mass_value * velocity
    thread_id: str              # which thread it belongs to
    description: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class NarrativeThread:
    """A thread of narrative with accumulated momentum."""
    thread_id: str
    label: str
    # Current momentum (accumulated)
    momentum: float = 0.0
    # Current direction (0-1, where it's heading)
    direction: float = 0.5
    # Number of events in this thread
    event_count: int = 0
    # State of the thread
    state: ThreadState = ThreadState.IGNITED
    # Mass class (highest mass event in thread)
    dominant_mass: NarrativeMass = NarrativeMass.MINOR
    # Events in this thread
    event_ids: List[str] = field(default_factory=list)
    # Velocity (rate of narrative advance)
    velocity: float = 0.0
    # Whether this thread has been deflected
    deflection_count: int = 0
    # Whether this thread has collided
    collision_count: int = 0
    # Tempered direction (after tempering)
    tempered_direction: Optional[float] = None
    # Sparks produced by collisions
    spark_energy: float = 0.0
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)


@dataclass
class Collision:
    """Record of a collision between two narrative threads."""
    collision_id: str
    thread_a: str
    thread_b: str
    outcome: CollisionOutcome
    spark_energy: float
    surviving_thread: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class NarrativeObstacle:
    """An obstacle that deflects narrative threads."""
    obstacle_id: str
    label: str
    # How strongly it deflects (0-1)
    deflection_strength: float = 0.5
    # New direction it pushes threads toward
    redirect_direction: float = 0.5
    created_at: float = field(default_factory=time.time)


# =============================================================================
# Kinetic Narrative Forge Engine
# =============================================================================

class EngineKineticNarrativeForge:
    """
    Thread-safe singleton orchestrating kinetic narrative momentum.

    Usage:
        forge = EngineKineticNarrativeForge.get_instance()
        forge.ignite_event("ev_call", "The Call to Adventure",
                           NarrativeMass.MAJOR, velocity=0.7, thread_id="th_hero")
        forge.ignite_event("ev_mentor", "Meeting the Mentor",
                           NarrativeMass.MODERATE, velocity=0.5, thread_id="th_hero")
        forge.ignite_event("ev_rival", "Rival Appears",
                           NarrativeMass.MAJOR, velocity=0.3, thread_id="th_rival")
        forge.place_obstacle("ob_choice", "Impossible Choice",
                            deflection_strength=0.8, redirect_direction=0.9)
        forge.cycle()
    """

    _instance: Optional["EngineKineticNarrativeForge"] = None
    _lock = threading.RLock()

    # Mass value mapping (numerical weight for each mass class)
    _MASS_VALUES = {
        NarrativeMass.TRIVIAL: 0.1,
        NarrativeMass.MINOR: 0.3,
        NarrativeMass.MODERATE: 0.5,
        NarrativeMass.MAJOR: 0.7,
        NarrativeMass.CRITICAL: 0.9,
        NarrativeMass.CATASTROPHIC: 1.0,
    }
    # How much each event accelerates its thread
    _ACCELERATION_FACTOR = 0.15
    # Momentum decay per cycle (threads lose energy)
    _MOMENTUM_DECAY = 0.05
    # Threshold for collision detection (directions must be close enough)
    _COLLISION_PROXIMITY = 0.3
    # Threshold for a thread to be considered dormant
    _DORMANT_THRESHOLD = 0.05
    # Minimum momentum for tempering
    _TEMPER_THRESHOLD = 0.3
    # How much spark energy a collision produces
    _SPARK_FACTOR = 0.5

    def __init__(self) -> None:
        self._events: Dict[str, NarrativeEvent] = {}
        self._threads: Dict[str, NarrativeThread] = {}
        self._obstacles: Dict[str, NarrativeObstacle] = {}
        self._collisions: Deque[Collision] = deque(maxlen=100)
        self._phase: ForgePhase = ForgePhase.IGNITE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {
            "total_events": 0,
            "total_threads": 0,
            "total_obstacles": 0,
            "total_collisions": 0,
            "mergers": 0,
            "sparks": 0,
            "shatters": 0,
            "deflections": 0,
            "annihilations": 0,
            "tempered_threads": 0,
            "dormant_threads": 0,
            "total_momentum": 0.0,
            "total_spark_energy": 0.0,
            "avg_momentum": 0.0,
            "max_momentum": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineKineticNarrativeForge":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Event & Thread Management
    # -------------------------------------------------------------------------

    def ignite_event(
        self,
        event_id: str,
        label: str,
        mass: NarrativeMass,
        velocity: float = 0.5,
        thread_id: str = "default",
        description: str = "",
    ) -> Dict[str, Any]:
        """Ignite a new narrative event with kinetic energy."""
        with self._global_lock:
            if event_id in self._events:
                return {"error": f"Event already exists: {event_id}"}
            velocity = max(0.0, min(1.0, velocity))
            mass_value = self._MASS_VALUES.get(mass, 0.5)
            momentum = mass_value * velocity
            event = NarrativeEvent(
                event_id=event_id,
                label=label,
                mass=mass,
                velocity=velocity,
                momentum=momentum,
                thread_id=thread_id,
                description=description,
            )
            self._events[event_id] = event
            # Get or create thread
            thread = self._threads.get(thread_id)
            if thread is None:
                thread = NarrativeThread(
                    thread_id=thread_id,
                    label=f"Thread {thread_id}",
                )
                self._threads[thread_id] = thread
            # Add event to thread
            thread.event_ids.append(event_id)
            thread.event_count += 1
            thread.momentum += momentum
            thread.velocity = velocity
            thread.direction = velocity  # direction follows latest velocity
            thread.last_updated = time.time()
            # Update dominant mass
            if self._MASS_VALUES.get(mass, 0) > self._MASS_VALUES.get(thread.dominant_mass, 0):
                thread.dominant_mass = mass
            if thread.state == ThreadState.IGNITED:
                thread.state = ThreadState.ACCELERATING
            self._record_event("event_ignited", {
                "event_id": event_id,
                "label": label,
                "mass": mass.value,
                "velocity": velocity,
                "thread_id": thread_id,
                "momentum": round(momentum, 4),
            })
            return {
                "event_id": event_id,
                "label": label,
                "mass": mass.value,
                "velocity": velocity,
                "momentum": round(momentum, 4),
                "thread_id": thread_id,
                "thread_momentum": round(thread.momentum, 4),
            }

    def place_obstacle(
        self,
        obstacle_id: str,
        label: str,
        deflection_strength: float = 0.5,
        redirect_direction: float = 0.5,
    ) -> Dict[str, Any]:
        """Place an obstacle that will deflect narrative threads."""
        with self._global_lock:
            if obstacle_id in self._obstacles:
                return {"error": f"Obstacle already exists: {obstacle_id}"}
            obstacle = NarrativeObstacle(
                obstacle_id=obstacle_id,
                label=label,
                deflection_strength=max(0.0, min(1.0, deflection_strength)),
                redirect_direction=max(0.0, min(1.0, redirect_direction)),
            )
            self._obstacles[obstacle_id] = obstacle
            self._record_event("obstacle_placed", {
                "obstacle_id": obstacle_id,
                "label": label,
                "deflection_strength": obstacle.deflection_strength,
            })
            return {
                "obstacle_id": obstacle_id,
                "label": label,
                "deflection_strength": obstacle.deflection_strength,
                "redirect_direction": obstacle.redirect_direction,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single kinetic narrative forge cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = ForgePhase.IGNITE
            phase_outputs["ignite"] = self._phase_ignite()
            self._phase = ForgePhase.ACCELERATE
            phase_outputs["accelerate"] = self._phase_accelerate()
            self._phase = ForgePhase.DEFLECT
            phase_outputs["deflect"] = self._phase_deflect()
            self._phase = ForgePhase.COLLIDE
            phase_outputs["collide"] = self._phase_collide()
            self._phase = ForgePhase.TEMPER
            phase_outputs["temper"] = self._phase_temper()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_ignite(self) -> Dict[str, Any]:
        """Ignite phase: check for newly ignited threads."""
        ignited = 0
        for thread in self._threads.values():
            if thread.state == ThreadState.IGNITED and thread.event_count > 0:
                thread.state = ThreadState.ACCELERATING
                ignited += 1
        return {
            "threads_ignited": ignited,
            "total_threads": len(self._threads),
        }

    def _phase_accelerate(self) -> Dict[str, Any]:
        """Accelerate phase: threads gain momentum from accumulated events."""
        accelerated = 0
        max_momentum = 0.0
        for thread in self._threads.values():
            if thread.state in (ThreadState.DORMANT, ThreadState.MERGED, ThreadState.SHATTERED):
                continue
            # Acceleration: momentum grows with event count
            acceleration = thread.event_count * self._ACCELERATION_FACTOR * 0.1
            thread.momentum += acceleration
            # Decay: momentum naturally decays
            thread.momentum *= (1.0 - self._MOMENTUM_DECAY)
            thread.momentum = max(0.0, thread.momentum)
            if thread.momentum > max_momentum:
                max_momentum = thread.momentum
            if thread.state == ThreadState.ACCELERATING:
                accelerated += 1
            # Check for dormancy
            if thread.momentum < self._DORMANT_THRESHOLD:
                thread.state = ThreadState.DORMANT
            thread.last_updated = time.time()
        return {
            "threads_accelerated": accelerated,
            "max_momentum": round(max_momentum, 4),
        }

    def _phase_deflect(self) -> Dict[str, Any]:
        """Deflect phase: obstacles deflect active threads."""
        deflections = 0
        for obstacle in self._obstacles.values():
            for thread in self._threads.values():
                if thread.state in (ThreadState.DORMANT, ThreadState.MERGED, ThreadState.SHATTERED):
                    continue
                # Check if thread direction is close to obstacle
                direction_diff = abs(thread.direction - obstacle.redirect_direction)
                if direction_diff < self._COLLISION_PROXIMITY:
                    # Deflect the thread
                    old_direction = thread.direction
                    thread.direction = (
                        thread.direction * (1.0 - obstacle.deflection_strength)
                        + obstacle.redirect_direction * obstacle.deflection_strength
                    )
                    thread.deflection_count += 1
                    thread.state = ThreadState.DEFLECTED
                    deflections += 1
                    self._record_event("thread_deflected", {
                        "thread_id": thread.thread_id,
                        "obstacle_id": obstacle.obstacle_id,
                        "old_direction": round(old_direction, 4),
                        "new_direction": round(thread.direction, 4),
                    })
        return {
            "deflections": deflections,
            "obstacles_active": len(self._obstacles),
        }

    def _phase_collide(self) -> Dict[str, Any]:
        """Collide phase: detect and resolve thread collisions."""
        collisions_this_cycle = 0
        mergers = 0
        sparks = 0
        shatters = 0
        annihilations = 0
        active_threads = [
            t for t in self._threads.values()
            if t.state not in (ThreadState.DORMANT, ThreadState.MERGED, ThreadState.SHATTERED)
        ]
        # Check pairs for collision
        for i in range(len(active_threads)):
            for j in range(i + 1, len(active_threads)):
                ta = active_threads[i]
                tb = active_threads[j]
                if ta.state in (ThreadState.MERGED, ThreadState.SHATTERED, ThreadState.DORMANT):
                    continue
                if tb.state in (ThreadState.MERGED, ThreadState.SHATTERED, ThreadState.DORMANT):
                    continue
                # Collision condition: directions are close and both have momentum
                direction_diff = abs(ta.direction - tb.direction)
                if direction_diff < self._COLLISION_PROXIMITY and ta.momentum > 0.1 and tb.momentum > 0.1:
                    # Determine collision outcome
                    total_momentum = ta.momentum + tb.momentum
                    momentum_diff = abs(ta.momentum - tb.momentum)
                    # Outcome based on momentum ratio
                    if momentum_diff < 0.1:
                        # Similar momentum: merger
                        outcome = CollisionOutcome.MERGER
                        ta.momentum = total_momentum * 0.8  # some energy lost
                        ta.direction = (ta.direction + tb.direction) / 2.0
                        ta.event_count += tb.event_count
                        tb.state = ThreadState.MERGED
                        ta.state = ThreadState.ACCELERATING
                        surviving = ta.thread_id
                        mergers += 1
                    elif momentum_diff < 0.3:
                        # Moderate difference: spark
                        outcome = CollisionOutcome.SPARK
                        spark_energy = total_momentum * self._SPARK_FACTOR
                        ta.spark_energy += spark_energy
                        tb.spark_energy += spark_energy
                        ta.momentum *= 0.7
                        tb.momentum *= 0.7
                        ta.state = ThreadState.COLLIDING
                        tb.state = ThreadState.COLLIDING
                        surviving = None
                        sparks += 1
                    elif momentum_diff < 0.5:
                        # Large difference: weaker thread shatters
                        outcome = CollisionOutcome.SHATTER
                        if ta.momentum < tb.momentum:
                            ta.state = ThreadState.SHATTERED
                            ta.momentum = 0.0
                            surviving = tb.thread_id
                        else:
                            tb.state = ThreadState.SHATTERED
                            tb.momentum = 0.0
                            surviving = ta.thread_id
                        shatters += 1
                    else:
                        # Huge difference: annihilation (both destroyed)
                        outcome = CollisionOutcome.ANNIHILATION
                        ta.state = ThreadState.SHATTERED
                        tb.state = ThreadState.SHATTERED
                        ta.momentum = 0.0
                        tb.momentum = 0.0
                        surviving = None
                        annihilations += 1
                    # Record collision
                    collision_id = f"col_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
                    collision = Collision(
                        collision_id=collision_id,
                        thread_a=ta.thread_id,
                        thread_b=tb.thread_id,
                        outcome=outcome,
                        spark_energy=total_momentum * self._SPARK_FACTOR,
                        surviving_thread=surviving,
                    )
                    self._collisions.append(collision)
                    collisions_this_cycle += 1
                    ta.collision_count += 1
                    tb.collision_count += 1
                    self._record_event("threads_collided", {
                        "collision_id": collision_id,
                        "thread_a": ta.thread_id,
                        "thread_b": tb.thread_id,
                        "outcome": outcome.value,
                        "spark_energy": round(collision.spark_energy, 4),
                        "surviving": surviving,
                    })
        return {
            "collisions": collisions_this_cycle,
            "mergers": mergers,
            "sparks": sparks,
            "shatters": shatters,
            "annihilations": annihilations,
        }

    def _phase_temper(self) -> Dict[str, Any]:
        """Temper phase: stabilize momentum into coherent direction."""
        tempered = 0
        for thread in self._threads.values():
            if thread.state in (ThreadState.DORMANT, ThreadState.MERGED, ThreadState.SHATTERED):
                continue
            if thread.momentum >= self._TEMPER_THRESHOLD and thread.state != ThreadState.TEMPERED:
                # Temper: stabilize direction
                thread.tempered_direction = thread.direction
                thread.state = ThreadState.TEMPERED
                tempered += 1
                self._record_event("thread_tempered", {
                    "thread_id": thread.thread_id,
                    "momentum": round(thread.momentum, 4),
                    "direction": round(thread.direction, 4),
                })
        return {
            "threads_tempered": tempered,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        """Get a specific narrative thread."""
        with self._global_lock:
            t = self._threads.get(thread_id)
            if t is None:
                return {"error": f"Thread not found: {thread_id}"}
            return self._serialize_thread(t)

    def get_all_threads(self) -> List[Dict[str, Any]]:
        """Get all narrative threads."""
        with self._global_lock:
            return [self._serialize_thread(t) for t in self._threads.values()]

    def get_collisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent collisions."""
        with self._global_lock:
            return [
                {
                    "collision_id": c.collision_id,
                    "thread_a": c.thread_a,
                    "thread_b": c.thread_b,
                    "outcome": c.outcome.value,
                    "spark_energy": round(c.spark_energy, 4),
                    "surviving_thread": c.surviving_thread,
                    "timestamp": c.timestamp,
                }
                for c in list(self._collisions)[-limit:]
            ]

    def get_obstacles(self) -> List[Dict[str, Any]]:
        """Get all obstacles."""
        with self._global_lock:
            return [
                {
                    "obstacle_id": o.obstacle_id,
                    "label": o.label,
                    "deflection_strength": o.deflection_strength,
                    "redirect_direction": o.redirect_direction,
                    "created_at": o.created_at,
                }
                for o in self._obstacles.values()
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the forge."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple cycles and return the final status."""
        with self._global_lock:
            for _ in range(max(1, cycles)):
                self.cycle()
            return self.get_status()

    def reset(self) -> Dict[str, Any]:
        """Reset the entire forge."""
        with self._global_lock:
            self._events.clear()
            self._threads.clear()
            self._obstacles.clear()
            self._collisions.clear()
            self._phase = ForgePhase.IGNITE
            self._cycle_count = 0
            self._events_log.clear()
            self._init_stats()
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _serialize_thread(self, t: NarrativeThread) -> Dict[str, Any]:
        return {
            "thread_id": t.thread_id,
            "label": t.label,
            "momentum": round(t.momentum, 4),
            "direction": round(t.direction, 4),
            "velocity": round(t.velocity, 4),
            "event_count": t.event_count,
            "state": t.state.value,
            "dominant_mass": t.dominant_mass.value,
            "deflection_count": t.deflection_count,
            "collision_count": t.collision_count,
            "tempered_direction": round(t.tempered_direction, 4) if t.tempered_direction is not None else None,
            "spark_energy": round(t.spark_energy, 4),
            "event_ids": list(t.event_ids),
            "created_at": t.created_at,
            "last_updated": t.last_updated,
        }

    def _update_stats(self) -> None:
        total_events = len(self._events)
        total_threads = len(self._threads)
        total_obstacles = len(self._obstacles)
        total_collisions = len(self._collisions)
        mergers = sum(1 for c in self._collisions if c.outcome == CollisionOutcome.MERGER)
        sparks = sum(1 for c in self._collisions if c.outcome == CollisionOutcome.SPARK)
        shatters = sum(1 for c in self._collisions if c.outcome == CollisionOutcome.SHATTER)
        deflections = sum(t.deflection_count for t in self._threads.values())
        annihilations = sum(1 for c in self._collisions if c.outcome == CollisionOutcome.ANNIHILATION)
        tempered = sum(1 for t in self._threads.values() if t.state == ThreadState.TEMPERED)
        dormant = sum(1 for t in self._threads.values() if t.state == ThreadState.DORMANT)
        total_momentum = sum(t.momentum for t in self._threads.values())
        total_spark = sum(t.spark_energy for t in self._threads.values())
        max_momentum = max((t.momentum for t in self._threads.values()), default=0.0)
        self._stats["total_events"] = total_events
        self._stats["total_threads"] = total_threads
        self._stats["total_obstacles"] = total_obstacles
        self._stats["total_collisions"] = total_collisions
        self._stats["mergers"] = mergers
        self._stats["sparks"] = sparks
        self._stats["shatters"] = shatters
        self._stats["deflections"] = deflections
        self._stats["annihilations"] = annihilations
        self._stats["tempered_threads"] = tempered
        self._stats["dormant_threads"] = dormant
        self._stats["total_momentum"] = round(total_momentum, 4)
        self._stats["total_spark_energy"] = round(total_spark, 4)
        self._stats["avg_momentum"] = round(total_momentum / total_threads, 4) if total_threads else 0.0
        self._stats["max_momentum"] = round(max_momentum, 4)

    def _init_stats(self) -> None:
        self._stats = {
            "total_events": 0,
            "total_threads": 0,
            "total_obstacles": 0,
            "total_collisions": 0,
            "mergers": 0,
            "sparks": 0,
            "shatters": 0,
            "deflections": 0,
            "annihilations": 0,
            "tempered_threads": 0,
            "dormant_threads": 0,
            "total_momentum": 0.0,
            "total_spark_energy": 0.0,
            "avg_momentum": 0.0,
            "max_momentum": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
