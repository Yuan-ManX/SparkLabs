"""
SparkLabs Agent - Volition Genesis Reactor

The AgentVolitionGenesisReactor models how volition - the experience of
will and agency - emerges from the reactor of desires, beliefs, and
opportunities. Rather than pre-scripting agent goals, the reactor allows
intentions to crystallize spontaneously when the right motivational
material aligns with world conditions.

Volition is not a single variable; it is a process with depth. An agent
doesn't simply "want X" - it experiences a gradient of wanting that
builds from raw motivational material (desires), gets filtered through
beliefs about what is possible, and ignites into committed intention
when an opportunity presents itself. This ignition is the moment of
volitional genesis: the birth of purpose.

The reactor also models volitional decay (intentions that lose energy
over time) and transmutation (intentions that transform into new forms
when blocked or fulfilled). This creates a living motivational landscape
where purpose is always in flux.

Architecture:
  NUCLEATE   ->  IGNITE     ->  SUSTAIN    ->  DECAY      ->  TRANSMUTE
  (raw         (alignment    (committed     (energy        (transform
   motivational triggers      intention      leaks from     blocked or
   material     ignition      sustains       unattended     fulfilled
   accumulates  into          through        intentions)    intentions
   in the       committed     cycles of      )              into new
   reactor)     intention)    attention)                    forms)

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

class ReactorPhase(Enum):
    """Phases of the volition genesis cycle."""
    NUCLEATE = "nucleate"       # accumulate motivational material
    IGNITE = "ignite"           # trigger intention formation
    SUSTAIN = "sustain"         # maintain committed intentions
    DECAY = "decay"             # energy leaks from unattended intentions
    TRANSMUTE = "transmute"     # transform blocked or fulfilled intentions


class DesireType(Enum):
    """Fundamental categories of agent desires."""
    SURVIVAL = "survival"           # stay alive, avoid harm
    SOCIAL = "social"               # belong, connect, status
    ACHIEVEMENT = "achievement"     # accomplish, master, overcome
    CURIOSITY = "curiosity"         # explore, discover, understand
    AESTHETIC = "aesthetic"         # beauty, harmony, creation
    TRANSCENDENCE = "transcendence"  # meaning, purpose, legacy


class IntentionState(Enum):
    """Lifecycle state of a formed intention."""
    NASCENT = "nascent"             # just ignited, not yet committed
    COMMITTED = "committed"         # agent is actively pursuing
    CONTESTED = "contested"         # facing resistance, under pressure
    FULFILLED = "fulfilled"         # successfully achieved
    BLOCKED = "blocked"             # cannot proceed
    TRANSMUTED = "transmuted"       # transformed into something new
    DISSOLVED = "dissolved"         # energy depleted, abandoned


class TransmutationMode(Enum):
    """How a blocked intention transforms."""
    SUBLIMATE = "sublimate"         # redirect to higher aspiration
    DISPLACE = "displace"           # redirect to similar goal
    REGRESS = "regress"             # fall back to simpler desire
    FUSE = "fuse"                   # merge with another blocked intention
    DISSOLVE = "dissolve"           # give up entirely


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Desire:
    """A raw motivational drive."""
    desire_id: str
    desire_type: DesireType
    label: str
    intensity: float = 0.5          # current strength (0.0-1.0)
    base_intensity: float = 0.5     # resting level
    volatility: float = 0.3         # how much it fluctuates
    last_pulsed: float = field(default_factory=time.time)


@dataclass
class Belief:
    """An agent's belief about what is possible."""
    belief_id: str
    label: str
    confidence: float = 0.5         # how certain the agent is (0.0-1.0)
    domain: str = "general"
    enables: List[str] = field(default_factory=list)  # desire_ids this belief enables
    inhibits: List[str] = field(default_factory=list)  # desire_ids this belief blocks


@dataclass
class Opportunity:
    """A world condition that can ignite intention."""
    opportunity_id: str
    label: str
    domain: str
    affinity_desires: List[str] = field(default_factory=list)  # desires it resonates with
    strength: float = 0.5           # how compelling (0.0-1.0)
    urgency: float = 0.3            # time pressure (0.0-1.0)
    discovered_at: float = field(default_factory=time.time)
    consumed: bool = False


