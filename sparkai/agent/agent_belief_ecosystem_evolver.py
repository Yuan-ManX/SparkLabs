"""
SparkLabs Agent - Belief Ecosystem Evolver

The AgentBeliefEcosystemEvolver models NPC beliefs as a living ecosystem
where beliefs function like species competing for territory in an NPC's
mind. Rather than static belief values, each belief is a population that
grows, shrinks, competes, forms symbiotic relationships, and can go
extinct.

This ecological metaphor captures how worldviews actually form: beliefs
don't exist in isolation - they compete for mental resources, form
alliances, prey on each other, and evolve through mutation. A new
experience is an invasive species that may flourish or die out depending
on the existing ecological balance.

Belief species properties:
  - population     : how many "mental slots" the belief occupies (0.0-1.0)
  - fitness        : how well-adapted the belief is to current conditions
  - niche          : the cognitive niche the belief occupies
  - mutation_rate  : how readily the belief spawns variants
  - carrying_cap   : maximum population the mind can sustain for this niche

Ecological relationships:
  COMPETITION   : two beliefs compete for the same cognitive niche
  SYMBIOSIS     : beliefs mutually reinforce each other
  PREDATION     : one belief suppresses another (skepticism eats superstition)
  COMMENSALISM  : one belief benefits from another without affecting it
  PARASITISM    : one belief benefits at the other's expense

Architecture:
  GERMINATE  ->  COMPETE  ->  ADAPT   ->  EVOLVE    ->  EQUILIBRATE
  (seed new      (beliefs        (beliefs     (ecological        (ecosystem
   beliefs and    compete for     mutate      relationships       reaches
   populations)   resources)      and adapt)  shape populations)   balance)

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class BeliefNiche(Enum):
    """Cognitive niches that beliefs can occupy."""
    WORLDVIEW = "worldview"          # fundamental view of reality
    MORALITY = "morality"            # ethical framework
    IDENTITY = "identity"            # self-concept
    SOCIAL = "social"                # beliefs about others
    SURVIVAL = "survival"            # threat/safety beliefs
    SPIRITUAL = "spiritual"          # transcendent beliefs
    PRACTICAL = "practical"          # everyday knowledge
    POLITICAL = "political"          # power and governance


class EcosystemPhase(Enum):
    """Phases of the belief ecosystem cycle."""
    GERMINATE = "germinate"
    COMPETE = "compete"
    ADAPT = "adapt"
    EVOLVE = "evolve"
    EQUILIBRATE = "equilibrate"


class EcologicalRelation(Enum):
    """Types of relationships between belief species."""
    COMPETITION = "competition"
    SYMBIOSIS = "symbiosis"
    PREDATION = "predation"
    COMMENSALISM = "commensalism"
    PARASITISM = "parasitism"
    NEUTRAL = "neutral"


class InvasionOutcome(Enum):
    """Outcome of a new belief attempting to invade an ecosystem."""
    FLOURISHED = "flourished"    # belief established and grew
    ESTABLISHED = "established"  # belief survived but small
    REJECTED = "rejected"        # belief couldn't gain foothold
    EXTINCT = "extinct"          # belief died out quickly


# =============================================================================
# Ecological Tables
# =============================================================================

# Relationship matrix: how belief niches interact
# (niche_a, niche_b) -> (relation, strength)
NICHE_INTERACTIONS: Dict[Tuple[BeliefNiche, BeliefNiche], Tuple[EcologicalRelation, float]] = {
    (BeliefNiche.WORLDVIEW, BeliefNiche.MORALITY): (EcologicalRelation.SYMBIOSIS, 0.7),
    (BeliefNiche.WORLDVIEW, BeliefNiche.SPIRITUAL): (EcologicalRelation.SYMBIOSIS, 0.8),
    (BeliefNiche.WORLDVIEW, BeliefNiche.PRACTICAL): (EcologicalRelation.COMPETITION, 0.3),
    (BeliefNiche.MORALITY, BeliefNiche.SURVIVAL): (EcologicalRelation.PREDATION, 0.4),
    (BeliefNiche.MORALITY, BeliefNiche.POLITICAL): (EcologicalRelation.SYMBIOSIS, 0.6),
    (BeliefNiche.IDENTITY, BeliefNiche.SOCIAL): (EcologicalRelation.SYMBIOSIS, 0.5),
    (BeliefNiche.IDENTITY, BeliefNiche.MORALITY): (EcologicalRelation.COMMENSALISM, 0.3),
    (BeliefNiche.SOCIAL, BeliefNiche.SURVIVAL): (EcologicalRelation.PARASITISM, 0.3),
    (BeliefNiche.SPIRITUAL, BeliefNiche.PRACTICAL): (EcologicalRelation.COMPETITION, 0.4),
    (BeliefNiche.SPIRITUAL, BeliefNiche.SURVIVAL): (EcologicalRelation.PARASITISM, 0.2),
    (BeliefNiche.POLITICAL, BeliefNiche.SURVIVAL): (EcologicalRelation.COMPETITION, 0.3),
    (BeliefNiche.POLITICAL, BeliefNiche.PRACTICAL): (EcologicalRelation.COMMENSALISM, 0.2),
    (BeliefNiche.PRACTICAL, BeliefNiche.SURVIVAL): (EcologicalRelation.SYMBIOSIS, 0.4),
}


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class BeliefSpecies:
    """A belief existing as a species in an NPC's mental ecosystem."""
    belief_id: str
    label: str                   # human-readable belief name
    niche: BeliefNiche
    population: float            # 0.0 - 1.0, how dominant the belief is
    fitness: float               # 0.0 - 1.0, adaptation to current conditions
    mutation_rate: float         # 0.0 - 1.0, how readily it spawns variants
    carrying_capacity: float     # max population for this niche in this mind
    # Generation count (how many cycles the belief has survived)
    generation: int = 0
    # Whether this belief is native (seeded at creation) or invasive
    is_native: bool = True
    # Metadata
    introduced_at: float = field(default_factory=time.time)
    last_adapted_at: float = field(default_factory=time.time)
    # Mutation history
    mutations: int = 0


