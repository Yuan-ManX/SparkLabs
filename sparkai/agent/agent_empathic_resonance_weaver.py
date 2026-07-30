"""
SparkLabs Agent - Empathic Resonance Weaver

The AgentEmpathicResonanceWeaver models how agents develop empathic bonds
with one another. Empathy is treated as a woven fabric of resonant
connections: each agent carries an emotional frequency, and when two
frequencies meet they either consonate, dissonate, or complement each
other. Over repeated shared experiences these interactions consolidate
into stable empathic bonds that color the agent's emotional repertoire.

The weaver treats empathic connection as a five-phase cycle. Agents first
attune to the emotional frequencies around them, then resonate with what
they sense. Resonant experiences are reflected upon, which grows emotional
intelligence. Bonds that are not reinforced dissolve over time, while
bonds that survive reflection integrate into the agent's long-term
emotional makeup - becoming part of who the agent is.

Architecture:
  ATTUNE     ->  RESONATE   ->  REFLECT    ->  DISSOLVE   ->  INTEGRATE
  (agents       (shared       (agents       (unused        (stable bonds
   calibrate    emotions      reflect on    bonds fade     fold into the
   to nearby    amplify or    empathic      and sever)     agent's
   frequencies  clash)        moments,      emotional
   and form     growing       repertoire)
   baseline     emotional
   empathy)     intelligence)

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

class EmpathicPhase(Enum):
    """Phases of the empathic resonance cycle."""
    ATTUNE = "attune"           # calibrate to nearby emotional frequencies
    RESONATE = "resonate"       # shared emotions amplify or clash
    REFLECT = "reflect"         # reflect on empathic moments
    DISSOLVE = "dissolve"       # unused bonds fade and sever
    INTEGRATE = "integrate"     # stable bonds fold into the agent


class EmotionalFrequency(Enum):
    """Emotional frequencies an agent can carry."""
    JOY = "joy"
    GRIEF = "grief"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    SERENITY = "serenity"
    MELANCHOLY = "melancholy"
    ZEAL = "zeal"
    DREAD = "dread"


class BondState(Enum):
    """Lifecycle state of an empathic bond."""
    NASCENT = "nascent"             # just formed, fragile
    TUNING = "tuning"               # calibrating to the other agent
    RESONANT = "resonant"           # actively resonating
    HARMONIC = "harmonic"           # integrated and stable
    DISSOLVING = "dissolving"       # fading from neglect
    SEVERED = "severed"             # broken


class ResonanceType(Enum):
    """Quality of resonance between two emotional frequencies."""
    CONSONANT = "consonant"         # aligned emotions amplify
    DISSONANT = "dissonant"         # conflicting emotions create tension
    COMPLEMENTARY = "complementary"  # different emotions balance
    NEUTRAL = "neutral"             # no significant interaction


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class EmpathicBond:
    """A resonant empathic bond between two agents."""
    bond_id: str
    agent_a: str
    agent_b: str
    frequency: EmotionalFrequency
    state: BondState = BondState.NASCENT
    strength: float = 0.1                          # 0.0-1.0
    resonance_type: ResonanceType = ResonanceType.NEUTRAL
    consonance: float = 0.0                        # 0.0-1.0
    dissonance: float = 0.0                        # 0.0-1.0
    shared_experiences: int = 0
    created_at: float = field(default_factory=time.time)
    last_resonated: float = field(default_factory=time.time)


@dataclass
class EmpathicAgent:
    """The empathic state of a single agent."""
    agent_id: str
    empathy_capacity: float = 0.5                  # 0.0-1.0
    emotional_intelligence: float = 0.3            # 0.0-1.0
    current_frequency: EmotionalFrequency = EmotionalFrequency.SERENITY
    frequency_intensity: float = 0.3               # 0.0-1.0
    bonds: Dict[str, EmpathicBond] = field(default_factory=dict)
    total_bonds: int = 0
    total_resonances: int = 0
    total_dissonances: int = 0
    total_integrations: int = 0
    reflections: List["EmpathicReflection"] = field(default_factory=list)


@dataclass
class EmpathicReflection:
    """A recorded reflection an agent has about an empathic bond."""
    reflection_id: str
    agent_id: str
    bond_id: str
    insight: str
    timestamp: float = field(default_factory=time.time)


# =============================================================================
# Engine
# =============================================================================

class AgentEmpathicResonanceWeaver:
    """
    Thread-safe singleton orchestrating empathic resonance across agents.

    Usage:
        weaver = AgentEmpathicResonanceWeaver.get_instance()
        weaver.register_agent("hero")
        weaver.register_agent("ally")
        weaver.set_emotion("hero", EmotionalFrequency.JOY, 0.7)
        weaver.set_emotion("ally", EmotionalFrequency.JOY, 0.6)
        weaver.form_bond("hero", "ally")
        weaver.experience_together("hero", "ally", "shared victory")
        weaver.cycle()
    """

    _instance: Optional["AgentEmpathicResonanceWeaver"] = None
    _lock = threading.RLock()

    # Tuning constants
    _RESONANCE_THRESHOLD = 0.3      # minimum bond strength for resonance
    _CONSONANCE_BOOST = 0.15        # how much consonant resonance strengthens bonds
    _DISSONANCE_PENALTY = 0.10      # how much dissonant resonance weakens bonds
    _DISSOLUTION_RATE = 0.05        # how fast unused bonds dissolve
    _INTEGRATION_THRESHOLD = 0.65   # bond strength needed for integration
    _REFLECTION_THRESHOLD = 0.5     # emotional intelligence needed for reflection
    _EI_GROWTH_RATE = 0.08          # how much emotional intelligence grows per reflection

    # Opposing frequency pairs - used to classify dissonant resonance
    _OPPOSING_PAIRS: Dict[EmotionalFrequency, EmotionalFrequency] = {
        EmotionalFrequency.JOY: EmotionalFrequency.GRIEF,
        EmotionalFrequency.GRIEF: EmotionalFrequency.JOY,
        EmotionalFrequency.ANGER: EmotionalFrequency.FEAR,
        EmotionalFrequency.FEAR: EmotionalFrequency.ANGER,
        EmotionalFrequency.TRUST: EmotionalFrequency.DISGUST,
        EmotionalFrequency.DISGUST: EmotionalFrequency.TRUST,
        EmotionalFrequency.SURPRISE: EmotionalFrequency.ANTICIPATION,
        EmotionalFrequency.ANTICIPATION: EmotionalFrequency.SURPRISE,
        EmotionalFrequency.SERENITY: EmotionalFrequency.MELANCHOLY,
        EmotionalFrequency.MELANCHOLY: EmotionalFrequency.SERENITY,
        EmotionalFrequency.ZEAL: EmotionalFrequency.DREAD,
        EmotionalFrequency.DREAD: EmotionalFrequency.ZEAL,
    }

    def __init__(self) -> None:
        self._agents: Dict[str, EmpathicAgent] = {}
        self._bonds: Dict[str, EmpathicBond] = {}
        self._reflections: Deque[EmpathicReflection] = deque(maxlen=500)
        self._phase: EmpathicPhase = EmpathicPhase.ATTUNE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = self._init_stats()

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentEmpathicResonanceWeaver":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        empathy_capacity: float = 0.5,
        emotional_intelligence: float = 0.3,
    ) -> Dict[str, Any]:
        """Register a new agent in the empathic weaver."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            agent = EmpathicAgent(
                agent_id=agent_id,
                empathy_capacity=max(0.0, min(1.0, empathy_capacity)),
                emotional_intelligence=max(0.0, min(1.0, emotional_intelligence)),
            )
            self._agents[agent_id] = agent
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "empathy_capacity": agent.empathy_capacity,
                "emotional_intelligence": agent.emotional_intelligence,
                "current_frequency": agent.current_frequency.value,
                "frequency_intensity": agent.frequency_intensity,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent and sever all of its empathic bonds."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            agent = self._agents[agent_id]
            severed: List[str] = []
            # Sever every bond this agent participates in
            for bond_id in list(agent.bonds.keys()):
                bond = self._bonds.get(bond_id)
                if bond is not None:
                    other_id = bond.agent_b if bond.agent_a == agent_id else bond.agent_a
                    other = self._agents.get(other_id)
                    if other is not None:
                        other.bonds.pop(bond_id, None)
                    bond.state = BondState.SEVERED
                    severed.append(bond_id)
                    del self._bonds[bond_id]
            del self._agents[agent_id]
            self._stats["total_agents"] = len(self._agents)
            self._stats["total_bonds"] = len(self._bonds)
            self._record_event("agent_removed", {
                "agent_id": agent_id, "severed_bonds": len(severed),
            })
            return {"removed": agent_id, "severed_bonds": len(severed)}

    def set_emotion(
        self,
        agent_id: str,
        frequency: EmotionalFrequency,
        intensity: float = 0.5,
    ) -> Dict[str, Any]:
        """Set the agent's current emotional frequency and intensity."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            agent.current_frequency = frequency
            agent.frequency_intensity = max(0.0, min(1.0, intensity))
            self._record_event("emotion_set", {
                "agent_id": agent_id,
                "frequency": frequency.value,
                "intensity": agent.frequency_intensity,
            })
            return {
                "agent_id": agent_id,
                "current_frequency": agent.current_frequency.value,
                "frequency_intensity": agent.frequency_intensity,
            }

    # -------------------------------------------------------------------------
    # Bond Management
    # -------------------------------------------------------------------------

    def form_bond(self, agent_a: str, agent_b: str) -> Dict[str, Any]:
        """Create a NASCENT empathic bond between two agents."""
        with self._global_lock:
            if agent_a not in self._agents:
                return {"error": f"Agent not found: {agent_a}"}
            if agent_b not in self._agents:
                return {"error": f"Agent not found: {agent_b}"}
            if agent_a == agent_b:
                return {"error": "Cannot bond an agent with itself"}
            # Reject duplicate bonds between the same pair
            for existing in self._bonds.values():
                if (existing.agent_a == agent_a and existing.agent_b == agent_b) or \
                   (existing.agent_a == agent_b and existing.agent_b == agent_a):
                    if existing.state != BondState.SEVERED:
                        return {"error": f"Bond already exists between {agent_a} and {agent_b}"}
            agent_a_obj = self._agents[agent_a]
            bond_id = f"bond_{agent_a}_{agent_b}_{int(time.time() * 1000) % 100000}"
            bond = EmpathicBond(
                bond_id=bond_id,
                agent_a=agent_a,
                agent_b=agent_b,
                frequency=agent_a_obj.current_frequency,
                state=BondState.NASCENT,
                strength=0.1,
            )
            self._bonds[bond_id] = bond
            self._agents[agent_a].bonds[bond_id] = bond
            self._agents[agent_b].bonds[bond_id] = bond
            self._agents[agent_a].total_bonds += 1
            self._agents[agent_b].total_bonds += 1
            self._stats["total_bonds"] = len(self._bonds)
            self._record_event("bond_formed", {
                "bond_id": bond_id,
                "agent_a": agent_a,
                "agent_b": agent_b,
                "frequency": bond.frequency.value,
            })
            return {
                "bond_id": bond_id,
                "agent_a": agent_a,
                "agent_b": agent_b,
                "frequency": bond.frequency.value,
                "state": bond.state.value,
                "strength": bond.strength,
            }

    def experience_together(
        self,
        agent_a: str,
        agent_b: str,
        context_label: str = "",
    ) -> Dict[str, Any]:
        """Agents share an experience, strengthening their bond."""
        with self._global_lock:
            if agent_a not in self._agents:
                return {"error": f"Agent not found: {agent_a}"}
            if agent_b not in self._agents:
                return {"error": f"Agent not found: {agent_b}"}
            # Locate the bond between these two agents
            bond: Optional[EmpathicBond] = None
            for candidate in self._agents[agent_a].bonds.values():
                if candidate.agent_a == agent_b or candidate.agent_b == agent_b:
                    bond = candidate
                    break
            if bond is None:
                return {"error": f"No bond exists between {agent_a} and {agent_b}"}
            if bond.state == BondState.SEVERED:
                return {"error": f"Bond is severed: {bond.bond_id}"}
            a_obj = self._agents[agent_a]
            b_obj = self._agents[agent_b]
            # Shared experiences strengthen the bond and refresh resonance
            bond.shared_experiences += 1
            bond.last_resonated = time.time()
            # Strength grows with the harmonic mean of both agents' empathy capacity
            empathy_factor = (2 * a_obj.empathy_capacity * b_obj.empathy_capacity) / (
                a_obj.empathy_capacity + b_obj.empathy_capacity + 1e-9
            )
            bond.strength = min(1.0, bond.strength + 0.05 * empathy_factor)
            # If both agents share the same frequency, consonance rises
            if a_obj.current_frequency == b_obj.current_frequency:
                bond.consonance = min(1.0, bond.consonance + 0.05)
                bond.frequency = a_obj.current_frequency
            # Promote NASCENT bonds into TUNING once they have shared context
            if bond.state == BondState.NASCENT and bond.shared_experiences >= 1:
                bond.state = BondState.TUNING
            self._record_event("experience_shared", {
                "bond_id": bond.bond_id,
                "agent_a": agent_a,
                "agent_b": agent_b,
                "shared_experiences": bond.shared_experiences,
                "context": context_label,
            })
            return {
                "bond_id": bond.bond_id,
                "shared_experiences": bond.shared_experiences,
                "strength": round(bond.strength, 4),
                "state": bond.state.value,
                "context": context_label,
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single empathic resonance cycle across all five phases."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            # ATTUNE: agents attune to nearby agents' emotional frequencies
            self._phase = EmpathicPhase.ATTUNE
            phase_outputs["attune"] = self._phase_attune()
            # RESONATE: agents resonate with others' emotions
            self._phase = EmpathicPhase.RESONATE
            phase_outputs["resonate"] = self._phase_resonate()
            # REFLECT: agents reflect on empathic experiences
            self._phase = EmpathicPhase.REFLECT
            phase_outputs["reflect"] = self._phase_reflect()
            # DISSOLVE: weak bonds dissolve over distance/time
            self._phase = EmpathicPhase.DISSOLVE
            phase_outputs["dissolve"] = self._phase_dissolve()
            # INTEGRATE: stable bonds integrate into the agent's emotional repertoire
            self._phase = EmpathicPhase.INTEGRATE
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

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple empathic resonance cycles."""
        with self._global_lock:
            if cycles < 1 or cycles > 1000:
                return {"error": "cycles must be between 1 and 1000"}
            for _ in range(cycles):
                # Run the phase sequence directly since we already hold the lock.
                t0 = time.time()
                phase_outputs: Dict[str, Any] = {}
                self._phase = EmpathicPhase.ATTUNE
                phase_outputs["attune"] = self._phase_attune()
                self._phase = EmpathicPhase.RESONATE
                phase_outputs["resonate"] = self._phase_resonate()
                self._phase = EmpathicPhase.REFLECT
                phase_outputs["reflect"] = self._phase_reflect()
                self._phase = EmpathicPhase.DISSOLVE
                phase_outputs["dissolve"] = self._phase_dissolve()
                self._phase = EmpathicPhase.INTEGRATE
                phase_outputs["integrate"] = self._phase_integrate()
                self._cycle_count += 1
                self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
                self._update_stats()
            return {
                "cycles_run": cycles,
                "final_phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "stats": dict(self._stats),
            }

    # -------------------------------------------------------------------------
    # Phase Implementations
    # -------------------------------------------------------------------------

    def _phase_attune(self) -> Dict[str, Any]:
        """ATTUNE: agents calibrate to nearby emotional frequencies."""
        attuned = 0
        promoted = 0
        now = time.time()
        for agent in self._agents.values():
            # Emotional intensity decays gently toward a baseline of 0.3
            agent.frequency_intensity = agent.frequency_intensity * 0.95 + 0.3 * 0.05
            agent.frequency_intensity = max(0.0, min(1.0, agent.frequency_intensity))
            attuned += 1
        # NASCENT bonds with capable agents begin tuning to each other
        for bond in self._bonds.values():
            if bond.state != BondState.NASCENT:
                continue
            a_obj = self._agents.get(bond.agent_a)
            b_obj = self._agents.get(bond.agent_b)
            if a_obj is None or b_obj is None:
                continue
            if a_obj.empathy_capacity >= 0.2 and b_obj.empathy_capacity >= 0.2:
                bond.state = BondState.TUNING
                bond.last_resonated = now
                promoted += 1
        return {"attuned": attuned, "promoted_to_tuning": promoted}

    def _phase_resonate(self) -> Dict[str, Any]:
        """RESONATE: shared emotions amplify or clash within each bond."""
        resonated = 0
        dissonated = 0
        complemented = 0
        neutral = 0
        now = time.time()
        for bond in self._bonds.values():
            if bond.state in (BondState.SEVERED, BondState.NASCENT):
                continue
            if bond.strength < self._RESONANCE_THRESHOLD:
                continue
            a_obj = self._agents.get(bond.agent_a)
            b_obj = self._agents.get(bond.agent_b)
            if a_obj is None or b_obj is None:
                continue
            resonance_type, factor = self._classify_resonance(
                a_obj.current_frequency, b_obj.current_frequency,
                a_obj.frequency_intensity, b_obj.frequency_intensity,
            )
            bond.resonance_type = resonance_type
            if resonance_type == ResonanceType.CONSONANT:
                # Aligned emotions amplify the bond
                boost = self._CONSONANCE_BOOST * factor
                bond.strength = min(1.0, bond.strength + boost)
                bond.consonance = min(1.0, bond.consonance + boost * 0.5)
                bond.frequency = a_obj.current_frequency
                a_obj.total_resonances += 1
                b_obj.total_resonances += 1
                resonated += 1
            elif resonance_type == ResonanceType.DISSONANT:
                # Conflicting emotions create tension and weaken the bond
                penalty = self._DISSONANCE_PENALTY * factor
                bond.strength = max(0.0, bond.strength - penalty)
                bond.dissonance = min(1.0, bond.dissonance + penalty * 0.5)
                a_obj.total_dissonances += 1
                b_obj.total_dissonances += 1
                dissonated += 1
            elif resonance_type == ResonanceType.COMPLEMENTARY:
                # Different emotions balance each other; small steady growth
                growth = 0.03 * factor
                bond.strength = min(1.0, bond.strength + growth)
                bond.consonance = min(1.0, bond.consonance + growth * 0.3)
                complemented += 1
            else:
                neutral += 1
            bond.last_resonated = now
            # Promote TUNING bonds into RESONANT once they are strong enough
            if bond.state == BondState.TUNING and bond.strength >= self._RESONANCE_THRESHOLD:
                bond.state = BondState.RESONANT
        self._stats["total_resonances"] += resonated
        self._stats["total_dissonances"] += dissonated
        return {
            "resonated": resonated,
            "dissonated": dissonated,
            "complemented": complemented,
            "neutral": neutral,
        }

    def _phase_reflect(self) -> Dict[str, Any]:
        """REFLECT: agents reflect on empathic experiences, growing emotional intelligence."""
        reflections_created = 0
        ei_grown = 0
        now = time.time()
        for agent in self._agents.values():
            if agent.emotional_intelligence < self._REFLECTION_THRESHOLD:
                continue
            for bond in list(agent.bonds.values()):
                if bond.state == BondState.SEVERED:
                    continue
                # Only reflect on bonds that have resonated recently
                if now - bond.last_resonated > 10.0:
                    continue
                if bond.resonance_type == ResonanceType.NEUTRAL:
                    continue
                # Stochastic reflection: not every resonant moment is reflected upon
                if random.random() > agent.emotional_intelligence * 0.5:
                    continue
                other_id = bond.agent_b if bond.agent_a == agent.agent_id else bond.agent_a
                insight = self._compose_insight(agent.agent_id, other_id, bond)
                reflection = EmpathicReflection(
                    reflection_id=f"refl_{agent.agent_id}_{int(now * 1000) % 100000}_{reflections_created}",
                    agent_id=agent.agent_id,
                    bond_id=bond.bond_id,
                    insight=insight,
                    timestamp=now,
                )
                agent.reflections.append(reflection)
                self._reflections.append(reflection)
                # Emotional intelligence grows with each reflection
                agent.emotional_intelligence = min(
                    1.0, agent.emotional_intelligence + self._EI_GROWTH_RATE
                )
                ei_grown += 1
                reflections_created += 1
        self._stats["total_reflections"] += reflections_created
        return {"reflections_created": reflections_created, "ei_grown": ei_grown}

    def _phase_dissolve(self) -> Dict[str, Any]:
        """DISSOLVE: weak or neglected bonds fade and eventually sever."""
        dissolved = 0
        severed = 0
        now = time.time()
        to_sever: List[str] = []
        for bond in self._bonds.values():
            if bond.state == BondState.SEVERED:
                continue
            # Bonds neglected for a long time lose strength
            time_since_resonance = now - bond.last_resonated
            if time_since_resonance > 5.0:
                decay = self._DISSOLUTION_RATE * (1.0 + time_since_resonance / 20.0)
                bond.strength = max(0.0, bond.strength - decay)
                # Mark bonds that have weakened noticeably as dissolving
                if bond.state in (BondState.RESONANT, BondState.TUNING, BondState.HARMONIC) \
                        and bond.strength < self._RESONANCE_THRESHOLD:
                    bond.state = BondState.DISSOLVING
                    dissolved += 1
            # Bonds with effectively no strength are severed
            if bond.strength <= 0.01:
                bond.state = BondState.SEVERED
                to_sever.append(bond.bond_id)
                severed += 1
        # Remove severed bonds from the graph
        for bond_id in to_sever:
            bond = self._bonds.pop(bond_id, None)
            if bond is None:
                continue
            a_obj = self._agents.get(bond.agent_a)
            b_obj = self._agents.get(bond.agent_b)
            if a_obj is not None:
                a_obj.bonds.pop(bond_id, None)
            if b_obj is not None:
                b_obj.bonds.pop(bond_id, None)
            self._record_event("bond_severed", {"bond_id": bond_id})
        if to_sever:
            self._stats["total_bonds"] = len(self._bonds)
        return {"dissolved": dissolved, "severed": severed}

    def _phase_integrate(self) -> Dict[str, Any]:
        """INTEGRATE: stable bonds fold into the agent's emotional repertoire."""
        integrated = 0
        for bond in self._bonds.values():
            if bond.state != BondState.RESONANT:
                continue
            if bond.strength < self._INTEGRATION_THRESHOLD:
                continue
            a_obj = self._agents.get(bond.agent_a)
            b_obj = self._agents.get(bond.agent_b)
            if a_obj is None or b_obj is None:
                continue
            # The bond becomes harmonic and folds into both agents' repertoire
            bond.state = BondState.HARMONIC
            a_obj.total_integrations += 1
            b_obj.total_integrations += 1
            # Harmonic bonds expand empathy capacity slightly
            a_obj.empathy_capacity = min(1.0, a_obj.empathy_capacity + 0.01)
            b_obj.empathy_capacity = min(1.0, b_obj.empathy_capacity + 0.01)
            integrated += 1
            self._record_event("bond_integrated", {
                "bond_id": bond.bond_id,
                "agent_a": bond.agent_a,
                "agent_b": bond.agent_b,
                "frequency": bond.frequency.value,
            })
        self._stats["total_integrations"] += integrated
        return {"integrated": integrated}

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get the full empathic state of an agent."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent.agent_id,
                "empathy_capacity": round(agent.empathy_capacity, 4),
                "emotional_intelligence": round(agent.emotional_intelligence, 4),
                "current_frequency": agent.current_frequency.value,
                "frequency_intensity": round(agent.frequency_intensity, 4),
                "active_bonds": len(agent.bonds),
                "total_bonds": agent.total_bonds,
                "total_resonances": agent.total_resonances,
                "total_dissonances": agent.total_dissonances,
                "total_integrations": agent.total_integrations,
                "reflections_count": len(agent.reflections),
                "bonds": [self._summarize_bond(b) for b in agent.bonds.values()],
            }

    def get_bond(self, bond_id: str) -> Dict[str, Any]:
        """Get details of a specific empathic bond."""
        with self._global_lock:
            bond = self._bonds.get(bond_id)
            if bond is None:
                return {"error": f"Bond not found: {bond_id}"}
            return self._summarize_bond(bond)

    def get_all_bonds(self) -> List[Dict[str, Any]]:
        """List all empathic bonds."""
        with self._global_lock:
            return [self._summarize_bond(b) for b in self._bonds.values()]

    def get_reflections(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent reflections produced by an agent."""
        with self._global_lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return []
            recent = list(agent.reflections)[-limit:] if limit > 0 else list(agent.reflections)
            return [
                {
                    "reflection_id": r.reflection_id,
                    "agent_id": r.agent_id,
                    "bond_id": r.bond_id,
                    "insight": r.insight,
                    "timestamp": r.timestamp,
                }
                for r in recent
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent weaver events."""
        with self._global_lock:
            return list(self._events_log)[-limit:] if limit > 0 else list(self._events_log)

    def get_status(self) -> Dict[str, Any]:
        """Get global weaver status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_agents": len(self._agents),
                "total_bonds": len(self._bonds),
                "total_reflections": len(self._reflections),
                "stats": dict(self._stats),
            }

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire empathic weaver."""
        with self._global_lock:
            n_agents = len(self._agents)
            n_bonds = len(self._bonds)
            self._agents.clear()
            self._bonds.clear()
            self._reflections.clear()
            self._phase = EmpathicPhase.ATTUNE
            self._cycle_count = 0
            self._events_log.clear()
            self._stats = self._init_stats()
            return {"reset": True, "cleared_agents": n_agents, "cleared_bonds": n_bonds}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _init_stats(self) -> Dict[str, Any]:
        """Initialize the aggregate statistics dictionary."""
        return {
            "total_agents": 0,
            "total_bonds": 0,
            "total_resonances": 0,
            "total_dissonances": 0,
            "total_integrations": 0,
            "total_reflections": 0,
            "active_bonds": 0,
            "harmonic_bonds": 0,
            "resonant_bonds": 0,
            "dissolving_bonds": 0,
            "avg_bond_strength": 0.0,
            "avg_empathy_capacity": 0.0,
            "avg_emotional_intelligence": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    def _update_stats(self) -> None:
        """Recompute aggregate statistics from the current state."""
        active = [b for b in self._bonds.values() if b.state != BondState.SEVERED]
        self._stats["active_bonds"] = len(active)
        self._stats["harmonic_bonds"] = sum(1 for b in active if b.state == BondState.HARMONIC)
        self._stats["resonant_bonds"] = sum(1 for b in active if b.state == BondState.RESONANT)
        self._stats["dissolving_bonds"] = sum(1 for b in active if b.state == BondState.DISSOLVING)
        if active:
            self._stats["avg_bond_strength"] = sum(b.strength for b in active) / len(active)
        else:
            self._stats["avg_bond_strength"] = 0.0
        if self._agents:
            self._stats["avg_empathy_capacity"] = (
                sum(a.empathy_capacity for a in self._agents.values()) / len(self._agents)
            )
            self._stats["avg_emotional_intelligence"] = (
                sum(a.emotional_intelligence for a in self._agents.values()) / len(self._agents)
            )
        else:
            self._stats["avg_empathy_capacity"] = 0.0
            self._stats["avg_emotional_intelligence"] = 0.0

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a weaver event in the events log."""
        self._events_log.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })

    def _classify_resonance(
        self,
        freq_a: EmotionalFrequency,
        freq_b: EmotionalFrequency,
        intensity_a: float,
        intensity_b: float,
    ) -> Tuple[ResonanceType, float]:
        """
        Classify the resonance between two emotional frequencies.

        Returns the resonance type and a 0.0-1.0 factor that scales how
        strongly the resonance affects the bond.
        """
        # Either side too quiet to register a meaningful interaction
        if intensity_a < 0.15 or intensity_b < 0.15:
            return ResonanceType.NEUTRAL, 0.0
        # Intensity harmonic mean drives the resonance factor
        factor = math.tanh(intensity_a * intensity_b)
        if freq_a == freq_b:
            return ResonanceType.CONSONANT, factor
        if self._OPPOSING_PAIRS.get(freq_a) == freq_b:
            return ResonanceType.DISSONANT, factor
        return ResonanceType.COMPLEMENTARY, factor * 0.5

    def _compose_insight(self, agent_id: str, other_id: str, bond: EmpathicBond) -> str:
        """Compose a short reflection insight describing an empathic moment."""
        if bond.resonance_type == ResonanceType.CONSONANT:
            return f"{agent_id} felt shared {bond.frequency.value} with {other_id}"
        if bond.resonance_type == ResonanceType.DISSONANT:
            return f"{agent_id} sensed tension with {other_id} over {bond.frequency.value}"
        if bond.resonance_type == ResonanceType.COMPLEMENTARY:
            return f"{agent_id} found balance with {other_id} through {bond.frequency.value}"
        return f"{agent_id} noticed {other_id} quietly"

    def _summarize_bond(self, b: EmpathicBond) -> Dict[str, Any]:
        """Summarize a bond for listing and queries."""
        return {
            "bond_id": b.bond_id,
            "agent_a": b.agent_a,
            "agent_b": b.agent_b,
            "frequency": b.frequency.value,
            "state": b.state.value,
            "strength": round(b.strength, 4),
            "resonance_type": b.resonance_type.value,
            "consonance": round(b.consonance, 4),
            "dissonance": round(b.dissonance, 4),
            "shared_experiences": b.shared_experiences,
            "created_at": b.created_at,
            "last_resonated": b.last_resonated,
        }
