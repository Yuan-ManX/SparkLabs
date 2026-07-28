"""
SparkLabs Engine - Probability Collapse Theater

The EngineProbabilityCollapseTheater models game events as quantum-like
probability amplitudes. Before an event is observed, it exists in
superposition - a cloud of possible outcomes, each with its own
probability amplitude. When a player or agent observes the event, the
superposition collapses into a single definite outcome.

This creates a world where the future is genuinely undetermined until
someone looks. A treasure chest doesn't contain a specific item until
opened; an NPC doesn't have a fixed disposition until talked to; a
dungeon's layout isn't finalized until explored. The theater manages
these probability waves, their interference patterns, and their collapse.

The theater also models entanglement between events. Two probability
waves can be entangled such that collapsing one immediately determines
the other, even at a distance. This enables correlated world generation:
if the boss in dungeon A drops a fire sword, the boss in dungeon B
(the entangled partner) will drop an ice shield.

Architecture:
  SUPERPOSE   ->  INTERFERE   ->  OBSERVE    ->  COLLAPSE   ->  DECOHERE
  (new events    (waves        (an observer   (waves         (collapsed
   enter          interact,     triggers       collapse       outcomes
   superposition  creating      potential      into definite  fade back
   with multiple  constructive  collapse)      outcomes)      into potential
   outcomes)      or            )              )              for future
                 destructive                                  events)

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

class TheaterPhase(Enum):
    """Phases of the probability collapse cycle."""
    SUPERPOSE = "superpose"     # new waves enter superposition
    INTERFERE = "interfere"     # waves interact and interfere
    OBSERVE = "observe"         # observers trigger potential collapse
    COLLAPSE = "collapse"       # waves collapse into definite outcomes
    DECOHERE = "decohere"       # collapsed outcomes fade back into potential


class WaveState(Enum):
    """State of a probability wave."""
    SUPERPOSED = "superposed"   # multiple outcomes possible
    INTERFERING = "interfering" # interacting with other waves
    OBSERVED = "observed"       # an observer is looking
    COLLAPSED = "collapsed"     # reduced to a single outcome
    DECOHERED = "decohered"     # outcome fading back into potential


class ObservationType(Enum):
    """Types of observers that can trigger collapse."""
    PLAYER = "player"           # the human player observes
    AGENT = "agent"             # an AI agent observes
    SYSTEM = "system"           # the game system observes
    NARRATIVE = "narrative"     # the narrative director observes


class InterferenceType(Enum):
    """Types of interference between probability waves."""
    CONSTRUCTIVE = "constructive"   # amplitudes reinforce
    DESTRUCTIVE = "destructive"     # amplitudes cancel
    MIXED = "mixed"                 # partial reinforcement/cancellation


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AmplitudeBranch:
    """One possible outcome of a probability wave."""
    branch_id: str
    label: str
    amplitude: complex            # quantum-like amplitude
    weight: float = 0.0           # |amplitude|^2 (probability)
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProbabilityWave:
    """A superposition of possible event outcomes."""
    wave_id: str
    label: str
    branches: Dict[str, AmplitudeBranch] = field(default_factory=dict)
    state: WaveState = WaveState.SUPERPOSED
    domain: str = "general"
    created_at: float = field(default_factory=time.time)
    collapsed_branch: Optional[str] = None
    collapsed_at: Optional[float] = None
    observation_count: int = 0
    entangled_with: Set[str] = field(default_factory=set)
    coherence: float = 1.0       # how much superposition remains


@dataclass
class EntanglementLink:
    """A correlation link between two probability waves."""
    link_id: str
    wave_a: str
    wave_b: str
    correlation: float            # -1.0 to 1.0
    link_type: str = "mirror"     # mirror, complement, cause_effect


@dataclass
class CollapseResult:
    """The result of a wave collapsing."""
    result_id: str
    wave_id: str
    collapsed_branch: str
    observer: str
    observer_type: ObservationType
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    entangled_collapses: List[str] = field(default_factory=list)


# =============================================================================
# Engine
# =============================================================================

class EngineProbabilityCollapseTheater:
    """
    Thread-safe singleton for probability collapse theater.

    Usage:
        theater = EngineProbabilityCollapseTheater.get_instance()
        theater.create_wave("w_chest", "Treasure Chest", "loot")
        theater.add_branch("w_chest", "b_gold", "Gold Coins", 0.6+0j)
        theater.add_branch("w_chest", "b_gem", "Rare Gem", 0.4+0.2j)
        theater.entangle("w_chest", "w_chest2", "mirror", 1.0)
        theater.observe("w_chest", "player_1", ObservationType.PLAYER)
        theater.cycle()
    """

    _instance: Optional["EngineProbabilityCollapseTheater"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._waves: Dict[str, ProbabilityWave] = {}
        self._entanglements: Dict[str, EntanglementLink] = {}
        self._results: Deque[CollapseResult] = deque(maxlen=100)
        self._phase: TheaterPhase = TheaterPhase.SUPERPOSE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_waves": 0,
            "total_branches": 0,
            "total_entanglements": 0,
            "total_collapses": 0,
            "total_observations": 0,
            "superposed_waves": 0,
            "collapsed_waves": 0,
            "avg_coherence": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineProbabilityCollapseTheater":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Wave Management
    # -------------------------------------------------------------------------

    def create_wave(
        self,
        wave_id: str,
        label: str,
        domain: str = "general",
    ) -> Dict[str, Any]:
        """Create a new probability wave in superposition."""
        with self._global_lock:
            if wave_id in self._waves:
                return {"error": f"Wave already exists: {wave_id}"}
            wave = ProbabilityWave(
                wave_id=wave_id,
                label=label,
                domain=domain,
            )
            self._waves[wave_id] = wave
            self._stats["total_waves"] = len(self._waves)
            self._record_event("wave_created", {
                "wave_id": wave_id, "label": label, "domain": domain,
            })
            return {
                "wave_id": wave_id,
                "label": label,
                "domain": domain,
                "state": wave.state.value,
            }

    def add_branch(
        self,
        wave_id: str,
        branch_id: str,
        label: str,
        amplitude: complex,
        description: str = "",
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a possible outcome branch to a wave."""
        with self._global_lock:
            wave = self._waves.get(wave_id)
            if wave is None:
                return {"error": f"Wave not found: {wave_id}"}
            if branch_id in wave.branches:
                return {"error": f"Branch already exists: {branch_id}"}
            branch = AmplitudeBranch(
                branch_id=branch_id,
                label=label,
                amplitude=amplitude,
                weight=abs(amplitude) ** 2,
                description=description,
                properties=properties or {},
            )
            wave.branches[branch_id] = branch
            self._stats["total_branches"] = sum(len(w.branches) for w in self._waves.values())
            return {
                "wave_id": wave_id,
                "branch_id": branch_id,
                "label": label,
                "weight": round(branch.weight, 6),
            }

    def remove_wave(self, wave_id: str) -> Dict[str, Any]:
        """Remove a probability wave."""
        with self._global_lock:
            if wave_id not in self._waves:
                return {"error": f"Wave not found: {wave_id}"}
            # Remove entanglements
            to_remove = [
                lid for lid, link in self._entanglements.items()
                if link.wave_a == wave_id or link.wave_b == wave_id
            ]
            for lid in to_remove:
                other_id = self._entanglements[lid].wave_b if self._entanglements[lid].wave_a == wave_id else self._entanglements[lid].wave_a
                if other_id in self._waves:
                    self._waves[other_id].entangled_with.discard(wave_id)
                del self._entanglements[lid]
            del self._waves[wave_id]
            self._stats["total_waves"] = len(self._waves)
            self._stats["total_entanglements"] = len(self._entanglements)
            return {"removed": wave_id}

    def list_waves(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all probability waves."""
        with self._global_lock:
            return [self._summarize_wave(w) for w in list(self._waves.values())[:limit]]

    def get_wave(self, wave_id: str) -> Optional[Dict[str, Any]]:
        """Get full details of a probability wave."""
        with self._global_lock:
            w = self._waves.get(wave_id)
            if w is None:
                return None
            return {
                "wave_id": w.wave_id,
                "label": w.label,
                "domain": w.domain,
                "state": w.state.value,
                "coherence": round(w.coherence, 4),
                "observation_count": w.observation_count,
                "collapsed_branch": w.collapsed_branch,
                "entangled_with": list(w.entangled_with),
                "branches": [
                    {
                        "branch_id": b.branch_id,
                        "label": b.label,
                        "amplitude_real": round(b.amplitude.real, 4),
                        "amplitude_imag": round(b.amplitude.imag, 4),
                        "weight": round(b.weight, 6),
                        "description": b.description,
                    }
                    for b in w.branches.values()
                ],
            }

    # -------------------------------------------------------------------------
    # Entanglement Management
    # -------------------------------------------------------------------------

    def entangle(
        self,
        wave_a: str,
        wave_b: str,
        link_type: str = "mirror",
        correlation: float = 1.0,
    ) -> Dict[str, Any]:
        """Entangle two probability waves."""
        with self._global_lock:
            if wave_a not in self._waves:
                return {"error": f"Wave not found: {wave_a}"}
            if wave_b not in self._waves:
                return {"error": f"Wave not found: {wave_b}"}
            if wave_a == wave_b:
                return {"error": "Cannot entangle a wave with itself"}
            link_id = f"entangle_{wave_a}_{wave_b}_{int(time.time() * 1000) % 100000}"
            link = EntanglementLink(
                link_id=link_id,
                wave_a=wave_a,
                wave_b=wave_b,
                correlation=max(-1.0, min(1.0, correlation)),
                link_type=link_type,
            )
            self._entanglements[link_id] = link
            self._waves[wave_a].entangled_with.add(wave_b)
            self._waves[wave_b].entangled_with.add(wave_a)
            self._stats["total_entanglements"] = len(self._entanglements)
            self._record_event("entangled", {
                "link_id": link_id,
                "wave_a": wave_a,
                "wave_b": wave_b,
                "correlation": correlation,
            })
            return {
                "link_id": link_id,
                "wave_a": wave_a,
                "wave_b": wave_b,
                "correlation": link.correlation,
                "link_type": link_type,
            }

    def list_entanglements(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all entanglement links."""
        with self._global_lock:
            return [
                {
                    "link_id": l.link_id,
                    "wave_a": l.wave_a,
                    "wave_b": l.wave_b,
                    "correlation": l.correlation,
                    "link_type": l.link_type,
                }
                for l in list(self._entanglements.values())[:limit]
            ]

    # -------------------------------------------------------------------------
    # Observation
    # -------------------------------------------------------------------------

    def observe(
        self,
        wave_id: str,
        observer: str,
        observer_type: ObservationType = ObservationType.PLAYER,
    ) -> Dict[str, Any]:
        """Mark a wave as observed, triggering potential collapse."""
        with self._global_lock:
            wave = self._waves.get(wave_id)
            if wave is None:
                return {"error": f"Wave not found: {wave_id}"}
            if wave.state == WaveState.COLLAPSED:
                return {
                    "wave_id": wave_id,
                    "already_collapsed": True,
                    "collapsed_branch": wave.collapsed_branch,
                }
            wave.observation_count += 1
            wave.state = WaveState.OBSERVED
            self._stats["total_observations"] += 1
            self._record_event("observed", {
                "wave_id": wave_id,
                "observer": observer,
                "observer_type": observer_type.value,
            })
            # Collapse is handled in the cycle's COLLAPSE phase
            return {
                "wave_id": wave_id,
                "observer": observer,
                "observer_type": observer_type.value,
                "observation_count": wave.observation_count,
                "state": wave.state.value,
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single probability collapse cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            # SUPERPOSE: normalize wave amplitudes
            self._phase = TheaterPhase.SUPERPOSE
            phase_outputs["superpose"] = self._phase_superpose()
            # INTERFERE: waves interact through entanglement
            self._phase = TheaterPhase.INTERFERE
            phase_outputs["interfere"] = self._phase_interfere()
            # OBSERVE: process observation triggers
            self._phase = TheaterPhase.OBSERVE
            phase_outputs["observe"] = self._phase_observe()
            # COLLAPSE: observed waves collapse into definite outcomes
            self._phase = TheaterPhase.COLLAPSE
            phase_outputs["collapse"] = self._phase_collapse()
            # DECOHERE: collapsed outcomes fade back into potential
            self._phase = TheaterPhase.DECOHERE
            phase_outputs["decohere"] = self._phase_decohere()
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

    def _phase_superpose(self) -> Dict[str, Any]:
        """SUPERPOSE: normalize wave amplitudes and update weights."""
        normalized = 0
        for wave in self._waves.values():
            if wave.state not in (WaveState.SUPERPOSED, WaveState.INTERFERING):
                continue
            if not wave.branches:
                continue
            # Normalize amplitudes so total probability = 1.0
            total_weight = sum(abs(b.amplitude) ** 2 for b in wave.branches.values())
            if total_weight > 0:
                norm = math.sqrt(total_weight)
                for b in wave.branches.values():
                    b.amplitude = b.amplitude / norm
                    b.weight = abs(b.amplitude) ** 2
                normalized += 1
            # Restore coherence slightly for superposed waves
            if wave.state == WaveState.SUPERPOSED:
                wave.coherence = min(1.0, wave.coherence + 0.01)
        return {"normalized": normalized}

    def _phase_interfere(self) -> Dict[str, Any]:
        """INTERFERE: entangled waves affect each other's amplitudes."""
        interfered = 0
        interference_types: Dict[str, int] = {"constructive": 0, "destructive": 0, "mixed": 0}
        for link in self._entanglements.values():
            wave_a = self._waves.get(link.wave_a)
            wave_b = self._waves.get(link.wave_b)
            if wave_a is None or wave_b is None:
                continue
            if wave_a.state not in (WaveState.SUPERPOSED, WaveState.INTERFERING):
                continue
            if wave_b.state not in (WaveState.SUPERPOSED, WaveState.INTERFERING):
                continue
            # Mark as interfering
            wave_a.state = WaveState.INTERFERING
            wave_b.state = WaveState.INTERFERING
            # Simple interference: adjust amplitudes based on correlation
            if link.link_type == "mirror" and link.correlation > 0.5:
                # Constructive: aligned waves reinforce dominant branches
                if wave_a.branches and wave_b.branches:
                    dominant_a = max(wave_a.branches.values(), key=lambda b: b.weight)
                    dominant_b = max(wave_b.branches.values(), key=lambda b: b.weight)
                    boost = 0.05 * link.correlation
                    dominant_a.amplitude = complex(
                        dominant_a.amplitude.real * (1 + boost),
                        dominant_a.amplitude.imag,
                    )
                    dominant_b.amplitude = complex(
                        dominant_b.amplitude.real * (1 + boost),
                        dominant_b.amplitude.imag,
                    )
                    interference_types["constructive"] += 1
            elif link.link_type == "complement" and link.correlation < -0.5:
                # Destructive: complementary waves suppress same branches
                if wave_a.branches and wave_b.branches:
                    dominant_a = max(wave_a.branches.values(), key=lambda b: b.weight)
                    dominant_b = max(wave_b.branches.values(), key=lambda b: b.weight)
                    suppress = 0.05 * abs(link.correlation)
                    dominant_a.amplitude = complex(
                        dominant_a.amplitude.real * (1 - suppress),
                        dominant_a.amplitude.imag,
                    )
                    dominant_b.amplitude = complex(
                        dominant_b.amplitude.real * (1 - suppress),
                        dominant_b.amplitude.imag,
                    )
                    interference_types["destructive"] += 1
            else:
                interference_types["mixed"] += 1
            interfered += 1
        return {"interfered": interfered, "types": interference_types}

    def _phase_observe(self) -> Dict[str, Any]:
        """OBSERVE: process waves that have been marked as observed."""
        observed = 0
        for wave in self._waves.values():
            if wave.state == WaveState.OBSERVED:
                observed += 1
                # Observation reduces coherence
                wave.coherence = max(0.0, wave.coherence - 0.3)
        return {"observed": observed}

    def _phase_collapse(self) -> Dict[str, Any]:
        """COLLAPSE: observed waves with low coherence collapse into definite outcomes."""
        collapsed = 0
        entangled_collapses = 0
        for wave in list(self._waves.values()):
            if wave.state != WaveState.OBSERVED:
                continue
            if wave.coherence > 0.3:
                continue
            if not wave.branches:
                continue
            # Select branch based on weights (Born rule)
            branches = list(wave.branches.values())
            total_weight = sum(b.weight for b in branches)
            if total_weight <= 0:
                # Equal probability fallback
                selected = random.choice(branches)
            else:
                r = random.random() * total_weight
                cumulative = 0.0
                selected = branches[0]
                for b in branches:
                    cumulative += b.weight
                    if r <= cumulative:
                        selected = b
                        break
            wave.collapsed_branch = selected.branch_id
            wave.collapsed_at = time.time()
            wave.state = WaveState.COLLAPSED
            collapsed += 1
            # Record collapse result
            result = CollapseResult(
                result_id=f"result_{wave.wave_id}_{int(time.time() * 1000) % 100000}",
                wave_id=wave.wave_id,
                collapsed_branch=selected.branch_id,
                observer="system",
                observer_type=ObservationType.SYSTEM,
                description=f"Wave '{wave.label}' collapsed to '{selected.label}'",
            )
            # Entangled collapse: collapse entangled partners
            entangled_ids = []
            for entangled_id in wave.entangled_with:
                partner = self._waves.get(entangled_id)
                if partner is None or partner.state == WaveState.COLLAPSED:
                    continue
                # Find corresponding link
                link = None
                for l in self._entanglements.values():
                    if (l.wave_a == wave.wave_id and l.wave_b == entangled_id) or \
                       (l.wave_a == entangled_id and l.wave_b == wave.wave_id):
                        link = l
                        break
                if link is None:
                    continue
                # Collapse partner based on correlation and link type
                if link.link_type == "mirror" and link.correlation > 0.5:
                    # Mirror: partner collapses to its dominant branch (same outcome pattern)
                    if partner.branches:
                        partner_dominant = max(partner.branches.values(), key=lambda b: b.weight)
                        partner.collapsed_branch = partner_dominant.branch_id
                        partner.collapsed_at = time.time()
                        partner.state = WaveState.COLLAPSED
                        entangled_collapses += 1
                        entangled_ids.append(entangled_id)
                elif link.link_type == "complement" and link.correlation < -0.5:
                    # Complement: partner collapses to its weakest dominant (opposite outcome)
                    if partner.branches:
                        partner_weakest = min(partner.branches.values(), key=lambda b: b.weight)
                        partner.collapsed_branch = partner_weakest.branch_id
                        partner.collapsed_at = time.time()
                        partner.state = WaveState.COLLAPSED
                        entangled_collapses += 1
                        entangled_ids.append(entangled_id)
            result.entangled_collapses = entangled_ids
            self._results.append(result)
            self._stats["total_collapses"] = len(self._results)
            self._record_event("collapsed", {
                "wave_id": wave.wave_id,
                "collapsed_branch": selected.branch_id,
                "entangled_collapses": entangled_ids,
            })
        return {"collapsed": collapsed, "entangled_collapses": entangled_collapses}

    def _phase_decohere(self) -> Dict[str, Any]:
        """DECOHERE: collapsed outcomes fade back into potential over time."""
        decohered = 0
        now = time.time()
        for wave in self._waves.values():
            if wave.state != WaveState.COLLAPSED:
                continue
            if wave.collapsed_at is None:
                continue
            age = now - wave.collapsed_at
            # After sufficient time, allow re-superposition
            if age > 10.0:
                wave.state = WaveState.SUPERPOSED
                wave.collapsed_branch = None
                wave.collapsed_at = None
                wave.coherence = 0.5
                decohered += 1
        return {"decohered": decohered}

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get global theater status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_waves": len(self._waves),
                "total_entanglements": len(self._entanglements),
                "total_results": len(self._results),
                "stats": dict(self._stats),
            }

    def get_results(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent collapse results."""
        with self._global_lock:
            return [
                {
                    "result_id": r.result_id,
                    "wave_id": r.wave_id,
                    "collapsed_branch": r.collapsed_branch,
                    "observer": r.observer,
                    "observer_type": r.observer_type.value,
                    "description": r.description,
                    "entangled_collapses": r.entangled_collapses,
                    "timestamp": r.timestamp,
                }
                for r in list(self._results)[-limit:]
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent theater events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire theater."""
        with self._global_lock:
            n_waves = len(self._waves)
            n_entangle = len(self._entanglements)
            self._waves.clear()
            self._entanglements.clear()
            self._results.clear()
            self._phase = TheaterPhase.SUPERPOSE
            self._cycle_count = 0
            self._events_log.clear()
            self._stats = {
                "total_waves": 0,
                "total_branches": 0,
                "total_entanglements": 0,
                "total_collapses": 0,
                "total_observations": 0,
                "superposed_waves": 0,
                "collapsed_waves": 0,
                "avg_coherence": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            return {
                "reset": True,
                "cleared_waves": n_waves,
                "cleared_entanglements": n_entangle,
            }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        """Update aggregate statistics."""
        superposed = [w for w in self._waves.values() if w.state in (WaveState.SUPERPOSED, WaveState.INTERFERING, WaveState.OBSERVED)]
        collapsed = [w for w in self._waves.values() if w.state == WaveState.COLLAPSED]
        self._stats["superposed_waves"] = len(superposed)
        self._stats["collapsed_waves"] = len(collapsed)
        if self._waves:
            self._stats["avg_coherence"] = sum(w.coherence for w in self._waves.values()) / len(self._waves)
        else:
            self._stats["avg_coherence"] = 0.0
        self._stats["total_branches"] = sum(len(w.branches) for w in self._waves.values())

    def _summarize_wave(self, w: ProbabilityWave) -> Dict[str, Any]:
        """Summarize a wave for listing."""
        return {
            "wave_id": w.wave_id,
            "label": w.label,
            "domain": w.domain,
            "state": w.state.value,
            "coherence": round(w.coherence, 4),
            "branch_count": len(w.branches),
            "observation_count": w.observation_count,
            "collapsed_branch": w.collapsed_branch,
            "entangled_count": len(w.entangled_with),
        }

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a theater event."""
        self._events_log.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
