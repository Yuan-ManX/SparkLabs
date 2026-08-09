"""
SparkLabs Engine - Causal Cascade Composer"""

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

class CascadePhase(Enum):
    """Phases of the causal cascade composition cycle."""
    SEED = "seed"            # new causal events seed ripples into the network
    PROPAGATE = "propagate"  # ripples propagate outward, expending energy
    BRANCH = "branch"        # energetic ripples split into sub-ripples
    CONVERGE = "converge"    # meeting ripples combine into emergent consequences
    SETTLE = "settle"        # depleted ripples settle into stable consequences


class CausalEventType(Enum):
    """Types of causal events that seed ripples."""
    ACTION = "action"                # player or entity action
    DECISION = "decision"            # a choice that branches the future
    ENVIRONMENTAL = "environmental"  # world-state change (weather, terrain)
    SOCIAL = "social"                # relationship and faction interaction
    NARRATIVE = "narrative"          # story beat with plot weight
    COMBAT = "combat"                # violent conflict and its fallout
    ECONOMIC = "economic"            # trade, wealth, and resource flow
    POLITICAL = "political"          # power, governance, and authority
    MAGICAL = "magical"              # supernatural forces and their wake
    TECHNOLOGICAL = "technological"  # invention and crafted systems


class RippleState(Enum):
    """Lifecycle state of a causal ripple."""
    SEEDED = "seeded"          # just seeded, awaiting propagation
    PROPAGATING = "propagating"  # actively traveling outward
    BRANCHED = "branched"      # has spawned sub-ripples, still propagating
    CONVERGED = "converged"    # absorbed into a convergence, no longer travels
    SETTLED = "settled"        # crystallized into a stable consequence
    DISSIPATED = "dissipated"  # energy fully spent with no lasting effect


class ConvergenceType(Enum):
    """Types of convergence when two or more ripples meet."""
    AMPLIFICATION = "amplification"  # ripples combine and amplify
    CANCELATION = "cancelation"      # ripples cancel out
    TRANSFORMATION = "transformation"  # convergence creates a new consequence
    REDIRECTION = "redirection"      # convergence redirects the causal chain


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CausalEvent:
    """A significant event that seeds a causal ripple into the cascade network."""
    event_id: str
    label: str
    event_type: CausalEventType
    source_entity: str = ""
    energy: float = 0.7                       # initial energy budget (0.0-1.0)
    position: Tuple[float, float] = (0.5, 0.5)  # normalized world position
    description: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class CausalRipple:
    """A propagating causal ripple traveling through the world."""
    ripple_id: str
    source_event_id: str
    current_energy: float = 0.7
    current_position: Tuple[float, float] = (0.5, 0.5)
    direction: float = 0.0                    # radians
    state: RippleState = RippleState.SEEDED
    branched_from: Optional[str] = None       # parent ripple_id if spawned by branching
    convergence_count: int = 0
    distance_traveled: float = 0.0
    created_at: float = field(default_factory=time.time)
    settled_consequence: Optional[str] = None  # consequence_id once settled


@dataclass
class Convergence:
    """A record of two or more ripples converging."""
    convergence_id: str
    ripple_ids: List[str] = field(default_factory=list)
    convergence_type: ConvergenceType = ConvergenceType.AMPLIFICATION
    combined_energy: float = 0.0
    emergent_consequence: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class SettledConsequence:
    """A stable consequence that a settled ripple leaves in the world."""
    consequence_id: str
    source_ripple_id: str
    position: Tuple[float, float] = (0.5, 0.5)
    energy: float = 0.0
    description: str = ""
    event_type: CausalEventType = CausalEventType.ACTION
    persistence: float = 0.5                  # 0.0-1.0, how durably it persists
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# Causal Cascade Composer
# =============================================================================

