"""
SparkLabs Agent - Empathy Resonance Network

The AgentEmpathyResonanceNetwork models how empathy emerges between agents
through shared emotional experiences. Empathy is not a static trait; it is
a living resonance that forms when agents attune to each other's emotional
states, mirror what they observe, and gradually absorb the capacity to
feel what another feels.

The network treats empathy as a wave phenomenon. When two agents experience
similar emotions in proximity, their emotional states begin to oscillate
in sympathy. Over time, these sympathetic oscillations form stable resonance
bonds - the structural foundation of empathy. Strong bonds allow emotional
states to propagate from one agent to another, creating the experience of
"feeling with" another being.

The network also models empathy decay (bonds that weaken without reinforcement)
and empathy projection (the transformation of felt empathy into compassionate
action). This creates a dynamic social fabric where agents genuinely care
about each other - not because they are scripted to, but because their
resonance histories make caring the natural response.

Architecture:
  ATTUNE     ->  MIRROR      ->  RESONATE    ->  ABSORB     ->  PROJECT
  (agents       (agents        (mirrored       (resonance    (absorbed
   calibrate    reproduce      states          is            empathy
   emotional    observed       amplify         integrated    drives
   baselines    emotional      into stable     into          compassionate
   and detect   states of      resonance       long-term     action and
   proximity    others)        bonds)          empathy)      behavior)

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

class EmpathyPhase(Enum):
    """Phases of the empathy resonance cycle."""
    ATTUNE = "attune"           # calibrate baselines and detect proximity
    MIRROR = "mirror"           # reproduce observed emotional states
    RESONATE = "resonate"       # mirrored states amplify into bonds
    ABSORB = "absorb"           # resonance integrates into long-term empathy
    PROJECT = "project"         # empathy drives compassionate action


class EmpathyType(Enum):
    """Modalities of empathy an agent can develop."""
    COGNITIVE = "cognitive"         # understanding another's perspective
    EMOTIONAL = "emotional"         # feeling what another feels
    COMPASSIONATE = "compassionate"  # urge to help based on felt empathy
    SOMATIC = "somatic"             # bodily mirroring of another's state
    SPATIAL = "spatial"             # awareness of another's spatial needs


class ResonanceMode(Enum):
    """Quality of the resonance between two agents."""
    HARMONIC = "harmonic"           # aligned, mutually reinforcing
    DISSONANT = "dissonant"         # conflicting, produces tension
    SYMPATHETIC = "sympathetic"     # responsive but not self-reinforcing
    PARASITIC = "parasitic"         # one-directional, draining


class BondState(Enum):
    """Lifecycle state of an empathy bond."""
    NASCENT = "nascent"             # just forming, fragile
    FORMING = "forming"             # growing stronger with each interaction
    STABLE = "stable"               # solid, self-sustaining
    RESONATING = "resonating"       # actively transmitting emotion
    DECAYING = "decaying"           # weakening from neglect
    SEVERED = "severed"             # broken beyond repair


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class EmotionalEpisode:
    """A recorded emotional event experienced by an agent."""
    episode_id: str
    agent_id: str
    emotion: str
    valence: float                    # -1.0 (negative) to 1.0 (positive)
    arousal: float                    # 0.0 (calm) to 1.0 (intense)
    timestamp: float = field(default_factory=time.time)
    context: str = ""
    shared_with: Set[str] = field(default_factory=set)


@dataclass
class EmpathyBond:
    """A resonance bond between two agents."""
    bond_id: str
    agent_a: str
    agent_b: str
    empathy_type: EmpathyType
    mode: ResonanceMode = ResonanceMode.SYMPATHETIC
    state: BondState = BondState.NASCENT
    strength: float = 0.1             # 0.0-1.0
    resonance_frequency: float = 0.5  # how quickly states propagate
    last_reinforced: float = field(default_factory=time.time)
    total_shared_episodes: int = 0
    emotional_sync: float = 0.0       # how aligned their states are


@dataclass
class EmpathyField:
    """The empathy state of a single agent."""
    agent_id: str
    baseline_valence: float = 0.0
    baseline_arousal: float = 0.3
    current_valence: float = 0.0
    current_arousal: float = 0.3
    empathy_capacity: float = 0.5     # how much empathy this agent can hold
    active_bonds: Set[str] = field(default_factory=set)
    absorbed_empathy: Dict[str, float] = field(default_factory=dict)
    projected_actions: int = 0
    last_attuned: float = field(default_factory=time.time)


@dataclass
class CompassionateAction:
    """An action driven by empathy."""
    action_id: str
    source_agent: str
    target_agent: str
    action_type: str
    intensity: float
    timestamp: float = field(default_factory=time.time)
    description: str = ""


# =============================================================================
# Engine
# =============================================================================

class AgentEmpathyResonanceNetwork:
    """
    Thread-safe singleton orchestrating empathy resonance across agents.

    Usage:
        network = AgentEmpathyResonanceNetwork.get_instance()
        network.register_agent("hero")
        network.register_agent("ally")
        network.record_episode("ep_1", "hero", "joy", 0.8, 0.6)
        network.record_episode("ep_2", "ally", "joy", 0.7, 0.5, shared_with={"hero"})
        network.form_bond("hero", "ally", EmpathyType.EMOTIONAL)
        network.cycle()
    """

    _instance: Optional["AgentEmpathyResonanceNetwork"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._fields: Dict[str, EmpathyField] = {}
        self._bonds: Dict[str, EmpathyBond] = {}
        self._episodes: Deque[EmotionalEpisode] = deque(maxlen=500)
        self._actions: Deque[CompassionateAction] = deque(maxlen=200)
        self._phase: EmpathyPhase = EmpathyPhase.ATTUNE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_agents": 0,
            "total_bonds": 0,
            "total_episodes": 0,
            "total_actions": 0,
            "active_bonds": 0,
            "resonating_bonds": 0,
            "avg_bond_strength": 0.0,
            "avg_empathy_capacity": 0.0,
            "total_absorbed": 0.0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentEmpathyResonanceNetwork":
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
        baseline_valence: float = 0.0,
        baseline_arousal: float = 0.3,
        empathy_capacity: float = 0.5,
    ) -> Dict[str, Any]:
        """Register a new agent in the empathy network."""
        with self._global_lock:
            if agent_id in self._fields:
                return {"error": f"Agent already registered: {agent_id}"}
            field_obj = EmpathyField(
                agent_id=agent_id,
                baseline_valence=max(-1.0, min(1.0, baseline_valence)),
                baseline_arousal=max(0.0, min(1.0, baseline_arousal)),
                current_valence=baseline_valence,
                current_arousal=baseline_arousal,
                empathy_capacity=max(0.0, min(1.0, empathy_capacity)),
            )
            self._fields[agent_id] = field_obj
            self._stats["total_agents"] = len(self._fields)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "baseline_valence": field_obj.baseline_valence,
                "baseline_arousal": field_obj.baseline_arousal,
                "empathy_capacity": field_obj.empathy_capacity,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent and sever all their bonds."""
        with self._global_lock:
            if agent_id not in self._fields:
                return {"error": f"Agent not found: {agent_id}"}
            # Sever all bonds involving this agent
            severed = []
            to_remove = [
                bid for bid, b in self._bonds.items()
                if b.agent_a == agent_id or b.agent_b == agent_id
            ]
            for bid in to_remove:
                bond = self._bonds[bid]
                other = bond.agent_b if bond.agent_a == agent_id else bond.agent_a
                if other in self._fields:
                    self._fields[other].active_bonds.discard(bid)
                severed.append(bid)
                del self._bonds[bid]
            del self._fields[agent_id]
            self._stats["total_agents"] = len(self._fields)
            self._stats["total_bonds"] = len(self._bonds)
            self._record_event("agent_removed", {
                "agent_id": agent_id, "severed_bonds": len(severed),
            })
            return {"removed": agent_id, "severed_bonds": len(severed)}

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        with self._global_lock:
            return [self._summarize_field(f) for f in self._fields.values()]

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get full empathy details for an agent."""
        with self._global_lock:
            f = self._fields.get(agent_id)
            if f is None:
                return None
            bonds = [
                self._summarize_bond(self._bonds[bid])
                for bid in f.active_bonds
                if bid in self._bonds
            ]
            return {
                "agent_id": agent_id,
                "baseline_valence": f.baseline_valence,
                "baseline_arousal": f.baseline_arousal,
                "current_valence": round(f.current_valence, 4),
                "current_arousal": round(f.current_arousal, 4),
                "empathy_capacity": f.empathy_capacity,
                "active_bond_count": len(f.active_bonds),
                "total_absorbed_empathy": sum(f.absorbed_empathy.values()),
                "projected_actions": f.projected_actions,
                "bonds": bonds,
                "absorbed_empathy": dict(f.absorbed_empathy),
            }

    # -------------------------------------------------------------------------
    # Episode Management
    # -------------------------------------------------------------------------

    def record_episode(
        self,
        episode_id: str,
        agent_id: str,
        emotion: str,
        valence: float = 0.0,
        arousal: float = 0.3,
        context: str = "",
        shared_with: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Record an emotional episode for an agent."""
        with self._global_lock:
            if agent_id not in self._fields:
                return {"error": f"Agent not found: {agent_id}"}
            shared_set = set(shared_with) if shared_with else set()
            episode = EmotionalEpisode(
                episode_id=episode_id,
                agent_id=agent_id,
                emotion=emotion,
                valence=max(-1.0, min(1.0, valence)),
                arousal=max(0.0, min(1.0, arousal)),
                context=context,
                shared_with=shared_set,
            )
            self._episodes.append(episode)
            # Update agent's current emotional state
            f = self._fields[agent_id]
            f.current_valence = 0.7 * f.current_valence + 0.3 * episode.valence
            f.current_arousal = 0.7 * f.current_arousal + 0.3 * episode.arousal
            self._stats["total_episodes"] = len(self._episodes)
            self._record_event("episode_recorded", {
                "episode_id": episode_id,
                "agent_id": agent_id,
                "emotion": emotion,
                "shared_with": list(shared_set),
            })
            return {
                "episode_id": episode_id,
                "agent_id": agent_id,
                "emotion": emotion,
                "valence": episode.valence,
                "arousal": episode.arousal,
                "shared_with": list(shared_set),
            }

    # -------------------------------------------------------------------------
    # Bond Management
    # -------------------------------------------------------------------------

    def form_bond(
        self,
        agent_a: str,
        agent_b: str,
        empathy_type: EmpathyType,
        mode: ResonanceMode = ResonanceMode.SYMPATHETIC,
        initial_strength: float = 0.1,
    ) -> Dict[str, Any]:
        """Form an empathy bond between two agents."""
        with self._global_lock:
            if agent_a not in self._fields:
                return {"error": f"Agent not found: {agent_a}"}
            if agent_b not in self._fields:
                return {"error": f"Agent not found: {agent_b}"}
            if agent_a == agent_b:
                return {"error": "Cannot bond an agent with itself"}
            # Check for existing bond
            for b in self._bonds.values():
                if (b.agent_a == agent_a and b.agent_b == agent_b) or \
                   (b.agent_a == agent_b and b.agent_b == agent_a):
                    if b.empathy_type == empathy_type:
                        return {"error": f"Bond already exists between {agent_a} and {agent_b}"}
            bond_id = f"bond_{agent_a}_{agent_b}_{empathy_type.value}_{int(time.time() * 1000) % 100000}"
            bond = EmpathyBond(
                bond_id=bond_id,
                agent_a=agent_a,
                agent_b=agent_b,
                empathy_type=empathy_type,
                mode=mode,
                state=BondState.NASCENT,
                strength=max(0.0, min(1.0, initial_strength)),
                resonance_frequency=0.3 + initial_strength * 0.4,
            )
            self._bonds[bond_id] = bond
            self._fields[agent_a].active_bonds.add(bond_id)
            self._fields[agent_b].active_bonds.add(bond_id)
            self._stats["total_bonds"] = len(self._bonds)
            self._record_event("bond_formed", {
                "bond_id": bond_id,
                "agent_a": agent_a,
                "agent_b": agent_b,
                "empathy_type": empathy_type.value,
            })
            return {
                "bond_id": bond_id,
                "agent_a": agent_a,
                "agent_b": agent_b,
                "empathy_type": empathy_type.value,
                "mode": mode.value,
                "strength": bond.strength,
            }

    def reinforce_bond(self, bond_id: str, amount: float = 0.1) -> Dict[str, Any]:
        """Reinforce an existing empathy bond."""
        with self._global_lock:
            bond = self._bonds.get(bond_id)
            if bond is None:
                return {"error": f"Bond not found: {bond_id}"}
            bond.strength = min(1.0, bond.strength + max(0.0, min(1.0, amount)))
            bond.last_reinforced = time.time()
            bond.total_shared_episodes += 1
            # State transitions
            if bond.state == BondState.NASCENT and bond.strength > 0.2:
                bond.state = BondState.FORMING
            elif bond.state == BondState.FORMING and bond.strength > 0.5:
                bond.state = BondState.STABLE
            elif bond.state == BondState.STABLE and bond.strength > 0.7:
                bond.state = BondState.RESONATING
            elif bond.state == BondState.DECAYING and bond.strength > 0.4:
                bond.state = BondState.STABLE
            return {
                "bond_id": bond_id,
                "strength": round(bond.strength, 4),
                "state": bond.state.value,
                "total_shared_episodes": bond.total_shared_episodes,
            }

    def sever_bond(self, bond_id: str) -> Dict[str, Any]:
        """Sever an empathy bond."""
        with self._global_lock:
            bond = self._bonds.get(bond_id)
            if bond is None:
                return {"error": f"Bond not found: {bond_id}"}
            bond.state = BondState.SEVERED
            if bond.agent_a in self._fields:
                self._fields[bond.agent_a].active_bonds.discard(bond_id)
            if bond.agent_b in self._fields:
                self._fields[bond.agent_b].active_bonds.discard(bond_id)
            del self._bonds[bond_id]
            self._stats["total_bonds"] = len(self._bonds)
            self._record_event("bond_severed", {"bond_id": bond_id})
            return {"severed": bond_id}

    def list_bonds(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all empathy bonds."""
        with self._global_lock:
            return [self._summarize_bond(b) for b in list(self._bonds.values())[:limit]]

    def get_bond(self, bond_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific bond."""
        with self._global_lock:
            b = self._bonds.get(bond_id)
            return self._summarize_bond(b) if b else None

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single empathy resonance cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            # ATTUNE: calibrate baselines and detect proximity
            self._phase = EmpathyPhase.ATTUNE
            phase_outputs["attune"] = self._phase_attune()
            # MIRROR: agents reproduce observed emotional states
            self._phase = EmpathyPhase.MIRROR
            phase_outputs["mirror"] = self._phase_mirror()
            # RESONATE: mirrored states amplify into bonds
            self._phase = EmpathyPhase.RESONATE
            phase_outputs["resonate"] = self._phase_resonate()
            # ABSORB: resonance integrates into long-term empathy
            self._phase = EmpathyPhase.ABSORB
            phase_outputs["absorb"] = self._phase_absorb()
            # PROJECT: empathy drives compassionate action
            self._phase = EmpathyPhase.PROJECT
            phase_outputs["project"] = self._phase_project()
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

    def _phase_attune(self) -> Dict[str, Any]:
        """ATTUNE: agents calibrate baselines and detect emotional proximity."""
        attuned = 0
        for f in self._fields.values():
            # Drift current state back toward baseline
            f.current_valence = f.current_valence * 0.95 + f.baseline_valence * 0.05
            f.current_arousal = f.current_arousal * 0.95 + f.baseline_arousal * 0.05
            f.last_attuned = time.time()
            attuned += 1
        return {"attuned": attuned}

    def _phase_mirror(self) -> Dict[str, Any]:
        """MIRROR: agents reproduce observed emotional states of bonded partners."""
        mirrored = 0
        for bond in self._bonds.values():
            if bond.state in (BondState.SEVERED,):
                continue
            fa = self._fields.get(bond.agent_a)
            fb = self._fields.get(bond.agent_b)
            if fa is None or fb is None:
                continue
            # Calculate emotional distance
            valence_diff = abs(fa.current_valence - fb.current_valence)
            arousal_diff = abs(fa.current_arousal - fb.current_arousal)
            emotional_distance = (valence_diff + arousal_diff) / 2.0
            # Mirror: move each agent's state slightly toward the other
            mirror_strength = bond.strength * bond.resonance_frequency * 0.3
            if bond.mode == ResonanceMode.HARMONIC:
                fa.current_valence += (fb.current_valence - fa.current_valence) * mirror_strength
                fb.current_valence += (fa.current_valence - fb.current_valence) * mirror_strength
                fa.current_arousal += (fb.current_arousal - fa.current_arousal) * mirror_strength
                fb.current_arousal += (fa.current_arousal - fb.current_arousal) * mirror_strength
                mirrored += 2
            elif bond.mode == ResonanceMode.SYMPATHETIC:
                # One-directional: weaker agent mirrors stronger
                if fa.empathy_capacity < fb.empathy_capacity:
                    fa.current_valence += (fb.current_valence - fa.current_valence) * mirror_strength
                    fa.current_arousal += (fb.current_arousal - fa.current_arousal) * mirror_strength
                    mirrored += 1
                else:
                    fb.current_valence += (fa.current_valence - fb.current_valence) * mirror_strength
                    fb.current_arousal += (fa.current_arousal - fb.current_arousal) * mirror_strength
                    mirrored += 1
            elif bond.mode == ResonanceMode.DISSONANT:
                # Move apart
                fa.current_valence -= (fb.current_valence - fa.current_valence) * mirror_strength * 0.5
                fb.current_valence -= (fa.current_valence - fb.current_valence) * mirror_strength * 0.5
                mirrored += 2
            # Update emotional sync
            bond.emotional_sync = max(0.0, 1.0 - emotional_distance)
            # Clamp values
            fa.current_valence = max(-1.0, min(1.0, fa.current_valence))
            fa.current_arousal = max(0.0, min(1.0, fa.current_arousal))
            fb.current_valence = max(-1.0, min(1.0, fb.current_valence))
            fb.current_arousal = max(0.0, min(1.0, fb.current_arousal))
        return {"mirrored": mirrored}

    def _phase_resonate(self) -> Dict[str, Any]:
        """RESONATE: mirrored states amplify into stable resonance bonds."""
        resonated = 0
        decayed = 0
        now = time.time()
        for bond in self._bonds.values():
            if bond.state == BondState.SEVERED:
                continue
            # Bonds with high emotional sync grow stronger
            if bond.emotional_sync > 0.5:
                growth = bond.emotional_sync * 0.02 * bond.resonance_frequency
                bond.strength = min(1.0, bond.strength + growth)
                resonated += 1
                # State transitions
                if bond.state == BondState.NASCENT and bond.strength > 0.2:
                    bond.state = BondState.FORMING
                elif bond.state == BondState.FORMING and bond.strength > 0.5:
                    bond.state = BondState.STABLE
                elif bond.state == BondState.STABLE and bond.strength > 0.7:
                    bond.state = BondState.RESONATING
            else:
                # Low sync: bond decays
                time_since_reinforced = now - bond.last_reinforced
                if time_since_reinforced > 5.0:
                    decay_amount = 0.01 * (time_since_reinforced / 10.0)
                    bond.strength = max(0.0, bond.strength - decay_amount)
                    decayed += 1
                    if bond.state == BondState.STABLE and bond.strength < 0.4:
                        bond.state = BondState.DECAYING
                    elif bond.state == BondState.DECAYING and bond.strength < 0.1:
                        bond.state = BondState.SEVERED
        return {"resonated": resonated, "decayed": decayed}

    def _phase_absorb(self) -> Dict[str, Any]:
        """ABSORB: resonance integrates into long-term empathy capacity."""
        absorbed = 0.0
        for bond in self._bonds.values():
            if bond.state not in (BondState.STABLE, BondState.RESONATING):
                continue
            fa = self._fields.get(bond.agent_a)
            fb = self._fields.get(bond.agent_b)
            if fa is None or fb is None:
                continue
            # Each agent absorbs empathy from the bond
            absorption = bond.strength * 0.01
            fa.absorbed_empathy[bond.agent_b] = fa.absorbed_empathy.get(bond.agent_b, 0.0) + absorption
            fb.absorbed_empathy[bond.agent_a] = fb.absorbed_empathy.get(bond.agent_a, 0.0) + absorption
            # Grow empathy capacity slightly
            fa.empathy_capacity = min(1.0, fa.empathy_capacity + absorption * 0.1)
            fb.empathy_capacity = min(1.0, fb.empathy_capacity + absorption * 0.1)
            absorbed += absorption * 2
        self._stats["total_absorbed"] += absorbed
        return {"absorbed": round(absorbed, 4)}

    def _phase_project(self) -> Dict[str, Any]:
        """PROJECT: absorbed empathy drives compassionate action."""
        actions = 0
        for f in self._fields.values():
            for target_id, empathy_level in f.absorbed_empathy.items():
                if empathy_level < 0.3:
                    continue
                # Probability of compassionate action
                action_prob = empathy_level * f.empathy_capacity * 0.3
                if random.random() < action_prob:
                    target = self._fields.get(target_id)
                    if target is None:
                        continue
                    # Determine action type based on target's state
                    if target.current_valence < -0.3:
                        action_type = "comfort"
                        intensity = min(1.0, abs(target.current_valence) * empathy_level)
                        desc = f"{f.agent_id} comforts {target_id}"
                    elif target.current_arousal > 0.7:
                        action_type = "support"
                        intensity = min(1.0, target.current_arousal * empathy_level)
                        desc = f"{f.agent_id} supports {target_id}"
                    else:
                        action_type = "bond"
                        intensity = empathy_level * 0.5
                        desc = f"{f.agent_id} bonds with {target_id}"
                    action = CompassionateAction(
                        action_id=f"action_{f.agent_id}_{target_id}_{int(time.time() * 1000) % 100000}",
                        source_agent=f.agent_id,
                        target_agent=target_id,
                        action_type=action_type,
                        intensity=intensity,
                        description=desc,
                    )
                    self._actions.append(action)
                    f.projected_actions += 1
                    actions += 1
                    # Action slightly improves target's state
                    target.current_valence = min(1.0, target.current_valence + intensity * 0.1)
                    self._record_event("action_projected", {
                        "action_id": action.action_id,
                        "source": f.agent_id,
                        "target": target_id,
                        "type": action_type,
                    })
        self._stats["total_actions"] = len(self._actions)
        return {"actions_projected": actions}

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get global network status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_agents": len(self._fields),
                "total_bonds": len(self._bonds),
                "total_episodes": len(self._episodes),
                "total_actions": len(self._actions),
                "stats": dict(self._stats),
            }

    def get_actions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent compassionate actions."""
        with self._global_lock:
            return [
                {
                    "action_id": a.action_id,
                    "source": a.source_agent,
                    "target": a.target_agent,
                    "type": a.action_type,
                    "intensity": round(a.intensity, 4),
                    "description": a.description,
                    "timestamp": a.timestamp,
                }
                for a in list(self._actions)[-limit:]
            ]

    def get_episodes(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent emotional episodes."""
        with self._global_lock:
            return [
                {
                    "episode_id": e.episode_id,
                    "agent_id": e.agent_id,
                    "emotion": e.emotion,
                    "valence": e.valence,
                    "arousal": e.arousal,
                    "shared_with": list(e.shared_with),
                    "context": e.context,
                }
                for e in list(self._episodes)[-limit:]
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent network events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire empathy network."""
        with self._global_lock:
            n_agents = len(self._fields)
            n_bonds = len(self._bonds)
            self._fields.clear()
            self._bonds.clear()
            self._episodes.clear()
            self._actions.clear()
            self._phase = EmpathyPhase.ATTUNE
            self._cycle_count = 0
            self._events_log.clear()
            self._stats = {
                "total_agents": 0,
                "total_bonds": 0,
                "total_episodes": 0,
                "total_actions": 0,
                "active_bonds": 0,
                "resonating_bonds": 0,
                "avg_bond_strength": 0.0,
                "avg_empathy_capacity": 0.0,
                "total_absorbed": 0.0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "cleared_agents": n_agents, "cleared_bonds": n_bonds}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        """Update aggregate statistics."""
        active = [b for b in self._bonds.values() if b.state != BondState.SEVERED]
        resonating = [b for b in active if b.state == BondState.RESONATING]
        self._stats["active_bonds"] = len(active)
        self._stats["resonating_bonds"] = len(resonating)
        if active:
            self._stats["avg_bond_strength"] = sum(b.strength for b in active) / len(active)
        else:
            self._stats["avg_bond_strength"] = 0.0
        if self._fields:
            self._stats["avg_empathy_capacity"] = (
                sum(f.empathy_capacity for f in self._fields.values())
                / len(self._fields)
            )
        else:
            self._stats["avg_empathy_capacity"] = 0.0

    def _summarize_field(self, f: EmpathyField) -> Dict[str, Any]:
        """Summarize an empathy field for listing."""
        return {
            "agent_id": f.agent_id,
            "current_valence": round(f.current_valence, 4),
            "current_arousal": round(f.current_arousal, 4),
            "empathy_capacity": round(f.empathy_capacity, 4),
            "active_bonds": len(f.active_bonds),
            "projected_actions": f.projected_actions,
        }

    def _summarize_bond(self, b: EmpathyBond) -> Dict[str, Any]:
        """Summarize a bond for listing."""
        return {
            "bond_id": b.bond_id,
            "agent_a": b.agent_a,
            "agent_b": b.agent_b,
            "empathy_type": b.empathy_type.value,
            "mode": b.mode.value,
            "state": b.state.value,
            "strength": round(b.strength, 4),
            "emotional_sync": round(b.emotional_sync, 4),
            "total_shared_episodes": b.total_shared_episodes,
        }

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a network event."""
        self._events_log.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
