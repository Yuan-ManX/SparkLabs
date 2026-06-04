"""
SparkAI Agent - World Evolution System

Autonomous multi-day world evolution engine that drives continuous
world progression through natural cycles: day/night, seasons, resource
flows, population dynamics, and emergent storyline progression.

The system manages time advancement, triggers evolution events, tracks
world state across cycles, and ensures coherent world progression
without explicit scripting.
"""

from __future__ import annotations

import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DayPhase(str, Enum):
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    NIGHT = "night"
    MIDNIGHT = "midnight"


class Season(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class EvolutionTrigger(str, Enum):
    TIME_ADVANCE = "time_advance"
    POPULATION_THRESHOLD = "population_threshold"
    RESOURCE_CRISIS = "resource_crisis"
    FACTION_CONFLICT = "faction_conflict"
    DISCOVERY = "discovery"
    EXTERNAL_EVENT = "external_event"
    CHARACTER_MILESTONE = "character_milestone"


class EvolutionPhase(str, Enum):
    STABLE = "stable"
    GROWING = "growing"
    DECLINING = "declining"
    TRANSITIONING = "transitioning"
    CRISIS = "crisis"
    RENAISSANCE = "renaissance"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class EvolutionDay:
    """A single day in the world evolution timeline."""
    day_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    day_number: int = 1
    season: Season = Season.SPRING
    dominant_phase: EvolutionPhase = EvolutionPhase.STABLE
    events: List[str] = field(default_factory=list)
    character_actions: List[Dict[str, Any]] = field(default_factory=list)
    faction_changes: List[Dict[str, Any]] = field(default_factory=list)
    resource_changes: Dict[str, float] = field(default_factory=dict)
    narrative_developments: List[str] = field(default_factory=list)
    world_state_snapshot: Dict[str, Any] = field(default_factory=dict)
    duration_minutes: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day_id": self.day_id,
            "day_number": self.day_number,
            "season": self.season.value,
            "dominant_phase": self.dominant_phase.value,
            "events": self.events,
            "character_actions": self.character_actions,
            "faction_changes": self.faction_changes,
            "resource_changes": self.resource_changes,
            "narrative_developments": self.narrative_developments,
            "world_state_snapshot": self.world_state_snapshot,
            "duration_minutes": self.duration_minutes,
        }


@dataclass
class EvolutionSchedule:
    """Pre-computed schedule of evolution events."""
    schedule_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_id: str = ""
    total_days: int = 30
    days_elapsed: int = 0
    current_season: Season = Season.SPRING
    planned_events: List[Dict[str, Any]] = field(default_factory=list)
    triggered_events: List[str] = field(default_factory=list)
    evolution_triggers: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "world_id": self.world_id,
            "total_days": self.total_days,
            "days_elapsed": self.days_elapsed,
            "current_season": self.current_season.value,
            "planned_events": self.planned_events,
            "triggered_events": self.triggered_events,
            "evolution_triggers": self.evolution_triggers,
        }


@dataclass
class PopulationModel:
    """Dynamic population model for world entities."""
    model_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_type: str = ""
    initial_count: int = 100
    current_count: int = 100
    growth_rate: float = 0.01
    carrying_capacity: int = 500
    death_rate: float = 0.005
    migration_rate: float = 0.0
    birth_rate: float = 0.015
    seasonal_modifier: float = 1.0
    historical_data: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "entity_type": self.entity_type,
            "initial_count": self.initial_count,
            "current_count": self.current_count,
            "growth_rate": self.growth_rate,
            "carrying_capacity": self.carrying_capacity,
            "historical_data": self.historical_data,
        }


@dataclass
class ResourceCycle:
    """Resource production and consumption cycle."""
    cycle_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    resource_name: str = ""
    current_amount: float = 1000.0
    max_capacity: float = 5000.0
    production_rate: float = 10.0
    consumption_rate: float = 8.0
    seasonal_factor: float = 1.0
    is_renewable: bool = True
    depletion_warning: bool = False
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "resource_name": self.resource_name,
            "current_amount": self.current_amount,
            "max_capacity": self.max_capacity,
            "production_rate": self.production_rate,
            "consumption_rate": self.consumption_rate,
            "is_renewable": self.is_renewable,
            "depletion_warning": self.depletion_warning,
            "history": self.history,
        }


