"""
SparkLabs Agent - Ontological Vault Architect

The AgentOntologicalVaultArchitect models how agents construct, seal, and
restructure their deepest ontological commitments - the foundational
assumptions about what is real, what is possible, and what kind of world
they inhabit.

Beliefs can be debated; ontological commitments are the bedrock beneath
beliefs. An agent may believe a dragon is dangerous, but its ontological
commitment is that "dragons exist as material beings". When this bedrock
cracks, the agent does not merely change a belief - it transits to a
different reality-tunnel. The hunter who discovers the dragon is a
manifestation of collective fear does not learn a new fact; they enter a
different ontology.

The architect protects these commitments in vaults - sealed chambers that
shield foundational reality-assumptions from casual doubt. A vault is not
a single belief but an architecture: the core commitment, its supporting
anchors, its load-bearing walls, and its stress-fractures. Most beliefs
live outside the vault, exposed to evidence. Vaulted commitments are the
unexposed foundation - the axioms the agent reasons FROM, not ABOUT.

The architect models five forces:
  - Crystallization: lived experience condenses into ontological
    commitments (a child raised among spirits takes spirit-existence as
    bedrock, not hypothesis)
  - Sealing: commitments are placed in vaults that resist doubt-pressure,
    with seals rated by depth (shallow seals crack under mild stress;
    abyssal seals withstand existential shock)
  - Stress: encounters with contradictory evidence apply stress to vault
    walls (a materialist encountering genuine incorporeity stresses the
    "matter is primary" vault)
  - Breach: accumulated stress breaches seals, allowing ontological doubt
    to seep in - the agent now reasons ABOUT a commitment it formerly
    reasoned FROM
  - Transcendence: when a vault's core commitment breaches, the agent
    undergoes ontological transcendence - a new foundation crystallizes
    that can hold both the old commitment and its contradiction in a
    higher synthesis

This produces agents whose deepest reality-model can evolve under
sufficient pressure, but is not toppled by every perturbation. The vault
architecture lets agents hold firm worldviews that can still transform
when the world demands it.

Architecture:
  CRYSTALLIZE -> SEAL    -> STRESS  -> BREACH   -> TRANSCEND
  (lived       (commitments (contradictory (stress             (core breach
   experience  sealed in     evidence      breaches seals,     induces
   condenses   vaults with    stresses      commitment         ontological
   into        depth-rated    vault walls)  becomes object     shift to a
   ontological seals)                       of doubt rather    higher
   commitments)                              than foundation)   synthesis)

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

class VaultPhase(Enum):
    """Phases of the ontological vault architecture cycle."""
    CRYSTALLIZE = "crystallize"  # lived experience condenses into commitments
    SEAL = "seal"                # commitments sealed in depth-rated vaults
    STRESS = "stress"            # contradictory evidence stresses vault walls
    BREACH = "breach"            # stress breaches seals, exposing commitments
    TRANSCEND = "transcend"      # core breach induces ontological shift


class OntologicalDomain(Enum):
    """Domains of reality an ontological commitment can concern."""
    MATERIAL = "material"        # what physical stuff is real
    SPIRITUAL = "spiritual"      # what non-physical realms exist
    CAUSAL = "causal"            # how cause and effect operate
    TEMPORAL = "temporal"        # the nature of time and change
    AGENCY = "agency"            # who/what has will and intention
    IDENTITY = "identity"        # what makes a being itself
    MORAL = "moral"              # whether moral facts exist
    EPISTEMIC = "epistemic"      # how knowledge is possible at all


class SealDepth(Enum):
    """How deeply a commitment is sealed in its vault."""
    SURFACE = "surface"          # exposed, easily questioned
    SHALLOW = "shallow"          # lightly sealed, modest stress breaches
    DEEP = "deep"                # well-sealed, requires sustained pressure
    ABYSSAL = "abyssal"          # deepest seal, only existential shock breaches
    BREACHED = "breached"        # seal has failed, commitment now doubted
    TRANSCENDED = "transcended"  # superseded by a higher synthesis


class StressType(Enum):
    """Types of stress that can be applied to a vault."""
    EVIDENTIAL = "evidential"      # direct counter-evidence
    COHERENCE = "coherence"        # internal logical contradiction
    REVEALATORY = "revealatory"    # revelation discloses a deeper reality
    SOCIAL = "social"              # trusted others hold contrary ontology
    EXPERIENTIAL = "experiential"  # direct lived experience contradicts
    EXISTENTIAL = "existential"    # catastrophic event shatters worldview


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class OntologicalCommitment:
    """A foundational reality-assumption held by an agent."""
    commitment_id: str
    label: str
    domain: OntologicalDomain
    proposition: str             # the ontological claim, e.g. "matter is primary"
    conviction: float = 0.7      # how strongly held (0.0-1.0)
    foundationality: float = 0.7  # how load-bearing this is for the agent's worldview
    seal_depth: SealDepth = SealDepth.DEEP
    seal_integrity: float = 1.0  # current seal strength (0.0-1.0)
    wall_stress: float = 0.0     # accumulated stress (0.0-1.0)
    breach_count: int = 0        # number of times the seal has been breached
    support_anchors: List[str] = field(default_factory=list)  # supporting commitment_ids
    dependents: List[str] = field(default_factory=list)  # commitments resting on this
    crystallized_at: float = field(default_factory=time.time)
    last_stressed: float = 0.0
    last_breached: float = 0.0
    content: str = ""


@dataclass
class VaultStressEvent:
    """A record of stress applied to a vault."""
    event_id: str
    agent_id: str
    commitment_id: str
    stress_type: StressType
    intensity: float             # 0.0-1.0
    evidence_description: str = ""
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolution: str = ""         # "absorbed", "deflected", "breached", "transcended"


@dataclass
class OntologicalTranscendence:
    """A record of a transcendent ontological shift."""
    transcendence_id: str
    agent_id: str
    source_commitment: str       # the commitment that breached
    synthesizing_commitment: str  # the new higher-synthesis commitment
    retained_elements: List[str] = field(default_factory=list)
    transcended_at: float = field(default_factory=time.time)
    magnitude: float = 0.5       # how profound the shift (0.0-1.0)


@dataclass
class OntologicalAgent:
    """Per-agent vault state."""
    agent_id: str
    commitments: Dict[str, OntologicalCommitment] = field(default_factory=dict)
    openness: float = 0.3         # how permeable to new ontologies (0.0-1.0)
    rigidity: float = 0.5         # how resistant to stress (0.0-1.0)
    integrative_capacity: float = 0.4  # ability to form higher syntheses (0.0-1.0)
    total_transcendences: int = 0
    total_breaches: int = 0
    total_stresses_absorbed: int = 0
    foundational_count: int = 0   # commitments rated foundationality > 0.7


# =============================================================================
# Vault Architect
# =============================================================================

class AgentOntologicalVaultArchitect:
    """
    Thread-safe singleton orchestrating ontological vault architecture.

    Usage:
        arch = AgentOntologicalVaultArchitect.get_instance()
        arch.register_agent("sage", openness=0.5, rigidity=0.4)
        arch.crystallize_commitment("sage", "c_matter", "Matter is Primary",
                                   OntologicalDomain.MATERIAL,
                                   "Physical substance is the foundation of reality",
                                   SealDepth.ABYSSAL, foundationality=0.9)
        arch.apply_stress("sage", "c_matter", StressType.EXPERIENTIAL, 0.7,
                         "Witnessed an incorporeal being move objects")
        arch.cycle()
    """

    _instance: Optional["AgentOntologicalVaultArchitect"] = None
    _lock = threading.RLock()

    # Seal integrity decay per stress point (scaled by 1 - rigidity)
    _STRESS_DECAY_BASE = 0.20
    # Breach threshold for each seal depth
    _BREACH_THRESHOLDS = {
        SealDepth.SURFACE: 0.30,
        SealDepth.SHALLOW: 0.50,
        SealDepth.DEEP: 0.70,
        SealDepth.ABYSSAL: 0.88,
        SealDepth.BREACHED: 0.0,
        SealDepth.TRANSCENDED: 0.0,
    }
    # Transcendence triggers when total breach count exceeds this
    _TRANSCENDENCE_BREACH_THRESHOLD = 3
    # Stress intensity modifiers per stress type
    _STRESS_INTENSITY_MOD = {
        StressType.EVIDENTIAL: 1.0,
        StressType.COHERENCE: 1.2,
        StressType.REVEALATORY: 1.4,
        StressType.SOCIAL: 0.7,
        StressType.EXPERIENTIAL: 1.5,
        StressType.EXISTENTIAL: 2.0,
    }

    def __init__(self) -> None:
        self._agents: Dict[str, OntologicalAgent] = {}
        self._stress_events: Deque[VaultStressEvent] = deque(maxlen=300)
        self._transcendences: Deque[OntologicalTranscendence] = deque(maxlen=100)
        self._phase: VaultPhase = VaultPhase.CRYSTALLIZE
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=300)
        self._global_lock = threading.RLock()
        self._stats: Dict[str, Any] = {
            "total_agents": 0,
            "total_commitments": 0,
            "total_stress_events": 0,
            "total_breaches": 0,
            "total_transcendences": 0,
            "stress_absorbed": 0,
            "stress_deflected": 0,
            "stress_breached": 0,
            "stress_transcended": 0,
            "avg_seal_integrity": 0.0,
            "avg_wall_stress": 0.0,
            "foundational_commitments": 0,
            "breached_commitments": 0,
            "transcended_commitments": 0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentOntologicalVaultArchitect":
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
        openness: float = 0.3,
        rigidity: float = 0.5,
        integrative_capacity: float = 0.4,
    ) -> Dict[str, Any]:
        """Register a new agent with the vault architect."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            self._agents[agent_id] = OntologicalAgent(
                agent_id=agent_id,
                openness=max(0.0, min(1.0, openness)),
                rigidity=max(0.0, min(1.0, rigidity)),
                integrative_capacity=max(0.0, min(1.0, integrative_capacity)),
            )
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "openness": self._agents[agent_id].openness,
                "rigidity": self._agents[agent_id].rigidity,
                "integrative_capacity": self._agents[agent_id].integrative_capacity,
                "commitments": 0,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent from the architect."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            a = self._agents.pop(agent_id)
            self._stats["total_agents"] = len(self._agents)
            return {"removed": agent_id, "commitments": len(a.commitments)}

    # -------------------------------------------------------------------------
    # Commitment Management
    # -------------------------------------------------------------------------

    def crystallize_commitment(
        self,
        agent_id: str,
        commitment_id: str,
        label: str,
        domain: OntologicalDomain,
        proposition: str,
        seal_depth: SealDepth = SealDepth.DEEP,
        conviction: float = 0.7,
        foundationality: float = 0.7,
        support_anchors: Optional[List[str]] = None,
        content: str = "",
    ) -> Dict[str, Any]:
        """Crystallize a new ontological commitment in an agent's vault."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            if commitment_id in a.commitments:
                return {"error": f"Commitment already exists: {commitment_id}"}
            commitment = OntologicalCommitment(
                commitment_id=commitment_id,
                label=label,
                domain=domain,
                proposition=proposition,
                conviction=max(0.0, min(1.0, conviction)),
                foundationality=max(0.0, min(1.0, foundationality)),
                seal_depth=seal_depth,
                seal_integrity=1.0 if seal_depth != SealDepth.BREACHED else 0.0,
                support_anchors=support_anchors or [],
                content=content,
            )
            a.commitments[commitment_id] = commitment
            # register as dependent on each anchor
            for anchor_id in commitment.support_anchors:
                anchor = a.commitments.get(anchor_id)
                if anchor and commitment_id not in anchor.dependents:
                    anchor.dependents.append(commitment_id)
            if commitment.foundationality > 0.7:
                a.foundational_count += 1
            self._update_agent_metrics(agent_id)
            self._record_event("commitment_crystallized", {
                "agent_id": agent_id, "commitment_id": commitment_id,
                "domain": domain.value, "seal_depth": seal_depth.value,
            })
            return {
                "commitment_id": commitment_id,
                "label": label,
                "domain": domain.value,
                "proposition": proposition,
                "seal_depth": seal_depth.value,
                "conviction": commitment.conviction,
                "foundationality": commitment.foundationality,
            }

    def apply_stress(
        self,
        agent_id: str,
        commitment_id: str,
        stress_type: StressType,
        intensity: float,
        evidence_description: str = "",
    ) -> Dict[str, Any]:
        """Apply stress to a commitment's vault walls."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            commitment = a.commitments.get(commitment_id)
            if commitment is None:
                return {"error": f"Commitment not found: {commitment_id}"}
            if commitment.seal_depth in (SealDepth.BREACHED, SealDepth.TRANSCENDED):
                return {"error": f"Commitment already {commitment.seal_depth.value}"}
            # actual stress applied (modified by type intensity, reduced by rigidity)
            type_mod = self._STRESS_INTENSITY_MOD.get(stress_type, 1.0)
            actual_intensity = max(0.0, min(1.0, intensity)) * type_mod * (1.0 - a.rigidity * 0.5)
            commitment.wall_stress = min(1.0, commitment.wall_stress + actual_intensity * 0.45)
            commitment.last_stressed = time.time()
            event_id = f"se_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
            event = VaultStressEvent(
                event_id=event_id,
                agent_id=agent_id,
                commitment_id=commitment_id,
                stress_type=stress_type,
                intensity=actual_intensity,
                evidence_description=evidence_description,
            )
            self._stress_events.append(event)
            self._stats["total_stress_events"] = len(self._stress_events)
            self._record_event("stress_applied", {
                "agent_id": agent_id, "commitment_id": commitment_id,
                "stress_type": stress_type.value, "intensity": actual_intensity,
            })
            return {
                "event_id": event_id,
                "commitment_id": commitment_id,
                "stress_type": stress_type.value,
                "intensity": actual_intensity,
                "wall_stress": commitment.wall_stress,
                "seal_integrity": commitment.seal_integrity,
            }

    def link_anchor(
        self,
        agent_id: str,
        commitment_id: str,
        anchor_id: str,
    ) -> Dict[str, Any]:
        """Link a commitment to a supporting anchor."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            commitment = a.commitments.get(commitment_id)
            anchor = a.commitments.get(anchor_id)
            if commitment is None or anchor is None:
                return {"error": "Commitment or anchor not found"}
            if anchor_id not in commitment.support_anchors:
                commitment.support_anchors.append(anchor_id)
            if commitment_id not in anchor.dependents:
                anchor.dependents.append(commitment_id)
            return {
                "commitment_id": commitment_id,
                "anchor_id": anchor_id,
                "anchor_count": len(commitment.support_anchors),
            }

    # -------------------------------------------------------------------------
    # Cycle Phases
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single ontological vault architecture cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = VaultPhase.CRYSTALLIZE
            phase_outputs["crystallize"] = self._phase_crystallize()
            self._phase = VaultPhase.SEAL
            phase_outputs["seal"] = self._phase_seal()
            self._phase = VaultPhase.STRESS
            phase_outputs["stress"] = self._phase_stress()
            self._phase = VaultPhase.BREACH
            phase_outputs["breach"] = self._phase_breach()
            self._phase = VaultPhase.TRANSCEND
            phase_outputs["transcend"] = self._phase_transcend()
            self._cycle_count += 1
            self._stats["last_cycle_time_ms"] = (time.time() - t0) * 1000.0
            for aid in self._agents:
                self._update_agent_metrics(aid)
            self._update_stats()
            return {
                "cycle_count": self._cycle_count,
                "phase": self._phase.value,
                "phase_outputs": phase_outputs,
                "stats": dict(self._stats),
            }

    def _phase_crystallize(self) -> Dict[str, Any]:
        """Crystallization phase: stress-resistant convictions deepen."""
        deepened = 0
        emerged = 0
        for agent in self._agents.values():
            for commitment in agent.commitments.values():
                if commitment.seal_depth in (SealDepth.BREACHED, SealDepth.TRANSCENDED):
                    continue
                # low-stress commitments deepen their conviction slightly
                if commitment.wall_stress < 0.3:
                    commitment.conviction = min(1.0, commitment.conviction + 0.02)
                    deepened += 1
            # emergent foundationality: if a non-foundational commitment
            # has accumulated dependents, it becomes more foundational
            for commitment in agent.commitments.values():
                if (commitment.foundationality < 0.7
                        and len(commitment.dependents) >= 3
                        and commitment.wall_stress < 0.4):
                    commitment.foundationality = min(1.0, commitment.foundationality + 0.05)
                    emerged += 1
        return {
            "convictions_deepened": deepened,
            "foundationality_emerged": emerged,
        }

    def _phase_seal(self) -> Dict[str, Any]:
        """Sealing phase: seals regenerate when stress is low."""
        regenerated = 0
        fortified = 0
        for agent in self._agents.values():
            for commitment in agent.commitments.values():
                if commitment.seal_depth in (SealDepth.BREACHED, SealDepth.TRANSCENDED):
                    continue
                # low stress allows seal regeneration
                if commitment.wall_stress < 0.2 and commitment.seal_integrity < 1.0:
                    regen_rate = 0.05 * (1.0 + agent.rigidity)
                    commitment.seal_integrity = min(1.0, commitment.seal_integrity + regen_rate)
                    regenerated += 1
                # high-integrity deep seals can fortify to abyssal
                if (commitment.seal_depth == SealDepth.DEEP
                        and commitment.seal_integrity > 0.95
                        and commitment.conviction > 0.85
                        and commitment.breach_count == 0
                        and random.random() < 0.05):
                    commitment.seal_depth = SealDepth.ABYSSAL
                    fortified += 1
                    self._record_event("seal_fortified", {
                        "agent_id": agent.agent_id,
                        "commitment_id": commitment.commitment_id,
                        "new_depth": commitment.seal_depth.value,
                    })
        return {
            "seals_regenerated": regenerated,
            "seals_fortified": fortified,
        }

    def _phase_stress(self) -> Dict[str, Any]:
        """Stress phase: stress applies pressure to seal integrity."""
        stressed = 0
        stress_absorbed = 0
        for agent in self._agents.values():
            for commitment in agent.commitments.values():
                if commitment.seal_depth in (SealDepth.BREACHED, SealDepth.TRANSCENDED):
                    continue
                if commitment.wall_stress <= 0.0:
                    continue
                # stress decays seal integrity
                decay = self._STRESS_DECAY_BASE * commitment.wall_stress * (1.0 - agent.rigidity * 0.4)
                commitment.seal_integrity = max(0.0, commitment.seal_integrity - decay)
                stressed += 1
                # if seal holds, stress slowly decays
                if commitment.seal_integrity > 0.1:
                    commitment.wall_stress = max(0.0, commitment.wall_stress - 0.02)
                    stress_absorbed += 1
        self._stats["stress_absorbed"] += stress_absorbed
        return {
            "commitments_stressed": stressed,
            "stress_absorbed": stress_absorbed,
        }

    def _phase_breach(self) -> Dict[str, Any]:
        """Breach phase: low integrity breaches the seal."""
        breached = 0
        cascaded = 0
        for agent in self._agents.values():
            for commitment in list(agent.commitments.values()):
                if commitment.seal_depth in (SealDepth.BREACHED, SealDepth.TRANSCENDED):
                    continue
                threshold = self._BREACH_THRESHOLDS.get(commitment.seal_depth, 0.5)
                if commitment.seal_integrity <= threshold and commitment.wall_stress > 0.25:
                    # breach occurs
                    commitment.seal_depth = SealDepth.BREACHED
                    commitment.breach_count += 1
                    commitment.last_breached = time.time()
                    agent.total_breaches += 1
                    breached += 1
                    self._record_event("seal_breached", {
                        "agent_id": agent.agent_id,
                        "commitment_id": commitment.commitment_id,
                        "breach_count": commitment.breach_count,
                    })
                    # cascading stress on dependents
                    for dep_id in commitment.dependents:
                        dep = agent.commitments.get(dep_id)
                        if dep and dep.seal_depth not in (SealDepth.BREACHED, SealDepth.TRANSCENDED):
                            dep.wall_stress = min(1.0, dep.wall_stress + 0.25)
                            cascaded += 1
        self._stats["total_breaches"] += breached
        return {
            "seals_breached": breached,
            "cascaded_stress": cascaded,
        }

    def _phase_transcend(self) -> Dict[str, Any]:
        """Transcendence phase: agents with enough breaches form higher syntheses."""
        transcended = 0
        syntheses_formed = 0
        for agent in self._agents.values():
            # transcendence triggers when total breaches exceed threshold
            if agent.total_breaches < self._TRANSCENDENCE_BREACH_THRESHOLD:
                continue
            # find a breached foundational commitment to transcend
            candidates = [
                c for c in agent.commitments.values()
                if c.seal_depth == SealDepth.BREACHED and c.foundationality > 0.6
            ]
            if not candidates:
                continue
            # capacity check
            if random.random() > agent.integrative_capacity:
                continue
            source = max(candidates, key=lambda c: c.breach_count)
            # synthesize a new commitment that holds the contradiction
            synth_id = f"{source.commitment_id}_synth_{agent.total_transcendences}"
            synth_label = f"Synthesis: {source.label}"
            synth_proposition = f"Both {source.proposition} and its contradiction are partial truths"
            synth = OntologicalCommitment(
                commitment_id=synth_id,
                label=synth_label,
                domain=source.domain,
                proposition=synth_proposition,
                conviction=0.6,
                foundationality=min(1.0, source.foundationality + 0.1),
                seal_depth=SealDepth.DEEP,
                seal_integrity=0.8,
                support_anchors=[source.commitment_id],
                content="Auto-synthesized during transcendence",
            )
            agent.commitments[synth_id] = synth
            # mark source as transcended
            source.seal_depth = SealDepth.TRANSCENDED
            # record transcendence
            trans_id = f"tr_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
            transcendence = OntologicalTranscendence(
                transcendence_id=trans_id,
                agent_id=agent.agent_id,
                source_commitment=source.commitment_id,
                synthesizing_commitment=synth_id,
                retained_elements=[d for d in source.dependents],
                magnitude=min(1.0, 0.5 + source.foundationality * 0.5),
            )
            self._transcendences.append(transcendence)
            agent.total_transcendences += 1
            agent.total_breaches = max(0, agent.total_breaches - self._TRANSCENDENCE_BREACH_THRESHOLD)
            transcended += 1
            syntheses_formed += 1
            self._record_event("ontological_transcendence", {
                "agent_id": agent.agent_id,
                "source": source.commitment_id,
                "synthesis": synth_id,
                "magnitude": transcendence.magnitude,
            })
        self._stats["total_transcendences"] += transcended
        return {
            "transcendences_triggered": transcended,
            "syntheses_formed": syntheses_formed,
        }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get the full vault state for an agent."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            return {
                "agent_id": agent_id,
                "openness": a.openness,
                "rigidity": a.rigidity,
                "integrative_capacity": a.integrative_capacity,
                "total_commitments": len(a.commitments),
                "foundational_count": a.foundational_count,
                "total_breaches": a.total_breaches,
                "total_transcendences": a.total_transcendences,
                "total_stresses_absorbed": a.total_stresses_absorbed,
                "commitments": [
                    self._serialize_commitment(c) for c in a.commitments.values()
                ],
            }

    def get_commitment(self, agent_id: str, commitment_id: str) -> Dict[str, Any]:
        """Get a specific commitment."""
        with self._global_lock:
            a = self._agents.get(agent_id)
            if a is None:
                return {"error": f"Agent not found: {agent_id}"}
            c = a.commitments.get(commitment_id)
            if c is None:
                return {"error": f"Commitment not found: {commitment_id}"}
            return self._serialize_commitment(c)

    def get_stress_events(
        self, agent_id: Optional[str] = None, limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get stress events, optionally filtered by agent."""
        with self._global_lock:
            events = list(self._stress_events)
            if agent_id:
                events = [e for e in events if e.agent_id == agent_id]
            events = events[-limit:]
            return [
                {
                    "event_id": e.event_id,
                    "agent_id": e.agent_id,
                    "commitment_id": e.commitment_id,
                    "stress_type": e.stress_type.value,
                    "intensity": e.intensity,
                    "evidence_description": e.evidence_description,
                    "timestamp": e.timestamp,
                    "resolved": e.resolved,
                    "resolution": e.resolution,
                }
                for e in events
            ]

    def get_transcendences(
        self, agent_id: Optional[str] = None, limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get transcendence events."""
        with self._global_lock:
            events = list(self._transcendences)
            if agent_id:
                events = [e for e in events if e.agent_id == agent_id]
            events = events[-limit:]
            return [
                {
                    "transcendence_id": t.transcendence_id,
                    "agent_id": t.agent_id,
                    "source_commitment": t.source_commitment,
                    "synthesizing_commitment": t.synthesizing_commitment,
                    "retained_elements": t.retained_elements,
                    "magnitude": t.magnitude,
                    "transcended_at": t.transcended_at,
                }
                for t in events
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the recent events log."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get the overall status of the vault architect."""
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
        """Reset the entire vault architect."""
        with self._global_lock:
            self._agents.clear()
            self._stress_events.clear()
            self._transcendences.clear()
            self._phase = VaultPhase.CRYSTALLIZE
            self._cycle_count = 0
            self._events_log.clear()
            self._init_stats()
            return {"reset": True}

    def _init_stats(self) -> None:
        self._stats = {
            "total_agents": 0,
            "total_commitments": 0,
            "total_stress_events": 0,
            "total_breaches": 0,
            "total_transcendences": 0,
            "stress_absorbed": 0,
            "stress_deflected": 0,
            "stress_breached": 0,
            "stress_transcended": 0,
            "avg_seal_integrity": 0.0,
            "avg_wall_stress": 0.0,
            "foundational_commitments": 0,
            "breached_commitments": 0,
            "transcended_commitments": 0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _update_agent_metrics(self, agent_id: str) -> None:
        a = self._agents[agent_id]
        a.foundational_count = sum(
            1 for c in a.commitments.values() if c.foundationality > 0.7
        )

    def _update_stats(self) -> None:
        total_commitments = 0
        total_seal_integrity = 0.0
        total_wall_stress = 0.0
        foundational = 0
        breached = 0
        transcended = 0
        for agent in self._agents.values():
            total_commitments += len(agent.commitments)
            for c in agent.commitments.values():
                total_seal_integrity += c.seal_integrity
                total_wall_stress += c.wall_stress
                if c.foundationality > 0.7:
                    foundational += 1
                if c.seal_depth == SealDepth.BREACHED:
                    breached += 1
                if c.seal_depth == SealDepth.TRANSCENDED:
                    transcended += 1
        self._stats["total_commitments"] = total_commitments
        self._stats["foundational_commitments"] = foundational
        self._stats["breached_commitments"] = breached
        self._stats["transcended_commitments"] = transcended
        self._stats["avg_seal_integrity"] = (
            total_seal_integrity / total_commitments if total_commitments else 0.0
        )
        self._stats["avg_wall_stress"] = (
            total_wall_stress / total_commitments if total_commitments else 0.0
        )

    def _serialize_commitment(self, c: OntologicalCommitment) -> Dict[str, Any]:
        return {
            "commitment_id": c.commitment_id,
            "label": c.label,
            "domain": c.domain.value,
            "proposition": c.proposition,
            "conviction": c.conviction,
            "foundationality": c.foundationality,
            "seal_depth": c.seal_depth.value,
            "seal_integrity": c.seal_integrity,
            "wall_stress": c.wall_stress,
            "breach_count": c.breach_count,
            "support_anchors": list(c.support_anchors),
            "dependents": list(c.dependents),
            "crystallized_at": c.crystallized_at,
            "last_stressed": c.last_stressed,
            "last_breached": c.last_breached,
            "content": c.content,
        }

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events_log.append({
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