@dataclass
class Intention:
    """A committed course of action born from volition."""
    intention_id: str
    agent_id: str
    label: str
    source_desire: str
    source_opportunity: str
    state: IntentionState = IntentionState.NASCENT
    energy: float = 1.0             # volitional energy (0.0-1.0)
    commitment: float = 0.3         # how locked-in the agent is (0.0-1.0)
    attention: float = 0.5          # current focus allocation (0.0-1.0)
    resistance: float = 0.0         # accumulated obstacles (0.0-1.0)
    ignition_strength: float = 0.5  # how powerfully it ignited
    created_at: float = field(default_factory=time.time)
    last_sustained: float = field(default_factory=time.time)
    transmuted_to: Optional[str] = None  # intention_id if transmuted


@dataclass
class AgentReactor:
    """Per-agent volition reactor state."""
    agent_id: str
    desires: Dict[str, Desire] = field(default_factory=dict)
    beliefs: Dict[str, Belief] = field(default_factory=dict)
    opportunities: Dict[str, Opportunity] = field(default_factory=dict)
    intentions: Dict[str, Intention] = field(default_factory=dict)
    total_ignited: int = 0
    total_fulfilled: int = 0
    total_transmuted: int = 0
    total_dissolved: int = 0
    volitional_pressure: float = 0.0  # accumulated unfulfilled drive


# =============================================================================
# Engine
# =============================================================================