# ---------------------------------------------------------------------------
# World Evolution System
# ---------------------------------------------------------------------------

class AgentWorldEvolution:
    """
    Autonomous world evolution engine.

    Drives multi-day world progression with time cycles, population dynamics,
    resource flows, faction evolution, and emergent narrative development.
    """

    _instance: Optional["AgentWorldEvolution"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "AgentWorldEvolution":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentWorldEvolution":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._schedules: Dict[str, EvolutionSchedule] = {}
        self._history: Dict[str, List[EvolutionDay]] = {}
        self._populations: Dict[str, List[PopulationModel]] = {}
        self._resources: Dict[str, List[ResourceCycle]] = {}
        self._active_triggers: Dict[str, List[Dict[str, Any]]] = {}
        self._day_phases: List[DayPhase] = list(DayPhase)
        self._season_cycle: List[Season] = list(Season)
        self._season_durations: Dict[Season, int] = {
            Season.SPRING: 90, Season.SUMMER: 90,
            Season.AUTUMN: 90, Season.WINTER: 90,
        }
        self._total_evolutions: int = 0
        self._total_days_simulated: int = 0

    # ------------------------------------------------------------------
    # Schedule Management
    # ------------------------------------------------------------------

    def create_schedule(
        self, world_id: str, total_days: int = 30,
        starting_season: Season = Season.SPRING,
        pre_planned_events: Optional[List[Dict[str, Any]]] = None,
        auto_generate_events: bool = True,
    ) -> EvolutionSchedule:
        """Create an evolution schedule for a world."""
        with self._lock:
            schedule = EvolutionSchedule(
                world_id=world_id,
                total_days=total_days,
                current_season=starting_season,
                planned_events=pre_planned_events or [],
            )
            if auto_generate_events:
                schedule.planned_events.extend(
                    self._generate_seasonal_events(starting_season, total_days)
                )
            self._schedules[world_id] = schedule
            if world_id not in self._history:
                self._history[world_id] = []
            return schedule

    def advance_day(
        self, world_id: str,
        character_actions: Optional[List[Dict[str, Any]]] = None,
        external_events: Optional[List[str]] = None,
    ) -> EvolutionDay:
        """Advance the world by one day and return the day record."""
        with self._lock:
            schedule = self._get_schedule(world_id)
            schedule.days_elapsed += 1
            day_num = schedule.days_elapsed

            # Update season
            season = self._calculate_season(schedule)
            schedule.current_season = season

            # Determine day phase
            dominant_phase = self._determine_phase(world_id, schedule)

            # Trigger events for this day
            events: List[str] = []
            for planned in schedule.planned_events:
                if planned.get("day", -1) == day_num:
                    events.append(planned["event_name"])
                    schedule.triggered_events.append(planned["event_name"])

            if external_events:
                events.extend(external_events)

            # Process populations
            pop_changes = self._advance_populations(world_id, season)

            # Process resources
            resource_changes = self._advance_resources(world_id, season)

            # Generate narrative developments
            narratives = self._generate_narrative_developments(
                world_id, events, pop_changes, resource_changes
            )

            day = EvolutionDay(
                day_number=day_num,
                season=season,
                dominant_phase=dominant_phase,
                events=events,
                character_actions=character_actions or [],
                faction_changes=pop_changes,
                resource_changes={
                    r: rc.current_amount for r, rc in resource_changes.items()
                },
                narrative_developments=narratives,
                world_state_snapshot=self._capture_world_state(world_id),
                duration_minutes=0.0,
            )

            if world_id not in self._history:
                self._history[world_id] = []
            self._history[world_id].append(day)
            self._total_days_simulated += 1
            schedule.updated_at = _time_module.time()
            return day

    def advance_multiple_days(
        self, world_id: str, num_days: int = 7,
        character_actions_per_day: Optional[List[List[Dict[str, Any]]]] = None,
    ) -> List[EvolutionDay]:
        """Advance multiple days at once."""
        with self._lock:
            days: List[EvolutionDay] = []
            for i in range(num_days):
                actions = None
                if character_actions_per_day and i < len(character_actions_per_day):
                    actions = character_actions_per_day[i]
                day = self.advance_day(world_id, character_actions=actions)
                days.append(day)
            self._total_evolutions += 1
            return days

    # ------------------------------------------------------------------
    # Population Dynamics
    # ------------------------------------------------------------------

    def create_population_model(
        self, world_id: str, entity_type: str,
        initial_count: int = 100, growth_rate: float = 0.01,
        carrying_capacity: int = 500,
    ) -> PopulationModel:
        """Create a population model for a world entity type."""
        with self._lock:
            model = PopulationModel(
                entity_type=entity_type,
                initial_count=initial_count,
                current_count=initial_count,
                growth_rate=growth_rate,
                carrying_capacity=carrying_capacity,
            )
            if world_id not in self._populations:
                self._populations[world_id] = []
            self._populations[world_id].append(model)
            return model

    # ------------------------------------------------------------------
    # Resource Management
    # ------------------------------------------------------------------

    def create_resource_cycle(
        self, world_id: str, resource_name: str,
        initial_amount: float = 1000.0, max_capacity: float = 5000.0,
        production_rate: float = 10.0, consumption_rate: float = 8.0,
        is_renewable: bool = True,
    ) -> ResourceCycle:
        """Create a resource cycle model."""
        with self._lock:
            cycle = ResourceCycle(
                resource_name=resource_name,
                current_amount=initial_amount,
                max_capacity=max_capacity,
                production_rate=production_rate,
                consumption_rate=consumption_rate,
                is_renewable=is_renewable,
            )
            if world_id not in self._resources:
                self._resources[world_id] = []
            self._resources[world_id].append(cycle)
            return cycle

    # ------------------------------------------------------------------
    # Evolution Triggers
    # ------------------------------------------------------------------

    def add_evolution_trigger(
        self, world_id: str, trigger_type: EvolutionTrigger,
        condition_data: Dict[str, Any],
        effect_data: Dict[str, Any],
        priority: int = 5,
    ) -> str:
        """Add a conditional evolution trigger."""
        with self._lock:
            trigger_id = uuid.uuid4().hex
            trigger = {
                "trigger_id": trigger_id,
                "trigger_type": trigger_type.value,
                "condition": condition_data,
                "effect": effect_data,
                "priority": priority,
                "is_active": True,
                "times_triggered": 0,
                "created_at": _time_module.time(),
            }
            if world_id not in self._active_triggers:
                self._active_triggers[world_id] = []
            self._active_triggers[world_id].append(trigger)
            return trigger_id

    def check_triggers(self, world_id: str) -> List[Dict[str, Any]]:
        """Check and fire any active triggers for a world."""
        with self._lock:
            fired: List[Dict[str, Any]] = []
            triggers = self._active_triggers.get(world_id, [])
            schedule = self._get_schedule(world_id)
            for trigger in triggers:
                if not trigger["is_active"]:
                    continue
                if self._evaluate_trigger_condition(trigger, schedule, world_id):
                    trigger["times_triggered"] += 1
                    fired.append(trigger["effect"])
            return fired

    # ------------------------------------------------------------------
    # Stats & Query
    # ------------------------------------------------------------------

    def get_evolution_stats(self) -> Dict[str, Any]:
        """Get overall evolution system statistics."""
        with self._lock:
            return {
                "total_evolutions": self._total_evolutions,
                "total_days_simulated": self._total_days_simulated,
                "active_worlds": len(self._schedules),
                "total_population_models": sum(
                    len(p) for p in self._populations.values()
                ),
                "total_resource_cycles": sum(
                    len(r) for r in self._resources.values()
                ),
                "active_triggers": sum(
                    len(t) for t in self._active_triggers.values()
                ),
            }

    def get_world_timeline(self, world_id: str) -> List[Dict[str, Any]]:
        """Get the full timeline for a world."""
        with self._lock:
            days = self._history.get(world_id, [])
            return [d.to_dict() for d in days]

    def get_world_state(self, world_id: str) -> Dict[str, Any]:
        """Get the current state of a world."""
        with self._lock:
            schedule = self._get_schedule(world_id)
            return {
                "world_id": world_id,
                "days_elapsed": schedule.days_elapsed,
                "current_season": schedule.current_season.value,
                "days_remaining": schedule.total_days - schedule.days_elapsed,
                "triggered_events_count": len(schedule.triggered_events),
                "population_models": [
                    p.to_dict() for p in self._populations.get(world_id, [])
                ],
                "resource_cycles": [
                    r.to_dict() for r in self._resources.get(world_id, [])
                ],
                "day_history_count": len(self._history.get(world_id, [])),
                "active_triggers_count": len(
                    self._active_triggers.get(world_id, [])
                ),
            }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _get_schedule(self, world_id: str) -> EvolutionSchedule:
        if world_id not in self._schedules:
            schedule = EvolutionSchedule(world_id=world_id)
            self._schedules[world_id] = schedule
        return self._schedules[world_id]

    def _calculate_season(self, schedule: EvolutionSchedule) -> Season:
        season_length = self._season_durations.get(
            schedule.current_season, 90
        )
        days_in_season = schedule.days_elapsed % season_length
        if days_in_season == 0 and schedule.days_elapsed > 0:
            idx = self._season_cycle.index(schedule.current_season)
            return self._season_cycle[(idx + 1) % 4]
        return schedule.current_season

    def _determine_phase(
        self, world_id: str, schedule: EvolutionSchedule
    ) -> EvolutionPhase:
        pops = self._populations.get(world_id, [])
        if not pops:
            return EvolutionPhase.STABLE
        total_pop = sum(p.current_count for p in pops)
        max_capacity = sum(p.carrying_capacity for p in pops)
        ratio = total_pop / max(max_capacity, 1)

        resources = self._resources.get(world_id, [])
        depleted = sum(1 for r in resources if r.depletion_warning)

        if depleted > len(resources) * 0.5:
            return EvolutionPhase.CRISIS
        if ratio > 0.9:
            return EvolutionPhase.DECLINING
        if ratio > 0.6:
            return EvolutionPhase.STABLE
        if ratio > 0.3:
            return EvolutionPhase.GROWING
        return EvolutionPhase.RENAISSANCE

    def _generate_seasonal_events(
        self, season: Season, total_days: int
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        event_templates = {
            Season.SPRING: [
                "Spring Planting Festival",
                "River Thaw Trading Boom",
                "Migration Season Begins",
                "Spring Equinox Celebration",
            ],
            Season.SUMMER: [
                "Summer Tournament",
                "Heat Wave Survival",
                "Harvest Preparation",
                "Midsummer Festival",
            ],
            Season.AUTUMN: [
                "Harvest Festival",
                "Trade Caravan Arrives",
                "Autumn Equinox Ritual",
                "Preparation for Winter",
            ],
            Season.WINTER: [
                "Winter Solstice Feast",
                "Blizzard Survival",
                "Ice Market Opens",
                "Year-End Ceremony",
            ],
        }
        templates = event_templates.get(season, [])
        for i, event_name in enumerate(templates):
            day_offset = (i * (total_days // max(len(templates), 1))) + 1
            events.append({
                "event_name": event_name,
                "day": min(day_offset, total_days),
                "season": season.value,
                "auto_generated": True,
            })
        return events

    def _advance_populations(
        self, world_id: str, season: Season
    ) -> List[Dict[str, Any]]:
        changes: List[Dict[str, Any]] = []
        seasonal_mod = {
            Season.SPRING: 1.2, Season.SUMMER: 1.0,
            Season.AUTUMN: 0.9, Season.WINTER: 0.7,
        }.get(season, 1.0)

        for model in self._populations.get(world_id, []):
            model.seasonal_modifier = seasonal_mod
            births = int(model.current_count * model.birth_rate * seasonal_mod)
            deaths = int(model.current_count * model.death_rate / max(seasonal_mod, 0.1))
            net_migration = int(model.current_count * model.migration_rate)
            capacity_factor = 1.0 - (
                model.current_count / max(model.carrying_capacity, 1)
            )
            new_count = max(0, model.current_count + births - deaths + net_migration)
            new_count = int(new_count * (0.5 + 0.5 * max(0, capacity_factor)))
            old_count = model.current_count
            model.current_count = new_count
            model.historical_data.append({
                "day": self._schedules[world_id].days_elapsed,
                "count": new_count,
                "births": births,
                "deaths": deaths,
                "season": season.value,
            })
            changes.append({
                "entity_type": model.entity_type,
                "old_count": old_count,
                "new_count": new_count,
                "delta": new_count - old_count,
            })
        return changes

    def _advance_resources(
        self, world_id: str, season: Season
    ) -> Dict[str, ResourceCycle]:
        seasonal_mod = {
            Season.SPRING: 1.1, Season.SUMMER: 0.9,
            Season.AUTUMN: 1.3, Season.WINTER: 0.6,
        }.get(season, 1.0)

        for cycle in self._resources.get(world_id, []):
            cycle.seasonal_factor = seasonal_mod
            produced = cycle.production_rate * seasonal_mod
            consumed = cycle.consumption_rate / max(seasonal_mod, 0.1)
            net = produced - consumed
            cycle.current_amount = max(
                0, min(cycle.max_capacity, cycle.current_amount + net)
            )
            cycle.depletion_warning = (
                cycle.current_amount < cycle.max_capacity * 0.1
            )
            cycle.history.append({
                "day": self._schedules[world_id].days_elapsed,
                "amount": cycle.current_amount,
                "season": season.value,
            })
        return {
            r.cycle_id: r for r in self._resources.get(world_id, [])
        }

    def _generate_narrative_developments(
        self, world_id: str, events: List[str],
        pop_changes: List[Dict[str, Any]],
        resource_changes: Dict[str, float],
    ) -> List[str]:
        narratives: List[str] = []
        for change in pop_changes:
            if change["delta"] > 50:
                narratives.append(
                    f"{change['entity_type']} population booms to {change['new_count']}"
                )
            elif change["delta"] < -50:
                narratives.append(
                    f"{change['entity_type']} population declines to {change['new_count']}"
                )
        for rid, amount in resource_changes.items():
            # Find the resource cycle
            for cycle in self._resources.get(world_id, []):
                if cycle.cycle_id == rid and cycle.depletion_warning:
                    narratives.append(
                        f"Warning: {cycle.resource_name} resources nearing depletion"
                    )
        for event in events:
            if len(narratives) < 10:
                narratives.append(f"Event occurred: {event}")
        return narratives

    def _capture_world_state(self, world_id: str) -> Dict[str, Any]:
        state: Dict[str, Any] = {}
        schedule = self._schedules.get(world_id)
        if schedule:
            state["season"] = schedule.current_season.value
            state["days_elapsed"] = schedule.days_elapsed
        populations = self._populations.get(world_id, [])
        state["total_population"] = sum(p.current_count for p in populations)
        state["population_by_type"] = {
            p.entity_type: p.current_count for p in populations
        }
        resources = self._resources.get(world_id, [])
        state["total_resources"] = sum(r.current_amount for r in resources)
        state["resources"] = {
            r.resource_name: r.current_amount for r in resources
        }
        return state

    def _evaluate_trigger_condition(
        self, trigger: Dict[str, Any],
        schedule: EvolutionSchedule,
        world_id: str,
    ) -> bool:
        condition = trigger.get("condition", {})
        cond_type = condition.get("type", "")

        if cond_type == "day_number":
            target = condition.get("target", 0)
            return schedule.days_elapsed >= target
        if cond_type == "season":
            target_season = condition.get("target", "")
            return schedule.current_season.value == target_season
        if cond_type == "population":
            target_type = condition.get("entity_type", "")
            threshold = condition.get("threshold", 100)
            comparison = condition.get("comparison", ">=")
            for model in self._populations.get(world_id, []):
                if model.entity_type == target_type:
                    if comparison == ">=":
                        return model.current_count >= threshold
                    if comparison == "<=":
                        return model.current_count <= threshold
        if cond_type == "resource":
            resource_name = condition.get("resource_name", "")
            threshold = condition.get("threshold", 100)
            for cycle in self._resources.get(world_id, []):
                if cycle.resource_name == resource_name:
                    return cycle.current_amount <= threshold
        return False


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_world_evolution() -> AgentWorldEvolution:
    return AgentWorldEvolution.get_instance()