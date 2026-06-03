"""
SparkLabs Agent - Simulation Controller

AI-driven real-time world simulation controller for the SparkLabs
AI-native game engine. Manages autonomous agent populations, world
state evolution, simulation ticks, event broadcasting, and emergent
interaction observation.

Architecture:
  AgentSimulationController (Singleton)
    |-- AutonomousAgent (AI agent in the simulation world)
    |-- WorldState (overall world state snapshot)
    |-- SimulationTick (single tick of simulation processing)
    |-- AgentState (IDLE, EXPLORING, INTERACTING, CRAFTING, COMBATING, RESTING, TRAVELING, TRADING)
    |-- TimeOfDay (DAWN, MORNING, AFTERNOON, DUSK, NIGHT, MIDNIGHT)
    |-- WeatherType (CLEAR, CLOUDY, RAIN, STORM, SNOW, FOG, HEATWAVE)

Agent States:
  IDLE, EXPLORING, INTERACTING, CRAFTING, COMBATING,
  RESTING, TRAVELING, TRADING

Time of Day:
  DAWN, MORNING, AFTERNOON, DUSK, NIGHT, MIDNIGHT

Weather Types:
  CLEAR, CLOUDY, RAIN, STORM, SNOW, FOG, HEATWAVE

Usage:
    ctrl = get_simulation_controller()
    agent = ctrl.create_agent(name="Guardian", personality_profile="guardian")
    ctrl.update_agent_state(agent.agent_id, AgentState.EXPLORING)
    tick = ctrl.simulate_tick()
    ctrl.advance_world_state()
    ctrl.broadcast_event("meteor_strike", {"region": "north"})
    interactions = ctrl.observe_agent_interactions()
    snapshot = ctrl.get_world_snapshot()
    relationships = ctrl.get_agent_relationships(agent.agent_id)
    population = ctrl.spawn_agent_population(count=100)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AgentState(Enum):
    IDLE = "idle"
    EXPLORING = "exploring"
    INTERACTING = "interacting"
    CRAFTING = "crafting"
    COMBATING = "combating"
    RESTING = "resting"
    TRAVELING = "traveling"
    TRADING = "trading"


class TimeOfDay(Enum):
    DAWN = "dawn"
    MORNING = "morning"
    AFTERNOON = "afternoon"
    DUSK = "dusk"
    NIGHT = "night"
    MIDNIGHT = "midnight"


class WeatherType(Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    STORM = "storm"
    SNOW = "snow"
    FOG = "fog"
    HEATWAVE = "heatwave"


PERSONALITY_ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "guardian": {
        "aggression": 0.20,
        "curiosity": 0.40,
        "sociability": 0.55,
        "crafting_affinity": 0.50,
        "exploration_drive": 0.35,
        "combat_proficiency": 0.70,
        "trading_aptitude": 0.45,
        "rest_priority": 0.30,
        "preferred_states": [AgentState.RESTING, AgentState.INTERACTING, AgentState.COMBATING],
        "description": "Protective and loyal, prioritizes defense and community safety.",
    },
    "explorer": {
        "aggression": 0.25,
        "curiosity": 0.95,
        "sociability": 0.50,
        "crafting_affinity": 0.45,
        "exploration_drive": 0.95,
        "combat_proficiency": 0.40,
        "trading_aptitude": 0.35,
        "rest_priority": 0.20,
        "preferred_states": [AgentState.EXPLORING, AgentState.TRAVELING, AgentState.IDLE],
        "description": "Driven by discovery, constantly seeks new frontiers and hidden knowledge.",
    },
    "merchant": {
        "aggression": 0.10,
        "curiosity": 0.55,
        "sociability": 0.85,
        "crafting_affinity": 0.60,
        "exploration_drive": 0.40,
        "combat_proficiency": 0.20,
        "trading_aptitude": 0.95,
        "rest_priority": 0.25,
        "preferred_states": [AgentState.TRADING, AgentState.INTERACTING, AgentState.TRAVELING],
        "description": "Shrewd negotiator focused on commerce, resource accumulation, and networking.",
    },
    "warrior": {
        "aggression": 0.85,
        "curiosity": 0.30,
        "sociability": 0.35,
        "crafting_affinity": 0.40,
        "exploration_drive": 0.45,
        "combat_proficiency": 0.95,
        "trading_aptitude": 0.15,
        "rest_priority": 0.35,
        "preferred_states": [AgentState.COMBATING, AgentState.RESTING, AgentState.TRAVELING],
        "description": "Battle-hardened combatant who thrives in conflict and martial pursuits.",
    },
    "artisan": {
        "aggression": 0.10,
        "curiosity": 0.55,
        "sociability": 0.60,
        "crafting_affinity": 0.95,
        "exploration_drive": 0.30,
        "combat_proficiency": 0.15,
        "trading_aptitude": 0.55,
        "rest_priority": 0.30,
        "preferred_states": [AgentState.CRAFTING, AgentState.TRADING, AgentState.IDLE],
        "description": "Master crafter dedicated to creating items, tools, and structures.",
    },
    "scholar": {
        "aggression": 0.05,
        "curiosity": 0.90,
        "sociability": 0.45,
        "crafting_affinity": 0.55,
        "exploration_drive": 0.60,
        "combat_proficiency": 0.10,
        "trading_aptitude": 0.30,
        "rest_priority": 0.40,
        "preferred_states": [AgentState.IDLE, AgentState.INTERACTING, AgentState.EXPLORING],
        "description": "Knowledge-seeker who studies the world and shares wisdom with others.",
    },
    "scout": {
        "aggression": 0.35,
        "curiosity": 0.80,
        "sociability": 0.40,
        "crafting_affinity": 0.35,
        "exploration_drive": 0.85,
        "combat_proficiency": 0.55,
        "trading_aptitude": 0.25,
        "rest_priority": 0.20,
        "preferred_states": [AgentState.EXPLORING, AgentState.TRAVELING, AgentState.COMBATING],
        "description": "Fast and observant, excels at reconnaissance and pathfinding.",
    },
    "diplomat": {
        "aggression": 0.05,
        "curiosity": 0.60,
        "sociability": 0.95,
        "crafting_affinity": 0.30,
        "exploration_drive": 0.35,
        "combat_proficiency": 0.10,
        "trading_aptitude": 0.75,
        "rest_priority": 0.25,
        "preferred_states": [AgentState.INTERACTING, AgentState.TRADING, AgentState.IDLE],
        "description": "Social nexus who builds relationships, alliances, and resolves conflicts.",
    },
    "hermit": {
        "aggression": 0.30,
        "curiosity": 0.60,
        "sociability": 0.10,
        "crafting_affinity": 0.70,
        "exploration_drive": 0.25,
        "combat_proficiency": 0.45,
        "trading_aptitude": 0.10,
        "rest_priority": 0.50,
        "preferred_states": [AgentState.IDLE, AgentState.CRAFTING, AgentState.RESTING],
        "description": "Solitary figure who prefers isolation and self-sufficiency.",
    },
    "nomad": {
        "aggression": 0.25,
        "curiosity": 0.70,
        "sociability": 0.45,
        "crafting_affinity": 0.50,
        "exploration_drive": 0.75,
        "combat_proficiency": 0.35,
        "trading_aptitude": 0.50,
        "rest_priority": 0.20,
        "preferred_states": [AgentState.TRAVELING, AgentState.EXPLORING, AgentState.TRADING],
        "description": "Wandering soul who moves between regions, never staying in one place for long.",
    },
}

GOAL_TEMPLATES: Dict[str, List[str]] = {
    "survival": [
        "gather_food", "find_shelter", "secure_water_source", "avoid_predators",
        "build_fire", "craft_basic_tools", "tend_wounds", "preserve_rations",
    ],
    "wealth": [
        "accumulate_currency", "invest_in_business", "acquire_rare_items",
        "establish_trade_route", "own_property", "diversify_assets",
        "negotiate_contract", "secure_monopoly",
    ],
    "power": [
        "gain_political_influence", "command_army", "control_territory",
        "forge_alliance", "eliminate_rival", "establish_stronghold",
        "recruit_followers", "seize_authority",
    ],
    "knowledge": [
        "study_ancient_texts", "discover_lost_artifact", "master_skill",
        "unlock_secret", "map_unknown_region", "document_species",
        "decode_language", "experiment_with_alchemy",
    ],
    "social": [
        "build_relationships", "host_gathering", "mediate_conflict",
        "earn_reputation", "mentor_novice", "join_guild",
        "unite_factions", "spread_influence",
    ],
    "crafting": [
        "forge_legendary_weapon", "build_workshop", "master_blueprint",
        "gather_rare_materials", "invent_technique", "complete_commission",
        "teach_apprentice", "perfect_creation",
    ],
}

EVENT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "meteor_strike": {
        "impact_radius": 50.0,
        "resource_deposit": ["star_metal", "crystal_shards", "aether_dust"],
        "terrain_change": "crater",
        "danger_level": 0.8,
        "duration_ticks": 1,
    },
    "trade_caravan_arrival": {
        "impact_radius": 10.0,
        "resource_deposit": ["exotic_goods", "foreign_currency", "rare_spices"],
        "terrain_change": None,
        "danger_level": 0.1,
        "duration_ticks": 5,
    },
    "plague_outbreak": {
        "impact_radius": 100.0,
        "resource_deposit": [],
        "terrain_change": None,
        "danger_level": 0.9,
        "duration_ticks": 20,
    },
    "festival": {
        "impact_radius": 30.0,
        "resource_deposit": ["festival_tokens", "celebratory_items"],
        "terrain_change": None,
        "danger_level": 0.0,
        "duration_ticks": 3,
    },
    "earthquake": {
        "impact_radius": 200.0,
        "resource_deposit": ["exposed_ore", "cracked_stone"],
        "terrain_change": "fissure",
        "danger_level": 0.7,
        "duration_ticks": 1,
    },
    "monster_invasion": {
        "impact_radius": 150.0,
        "resource_deposit": ["monster_parts", "trophies", "rare_drops"],
        "terrain_change": None,
        "danger_level": 0.95,
        "duration_ticks": 10,
    },
    "celestial_alignment": {
        "impact_radius": 500.0,
        "resource_deposit": ["arcane_essence", "starlight_crystal"],
        "terrain_change": None,
        "danger_level": 0.1,
        "duration_ticks": 1,
    },
    "market_crash": {
        "impact_radius": 80.0,
        "resource_deposit": [],
        "terrain_change": None,
        "danger_level": 0.3,
        "duration_ticks": 8,
    },
    "discovery_of_ruins": {
        "impact_radius": 20.0,
        "resource_deposit": ["ancient_relic", "lost_knowledge", "artifact"],
        "terrain_change": None,
        "danger_level": 0.4,
        "duration_ticks": 15,
    },
}

AGENT_NAME_PREFIXES: List[str] = [
    "Ael", "Bran", "Cael", "Dorn", "Eira",
    "Fenn", "Gael", "Hara", "Iris", "Jorn",
    "Kael", "Lira", "Morn", "Nysa", "Orin",
    "Pyrr", "Quin", "Rook", "Sera", "Tarn",
]

AGENT_NAME_SUFFIXES: List[str] = [
    "dras", "wen", "mir", "thas", "lyn",
    "kor", "vale", "reth", "sian", "dorn",
    "fael", "gorn", "hale", "iras", "jinn",
    "keth", "lor", "mar", "nis", "orak",
]


@dataclass
class AutonomousAgent:
    agent_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    personality_profile: str = ""
    current_state: str = "idle"
    goals: List[str] = field(default_factory=list)
    relationships: Dict[str, float] = field(default_factory=dict)
    memories: List[Dict[str, Any]] = field(default_factory=list)
    decision_history: List[Dict[str, Any]] = field(default_factory=list)
    inventory: List[str] = field(default_factory=list)
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "personality_profile": self.personality_profile,
            "current_state": self.current_state,
            "goals": self.goals,
            "relationships": self.relationships,
            "memories": self.memories,
            "decision_history": self.decision_history,
            "inventory": self.inventory,
            "position": list(self.position),
        }


@dataclass
class WorldState:
    world_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    time_of_day: str = "morning"
    weather: str = "clear"
    global_events: List[Dict[str, Any]] = field(default_factory=list)
    agent_population: int = 0
    resource_levels: Dict[str, float] = field(default_factory=dict)
    conflict_level: float = 0.0
    stability_index: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "world_id": self.world_id,
            "time_of_day": self.time_of_day,
            "weather": self.weather,
            "global_events": self.global_events,
            "agent_population": self.agent_population,
            "resource_levels": self.resource_levels,
            "conflict_level": round(self.conflict_level, 3),
            "stability_index": round(self.stability_index, 3),
        }


@dataclass
class SimulationTick:
    tick_number: int = 0
    timestamp: float = 0.0
    events_processed: List[str] = field(default_factory=list)
    agent_decisions: Dict[str, str] = field(default_factory=dict)
    state_changes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick_number": self.tick_number,
            "timestamp": self.timestamp,
            "events_processed": self.events_processed,
            "agent_decisions": self.agent_decisions,
            "state_changes": self.state_changes,
        }


class AgentSimulationController:
    """AI-driven real-time world simulation controller.

    Manages autonomous agent populations within a dynamic world,
    processing simulation ticks, broadcasting events, observing
    emergent interactions, and maintaining world state coherence.
    """

    _instance: Optional["AgentSimulationController"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_AGENTS: int = 10000
    MAX_EVENTS_PER_TICK: int = 100
    MAX_MEMORIES_PER_AGENT: int = 200
    MAX_DECISIONS_PER_AGENT: int = 500
    DEFAULT_TICK_INTERVAL_SECONDS: float = 0.1
    MAX_RELATIONSHIP_VALUE: float = 1.0
    MIN_RELATIONSHIP_VALUE: float = -1.0

    TIME_OF_DAY_CYCLE: List[TimeOfDay] = [
        TimeOfDay.DAWN,
        TimeOfDay.MORNING,
        TimeOfDay.AFTERNOON,
        TimeOfDay.DUSK,
        TimeOfDay.NIGHT,
        TimeOfDay.MIDNIGHT,
    ]

    WEATHER_TRANSITION_MATRIX: Dict[WeatherType, Dict[WeatherType, float]] = {
        WeatherType.CLEAR: {
            WeatherType.CLEAR: 0.60,
            WeatherType.CLOUDY: 0.25,
            WeatherType.RAIN: 0.10,
            WeatherType.FOG: 0.04,
            WeatherType.HEATWAVE: 0.01,
        },
        WeatherType.CLOUDY: {
            WeatherType.CLOUDY: 0.40,
            WeatherType.CLEAR: 0.25,
            WeatherType.RAIN: 0.20,
            WeatherType.STORM: 0.10,
            WeatherType.FOG: 0.05,
        },
        WeatherType.RAIN: {
            WeatherType.RAIN: 0.35,
            WeatherType.CLOUDY: 0.30,
            WeatherType.STORM: 0.20,
            WeatherType.CLEAR: 0.10,
            WeatherType.FOG: 0.05,
        },
        WeatherType.STORM: {
            WeatherType.STORM: 0.25,
            WeatherType.RAIN: 0.35,
            WeatherType.CLOUDY: 0.25,
            WeatherType.CLEAR: 0.10,
            WeatherType.SNOW: 0.05,
        },
        WeatherType.SNOW: {
            WeatherType.SNOW: 0.50,
            WeatherType.CLOUDY: 0.25,
            WeatherType.CLEAR: 0.15,
            WeatherType.STORM: 0.10,
        },
        WeatherType.FOG: {
            WeatherType.FOG: 0.45,
            WeatherType.CLEAR: 0.30,
            WeatherType.CLOUDY: 0.20,
            WeatherType.RAIN: 0.05,
        },
        WeatherType.HEATWAVE: {
            WeatherType.HEATWAVE: 0.40,
            WeatherType.CLEAR: 0.35,
            WeatherType.CLOUDY: 0.20,
            WeatherType.STORM: 0.05,
        },
    }

    BASE_RESOURCE_TYPES: List[str] = [
        "food", "water", "wood", "stone", "iron",
        "gold", "herbs", "cloth", "leather", "mana",
    ]

    def __new__(cls) -> "AgentSimulationController":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentSimulationController":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        _time_module.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._agents: Dict[str, AutonomousAgent] = {}
            self._world_state: Optional[WorldState] = None
            self._tick_history: List[SimulationTick] = []
            self._event_queue: List[Dict[str, Any]] = []
            self._active_events: Dict[str, Dict[str, Any]] = {}
            self._tick_counter: int = 0
            self._total_agents_created: int = 0
            self._total_ticks_processed: int = 0
            self._total_events_broadcast: int = 0
            self._agent_name_registry: Dict[str, str] = {}
            self._initialized = True

    def create_agent(
        self,
        name: str = "",
        personality_profile: str = "guardian",
        starting_state: Optional[AgentState] = None,
        position: Optional[Tuple[float, float, float]] = None,
        initial_goals: Optional[List[str]] = None,
        initial_inventory: Optional[List[str]] = None,
    ) -> AutonomousAgent:
        _time_module.sleep(0.001)
        rng = random.Random()

        if not name:
            name = self._generate_agent_name(rng)
            while name in self._agent_name_registry:
                name = self._generate_agent_name(rng)
        self._agent_name_registry[name] = name

        profile = PERSONALITY_ARCHETYPES.get(
            personality_profile, PERSONALITY_ARCHETYPES["guardian"]
        )

        if starting_state is not None:
            state = starting_state.value
        else:
            preferred = profile.get("preferred_states", [AgentState.IDLE])
            state = rng.choice(preferred).value if preferred else AgentState.IDLE.value

        if initial_goals is None:
            initial_goals = self._generate_goals_for_profile(personality_profile, rng)

        if initial_inventory is None:
            initial_inventory = []

        if position is None:
            position = (
                round(rng.uniform(0, 1000), 2),
                round(rng.uniform(0, 1000), 2),
                round(rng.uniform(0, 100), 2),
            )

        agent = AutonomousAgent(
            agent_id=uuid.uuid4().hex,
            name=name,
            personality_profile=personality_profile,
            current_state=state,
            goals=initial_goals,
            relationships={},
            memories=[],
            decision_history=[],
            inventory=initial_inventory,
            position=position,
        )
        self._agents[agent.agent_id] = agent
        self._total_agents_created += 1

        if self._world_state is not None:
            self._world_state.agent_population = len(self._agents)

        return agent

    def update_agent_state(
        self,
        agent_id: str,
        new_state: AgentState,
        reason: str = "",
    ) -> Optional[AutonomousAgent]:
        _time_module.sleep(0.001)
        agent = self._agents.get(agent_id)
        if agent is None:
            return None

        previous_state = agent.current_state
        agent.current_state = new_state.value

        decision_entry: Dict[str, Any] = {
            "tick": self._tick_counter,
            "timestamp": _time_module.time(),
            "previous_state": previous_state,
            "new_state": new_state.value,
            "reason": reason,
        }
        agent.decision_history.append(decision_entry)

        if len(agent.decision_history) > self.MAX_DECISIONS_PER_AGENT:
            agent.decision_history = agent.decision_history[
                -self.MAX_DECISIONS_PER_AGENT:
            ]

        return agent

    def simulate_tick(self) -> SimulationTick:
        _time_module.sleep(0.001)
        self._tick_counter += 1
        self._total_ticks_processed += 1

        tick_events: List[str] = []
        agent_decisions: Dict[str, str] = {}
        state_changes: Dict[str, str] = {}

        processed_events = self._process_event_queue()
        tick_events.extend(processed_events)

        if self._world_state is not None:
            active_event_ids = list(self._active_events.keys())
            for event_id in active_event_ids:
                event_data = self._active_events.get(event_id)
                if event_data is None:
                    continue
                event_data["remaining_ticks"] = event_data.get("remaining_ticks", 0) - 1
                if event_data["remaining_ticks"] <= 0:
                    self._active_events.pop(event_id, None)
                    tick_events.append(f"event_expired:{event_data.get('event_type', 'unknown')}")

        rng = random.Random()
        agent_ids = list(self._agents.keys())
        rng.shuffle(agent_ids)

        agents_to_decide = agent_ids[: min(500, len(agent_ids))]

        for agent_id in agents_to_decide:
            agent = self._agents.get(agent_id)
            if agent is None:
                continue

            previous_state = agent.current_state
            new_state = self._decide_agent_state(agent, rng)
            agent.current_state = new_state
            state_changes[agent_id] = f"{previous_state}->{new_state}"

            decision_entry: Dict[str, Any] = {
                "tick": self._tick_counter,
                "timestamp": _time_module.time(),
                "previous_state": previous_state,
                "new_state": new_state,
                "reason": "autonomous_decision",
            }
            agent.decision_history.append(decision_entry)
            if len(agent.decision_history) > self.MAX_DECISIONS_PER_AGENT:
                agent.decision_history = agent.decision_history[
                    -self.MAX_DECISIONS_PER_AGENT:
                ]

            agent_decisions[agent_id] = new_state

            self._update_agent_position(agent, rng)

        for agent_id in agents_to_decide:
            agent = self._agents.get(agent_id)
            if agent is None:
                continue
            if agent.current_state == AgentState.INTERACTING.value:
                neighbors = self._find_nearby_agents(agent, rng)
                for neighbor_id in neighbors:
                    current_val = agent.relationships.get(
                        neighbor_id, rng.uniform(-0.1, 0.1)
                    )
                    delta = rng.uniform(-0.05, 0.08)
                    new_val = max(
                        self.MIN_RELATIONSHIP_VALUE,
                        min(self.MAX_RELATIONSHIP_VALUE, current_val + delta),
                    )
                    agent.relationships[neighbor_id] = round(new_val, 4)

        if self._world_state is not None:
            self._update_world_stability()

        tick = SimulationTick(
            tick_number=self._tick_counter,
            timestamp=_time_module.time(),
            events_processed=tick_events,
            agent_decisions=agent_decisions,
            state_changes=state_changes,
        )
        self._tick_history.append(tick)

        if len(self._tick_history) > 10000:
            self._tick_history = self._tick_history[-10000:]

        return tick

    def advance_world_state(self) -> WorldState:
        _time_module.sleep(0.001)
        rng = random.Random()

        if self._world_state is None:
            self._world_state = WorldState(
                world_id=uuid.uuid4().hex,
                time_of_day=TimeOfDay.MORNING.value,
                weather=WeatherType.CLEAR.value,
                global_events=[],
                agent_population=len(self._agents),
                resource_levels=self._generate_initial_resources(rng),
                conflict_level=0.0,
                stability_index=0.5,
            )

        current_tod = self._world_state.time_of_day
        current_weather = self._world_state.weather

        try:
            tod_enum = TimeOfDay(current_tod)
        except ValueError:
            tod_enum = TimeOfDay.MORNING

        cycle = self.TIME_OF_DAY_CYCLE
        current_idx = cycle.index(tod_enum) if tod_enum in cycle else 0
        next_idx = (current_idx + 1) % len(cycle)
        self._world_state.time_of_day = cycle[next_idx].value

        try:
            weather_enum = WeatherType(current_weather)
        except ValueError:
            weather_enum = WeatherType.CLEAR

        transition = self.WEATHER_TRANSITION_MATRIX.get(weather_enum, {})
        if transition:
            weather_keys = list(transition.keys())
            weather_weights = [transition.get(k, 0.0) for k in weather_keys]
            total_weight = sum(weather_weights)
            if total_weight > 0:
                roll = rng.uniform(0, total_weight)
                cumulative = 0.0
                chosen = weather_enum
                for key, weight in zip(weather_keys, weather_weights):
                    cumulative += weight
                    if roll <= cumulative:
                        chosen = key
                        break
                self._world_state.weather = chosen.value

        self._world_state.agent_population = len(self._agents)

        resource_delta = rng.uniform(-0.05, 0.05)
        for resource_key in self._world_state.resource_levels:
            current_val = self._world_state.resource_levels[resource_key]
            self._world_state.resource_levels[resource_key] = round(
                max(0.0, min(1.0, current_val + resource_delta)), 3
            )

        self._update_world_stability()

        return self._world_state

    def broadcast_event(
        self,
        event_type: str,
        event_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        template = EVENT_TEMPLATES.get(event_type, {})
        event_data: Dict[str, Any] = {
            "event_id": uuid.uuid4().hex,
            "event_type": event_type,
            "timestamp": _time_module.time(),
            "tick": self._tick_counter,
            "impact_radius": template.get("impact_radius", 0.0),
            "resource_deposit": list(template.get("resource_deposit", [])),
            "terrain_change": template.get("terrain_change"),
            "danger_level": template.get("danger_level", 0.0),
            "duration_ticks": template.get("duration_ticks", 1),
            "remaining_ticks": template.get("duration_ticks", 1),
            "params": event_params or {},
        }

        self._event_queue.append(event_data)
        self._total_events_broadcast += 1

        if self._world_state is not None:
            self._world_state.global_events.append(
                {
                    "event_id": event_data["event_id"],
                    "event_type": event_type,
                    "tick": event_data["tick"],
                    "danger_level": event_data["danger_level"],
                }
            )
            if len(self._world_state.global_events) > 1000:
                self._world_state.global_events = self._world_state.global_events[-1000:]

        return event_data

    def observe_agent_interactions(self) -> List[Dict[str, Any]]:
        _time_module.sleep(0.001)
        interactions: List[Dict[str, Any]] = []

        agent_list = list(self._agents.values())
        rng = random.Random()

        for agent in agent_list:
            if agent.current_state != AgentState.INTERACTING.value:
                continue

            nearby = self._find_nearby_agents(agent, rng)
            for neighbor_id in nearby:
                neighbor = self._agents.get(neighbor_id)
                if neighbor is None:
                    continue

                interaction_type = self._derive_interaction_type(agent, neighbor, rng)

                interaction: Dict[str, Any] = {
                    "interaction_id": uuid.uuid4().hex,
                    "tick": self._tick_counter,
                    "source_agent_id": agent.agent_id,
                    "target_agent_id": neighbor.agent_id,
                    "source_name": agent.name,
                    "target_name": neighbor.name,
                    "interaction_type": interaction_type,
                    "relationship_value": agent.relationships.get(
                        neighbor.agent_id, 0.0
                    ),
                    "distance": round(
                        math.sqrt(
                            (agent.position[0] - neighbor.position[0]) ** 2
                            + (agent.position[1] - neighbor.position[1]) ** 2
                            + (agent.position[2] - neighbor.position[2]) ** 2
                        ),
                        2,
                    ),
                }
                interactions.append(interaction)

        return interactions

    def get_world_snapshot(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        if self._world_state is None:
            self.advance_world_state()

        ws = self._world_state
        if ws is None:
            return {}

        active_event_types = list(
            set(e.get("event_type", "unknown") for e in self._active_events.values())
        )

        state_distribution: Dict[str, int] = {}
        for agent in self._agents.values():
            s = agent.current_state
            state_distribution[s] = state_distribution.get(s, 0) + 1

        profile_distribution: Dict[str, int] = {}
        for agent in self._agents.values():
            p = agent.personality_profile
            profile_distribution[p] = profile_distribution.get(p, 0) + 1

        avg_relationship_count = 0.0
        if self._agents:
            avg_relationship_count = round(
                sum(len(a.relationships) for a in self._agents.values())
                / len(self._agents),
                2,
            )

        return {
            "world_id": ws.world_id,
            "tick": self._tick_counter,
            "time_of_day": ws.time_of_day,
            "weather": ws.weather,
            "agent_population": ws.agent_population,
            "resource_levels": ws.resource_levels,
            "conflict_level": ws.conflict_level,
            "stability_index": ws.stability_index,
            "active_events": active_event_types,
            "active_event_count": len(self._active_events),
            "queued_event_count": len(self._event_queue),
            "total_agents_created": self._total_agents_created,
            "total_ticks_processed": self._total_ticks_processed,
            "total_events_broadcast": self._total_events_broadcast,
            "state_distribution": state_distribution,
            "profile_distribution": profile_distribution,
            "average_relationship_count": avg_relationship_count,
        }

    def get_agent_relationships(
        self, agent_id: str
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        agent = self._agents.get(agent_id)
        if agent is None:
            return {"error": "agent_not_found", "agent_id": agent_id}

        friends: List[Dict[str, Any]] = []
        foes: List[Dict[str, Any]] = []
        neutrals: List[Dict[str, Any]] = []

        for target_id, value in agent.relationships.items():
            target = self._agents.get(target_id)
            if target is None:
                continue
            entry = {
                "agent_id": target_id,
                "name": target.name,
                "relationship_value": value,
                "personality_profile": target.personality_profile,
                "current_state": target.current_state,
            }
            if value > 0.3:
                friends.append(entry)
            elif value < -0.3:
                foes.append(entry)
            else:
                neutrals.append(entry)

        friends.sort(key=lambda x: x["relationship_value"], reverse=True)
        foes.sort(key=lambda x: x["relationship_value"])

        return {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "total_relationships": len(agent.relationships),
            "friends": friends,
            "foes": foes,
            "neutrals": neutrals,
            "friend_count": len(friends),
            "foe_count": len(foes),
            "neutral_count": len(neutrals),
        }

    def spawn_agent_population(
        self,
        count: int = 100,
        personality_distribution: Optional[Dict[str, float]] = None,
        region_bounds: Optional[Tuple[float, float, float, float]] = None,
    ) -> List[AutonomousAgent]:
        _time_module.sleep(0.001)
        rng = random.Random()

        if personality_distribution is None:
            personality_distribution = {
                "guardian": 0.20,
                "explorer": 0.15,
                "merchant": 0.15,
                "warrior": 0.10,
                "artisan": 0.10,
                "scholar": 0.10,
                "scout": 0.05,
                "diplomat": 0.05,
                "hermit": 0.05,
                "nomad": 0.05,
            }

        max_allowed = self.MAX_AGENTS - len(self._agents)
        actual_count = min(count, max_allowed)
        if actual_count <= 0:
            return []

        spawned: List[AutonomousAgent] = []
        profiles = list(personality_distribution.keys())

        for _ in range(actual_count):
            profile = rng.choices(
                profiles,
                weights=[personality_distribution.get(p, 0.0) for p in profiles],
                k=1,
            )[0]

            if region_bounds is not None:
                x_min, x_max, y_min, y_max = region_bounds
                position: Tuple[float, float, float] = (
                    round(rng.uniform(x_min, x_max), 2),
                    round(rng.uniform(y_min, y_max), 2),
                    round(rng.uniform(0, 100), 2),
                )
            else:
                position = (
                    round(rng.uniform(0, 1000), 2),
                    round(rng.uniform(0, 1000), 2),
                    round(rng.uniform(0, 100), 2),
                )

            agent = self.create_agent(
                name="",
                personality_profile=profile,
                starting_state=None,
                position=position,
            )
            spawned.append(agent)

        for agent_a in spawned:
            num_relationships = rng.randint(2, min(8, len(spawned) - 1))
            candidates = [a for a in spawned if a.agent_id != agent_a.agent_id]
            rng.shuffle(candidates)
            selected = candidates[:num_relationships]

            for agent_b in selected:
                profile_a = PERSONALITY_ARCHETYPES.get(
                    agent_a.personality_profile,
                    PERSONALITY_ARCHETYPES["guardian"],
                )
                profile_b = PERSONALITY_ARCHETYPES.get(
                    agent_b.personality_profile,
                    PERSONALITY_ARCHETYPES["guardian"],
                )
                compat = (
                    (profile_a.get("sociability", 0.5) + profile_b.get("sociability", 0.5))
                    / 2
                    * rng.uniform(0.5, 1.5)
                )
                compat = max(
                    self.MIN_RELATIONSHIP_VALUE,
                    min(self.MAX_RELATIONSHIP_VALUE, compat * 2 - 1),
                )
                agent_a.relationships[agent_b.agent_id] = round(compat, 4)
                agent_b.relationships[agent_a.agent_id] = round(
                    compat * rng.uniform(0.8, 1.2), 4
                )

        if self._world_state is not None:
            self._world_state.agent_population = len(self._agents)

        return spawned

    def _generate_agent_name(self, rng: random.Random) -> str:
        _time_module.sleep(0.001)
        return rng.choice(AGENT_NAME_PREFIXES) + rng.choice(AGENT_NAME_SUFFIXES)

    def _generate_goals_for_profile(
        self, profile: str, rng: random.Random
    ) -> List[str]:
        _time_module.sleep(0.001)
        goal_mapping: Dict[str, List[str]] = {
            "guardian": ["survival", "social"],
            "explorer": ["knowledge", "survival"],
            "merchant": ["wealth", "social"],
            "warrior": ["power", "survival"],
            "artisan": ["crafting", "wealth"],
            "scholar": ["knowledge", "crafting"],
            "scout": ["knowledge", "survival"],
            "diplomat": ["social", "power"],
            "hermit": ["crafting", "survival"],
            "nomad": ["survival", "knowledge"],
        }

        goal_categories = goal_mapping.get(profile, ["survival"])
        goals: List[str] = []
        for category in goal_categories:
            templates = GOAL_TEMPLATES.get(category, [])
            if templates:
                chosen = rng.choice(templates)
                goals.append(chosen)
        return goals

    def _generate_initial_resources(
        self, rng: random.Random
    ) -> Dict[str, float]:
        _time_module.sleep(0.001)
        return {res: round(rng.uniform(0.3, 0.9), 3) for res in self.BASE_RESOURCE_TYPES}

    def _decide_agent_state(
        self, agent: AutonomousAgent, rng: random.Random
    ) -> str:
        _time_module.sleep(0.001)
        profile = PERSONALITY_ARCHETYPES.get(
            agent.personality_profile,
            PERSONALITY_ARCHETYPES["guardian"],
        )

        preferred_states = profile.get("preferred_states", [AgentState.IDLE])

        if rng.random() < 0.7:
            return rng.choice(preferred_states).value

        all_states = list(AgentState)
        return rng.choice(all_states).value

    def _update_agent_position(
        self, agent: AutonomousAgent, rng: random.Random
    ) -> None:
        _time_module.sleep(0.001)
        movement_amount = 0.0

        if agent.current_state == AgentState.EXPLORING.value:
            movement_amount = rng.uniform(1.0, 5.0)
        elif agent.current_state == AgentState.TRAVELING.value:
            movement_amount = rng.uniform(2.0, 8.0)
        elif agent.current_state == AgentState.COMBATING.value:
            movement_amount = rng.uniform(0.5, 3.0)
        else:
            movement_amount = rng.uniform(0.0, 0.5)

        dx = rng.uniform(-1, 1) * movement_amount
        dy = rng.uniform(-1, 1) * movement_amount
        dz = rng.uniform(-0.5, 0.5) * movement_amount

        agent.position = (
            round(max(0.0, min(1000.0, agent.position[0] + dx)), 2),
            round(max(0.0, min(1000.0, agent.position[1] + dy)), 2),
            round(max(0.0, min(100.0, agent.position[2] + dz)), 2),
        )

    def _find_nearby_agents(
        self, agent: AutonomousAgent, rng: random.Random
    ) -> List[str]:
        _time_module.sleep(0.001)
        nearby: List[str] = []
        interaction_radius = 50.0

        for other in self._agents.values():
            if other.agent_id == agent.agent_id:
                continue
            dist = math.sqrt(
                (agent.position[0] - other.position[0]) ** 2
                + (agent.position[1] - other.position[1]) ** 2
                + (agent.position[2] - other.position[2]) ** 2
            )
            if dist <= interaction_radius:
                nearby.append(other.agent_id)

        max_interactions = 10
        if len(nearby) > max_interactions:
            rng.shuffle(nearby)
            nearby = nearby[:max_interactions]

        return nearby

    def _derive_interaction_type(
        self,
        agent_a: AutonomousAgent,
        agent_b: AutonomousAgent,
        rng: random.Random,
    ) -> str:
        _time_module.sleep(0.001)
        relationship = agent_a.relationships.get(agent_b.agent_id, 0.0)

        if relationship > 0.5:
            return rng.choice(["trade", "gift", "share_info", "assist", "celebrate"])
        elif relationship > 0.1:
            return rng.choice(["greet", "trade", "share_info", "chat", "observe"])
        elif relationship < -0.5:
            return rng.choice(["threaten", "attack", "steal", "insult", "flee"])
        elif relationship < -0.1:
            return rng.choice(["avoid", "glare", "warn", "ignore", "mock"])
        return rng.choice(["observe", "greet", "ignore", "wander", "nod"])

    def _process_event_queue(self) -> List[str]:
        _time_module.sleep(0.001)
        processed: List[str] = []
        events_to_process = self._event_queue[: self.MAX_EVENTS_PER_TICK]
        self._event_queue = self._event_queue[self.MAX_EVENTS_PER_TICK :]

        for event_data in events_to_process:
            event_id = event_data.get("event_id", "")
            event_type = event_data.get("event_type", "unknown")
            self._active_events[event_id] = event_data
            processed.append(f"event_activated:{event_type}")

            if self._world_state is not None:
                danger = event_data.get("danger_level", 0.0)
                self._world_state.conflict_level = round(
                    min(1.0, self._world_state.conflict_level + danger * 0.05), 3
                )

        return processed

    def _update_world_stability(self) -> None:
        _time_module.sleep(0.001)
        if self._world_state is None:
            return

        rng = random.Random()
        conflict_factor = self._world_state.conflict_level * 0.4
        resource_avg = 0.0
        if self._world_state.resource_levels:
            resource_avg = sum(self._world_state.resource_levels.values()) / len(
                self._world_state.resource_levels
            )
        resource_factor = resource_avg * 0.3
        population_factor = min(1.0, self._world_state.agent_population / 1000.0) * 0.2
        noise_factor = rng.uniform(-0.05, 0.05)

        stability = 0.5 + resource_factor - conflict_factor - population_factor + noise_factor
        self._world_state.stability_index = round(
            max(0.0, min(1.0, stability)), 3
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_agents": len(self._agents),
            "total_ticks": self._total_ticks_processed,
            "total_events": self._total_events_broadcast,
            "active_worlds": 1 if self._world_state is not None else 0,
            "total_agents_created": self._total_agents_created,
            "total_ticks_processed": self._total_ticks_processed,
            "total_events_broadcast": self._total_events_broadcast,
            "active_events_count": len(self._active_events),
            "state_distribution": self._get_state_distribution(),
            "world_stability": self._world_state.stability_index if self._world_state else 0.0,
            "world_time": self._world_state.time_of_day if self._world_state else "unknown",
        }

    def _get_state_distribution(self) -> Dict[str, int]:
        distribution: Dict[str, int] = {}
        for agent in self._agents.values():
            state = agent.current_state
            distribution[state] = distribution.get(state, 0) + 1
        return distribution

    def list_agents(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._agents.values()]


def get_simulation_controller() -> AgentSimulationController:
    return AgentSimulationController.get_instance()