class AgentVolitionGenesisReactor:
    """
    Thread-safe singleton orchestrating volition genesis across agents.

    Usage:
        reactor = AgentVolitionGenesisReactor.get_instance()
        reactor.register_agent("hero")
        reactor.add_desire("hero", "d_survive", DesireType.SURVIVAL, "Stay Alive", 0.8)
        reactor.add_belief("hero", "b_combat", "I can fight", 0.7, enables=["d_survive"])
        reactor.add_opportunity("hero", "opp_enemy", "Enemy Approaches", "combat",
                                affinity_desires=["d_survive"], strength=0.8, urgency=0.7)
        reactor.cycle()
    """

    _instance: Optional["AgentVolitionGenesisReactor"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._reactors: Dict[str, AgentReactor] = {}
        self._phase: ReactorPhase = ReactorPhase.NUCLEATE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_agents": 0,
            "total_desires": 0,
            "total_beliefs": 0,
            "total_opportunities": 0,
            "total_intentions": 0,
            "total_ignited": 0,
            "total_fulfilled": 0,
            "total_transmuted": 0,
            "total_dissolved": 0,
            "avg_volitional_pressure": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentVolitionGenesisReactor":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Agent Registration
    # -------------------------------------------------------------------------

    def register_agent(self, agent_id: str) -> Dict[str, Any]:
        """Register a new agent with an empty reactor."""
        with self._global_lock:
            if agent_id in self._reactors:
                return {"error": f"Agent already registered: {agent_id}"}
            self._reactors[agent_id] = AgentReactor(agent_id=agent_id)
            self._stats["total_agents"] = len(self._reactors)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {"agent_id": agent_id, "desires": 0, "beliefs": 0, "intentions": 0}

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent's reactor."""
        with self._global_lock:
            if agent_id not in self._reactors:
                return {"error": f"Agent not found: {agent_id}"}
            r = self._reactors.pop(agent_id)
            self._stats["total_agents"] = len(self._reactors)
            self._update_counts()
            return {"removed": agent_id, "intentions": len(r.intentions)}

    # -------------------------------------------------------------------------
    # Desire Management
    # -------------------------------------------------------------------------

    def add_desire(
        self,
        agent_id: str,
        desire_id: str,
        desire_type: DesireType,
        label: str,
        intensity: float = 0.5,
        volatility: float = 0.3,
    ) -> Dict[str, Any]:
        """Add a desire to an agent's reactor."""
        with self._global_lock:
            r = self._reactors.get(agent_id)
            if r is None:
                return {"error": f"Agent not found: {agent_id}"}
            if desire_id in r.desires:
                return {"error": f"Desire already exists: {desire_id}"}
            desire = Desire(
                desire_id=desire_id,
                desire_type=desire_type,
                label=label,
                intensity=max(0.0, min(1.0, intensity)),
                base_intensity=max(0.0, min(1.0, intensity)),
                volatility=max(0.0, min(1.0, volatility)),
            )
            r.desires[desire_id] = desire
            self._update_counts()
            self._record_event("desire_added", {
                "agent_id": agent_id, "desire_id": desire_id, "type": desire_type.value,
            })
            return {
                "desire_id": desire_id,
                "type": desire_type.value,
                "label": label,
                "intensity": desire.intensity,
            }

    # -------------------------------------------------------------------------
    # Belief Management
    # -------------------------------------------------------------------------

    def add_belief(
        self,
        agent_id: str,
        belief_id: str,
        label: str,
        confidence: float = 0.5,
        domain: str = "general",
        enables: Optional[List[str]] = None,
        inhibits: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Add a belief to an agent's reactor."""
        with self._global_lock:
            r = self._reactors.get(agent_id)
            if r is None:
                return {"error": f"Agent not found: {agent_id}"}
            if belief_id in r.beliefs:
                return {"error": f"Belief already exists: {belief_id}"}
            belief = Belief(
                belief_id=belief_id,
                label=label,
                confidence=max(0.0, min(1.0, confidence)),
                domain=domain,
                enables=enables or [],
                inhibits=inhibits or [],
            )
            r.beliefs[belief_id] = belief
            self._update_counts()
            self._record_event("belief_added", {
                "agent_id": agent_id, "belief_id": belief_id, "domain": domain,
            })
            return {
                "belief_id": belief_id,
                "label": label,
                "confidence": belief.confidence,
                "enables": belief.enables,
                "inhibits": belief.inhibits,
            }

    # -------------------------------------------------------------------------
    # Opportunity Management
    # -------------------------------------------------------------------------

    def add_opportunity(
        self,
        agent_id: str,
        opportunity_id: str,
        label: str,
        domain: str,
        affinity_desires: Optional[List[str]] = None,
        strength: float = 0.5,
        urgency: float = 0.3,
    ) -> Dict[str, Any]:
        """Add an opportunity to an agent's reactor."""
        with self._global_lock:
            r = self._reactors.get(agent_id)
            if r is None:
                return {"error": f"Agent not found: {agent_id}"}
            if opportunity_id in r.opportunities:
                return {"error": f"Opportunity already exists: {opportunity_id}"}
            opp = Opportunity(
                opportunity_id=opportunity_id,
                label=label,
                domain=domain,
                affinity_desires=affinity_desires or [],
                strength=max(0.0, min(1.0, strength)),
                urgency=max(0.0, min(1.0, urgency)),
            )
            r.opportunities[opportunity_id] = opp
            self._update_counts()
            self._record_event("opportunity_added", {
                "agent_id": agent_id, "opportunity_id": opportunity_id, "domain": domain,
            })
            return {
                "opportunity_id": opportunity_id,
                "label": label,
                "domain": domain,
                "strength": opp.strength,
                "urgency": opp.urgency,
            }

    def consume_opportunity(self, agent_id: str, opportunity_id: str) -> Dict[str, Any]:
        """Mark an opportunity as consumed (used to ignite an intention)."""
        with self._global_lock:
            r = self._reactors.get(agent_id)
            if r is None:
                return {"error": f"Agent not found: {agent_id}"}
            opp = r.opportunities.get(opportunity_id)
            if opp is None:
                return {"error": f"Opportunity not found: {opportunity_id}"}
            opp.consumed = True
            return {"consumed": opportunity_id}

    # -------------------------------------------------------------------------
    # Intention Management
    # -------------------------------------------------------------------------

    def fulfill_intention(self, agent_id: str, intention_id: str) -> Dict[str, Any]:
        """Mark an intention as fulfilled."""
        with self._global_lock:
            r = self._reactors.get(agent_id)
            if r is None:
                return {"error": f"Agent not found: {agent_id}"}
            intent = r.intentions.get(intention_id)
            if intent is None:
                return {"error": f"Intention not found: {intention_id}"}
            intent.state = IntentionState.FULFILLED
            r.total_fulfilled += 1
            self._update_counts()
            self._record_event("intention_fulfilled", {
                "agent_id": agent_id, "intention_id": intention_id,
            })
            return {"fulfilled": intention_id}

    def block_intention(self, agent_id: str, intention_id: str, resistance: float = 0.5) -> Dict[str, Any]:
        """Add resistance to an intention, potentially blocking it."""
        with self._global_lock:
            r = self._reactors.get(agent_id)
            if r is None:
                return {"error": f"Agent not found: {agent_id}"}
            intent = r.intentions.get(intention_id)
            if intent is None:
                return {"error": f"Intention not found: {intention_id}"}
            intent.resistance = min(1.0, intent.resistance + resistance)
            if intent.resistance >= 0.8 and intent.state == IntentionState.COMMITTED:
                intent.state = IntentionState.CONTESTED
            return {
                "intention_id": intention_id,
                "resistance": intent.resistance,
                "state": intent.state.value,
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single volition genesis cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            # NUCLEATE: desires pulse and accumulate pressure
            self._phase = ReactorPhase.NUCLEATE
            phase_outputs["nucleate"] = self._phase_nucleate()
            # IGNITE: check for desire-belief-opportunity alignment
            self._phase = ReactorPhase.IGNITE
            phase_outputs["ignite"] = self._phase_ignite()
            # SUSTAIN: committed intentions gain energy from attention
            self._phase = ReactorPhase.SUSTAIN
            phase_outputs["sustain"] = self._phase_sustain()
            # DECAY: unattended intentions lose energy
            self._phase = ReactorPhase.DECAY
            phase_outputs["decay"] = self._phase_decay()
            # TRANSMUTE: blocked or fulfilled intentions transform
            self._phase = ReactorPhase.TRANSMUTE
            phase_outputs["transmute"] = self._phase_transmute()
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

    def _phase_nucleate(self) -> Dict[str, Any]:
        """NUCLEATE: desires pulse with volatility, accumulating volitional pressure."""
        pulsed = 0
        for r in self._reactors.values():
            pressure_delta = 0.0
            for desire in r.desires.values():
                # Pulse: intensity fluctuates around base
                fluctuation = (random.random() - 0.5) * desire.volatility * 0.3
                desire.intensity = max(0.0, min(1.0, desire.intensity + fluctuation))
                # Drift back toward base
                desire.intensity += (desire.base_intensity - desire.intensity) * 0.1
                desire.last_pulsed = time.time()
                pulsed += 1
                # High-intensity unfulfilled desires add pressure
                active_intents = [
                    i for i in r.intentions.values()
                    if i.source_desire == desire.desire_id
                    and i.state in (IntentionState.NASCENT, IntentionState.COMMITTED, IntentionState.CONTESTED)
                ]
                if not active_intents and desire.intensity > 0.5:
                    pressure_delta += desire.intensity * 0.02
            r.volitional_pressure = min(1.0, r.volitional_pressure + pressure_delta)
            # Pressure naturally decays slightly
            r.volitional_pressure = max(0.0, r.volitional_pressure - 0.01)
        return {"pulsed": pulsed}

    def _phase_ignite(self) -> Dict[str, Any]:
        """IGNITE: when desire, belief, and opportunity align, form an intention."""
        ignited = 0
        for r in self._reactors.values():
            for opp in r.opportunities.values():
                if opp.consumed:
                    continue
                for desire_id in opp.affinity_desires:
                    desire = r.desires.get(desire_id)
                    if desire is None:
                        continue
                    # Check if already has an active intention for this desire
                    has_active = any(
                        i.source_desire == desire_id
                        and i.state in (IntentionState.NASCENT, IntentionState.COMMITTED, IntentionState.CONTESTED)
                        for i in r.intentions.values()
                    )
                    if has_active:
                        continue
                    # Find enabling beliefs
                    enabling_confidence = 0.5
                    inhibiting_confidence = 0.0
                    for belief in r.beliefs.values():
                        if desire_id in belief.enables:
                            enabling_confidence = max(enabling_confidence, belief.confidence)
                        if desire_id in belief.inhibits:
                            inhibiting_confidence = max(inhibiting_confidence, belief.confidence)
                    # Calculate ignition strength
                    net_belief = enabling_confidence * (1.0 - inhibiting_confidence)
                    ignition = (
                        desire.intensity * 0.4
                        + opp.strength * 0.3
                        + net_belief * 0.2
                        + opp.urgency * 0.1
                    )
                    if ignition >= 0.5:
                        # Ignite a new intention
                        intention_id = f"intent_{desire_id}_{opp.opportunity_id}_{int(time.time() * 1000) % 100000}"
                        intention = Intention(
                            intention_id=intention_id,
                            agent_id=r.agent_id,
                            label=f"Pursue: {desire.label} via {opp.label}",
                            source_desire=desire_id,
                            source_opportunity=opp.opportunity_id,
                            state=IntentionState.NASCENT,
                            energy=ignition,
                            commitment=0.2 + ignition * 0.3,
                            attention=0.3 + ignition * 0.2,
                            ignition_strength=ignition,
                        )
                        r.intentions[intention_id] = intention
                        opp.consumed = True
                        r.total_ignited += 1
                        ignited += 1
                        self._record_event("ignited", {
                            "agent_id": r.agent_id,
                            "intention_id": intention_id,
                            "desire": desire_id,
                            "ignition_strength": round(ignition, 4),
                        })
        self._update_counts()
        return {"ignited": ignited, "total_intentions": self._stats["total_intentions"]}

    def _phase_sustain(self) -> Dict[str, Any]:
        """SUSTAIN: committed intentions gain energy from attention."""
        sustained = 0
        for r in self._reactors.values():
            # Sort intentions by energy to allocate attention
            active = [
                i for i in r.intentions.values()
                if i.state in (IntentionState.NASCENT, IntentionState.COMMITTED, IntentionState.CONTESTED)
            ]
            if not active:
                continue
            # Nascent intentions transition to committed
            for intent in active:
                if intent.state == IntentionState.NASCENT:
                    intent.state = IntentionState.COMMITTED
                    sustained += 1
                # Allocate attention proportionally to energy
                intent.attention = min(1.0, intent.attention + 0.05)
                # Energy increases with attention, decreases with resistance
                energy_delta = intent.attention * 0.05 - intent.resistance * 0.03
                intent.energy = max(0.0, min(1.0, intent.energy + energy_delta))
                intent.commitment = min(1.0, intent.commitment + 0.02)
                intent.last_sustained = time.time()
                # Reduce resistance slightly through sustained effort
                intent.resistance = max(0.0, intent.resistance - 0.01)
        return {"sustained": sustained}

    def _phase_decay(self) -> Dict[str, Any]:
        """DECAY: unattended intentions lose energy and may dissolve."""
        decayed = 0
        dissolved = 0
        for r in self._reactors.values():
            for intent in r.intentions.values():
                if intent.state not in (IntentionState.NASCENT, IntentionState.COMMITTED, IntentionState.CONTESTED):
                    continue
                # Energy decays if attention is low
                if intent.attention < 0.3:
                    intent.energy = max(0.0, intent.energy - 0.05)
                    decayed += 1
                # Attention naturally drifts down
                intent.attention = max(0.0, intent.attention - 0.02)
                # Dissolve if energy is too low
                if intent.energy < 0.1:
                    intent.state = IntentionState.DISSOLVED
                    r.total_dissolved += 1
                    dissolved += 1
                    self._record_event("dissolved", {
                        "agent_id": r.agent_id,
                        "intention_id": intent.intention_id,
                    })
        self._update_counts()
        return {"decayed": decayed, "dissolved": dissolved}

    def _phase_transmute(self) -> Dict[str, Any]:
        """TRANSMUTE: blocked or fulfilled intentions transform into new forms."""
        transmuted = 0
        for r in self._reactors.values():
            for intent in r.intentions.values():
                if intent.state == IntentionState.CONTESTED and intent.resistance >= 0.9:
                    # Blocked intention: transmute
                    mode = self._choose_transmutation(r, intent)
                    intent.state = IntentionState.TRANSMUTED
                    intent.transmuted_to = mode.value
                    r.total_transmuted += 1
                    transmuted += 1
                    self._record_event("transmuted", {
                        "agent_id": r.agent_id,
                        "intention_id": intent.intention_id,
                        "mode": mode.value,
                    })
        self._update_counts()
        return {"transmuted": transmuted}

    def _choose_transmutation(self, reactor: AgentReactor, intent: Intention) -> TransmutationMode:
        """Choose how a blocked intention transforms."""
        desire = reactor.desires.get(intent.source_desire)
        if desire is None:
            return TransmutationMode.DISSOLVE
        # High-intensity desires tend to sublimate or displace
        if desire.intensity > 0.7:
            return TransmutationMode.SUBLIMATE if random.random() < 0.5 else TransmutationMode.DISPLACE
        # Low-intensity desires tend to regress or dissolve
        if desire.intensity < 0.3:
            return TransmutationMode.REGRESS if random.random() < 0.4 else TransmutationMode.DISSOLVE
        # Medium intensity: fuse or dissolve
        return TransmutationMode.FUSE if random.random() < 0.3 else TransmutationMode.DISSOLVE

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get global reactor status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_agents": len(self._reactors),
                "stats": dict(self._stats),
            }

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get full reactor details for an agent."""
        with self._global_lock:
            r = self._reactors.get(agent_id)
            if r is None:
                return None
            return {
                "agent_id": agent_id,
                "total_desires": len(r.desires),
                "total_beliefs": len(r.beliefs),
                "total_opportunities": len(r.opportunities),
                "total_intentions": len(r.intentions),
                "total_ignited": r.total_ignited,
                "total_fulfilled": r.total_fulfilled,
                "total_transmuted": r.total_transmuted,
                "total_dissolved": r.total_dissolved,
                "volitional_pressure": round(r.volitional_pressure, 4),
                "desires": [
                    {
                        "desire_id": d.desire_id,
                        "type": d.desire_type.value,
                        "label": d.label,
                        "intensity": round(d.intensity, 4),
                        "base_intensity": d.base_intensity,
                        "volatility": d.volatility,
                    }
                    for d in r.desires.values()
                ],
                "beliefs": [
                    {
                        "belief_id": b.belief_id,
                        "label": b.label,
                        "confidence": b.confidence,
                        "domain": b.domain,
                        "enables": b.enables,
                        "inhibits": b.inhibits,
                    }
                    for b in r.beliefs.values()
                ],
                "opportunities": [
                    {
                        "opportunity_id": o.opportunity_id,
                        "label": o.label,
                        "domain": o.domain,
                        "strength": o.strength,
                        "urgency": o.urgency,
                        "consumed": o.consumed,
                        "affinity_desires": o.affinity_desires,
                    }
                    for o in r.opportunities.values()
                ],
                "intentions": [
                    {
                        "intention_id": i.intention_id,
                        "label": i.label,
                        "source_desire": i.source_desire,
                        "source_opportunity": i.source_opportunity,
                        "state": i.state.value,
                        "energy": round(i.energy, 4),
                        "commitment": round(i.commitment, 4),
                        "attention": round(i.attention, 4),
                        "resistance": round(i.resistance, 4),
                        "ignition_strength": round(i.ignition_strength, 4),
                        "transmuted_to": i.transmuted_to,
                    }
                    for i in r.intentions.values()
                ],
            }

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        with self._global_lock:
            return [
                {
                    "agent_id": r.agent_id,
                    "desires": len(r.desires),
                    "beliefs": len(r.beliefs),
                    "opportunities": len(r.opportunities),
                    "intentions": len(r.intentions),
                    "volitional_pressure": round(r.volitional_pressure, 4),
                }
                for r in self._reactors.values()
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent reactor events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire reactor."""
        with self._global_lock:
            n = len(self._reactors)
            self._reactors.clear()
            self._phase = ReactorPhase.NUCLEATE
            self._cycle_count = 0
            self._events_log.clear()
            self._stats = {
                "total_agents": 0,
                "total_desires": 0,
                "total_beliefs": 0,
                "total_opportunities": 0,
                "total_intentions": 0,
                "total_ignited": 0,
                "total_fulfilled": 0,
                "total_transmuted": 0,
                "total_dissolved": 0,
                "avg_volitional_pressure": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "cleared_agents": n}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _update_counts(self) -> None:
        """Update aggregate counts."""
        self._stats["total_desires"] = sum(len(r.desires) for r in self._reactors.values())
        self._stats["total_beliefs"] = sum(len(r.beliefs) for r in self._reactors.values())
        self._stats["total_opportunities"] = sum(len(r.opportunities) for r in self._reactors.values())
        self._stats["total_intentions"] = sum(len(r.intentions) for r in self._reactors.values())
        self._stats["total_ignited"] = sum(r.total_ignited for r in self._reactors.values())
        self._stats["total_fulfilled"] = sum(r.total_fulfilled for r in self._reactors.values())
        self._stats["total_transmuted"] = sum(r.total_transmuted for r in self._reactors.values())
        self._stats["total_dissolved"] = sum(r.total_dissolved for r in self._reactors.values())

    def _update_stats(self) -> None:
        """Update aggregate statistics."""
        self._update_counts()
        if self._reactors:
            self._stats["avg_volitional_pressure"] = (
                sum(r.volitional_pressure for r in self._reactors.values())
                / len(self._reactors)
            )

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a reactor event."""
        self._events_log.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
