"""
SparkLabs Agent - Behavioral Genome System

A behavioral genome system for NPC personality traits and behavioral
inheritance. Models NPC behavior as a genome of quantitative traits that
can be registered, cross-bred to produce offspring, mutated to introduce
variation, and expressed into a phenotype used at runtime.

Architecture:
  BehavioralGenomeSystem (Singleton)
    |-- GenomeTrait (single heritable trait with dominance and mutation rate)
    |-- BehavioralGenome (collection of traits with lineage and fitness)
    |-- GenomeExpression (expressed phenotype derived from a genome)
    |-- BehavioralGenomeSnapshot (point-in-time state capture)

The system is intentionally deterministic in its breeding logic so that
population evolution is reproducible given the same parent genomes and
mutation seed. Trait values are normalized to the [0.0, 1.0] range.
"""

from __future__ import annotations

import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


_time = _time_module


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class GenomeTrait:
    """A single heritable behavioral trait.

    Attributes:
        trait_id: Auto-generated unique identifier for the trait.
        name: Human-readable trait name.
        value: Quantitative trait value normalized to [0.0, 1.0].
        dominance: Dominance weight in [0.0, 1.0]; higher values are
            more likely to be expressed over a recessive counterpart.
        mutation_rate: Probability in [0.0, 1.0] that the trait mutates
            during a breeding step.
        category: Free-form grouping label (e.g. "personality", "combat").
    """

    trait_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    value: float = 0.5
    dominance: float = 0.5
    mutation_rate: float = 0.05
    category: str = "general"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trait_id": self.trait_id,
            "name": self.name,
            "value": self.value,
            "dominance": self.dominance,
            "mutation_rate": self.mutation_rate,
            "category": self.category,
        }


@dataclass
class BehavioralGenome:
    """A behavioral genome composed of named traits with lineage.

    Attributes:
        genome_id: Auto-generated unique identifier for the genome.
        traits: Mapping of trait name to GenomeTrait.
        generation: Evolutionary generation index; 0 for registered seeds.
        parent_ids: IDs of the parent genomes used to breed this one.
        fitness_score: Latest fitness evaluation in [0.0, 1.0].
    """

    genome_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    traits: Dict[str, GenomeTrait] = field(default_factory=dict)
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    fitness_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "genome_id": self.genome_id,
            "traits": {name: t.to_dict() for name, t in self.traits.items()},
            "generation": self.generation,
            "parent_ids": list(self.parent_ids),
            "fitness_score": self.fitness_score,
        }


@dataclass
class GenomeExpression:
    """The expressed phenotype derived from a behavioral genome.

    Attributes:
        expressed_traits: Trait name to expressed value in [0.0, 1.0].
        hidden_traits: Trait name to value for traits that remain hidden.
        phenotype: Human-readable summary label of the expressed profile.
    """

    expressed_traits: Dict[str, float] = field(default_factory=dict)
    hidden_traits: Dict[str, float] = field(default_factory=dict)
    phenotype: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expressed_traits": dict(self.expressed_traits),
            "hidden_traits": dict(self.hidden_traits),
            "phenotype": self.phenotype,
        }


@dataclass
class BehavioralGenomeSnapshot:
    """Point-in-time capture of the behavioral genome system state.

    Attributes:
        snapshot_id: Auto-generated unique identifier for the snapshot.
        captured_at: POSIX timestamp of capture.
        genome_count: Number of genomes in the pool.
        generation: Highest generation index observed in the pool.
        genomes: Serialized list of all genomes at capture time.
        system_status: Aggregate status dictionary at capture time.
    """

    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    captured_at: float = field(default_factory=_time.time)
    genome_count: int = 0
    generation: int = 0
    genomes: List[Dict[str, Any]] = field(default_factory=list)
    system_status: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "genome_count": self.genome_count,
            "generation": self.generation,
            "genomes": self.genomes,
            "system_status": self.system_status,
        }


