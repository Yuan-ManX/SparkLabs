"""
SparkLabs Agent - Identity Crystallization Forge

The AgentIdentityCrystallizationForge models how an agent's sense of self
forms and transforms over time. Identity is not a fixed attribute; it is a
crystalline structure that grows from accumulated experiences, hardens
through repetition, and can fracture under contradiction or be reforged
through reflection.

The forge treats identity as a crystal lattice. Each experience deposits
a facet onto the lattice - a small face of who the agent is. Facets that
are reinforced through repetition grow larger and more defined, while
facets that are contradicted develop stress fractures. When stress
exceeds the crystal's temper, the identity fractures - a crisis of self
that can either shatter the agent's confidence or, through tempering,
produce a more nuanced and resilient identity.

The forge also models identity refraction: how an agent's core identity
bends and colors new experiences. An agent who sees themselves as a
protector will interpret a stranger's request for help differently than
one who sees themselves as a lone wolf. This creates a feedback loop
where identity shapes experience, and experience reshapes identity.

Architecture:
  DISTILL      ->  CRYSTALLIZE  ->  TEMPER     ->  FRACTURE   ->  REFRACT
  (extract       (facets          (repetition     (stress from    (identity
   identity      deposit onto     strengthens     contradiction    colors new
   facets from   the identity     facets and      exceeds temper,   experiences
   experiences)  lattice)         builds temper)  causing crisis)   and feedback)

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

class ForgePhase(Enum):
    """Phases of the identity crystallization cycle."""
    DISTILL = "distill"           # extract identity facets from experiences
    CRYSTALLIZE = "crystallize"   # deposit facets onto the identity lattice
    TEMPER = "temper"             # repetition strengthens facets and builds temper
    FRACTURE = "fracture"         # contradiction causes stress fractures
    REFRACT = "refract"           # identity colors new experiences


class FacetDomain(Enum):
    """Domains of identity facets."""
    ROLE = "role"                 # what the agent does (warrior, healer, leader)
    VALUE = "value"               # what the agent believes in (justice, freedom)
    RELATION = "relation"         # how the agent connects to others (loyal, aloof)
    ABILITY = "ability"           # what the agent can do (skilled, learning)
    TRAIT = "trait"               # personality characteristics (brave, cautious)
    HISTORY = "history"           # formative past experiences
    ASPIRATION = "aspiration"     # what the agent wants to become


class FacetState(Enum):
    """State of an identity facet."""
    NUCLEATING = "nucleating"     # just forming, not yet part of identity
    GROWING = "growing"           # actively developing
    CRYSTALLIZED = "crystallized" # solid part of identity
    STRESSED = "stressed"         # under contradiction pressure
    FRACTURED = "fractured"       # cracked but still present
    DISSOLVED = "dissolved"       # no longer part of identity


class CrisisType(Enum):
    """Types of identity crisis that can occur during fracture."""
    ROLE_CONFLICT = "role_conflict"       # contradictory role demands
    VALUE_BETRAYAL = "value_betrayal"     # actions violated core values
    RELATION_LOSS = "relation_loss"       # loss of defining relationship
    ABILITY_FAILURE = "ability_failure"   # failure in core competency
    TRAIT_CONTRADICTION = "trait_contradiction"  # behavior contradicts traits


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class IdentityFacet:
    """A single facet of an agent's identity."""
    facet_id: str
    agent_id: str
    domain: FacetDomain
    label: str
    description: str = ""
    state: FacetState = FacetState.NUCLEATING
    clarity: float = 0.1           # 0.0-1.0: how well-defined the facet is
    weight: float = 0.1            # 0.0-1.0: how central to identity
    temper: float = 0.0            # 0.0-1.0: resistance to fracture
    stress: float = 0.0            # 0.0-1.0: accumulated contradiction pressure
    reinforcement_count: int = 0
    contradiction_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_reinforced: float = field(default_factory=time.time)
    facets_aligned: Set[str] = field(default_factory=set)
    facets_opposed: Set[str] = field(default_factory=set)


