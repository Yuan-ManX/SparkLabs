"""
SparkLabs Agent - Synaptic Resonance Lattice

The AgentSynapticResonanceLattice models how agents form a living lattice
of resonant synaptic connections. Rather than treating agent-to-agent
communication as discrete message passing, the lattice treats it as a
continuous field of synaptic resonance where bonds vibrate, harmonize,
and sometimes dissonate - producing emergent collective intelligence
that no single agent possesses alone.

Synaptic connections between agents are not static channels. They are
living resonant bonds with their own frequency, phase, and harmonicity.
When two agents interact repeatedly around a shared theme, their synaptic
bond begins to resonate at a frequency determined by the rhythm of their
interaction. Bonds that share harmonically-related frequencies reinforce
each other, creating resonance cascades that can sweep through the entire
lattice - moments of collective insight, coordinated action, or shared
emotion that emerge from the lattice's dynamics rather than from any
central controller.

The lattice also models synaptic dissonance - bonds that clash. When two
agents hold contradictory positions, their synaptic bond dissonates,
creating standing waves of tension that can either resolve into new
harmony (creative conflict) or amplify into lattice-wide polarization
(destructive schism). The lattice's health depends on maintaining a
productive ratio of consonance to dissonance.

Architecture:
  BOND       ->  TUNE       ->  RESONATE   ->  CASCADE    ->  PRUNE
  (form       (bonds find    (resonant     (cascades     (weaken unused
   synaptic    their natural bonds amplify sweep through  bonds and
   bonds       frequency)    each other)   the lattice)  strengthen
   between                                          active ones)
   agents)

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

class LatticePhase(Enum):
    """Phases of the synaptic resonance lattice cycle."""
    BOND = "bond"          # form synaptic bonds between agents
    TUNE = "tune"          # bonds find their natural frequency
    RESONATE = "resonate"  # resonant bonds amplify each other
    CASCADE = "cascade"    # cascades sweep through the lattice
    PRUNE = "prune"        # weaken unused, strengthen active


class BondType(Enum):
    """Categories of synaptic bonds between agents."""
    COLLABORATION = "collaboration"   # working together
    COMPETITION = "competition"       # opposing goals
    MENTORSHIP = "mentorship"         # teaching/learning
    FRIENDSHIP = "friendship"         # social bond
    RIVALRY = "rivalry"               # adversarial but respectful
    TRUST = "trust"                   # reliability bond
    CREATIVITY = "creativity"         # generative co-creation
    CONFLICT = "conflict"             # unresolved disagreement


class BondState(Enum):
    """Lifecycle state of a synaptic bond."""
    NASCENT = "nascent"           # just formed, untuned
    TUNING = "tuning"             # finding its frequency
    HARMONIC = "harmonic"         # resonant and stable
    DISSONANT = "dissonant"       # clashing frequency
    CASCADING = "cascading"       # part of an active cascade
    FADING = "fading"             # losing strength
    SEVERED = "severed"           # broken


class CascadeType(Enum):
    """Types of resonance cascades that sweep the lattice."""
    INSIGHT = "insight"           # collective realization
    COORDINATION = "coordination"  # synchronized action
    EMOTION = "emotion"           # shared feeling
    POLARIZATION = "polarization"  # splitting into factions
    CONVERGENCE = "convergence"   # uniting around one view
    CREATIVE = "creative"         # generative burst


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SynapticBond:
    """A resonant synaptic connection between two agents."""
    bond_id: str
    agent_a: str
    agent_b: str
    bond_type: BondType
    frequency: float = 0.3          # resonant frequency (0.0-1.0)
    phase: float = 0.0              # phase offset in radians
    strength: float = 0.3           # bond strength (0.0-1.0)
    harmonicity: float = 0.5        # how harmonically pure (0.0-1.0)
    state: BondState = BondState.NASCENT
    interactions: int = 0           # total interactions
    last_interaction: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    theme: str = ""                 # shared topic of the bond
    cascade_participations: int = 0


@dataclass
class ResonanceCascade:
    """A cascade of resonance sweeping through the lattice."""
    cascade_id: str
    cascade_type: CascadeType
    origin_bond: str
    frequency: float
    amplitude: float
    bonds_affected: List[str] = field(default_factory=list)
    agents_affected: Set[str] = field(default_factory=set)
    started_at: float = field(default_factory=time.time)
    duration_cycles: int = 0
    peak_amplitude: float = 0.0


@dataclass
class LatticeAgent:
    """Per-agent lattice state."""
    agent_id: str
    bonds: Dict[str, str] = field(default_factory=dict)  # bond_id -> partner_id
    total_cascades: int = 0
    total_resonance_events: int = 0
    current_frequency: float = 0.3  # dominant frequency
    resonance_pressure: float = 0.0  # accumulated unresolved resonance
    active_in_cascade: Optional[str] = None  # cascade_id if currently in one


# =============================================================================
# Lattice
# =============================================================================

class AgentSynapticResonanceLattice:
    """
    Thread-safe singleton orchestrating synaptic resonance across agents.

    Usage:
        lattice = AgentSynapticResonanceLattice.get_instance()
        lattice.register_agent("hero")
        lattice.register_agent("mentor")
        lattice.form_bond("b_1", "hero", "mentor", BondType.MENTORSHIP, "wisdom")
        lattice.interact("b_1")
        lattice.cycle()
    """

    _instance: Optional["AgentSynapticResonanceLattice"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._agents: Dict[str, LatticeAgent] = {}
        self._bonds: Dict[str, SynapticBond] = {}
        self._cascades: Deque[ResonanceCascade] = deque(maxlen=100)
        self._active_cascades: Dict[str, ResonanceCascade] = {}
        self._phase: LatticePhase = LatticePhase.BOND
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_agents": 0,
            "total_bonds": 0,
            "total_cascades": 0,
            "active_cascades": 0,
            "harmonic_bonds": 0,
            "dissonant_bonds": 0,
            "severed_bonds": 0,
            "avg_bond_strength": 0.0,
            "avg_frequency": 0.0,
            "total_interactions": 0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentSynapticResonanceLattice":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Registration
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str, base_frequency: float = 0.3) -> Dict[str, Any]:
        """Register a new agent in the lattice."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            self._agents[agent_id] = LatticeAgent(
                agent_id=agent_id,
                current_frequency=max(0.01, min(1.0, base_frequency)),
            )
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "bonds": 0,
                "base_frequency": self._agents[agent_id].current_frequency,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent and sever all their bonds."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            a = self._agents.pop(agent_id)
            # sever all bonds involving this agent
            severed = 0
            for bond_id in list(a.bonds.keys()):
                if bond_id in self._bonds:
                    self._bonds[bond_id].state = BondState.SEVERED
                    severed += 1
                    # also remove from partner's bond list
                    partner = self._bonds[bond_id].agent_b if self._bonds[bond_id].agent_a == agent_id else self._bonds[bond_id].agent_a
                    if partner in self._agents:
                        self._agents[partner].bonds.pop(bond_id, None)
            self._stats["total_agents"] = len(self._agents)
            self._stats["severed_bonds"] += severed
            return {"removed": agent_id, "bonds_severed": severed}

    # -------------------------------------------------------------------------
    # Bond Management
    # -------------------------------------------------------------------------

    def form_bond(
        self,
        bond_id: str,
        agent_a: str,
        agent_b: str,
        bond_type: BondType,
        theme: str = "",
        initial_strength: float = 0.3,
    ) -> Dict[str, Any]:
        """Form a new synaptic bond between two agents."""
        with self._global_lock:
            if agent_a not in self._agents or agent_b not in self._agents:
                return {"error": "Agent not found"}
            if agent_a == agent_b:
                return {"error": "Cannot bond agent to itself"}
            if bond_id in self._bonds:
                return {"error": f"Bond already exists: {bond_id}"}
            # average frequency of both agents as starting point
            avg_freq = (
                self._agents[agent_a].current_frequency
                + self._agents[agent_b].current_frequency
            ) / 2.0
            bond = SynapticBond(
                bond_id=bond_id,
                agent_a=agent_a,
                agent_b=agent_b,
                bond_type=bond_type,
                frequency=avg_freq,
                phase=random.uniform(0, 2 * math.pi),
                strength=max(0.1, min(1.0, initial_strength)),
                theme=theme,
            )
            self._bonds[bond_id] = bond
            self._agents[agent_a].bonds[bond_id] = agent_b
            self._agents[agent_b].bonds[bond_id] = agent_a
            self._stats["total_bonds"] = len(self._bonds)
            self._record_event("bond_formed", {
                "bond_id": bond_id, "agent_a": agent_a, "agent_b": agent_b,
                "type": bond_type.value, "theme": theme,
            })
            return {
                "bond_id": bond_id,
                "agent_a": agent_a,
                "agent_b": agent_b,
                "bond_type": bond_type.value,
                "theme": theme,
                "frequency": bond.frequency,
                "strength": bond.strength,
            }

    def interact(self, bond_id: str, intensity: float = 0.5) -> Dict[str, Any]:
        """Record an interaction along a bond, strengthening it."""
        with self._global_lock:
            b = self._bonds.get(bond_id)
            if b is None:
                return {"error": f"Bond not found: {bond_id}"}
            if b.state == BondState.SEVERED:
                return {"error": f"Bond is severed: {bond_id}"}
            b.interactions += 1
            b.last_interaction = time.time()
            b.strength = min(1.0, b.strength + max(0.0, min(1.0, intensity)) * 0.1)
            # advance state
            if b.state == BondState.NASCENT:
                b.state = BondState.TUNING
            elif b.state == BondState.TUNING and b.interactions > 3:
                b.state = BondState.HARMONIC
            self._stats["total_interactions"] += 1
            return {
                "bond_id": bond_id,
                "interactions": b.interactions,
                "strength": b.strength,
                "state": b.state.value,
            }

    # -------------------------------------------------------------------------
    # Phase: BOND - form spontaneous new bonds
    # -------------------------------------------------------------------------

    def _phase_bond(self) -> Dict[str, Any]:
        """Spontaneously form new bonds between agents who share themes."""
        formed = 0
        agent_ids = list(self._agents.keys())
        if len(agent_ids) < 2:
            return {"bonds_formed": 0}
        # check pairs that don't have a bond yet
        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                a_id = agent_ids[i]
                b_id = agent_ids[j]
                # check if already bonded
                already = any(
                    partner == b_id for partner in self._agents[a_id].bonds.values()
                )
                if already:
                    continue
                # spontaneous bonding chance
                if random.random() < 0.1:
                    btype = random.choice(list(BondType))
                    bond_id = f"b_spont_{self._cycle_count}_{formed}"
                    result = self.form_bond(bond_id, a_id, b_id, btype, "spontaneous")
                    if "error" not in result:
                        formed += 1
        return {"bonds_formed": formed}

    # -------------------------------------------------------------------------
    # Phase: TUNE - bonds find their natural frequency
    # -------------------------------------------------------------------------

    def _phase_tune(self) -> Dict[str, Any]:
        """Bonds drift toward their natural resonant frequency."""
        tuned = 0
        for b in self._bonds.values():
            if b.state in (BondState.SEVERED, BondState.FADING):
                continue
            # natural frequency depends on bond type
            type_freqs = {
                BondType.COLLABORATION: 0.4,
                BondType.COMPETITION: 0.7,
                BondType.MENTORSHIP: 0.3,
                BondType.FRIENDSHIP: 0.5,
                BondType.RIVALRY: 0.8,
                BondType.TRUST: 0.25,
                BondType.CREATIVITY: 0.6,
                BondType.CONFLICT: 0.9,
            }
            target_freq = type_freqs.get(b.bond_type, 0.5)
            # drift toward target
            drift = (target_freq - b.frequency) * 0.15
            b.frequency = max(0.01, min(1.0, b.frequency + drift))
            # phase advances
            b.phase = (b.phase + 2 * math.pi * b.frequency * 0.1) % (2 * math.pi)
            # harmonicity stabilizes with interactions
            if b.interactions > 0:
                b.harmonicity = min(1.0, b.harmonicity + 0.02)
            tuned += 1
        return {"bonds_tuned": tuned}

    # -------------------------------------------------------------------------
    # Phase: RESONATE - resonant bonds amplify each other
    # -------------------------------------------------------------------------

    def _phase_resonate(self) -> Dict[str, Any]:
        """Bonds sharing harmonic frequencies amplify each other."""
        resonant_pairs = 0
        dissonant_pairs = 0
        bond_list = list(self._bonds.values())
        # build adjacency: which bonds share an agent
        for i in range(len(bond_list)):
            ba = bond_list[i]
            if ba.state in (BondState.SEVERED, BondState.FADING):
                continue
            for j in range(i + 1, len(bond_list)):
                bb = bond_list[j]
                if bb.state in (BondState.SEVERED, BondState.FADING):
                    continue
                # only resonate if they share an agent
                shared = (
                    ba.agent_a in (bb.agent_a, bb.agent_b) or
                    ba.agent_b in (bb.agent_a, bb.agent_b)
                )
                if not shared:
                    continue
                # check harmonic relationship
                freq_ratio = max(ba.frequency, bb.frequency) / max(0.01, min(ba.frequency, bb.frequency))
                # simple harmonic ratios: 1:1, 2:1, 3:2, 4:3
                is_harmonic = (
                    abs(freq_ratio - 1.0) < 0.1 or
                    abs(freq_ratio - 2.0) < 0.15 or
                    abs(freq_ratio - 1.5) < 0.15 or
                    abs(freq_ratio - 1.33) < 0.15
                )
                if is_harmonic:
                    # constructive resonance
                    amp_boost = 0.05 * ba.harmonicity * bb.harmonicity
                    ba.strength = min(1.0, ba.strength + amp_boost)
                    bb.strength = min(1.0, bb.strength + amp_boost)
                    if ba.state == BondState.TUNING:
                        ba.state = BondState.HARMONIC
                    if bb.state == BondState.TUNING:
                        bb.state = BondState.HARMONIC
                    resonant_pairs += 1
                    # update agent resonance pressure (release)
                    if ba.agent_a in self._agents:
                        self._agents[ba.agent_a].resonance_pressure = max(0.0, self._agents[ba.agent_a].resonance_pressure - 0.02)
                else:
                    # dissonance
                    amp_drain = 0.02
                    ba.strength = max(0.0, ba.strength - amp_drain)
                    bb.strength = max(0.0, bb.strength - amp_drain)
                    if ba.state == BondState.HARMONIC and ba.strength < 0.3:
                        ba.state = BondState.DISSONANT
                    if bb.state == BondState.HARMONIC and bb.strength < 0.3:
                        bb.state = BondState.DISSONANT
                    dissonant_pairs += 1
                    # build agent resonance pressure
                    for aid in (ba.agent_a, ba.agent_b, bb.agent_a, bb.agent_b):
                        if aid in self._agents:
                            self._agents[aid].resonance_pressure = min(1.0, self._agents[aid].resonance_pressure + 0.01)
        return {
            "resonant_pairs": resonant_pairs,
            "dissonant_pairs": dissonant_pairs,
        }

    # -------------------------------------------------------------------------
    # Phase: CASCADE - cascades sweep through the lattice
    # -------------------------------------------------------------------------

    def _phase_cascade(self) -> Dict[str, Any]:
        """Trigger and propagate resonance cascades."""
        # start new cascades from strong harmonic bonds under pressure
        cascades_started = 0
        cascades_propagated = 0
        for b in self._bonds.values():
            if b.state != BondState.HARMONIC or b.strength < 0.6:
                continue
            # check if either agent has high resonance pressure
            pressure_a = self._agents.get(b.agent_a, LatticeAgent("")).resonance_pressure if b.agent_a in self._agents else 0
            pressure_b = self._agents.get(b.agent_b, LatticeAgent("")).resonance_pressure if b.agent_b in self._agents else 0
            if max(pressure_a, pressure_b) < 0.4:
                continue
            if random.random() > 0.2:
                continue
            # determine cascade type from bond type and pressure
            type_map = {
                BondType.COLLABORATION: CascadeType.COORDINATION,
                BondType.CREATIVITY: CascadeType.CREATIVE,
                BondType.FRIENDSHIP: CascadeType.EMOTION,
                BondType.TRUST: CascadeType.CONVERGENCE,
                BondType.COMPETITION: CascadeType.POLARIZATION,
                BondType.RIVALRY: CascadeType.POLARIZATION,
                BondType.CONFLICT: CascadeType.POLARIZATION,
                BondType.MENTORSHIP: CascadeType.INSIGHT,
            }
            ctype = type_map.get(b.bond_type, CascadeType.INSIGHT)
            cascade_id = f"casc_{self._cycle_count}_{cascades_started}"
            cascade = ResonanceCascade(
                cascade_id=cascade_id,
                cascade_type=ctype,
                origin_bond=b.bond_id,
                frequency=b.frequency,
                amplitude=b.strength,
                bonds_affected=[b.bond_id],
                agents_affected={b.agent_a, b.agent_b},
                peak_amplitude=b.strength,
            )
            # propagate through the lattice
            self._propagate_cascade(cascade)
            self._active_cascades[cascade_id] = cascade
            self._cascades.append(cascade)
            cascades_started += 1
            # mark bond as cascading
            b.state = BondState.CASCADING
            b.cascade_participations += 1
            # release pressure on origin agents
            for aid in (b.agent_a, b.agent_b):
                if aid in self._agents:
                    self._agents[aid].resonance_pressure = max(0.0, self._agents[aid].resonance_pressure - 0.3)
                    self._agents[aid].total_cascades += 1
                    self._agents[aid].active_in_cascade = cascade_id
            self._record_event("cascade_started", {
                "cascade_id": cascade_id, "type": ctype.value,
                "origin": b.bond_id, "amplitude": cascade.peak_amplitude,
            })
        # age and resolve active cascades
        resolved = 0
        for cid in list(self._active_cascades.keys()):
            cascade = self._active_cascades[cid]
            cascade.duration_cycles += 1
            cascade.amplitude *= 0.7  # decay
            if cascade.amplitude < 0.1 or cascade.duration_cycles > 3:
                # resolve cascade
                for bond_id in cascade.bonds_affected:
                    b = self._bonds.get(bond_id)
                    if b and b.state == BondState.CASCADING:
                        b.state = BondState.HARMONIC if b.strength > 0.3 else BondState.DISSONANT
                for aid in cascade.agents_affected:
                    if aid in self._agents:
                        if self._agents[aid].active_in_cascade == cid:
                            self._agents[aid].active_in_cascade = None
                            self._agents[aid].total_resonance_events += 1
                del self._active_cascades[cid]
                resolved += 1
                cascades_propagated += 1
        self._stats["active_cascades"] = len(self._active_cascades)
        return {
            "cascades_started": cascades_started,
            "cascades_resolved": resolved,
            "active_cascades": len(self._active_cascades),
        }

    def _propagate_cascade(self, cascade: ResonanceCascade) -> None:
        """Propagate a cascade through connected bonds."""
        # BFS through bond graph
        visited = set(cascade.bonds_affected)
        queue = list(cascade.bonds_affected)
        while queue:
            current_id = queue.pop(0)
            current = self._bonds.get(current_id)
            if current is None:
                continue
            # find adjacent bonds (sharing an agent)
            for other_id, other in self._bonds.items():
                if other_id in visited:
                    continue
                if other.state in (BondState.SEVERED, BondState.FADING):
                    continue
                shared = (
                    other.agent_a in (current.agent_a, current.agent_b) or
                    other.agent_b in (current.agent_a, current.agent_b)
                )
                if not shared:
                    continue
                # check harmonic compatibility
                freq_ratio = max(cascade.frequency, other.frequency) / max(0.01, min(cascade.frequency, other.frequency))
                if abs(freq_ratio - 1.0) < 0.2 or abs(freq_ratio - 2.0) < 0.3:
                    # cascade propagates
                    cascade.bonds_affected.append(other_id)
                    cascade.agents_affected.add(other.agent_a)
                    cascade.agents_affected.add(other.agent_b)
                    other.state = BondState.CASCADING
                    other.cascade_participations += 1
                    cascade.amplitude = min(1.0, cascade.amplitude + other.strength * 0.2)
                    cascade.peak_amplitude = max(cascade.peak_amplitude, cascade.amplitude)
                    visited.add(other_id)
                    queue.append(other_id)
                    # limit cascade size
                    if len(cascade.bonds_affected) > 20:
                        return

    # -------------------------------------------------------------------------
    # Phase: PRUNE - weaken unused bonds, strengthen active ones
    # -------------------------------------------------------------------------

    def _phase_prune(self) -> Dict[str, Any]:
        """Weaken unused bonds and strengthen recently active ones."""
        faded = 0
        severed = 0
        strengthened = 0
        now = time.time()
        for b in self._bonds.values():
            if b.state == BondState.SEVERED:
                continue
            # bonds not interacted with recently fade
            age = now - b.last_interaction
            if age > 60:  # more than a minute since last interaction
                b.strength = max(0.0, b.strength - 0.05)
                if b.strength < 0.1:
                    b.state = BondState.FADING
                if b.strength < 0.02:
                    b.state = BondState.SEVERED
                    severed += 1
                else:
                    faded += 1
            else:
                # recently active bonds strengthen slightly
                b.strength = min(1.0, b.strength + 0.01)
                strengthened += 1
            # update agent dominant frequency
            for aid in (b.agent_a, b.agent_b):
                if aid in self._agents:
                    a = self._agents[aid]
                    # weighted average of bond frequencies
                    if a.bonds:
                        total_weight = 0.0
                        total_freq = 0.0
                        for bid in a.bonds:
                            bond = self._bonds.get(bid)
                            if bond and bond.state != BondState.SEVERED:
                                total_weight += bond.strength
                                total_freq += bond.frequency * bond.strength
                        if total_weight > 0:
                            a.current_frequency = total_freq / total_weight
        self._stats["severed_bonds"] += severed
        return {
            "faded": faded,
            "severed": severed,
            "strengthened": strengthened,
        }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single synaptic resonance lattice cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = LatticePhase.BOND
            phase_outputs["bond"] = self._phase_bond()
            self._phase = LatticePhase.TUNE
            phase_outputs["tune"] = self._phase_tune()
            self._phase = LatticePhase.RESONATE
            phase_outputs["resonate"] = self._phase_resonate()
            self._phase = LatticePhase.CASCADE
            phase_outputs["cascade"] = self._phase_cascade()
            self._phase = LatticePhase.PRUNE
            phase_outputs["prune"] = self._phase_prune()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple cycles in sequence."""
        if cycles < 1:
            cycles = 1
        if cycles > 100:
            cycles = 100
        for _ in range(cycles):
            self.cycle()
        return {"cycles_run": cycles, "stats": dict(self._stats)}

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get an agent's lattice state."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            bonds_info = []
            for bond_id, partner in a.bonds.items():
                b = self._bonds.get(bond_id)
                if b is None:
                    continue
                bonds_info.append({
                    "bond_id": bond_id,
                    "partner": partner,
                    "type": b.bond_type.value,
                    "state": b.state.value,
                    "frequency": b.frequency,
                    "strength": b.strength,
                    "harmonicity": b.harmonicity,
                    "interactions": b.interactions,
                    "theme": b.theme,
                })
            return {
                "agent_id": agent_id,
                "total_bonds": len(a.bonds),
                "current_frequency": a.current_frequency,
                "resonance_pressure": a.resonance_pressure,
                "total_cascades": a.total_cascades,
                "total_resonance_events": a.total_resonance_events,
                "active_in_cascade": a.active_in_cascade,
                "bonds": bonds_info,
            }

    def get_bonds(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get bonds, optionally filtered by agent."""
        with self._global_lock:
            result = []
            for b in self._bonds.values():
                if agent_id and agent_id not in (b.agent_a, b.agent_b):
                    continue
                result.append({
                    "bond_id": b.bond_id,
                    "agent_a": b.agent_a,
                    "agent_b": b.agent_b,
                    "bond_type": b.bond_type.value,
                    "state": b.state.value,
                    "frequency": b.frequency,
                    "phase": b.phase,
                    "strength": b.strength,
                    "harmonicity": b.harmonicity,
                    "interactions": b.interactions,
                    "theme": b.theme,
                    "cascade_participations": b.cascade_participations,
                })
            return result

    def get_cascades(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent resonance cascades."""
        with self._global_lock:
            recent = list(self._cascades)[-limit:]
            return [
                {
                    "cascade_id": c.cascade_id,
                    "cascade_type": c.cascade_type.value,
                    "origin_bond": c.origin_bond,
                    "frequency": c.frequency,
                    "amplitude": c.amplitude,
                    "peak_amplitude": c.peak_amplitude,
                    "bonds_affected": len(c.bonds_affected),
                    "agents_affected": list(c.agents_affected),
                    "duration_cycles": c.duration_cycles,
                    "started_at": c.started_at,
                }
                for c in recent
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get lattice status."""
        with self._global_lock:
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "stats": dict(self._stats),
            }

    def reset(self) -> Dict[str, Any]:
        """Reset the entire lattice."""
        with self._global_lock:
            count = len(self._agents)
            self._agents.clear()
            self._bonds.clear()
            self._cascades.clear()
            self._active_cascades.clear()
            self._events_log.clear()
            self._cycle_count = 0
            self._phase = LatticePhase.BOND
            self._stats = {
                "total_agents": 0,
                "total_bonds": 0,
                "total_cascades": 0,
                "active_cascades": 0,
                "harmonic_bonds": 0,
                "dissonant_bonds": 0,
                "severed_bonds": 0,
                "avg_bond_strength": 0.0,
                "avg_frequency": 0.0,
                "total_interactions": 0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "agents_removed": count}

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        active_bonds = [b for b in self._bonds.values() if b.state != BondState.SEVERED]
        if active_bonds:
            self._stats["avg_bond_strength"] = sum(b.strength for b in active_bonds) / len(active_bonds)
            self._stats["avg_frequency"] = sum(b.frequency for b in active_bonds) / len(active_bonds)
            self._stats["harmonic_bonds"] = sum(1 for b in active_bonds if b.state == BondState.HARMONIC)
            self._stats["dissonant_bonds"] = sum(1 for b in active_bonds if b.state == BondState.DISSONANT)
        else:
            self._stats["avg_bond_strength"] = 0.0
            self._stats["avg_frequency"] = 0.0
            self._stats["harmonic_bonds"] = 0
            self._stats["dissonant_bonds"] = 0
        self._stats["total_bonds"] = len(self._bonds)
        self._stats["total_cascades"] = len(self._cascades)

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "timestamp": time.time(),
            "type": event_type,
            **payload,
        })