# =============================================================================
# BehavioralGenomeSystem (Singleton)
# =============================================================================


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a float to the [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


class BehavioralGenomeSystem:
    """Behavioral genome system managing a pool of breedable genomes.

    Provides trait registration, cross-breeding with dominance-based
    inheritance, mutation, phenotypic expression, and generation-based
    evolution. The system is thread-safe and intended to be accessed
    through the module-level :func:`get_behavioral_genome_system`
    factory.

    Usage:
        system = get_behavioral_genome_system()
        parent_a = system.register_genome(BehavioralGenome(
            traits={"aggression": GenomeTrait(name="aggression", value=0.8)}))
        parent_b = system.register_genome(BehavioralGenome(
            traits={"aggression": GenomeTrait(name="aggression", value=0.2)}))
        child = system.cross_breed(parent_a.genome_id, parent_b.genome_id)
        expression = system.express(child.genome_id)
    """

    _instance: Optional["BehavioralGenomeSystem"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_GENOMES: int = 5000

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._genomes: Dict[str, BehavioralGenome] = {}
        self._current_generation: int = 0
        self._stats: Dict[str, Any] = {
            "total_registered": 0,
            "total_bred": 0,
            "total_mutations": 0,
            "total_expressions": 0,
            "evolutions_run": 0,
        }
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "BehavioralGenomeSystem":
        """Return the singleton BehavioralGenomeSystem instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Genome Registration
    # ------------------------------------------------------------------

    def register_genome(self, genome: BehavioralGenome) -> BehavioralGenome:
        """Register a seed genome in the pool.

        Assigns a fresh genome_id if the supplied genome has none, clamps
        trait values, and stores the genome for breeding. Registered
        genomes are treated as generation 0 unless their generation field
        is already set.

        Args:
            genome: The BehavioralGenome to register.

        Returns:
            The registered BehavioralGenome (with normalized trait values).
        """
        with self._instance_lock:
            self._enforce_max_genomes()
            if not genome.genome_id:
                genome.genome_id = uuid.uuid4().hex
            for trait in genome.traits.values():
                trait.value = _clamp(trait.value)
                trait.dominance = _clamp(trait.dominance)
                trait.mutation_rate = _clamp(trait.mutation_rate)
            if genome.generation == 0:
                genome.generation = 0
            self._genomes[genome.genome_id] = genome
            self._stats["total_registered"] += 1
            return genome

    # ------------------------------------------------------------------
    # Breeding & Mutation
    # ------------------------------------------------------------------

    def cross_breed(
        self, genome_a_id: str, genome_b_id: str
    ) -> Optional[BehavioralGenome]:
        """Cross-breed two genomes to produce an offspring genome.

        For each trait present in either parent, the offspring inherits a
        value blended from both parents, weighted by dominance. Traits
        present in only one parent are inherited directly (with mutation).
        The offspring's generation is one greater than the max parent
        generation, and its parent_ids record both parents.

        Args:
            genome_a_id: ID of the first parent genome.
            genome_b_id: ID of the second parent genome.

        Returns:
            The newly created offspring BehavioralGenome, or None if
            either parent is not found.
        """
        with self._instance_lock:
            parent_a = self._genomes.get(genome_a_id)
            parent_b = self._genomes.get(genome_b_id)
            if parent_a is None or parent_b is None:
                return None

            self._enforce_max_genomes()
            child_traits: Dict[str, GenomeTrait] = {}
            all_trait_names = set(parent_a.traits) | set(parent_b.traits)
            for name in all_trait_names:
                trait_a = parent_a.traits.get(name)
                trait_b = parent_b.traits.get(name)
                if trait_a is not None and trait_b is not None:
                    dom_total = trait_a.dominance + trait_b.dominance
                    if dom_total <= 0:
                        weight_a = 0.5
                    else:
                        weight_a = trait_a.dominance / dom_total
                    blended_value = (
                        trait_a.value * weight_a + trait_b.value * (1.0 - weight_a)
                    )
                    child_traits[name] = GenomeTrait(
                        name=name,
                        value=_clamp(blended_value),
                        dominance=(trait_a.dominance + trait_b.dominance) / 2.0,
                        mutation_rate=(trait_a.mutation_rate + trait_b.mutation_rate) / 2.0,
                        category=trait_a.category,
                    )
                else:
                    source = trait_a if trait_a is not None else trait_b
                    assert source is not None  # for type checkers
                    child_traits[name] = GenomeTrait(
                        name=source.name,
                        value=_clamp(source.value),
                        dominance=source.dominance,
                        mutation_rate=source.mutation_rate,
                        category=source.category,
                    )

            child = BehavioralGenome(
                traits=child_traits,
                generation=max(parent_a.generation, parent_b.generation) + 1,
                parent_ids=[parent_a.genome_id, parent_b.genome_id],
                fitness_score=0.0,
            )
            self._genomes[child.genome_id] = child
            if child.generation > self._current_generation:
                self._current_generation = child.generation
            self._stats["total_bred"] += 1
            return child

    def mutate(
        self, genome_id: str, rate: float = 0.1
    ) -> Optional[BehavioralGenome]:
        """Apply random mutations to a genome's traits.

        Each trait mutates with probability proportional to the trait's
        own mutation_rate scaled by the supplied ``rate``. Mutated values
        are perturbed by a random delta and clamped to [0.0, 1.0]. The
        mutation is applied in-place to the stored genome.

        Args:
            genome_id: ID of the genome to mutate.
            rate: Global mutation rate multiplier in [0.0, 1.0].

        Returns:
            The mutated BehavioralGenome, or None if not found.
        """
        with self._instance_lock:
            genome = self._genomes.get(genome_id)
            if genome is None:
                return None
            mutations_applied = 0
            for trait in genome.traits.values():
                if random.random() < trait.mutation_rate * rate:
                    delta = random.uniform(-0.15, 0.15)
                    trait.value = _clamp(trait.value + delta)
                    mutations_applied += 1
            self._stats["total_mutations"] += mutations_applied
            return genome

    # ------------------------------------------------------------------
    # Expression
    # ------------------------------------------------------------------

    def express(self, genome_id: str) -> Optional[GenomeExpression]:
        """Express a genome into its observable phenotype.

        A trait is considered expressed if its value exceeds 0.5;
        otherwise it is recorded as hidden. The phenotype is a short
        human-readable summary built from the dominant expressed traits.

        Args:
            genome_id: ID of the genome to express.

        Returns:
            A GenomeExpression describing expressed and hidden traits,
            or None if the genome is not found.
        """
        with self._instance_lock:
            genome = self._genomes.get(genome_id)
            if genome is None:
                return None
            expressed: Dict[str, float] = {}
            hidden: Dict[str, float] = {}
            for name, trait in genome.traits.items():
                if trait.value >= 0.5:
                    expressed[name] = trait.value
                else:
                    hidden[name] = trait.value
            # Build a phenotype label from the top expressed traits.
            top_traits = sorted(
                expressed.items(), key=lambda kv: kv[1], reverse=True
            )[:3]
            phenotype = ", ".join(
                f"{name}={value:.2f}" for name, value in top_traits
            )
            expression = GenomeExpression(
                expressed_traits=expressed,
                hidden_traits=hidden,
                phenotype=phenotype or "neutral",
            )
            self._stats["total_expressions"] += 1
            return expression

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_genome(self, genome_id: str) -> Optional[BehavioralGenome]:
        """Retrieve a genome by ID."""
        with self._instance_lock:
            return self._genomes.get(genome_id)

    def get_all_genomes(self) -> List[BehavioralGenome]:
        """Return a list of all genomes in the pool."""
        with self._instance_lock:
            return list(self._genomes.values())

    # ------------------------------------------------------------------
    # Evolution
    # ------------------------------------------------------------------

    def evolve_generation(self) -> int:
        """Advance the population by one evolutionary generation.

        Pairs the fittest genomes with random partners, breeds them, and
        applies a light mutation pass to the offspring. Genomes with no
        recorded fitness are treated as having fitness 0.5. The current
        generation counter is incremented and returned.

        Returns:
            The new current generation index.
        """
        with self._instance_lock:
            genomes = list(self._genomes.values())
            if len(genomes) < 2:
                self._current_generation += 1
                self._stats["evolutions_run"] += 1
                return self._current_generation

            # Sort by fitness descending; missing fitness treated as 0.5.
            genomes.sort(
                key=lambda g: g.fitness_score if g.fitness_score > 0 else 0.5,
                reverse=True,
            )
            # Breed the top half with a shuffled partner from the pool.
            top_half = genomes[: max(2, len(genomes) // 2)]
            partners = list(genomes)
            random.shuffle(partners)
            for i, parent_a in enumerate(top_half):
                parent_b = partners[i % len(partners)]
                if parent_b.genome_id == parent_a.genome_id:
                    continue
                child = self.cross_breed(parent_a.genome_id, parent_b.genome_id)
                if child is not None:
                    self.mutate(child.genome_id, rate=0.5)

            self._current_generation += 1
            self._stats["evolutions_run"] += 1
            return self._current_generation

    # ------------------------------------------------------------------
    # Status & Snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return aggregate status of the genome system."""
        with self._instance_lock:
            trait_count = sum(len(g.traits) for g in self._genomes.values())
            max_generation = max(
                (g.generation for g in self._genomes.values()), default=0
            )
            return {
                "genome_count": len(self._genomes),
                "trait_count": trait_count,
                "current_generation": self._current_generation,
                "max_generation": max_generation,
                "stats": dict(self._stats),
            }

    def get_snapshot(self) -> BehavioralGenomeSnapshot:
        """Capture a point-in-time snapshot of the system state."""
        with self._instance_lock:
            status = self.get_status()
            return BehavioralGenomeSnapshot(
                captured_at=_time.time(),
                genome_count=len(self._genomes),
                generation=self._current_generation,
                genomes=[g.to_dict() for g in self._genomes.values()],
                system_status=status,
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all genomes and reset statistics."""
        with self._instance_lock:
            self._genomes.clear()
            self._current_generation = 0
            self._stats = {
                "total_registered": 0,
                "total_bred": 0,
                "total_mutations": 0,
                "total_expressions": 0,
                "evolutions_run": 0,
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enforce_max_genomes(self) -> None:
        """Evict the oldest genomes when the pool exceeds the cap."""
        if len(self._genomes) <= self._MAX_GENOMES:
            return
        # Evict lowest-fitness genomes first to preserve quality.
        sorted_ids = sorted(
            self._genomes.keys(),
            key=lambda gid: self._genomes[gid].fitness_score,
        )
        excess = len(self._genomes) - self._MAX_GENOMES
        for gid in sorted_ids[:excess]:
            self._genomes.pop(gid, None)


# =============================================================================
# Module-level factory
# =============================================================================


def get_behavioral_genome_system() -> BehavioralGenomeSystem:
    """Return the singleton BehavioralGenomeSystem instance."""
    return BehavioralGenomeSystem.get_instance()