@dataclass
class EcologicalRelationship:
    """A relationship between two belief species."""
    belief_a: str
    belief_b: str
    relation: EcologicalRelation
    strength: float              # 0.0 - 1.0
    # Current effect being applied (computed each cycle)
    current_effect_a: float = 0.0  # effect on belief_a
    current_effect_b: float = 0.0  # effect on belief_b


@dataclass
class BeliefEcosystem:
    """The complete belief ecosystem of one NPC."""
    npc_id: str
    # All belief species in the ecosystem
    species: Dict[str, BeliefSpecies]
    # Relationships between species
    relationships: List[EcologicalRelationship]
    # Ecosystem health (0.0 = collapsed, 1.0 = thriving)
    biodiversity: float = 0.5
    # Ecosystem stability (0.0 = chaotic, 1.0 = stable)
    stability: float = 0.5
    # Total carrying capacity of the mind
    total_capacity: float = 1.0
    # Metadata
    created_at: float = field(default_factory=time.time)
    cycle_count: int = 0
    invasion_count: int = 0
    extinction_count: int = 0


@dataclass
class InvasionEvent:
    """A recorded belief invasion attempt."""
    event_id: str
    npc_id: str
    belief_id: str
    belief_label: str
    niche: str
    initial_population: float
    outcome: str  # InvasionOutcome value
    timestamp: float
    description: str = ""


@dataclass
class EcosystemStats:
    """Aggregate statistics for the ecosystem evolver."""
    total_ecosystems: int = 0
    total_species: int = 0
    total_invasions: int = 0
    total_extinctions: int = 0
    total_mutations: int = 0
    total_symbioses: int = 0
    total_predations: int = 0
    avg_biodiversity: float = 0.5
    avg_stability: float = 0.5
    last_cycle_time_ms: float = 0.0
    active: bool = False


# =============================================================================
# Agent Belief Ecosystem Evolver
# =============================================================================