class EngineCausalCascadeComposer:
    """
    Thread-safe singleton orchestrating causal cascade composition.

    Usage:
        composer = EngineCausalCascadeComposer.get_instance()
        composer.seed_event(
            "e_battle",
            "Battle of the Northern Pass",
            CausalEventType.COMBAT,
            source_entity="General Vorn",
            energy=0.9,
            x=0.4,
            y=0.3,
            description="A decisive victory that reshapes the border.",
        )
        composer.seed_event(
            "e_treaty",
            "The Salt Road Treaty",
            CausalEventType.POLITICAL,
            source_entity="Senate",
            energy=0.6,
            x=0.5,
            y=0.5,
        )
        composer.cycle()
        composer.simulate(cycles=8)
    """

    _instance: Optional["EngineCausalCascadeComposer"] = None
    _lock = threading.RLock()

    # How fast ripples move per cycle (normalized world units).
    _PROPAGATION_SPEED = 0.15
    # Energy lost per propagation step.
    _ENERGY_DECAY = 0.08
    # Minimum energy for a ripple to be eligible to branch.
    _BRANCH_THRESHOLD = 0.4
    # Chance of branching per cycle when energy exceeds the threshold.
    _BRANCH_PROBABILITY = 0.3
    # Distance within which two ripples converge.
    _CONVERGENCE_DISTANCE = 0.15
    # Energy below which a ripple settles into a stable consequence.
    _SETTLE_THRESHOLD = 0.08
    # Energy below which a ripple dissipates completely with no consequence.
    _DISSIPATE_THRESHOLD = 0.02
    # Energy multiplier when ripples amplify on convergence.
    _AMPLIFICATION_FACTOR = 1.3
    # Base persistence for settled consequences.
    _PERSISTENCE_BASE = 0.5
    # Angular offset applied to sub-ripples when branching.
    _BRANCH_ANGLE = math.pi / 4.0
    # Energy fraction retained by the parent ripple after branching.
    _BRANCH_PARENT_RETENTION = 0.4
    # Energy fraction granted to each child ripple on branching.
    _BRANCH_CHILD_SHARE = 0.25

    def __init__(self) -> None:
        self._events: Dict[str, CausalEvent] = {}
        self._ripples: Dict[str, CausalRipple] = {}
        self._convergences: Deque[Convergence] = deque(maxlen=300)
        self._settled: Deque[SettledConsequence] = deque(maxlen=300)
        self._phase: CascadePhase = CascadePhase.SEED
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {}
        self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineCausalCascadeComposer":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Seeding
    # -------------------------------------------------------------------------

    def seed_event(
        self,
        event_id: str,
        label: str,
        event_type: CausalEventType,
        source_entity: str = "",
        energy: float = 0.7,
        x: float = 0.5,
        y: float = 0.5,
        description: str = "",
    ) -> Dict[str, Any]:
        """Seed a new causal event and its initial ripple into the network."""
        with self._global_lock:
            if event_id in self._events:
                return {"error": f"Event already exists: {event_id}"}
            clamped_energy = max(0.0, min(1.0, energy))
            cx = max(0.0, min(1.0, x))
            cy = max(0.0, min(1.0, y))
            event = CausalEvent(
                event_id=event_id,
                label=label,
                event_type=event_type,
                source_entity=source_entity,
                energy=clamped_energy,
                position=(cx, cy),
                description=description,
            )
            self._events[event_id] = event
            # Seed the initial ripple at the event's position with full energy.
            ripple_id = self._new_id("ripple")
            ripple = CausalRipple(
                ripple_id=ripple_id,
                source_event_id=event_id,
                current_energy=clamped_energy,
                current_position=(cx, cy),
                direction=random.uniform(0.0, 2.0 * math.pi),
                state=RippleState.SEEDED,
            )
            self._ripples[ripple_id] = ripple
            self._stats["total_events_seeded"] += 1
            self._stats["total_ripples_created"] += 1
            self._record_event("event_seeded", {
                "event_id": event_id,
                "label": label,
                "event_type": event_type.value,
                "source_entity": source_entity,
                "energy": clamped_energy,
                "ripple_id": ripple_id,
            })
            return {
                "event_id": event_id,
                "label": label,
                "event_type": event_type.value,
                "source_entity": source_entity,
                "energy": clamped_energy,
                "position": (cx, cy),
                "ripple_id": ripple_id,
                "state": ripple.state.value,
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single causal cascade composition cycle through all phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = CascadePhase.SEED
            phase_outputs["seed"] = self._phase_seed()
            self._phase = CascadePhase.PROPAGATE
            phase_outputs["propagate"] = self._phase_propagate()
            self._phase = CascadePhase.BRANCH
            phase_outputs["branch"] = self._phase_branch()
            self._phase = CascadePhase.CONVERGE
            phase_outputs["converge"] = self._phase_converge()
            self._phase = CascadePhase.SETTLE
            phase_outputs["settle"] = self._phase_settle()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_seed(self) -> Dict[str, Any]:
        """Seed phase: recently seeded ripples begin propagating."""
        transitioned = 0
        for ripple in self._ripples.values():
            if ripple.state == RippleState.SEEDED:
                ripple.state = RippleState.PROPAGATING
                transitioned += 1
        return {
            "ripples_activated": transitioned,
            "active_ripples": len(self._ripples),
        }

    def _phase_propagate(self) -> Dict[str, Any]:
        """Propagation phase: ripples move outward and lose energy with distance."""
        propagated = 0
        for ripple in self._ripples.values():
            # Only ripples that are actively traveling propagate forward.
            if ripple.state not in (RippleState.PROPAGATING, RippleState.BRANCHED):
                continue
            dx = math.cos(ripple.direction) * self._PROPAGATION_SPEED
            dy = math.sin(ripple.direction) * self._PROPAGATION_SPEED
            px, py = ripple.current_position
            nx, ny = px + dx, py + dy
            # Reflect at world boundaries so ripples stay within the play space.
            if nx < 0.0 or nx > 1.0:
                ripple.direction = math.pi - ripple.direction
                nx = max(0.0, min(1.0, nx))
            if ny < 0.0 or ny > 1.0:
                ripple.direction = -ripple.direction
                ny = max(0.0, min(1.0, ny))
            ripple.current_position = (nx, ny)
            ripple.distance_traveled += self._PROPAGATION_SPEED
            ripple.current_energy = max(0.0, ripple.current_energy - self._ENERGY_DECAY)
            propagated += 1
        return {
            "ripples_propagated": propagated,
            "avg_energy": self._avg_energy(),
            "avg_distance": self._avg_distance(),
        }

    def _phase_branch(self) -> Dict[str, Any]:
        """Branch phase: energetic ripples split into sub-ripples."""
        branched = 0
        children_created = 0
        # Snapshot ripple ids to avoid mutating the dict during iteration.
        ripple_ids = list(self._ripples.keys())
        for ripple_id in ripple_ids:
            ripple = self._ripples.get(ripple_id)
            if ripple is None:
                continue
            if ripple.state != RippleState.PROPAGATING:
                continue
            if ripple.current_energy < self._BRANCH_THRESHOLD:
                continue
            if random.random() > self._BRANCH_PROBABILITY:
                continue
            # Spawn two children fanning outward from the parent direction.
            parent_energy = ripple.current_energy
            for sign in (-1, 1):
                child_dir = ripple.direction + sign * self._BRANCH_ANGLE
                cx, cy = ripple.current_position
                child = CausalRipple(
                    ripple_id=self._new_id("ripple"),
                    source_event_id=ripple.source_event_id,
                    current_energy=max(0.0, min(1.0, parent_energy * self._BRANCH_CHILD_SHARE)),
                    current_position=(cx, cy),
                    direction=child_dir,
                    state=RippleState.PROPAGATING,
                    branched_from=ripple.ripple_id,
                )
                self._ripples[child.ripple_id] = child
                children_created += 1
                self._stats["total_ripples_created"] += 1
            # Parent retains a fraction of its energy and continues traveling.
            ripple.current_energy = max(0.0, min(1.0, parent_energy * self._BRANCH_PARENT_RETENTION))
            ripple.state = RippleState.BRANCHED
            branched += 1
            self._record_event("ripple_branched", {
                "parent_ripple_id": ripple.ripple_id,
                "source_event_id": ripple.source_event_id,
                "children_energy_share": parent_energy * self._BRANCH_CHILD_SHARE,
            })
        self._stats["total_branched"] += branched
        return {
            "ripples_branched": branched,
            "children_created": children_created,
        }

    def _phase_converge(self) -> Dict[str, Any]:
        """Converge phase: meeting ripples combine into emergent consequences."""
        amplification = 0
        cancelation = 0
        transformation = 0
        redirection = 0
        # Collect ripples that are still traveling and eligible to converge.
        traveling = [
            r for r in self._ripples.values()
            if r.state in (RippleState.PROPAGATING, RippleState.BRANCHED)
        ]
        consumed: set = set()
        for i in range(len(traveling)):
            a = traveling[i]
            if a.ripple_id in consumed:
                continue
            for j in range(i + 1, len(traveling)):
                b = traveling[j]
                if b.ripple_id in consumed:
                    continue
                ax, ay = a.current_position
                bx, by = b.current_position
                distance = math.hypot(ax - bx, ay - by)
                if distance > self._CONVERGENCE_DISTANCE:
                    continue
                # The two ripples meet - determine how they converge.
                ea = a.current_energy
                eb = b.current_energy
                combined = ea + eb
                mx = (ax + bx) / 2.0
                my = (ay + by) / 2.0
                max_energy = max(ea, eb)
                min_energy = min(ea, eb)
                ratio = (min_energy / max_energy) if max_energy > 0.0 else 0.0
                if ratio > 0.6 and combined > 0.5:
                    conv_type = ConvergenceType.AMPLIFICATION
                elif ratio < 0.3:
                    conv_type = ConvergenceType.CANCELATION
                elif random.random() < 0.5:
                    conv_type = ConvergenceType.TRANSFORMATION
                else:
                    conv_type = ConvergenceType.REDIRECTION
                emergent: Optional[str] = None
                new_ripple_id: Optional[str] = None
                if conv_type == ConvergenceType.AMPLIFICATION:
                    # Ripples combine and amplify - a stronger ripple emerges.
                    new_energy = min(1.0, combined * self._AMPLIFICATION_FACTOR)
                    new_dir = (a.direction + b.direction) / 2.0
                    new_ripple_id = self._spawn_converged_ripple(
                        source_event_id=a.source_event_id,
                        energy=new_energy,
                        position=(mx, my),
                        direction=new_dir,
                        convergence_count=a.convergence_count + b.convergence_count + 1,
                        branched_from=None,
                    )
                    emergent = new_ripple_id
                    amplification += 1
                elif conv_type == ConvergenceType.TRANSFORMATION:
                    # Convergence births an entirely new consequence chain.
                    new_energy = min(1.0, combined * 0.8)
                    new_dir = random.uniform(0.0, 2.0 * math.pi)
                    new_ripple_id = self._spawn_converged_ripple(
                        source_event_id=a.source_event_id,
                        energy=new_energy,
                        position=(mx, my),
                        direction=new_dir,
                        convergence_count=a.convergence_count + b.convergence_count + 1,
                        branched_from=None,
                    )
                    emergent = new_ripple_id
                    transformation += 1
                elif conv_type == ConvergenceType.REDIRECTION:
                    # Convergence redirects the causal chain along a new axis.
                    new_energy = min(1.0, combined * 0.7)
                    new_dir = (a.direction + b.direction) / 2.0 + math.pi / 3.0
                    new_ripple_id = self._spawn_converged_ripple(
                        source_event_id=a.source_event_id,
                        energy=new_energy,
                        position=(mx, my),
                        direction=new_dir,
                        convergence_count=a.convergence_count + b.convergence_count + 1,
                        branched_from=None,
                    )
                    emergent = new_ripple_id
                    redirection += 1
                else:
                    # Cancelation - both ripples cancel out, no new ripple.
                    a.current_energy = 0.0
                    b.current_energy = 0.0
                    cancelation += 1
                # Mark the participating ripples as converged.
                a.state = RippleState.CONVERGED
                b.state = RippleState.CONVERGED
                consumed.add(a.ripple_id)
                consumed.add(b.ripple_id)
                convergence_id = self._new_id("conv")
                self._convergences.append(Convergence(
                    convergence_id=convergence_id,
                    ripple_ids=[a.ripple_id, b.ripple_id],
                    convergence_type=conv_type,
                    combined_energy=combined,
                    emergent_consequence=emergent,
                ))
                self._record_event("ripples_converged", {
                    "convergence_id": convergence_id,
                    "ripple_ids": [a.ripple_id, b.ripple_id],
                    "type": conv_type.value,
                    "combined_energy": combined,
                    "emergent_ripple": new_ripple_id,
                })
                break  # ripple a has converged; move to the next outer ripple
        self._stats["amplification_convergences"] += amplification
        self._stats["cancelation_convergences"] += cancelation
        self._stats["transformation_convergences"] += transformation
        self._stats["redirection_convergences"] += redirection
        self._stats["total_convergences"] = len(self._convergences)
        return {
            "amplification": amplification,
            "cancelation": cancelation,
            "transformation": transformation,
            "redirection": redirection,
            "total_convergences": len(self._convergences),
        }

    def _phase_settle(self) -> Dict[str, Any]:
        """Settle phase: depleted ripples settle or dissipate into the world."""
        settled = 0
        dissipated = 0
        to_remove: List[str] = []
        for ripple in self._ripples.values():
            if ripple.state in (RippleState.SETTLED, RippleState.DISSIPATED):
                continue
            # Converged ripples have been absorbed and are cleaned up here.
            if ripple.state == RippleState.CONVERGED:
                if ripple.current_energy < self._DISSIPATE_THRESHOLD:
                    ripple.state = RippleState.DISSIPATED
                    dissipated += 1
                    to_remove.append(ripple.ripple_id)
                else:
                    to_remove.append(ripple.ripple_id)
                continue
            energy = ripple.current_energy
            if energy < self._DISSIPATE_THRESHOLD:
                # Too little energy to leave any trace - dissipate completely.
                ripple.state = RippleState.DISSIPATED
                dissipated += 1
                to_remove.append(ripple.ripple_id)
            elif energy < self._SETTLE_THRESHOLD:
                # Enough residual energy to crystallize into a stable consequence.
                consequence_id = self._new_id("cons")
                event = self._events.get(ripple.source_event_id)
                event_type = event.event_type if event is not None else CausalEventType.ACTION
                event_label = event.label if event is not None else ripple.source_event_id
                persistence = min(
                    1.0,
                    self._PERSISTENCE_BASE + energy * 0.3,
                )
                description = (
                    f"Settled consequence of {event_type.value} event "
                    f"'{event_label}' after traveling {ripple.distance_traveled:.3f}"
                )
                self._settled.append(SettledConsequence(
                    consequence_id=consequence_id,
                    source_ripple_id=ripple.ripple_id,
                    position=ripple.current_position,
                    energy=energy,
                    description=description,
                    event_type=event_type,
                    persistence=persistence,
                ))
                ripple.state = RippleState.SETTLED
                ripple.settled_consequence = consequence_id
                settled += 1
                to_remove.append(ripple.ripple_id)
                self._record_event("consequence_settled", {
                    "consequence_id": consequence_id,
                    "source_ripple_id": ripple.ripple_id,
                    "source_event_id": ripple.source_event_id,
                    "event_type": event_type.value,
                    "energy": energy,
                    "persistence": persistence,
                })
        for rid in to_remove:
            self._ripples.pop(rid, None)
        self._stats["total_settled"] += settled
        self._stats["total_dissipated"] += dissipated
        return {
            "ripples_settled": settled,
            "ripples_dissipated": dissipated,
            "total_settled_consequences": len(self._settled),
        }

    # -------------------------------------------------------------------------
    # Public Accessors
    # -------------------------------------------------------------------------

    def get_ripple(self, ripple_id: str) -> Dict[str, Any]:
        """Get a specific ripple by ID."""
        with self._global_lock:
            r = self._ripples.get(ripple_id)
            if r is None:
                return {"error": f"Ripple not found: {ripple_id}"}
            return self._serialize_ripple(r)

    def get_all_ripples(self) -> List[Dict[str, Any]]:
        """Get all active ripples."""
        with self._global_lock:
            return [self._serialize_ripple(r) for r in self._ripples.values()]

    def get_convergences(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent convergence records."""
        with self._global_lock:
            entries = list(self._convergences)[-limit:]
            return [
                {
                    "convergence_id": c.convergence_id,
                    "ripple_ids": list(c.ripple_ids),
                    "convergence_type": c.convergence_type.value,
                    "combined_energy": c.combined_energy,
                    "emergent_consequence": c.emergent_consequence,
                    "timestamp": c.timestamp,
                }
                for c in entries
            ]

    def get_settled_consequences(self) -> List[Dict[str, Any]]:
        """Get all settled consequences."""
        with self._global_lock:
            return [
                {
                    "consequence_id": s.consequence_id,
                    "source_ripple_id": s.source_ripple_id,
                    "position": s.position,
                    "energy": s.energy,
                    "description": s.description,
                    "event_type": s.event_type.value,
                    "persistence": s.persistence,
                    "timestamp": s.timestamp,
                }
                for s in self._settled
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the composer."""
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
        """Reset the entire composer."""
        with self._global_lock:
            self._events.clear()
            self._ripples.clear()
            self._convergences.clear()
            self._settled.clear()
            self._events_log.clear()
            self._phase = CascadePhase.SEED
            self._cycle_count = 0
            self._init_stats()
            return {"reset": True}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _spawn_converged_ripple(
        self,
        source_event_id: str,
        energy: float,
        position: Tuple[float, float],
        direction: float,
        convergence_count: int,
        branched_from: Optional[str],
    ) -> str:
        """Create a new ripple born from a convergence and return its ID."""
        ripple_id = self._new_id("ripple")
        ripple = CausalRipple(
            ripple_id=ripple_id,
            source_event_id=source_event_id,
            current_energy=energy,
            current_position=position,
            direction=direction,
            state=RippleState.PROPAGATING,
            branched_from=branched_from,
            convergence_count=convergence_count,
        )
        self._ripples[ripple_id] = ripple
        self._stats["total_ripples_created"] += 1
        return ripple_id

    def _new_id(self, prefix: str) -> str:
        """Generate a unique ID with the given prefix."""
        return f"{prefix}_{int(time.time() * 1000)}_{random.randint(0, 9999)}"

    def _avg_energy(self) -> float:
        """Average energy across currently active ripples."""
        if not self._ripples:
            return 0.0
        return sum(r.current_energy for r in self._ripples.values()) / len(self._ripples)

    def _avg_distance(self) -> float:
        """Average distance traveled across currently active ripples."""
        if not self._ripples:
            return 0.0
        return sum(r.distance_traveled for r in self._ripples.values()) / len(self._ripples)

    def _serialize_ripple(self, r: CausalRipple) -> Dict[str, Any]:
        return {
            "ripple_id": r.ripple_id,
            "source_event_id": r.source_event_id,
            "current_energy": r.current_energy,
            "current_position": r.current_position,
            "direction": r.direction,
            "state": r.state.value,
            "branched_from": r.branched_from,
            "convergence_count": r.convergence_count,
            "distance_traveled": r.distance_traveled,
            "created_at": r.created_at,
            "settled_consequence": r.settled_consequence,
        }

    def _init_stats(self) -> None:
        self._stats = {
            "total_events_seeded": 0,
            "total_ripples_created": 0,
            "active_ripples": 0,
            "total_branched": 0,
            "total_convergences": 0,
            "amplification_convergences": 0,
            "cancelation_convergences": 0,
            "transformation_convergences": 0,
            "redirection_convergences": 0,
            "total_settled": 0,
            "total_dissipated": 0,
            "total_settled_consequences": 0,
            "avg_energy": 0.0,
            "avg_distance": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        self._stats["active_ripples"] = len(self._ripples)
        self._stats["total_settled_consequences"] = len(self._settled)
        self._stats["avg_energy"] = self._avg_energy()
        self._stats["avg_distance"] = self._avg_distance()

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
