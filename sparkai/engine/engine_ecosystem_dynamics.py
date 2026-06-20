"""
SparkLabs Engine - Ecosystem Dynamics Simulation System

A population dynamics simulation engine modeling flora and fauna
interactions including predator-prey relationships, carrying capacity,
species migration, and seasonal effects. Uses a Lotka-Volterra inspired
model with logistic growth for producers, functional response predation
for consumers, and seasonal modifiers on growth and carrying capacity.

Architecture:
  EcosystemDynamicsEngine (Singleton)
    |-- SpeciesProfile      — definition of a species and its traits
    |-- PopulationSnapshot  — per-tick population state record
    |-- RegionEcosystem     — a geographic region with species populations
    |-- MigrationEvent      — recorded migration between regions
    |-- EcosystemReport     — summary metrics for a simulation tick

Ecological Model:
  - Producers: logistic growth toward carrying capacity (season-modified)
  - Primary consumers: Holling Type II functional response on producers
  - Secondary/Tertiary consumers: Lotka-Volterra predation on lower trophic levels
  - Decomposers: growth proportional to dead biomass (mortality)
  - Migration: triggered by overpopulation, resource scarcity, or season
  - Seasonal effects: growth rate and carrying capacity modifiers per season
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SpeciesType(str, Enum):
    """Trophic classification of a species in the food web."""
    PRODUCER = "producer"
    PRIMARY_CONSUMER = "primary_consumer"
    SECONDARY_CONSUMER = "secondary_consumer"
    TERTIARY_CONSUMER = "tertiary_consumer"
    DECOMPOSER = "decomposer"


class PopulationStatus(str, Enum):
    """Health classification for a species population."""
    THRIVING = "thriving"
    STABLE = "stable"
    DECLINING = "declining"
    ENDANGERED = "endangered"
    EXTINCT = "extinct"
    OVERPOPULATED = "overpopulated"


class MigrationTrigger(str, Enum):
    """Cause of a migration event."""
    SEASONAL = "seasonal"
    RESOURCE_SCARCITY = "resource_scarcity"
    PREDATION_PRESSURE = "predation_pressure"
    CLIMATE_CHANGE = "climate_change"
    OVERPOPULATION = "overpopulation"


class SeasonType(str, Enum):
    """Season affecting growth rates and carrying capacity."""
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


# ---------------------------------------------------------------------------
# Seasonal Modifiers
# ---------------------------------------------------------------------------

_SEASON_MODIFIERS: Dict[SeasonType, Dict[str, float]] = {
    SeasonType.SPRING: {"growth": 1.3, "carrying_capacity": 1.1, "mortality": 0.8},
    SeasonType.SUMMER: {"growth": 1.2, "carrying_capacity": 1.2, "mortality": 0.7},
    SeasonType.AUTUMN: {"growth": 0.8, "carrying_capacity": 0.9, "mortality": 1.1},
    SeasonType.WINTER: {"growth": 0.4, "carrying_capacity": 0.6, "mortality": 1.6},
}


# Trophic-level body mass proxy for biomass estimation
_TROPHIC_BODY_MASS: Dict[SpeciesType, float] = {
    SpeciesType.PRODUCER: 1.0,
    SpeciesType.PRIMARY_CONSUMER: 10.0,
    SpeciesType.SECONDARY_CONSUMER: 50.0,
    SpeciesType.TERTIARY_CONSUMER: 200.0,
    SpeciesType.DECOMPOSER: 0.5,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SpeciesProfile:
    """Definition of a species and its ecological traits.

    Captures growth parameters, trophic relationships (predator and prey
    links), biome preferences, and migration tendencies. Used as the
    template from which populations are simulated.
    """

    species_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    species_type: SpeciesType = SpeciesType.PRODUCER
    base_growth_rate: float = 0.1
    carrying_capacity: float = 1000.0
    metabolic_rate: float = 1.0
    reproduction_age: float = 1.0
    lifespan: float = 10.0
    preferred_biomes: List[str] = field(default_factory=list)
    predator_ids: List[str] = field(default_factory=list)
    prey_ids: List[str] = field(default_factory=list)
    migration_pattern: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "species_id": self.species_id,
            "name": self.name,
            "species_type": self.species_type.value,
            "base_growth_rate": self.base_growth_rate,
            "carrying_capacity": self.carrying_capacity,
            "metabolic_rate": self.metabolic_rate,
            "reproduction_age": self.reproduction_age,
            "lifespan": self.lifespan,
            "preferred_biomes": list(self.preferred_biomes),
            "predator_ids": list(self.predator_ids),
            "prey_ids": list(self.prey_ids),
            "migration_pattern": dict(self.migration_pattern),
        }


@dataclass
class PopulationSnapshot:
    """Per-tick record of a species population in a region.

    Tracks population count along with birth, death, and migration rates
    and the computed status for the tick.
    """

    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    species_id: str = ""
    region_id: str = ""
    population_count: float = 0.0
    birth_rate: float = 0.0
    death_rate: float = 0.0
    migration_rate: float = 0.0
    status: PopulationStatus = PopulationStatus.STABLE
    tick: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "species_id": self.species_id,
            "region_id": self.region_id,
            "population_count": round(self.population_count, 4),
            "birth_rate": round(self.birth_rate, 6),
            "death_rate": round(self.death_rate, 6),
            "migration_rate": round(self.migration_rate, 6),
            "status": self.status.value,
            "tick": self.tick,
            "timestamp": self.timestamp,
        }


@dataclass
class RegionEcosystem:
    """A geographic region hosting species populations.

    Holds the current population of each species, per-species carrying
    capacities, climate data, and the current simulation tick and season.
    """

    region_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    biome_type: str = ""
    area: float = 100.0
    climate_data: Dict[str, Any] = field(default_factory=dict)
    species_populations: Dict[str, float] = field(default_factory=dict)
    carrying_capacities: Dict[str, float] = field(default_factory=dict)
    tick: int = 0
    season: SeasonType = SeasonType.SPRING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "name": self.name,
            "biome_type": self.biome_type,
            "area": self.area,
            "climate_data": dict(self.climate_data),
            "species_populations": {k: round(v, 4) for k, v in self.species_populations.items()},
            "carrying_capacities": {k: round(v, 4) for k, v in self.carrying_capacities.items()},
            "tick": self.tick,
            "season": self.season.value,
        }


@dataclass
class MigrationEvent:
    """A recorded migration of individuals between two regions.

    Captures the species, source and target regions, the number of
    individuals moved, and the trigger that caused the migration.
    """

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    species_id: str = ""
    source_region: str = ""
    target_region: str = ""
    count: float = 0.0
    trigger: MigrationTrigger = MigrationTrigger.SEASONAL
    tick: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "species_id": self.species_id,
            "source_region": self.source_region,
            "target_region": self.target_region,
            "count": round(self.count, 4),
            "trigger": self.trigger.value,
            "tick": self.tick,
            "timestamp": self.timestamp,
        }


@dataclass
class EcosystemReport:
    """Summary metrics for a region after a simulation tick.

    Aggregates biodiversity, stability, biomass, food-web health, and
    lists of keystone and threatened species along with recommendations.
    """

    report_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    region_id: str = ""
    tick: int = 0
    biodiversity_index: float = 0.0
    stability_score: float = 0.0
    total_biomass: float = 0.0
    species_count: int = 0
    food_web_health: float = 0.0
    keystone_species: List[str] = field(default_factory=list)
    threatened_species: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "region_id": self.region_id,
            "tick": self.tick,
            "biodiversity_index": round(self.biodiversity_index, 6),
            "stability_score": round(self.stability_score, 6),
            "total_biomass": round(self.total_biomass, 4),
            "species_count": self.species_count,
            "food_web_health": round(self.food_web_health, 6),
            "keystone_species": list(self.keystone_species),
            "threatened_species": list(self.threatened_species),
            "recommendations": list(self.recommendations),
        }


# ---------------------------------------------------------------------------
# Ecosystem Dynamics Engine
# ---------------------------------------------------------------------------

class EcosystemDynamicsEngine:
    """Population dynamics simulation engine using a Lotka-Volterra inspired model.

    Models flora and fauna population dynamics including predator-prey
    relationships, carrying capacity, species migration, and seasonal
    effects. Producers grow logistically toward a carrying capacity,
    consumers grow based on prey availability via a Holling Type II
    functional response, and predators decline without prey.

    The engine is thread-safe and uses a singleton pattern. Each region
    maintains independent populations that interact through the food web
    defined by species predator and prey links.

    Usage:
        engine = get_ecosystem_dynamics()
        grass = engine.register_species("Grass", SpeciesType.PRODUCER, ...)
        rabbit = engine.register_species("Rabbit", SpeciesType.PRIMARY_CONSUMER, ...)
        region = engine.create_region("Meadow", "grassland", 1000.0, {})
        engine.introduce_species(region.region_id, grass.species_id, 500)
        engine.introduce_species(region.region_id, rabbit.species_id, 50)
        report = engine.simulate_tick(region.region_id, SeasonType.SPRING)
    """

    _instance: Optional["EcosystemDynamicsEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # Simulation constants
    EPSILON: float = 1e-9
    TIME_STEP: float = 0.1
    PREDATION_RATE: float = 0.01
    CONVERSION_EFFICIENCY: float = 0.1
    HANDLING_TIME: float = 0.02
    MIGRATION_THRESHOLD: float = 1.2
    MIGRATION_FRACTION: float = 0.15
    EXTINCTION_THRESHOLD: float = 0.5
    ENDANGERED_THRESHOLD: float = 0.1
    DECLINING_THRESHOLD: float = 0.5
    THRIVING_THRESHOLD: float = 0.7

    def __new__(cls) -> "EcosystemDynamicsEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EcosystemDynamicsEngine":
        """Return the singleton EcosystemDynamicsEngine instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        time.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._species: Dict[str, SpeciesProfile] = {}
            self._regions: Dict[str, RegionEcosystem] = {}
            self._population_history: Dict[str, List[PopulationSnapshot]] = {}
            self._migration_events: List[MigrationEvent] = []
            self._reports: Dict[str, List[EcosystemReport]] = {}

            self._total_species_registered: int = 0
            self._total_regions_created: int = 0
            self._total_introductions: int = 0
            self._total_ticks_simulated: int = 0
            self._total_migrations: int = 0
            self._total_extinctions: int = 0
            self._initialized = True

    # ------------------------------------------------------------------
    # Species Management
    # ------------------------------------------------------------------

    def register_species(
        self,
        name: str,
        species_type: SpeciesType,
        base_growth_rate: float,
        carrying_capacity: float,
        metabolic_rate: float,
        reproduction_age: float,
        lifespan: float,
        preferred_biomes: List[str],
        predator_ids: List[str],
        prey_ids: List[str],
    ) -> SpeciesProfile:
        """Register a new species with its ecological traits.

        Args:
            name: Display name of the species.
            species_type: Trophic classification.
            base_growth_rate: Intrinsic per-capita growth rate.
            carrying_capacity: Default carrying capacity for the species.
            metabolic_rate: Energy expenditure per individual.
            reproduction_age: Age at which the species can reproduce.
            lifespan: Average lifespan of an individual.
            preferred_biomes: Biomes where the species thrives.
            predator_ids: Species IDs that prey on this species.
            prey_ids: Species IDs that this species preys on.

        Returns:
            The newly created SpeciesProfile.
        """
        time.sleep(0.001)
        with self._lock:
            profile = SpeciesProfile(
                species_id=uuid.uuid4().hex,
                name=name,
                species_type=species_type,
                base_growth_rate=base_growth_rate,
                carrying_capacity=carrying_capacity,
                metabolic_rate=metabolic_rate,
                reproduction_age=reproduction_age,
                lifespan=lifespan,
                preferred_biomes=list(preferred_biomes),
                predator_ids=list(predator_ids),
                prey_ids=list(prey_ids),
                migration_pattern={},
            )
            self._species[profile.species_id] = profile
            self._total_species_registered += 1
            return profile

    def get_species(self, species_id: str) -> Optional[SpeciesProfile]:
        """Retrieve a species profile by ID."""
        with self._lock:
            return self._species.get(species_id)

    # ------------------------------------------------------------------
    # Region Management
    # ------------------------------------------------------------------

    def create_region(
        self,
        name: str,
        biome_type: str,
        area: float,
        climate_data: Dict[str, Any],
    ) -> RegionEcosystem:
        """Create a new geographic region for ecosystem simulation.

        Args:
            name: Region display name.
            biome_type: Biome classification (e.g. "grassland", "forest").
            area: Area of the region in square units.
            climate_data: Climate parameters (temperature, rainfall, etc.).

        Returns:
            The newly created RegionEcosystem.
        """
        time.sleep(0.001)
        with self._lock:
            region = RegionEcosystem(
                region_id=uuid.uuid4().hex,
                name=name,
                biome_type=biome_type,
                area=area,
                climate_data=dict(climate_data),
                season=SeasonType.SPRING,
            )
            self._regions[region.region_id] = region
            self._population_history[region.region_id] = []
            self._reports[region.region_id] = []
            self._total_regions_created += 1
            return region

    def get_region_state(self, region_id: str) -> Optional[RegionEcosystem]:
        """Retrieve the current state of a region by ID.

        Args:
            region_id: The ID of the region to retrieve.

        Returns:
            The RegionEcosystem, or None if not found.
        """
        with self._lock:
            return self._regions.get(region_id)

    # ------------------------------------------------------------------
    # Population Introduction
    # ------------------------------------------------------------------

    def introduce_species(
        self,
        region_id: str,
        species_id: str,
        initial_population: float,
    ) -> Optional[PopulationSnapshot]:
        """Introduce a species into a region with an initial population.

        Args:
            region_id: Target region ID.
            species_id: Species to introduce.
            initial_population: Starting population count.

        Returns:
            A PopulationSnapshot of the introduction, or None if the
            region or species was not found.
        """
        time.sleep(0.001)
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                return None
            profile = self._species.get(species_id)
            if profile is None:
                return None

            region.species_populations[species_id] = float(initial_population)

            # Set carrying capacity: scale by area and biome preference
            base_capacity = profile.carrying_capacity
            if region.biome_type in profile.preferred_biomes:
                base_capacity *= 1.5
            area_factor = max(0.1, region.area / 100.0)
            region.carrying_capacities[species_id] = base_capacity * area_factor

            snapshot = PopulationSnapshot(
                species_id=species_id,
                region_id=region_id,
                population_count=float(initial_population),
                birth_rate=0.0,
                death_rate=0.0,
                migration_rate=0.0,
                status=self._compute_status(
                    float(initial_population),
                    region.carrying_capacities[species_id],
                    0.0,
                    0.0,
                ),
                tick=region.tick,
            )
            self._population_history[region_id].append(snapshot)
            self._total_introductions += 1
            return snapshot

    # ------------------------------------------------------------------
    # Simulation Core
    # ------------------------------------------------------------------

    def simulate_tick(
        self,
        region_id: str,
        season: SeasonType,
    ) -> Optional[EcosystemReport]:
        """Advance a region's ecosystem by one simulation tick.

        Applies a Lotka-Volterra inspired model:
          1. Compute seasonal modifiers on growth and carrying capacity.
          2. Producers grow logistically toward carrying capacity.
          3. Consumers grow based on prey availability (Holling Type II).
          4. Predators decline without prey, grow with prey.
          5. Decomposers grow proportional to total mortality.
          6. Migration is triggered by overpopulation or scarcity.
          7. Population status and snapshots are recorded.
          8. Biodiversity and stability metrics are computed.

        Args:
            region_id: The region to simulate.
            season: The season to apply for this tick.

        Returns:
            An EcosystemReport for the tick, or None if region not found.
        """
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                return None

            region.season = season
            modifiers = _SEASON_MODIFIERS.get(
                season, _SEASON_MODIFIERS[SeasonType.SPRING]
            )
            growth_mod = modifiers["growth"]
            capacity_mod = modifiers["carrying_capacity"]
            mortality_mod = modifiers["mortality"]

            dt = self.TIME_STEP
            current_pops = dict(region.species_populations)
            new_pops: Dict[str, float] = {}
            snapshots: List[PopulationSnapshot] = []

            for species_id, population in current_pops.items():
                profile = self._species.get(species_id)
                if profile is None:
                    new_pops[species_id] = population
                    continue

                carrying_capacity = region.carrying_capacities.get(
                    species_id, profile.carrying_capacity
                ) * capacity_mod

                birth_rate = 0.0
                death_rate = 0.0
                migration_rate = 0.0

                if profile.species_type == SpeciesType.PRODUCER:
                    # Logistic growth: dN/dt = r * N * (1 - N/K)
                    r = profile.base_growth_rate * growth_mod
                    growth = r * population * (
                        1.0 - population / max(carrying_capacity, self.EPSILON)
                    )
                    birth_rate = max(0.0, growth) / max(population, self.EPSILON)
                    # Natural mortality scaled by lifespan and season
                    natural_death = (
                        population / max(profile.lifespan, self.EPSILON)
                    ) * mortality_mod
                    death_rate = natural_death / max(population, self.EPSILON)
                    delta = growth - natural_death

                elif profile.species_type in (
                    SpeciesType.PRIMARY_CONSUMER,
                    SpeciesType.SECONDARY_CONSUMER,
                    SpeciesType.TERTIARY_CONSUMER,
                ):
                    # Lotka-Volterra with Holling Type II functional response
                    total_prey = sum(
                        current_pops.get(pid, 0.0) for pid in profile.prey_ids
                    )

                    # Holling Type II: consumption = a * N_prey / (1 + a * h * N_prey)
                    a = self.PREDATION_RATE
                    h = self.HANDLING_TIME
                    if total_prey > self.EPSILON:
                        functional_response = (
                            a * total_prey / (1.0 + a * h * total_prey)
                        )
                    else:
                        functional_response = 0.0

                    # Births from consumption
                    births = (
                        self.CONVERSION_EFFICIENCY * functional_response * population
                    )
                    birth_rate = births / max(population, self.EPSILON)

                    # Starvation mortality
                    starvation = (
                        population / max(profile.lifespan, self.EPSILON)
                    ) * mortality_mod
                    # Increase starvation when prey is scarce
                    if total_prey < population * 0.5:
                        starvation *= 2.0

                    # Predation loss from this species' predators
                    predation_loss = 0.0
                    for predator_id in profile.predator_ids:
                        predator_pop = current_pops.get(predator_id, 0.0)
                        predator_profile = self._species.get(predator_id)
                        if predator_profile is None:
                            continue
                        # Total prey available to this predator
                        predator_prey_total = sum(
                            current_pops.get(pid, 0.0)
                            for pid in predator_profile.prey_ids
                        )
                        if predator_prey_total <= self.EPSILON:
                            continue
                        share = population / predator_prey_total
                        pred_a = self.PREDATION_RATE
                        pred_h = self.HANDLING_TIME
                        pred_fr = (
                            pred_a * predator_prey_total
                            / (1.0 + pred_a * pred_h * predator_prey_total)
                        )
                        predation_loss += share * pred_fr * predator_pop

                    death_rate = (
                        starvation + predation_loss
                    ) / max(population, self.EPSILON)
                    delta = births - starvation - predation_loss

                elif profile.species_type == SpeciesType.DECOMPOSER:
                    # Decomposers grow proportional to dead biomass
                    dead_biomass = 0.0
                    for sid, pop in current_pops.items():
                        sp = self._species.get(sid)
                        trophic = sp.species_type if sp else SpeciesType.PRODUCER
                        body_mass = _TROPHIC_BODY_MASS.get(trophic, 1.0)
                        dead_biomass += pop * body_mass * 0.01

                    r = profile.base_growth_rate * growth_mod
                    growth = r * population * (
                        dead_biomass / max(dead_biomass + population, self.EPSILON)
                    )
                    birth_rate = max(0.0, growth) / max(population, self.EPSILON)
                    natural_death = (
                        population / max(profile.lifespan, self.EPSILON)
                    ) * mortality_mod
                    death_rate = natural_death / max(population, self.EPSILON)
                    delta = growth - natural_death

                else:
                    delta = 0.0

                # Apply delta with time step
                new_pop = population + delta * dt

                # Migration logic
                carrying_base = region.carrying_capacities.get(
                    species_id, profile.carrying_capacity
                )
                if new_pop > carrying_base * self.MIGRATION_THRESHOLD:
                    # Overpopulation migration
                    migrants = new_pop * self.MIGRATION_FRACTION
                    new_pop -= migrants
                    migration_rate = migrants / max(population, self.EPSILON)
                elif (
                    profile.species_type != SpeciesType.PRODUCER
                    and new_pop > self.EPSILON
                ):
                    # Resource scarcity migration for consumers
                    total_prey = sum(
                        current_pops.get(pid, 0.0) for pid in profile.prey_ids
                    )
                    if total_prey < new_pop * 0.3:
                        migrants = new_pop * 0.1
                        new_pop -= migrants
                        migration_rate = migrants / max(population, self.EPSILON)

                # Extinction threshold
                if new_pop < self.EXTINCTION_THRESHOLD:
                    if population >= self.EXTINCTION_THRESHOLD:
                        self._total_extinctions += 1
                    new_pop = 0.0
                    status = PopulationStatus.EXTINCT
                else:
                    status = self._compute_status(
                        new_pop, carrying_base, birth_rate, death_rate
                    )

                new_pops[species_id] = max(0.0, new_pop)

                snapshot = PopulationSnapshot(
                    species_id=species_id,
                    region_id=region_id,
                    population_count=max(0.0, new_pop),
                    birth_rate=birth_rate,
                    death_rate=death_rate,
                    migration_rate=migration_rate,
                    status=status,
                    tick=region.tick + 1,
                )
                snapshots.append(snapshot)

            # Commit new populations
            region.species_populations = new_pops
            region.tick += 1
            self._population_history[region_id].extend(snapshots)
            self._total_ticks_simulated += 1

            # Build the ecosystem report
            report = self._build_report(region, snapshots)
            self._reports[region_id].append(report)
            return report

    def simulate_ticks(
        self,
        region_id: str,
        num_ticks: int,
        starting_season: SeasonType,
    ) -> List[EcosystemReport]:
        """Simulate multiple ticks, cycling through seasons.

        Seasons advance in order SPRING -> SUMMER -> AUTUMN -> WINTER
        and wrap around. Each tick produces one EcosystemReport.

        Args:
            region_id: The region to simulate.
            num_ticks: Number of ticks to run.
            starting_season: Season for the first tick.

        Returns:
            List of EcosystemReport objects, one per tick. Empty if the
            region was not found.
        """
        with self._lock:
            if region_id not in self._regions:
                return []

        season_order = [
            SeasonType.SPRING,
            SeasonType.SUMMER,
            SeasonType.AUTUMN,
            SeasonType.WINTER,
        ]
        start_idx = season_order.index(starting_season)
        reports: List[EcosystemReport] = []
        for i in range(num_ticks):
            season = season_order[(start_idx + i) % len(season_order)]
            report = self.simulate_tick(region_id, season)
            if report is not None:
                reports.append(report)
        return reports

    # ------------------------------------------------------------------
    # Migration
    # ------------------------------------------------------------------

    def trigger_migration(
        self,
        species_id: str,
        source_region: str,
        target_region: str,
        trigger: MigrationTrigger,
    ) -> Optional[MigrationEvent]:
        """Manually trigger a migration event between two regions.

        Moves a fraction of the species population from the source region
        to the target region and records a MigrationEvent.

        Args:
            species_id: The species to migrate.
            source_region: Region to migrate from.
            target_region: Region to migrate to.
            trigger: The cause of the migration.

        Returns:
            The recorded MigrationEvent, or None if a region or species
            was not found.
        """
        time.sleep(0.001)
        with self._lock:
            source = self._regions.get(source_region)
            target = self._regions.get(target_region)
            if source is None or target is None:
                return None
            if species_id not in source.species_populations:
                return None

            population = source.species_populations[species_id]
            migrants = population * self.MIGRATION_FRACTION
            if migrants < self.EPSILON:
                return None

            source.species_populations[species_id] = max(
                0.0, population - migrants
            )
            target_pop = target.species_populations.get(species_id, 0.0) + migrants
            target.species_populations[species_id] = target_pop

            # Ensure target has a carrying capacity entry
            if species_id not in target.carrying_capacities:
                profile = self._species.get(species_id)
                if profile is not None:
                    base_capacity = profile.carrying_capacity
                    if target.biome_type in profile.preferred_biomes:
                        base_capacity *= 1.5
                    area_factor = max(0.1, target.area / 100.0)
                    target.carrying_capacities[species_id] = (
                        base_capacity * area_factor
                    )

            event = MigrationEvent(
                species_id=species_id,
                source_region=source_region,
                target_region=target_region,
                count=migrants,
                trigger=trigger,
                tick=source.tick,
            )
            self._migration_events.append(event)
            self._total_migrations += 1
            return event

    # ------------------------------------------------------------------
    # Query and Analysis
    # ------------------------------------------------------------------

    def get_population_history(
        self,
        region_id: str,
        species_id: str,
        limit: int = 100,
    ) -> List[PopulationSnapshot]:
        """Get the population history for a species in a region.

        Args:
            region_id: The region to query.
            species_id: The species to query.
            limit: Maximum number of recent snapshots to return.

        Returns:
            List of PopulationSnapshot objects, most recent last. Empty
            if the region or species has no history.
        """
        with self._lock:
            history = self._population_history.get(region_id, [])
            filtered = [s for s in history if s.species_id == species_id]
            if limit > 0:
                return filtered[-limit:]
            return filtered

    def assess_biodiversity(self, region_id: str) -> Dict[str, Any]:
        """Calculate biodiversity metrics for a region.

        Computes the Shannon-Wiener diversity index, species richness,
        evenness (Pielou's index), Simpson's diversity index, and total
        biomass.

        Args:
            region_id: The region to assess.

        Returns:
            Dict with biodiversity metrics, or an empty dict if the
            region was not found.
        """
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                return {}

            populations = {
                sid: pop for sid, pop in region.species_populations.items()
                if pop > self.EPSILON
            }
            total = sum(populations.values())
            species_count = len(populations)

            if total <= self.EPSILON or species_count == 0:
                return {
                    "region_id": region_id,
                    "species_richness": 0,
                    "shannon_index": 0.0,
                    "simpson_index": 0.0,
                    "evenness": 0.0,
                    "total_biomass": 0.0,
                    "total_population": 0.0,
                }

            # Shannon-Wiener index: H = -sum(p_i * ln(p_i))
            shannon = 0.0
            simpson_sum = 0.0
            for pop in populations.values():
                p = pop / total
                if p > self.EPSILON:
                    shannon -= p * math.log(p)
                    simpson_sum += p * p

            # Pielou's evenness: J = H / ln(S)
            evenness = (
                shannon / math.log(species_count)
                if species_count > 1 else 1.0
            )

            # Total biomass
            total_biomass = 0.0
            for sid, pop in populations.items():
                profile = self._species.get(sid)
                trophic = profile.species_type if profile else SpeciesType.PRODUCER
                body_mass = _TROPHIC_BODY_MASS.get(trophic, 1.0)
                total_biomass += pop * body_mass

            return {
                "region_id": region_id,
                "species_richness": species_count,
                "shannon_index": round(shannon, 6),
                "simpson_index": round(1.0 - simpson_sum, 6),
                "evenness": round(evenness, 6),
                "total_biomass": round(total_biomass, 4),
                "total_population": round(total, 4),
            }

    def detect_collapse_risk(self, region_id: str) -> Dict[str, Any]:
        """Detect species at risk of extinction in a region.

        Evaluates each species against carrying capacity and recent
        population trends to flag endangered and declining populations.

        Args:
            region_id: The region to analyze.

        Returns:
            Dict with risk assessment per species and an overall risk
            level. Empty dict if the region was not found.
        """
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                return {}

            at_risk: List[Dict[str, Any]] = []
            threatened: List[str] = []
            extinct: List[str] = []

            for species_id, population in region.species_populations.items():
                profile = self._species.get(species_id)
                if profile is None:
                    continue

                capacity = region.carrying_capacities.get(
                    species_id, profile.carrying_capacity
                )
                ratio = population / max(capacity, self.EPSILON)

                # Determine trend from history
                history = self._population_history.get(region_id, [])
                species_history = [
                    s for s in history if s.species_id == species_id
                ]
                trend = "unknown"
                if len(species_history) >= 2:
                    recent = species_history[-1].population_count
                    previous = species_history[-2].population_count
                    if recent < previous * 0.9:
                        trend = "declining"
                    elif recent > previous * 1.1:
                        trend = "growing"
                    else:
                        trend = "stable"

                risk_level = "low"
                if population < self.EXTINCTION_THRESHOLD:
                    risk_level = "extinct"
                    extinct.append(species_id)
                elif ratio < self.ENDANGERED_THRESHOLD:
                    risk_level = "critical"
                    threatened.append(species_id)
                elif ratio < self.DECLINING_THRESHOLD or trend == "declining":
                    risk_level = "high"
                    threatened.append(species_id)
                elif trend == "declining":
                    risk_level = "moderate"

                at_risk.append({
                    "species_id": species_id,
                    "species_name": profile.name,
                    "population": round(population, 4),
                    "carrying_capacity": round(capacity, 4),
                    "capacity_ratio": round(ratio, 6),
                    "trend": trend,
                    "risk_level": risk_level,
                })

            overall = "stable"
            if extinct:
                overall = "critical"
            elif any(r["risk_level"] == "critical" for r in at_risk):
                overall = "high"
            elif any(r["risk_level"] == "high" for r in at_risk):
                overall = "moderate"

            return {
                "region_id": region_id,
                "overall_risk": overall,
                "species_at_risk": at_risk,
                "threatened_count": len(threatened),
                "extinct_count": len(extinct),
                "threatened_species": threatened,
                "extinct_species": extinct,
            }

    def get_species_interactions(self, region_id: str) -> Dict[str, Any]:
        """Get predator-prey relationships for species present in a region.

        Builds an adjacency representation of the food web restricted to
        species currently inhabiting the region.

        Args:
            region_id: The region to analyze.

        Returns:
            Dict with predator-prey links, trophic level distribution,
            and food web connectivity. Empty dict if region not found.
        """
        with self._lock:
            region = self._regions.get(region_id)
            if region is None:
                return {}

            present = {
                sid for sid, pop in region.species_populations.items()
                if pop > self.EPSILON
            }

            links: List[Dict[str, Any]] = []
            for species_id in present:
                profile = self._species.get(species_id)
                if profile is None:
                    continue
                for prey_id in profile.prey_ids:
                    if prey_id in present:
                        prey_profile = self._species.get(prey_id)
                        links.append({
                            "predator": species_id,
                            "predator_name": profile.name,
                            "prey": prey_id,
                            "prey_name": prey_profile.name if prey_profile else "",
                        })

            # Trophic level distribution
            trophic_counts: Dict[str, int] = {}
            for species_id in present:
                profile = self._species.get(species_id)
                if profile is None:
                    continue
                t = profile.species_type.value
                trophic_counts[t] = trophic_counts.get(t, 0) + 1

            # Connectivity: ratio of actual links to possible predator-prey pairs
            possible_pairs = 0
            for species_id in present:
                profile = self._species.get(species_id)
                if profile is None:
                    continue
                possible_pairs += len([
                    pid for pid in profile.prey_ids if pid in present
                ])
            connectivity = len(links) / max(possible_pairs, 1)

            return {
                "region_id": region_id,
                "species_present": len(present),
                "links": links,
                "link_count": len(links),
                "trophic_distribution": trophic_counts,
                "connectivity": round(connectivity, 6),
            }

    # ------------------------------------------------------------------
    # Status and Reporting
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for the ecosystem dynamics engine.

        Returns:
            Dict with species, region, simulation, and migration counts.
        """
        with self._lock:
            total_population = 0.0
            total_biomass = 0.0
            region_summaries: List[Dict[str, Any]] = []

            for region in self._regions.values():
                region_pop = sum(region.species_populations.values())
                total_population += region_pop

                region_biomass = 0.0
                for sid, pop in region.species_populations.items():
                    profile = self._species.get(sid)
                    trophic = (
                        profile.species_type if profile else SpeciesType.PRODUCER
                    )
                    body_mass = _TROPHIC_BODY_MASS.get(trophic, 1.0)
                    region_biomass += pop * body_mass
                total_biomass += region_biomass

                region_summaries.append({
                    "region_id": region.region_id,
                    "name": region.name,
                    "tick": region.tick,
                    "season": region.season.value,
                    "species_count": len(region.species_populations),
                    "total_population": round(region_pop, 4),
                    "biomass": round(region_biomass, 4),
                })

            species_type_dist: Dict[str, int] = {}
            for profile in self._species.values():
                t = profile.species_type.value
                species_type_dist[t] = species_type_dist.get(t, 0) + 1

            return {
                "total_species": len(self._species),
                "total_species_registered": self._total_species_registered,
                "total_regions": len(self._regions),
                "total_regions_created": self._total_regions_created,
                "total_introductions": self._total_introductions,
                "total_ticks_simulated": self._total_ticks_simulated,
                "total_migrations": self._total_migrations,
                "total_extinctions": self._total_extinctions,
                "total_migration_events": len(self._migration_events),
                "total_population": round(total_population, 4),
                "total_biomass": round(total_biomass, 4),
                "species_type_distribution": species_type_dist,
                "regions": region_summaries,
            }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _compute_status(
        self,
        population: float,
        carrying_capacity: float,
        birth_rate: float,
        death_rate: float,
    ) -> PopulationStatus:
        """Classify population status based on capacity ratio and rates.

        Args:
            population: Current population count.
            carrying_capacity: Carrying capacity for the species.
            birth_rate: Per-capita birth rate.
            death_rate: Per-capita death rate.

        Returns:
            The appropriate PopulationStatus.
        """
        if population < self.EXTINCTION_THRESHOLD:
            return PopulationStatus.EXTINCT
        ratio = population / max(carrying_capacity, self.EPSILON)
        if ratio > self.MIGRATION_THRESHOLD:
            return PopulationStatus.OVERPOPULATED
        if ratio < self.ENDANGERED_THRESHOLD:
            return PopulationStatus.ENDANGERED
        if ratio < self.DECLINING_THRESHOLD and death_rate > birth_rate:
            return PopulationStatus.DECLINING
        if ratio > self.THRIVING_THRESHOLD and birth_rate >= death_rate:
            return PopulationStatus.THRIVING
        return PopulationStatus.STABLE

    def _build_report(
        self,
        region: RegionEcosystem,
        snapshots: List[PopulationSnapshot],
    ) -> EcosystemReport:
        """Build an EcosystemReport from the current region state.

        Computes biodiversity index, stability score, total biomass,
        food web health, and identifies keystone and threatened species.

        Args:
            region: The region to report on.
            snapshots: Population snapshots from the current tick.

        Returns:
            A populated EcosystemReport.
        """
        # Biodiversity (Shannon index)
        populations = {
            sid: pop for sid, pop in region.species_populations.items()
            if pop > self.EPSILON
        }
        total = sum(populations.values())
        species_count = len(populations)

        shannon = 0.0
        if total > self.EPSILON and species_count > 0:
            for pop in populations.values():
                p = pop / total
                if p > self.EPSILON:
                    shannon -= p * math.log(p)

        # Normalize biodiversity to [0, 1] using ln(species_count)
        max_shannon = math.log(species_count) if species_count > 1 else 1.0
        biodiversity_index = shannon / max(max_shannon, self.EPSILON)

        # Total biomass
        total_biomass = 0.0
        for sid, pop in populations.items():
            profile = self._species.get(sid)
            trophic = profile.species_type if profile else SpeciesType.PRODUCER
            body_mass = _TROPHIC_BODY_MASS.get(trophic, 1.0)
            total_biomass += pop * body_mass

        # Stability: based on how close populations are to half carrying
        # capacity and the balance of birth/death rates
        stability_scores: List[float] = []
        for snap in snapshots:
            profile = self._species.get(snap.species_id)
            if profile is None:
                continue
            capacity = region.carrying_capacities.get(
                snap.species_id, profile.carrying_capacity
            )
            if capacity <= self.EPSILON:
                continue
            ratio = snap.population_count / capacity
            # Peak stability at ratio ~0.5
            dist_from_ideal = abs(ratio - 0.5)
            stab = max(0.0, 1.0 - 2.0 * dist_from_ideal)
            # Penalize when death rate exceeds birth rate
            if snap.death_rate > snap.birth_rate:
                stab *= 0.5
            stability_scores.append(stab)

        stability_score = (
            sum(stability_scores) / len(stability_scores)
            if stability_scores else 0.0
        )

        # Food web health: based on trophic coverage and link integrity
        present = set(populations.keys())
        trophic_levels_present: set = set()
        for sid in present:
            profile = self._species.get(sid)
            if profile is not None:
                trophic_levels_present.add(profile.species_type)

        # Health increases with number of trophic levels represented
        trophic_factor = len(trophic_levels_present) / len(SpeciesType)

        # Link integrity: fraction of predator-prey links where both survive
        link_count = 0
        intact_links = 0
        for sid in present:
            profile = self._species.get(sid)
            if profile is None:
                continue
            for prey_id in profile.prey_ids:
                if prey_id in present:
                    link_count += 1
                    prey_cap = region.carrying_capacities.get(prey_id, 0.0)
                    prey_pop = populations.get(prey_id, 0.0)
                    if (
                        prey_cap > 0
                        and prey_pop / prey_cap > self.ENDANGERED_THRESHOLD
                    ):
                        intact_links += 1

        link_integrity = intact_links / max(link_count, 1)
        food_web_health = (trophic_factor + link_integrity) / 2.0

        # Keystone species: species with the most food web connections
        keystone: List[str] = []
        connection_counts: List[Tuple[str, int]] = []
        for sid in present:
            profile = self._species.get(sid)
            if profile is None:
                continue
            connections = len([
                pid for pid in profile.prey_ids if pid in present
            ]) + len([
                pid for pid in profile.predator_ids if pid in present
            ])
            connection_counts.append((sid, connections))

        connection_counts.sort(key=lambda x: x[1], reverse=True)
        if connection_counts and connection_counts[0][1] > 0:
            max_conn = connection_counts[0][1]
            keystone = [
                sid for sid, c in connection_counts if c >= max_conn * 0.6
            ]

        # Threatened species
        threatened: List[str] = []
        for snap in snapshots:
            if snap.status in (
                PopulationStatus.ENDANGERED,
                PopulationStatus.DECLINING,
            ):
                threatened.append(snap.species_id)

        # Recommendations
        recommendations: List[str] = []
        for snap in snapshots:
            profile = self._species.get(snap.species_id)
            name = profile.name if profile else snap.species_id
            if snap.status == PopulationStatus.ENDANGERED:
                recommendations.append(
                    f"Conservation measures needed for {name}: "
                    f"population critically low"
                )
            elif snap.status == PopulationStatus.OVERPOPULATED:
                recommendations.append(
                    f"Population control recommended for {name}: "
                    f"exceeding carrying capacity"
                )
            elif snap.status == PopulationStatus.DECLINING:
                recommendations.append(
                    f"Monitor {name}: population trend is declining"
                )

        if biodiversity_index < 0.3:
            recommendations.append(
                "Biodiversity is low; consider introducing new species"
            )
        if food_web_health < 0.4:
            recommendations.append(
                "Food web structure is unstable; trophic levels may be missing"
            )
        if stability_score < 0.3:
            recommendations.append(
                "Ecosystem stability is low; populations are far from equilibrium"
            )
        if not recommendations:
            recommendations.append("Ecosystem is healthy; no action required")

        return EcosystemReport(
            region_id=region.region_id,
            tick=region.tick,
            biodiversity_index=biodiversity_index,
            stability_score=stability_score,
            total_biomass=total_biomass,
            species_count=species_count,
            food_web_health=food_web_health,
            keystone_species=keystone,
            threatened_species=threatened,
            recommendations=recommendations,
        )

    def reset(self) -> None:
        """Reset the entire ecosystem dynamics engine state."""
        with self._lock:
            self._species.clear()
            self._regions.clear()
            self._population_history.clear()
            self._migration_events.clear()
            self._reports.clear()
            self._total_species_registered = 0
            self._total_regions_created = 0
            self._total_introductions = 0
            self._total_ticks_simulated = 0
            self._total_migrations = 0
            self._total_extinctions = 0


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_ecosystem_dynamics() -> EcosystemDynamicsEngine:
    """Get the singleton EcosystemDynamicsEngine instance."""
    return EcosystemDynamicsEngine.get_instance()