class AgentBeliefEcosystemEvolver:
    """
    Singleton agent that models NPC beliefs as a living ecosystem where
    beliefs compete, evolve, and form ecological relationships.

    The evolver runs a 5-phase cycle:
      1. GERMINATE    - New beliefs seed in ecosystems
      2. COMPETE      - Beliefs compete for cognitive resources
      3. ADAPT         - Beliefs mutate and adapt to conditions
      4. EVOLVE        - Ecological relationships shape populations
      5. EQUILIBRATE   - Ecosystem reaches balance or undergoes shift

    The ecological metaphor ensures NPC worldviews feel organic: beliefs
    don't flip like switches, they grow and decline like populations in
    a living ecosystem.
    """

    _instance: Optional["AgentBeliefEcosystemEvolver"] = None
    _instance_lock = threading.Lock()

    # Configuration
    MAX_ECOSYSTEMS = 200
    MAX_INVASION_HISTORY = 100
    # Minimum population for a belief to survive
    MIN_POPULATION = 0.02
    # Maximum population
    MAX_POPULATION = 1.0
    # Population growth rate per cycle
    GROWTH_RATE = 0.05
    # Population decline rate when unfit
    DECLINE_RATE = 0.03
    # Mutation probability per cycle
    MUTATION_CHANCE = 0.1
    # Mutation magnitude
    MUTATION_MAGNITUDE = 0.1
    # Extinction threshold
    EXTINCTION_THRESHOLD = 0.01
    # Biodiversity computation window
    MAX_SPECIES_PER_ECOSYSTEM = 20

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._ecosystems: Dict[str, BeliefEcosystem] = {}
        self._invasion_history: Deque[InvasionEvent] = deque(maxlen=self.MAX_INVASION_HISTORY)
        self._stats = EcosystemStats()
        self._cycle_count: int = 0
        self._active: bool = False

    @classmethod
    def get_instance(cls) -> "AgentBeliefEcosystemEvolver":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Ecosystem Management
    # -------------------------------------------------------------------------

    def create_ecosystem(self, npc_id: str,
                         beliefs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Create a new belief ecosystem for an NPC."""
        with self._lock:
            if npc_id in self._ecosystems:
                return {"error": f"Ecosystem already exists: {npc_id}"}
            if len(self._ecosystems) >= self.MAX_ECOSYSTEMS:
                return {"error": "Maximum ecosystems reached"}

            species: Dict[str, BeliefSpecies] = {}
            # Seed with default beliefs if none provided
            if not beliefs:
                beliefs = self._generate_default_beliefs()

            for b in beliefs:
                bid = str(b.get("belief_id", f"belief_{len(species)}"))
                label = str(b.get("label", bid))
                try:
                    niche = BeliefNiche(b.get("niche", "worldview"))
                except ValueError:
                    niche = BeliefNiche.WORLDVIEW
                population = max(0.0, min(self.MAX_POPULATION,
                                          float(b.get("population", 0.3))))
                fitness = max(0.0, min(1.0, float(b.get("fitness", 0.5))))
                mutation_rate = max(0.0, min(1.0, float(b.get("mutation_rate", 0.1))))
                carrying_cap = max(0.1, min(1.0, float(b.get("carrying_capacity", 0.7))))
                species[bid] = BeliefSpecies(
                    belief_id=bid,
                    label=label,
                    niche=niche,
                    population=population,
                    fitness=fitness,
                    mutation_rate=mutation_rate,
                    carrying_capacity=carrying_cap,
                )

            ecosystem = BeliefEcosystem(
                npc_id=npc_id,
                species=species,
                relationships=[],
            )
            # Compute initial relationships
            self._compute_relationships(ecosystem)
            self._ecosystems[npc_id] = ecosystem
            self._stats.total_ecosystems += 1
            self._stats.total_species += len(species)
            return self._ecosystem_to_dict(ecosystem)

    def get_ecosystem(self, npc_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            eco = self._ecosystems.get(npc_id)
            return self._ecosystem_to_dict(eco) if eco else None

    def list_ecosystems(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            results = [self._ecosystem_to_dict(e) for e in self._ecosystems.values()]
            results.sort(key=lambda e: e.get("created_at", 0), reverse=True)
            return results[:limit]

    def remove_ecosystem(self, npc_id: str) -> Dict[str, Any]:
        with self._lock:
            if npc_id not in self._ecosystems:
                return {"removed": False}
            species_count = len(self._ecosystems[npc_id].species)
            del self._ecosystems[npc_id]
            return {"removed": True, "npc_id": npc_id,
                    "cleared_species": species_count}

    # -------------------------------------------------------------------------
    # Belief Invasion (introducing new beliefs)
    # -------------------------------------------------------------------------

    def introduce_belief(self, npc_id: str, belief_id: str, label: str,
                         niche: str, initial_population: float = 0.2,
                         fitness: float = 0.5,
                         description: str = "") -> Dict[str, Any]:
        """Introduce a new belief species into an NPC's ecosystem (invasion)."""
        with self._lock:
            eco = self._ecosystems.get(npc_id)
            if eco is None:
                return {"error": f"Ecosystem not found: {npc_id}"}
            if belief_id in eco.species:
                return {"error": f"Belief already exists: {belief_id}"}
            try:
                niche_enum = BeliefNiche(niche)
            except ValueError:
                return {"error": f"Unknown niche: {niche}"}

            pop = max(0.0, min(self.MAX_POPULATION, float(initial_population)))
            fit = max(0.0, min(1.0, float(fitness)))

            # Check if the ecosystem can support this invasion
            # Higher biodiversity = harder to invade (niche saturation)
            same_niche_count = sum(1 for s in eco.species.values() if s.niche == niche_enum)
            invasion_resistance = min(0.8, same_niche_count * 0.2)
            effective_pop = pop * (1.0 - invasion_resistance)

            # Create the belief species
            species = BeliefSpecies(
                belief_id=belief_id,
                label=label,
                niche=niche_enum,
                population=effective_pop,
                fitness=fit,
                mutation_rate=round(random.uniform(0.05, 0.2), 3),
                carrying_capacity=0.7,
                is_native=False,
            )
            eco.species[belief_id] = species
            eco.invasion_count += 1
            self._stats.total_invasions += 1
            self._stats.total_species += 1

            # Recompute relationships
            self._compute_relationships(eco)

            # Determine outcome
            if effective_pop < self.EXTINCTION_THRESHOLD:
                outcome = InvasionOutcome.EXTINCT
                # Remove immediately
                del eco.species[belief_id]
                eco.extinction_count += 1
                self._stats.total_extinctions += 1
            elif effective_pop < 0.05:
                outcome = InvasionOutcome.REJECTED
            elif effective_pop < 0.15:
                outcome = InvasionOutcome.ESTABLISHED
            else:
                outcome = InvasionOutcome.FLOURISHED

            # Record invasion event
            event = InvasionEvent(
                event_id=f"inv_{npc_id}_{belief_id}_{int(time.time() * 1000)}",
                npc_id=npc_id,
                belief_id=belief_id,
                belief_label=label,
                niche=niche,
                initial_population=round(effective_pop, 4),
                outcome=outcome.value,
                timestamp=time.time(),
                description=description or f"Belief '{label}' introduced into {npc_id}'s ecosystem",
            )
            self._invasion_history.append(event)

            return {
                "event_id": event.event_id,
                "npc_id": npc_id,
                "belief_id": belief_id,
                "label": label,
                "niche": niche,
                "initial_population": round(effective_pop, 4),
                "invasion_resistance": round(invasion_resistance, 4),
                "outcome": outcome.value,
                "ecosystem": self._ecosystem_to_dict(eco),
            }

    # -------------------------------------------------------------------------
    # Phase Implementations
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """Run a single ecosystem evolution cycle.

        Phases: GERMINATE -> COMPETE -> ADAPT -> EVOLVE -> EQUILIBRATE
        """
        start_time = time.time()
        with self._lock:
            self._active = True

            # Phase 1: GERMINATE
            phase = EcosystemPhase.GERMINATE
            germinate_info = self._germinate_phase()

            # Phase 2: COMPETE
            phase = EcosystemPhase.COMPETE
            compete_info = self._compete_phase()

            # Phase 3: ADAPT
            phase = EcosystemPhase.ADAPT
            adapt_info = self._adapt_phase()

            # Phase 4: EVOLVE
            phase = EcosystemPhase.EVOLVE
            evolve_info = self._evolve_phase()

            # Phase 5: EQUILIBRATE
            phase = EcosystemPhase.EQUILIBRATE
            equilibrate_info = self._equilibrate_phase()

            self._cycle_count += 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._stats.last_cycle_time_ms = round(elapsed_ms, 2)
            self._stats.active = True
            self._update_avg_metrics()

            return {
                "phase": phase.value,
                "cycle": self._cycle_count,
                "germinate": germinate_info,
                "compete": compete_info,
                "adapt": adapt_info,
                "evolve": evolve_info,
                "equilibrate": equilibrate_info,
                "total_ecosystems": len(self._ecosystems),
                "total_species": sum(len(e.species) for e in self._ecosystems.values()),
                "cycle_time_ms": round(elapsed_ms, 2),
            }

    def _germinate_phase(self) -> Dict[str, Any]:
        """Phase 1: Belief populations naturally grow toward carrying capacity."""
        growth_count = 0
        for eco in self._ecosystems.values():
            for species in eco.species.values():
                if species.population < species.carrying_capacity:
                    # Growth is proportional to fitness and available capacity
                    available = species.carrying_capacity - species.population
                    growth = available * species.fitness * self.GROWTH_RATE
                    species.population = min(
                        species.carrying_capacity,
                        species.population + growth)
                    growth_count += 1
                species.generation += 1
        return {"species_grew": growth_count}

    def _compete_phase(self) -> Dict[str, Any]:
        """Phase 2: Beliefs in the same niche compete for resources."""
        competitions = 0
        for eco in self._ecosystems.values():
            # Group species by niche
            niche_groups: Dict[BeliefNiche, List[BeliefSpecies]] = {}
            for s in eco.species.values():
                niche_groups.setdefault(s.niche, []).append(s)

            for niche, group in niche_groups.items():
                if len(group) < 2:
                    continue
                # Total population in this niche
                total_pop = sum(s.population for s in group)
                carrying = max(s.carrying_capacity for s in group)
                if total_pop <= carrying:
                    continue  # No competition needed
                # Overpopulation: reduce all proportional to their share
                overflow = total_pop - carrying
                for s in group:
                    share = s.population / total_pop if total_pop > 0 else 0
                    reduction = overflow * share * (1.0 - s.fitness * 0.5)
                    s.population = max(0.0, s.population - reduction)
                    competitions += 1

        return {"competitions_resolved": competitions}

    def _adapt_phase(self) -> Dict[str, Any]:
        """Phase 3: Beliefs mutate and adapt to conditions."""
        mutations = 0
        for eco in self._ecosystems.values():
            for species in eco.species.values():
                # Mutation: fitness shifts
                if random.random() < species.mutation_rate * self.MUTATION_CHANCE:
                    mutation_delta = random.gauss(0, self.MUTATION_MAGNITUDE)
                    species.fitness = max(0.0, min(1.0, species.fitness + mutation_delta))
                    species.mutations += 1
                    self._stats.total_mutations += 1
                    mutations += 1
                    species.last_adapted_at = time.time()

                # Fitness affects population: unfit beliefs decline
                if species.fitness < 0.3:
                    decline = self.DECLINE_RATE * (0.3 - species.fitness) / 0.3
                    species.population = max(0.0, species.population - decline)

        return {"mutations_occurred": mutations}

    def _evolve_phase(self) -> Dict[str, Any]:
        """Phase 4: Ecological relationships shape populations."""
        symbiosis_count = 0
        predation_count = 0
        for eco in self._ecosystems.values():
            for rel in eco.relationships:
                species_a = eco.species.get(rel.belief_a)
                species_b = eco.species.get(rel.belief_b)
                if species_a is None or species_b is None:
                    continue

                effect_a = 0.0
                effect_b = 0.0

                if rel.relation == EcologicalRelation.SYMBIOSIS:
                    # Both benefit
                    benefit = rel.strength * 0.03 * min(species_a.fitness, species_b.fitness)
                    effect_a = benefit
                    effect_b = benefit
                    symbiosis_count += 1
                elif rel.relation == EcologicalRelation.PREDATION:
                    # A preys on B
                    predation = rel.strength * 0.05 * species_a.fitness
                    effect_a = predation  # A benefits
                    effect_b = -predation  # B suffers
                    predation_count += 1
                elif rel.relation == EcologicalRelation.PARASITISM:
                    # A benefits at B's expense (less than predation)
                    parasitism = rel.strength * 0.03 * species_a.fitness
                    effect_a = parasitism
                    effect_b = -parasitism * 0.5
                elif rel.relation == EcologicalRelation.COMPETITION:
                    # Both suffer slightly
                    competition = rel.strength * 0.02
                    effect_a = -competition
                    effect_b = -competition
                elif rel.relation == EcologicalRelation.COMMENSALISM:
                    # A benefits, B unaffected
                    effect_a = rel.strength * 0.02 * species_b.fitness

                species_a.population = max(0.0, min(self.MAX_POPULATION,
                    species_a.population + effect_a))
                species_b.population = max(0.0, min(self.MAX_POPULATION,
                    species_b.population + effect_b))
                rel.current_effect_a = round(effect_a, 5)
                rel.current_effect_b = round(effect_b, 5)

        self._stats.total_symbioses = symbiosis_count
        self._stats.total_predations = predation_count
        return {"symbiosis_interactions": symbiosis_count,
                "predation_interactions": predation_count}

    def _equilibrate_phase(self) -> Dict[str, Any]:
        """Phase 5: Remove extinct species, compute biodiversity and stability."""
        extinctions = 0
        for eco in self._ecosystems.values():
            # Remove extinct species
            extinct_ids = [bid for bid, s in eco.species.items()
                          if s.population < self.EXTINCTION_THRESHOLD]
            for bid in extinct_ids:
                del eco.species[bid]
                eco.extinction_count += 1
                self._stats.total_extinctions += 1
                extinctions += 1

            # Remove relationships involving extinct species
            eco.relationships = [r for r in eco.relationships
                                if r.belief_a in eco.species and r.belief_b in eco.species]

            # Compute biodiversity (Shannon diversity index, normalized)
            eco.biodiversity = self._compute_biodiversity(eco)
            # Compute stability (inverse of population volatility)
            eco.stability = self._compute_stability(eco)
            eco.cycle_count += 1

        return {"extinctions": extinctions}

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _generate_default_beliefs(self) -> List[Dict[str, Any]]:
        """Generate a default set of beliefs for a new ecosystem."""
        defaults = [
            {"belief_id": "self_worth", "label": "Sense of Self-Worth",
             "niche": "identity", "population": 0.5, "fitness": 0.6},
            {"belief_id": "trust_others", "label": "Trust in Others",
             "niche": "social", "population": 0.4, "fitness": 0.5},
            {"belief_id": "world_fair", "label": "The World is Fair",
             "niche": "worldview", "population": 0.3, "fitness": 0.4},
            {"belief_id": "survive_thrive", "label": "Will to Survive",
             "niche": "survival", "population": 0.7, "fitness": 0.8},
            {"belief_id": "do_right", "label": "Duty to Do Right",
             "niche": "morality", "population": 0.4, "fitness": 0.5},
        ]
        return defaults

    def _compute_relationships(self, eco: BeliefEcosystem) -> None:
        """Compute ecological relationships between all belief species."""
        eco.relationships = []
        species_list = list(eco.species.values())
        for a, b in combinations(species_list, 2):
            # Check niche interaction table
            key1 = (a.niche, b.niche)
            key2 = (b.niche, a.niche)
            if key1 in NICHE_INTERACTIONS:
                relation, strength = NICHE_INTERACTIONS[key1]
            elif key2 in NICHE_INTERACTIONS:
                relation, strength = NICHE_INTERACTIONS[key2]
            else:
                relation = EcologicalRelation.NEUTRAL
                strength = 0.0

            if relation != EcologicalRelation.NEUTRAL and strength > 0:
                eco.relationships.append(EcologicalRelationship(
                    belief_a=a.belief_id,
                    belief_b=b.belief_id,
                    relation=relation,
                    strength=strength,
                ))

    def _compute_biodiversity(self, eco: BeliefEcosystem) -> float:
        """Compute biodiversity using Shannon diversity index (normalized)."""
        if not eco.species:
            return 0.0
        total = sum(s.population for s in eco.species.values())
        if total <= 0:
            return 0.0
        shannon = 0.0
        for s in eco.species.values():
            p = s.population / total
            if p > 0:
                shannon -= p * (p and __import__('math').log(p))
        # Normalize by max possible (ln(n))
        max_div = __import__('math').log(len(eco.species)) if len(eco.species) > 1 else 1
        return round(min(1.0, shannon / max_div) if max_div > 0 else 0.0, 4)

    def _compute_stability(self, eco: BeliefEcosystem) -> float:
        """Compute ecosystem stability based on population distribution."""
        if not eco.species:
            return 0.0
        # Stability is high when populations are moderate (not extreme)
        deviations = []
        for s in eco.species.values():
            # Optimal population is around 0.3-0.5
            deviation = abs(s.population - 0.4)
            deviations.append(deviation)
        avg_deviation = sum(deviations) / len(deviations) if deviations else 1.0
        return round(max(0.0, min(1.0, 1.0 - avg_deviation * 2)), 4)

    def _update_avg_metrics(self) -> None:
        """Update average metrics across all ecosystems."""
        if not self._ecosystems:
            return
        total_bio = sum(e.biodiversity for e in self._ecosystems.values())
        total_stab = sum(e.stability for e in self._ecosystems.values())
        n = len(self._ecosystems)
        self._stats.avg_biodiversity = round(total_bio / n, 4)
        self._stats.avg_stability = round(total_stab / n, 4)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "total_ecosystems": len(self._ecosystems),
                "total_species": sum(len(e.species) for e in self._ecosystems.values()),
                "stats": self._stats_to_dict(),
            }

    def list_invasions(self, npc_id: Optional[str] = None,
                       limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            events = list(self._invasion_history)
            if npc_id:
                events = [e for e in events if e.npc_id == npc_id]
            events.sort(key=lambda e: e.timestamp, reverse=True)
            return [self._invasion_to_dict(e) for e in events[:limit]]

    def list_beliefs(self, npc_id: Optional[str] = None,
                     niche: Optional[str] = None,
                     limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            for eco in self._ecosystems.values():
                if npc_id and eco.npc_id != npc_id:
                    continue
                for s in eco.species.values():
                    if niche and s.niche.value != niche:
                        continue
                    results.append({
                        "npc_id": eco.npc_id,
                        "belief_id": s.belief_id,
                        "label": s.label,
                        "niche": s.niche.value,
                        "population": round(s.population, 4),
                        "fitness": round(s.fitness, 4),
                        "mutation_rate": round(s.mutation_rate, 4),
                        "carrying_capacity": round(s.carrying_capacity, 4),
                        "generation": s.generation,
                        "is_native": s.is_native,
                        "mutations": s.mutations,
                    })
            results.sort(key=lambda b: b.get("population", 0), reverse=True)
            return results[:limit]

    def list_relationships(self, npc_id: Optional[str] = None,
                           limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            for eco in self._ecosystems.values():
                if npc_id and eco.npc_id != npc_id:
                    continue
                for rel in eco.relationships:
                    results.append({
                        "npc_id": eco.npc_id,
                        "belief_a": rel.belief_a,
                        "belief_b": rel.belief_b,
                        "relation": rel.relation.value,
                        "strength": round(rel.strength, 4),
                        "current_effect_a": round(rel.current_effect_a, 5),
                        "current_effect_b": round(rel.current_effect_b, 5),
                    })
            return results[:limit]

    def simulate(self, cycles: int = 10) -> Dict[str, Any]:
        """Run multiple cycles and optionally seed random data."""
        with self._lock:
            # Seed sample ecosystems if empty
            if not self._ecosystems:
                archetypes = [
                    ("wise_elder", [
                        {"belief_id": "wisdom", "label": "Wisdom Matters Most",
                         "niche": "worldview", "population": 0.7, "fitness": 0.8},
                        {"belief_id": "patience", "label": "Patience is Virtue",
                         "niche": "morality", "population": 0.6, "fitness": 0.7},
                        {"belief_id": "tradition", "label": "Respect Tradition",
                         "niche": "spiritual", "population": 0.5, "fitness": 0.6},
                    ]),
                    ("young_rebel", [
                        {"belief_id": "change", "label": "Change is Needed",
                         "niche": "worldview", "population": 0.7, "fitness": 0.7},
                        {"belief_id": "authority_bad", "label": "Authority is Oppressive",
                         "niche": "political", "population": 0.6, "fitness": 0.6},
                        {"belief_id": "self_reliance", "label": "Self-Reliance",
                         "niche": "identity", "population": 0.5, "fitness": 0.7},
                    ]),
                    ("devoted_guard", [
                        {"belief_id": "duty", "label": "Duty Above All",
                         "niche": "morality", "population": 0.8, "fitness": 0.8},
                        {"belief_id": "loyalty", "label": "Loyalty to Lord",
                         "niche": "social", "population": 0.7, "fitness": 0.7},
                        {"belief_id": "order", "label": "Order is Safety",
                         "niche": "survival", "population": 0.6, "fitness": 0.6},
                    ]),
                ]
                for name, beliefs in archetypes:
                    self.create_ecosystem(f"sim_{name}", beliefs)

            # Run cycles with occasional invasions
            invasion_types = [
                ("new_idea", "Radical New Idea", "worldview", 0.15),
                ("doubt", "Seed of Doubt", "survival", 0.1),
                ("revelation", "Spiritual Revelation", "spiritual", 0.2),
                ("betrayal", "Trust Betrayed", "social", 0.15),
            ]
            for _ in range(cycles):
                # Occasionally introduce a new belief
                if self._ecosystems and random.random() < 0.4:
                    npc_id = random.choice(list(self._ecosystems.keys()))
                    inv = random.choice(invasion_types)
                    self.introduce_belief(npc_id, f"inv_{npc_id}_{int(time.time()*1000)}",
                                          inv[1], inv[2], inv[3])
                self.run_cycle()

            return {
                "cycles_run": cycles,
                "final_status": self.get_status(),
                "final_stats": self._stats_to_dict(),
            }

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            count = len(self._ecosystems)
            species_count = sum(len(e.species) for e in self._ecosystems.values())
            self._ecosystems.clear()
            self._invasion_history.clear()
            self._stats = EcosystemStats()
            self._cycle_count = 0
            self._active = False
            return {"reset": True, "cleared_ecosystems": count,
                    "cleared_species": species_count}

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def _ecosystem_to_dict(self, eco: BeliefEcosystem) -> Dict[str, Any]:
        return {
            "npc_id": eco.npc_id,
            "species": {
                bid: {
                    "belief_id": s.belief_id,
                    "label": s.label,
                    "niche": s.niche.value,
                    "population": round(s.population, 4),
                    "fitness": round(s.fitness, 4),
                    "mutation_rate": round(s.mutation_rate, 4),
                    "carrying_capacity": round(s.carrying_capacity, 4),
                    "generation": s.generation,
                    "is_native": s.is_native,
                    "mutations": s.mutations,
                    "introduced_at": s.introduced_at,
                    "last_adapted_at": s.last_adapted_at,
                }
                for bid, s in eco.species.items()
            },
            "relationships": [
                {
                    "belief_a": r.belief_a,
                    "belief_b": r.belief_b,
                    "relation": r.relation.value,
                    "strength": round(r.strength, 4),
                    "current_effect_a": round(r.current_effect_a, 5),
                    "current_effect_b": round(r.current_effect_b, 5),
                }
                for r in eco.relationships
            ],
            "biodiversity": round(eco.biodiversity, 4),
            "stability": round(eco.stability, 4),
            "cycle_count": eco.cycle_count,
            "invasion_count": eco.invasion_count,
            "extinction_count": eco.extinction_count,
            "created_at": eco.created_at,
        }

    def _invasion_to_dict(self, e: InvasionEvent) -> Dict[str, Any]:
        return {
            "event_id": e.event_id,
            "npc_id": e.npc_id,
            "belief_id": e.belief_id,
            "belief_label": e.belief_label,
            "niche": e.niche,
            "initial_population": round(e.initial_population, 4),
            "outcome": e.outcome,
            "timestamp": e.timestamp,
            "description": e.description,
        }

    def _stats_to_dict(self) -> Dict[str, Any]:
        return {
            "total_ecosystems": self._stats.total_ecosystems,
            "total_species": self._stats.total_species,
            "total_invasions": self._stats.total_invasions,
            "total_extinctions": self._stats.total_extinctions,
            "total_mutations": self._stats.total_mutations,
            "total_symbioses": self._stats.total_symbioses,
            "total_predations": self._stats.total_predations,
            "avg_biodiversity": self._stats.avg_biodiversity,
            "avg_stability": self._stats.avg_stability,
            "last_cycle_time_ms": self._stats.last_cycle_time_ms,
            "active": self._stats.active,
        }
