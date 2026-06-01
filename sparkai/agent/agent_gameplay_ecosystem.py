"""
SparkLabs Agent - Gameplay Ecosystem Simulator

An autonomous system for simulating and managing complex game world
ecosystems. Models species populations, resource flows, trophic
relationships, and environmental dynamics to create living,
breathing game worlds that respond to player actions.

Core capabilities:
  - Species population modeling with birth/death/migration rates
  - Trophic web construction (predator-prey, symbiosis, competition)
  - Resource distribution and depletion dynamics
  - Environmental event simulation (drought, bloom, migration)
  - Ecosystem stability analysis and equilibrium prediction
  - Biome transition modeling with gradient blending
  - Player impact assessment on ecological balance
  - Emergent behavior detection from species interactions

Architecture:
  GameplayEcosystemSimulator (Singleton)
    |-- EcosystemSpecies (dataclass)
    |-- EcosystemResource (dataclass)
    |-- TrophicRelation (dataclass)
    |-- EcosystemSnapshot (dataclass)
    |-- EnvironmentalEvent (dataclass)
    |-- EcologyReport (dataclass)
    |-- simulate_tick()
    |-- construct_trophic_web()
    |-- introduce_species()
    |-- trigger_environmental_event()
    |-- analyze_stability()
    |-- compute_biome_transition()
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SpeciesRole(Enum):
    PRODUCER = "producer"
    PRIMARY_CONSUMER = "primary_consumer"
    SECONDARY_CONSUMER = "secondary_consumer"
    APEX_PREDATOR = "apex_predator"
    DECOMPOSER = "decomposer"
    SCAVENGER = "scavenger"
    SYMBIONT = "symbiont"


class ResourceType(Enum):
    WATER = "water"
    FOOD_PLANT = "food_plant"
    FOOD_MEAT = "food_meat"
    SHELTER = "shelter"
    SUNLIGHT = "sunlight"
    MINERAL = "mineral"
    SPACE = "space"


class RelationType(Enum):
    PREDATION = "predation"
    COMPETITION = "competition"
    MUTUALISM = "mutualism"
    COMMENSALISM = "commensalism"
    PARASITISM = "parasitism"
    NEUTRAL = "neutral"


class EventCategory(Enum):
    CLIMATE = "climate"
    DISASTER = "disaster"
    BLOOM = "bloom"
    MIGRATION = "migration"
    DISEASE = "disease"
    HUMAN_INTERVENTION = "human_intervention"


class StabilityClass(Enum):
    STABLE = "stable"
    RESILIENT = "resilient"
    FRAGILE = "fragile"
    COLLAPSING = "collapsing"
    RECOVERING = "recovering"


@dataclass
class EcosystemSpecies:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    role: SpeciesRole = SpeciesRole.PRIMARY_CONSUMER
    population: int = 100
    max_population: int = 500
    growth_rate: float = 0.05
    death_rate: float = 0.02
    migration_rate: float = 0.01
    food_consumption: float = 1.0
    water_consumption: float = 0.5
    reproduction_threshold: float = 0.3
    stress_tolerance: float = 0.5
    preferred_biomes: List[str] = field(default_factory=list)
    predators: List[str] = field(default_factory=list)
    prey: List[str] = field(default_factory=list)
    competitors: List[str] = field(default_factory=list)
    behavior_tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "population": self.population,
            "max_population": self.max_population,
            "growth_rate": self.growth_rate,
            "death_rate": self.death_rate,
            "migration_rate": self.migration_rate,
            "food_consumption": self.food_consumption,
            "water_consumption": self.water_consumption,
            "reproduction_threshold": self.reproduction_threshold,
            "stress_tolerance": self.stress_tolerance,
            "preferred_biomes": self.preferred_biomes,
            "predators": self.predators,
            "prey": self.prey,
            "competitors": self.competitors,
            "behavior_tags": self.behavior_tags,
            "created_at": self.created_at,
        }


@dataclass
class EcosystemResource:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    resource_type: ResourceType = ResourceType.FOOD_PLANT
    quantity: float = 1000.0
    max_quantity: float = 2000.0
    regeneration_rate: float = 10.0
    depletion_factor: float = 1.0
    seasonal_variance: float = 0.2
    distribution_zones: List[str] = field(default_factory=list)
    consumed_by: List[str] = field(default_factory=list)
    critical_threshold: float = 0.2
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "resource_type": self.resource_type.value,
            "quantity": self.quantity,
            "max_quantity": self.max_quantity,
            "regeneration_rate": self.regeneration_rate,
            "depletion_factor": self.depletion_factor,
            "seasonal_variance": self.seasonal_variance,
            "distribution_zones": self.distribution_zones,
            "consumed_by": self.consumed_by,
            "critical_threshold": self.critical_threshold,
            "created_at": self.created_at,
        }


@dataclass
class TrophicRelation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_species_id: str = ""
    target_species_id: str = ""
    relation_type: RelationType = RelationType.NEUTRAL
    strength: float = 0.5
    energy_transfer_efficiency: float = 0.1
    impact_on_source: float = 0.0
    impact_on_target: float = 0.0
    seasonal_factor: float = 1.0
    distance_dependency: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_species_id": self.source_species_id,
            "target_species_id": self.target_species_id,
            "relation_type": self.relation_type.value,
            "strength": self.strength,
            "energy_transfer_efficiency": self.energy_transfer_efficiency,
            "impact_on_source": self.impact_on_source,
            "impact_on_target": self.impact_on_target,
            "seasonal_factor": self.seasonal_factor,
            "distance_dependency": self.distance_dependency,
            "created_at": self.created_at,
        }


@dataclass
class EcosystemSnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    tick: int = 0
    total_biomass: float = 0.0
    biodiversity_index: float = 0.0
    resource_abundance: Dict[str, float] = field(default_factory=dict)
    species_populations: Dict[str, int] = field(default_factory=dict)
    stability_class: str = StabilityClass.STABLE.value
    trophic_depth: int = 0
    energy_flow_rate: float = 0.0
    active_events: List[str] = field(default_factory=list)
    captured_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tick": self.tick,
            "total_biomass": self.total_biomass,
            "biodiversity_index": self.biodiversity_index,
            "resource_abundance": self.resource_abundance,
            "species_populations": self.species_populations,
            "stability_class": self.stability_class,
            "trophic_depth": self.trophic_depth,
            "energy_flow_rate": self.energy_flow_rate,
            "active_events": self.active_events,
            "captured_at": self.captured_at,
        }


@dataclass
class EnvironmentalEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    category: EventCategory = EventCategory.CLIMATE
    description: str = ""
    severity: float = 0.5
    duration_ticks: int = 10
    remaining_ticks: int = 10
    affected_species: List[str] = field(default_factory=list)
    affected_resources: List[str] = field(default_factory=list)
    population_modifier: float = 1.0
    resource_modifier: float = 1.0
    biome_targets: List[str] = field(default_factory=list)
    recovery_rate: float = 0.1
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "severity": self.severity,
            "duration_ticks": self.duration_ticks,
            "remaining_ticks": self.remaining_ticks,
            "affected_species": self.affected_species,
            "affected_resources": self.affected_resources,
            "population_modifier": self.population_modifier,
            "resource_modifier": self.resource_modifier,
            "biome_targets": self.biome_targets,
            "recovery_rate": self.recovery_rate,
            "created_at": self.created_at,
        }


@dataclass
class EcologyReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    ecosystem_id: str = ""
    tick: int = 0
    stability_analysis: str = ""
    risk_factors: List[str] = field(default_factory=list)
    dominant_species: List[str] = field(default_factory=list)
    threatened_species: List[str] = field(default_factory=list)
    resource_pressure_points: List[str] = field(default_factory=list)
    emergent_behaviors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    overall_health_score: float = 0.5
    generated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ecosystem_id": self.ecosystem_id,
            "tick": self.tick,
            "stability_analysis": self.stability_analysis,
            "risk_factors": self.risk_factors,
            "dominant_species": self.dominant_species,
            "threatened_species": self.threatened_species,
            "resource_pressure_points": self.resource_pressure_points,
            "emergent_behaviors": self.emergent_behaviors,
            "recommendations": self.recommendations,
            "overall_health_score": self.overall_health_score,
            "generated_at": self.generated_at,
        }


_SPECIES_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "rabbit": {
        "role": SpeciesRole.PRIMARY_CONSUMER,
        "growth_rate": 0.12, "death_rate": 0.04, "max_population": 800,
        "food_consumption": 0.8, "water_consumption": 0.3,
        "stress_tolerance": 0.4, "behavior_tags": ["herbivore", "fast_breeder", "burrower"],
    },
    "fox": {
        "role": SpeciesRole.SECONDARY_CONSUMER,
        "growth_rate": 0.06, "death_rate": 0.03, "max_population": 200,
        "food_consumption": 2.0, "water_consumption": 0.8,
        "stress_tolerance": 0.6, "behavior_tags": ["carnivore", "territorial", "nocturnal"],
    },
    "wolf": {
        "role": SpeciesRole.APEX_PREDATOR,
        "growth_rate": 0.04, "death_rate": 0.02, "max_population": 50,
        "food_consumption": 5.0, "water_consumption": 1.5,
        "stress_tolerance": 0.7, "behavior_tags": ["carnivore", "pack_hunter", "territorial"],
    },
    "deer": {
        "role": SpeciesRole.PRIMARY_CONSUMER,
        "growth_rate": 0.08, "death_rate": 0.03, "max_population": 400,
        "food_consumption": 3.0, "water_consumption": 1.0,
        "stress_tolerance": 0.5, "behavior_tags": ["herbivore", "migratory", "grazer"],
    },
    "eagle": {
        "role": SpeciesRole.APEX_PREDATOR,
        "growth_rate": 0.03, "death_rate": 0.02, "max_population": 30,
        "food_consumption": 1.5, "water_consumption": 0.4,
        "stress_tolerance": 0.6, "behavior_tags": ["carnivore", "aerial", "solitary"],
    },
    "bear": {
        "role": SpeciesRole.APEX_PREDATOR,
        "growth_rate": 0.03, "death_rate": 0.01, "max_population": 40,
        "food_consumption": 8.0, "water_consumption": 2.0,
        "stress_tolerance": 0.8, "behavior_tags": ["omnivore", "hibernator", "territorial"],
    },
    "mouse": {
        "role": SpeciesRole.PRIMARY_CONSUMER,
        "growth_rate": 0.18, "death_rate": 0.08, "max_population": 1500,
        "food_consumption": 0.2, "water_consumption": 0.1,
        "stress_tolerance": 0.3, "behavior_tags": ["herbivore", "fast_breeder", "prey"],
    },
    "hawk": {
        "role": SpeciesRole.SECONDARY_CONSUMER,
        "growth_rate": 0.05, "death_rate": 0.03, "max_population": 60,
        "food_consumption": 1.2, "water_consumption": 0.3,
        "stress_tolerance": 0.5, "behavior_tags": ["carnivore", "aerial", "migratory"],
    },
    "fungus": {
        "role": SpeciesRole.DECOMPOSER,
        "growth_rate": 0.15, "death_rate": 0.02, "max_population": 5000,
        "food_consumption": 0.0, "water_consumption": 0.2,
        "stress_tolerance": 0.9, "behavior_tags": ["decomposer", "spore_spreader", "resilient"],
    },
    "bee": {
        "role": SpeciesRole.SYMBIONT,
        "growth_rate": 0.1, "death_rate": 0.05, "max_population": 3000,
        "food_consumption": 0.3, "water_consumption": 0.1,
        "stress_tolerance": 0.4, "behavior_tags": ["pollinator", "colonial", "honey_producer"],
    },
}

_RESOURCE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "grassland_vegetation": {
        "resource_type": ResourceType.FOOD_PLANT,
        "quantity": 5000.0, "max_quantity": 5000.0, "regeneration_rate": 50.0,
        "seasonal_variance": 0.3, "critical_threshold": 0.15,
    },
    "fresh_water": {
        "resource_type": ResourceType.WATER,
        "quantity": 3000.0, "max_quantity": 3000.0, "regeneration_rate": 20.0,
        "seasonal_variance": 0.4, "critical_threshold": 0.1,
    },
    "prey_animals": {
        "resource_type": ResourceType.FOOD_MEAT,
        "quantity": 2000.0, "max_quantity": 2000.0, "regeneration_rate": 15.0,
        "seasonal_variance": 0.15, "critical_threshold": 0.2,
    },
    "forest_canopy": {
        "resource_type": ResourceType.SHELTER,
        "quantity": 1500.0, "max_quantity": 1500.0, "regeneration_rate": 5.0,
        "seasonal_variance": 0.05, "critical_threshold": 0.25,
    },
    "sunlight_exposure": {
        "resource_type": ResourceType.SUNLIGHT,
        "quantity": 4000.0, "max_quantity": 4000.0, "regeneration_rate": 100.0,
        "seasonal_variance": 0.5, "critical_threshold": 0.1,
    },
    "soil_nutrients": {
        "resource_type": ResourceType.MINERAL,
        "quantity": 2500.0, "max_quantity": 2500.0, "regeneration_rate": 8.0,
        "seasonal_variance": 0.1, "critical_threshold": 0.3,
    },
}

_PREDATION_RULES: Dict[str, List[str]] = {
    "fox": ["rabbit", "mouse"],
    "wolf": ["deer", "rabbit", "fox"],
    "eagle": ["rabbit", "mouse", "fish"],
    "bear": ["deer", "rabbit", "fish"],
    "hawk": ["mouse", "rabbit"],
}

_COMPETITION_RULES: Dict[str, List[str]] = {
    "fox": ["hawk"],
    "wolf": ["bear"],
    "eagle": ["hawk"],
    "deer": ["rabbit"],
    "rabbit": ["deer", "mouse"],
}


class GameplayEcosystemSimulator:
    _instance: Optional["GameplayEcosystemSimulator"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "GameplayEcosystemSimulator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._species: Dict[str, EcosystemSpecies] = {}
        self._resources: Dict[str, EcosystemResource] = {}
        self._relations: Dict[str, TrophicRelation] = {}
        self._snapshots: List[EcosystemSnapshot] = []
        self._active_events: Dict[str, EnvironmentalEvent] = {}
        self._reports: List[EcologyReport] = {}
        self._current_tick: int = 0
        self._total_species_introduced: int = 0
        self._total_events_triggered: int = 0
        self._total_snapshots: int = 0
        self._ecosystem_id: str = uuid.uuid4().hex[:8]

    def introduce_species(
        self,
        name: str,
        role: Optional[str] = None,
        population: int = 100,
        max_population: Optional[int] = None,
        growth_rate: Optional[float] = None,
        death_rate: Optional[float] = None,
        preferred_biomes: Optional[List[str]] = None,
    ) -> EcosystemSpecies:
        template = _SPECIES_TEMPLATES.get(name.lower(), {})
        role_enum = SpeciesRole(role) if role else template.get("role", SpeciesRole.PRIMARY_CONSUMER)
        mx = max_population or template.get("max_population", 500)
        gr = growth_rate if growth_rate is not None else template.get("growth_rate", 0.05)
        dr = death_rate if death_rate is not None else template.get("death_rate", 0.02)

        species = EcosystemSpecies(
            name=name,
            role=role_enum,
            population=population,
            max_population=mx,
            growth_rate=gr,
            death_rate=dr,
            food_consumption=template.get("food_consumption", 1.0),
            water_consumption=template.get("water_consumption", 0.5),
            stress_tolerance=template.get("stress_tolerance", 0.5),
            preferred_biomes=preferred_biomes or template.get("preferred_biomes", []),
            behavior_tags=template.get("behavior_tags", []),
        )

        self._species[species.id] = species
        self._total_species_introduced += 1

        self._auto_wire_relations(species)
        return species

    def _auto_wire_relations(self, species: EcosystemSpecies) -> None:
        species_lower = species.name.lower()

        if species_lower in _PREDATION_RULES:
            for prey_name in _PREDATION_RULES[species_lower]:
                prey = self._find_species_by_name(prey_name)
                if prey:
                    species.prey.append(prey.id)
                    prey.predators.append(species.id)
                    relation = TrophicRelation(
                        source_species_id=species.id,
                        target_species_id=prey.id,
                        relation_type=RelationType.PREDATION,
                        strength=0.7,
                        energy_transfer_efficiency=0.1,
                        impact_on_source=0.1,
                        impact_on_target=-0.4,
                    )
                    self._relations[relation.id] = relation

        if species_lower in _COMPETITION_RULES:
            for competitor_name in _COMPETITION_RULES[species_lower]:
                competitor = self._find_species_by_name(competitor_name)
                if competitor:
                    species.competitors.append(competitor.id)
                    competitor.competitors.append(species.id)
                    relation = TrophicRelation(
                        source_species_id=species.id,
                        target_species_id=competitor.id,
                        relation_type=RelationType.COMPETITION,
                        strength=0.5,
                        energy_transfer_efficiency=0.0,
                        impact_on_source=-0.05,
                        impact_on_target=-0.05,
                    )
                    self._relations[relation.id] = relation

    def _find_species_by_name(self, name: str) -> Optional[EcosystemSpecies]:
        for sp in self._species.values():
            if sp.name.lower() == name.lower():
                return sp
        return None

    def define_resource(
        self,
        name: str,
        resource_type: Optional[str] = None,
        quantity: float = 1000.0,
        max_quantity: Optional[float] = None,
        regeneration_rate: Optional[float] = None,
    ) -> EcosystemResource:
        template = _RESOURCE_TEMPLATES.get(name.lower(), {})
        rt = ResourceType(resource_type) if resource_type else template.get("resource_type", ResourceType.FOOD_PLANT)
        mx = max_quantity or template.get("max_quantity", quantity * 2)
        rr = regeneration_rate if regeneration_rate is not None else template.get("regeneration_rate", 10.0)

        resource = EcosystemResource(
            name=name,
            resource_type=rt,
            quantity=quantity,
            max_quantity=mx,
            regeneration_rate=rr,
            seasonal_variance=template.get("seasonal_variance", 0.2),
            critical_threshold=template.get("critical_threshold", 0.2),
        )

        self._resources[resource.id] = resource
        return resource

    def simulate_tick(self, ticks: int = 1) -> EcosystemSnapshot:
        for _ in range(ticks):
            self._current_tick += 1
            self._process_events()
            self._update_resources()
            self._update_populations()
            self._apply_relations()

        snapshot = self._capture_snapshot()
        self._snapshots.append(snapshot)
        self._total_snapshots += 1
        return snapshot

    def _process_events(self) -> None:
        expired = []
        for evt_id, evt in self._active_events.items():
            evt.remaining_ticks -= 1
            for sp_id in evt.affected_species:
                if sp_id in self._species:
                    self._species[sp_id].population = max(
                        1, int(self._species[sp_id].population * evt.population_modifier)
                    )
            for res_id in evt.affected_resources:
                if res_id in self._resources:
                    self._resources[res_id].quantity *= evt.resource_modifier
            if evt.remaining_ticks <= 0:
                expired.append(evt_id)

        for evt_id in expired:
            del self._active_events[evt_id]

    def _update_resources(self) -> None:
        for res in self._resources.values():
            seasonal = 1.0 + res.seasonal_variance * math.sin(
                self._current_tick * 0.1
            )
            regen = res.regeneration_rate * seasonal
            res.quantity = min(res.max_quantity, res.quantity + regen)

            total_consumption = 0.0
            for sp_id in res.consumed_by:
                if sp_id in self._species:
                    sp = self._species[sp_id]
                    if sp.role in (SpeciesRole.PRIMARY_CONSUMER, SpeciesRole.SECONDARY_CONSUMER, SpeciesRole.APEX_PREDATOR):
                        total_consumption += sp.food_consumption * sp.population * 0.01

            res.quantity = max(0.0, res.quantity - total_consumption * res.depletion_factor)

    def _update_populations(self) -> None:
        for sp in self._species.values():
            food_factor = 1.0
            water_factor = 1.0
            resource_ids = [rid for rid, res in self._resources.items() if sp.id in res.consumed_by]
            if resource_ids:
                food_avail = sum(
                    min(1.0, self._resources[rid].quantity / self._resources[rid].max_quantity)
                    for rid in resource_ids
                ) / max(len(resource_ids), 1)
                food_factor = max(0.2, food_avail)

            predator_pressure = 0.0
            for pred_id in sp.predators:
                if pred_id in self._species:
                    pred = self._species[pred_id]
                    predator_pressure += pred.population / max(pred.max_population, 1)
            predator_factor = max(0.1, 1.0 - predator_pressure * 0.5)

            growth = sp.population * sp.growth_rate * food_factor * (1.0 - sp.population / sp.max_population)
            death = sp.population * sp.death_rate * (2.0 - food_factor)
            migration = sp.population * sp.migration_rate * (1.0 - predator_factor)

            sp.population = max(1, int(sp.population + growth - death - migration))
            sp.population = min(sp.max_population, sp.population)

    def _apply_relations(self) -> None:
        for relation in self._relations.values():
            if relation.relation_type == RelationType.PREDATION:
                source = self._species.get(relation.source_species_id)
                target = self._species.get(relation.target_species_id)
                if source and target:
                    predated = int(target.population * relation.strength * relation.energy_transfer_efficiency)
                    target.population = max(1, target.population - predated)

    def _capture_snapshot(self) -> EcosystemSnapshot:
        total_biomass = sum(sp.population * sp.food_consumption for sp in self._species.values())

        populations = {sp.name: sp.population for sp in self._species.values()}
        unique_species = len(self._species)
        shannon_index = 0.0
        total_pop = sum(populations.values())
        if total_pop > 0:
            for pop in populations.values():
                if pop > 0:
                    p = pop / total_pop
                    shannon_index -= p * math.log(p)
        biodiversity = shannon_index / max(1.0, math.log(max(unique_species, 1)))

        resource_abundance = {
            res.name: res.quantity / max(res.max_quantity, 1)
            for res in self._resources.values()
        }

        trophic_depth = 0
        for sp in self._species.values():
            if sp.role == SpeciesRole.APEX_PREDATOR:
                trophic_depth = max(trophic_depth, 4)
            elif sp.role == SpeciesRole.SECONDARY_CONSUMER:
                trophic_depth = max(trophic_depth, 3)
            elif sp.role == SpeciesRole.PRIMARY_CONSUMER:
                trophic_depth = max(trophic_depth, 2)
            elif sp.role == SpeciesRole.PRODUCER:
                trophic_depth = max(trophic_depth, 1)

        stability = StabilityClass.STABLE
        if biodiversity < 0.3:
            stability = StabilityClass.FRAGILE
        elif len(self._active_events) > 2:
            stability = StabilityClass.RECOVERING
        elif biodiversity > 0.7 and len(self._active_events) == 0:
            stability = StabilityClass.RESILIENT

        return EcosystemSnapshot(
            tick=self._current_tick,
            total_biomass=round(total_biomass, 1),
            biodiversity_index=round(biodiversity, 4),
            resource_abundance={k: round(v, 3) for k, v in resource_abundance.items()},
            species_populations=populations,
            stability_class=stability.value,
            trophic_depth=trophic_depth,
            energy_flow_rate=round(biodiversity * 0.8 + 0.1, 3),
            active_events=[e.name for e in self._active_events.values()],
        )

    def trigger_environmental_event(
        self,
        name: str,
        category: Optional[str] = None,
        severity: float = 0.5,
        duration_ticks: int = 10,
        affected_species: Optional[List[str]] = None,
        affected_resources: Optional[List[str]] = None,
    ) -> EnvironmentalEvent:
        cat = EventCategory(category) if category else EventCategory.CLIMATE

        sp_ids = []
        if affected_species:
            for name_or_id in affected_species:
                found = self._find_species_by_name(name_or_id)
                if found:
                    sp_ids.append(found.id)
                elif name_or_id in self._species:
                    sp_ids.append(name_or_id)

        res_ids = []
        if affected_resources:
            for name_or_id in affected_resources:
                for rid, res in self._resources.items():
                    if res.name == name_or_id or rid == name_or_id:
                        res_ids.append(rid)

        pop_mod = 1.0 - severity * 0.3
        res_mod = 1.0 - severity * 0.2

        event = EnvironmentalEvent(
            name=name,
            category=cat,
            description=f"{cat.value} event: {name} (severity: {severity})",
            severity=severity,
            duration_ticks=duration_ticks,
            remaining_ticks=duration_ticks,
            affected_species=sp_ids,
            affected_resources=res_ids,
            population_modifier=pop_mod,
            resource_modifier=res_mod,
        )

        self._active_events[event.id] = event
        self._total_events_triggered += 1
        return event

    def analyze_stability(self) -> EcologyReport:
        snapshot = self._capture_snapshot()

        risk_factors = []
        for res in self._resources.values():
            ratio = res.quantity / max(res.max_quantity, 1)
            if ratio < res.critical_threshold:
                risk_factors.append(f"Critical resource depletion: {res.name} at {ratio:.1%}")

        for sp in self._species.values():
            pop_ratio = sp.population / max(sp.max_population, 1)
            if pop_ratio < 0.1:
                risk_factors.append(f"Critically low population: {sp.name} at {pop_ratio:.1%}")

        if snapshot.biodiversity_index < 0.3:
            risk_factors.append(f"Low biodiversity index ({snapshot.biodiversity_index:.3f}) threatens ecosystem resilience")

        populations = [(sp.name, sp.population) for sp in self._species.values()]
        populations.sort(key=lambda x: x[1], reverse=True)

        dominant = [name for name, _ in populations[:3]] if populations else []
        threatened = [name for name, pop in populations if pop < 10] if populations else []

        resource_pressures = [
            res.name for res in self._resources.values()
            if res.quantity / max(res.max_quantity, 1) < 0.3
        ]

        emergent = []
        if len(self._species) >= 3 and snapshot.biodiversity_index > 0.5:
            emergent.append("Trophic cascade potential detected")
        if len(self._active_events) > 0:
            emergent.append(f"Ecosystem under {len(self._active_events)} active environmental events")

        health_score = (
            snapshot.biodiversity_index * 0.4
            + (1.0 - len(risk_factors) * 0.15) * 0.3
            + (1.0 - len(self._active_events) * 0.1) * 0.3
        )
        health_score = max(0.0, min(1.0, health_score))

        recommendations = []
        if len(threatened) > 0:
            recommendations.append(f"Consider conservation measures for: {', '.join(threatened)}")
        if len(resource_pressures) > 0:
            recommendations.append(f"Resource supplementation needed for: {', '.join(resource_pressures)}")
        if snapshot.biodiversity_index < 0.4:
            recommendations.append("Introduce keystone species to boost biodiversity")

        report = EcologyReport(
            ecosystem_id=self._ecosystem_id,
            tick=self._current_tick,
            stability_analysis=f"Ecosystem rated {snapshot.stability_class} with biodiversity index {snapshot.biodiversity_index:.3f}",
            risk_factors=risk_factors,
            dominant_species=dominant,
            threatened_species=threatened,
            resource_pressure_points=resource_pressures,
            emergent_behaviors=emergent,
            recommendations=recommendations,
            overall_health_score=round(health_score, 3),
        )

        self._reports[report.id] = report
        return report

    def construct_trophic_web(
        self,
        force_rebuild: bool = False,
    ) -> Dict[str, Any]:
        web: Dict[str, List[Dict[str, Any]]] = {}
        for level in ["producer", "primary_consumer", "secondary_consumer", "apex_predator"]:
            web[level] = []

        for sp in self._species.values():
            level_key = sp.role.value
            entry = {
                "id": sp.id,
                "name": sp.name,
                "population": sp.population,
                "preys_on": [],
                "predated_by": [],
            }
            for pred_id in sp.prey:
                pred_sp = self._species.get(pred_id)
                if pred_sp:
                    entry["preys_on"].append(pred_sp.name)
            for pred_id in sp.predators:
                pred_sp = self._species.get(pred_id)
                if pred_sp:
                    entry["predated_by"].append(pred_sp.name)

            if level_key in web:
                web[level_key].append(entry)
            else:
                web.setdefault(level_key, []).append(entry)

        return {
            "ecosystem_id": self._ecosystem_id,
            "tick": self._current_tick,
            "trophic_web": web,
            "total_relations": len(self._relations),
            "trophic_depth": max(
                4 if len(web.get("apex_predator", [])) > 0 else 0,
                3 if len(web.get("secondary_consumer", [])) > 0 else 0,
                2 if len(web.get("primary_consumer", [])) > 0 else 0,
                1 if len(web.get("producer", [])) > 0 else 0,
            ),
        }

    def compute_biome_transition(
        self,
        from_biome: str,
        to_biome: str,
        transition_factor: float = 0.5,
    ) -> Dict[str, Any]:
        from_sp = [sp for sp in self._species.values() if from_biome in sp.preferred_biomes]
        to_sp = [sp for sp in self._species.values() if to_biome in sp.preferred_biomes]

        migrants = []
        declining = []
        threshold = 0.3

        for sp in from_sp:
            if to_biome in sp.preferred_biomes:
                migrants.append({
                    "species": sp.name,
                    "adaptability": sp.stress_tolerance,
                    "projected_population": int(sp.population * (1.0 + transition_factor * sp.stress_tolerance)),
                })
            else:
                projected = int(sp.population * (1.0 - transition_factor * (1.0 - sp.stress_tolerance)))
                declining.append({
                    "species": sp.name,
                    "current_population": sp.population,
                    "projected_population": max(1, projected),
                    "risk_level": "high" if projected < sp.population * threshold else "moderate",
                })

        for sp in to_sp:
            if sp not in from_sp:
                migrants.append({
                    "species": sp.name,
                    "adaptability": sp.stress_tolerance,
                    "projected_population": int(sp.population * (1.0 + transition_factor * 0.5)),
                })

        return {
            "from_biome": from_biome,
            "to_biome": to_biome,
            "transition_factor": transition_factor,
            "migrating_species": migrants,
            "declining_species": declining,
            "biodiversity_impact": round(
                len(migrants) / max(len(self._species), 1) - len(declining) * 0.1 / max(len(self._species), 1), 3
            ),
            "estimated_stabilization_ticks": max(5, int(10 * (1.0 - transition_factor))),
        }

    def get_species(self, species_id: str) -> Optional[EcosystemSpecies]:
        return self._species.get(species_id)

    def list_species(self) -> List[Dict[str, Any]]:
        return [sp.to_dict() for sp in self._species.values()]

    def list_resources(self) -> List[Dict[str, Any]]:
        return [res.to_dict() for res in self._resources.values()]

    def list_relations(self) -> List[Dict[str, Any]]:
        return [rel.to_dict() for rel in self._relations.values()]

    def list_snapshots(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [sn.to_dict() for sn in self._snapshots[-limit:]]

    def list_events(self) -> List[Dict[str, Any]]:
        return [evt.to_dict() for evt in self._active_events.values()]

    def get_latest_report(self) -> Optional[Dict[str, Any]]:
        if self._reports:
            latest = max(self._reports.values(), key=lambda r: r.generated_at)
            return latest.to_dict()
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "ecosystem_id": self._ecosystem_id,
            "current_tick": self._current_tick,
            "total_species": len(self._species),
            "total_resources": len(self._resources),
            "total_relations": len(self._relations),
            "total_species_introduced": self._total_species_introduced,
            "total_events_triggered": self._total_events_triggered,
            "total_snapshots": self._total_snapshots,
            "active_events": len(self._active_events),
            "trophic_depth": max(
                (4 if any(sp.role == SpeciesRole.APEX_PREDATOR for sp in self._species.values()) else 0),
                (3 if any(sp.role == SpeciesRole.SECONDARY_CONSUMER for sp in self._species.values()) else 0),
                (2 if any(sp.role == SpeciesRole.PRIMARY_CONSUMER for sp in self._species.values()) else 0),
                (1 if any(sp.role == SpeciesRole.PRODUCER for sp in self._species.values()) else 0),
            ),
            "species_by_role": {
                role.value: sum(1 for sp in self._species.values() if sp.role == role)
                for role in SpeciesRole
            },
        }


def get_gameplay_ecosystem_simulator() -> GameplayEcosystemSimulator:
    return GameplayEcosystemSimulator()