@dataclass
class ExperienceDeposit:
    """An experience that deposits material onto identity facets."""
    deposit_id: str
    agent_id: str
    label: str
    domain: FacetDomain
    valence: float = 0.0           # -1.0 to 1.0: positive/negative experience
    intensity: float = 0.5         # 0.0-1.0: how impactful
    target_facets: List[str] = field(default_factory=list)
    is_contradiction: bool = False
    timestamp: float = field(default_factory=time.time)
    description: str = ""


@dataclass
class IdentityCrisis:
    """A recorded identity crisis event."""
    crisis_id: str
    agent_id: str
    crisis_type: CrisisType
    severity: float                # 0.0-1.0
    fractured_facets: List[str] = field(default_factory=list)
    resolved: bool = False
    resolution: str = ""           # "tempered", "shattered", "integrated"
    timestamp: float = field(default_factory=time.time)


@dataclass
class RefractionLens:
    """How an agent's identity refracts (colors) new experiences."""
    agent_id: str
    dominant_role: str = ""
    dominant_value: str = ""
    confidence: float = 0.5        # 0.0-1.0: how strongly identity colors perception
    openness: float = 0.5          # 0.0-1.0: willingness to update identity


# =============================================================================
# Engine
# =============================================================================

class AgentIdentityCrystallizationForge:
    """
    Thread-safe singleton orchestrating identity crystallization across agents.

    Usage:
        forge = AgentIdentityCrystallizationForge.get_instance()
        forge.register_agent("hero")
        forge.add_facet("hero", "f_protector", FacetDomain.ROLE, "Protector")
        forge.deposit_experience("dep_1", "hero", "Saved a child",
                                 FacetDomain.ROLE, 0.8, 0.7, ["f_protector"])
        forge.deposit_experience("dep_2", "hero", "Failed to save them",
                                 FacetDomain.ROLE, -0.7, 0.8, ["f_protector"],
                                 is_contradiction=True)
        forge.cycle()
    """

    _instance: Optional["AgentIdentityCrystallizationForge"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._facets: Dict[str, IdentityFacet] = {}
        self._deposits: Deque[ExperienceDeposit] = deque(maxlen=500)
        self._crises: Deque[IdentityCrisis] = deque(maxlen=100)
        self._lenses: Dict[str, RefractionLens] = {}
        self._agents: Set[str] = set()
        self._phase: ForgePhase = ForgePhase.DISTILL
        self._cycle_count: int = 0
        self._events_log: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._global_lock = threading.RLock()
        self._stats = {
            "total_agents": 0,
            "total_facets": 0,
            "total_deposits": 0,
            "total_crises": 0,
            "crystallized_facets": 0,
            "fractured_facets": 0,
            "dissolved_facets": 0,
            "avg_temper": 0.0,
            "avg_clarity": 0.0,
            "resolved_crises": 0,
            "shattered_crises": 0,
            "last_cycle_time_ms": 0.0,
        }

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "AgentIdentityCrystallizationForge":
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
        confidence: float = 0.5,
        openness: float = 0.5,
    ) -> Dict[str, Any]:
        """Register a new agent in the forge."""
        with self._global_lock:
            if agent_id in self._agents:
                return {"error": f"Agent already registered: {agent_id}"}
            self._agents.add(agent_id)
            self._lenses[agent_id] = RefractionLens(
                agent_id=agent_id,
                confidence=max(0.0, min(1.0, confidence)),
                openness=max(0.0, min(1.0, openness)),
            )
            self._stats["total_agents"] = len(self._agents)
            self._record_event("agent_registered", {"agent_id": agent_id})
            return {
                "agent_id": agent_id,
                "confidence": self._lenses[agent_id].confidence,
                "openness": self._lenses[agent_id].openness,
            }

    def remove_agent(self, agent_id: str) -> Dict[str, Any]:
        """Remove an agent and all their facets."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            # Remove all facets belonging to this agent
            to_remove = [fid for fid, f in self._facets.items() if f.agent_id == agent_id]
            for fid in to_remove:
                del self._facets[fid]
            self._agents.discard(agent_id)
            self._lenses.pop(agent_id, None)
            self._stats["total_agents"] = len(self._agents)
            self._stats["total_facets"] = len(self._facets)
            self._record_event("agent_removed", {
                "agent_id": agent_id, "removed_facets": len(to_remove),
            })
            return {"removed": agent_id, "removed_facets": len(to_remove)}

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        with self._global_lock:
            return [self._summarize_agent(aid) for aid in self._agents]

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get full identity details for an agent."""
        with self._global_lock:
            if agent_id not in self._agents:
                return None
            facets = [f for f in self._facets.values() if f.agent_id == agent_id]
            lens = self._lenses.get(agent_id)
            return {
                "agent_id": agent_id,
                "total_facets": len(facets),
                "crystallized": sum(1 for f in facets if f.state == FacetState.CRYSTALLIZED),
                "stressed": sum(1 for f in facets if f.state == FacetState.STRESSED),
                "fractured": sum(1 for f in facets if f.state == FacetState.FRACTURED),
                "lens": {
                    "dominant_role": lens.dominant_role if lens else "",
                    "dominant_value": lens.dominant_value if lens else "",
                    "confidence": lens.confidence if lens else 0.5,
                    "openness": lens.openness if lens else 0.5,
                },
                "facets": [self._summarize_facet(f) for f in facets],
            }

    # -------------------------------------------------------------------------
    # Facet Management
    # -------------------------------------------------------------------------

    def add_facet(
        self,
        agent_id: str,
        facet_id: str,
        domain: FacetDomain,
        label: str,
        description: str = "",
        initial_weight: float = 0.1,
    ) -> Dict[str, Any]:
        """Add a new identity facet for an agent."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            if facet_id in self._facets:
                return {"error": f"Facet already exists: {facet_id}"}
            facet = IdentityFacet(
                facet_id=facet_id,
                agent_id=agent_id,
                domain=domain,
                label=label,
                description=description,
                weight=max(0.0, min(1.0, initial_weight)),
            )
            self._facets[facet_id] = facet
            self._stats["total_facets"] = len(self._facets)
            self._record_event("facet_added", {
                "facet_id": facet_id, "agent_id": agent_id, "domain": domain.value,
            })
            return {
                "facet_id": facet_id,
                "agent_id": agent_id,
                "domain": domain.value,
                "label": label,
                "state": facet.state.value,
            }

    def align_facets(self, facet_a: str, facet_b: str) -> Dict[str, Any]:
        """Mark two facets as aligned (mutually reinforcing)."""
        with self._global_lock:
            if facet_a not in self._facets or facet_b not in self._facets:
                return {"error": "One or both facets not found"}
            self._facets[facet_a].facets_aligned.add(facet_b)
            self._facets[facet_b].facets_aligned.add(facet_a)
            return {"aligned": [facet_a, facet_b]}

    def oppose_facets(self, facet_a: str, facet_b: str) -> Dict[str, Any]:
        """Mark two facets as opposed (mutually contradicting)."""
        with self._global_lock:
            if facet_a not in self._facets or facet_b not in self._facets:
                return {"error": "One or both facets not found"}
            self._facets[facet_a].facets_opposed.add(facet_b)
            self._facets[facet_b].facets_opposed.add(facet_a)
            return {"opposed": [facet_a, facet_b]}

    def list_facets(self, agent_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List identity facets, optionally filtered by agent."""
        with self._global_lock:
            facets = list(self._facets.values())
            if agent_id:
                facets = [f for f in facets if f.agent_id == agent_id]
            return [self._summarize_facet(f) for f in facets[:limit]]

    def get_facet(self, facet_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific facet."""
        with self._global_lock:
            f = self._facets.get(facet_id)
            return self._summarize_facet(f) if f else None

    # -------------------------------------------------------------------------
    # Experience Deposit
    # -------------------------------------------------------------------------

    def deposit_experience(
        self,
        deposit_id: str,
        agent_id: str,
        label: str,
        domain: FacetDomain,
        valence: float = 0.0,
        intensity: float = 0.5,
        target_facets: Optional[List[str]] = None,
        is_contradiction: bool = False,
        description: str = "",
    ) -> Dict[str, Any]:
        """Deposit an experience onto identity facets."""
        with self._global_lock:
            if agent_id not in self._agents:
                return {"error": f"Agent not found: {agent_id}"}
            deposit = ExperienceDeposit(
                deposit_id=deposit_id,
                agent_id=agent_id,
                label=label,
                domain=domain,
                valence=max(-1.0, min(1.0, valence)),
                intensity=max(0.0, min(1.0, intensity)),
                target_facets=target_facets or [],
                is_contradiction=is_contradiction,
                description=description,
            )
            self._deposits.append(deposit)
            self._stats["total_deposits"] = len(self._deposits)
            self._record_event("experience_deposited", {
                "deposit_id": deposit_id,
                "agent_id": agent_id,
                "domain": domain.value,
                "is_contradiction": is_contradiction,
            })
            return {
                "deposit_id": deposit_id,
                "agent_id": agent_id,
                "label": label,
                "domain": domain.value,
                "valence": deposit.valence,
                "intensity": deposit.intensity,
                "is_contradiction": is_contradiction,
                "target_facets": deposit.target_facets,
            }

    # -------------------------------------------------------------------------
    # Cycle
    # -------------------------------------------------------------------------

    def cycle(self) -> Dict[str, Any]:
        """Run a single identity crystallization cycle."""
        with self._global_lock:
            t0 = time.time()
            phase_outputs: Dict[str, Any] = {}
            self._phase = ForgePhase.DISTILL
            phase_outputs["distill"] = self._phase_distill()
            self._phase = ForgePhase.CRYSTALLIZE
            phase_outputs["crystallize"] = self._phase_crystallize()
            self._phase = ForgePhase.TEMPER
            phase_outputs["temper"] = self._phase_temper()
            self._phase = ForgePhase.FRACTURE
            phase_outputs["fracture"] = self._phase_fracture()
            self._phase = ForgePhase.REFRACT
            phase_outputs["refract"] = self._phase_refract()
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

    def _phase_distill(self) -> Dict[str, Any]:
        """DISTILL: extract identity facets from recent experiences."""
        distilled = 0
        # Process recent deposits that haven't been applied yet
        recent = list(self._deposits)[-50:]
        for deposit in recent:
            if deposit.agent_id not in self._agents:
                continue
            # Check if a matching facet already exists
            existing = [
                f for f in self._facets.values()
                if f.agent_id == deposit.agent_id and f.domain == deposit.domain
            ]
            if not existing and deposit.intensity > 0.4:
                # Create a new nucleating facet
                facet_id = f"f_{deposit.agent_id}_{deposit.domain.value}_{len(self._facets)}"
                facet = IdentityFacet(
                    facet_id=facet_id,
                    agent_id=deposit.agent_id,
                    domain=deposit.domain,
                    label=deposit.label,
                    description=deposit.description,
                    state=FacetState.NUCLEATING,
                    clarity=deposit.intensity * 0.3,
                    weight=deposit.intensity * 0.2,
                )
                self._facets[facet_id] = facet
                distilled += 1
                self._record_event("facet_nucleated", {
                    "facet_id": facet_id,
                    "agent_id": deposit.agent_id,
                    "domain": deposit.domain.value,
                })
        self._stats["total_facets"] = len(self._facets)
        return {"distilled": distilled}

    def _phase_crystallize(self) -> Dict[str, Any]:
        """CRYSTALLIZE: deposit experience material onto facets."""
        crystallized = 0
        recent = list(self._deposits)[-30:]
        for deposit in recent:
            for facet_id in deposit.target_facets:
                facet = self._facets.get(facet_id)
                if facet is None or facet.agent_id != deposit.agent_id:
                    continue
                if facet.state == FacetState.DISSOLVED:
                    continue
                if deposit.is_contradiction:
                    # Contradiction adds stress
                    facet.stress = min(1.0, facet.stress + deposit.intensity * 0.2)
                    facet.contradiction_count += 1
                    if facet.state == FacetState.NUCLEATING:
                        facet.state = FacetState.STRESSED
                    elif facet.state in (FacetState.GROWING, FacetState.CRYSTALLIZED):
                        facet.state = FacetState.STRESSED
                else:
                    # Reinforcement grows the facet
                    growth = deposit.intensity * 0.1
                    facet.clarity = min(1.0, facet.clarity + growth)
                    facet.weight = min(1.0, facet.weight + growth * 0.5)
                    facet.reinforcement_count += 1
                    facet.last_reinforced = time.time()
                    # Reduce stress slightly through reinforcement
                    facet.stress = max(0.0, facet.stress - growth * 0.3)
                    # State transitions
                    if facet.state == FacetState.NUCLEATING and facet.clarity > 0.3:
                        facet.state = FacetState.GROWING
                    elif facet.state == FacetState.GROWING and facet.clarity > 0.6:
                        facet.state = FacetState.CRYSTALLIZED
                    elif facet.state == FacetState.STRESSED and facet.stress < 0.3:
                        facet.state = FacetState.GROWING
                    elif facet.state == FacetState.FRACTURED and facet.stress < 0.2:
                        facet.state = FacetState.GROWING
                    crystallized += 1
        return {"crystallized": crystallized}

    def _phase_temper(self) -> Dict[str, Any]:
        """TEMPER: repetition strengthens facets and builds temper."""
        tempered = 0
        for facet in self._facets.values():
            if facet.state in (FacetState.DISSOLVED, FacetState.FRACTURED):
                continue
            # Temper grows with reinforcement count
            temper_growth = min(0.02, facet.reinforcement_count * 0.005)
            facet.temper = min(1.0, facet.temper + temper_growth)
            # Aligned facets provide mutual tempering
            for aligned_id in facet.facets_aligned:
                aligned = self._facets.get(aligned_id)
                if aligned and aligned.state != FacetState.DISSOLVED:
                    facet.temper = min(1.0, facet.temper + 0.005)
                    aligned.temper = min(1.0, aligned.temper + 0.005)
            tempered += 1
        return {"tempered": tempered}

    def _phase_fracture(self) -> Dict[str, Any]:
        """FRACTURE: stress from contradiction exceeds temper, causing crisis."""
        fractured = 0
        crises_triggered = 0
        for facet in list(self._facets.values()):
            if facet.state in (FacetState.DISSOLVED,):
                continue
            # Check if stress exceeds temper
            if facet.stress > facet.temper and facet.stress > 0.5:
                if facet.state != FacetState.FRACTURED:
                    old_state = facet.state
                    facet.state = FacetState.FRACTURED
                    fractured += 1
                    # Determine crisis type based on domain
                    crisis_type = {
                        FacetDomain.ROLE: CrisisType.ROLE_CONFLICT,
                        FacetDomain.VALUE: CrisisType.VALUE_BETRAYAL,
                        FacetDomain.RELATION: CrisisType.RELATION_LOSS,
                        FacetDomain.ABILITY: CrisisType.ABILITY_FAILURE,
                        FacetDomain.TRAIT: CrisisType.TRAIT_CONTRADICTION,
                    }.get(facet.domain, CrisisType.TRAIT_CONTRADICTION)
                    severity = facet.stress * (1.0 - facet.temper * 0.5)
                    crisis = IdentityCrisis(
                        crisis_id=f"crisis_{facet.facet_id}_{int(time.time() * 1000) % 100000}",
                        agent_id=facet.agent_id,
                        crisis_type=crisis_type,
                        severity=severity,
                        fractured_facets=[facet.facet_id],
                    )
                    self._crises.append(crisis)
                    crises_triggered += 1
                    self._record_event("crisis_triggered", {
                        "crisis_id": crisis.crisis_id,
                        "agent_id": facet.agent_id,
                        "facet_id": facet.facet_id,
                        "crisis_type": crisis_type.value,
                        "severity": round(severity, 3),
                    })
                    # Attempt resolution
                    self._resolve_crisis(crisis, facet)
        self._stats["total_crises"] = len(self._crises)
        return {"fractured": fractured, "crises": crises_triggered}

    def _resolve_crisis(self, crisis: IdentityCrisis, facet: IdentityFacet) -> None:
        """Attempt to resolve an identity crisis."""
        lens = self._lenses.get(crisis.agent_id)
        # Resolution depends on temper, openness, and severity
        resolve_chance = facet.temper * 0.4 + (lens.openness if lens else 0.5) * 0.3 + 0.1
        if random.random() < resolve_chance:
            # Tempered: facet survives but is transformed
            crisis.resolved = True
            crisis.resolution = "tempered"
            facet.stress = max(0.0, facet.stress * 0.3)
            facet.temper = min(1.0, facet.temper + 0.1)  # What doesn't break you...
            facet.state = FacetState.GROWING
            self._stats["resolved_crises"] += 1
        elif random.random() < 0.3:
            # Shattered: facet dissolves
            crisis.resolved = True
            crisis.resolution = "shattered"
            facet.state = FacetState.DISSOLVED
            facet.stress = 0.0
            self._stats["shattered_crises"] += 1
        else:
            # Integrated: facet remains fractured but integrated into identity
            crisis.resolved = True
            crisis.resolution = "integrated"
            facet.stress = max(0.0, facet.stress * 0.5)
            facet.state = FacetState.FRACTURED
            self._stats["resolved_crises"] += 1

    def _phase_refract(self) -> Dict[str, Any]:
        """REFRACT: identity colors new experiences through the refraction lens."""
        refracted = 0
        for agent_id in self._agents:
            facets = [f for f in self._facets.values() if f.agent_id == agent_id]
            lens = self._lenses.get(agent_id)
            if lens is None or not facets:
                continue
            # Find dominant role and value
            role_facets = [f for f in facets if f.domain == FacetDomain.ROLE and f.state == FacetState.CRYSTALLIZED]
            value_facets = [f for f in facets if f.domain == FacetDomain.VALUE and f.state == FacetState.CRYSTALLIZED]
            if role_facets:
                lens.dominant_role = max(role_facets, key=lambda f: f.weight).label
            if value_facets:
                lens.dominant_value = max(value_facets, key=lambda f: f.weight).label
            # Confidence grows with crystallized facets
            crystallized_count = sum(1 for f in facets if f.state == FacetState.CRYSTALLIZED)
            lens.confidence = min(1.0, 0.3 + crystallized_count * 0.1)
            # Openness decreases with high confidence but increases with fractured facets
            fractured_count = sum(1 for f in facets if f.state == FacetState.FRACTURED)
            lens.openness = max(0.1, min(1.0, 0.5 + fractured_count * 0.1 - crystallized_count * 0.02))
            refracted += 1
        return {"refracted": refracted}

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get global forge status."""
        with self._global_lock:
            return {
                "phase": self._phase.value,
                "cycle_count": self._cycle_count,
                "total_agents": len(self._agents),
                "total_facets": len(self._facets),
                "total_deposits": len(self._deposits),
                "total_crises": len(self._crises),
                "stats": dict(self._stats),
            }

    def get_crises(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent identity crises."""
        with self._global_lock:
            return [
                {
                    "crisis_id": c.crisis_id,
                    "agent_id": c.agent_id,
                    "crisis_type": c.crisis_type.value,
                    "severity": round(c.severity, 4),
                    "fractured_facets": c.fractured_facets,
                    "resolved": c.resolved,
                    "resolution": c.resolution,
                }
                for c in list(self._crises)[-limit:]
            ]

    def get_deposits(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent experience deposits."""
        with self._global_lock:
            return [
                {
                    "deposit_id": d.deposit_id,
                    "agent_id": d.agent_id,
                    "label": d.label,
                    "domain": d.domain.value,
                    "valence": d.valence,
                    "intensity": d.intensity,
                    "is_contradiction": d.is_contradiction,
                    "target_facets": d.target_facets,
                }
                for d in list(self._deposits)[-limit:]
            ]

    def get_events_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent forge events."""
        with self._global_lock:
            return list(self._events_log)[-limit:]

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def reset(self) -> Dict[str, Any]:
        """Reset the entire forge."""
        with self._global_lock:
            n_agents = len(self._agents)
            n_facets = len(self._facets)
            self._facets.clear()
            self._deposits.clear()
            self._crises.clear()
            self._lenses.clear()
            self._agents.clear()
            self._phase = ForgePhase.DISTILL
            self._cycle_count = 0
            self._events_log.clear()
            self._stats = {
                "total_agents": 0,
                "total_facets": 0,
                "total_deposits": 0,
                "total_crises": 0,
                "crystallized_facets": 0,
                "fractured_facets": 0,
                "dissolved_facets": 0,
                "avg_temper": 0.0,
                "avg_clarity": 0.0,
                "resolved_crises": 0,
                "shattered_crises": 0,
                "last_cycle_time_ms": 0.0,
            }
            return {"reset": True, "cleared_agents": n_agents, "cleared_facets": n_facets}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _update_stats(self) -> None:
        """Update aggregate statistics."""
        facets = list(self._facets.values())
        self._stats["crystallized_facets"] = sum(1 for f in facets if f.state == FacetState.CRYSTALLIZED)
        self._stats["fractured_facets"] = sum(1 for f in facets if f.state == FacetState.FRACTURED)
        self._stats["dissolved_facets"] = sum(1 for f in facets if f.state == FacetState.DISSOLVED)
        if facets:
            self._stats["avg_temper"] = sum(f.temper for f in facets) / len(facets)
            self._stats["avg_clarity"] = sum(f.clarity for f in facets) / len(facets)
        else:
            self._stats["avg_temper"] = 0.0
            self._stats["avg_clarity"] = 0.0

    def _summarize_agent(self, agent_id: str) -> Dict[str, Any]:
        """Summarize an agent for listing."""
        facets = [f for f in self._facets.values() if f.agent_id == agent_id]
        lens = self._lenses.get(agent_id)
        return {
            "agent_id": agent_id,
            "total_facets": len(facets),
            "crystallized": sum(1 for f in facets if f.state == FacetState.CRYSTALLIZED),
            "fractured": sum(1 for f in facets if f.state == FacetState.FRACTURED),
            "dominant_role": lens.dominant_role if lens else "",
            "confidence": round(lens.confidence, 3) if lens else 0.5,
        }

    def _summarize_facet(self, f: IdentityFacet) -> Dict[str, Any]:
        """Summarize a facet for listing."""
        return {
            "facet_id": f.facet_id,
            "agent_id": f.agent_id,
            "domain": f.domain.value,
            "label": f.label,
            "state": f.state.value,
            "clarity": round(f.clarity, 4),
            "weight": round(f.weight, 4),
            "temper": round(f.temper, 4),
            "stress": round(f.stress, 4),
            "reinforcement_count": f.reinforcement_count,
            "contradiction_count": f.contradiction_count,
            "aligned_with": list(f.facets_aligned),
            "opposed_to": list(f.facets_opposed),
        }

    def _record_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Record a forge event."""
        self._events_log.append({
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        })
