"""
SparkLabs Agent - Social Simulation Engine

AI-driven social dynamics simulation system for NPC relationship
modeling in game worlds. Constructs emergent social networks between
non-player characters, simulates relationship evolution, generates
context-aware social events, computes influence propagation maps,
predicts faction-level behaviors, and resolves inter-group conflicts
through mediation algorithms.

Architecture:
  AgentSocialSimulation (Singleton)
    |-- SocialRelationship (pairwise NPC relationship data)
    |-- SocialNetwork (complete graph of NPC social ties)
    |-- FactionNode (group identity with membership and goals)
    |-- SocialEvent (emergent event from social dynamics)
    |-- CharacterProfile (NPC personality and social attributes)

Relationship Types:
  FRIEND, FOE, RIVAL, LOVER, MENTOR, STUDENT, NEUTRAL

Event Types:
  BETRAYAL, ALLIANCE, TRADE, CONFLICT, CELEBRATION,
  RECONCILIATION, MENTORSHIP, RUMOR

Faction Templates:
  GUILD, TRIBE, KINGDOM, CABAL, ACADEMY, MERCENARY_BAND,
  REBEL_ALLIANCE, TRADING_CONSORTIUM

Usage:
    sim = get_agent_social_simulation()
    rel = sim.simulate_relationship_pair(profile_a, profile_b)
    network = sim.build_social_network(profiles, faction_nodes={'town': faction})
    event = sim.generate_social_event(network)
    influence = sim.compute_influence_map(network, source_npc_id)
    prediction = sim.predict_faction_behavior(faction, network)
    result = sim.resolve_social_conflict(faction_a, faction_b, network)
    stats = sim.get_stats()
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class RelationshipType(Enum):
    FRIEND = "friend"
    FOE = "foe"
    RIVAL = "rival"
    LOVER = "lover"
    MENTOR = "mentor"
    STUDENT = "student"
    NEUTRAL = "neutral"


class EventType(Enum):
    BETRAYAL = "betrayal"
    ALLIANCE = "alliance"
    TRADE = "trade"
    CONFLICT = "conflict"
    CELEBRATION = "celebration"
    RECONCILIATION = "reconciliation"
    MENTORSHIP = "mentorship"
    RUMOR = "rumor"


class FactionStatus(Enum):
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    HOSTILE = "hostile"
    ISOLATED = "isolated"
    DOMINANT = "dominant"


SOCIAL_TRAIT_ARCHETYPES: Dict[str, Dict[str, float]] = {
    "social_butterfly": {
        "extroversion": 0.90, "agreeableness": 0.75, "loyalty": 0.40, "charisma": 0.85,
    },
    "lone_wolf": {
        "extroversion": 0.15, "agreeableness": 0.30, "loyalty": 0.55, "charisma": 0.35,
    },
    "diplomat": {
        "extroversion": 0.60, "agreeableness": 0.85, "loyalty": 0.65, "charisma": 0.80,
    },
    "schemer": {
        "extroversion": 0.45, "agreeableness": 0.25, "loyalty": 0.15, "charisma": 0.70,
    },
    "guardian": {
        "extroversion": 0.40, "agreeableness": 0.60, "loyalty": 0.95, "charisma": 0.50,
    },
    "charmer": {
        "extroversion": 0.75, "agreeableness": 0.50, "loyalty": 0.30, "charisma": 0.95,
    },
    "sage": {
        "extroversion": 0.35, "agreeableness": 0.70, "loyalty": 0.70, "charisma": 0.55,
    },
    "tyrant": {
        "extroversion": 0.65, "agreeableness": 0.10, "loyalty": 0.25, "charisma": 0.80,
    },
    "idealist": {
        "extroversion": 0.55, "agreeableness": 0.80, "loyalty": 0.80, "charisma": 0.60,
    },
    "mercenary": {
        "extroversion": 0.40, "agreeableness": 0.30, "loyalty": 0.10, "charisma": 0.40,
    },
    "peacekeeper": {
        "extroversion": 0.50, "agreeableness": 0.90, "loyalty": 0.75, "charisma": 0.70,
    },
    "agitator": {
        "extroversion": 0.80, "agreeableness": 0.20, "loyalty": 0.20, "charisma": 0.75,
    },
}

RELATIONSHIP_ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "close_friendship": {
        "types": [RelationshipType.FRIEND.value],
        "strength_range": (0.60, 0.95),
        "trust_range": (0.65, 0.95),
        "compatibility_bonus": 0.20,
    },
    "bitter_enmity": {
        "types": [RelationshipType.FOE.value],
        "strength_range": (0.50, 0.90),
        "trust_range": (0.05, 0.30),
        "compatibility_bonus": -0.30,
    },
    "competitive_rivalry": {
        "types": [RelationshipType.RIVAL.value],
        "strength_range": (0.40, 0.75),
        "trust_range": (0.20, 0.50),
        "compatibility_bonus": -0.10,
    },
    "romantic_bond": {
        "types": [RelationshipType.LOVER.value],
        "strength_range": (0.65, 1.00),
        "trust_range": (0.70, 1.00),
        "compatibility_bonus": 0.25,
    },
    "mentor_protege": {
        "types": [RelationshipType.MENTOR.value, RelationshipType.STUDENT.value],
        "strength_range": (0.45, 0.80),
        "trust_range": (0.50, 0.80),
        "compatibility_bonus": 0.15,
    },
}

FACTION_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "merchants_guild": {
        "name": "Merchants Guild",
        "status": FactionStatus.STABLE.value,
        "reputation": 0.65,
        "territory": "market_district",
        "goals": ["control_trade_routes", "accumulate_wealth", "expand_market_influence"],
        "preferred_relationships": [RelationshipType.FRIEND.value, RelationshipType.NEUTRAL.value],
        "aggression_baseline": 0.15,
        "cooperation_baseline": 0.70,
    },
    "warrior_clan": {
        "name": "Warrior Clan",
        "status": FactionStatus.RISING.value,
        "reputation": 0.55,
        "territory": "highland_fortress",
        "goals": ["defend_homeland", "train_elite_warriors", "establish_military_dominance"],
        "preferred_relationships": [RelationshipType.RIVAL.value, RelationshipType.FOE.value],
        "aggression_baseline": 0.65,
        "cooperation_baseline": 0.25,
    },
    "arcane_academy": {
        "name": "Arcane Academy",
        "status": FactionStatus.STABLE.value,
        "reputation": 0.70,
        "territory": "ivory_spire",
        "goals": ["preserve_knowledge", "train_mages", "research_forbidden_arts"],
        "preferred_relationships": [RelationshipType.MENTOR.value, RelationshipType.STUDENT.value],
        "aggression_baseline": 0.10,
        "cooperation_baseline": 0.55,
    },
    "thieves_cabal": {
        "name": "Thieves Cabal",
        "status": FactionStatus.ISOLATED.value,
        "reputation": 0.20,
        "territory": "undercity_sewers",
        "goals": ["control_black_market", "infiltrate_nobility", "eliminate_rivals"],
        "preferred_relationships": [RelationshipType.NEUTRAL.value],
        "aggression_baseline": 0.50,
        "cooperation_baseline": 0.20,
    },
    "holy_order": {
        "name": "Holy Order",
        "status": FactionStatus.DOMINANT.value,
        "reputation": 0.80,
        "territory": "grand_cathedral",
        "goals": ["spread_faith", "heal_the_sick", "purge_heresy"],
        "preferred_relationships": [RelationshipType.FRIEND.value],
        "aggression_baseline": 0.25,
        "cooperation_baseline": 0.60,
    },
    "rebel_alliance": {
        "name": "Rebel Alliance",
        "status": FactionStatus.RISING.value,
        "reputation": 0.35,
        "territory": "hidden_camp",
        "goals": ["overthrow_tyrant", "liberate_oppressed", "establish_democracy"],
        "preferred_relationships": [RelationshipType.FRIEND.value],
        "aggression_baseline": 0.55,
        "cooperation_baseline": 0.45,
    },
    "nomadic_tribe": {
        "name": "Nomadic Tribe",
        "status": FactionStatus.STABLE.value,
        "reputation": 0.40,
        "territory": "wandering_plains",
        "goals": ["survive_the_season", "find_sacred_grounds", "preserve_oral_traditions"],
        "preferred_relationships": [RelationshipType.NEUTRAL.value, RelationshipType.FRIEND.value],
        "aggression_baseline": 0.20,
        "cooperation_baseline": 0.65,
    },
    "noble_house": {
        "name": "Noble House",
        "status": FactionStatus.DECLINING.value,
        "reputation": 0.50,
        "territory": "ancestral_estate",
        "goals": ["restore_family_honor", "arrange_political_marriages", "secure_legacy"],
        "preferred_relationships": [RelationshipType.FRIEND.value, RelationshipType.RIVAL.value],
        "aggression_baseline": 0.30,
        "cooperation_baseline": 0.50,
    },
}

EVENT_TRIGGER_THRESHOLDS: Dict[str, Dict[str, float]] = {
    EventType.BETRAYAL.value: {"trust_below": 0.25, "strength_above": 0.50, "probability": 0.15},
    EventType.ALLIANCE.value: {"trust_above": 0.55, "strength_above": 0.40, "probability": 0.20},
    EventType.TRADE.value: {"trust_above": 0.30, "strength_above": 0.20, "probability": 0.30},
    EventType.CONFLICT.value: {"trust_below": 0.40, "strength_above": 0.35, "probability": 0.25},
    EventType.CELEBRATION.value: {"trust_above": 0.60, "strength_above": 0.50, "probability": 0.18},
    EventType.RECONCILIATION.value: {"trust_below": 0.35, "strength_above": 0.45, "probability": 0.12},
    EventType.MENTORSHIP.value: {"trust_above": 0.45, "strength_above": 0.30, "probability": 0.22},
    EventType.RUMOR.value: {"trust_below": 0.50, "strength_above": 0.10, "probability": 0.28},
}

BACKSTORY_HOOKS: List[str] = [
    "orphaned_during_the_last_war",
    "raised_by_wolves_in_the_northern_wilds",
    "former_gladiator_who_earned_freedom",
    "disgraced_noble_seeking_redemption",
    "apprentice_to_a_legendary_artisan",
    "sole_survivor_of_a_cursed_expedition",
    "child_of_two_warring_factions",
    "escaped_from_a_secret_laboratory",
    "inherited_a_mysterious_artifact",
    "vowed_to_avenge_a_slaughtered_village",
    "former_pirate_turned_merchant",
    "deserted_from_an_elite_military_unit",
    "raised_in_a_hidden_monastery",
    "won_freedom_through_a_legendary_wager",
    "is_the_seventh_child_of_a_seventh_child",
]

SOCIAL_GOAL_TEMPLATES: List[str] = [
    "gain_political_influence",
    "find_true_love",
    "accumulate_vast_wealth",
    "protect_the_innocent",
    "master_a_forgotten_art",
    "build_a_powerful_faction",
    "seek_revenge_against_a_rival",
    "discover_hidden_knowledge",
    "unite_warring_tribes",
    "escape_a_dark_past",
    "become_a_legendary_hero",
    "maintain_peace_at_all_costs",
    "overthrow_a_corrupt_regime",
    "restore_an_ancient_lineage",
    "achieve_immortality_through_fame",
]


@dataclass
class CharacterProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "UnnamedNPC"
    extroversion: float = 0.50
    agreeableness: float = 0.50
    loyalty: float = 0.50
    charisma: float = 0.50
    archetype: str = "neutral"
    backstory_hook: str = ""
    social_goals: List[str] = field(default_factory=list)
    faction_id: str = ""
    influence_score: float = 0.30
    reputation: float = 0.50
    resource_level: float = 0.30

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "name": self.name,
            "extroversion": round(self.extroversion, 4),
            "agreeableness": round(self.agreeableness, 4),
            "loyalty": round(self.loyalty, 4),
            "charisma": round(self.charisma, 4),
            "archetype": self.archetype,
            "backstory_hook": self.backstory_hook,
            "social_goals": list(self.social_goals),
            "faction_id": self.faction_id,
            "influence_score": round(self.influence_score, 4),
            "reputation": round(self.reputation, 4),
            "resource_level": round(self.resource_level, 4),
        }


@dataclass
class SocialRelationship:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    npc_a_id: str = ""
    npc_b_id: str = ""
    relationship_type: str = RelationshipType.NEUTRAL.value
    strength: float = 0.30
    trust_level: float = 0.30
    history_events: List[str] = field(default_factory=list)
    compatibility_score: float = 0.00
    tension_level: float = 0.00
    duration: float = 0.00
    last_updated: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "npc_a_id": self.npc_a_id,
            "npc_b_id": self.npc_b_id,
            "relationship_type": self.relationship_type,
            "strength": round(self.strength, 4),
            "trust_level": round(self.trust_level, 4),
            "history_events": list(self.history_events),
            "compatibility_score": round(self.compatibility_score, 4),
            "tension_level": round(self.tension_level, 4),
            "duration": round(self.duration, 2),
            "last_updated": self.last_updated,
        }


@dataclass
class FactionNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "UnnamedFaction"
    members: List[str] = field(default_factory=list)
    reputation: float = 0.50
    territory: str = ""
    goals: List[str] = field(default_factory=list)
    status: str = FactionStatus.STABLE.value
    influence_radius: float = 0.30
    resource_pool: float = 0.50
    cohesion: float = 0.50
    aggression_index: float = 0.30
    diplomacy_index: float = 0.50

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "name": self.name,
            "member_count": len(self.members),
            "members": list(self.members),
            "reputation": round(self.reputation, 4),
            "territory": self.territory,
            "goals": list(self.goals),
            "status": self.status,
            "influence_radius": round(self.influence_radius, 4),
            "resource_pool": round(self.resource_pool, 4),
            "cohesion": round(self.cohesion, 4),
            "aggression_index": round(self.aggression_index, 4),
            "diplomacy_index": round(self.diplomacy_index, 4),
        }


@dataclass
class SocialEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = EventType.RUMOR.value
    participants: List[str] = field(default_factory=list)
    impact_scores: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    severity: float = 0.30
    affected_factions: List[str] = field(default_factory=list)
    ripple_effects: List[str] = field(default_factory=list)
    generated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "event_type": self.event_type,
            "participants": list(self.participants),
            "impact_scores": dict(self.impact_scores),
            "description": self.description,
            "severity": round(self.severity, 4),
            "affected_factions": list(self.affected_factions),
            "ripple_effects": list(self.ripple_effects),
            "generated_at": self.generated_at,
        }


@dataclass
class SocialNetwork:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    relationships: Dict[str, SocialRelationship] = field(default_factory=dict)
    factions: Dict[str, FactionNode] = field(default_factory=dict)
    profiles: Dict[str, CharacterProfile] = field(default_factory=dict)
    influence_map: Dict[str, float] = field(default_factory=dict)
    adjacency_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    faction_adjacency: Dict[str, Dict[str, float]] = field(default_factory=dict)
    network_density: float = 0.00
    average_trust: float = 0.00
    conflict_hotspots: List[Tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "id": self.id,
            "relationship_count": len(self.relationships),
            "faction_count": len(self.factions),
            "profile_count": len(self.profiles),
            "influence_map": {k: round(v, 4) for k, v in self.influence_map.items()},
            "network_density": round(self.network_density, 4),
            "average_trust": round(self.average_trust, 4),
            "conflict_hotspot_count": len(self.conflict_hotspots),
            "conflict_hotspots": [
                {"npc_a": a, "npc_b": b} for a, b in self.conflict_hotspots
            ],
        }


class AgentSocialSimulation:
    """
    AI-driven social dynamics simulation engine for NPC relationships.

    Constructs emergent social networks, simulates relationship evolution,
    generates context-aware social events, computes influence propagation,
    predicts faction-level behaviors, and resolves inter-group conflicts.

    Usage:
        sim = get_agent_social_simulation()
        profile_a = sim.create_character_profile(name="Elena", archetype="diplomat")
        profile_b = sim.create_character_profile(name="Marcus", archetype="lone_wolf")
        rel = sim.simulate_relationship_pair(profile_a, profile_b)
        network = sim.build_social_network([profile_a, profile_b])
        event = sim.generate_social_event(network)
        influence = sim.compute_influence_map(network, profile_a.id)
    """

    _instance: Optional["AgentSocialSimulation"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_NETWORK_SIZE = 200
    _INFLUENCE_DECAY_RATE = 0.15
    _TRUST_EVOLUTION_RATE = 0.05
    _STRENGTH_EVOLUTION_RATE = 0.03
    _CONFLICT_ESCALATION_THRESHOLD = 0.65
    _DIPLOMACY_COOLDOWN_STEPS = 3
    _MAX_EVENT_RIPPLE_DEPTH = 4

    def __new__(cls) -> "AgentSocialSimulation":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentSocialSimulation":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._profiles: Dict[str, CharacterProfile] = {}
        self._relationships: Dict[str, SocialRelationship] = {}
        self._factions: Dict[str, FactionNode] = {}
        self._events: List[SocialEvent] = []
        self._networks: List[SocialNetwork] = []
        self._event_history: List[SocialEvent] = []
        self._conflict_log: List[Dict[str, Any]] = []
        self._stats: Dict[str, Any] = {
            "relationships_simulated": 0,
            "networks_built": 0,
            "events_generated": 0,
            "conflicts_resolved": 0,
            "influence_maps_computed": 0,
            "faction_predictions_made": 0,
        }

    def create_character_profile(
        self,
        name: str = "UnnamedNPC",
        archetype: str = "neutral",
        faction_id: str = "",
        backstory_hook: str = "",
        social_goals: Optional[List[str]] = None,
    ) -> CharacterProfile:
        _time_module.sleep(0.001)

        traits = SOCIAL_TRAIT_ARCHETYPES.get(
            archetype,
            {"extroversion": 0.50, "agreeableness": 0.50, "loyalty": 0.50, "charisma": 0.50},
        )

        hook = backstory_hook if backstory_hook else BACKSTORY_HOOKS[
            hash(name + archetype) % len(BACKSTORY_HOOKS)
        ]

        goals = social_goals if social_goals else [
            SOCIAL_GOAL_TEMPLATES[hash(name + str(i)) % len(SOCIAL_GOAL_TEMPLATES)]
            for i in range(2)
        ]

        influence = traits["charisma"] * 0.5 + traits["extroversion"] * 0.3 + traits["agreeableness"] * 0.2
        influence = max(0.05, min(0.95, influence + (hash(name) % 100) / 1000.0))

        profile = CharacterProfile(
            name=name,
            extroversion=traits["extroversion"],
            agreeableness=traits["agreeableness"],
            loyalty=traits["loyalty"],
            charisma=traits["charisma"],
            archetype=archetype,
            backstory_hook=hook,
            social_goals=goals,
            faction_id=faction_id,
            influence_score=round(influence, 4),
            reputation=0.30 + traits["charisma"] * 0.40 + traits["agreeableness"] * 0.20,
        )

        self._profiles[profile.id] = profile

        if faction_id and faction_id in self._factions:
            faction = self._factions[faction_id]
            if profile.id not in faction.members:
                faction.members.append(profile.id)
                self._recompute_faction_cohesion(faction)

        return profile

    def simulate_relationship_pair(
        self,
        profile_a: CharacterProfile,
        profile_b: CharacterProfile,
    ) -> SocialRelationship:
        _time_module.sleep(0.001)

        compatibility = self._compute_compatibility(profile_a, profile_b)
        rel_type = self._determine_relationship_type(profile_a, profile_b, compatibility)

        trust = self._compute_initial_trust(profile_a, profile_b, compatibility)
        strength = self._compute_initial_strength(profile_a, profile_b, compatibility, rel_type)
        tension = 1.0 - (trust * 0.6 + strength * 0.4)
        tension = max(0.0, min(1.0, tension))

        history: List[str] = [f"initial_encounter_{rel_type}"]

        relationship = SocialRelationship(
            npc_a_id=profile_a.id,
            npc_b_id=profile_b.id,
            relationship_type=rel_type,
            strength=strength,
            trust_level=trust,
            history_events=history,
            compatibility_score=compatibility,
            tension_level=round(tension, 4),
        )

        pair_key = self._relationship_key(profile_a.id, profile_b.id)
        self._relationships[pair_key] = relationship
        self._stats["relationships_simulated"] += 1

        return relationship

    def build_social_network(
        self,
        profiles: List[CharacterProfile],
        faction_nodes: Optional[Dict[str, FactionNode]] = None,
    ) -> SocialNetwork:
        _time_module.sleep(0.001)

        network = SocialNetwork()

        for profile in profiles:
            network.profiles[profile.id] = profile

        faction_map: Dict[str, FactionNode] = {}
        if faction_nodes:
            for fid, fnode in faction_nodes.items():
                network.factions[fid] = fnode
                faction_map[fid] = fnode
        else:
            for profile in profiles:
                if profile.faction_id and profile.faction_id not in faction_map:
                    faction = self._factions.get(profile.faction_id)
                    if faction:
                        faction_map[profile.faction_id] = faction
                        network.factions[profile.faction_id] = faction

        profile_ids = list(network.profiles.keys())
        n = len(profile_ids)

        for i in range(n):
            for j in range(i + 1, n):
                pid_a = profile_ids[i]
                pid_b = profile_ids[j]
                pair_key = self._relationship_key(pid_a, pid_b)

                if pair_key in self._relationships:
                    rel = self._relationships[pair_key]
                else:
                    rel = self.simulate_relationship_pair(
                        network.profiles[pid_a], network.profiles[pid_b]
                    )

                network.relationships[pair_key] = rel

        network.adjacency_matrix = self._build_adjacency_matrix(profile_ids, network.relationships)

        influence_scores: Dict[str, float] = {}
        for pid in profile_ids:
            profile = network.profiles[pid]
            influence_scores[pid] = self._compute_raw_influence(pid, profile_ids, network.relationships)
        network.influence_map = influence_scores

        network.faction_adjacency = self._build_faction_adjacency(network)

        edge_count = len(network.relationships)
        max_edges = n * (n - 1) / 2.0
        network.network_density = edge_count / max(max_edges, 1.0)

        trust_sum = sum(r.trust_level for r in network.relationships.values())
        network.average_trust = trust_sum / max(len(network.relationships), 1)

        network.conflict_hotspots = self._detect_conflict_hotspots(network)

        self._stats["networks_built"] += 1
        return network

    def generate_social_event(
        self,
        network: SocialNetwork,
    ) -> Optional[SocialEvent]:
        _time_module.sleep(0.001)

        if not network.relationships:
            return None

        candidate_events: List[Tuple[float, str, SocialRelationship, str]] = []

        for pair_key, rel in network.relationships.items():
            trust = rel.trust_level
            strength = rel.strength

            for evt_type_str, thresholds in EVENT_TRIGGER_THRESHOLDS.items():
                trust_above = thresholds.get("trust_above", 0.0)
                trust_below = thresholds.get("trust_below", 1.0)
                strength_above = thresholds.get("strength_above", 0.0)
                prob = thresholds.get("probability", 0.1)

                condition_met = True
                if trust_above > 0 and trust < trust_above:
                    condition_met = False
                if trust_below < 1.0 and trust > trust_below:
                    condition_met = False
                if strength < strength_above:
                    condition_met = False

                if condition_met:
                    trigger_score = prob * (1.0 + rel.tension_level) * (1.0 + abs(rel.compatibility_score))
                    candidate_events.append((trigger_score, evt_type_str, rel, pair_key))

        if not candidate_events:
            return None

        candidate_events.sort(key=lambda x: x[0], reverse=True)
        max_score = candidate_events[0][0]
        threshold = max_score * 0.6

        top_candidates = [c for c in candidate_events if c[0] >= threshold]
        chosen = top_candidates[hash(str(network.id) + str(candidate_events[0][1])) % len(top_candidates)]

        _, event_type_str, rel, pair_key = chosen

        participants = [rel.npc_a_id, rel.npc_b_id]
        impact_scores = self._compute_event_impacts(event_type_str, rel, network)

        affected_factions: List[str] = []
        for pid in participants:
            profile = network.profiles.get(pid)
            if profile and profile.faction_id:
                if profile.faction_id not in affected_factions:
                    affected_factions.append(profile.faction_id)

        ripple = self._compute_ripple_effects(event_type_str, rel, network)

        description = self._generate_event_description(
            event_type_str, participants, network, rel
        )

        event = SocialEvent(
            event_type=event_type_str,
            participants=participants,
            impact_scores=impact_scores,
            description=description,
            severity=round(max(impact_scores.values()) if impact_scores else 0.3, 4),
            affected_factions=affected_factions,
            ripple_effects=ripple,
        )

        rel.history_events.append(f"{event_type_str}_{event.id[:8]}")
        rel.last_updated = _time_module.time()

        self._events.append(event)
        self._event_history.append(event)
        self._stats["events_generated"] += 1

        self._apply_event_ripple(event, network)

        return event

    def compute_influence_map(
        self,
        network: SocialNetwork,
        source_npc_id: str,
    ) -> Dict[str, float]:
        _time_module.sleep(0.001)

        profile_ids = list(network.profiles.keys())

        if source_npc_id not in network.profiles:
            return {source_npc_id: 0.0}

        distances: Dict[str, float] = {}
        active: List[str] = [source_npc_id]
        distances[source_npc_id] = 0.0

        visited: set = set()

        while active:
            current = active.pop(0)
            if current in visited:
                continue
            visited.add(current)

            current_dist = distances[current]

            for other_id in profile_ids:
                if other_id == current or other_id in visited:
                    continue

                pair_key = self._relationship_key(current, other_id)
                rel = network.relationships.get(pair_key)

                if rel is None:
                    continue

                edge_weight = 1.0 - rel.strength + 0.01
                new_dist = current_dist + edge_weight

                if other_id not in distances or new_dist < distances[other_id]:
                    distances[other_id] = new_dist
                    active.append(other_id)

        source_profile = network.profiles.get(source_npc_id)
        source_influence = source_profile.influence_score if source_profile else 0.3

        influence_map: Dict[str, float] = {}

        for pid in profile_ids:
            dist = distances.get(pid, float("inf"))
            if dist < float("inf"):
                decay = math.exp(-self._INFLUENCE_DECAY_RATE * dist)
                raw_influence = source_influence * decay
            else:
                raw_influence = 0.0
            influence_map[pid] = round(raw_influence, 4)

        influence_map[source_npc_id] = round(source_influence, 4)

        self._stats["influence_maps_computed"] += 1
        return influence_map

    def predict_faction_behavior(
        self,
        faction: FactionNode,
        network: SocialNetwork,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)

        cohesion = self._assess_faction_cohesion(faction, network)
        external_pressure = self._compute_external_pressure(faction, network)
        goal_alignment = self._compute_goal_alignment(faction, network)
        internal_tension = self._compute_internal_tension(faction, network)

        aggression = (
            faction.aggression_index * 0.35
            + external_pressure * 0.30
            + (1.0 - cohesion) * 0.20
            + internal_tension * 0.15
        )
        aggression = max(0.0, min(1.0, aggression))

        diplomacy = (
            faction.diplomacy_index * 0.40
            + cohesion * 0.25
            + goal_alignment * 0.20
            + (1.0 - external_pressure) * 0.15
        )
        diplomacy = max(0.0, min(1.0, diplomacy))

        predicted_actions: List[str] = []

        if aggression > 0.60:
            predicted_actions.append("launch_offensive")
            predicted_actions.append("issue_ultimatum")
        elif aggression > 0.35:
            predicted_actions.append("reinforce_borders")
            predicted_actions.append("recruit_allies")

        if diplomacy > 0.60:
            predicted_actions.append("propose_treaty")
            predicted_actions.append("establish_trade_route")
        elif diplomacy > 0.35:
            predicted_actions.append("send_emissary")
            predicted_actions.append("negotiate_ceasefire")

        if internal_tension > 0.50:
            predicted_actions.append("purge_dissidents")
        if cohesion < 0.40:
            predicted_actions.append("internal_reform")

        if not predicted_actions:
            predicted_actions.append("maintain_status_quo")

        threat_assessment: Dict[str, float] = {}
        for other_fid, other_faction in network.factions.items():
            if other_fid != faction.id:
                threat = self._compute_faction_threat(faction, other_faction, network)
                threat_assessment[other_faction.name] = round(threat, 4)

        self._stats["faction_predictions_made"] += 1

        return {
            "faction_id": faction.id,
            "faction_name": faction.name,
            "predicted_aggression": round(aggression, 4),
            "predicted_diplomacy": round(diplomacy, 4),
            "predicted_actions": predicted_actions,
            "cohesion": round(cohesion, 4),
            "external_pressure": round(external_pressure, 4),
            "goal_alignment": round(goal_alignment, 4),
            "internal_tension": round(internal_tension, 4),
            "threat_assessment": threat_assessment,
        }

    def resolve_social_conflict(
        self,
        faction_a: FactionNode,
        faction_b: FactionNode,
        network: SocialNetwork,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)

        power_a = self._compute_faction_power(faction_a, network)
        power_b = self._compute_faction_power(faction_b, network)

        power_ratio = power_a / max(power_b, 0.01)

        negotiation_strength_a = power_a * faction_a.diplomacy_index
        negotiation_strength_b = power_b * faction_b.diplomacy_index

        resolution_pressure = (
            (1.0 - power_ratio if power_ratio < 1.0 else 1.0 / power_ratio)
            * (faction_a.diplomacy_index + faction_b.diplomacy_index) / 2.0
        )
        resolution_pressure = max(0.1, min(1.0, resolution_pressure))

        outcomes: Dict[str, float] = {
            "ceasefire": resolution_pressure * 0.8 + (1.0 - max(faction_a.aggression_index, faction_b.aggression_index)) * 0.2,
            "negotiated_settlement": resolution_pressure * 0.85,
            "stalemate": 0.5 + (1.0 - resolution_pressure) * 0.3,
            "escalation": max(faction_a.aggression_index, faction_b.aggression_index) * (1.0 - resolution_pressure * 0.5),
            "one_sided_victory": max(power_a, power_b) / (power_a + power_b + 0.01) * (1.0 - resolution_pressure * 0.3),
        }

        best_outcome = max(outcomes, key=lambda k: outcomes[k])

        mediation_bonus = 0.0
        mediator_candidates: List[str] = []
        for fid, fnode in network.factions.items():
            if fid != faction_a.id and fid != faction_b.id:
                if fnode.diplomacy_index > 0.6 and fnode.cohesion > 0.5:
                    mediator_candidates.append(fid)
                    mediation_bonus += fnode.diplomacy_index * 0.1

        mediation_bonus = min(0.3, mediation_bonus)
        if mediator_candidates:
            outcomes["negotiated_settlement"] += mediation_bonus
            outcomes["ceasefire"] += mediation_bonus * 0.7
            outcomes["escalation"] -= mediation_bonus * 0.3

        reputation_impact_a = 0.0
        reputation_impact_b = 0.0

        if best_outcome in ("ceasefire", "negotiated_settlement"):
            reputation_impact_a = 0.05
            reputation_impact_b = 0.05
        elif best_outcome == "stalemate":
            reputation_impact_a = -0.02
            reputation_impact_b = -0.02
        elif best_outcome == "escalation":
            reputation_impact_a = -0.10
            reputation_impact_b = -0.10
        elif best_outcome == "one_sided_victory":
            if power_a > power_b:
                reputation_impact_a = 0.08
                reputation_impact_b = -0.15
            else:
                reputation_impact_a = -0.15
                reputation_impact_b = 0.08

        faction_a.reputation = max(0.0, min(1.0, faction_a.reputation + reputation_impact_a))
        faction_b.reputation = max(0.0, min(1.0, faction_b.reputation + reputation_impact_b))

        conflict_record = {
            "faction_a": faction_a.name,
            "faction_b": faction_b.name,
            "power_a": round(power_a, 4),
            "power_b": round(power_b, 4),
            "outcome": best_outcome,
            "outcome_probabilities": {k: round(v, 4) for k, v in outcomes.items()},
            "mediators": mediator_candidates,
            "resolution_pressure": round(resolution_pressure, 4),
            "resolved_at": _time_module.time(),
        }
        self._conflict_log.append(conflict_record)
        self._stats["conflicts_resolved"] += 1

        return conflict_record

    def list_characters(self) -> List[Dict[str, Any]]:
        """Return all character profiles as dicts."""
        _time_module.sleep(0.001)
        return [p.to_dict() for p in self._character_profiles.values()]

    def list_relationships(self) -> List[Dict[str, Any]]:
        """Return all relationships as dicts."""
        _time_module.sleep(0.001)
        return [r.to_dict() for r in self._relationships.values()]

    def get_network_summary(self) -> Dict[str, Any]:
        """Return a summary of the current social network state."""
        _time_module.sleep(0.001)
        return {
            "character_count": len(self._character_profiles),
            "relationship_count": len(self._relationships),
            "faction_count": len(self._factions),
            "event_count": len(self._event_history),
            "network_density": self._network_density if hasattr(self, '_network_density') else 0.0,
            "average_trust": self._average_trust if hasattr(self, '_average_trust') else 0.0,
            "factions": [f.to_dict() for f in self._factions.values()],
        }

    def list_events(self) -> List[Dict[str, Any]]:
        """Return all social events as dicts."""
        _time_module.sleep(0.001)
        return [e.to_dict() for e in self._event_history]

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "relationships_simulated": self._stats["relationships_simulated"],
            "networks_built": self._stats["networks_built"],
            "events_generated": self._stats["events_generated"],
            "conflicts_resolved": self._stats["conflicts_resolved"],
            "influence_maps_computed": self._stats["influence_maps_computed"],
            "faction_predictions_made": self._stats["faction_predictions_made"],
            "profiles_registered": len(self._profiles),
            "factions_registered": len(self._factions),
            "active_relationships": len(self._relationships),
            "event_history_size": len(self._event_history),
            "conflict_log_size": len(self._conflict_log),
            "available_archetypes": list(SOCIAL_TRAIT_ARCHETYPES.keys()),
            "available_relationship_archetypes": list(RELATIONSHIP_ARCHETYPES.keys()),
            "available_faction_templates": list(FACTION_TEMPLATES.keys()),
            "available_event_types": [e.value for e in EventType],
            "available_relationship_types": [r.value for r in RelationshipType],
        }

    def reset(self) -> None:
        _time_module.sleep(0.001)
        self._profiles.clear()
        self._relationships.clear()
        self._factions.clear()
        self._events.clear()
        self._event_history.clear()
        self._conflict_log.clear()
        self._stats = {
            "relationships_simulated": 0,
            "networks_built": 0,
            "events_generated": 0,
            "conflicts_resolved": 0,
            "influence_maps_computed": 0,
            "faction_predictions_made": 0,
        }

    def register_faction(self, faction: FactionNode) -> None:
        _time_module.sleep(0.001)
        self._factions[faction.id] = faction

    def create_faction_from_template(
        self,
        template_key: str,
        custom_name: Optional[str] = None,
    ) -> Optional[FactionNode]:
        _time_module.sleep(0.001)
        template = FACTION_TEMPLATES.get(template_key)
        if template is None:
            return None

        faction = FactionNode(
            name=custom_name if custom_name else template["name"],
            reputation=template["reputation"],
            territory=template.get("territory", ""),
            goals=list(template.get("goals", [])),
            status=template.get("status", FactionStatus.STABLE.value),
            aggression_index=template.get("aggression_baseline", 0.30),
            diplomacy_index=template.get("cooperation_baseline", 0.50),
        )

        self._factions[faction.id] = faction
        return faction

    def evolve_relationship(
        self,
        relationship: SocialRelationship,
        profile_a: CharacterProfile,
        profile_b: CharacterProfile,
        steps: int = 1,
    ) -> SocialRelationship:
        _time_module.sleep(0.001)

        for _ in range(steps):
            compat = relationship.compatibility_score

            trust_delta = (
                (profile_a.agreeableness + profile_b.agreeableness) / 2.0 * self._TRUST_EVOLUTION_RATE
                + compat * self._TRUST_EVOLUTION_RATE * 0.5
                - relationship.tension_level * self._TRUST_EVOLUTION_RATE * 0.3
            )
            relationship.trust_level = max(0.01, min(0.99, relationship.trust_level + trust_delta))

            strength_delta = (
                (relationship.trust_level * 0.4 + abs(compat) * 0.3 + 0.15) * self._STRENGTH_EVOLUTION_RATE
            )
            relationship.strength = max(0.01, min(1.0, relationship.strength + strength_delta))

            relationship.tension_level = max(0.0, min(1.0,
                1.0 - (relationship.trust_level * 0.55 + relationship.strength * 0.45)
            ))

            relationship.duration += 1.0
            relationship.last_updated = _time_module.time()

            self._maybe_shift_relationship_type(relationship)

        return relationship

    def get_faction_relationships(
        self,
        faction_a: FactionNode,
        faction_b: FactionNode,
        network: SocialNetwork,
    ) -> List[SocialRelationship]:
        _time_module.sleep(0.001)
        results: List[SocialRelationship] = []

        for pair_key, rel in network.relationships.items():
            a_in_faction = rel.npc_a_id in faction_a.members or rel.npc_b_id in faction_a.members
            b_in_faction = rel.npc_a_id in faction_b.members or rel.npc_b_id in faction_b.members
            if a_in_faction and b_in_faction:
                results.append(rel)

        return results

    def compute_faction_influence(
        self,
        faction: FactionNode,
        network: SocialNetwork,
    ) -> float:
        _time_module.sleep(0.001)

        if not faction.members:
            return 0.0

        total_influence = 0.0
        for member_id in faction.members:
            influence_map = self.compute_influence_map(network, member_id)
            avg_influence = sum(influence_map.values()) / max(len(influence_map), 1)
            total_influence += avg_influence

        return round(total_influence / len(faction.members), 4)

    def get_event_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        _time_module.sleep(0.001)
        results = list(self._event_history)
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        return [e.to_dict() for e in results[-limit:]]

    def get_conflict_log(
        self,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        _time_module.sleep(0.001)
        return list(self._conflict_log[-limit:])

    def _compute_compatibility(
        self,
        profile_a: CharacterProfile,
        profile_b: CharacterProfile,
    ) -> float:
        _time_module.sleep(0.001)

        extro_diff = 1.0 - abs(profile_a.extroversion - profile_b.extroversion)
        agree_sum = (profile_a.agreeableness + profile_b.agreeableness) / 2.0
        loyalty_sum = (profile_a.loyalty + profile_b.loyalty) / 2.0

        charisma_boost = max(profile_a.charisma, profile_b.charisma) * 0.15

        goal_overlap = len(
            set(profile_a.social_goals) & set(profile_b.social_goals)
        ) / max(len(set(profile_a.social_goals) | set(profile_b.social_goals)), 1)

        compatibility = (
            extro_diff * 0.25
            + agree_sum * 0.25
            + loyalty_sum * 0.20
            + charisma_boost * 0.15
            + goal_overlap * 0.15
        )

        same_faction_bonus = 0.10 if profile_a.faction_id and profile_a.faction_id == profile_b.faction_id else 0.0

        return max(-1.0, min(1.0, compatibility + same_faction_bonus - 0.30))

    def _determine_relationship_type(
        self,
        profile_a: CharacterProfile,
        profile_b: CharacterProfile,
        compatibility: float,
    ) -> str:
        _time_module.sleep(0.001)

        if compatibility > 0.55:
            loyalty_avg = (profile_a.loyalty + profile_b.loyalty) / 2.0
            charisma_avg = (profile_a.charisma + profile_b.charisma) / 2.0

            if charisma_avg > 0.70 and loyalty_avg < 0.45:
                return RelationshipType.LOVER.value
            elif loyalty_avg > 0.65:
                return RelationshipType.FRIEND.value
            elif profile_a.extroversion > profile_b.extroversion + 0.3:
                return RelationshipType.MENTOR.value
            elif profile_b.extroversion > profile_a.extroversion + 0.3:
                return RelationshipType.STUDENT.value
            else:
                return RelationshipType.FRIEND.value

        elif compatibility < -0.15:
            if profile_a.agreeableness < 0.30 or profile_b.agreeableness < 0.30:
                return RelationshipType.FOE.value
            else:
                return RelationshipType.RIVAL.value

        else:
            return RelationshipType.NEUTRAL.value

    def _compute_initial_trust(
        self,
        profile_a: CharacterProfile,
        profile_b: CharacterProfile,
        compatibility: float,
    ) -> float:
        _time_module.sleep(0.001)

        agree_avg = (profile_a.agreeableness + profile_b.agreeableness) / 2.0
        loyalty_avg = (profile_a.loyalty + profile_b.loyalty) / 2.0
        raw_trust = agree_avg * 0.40 + loyalty_avg * 0.40 + (compatibility + 1.0) / 2.0 * 0.20
        return round(max(0.05, min(0.95, raw_trust)), 4)

    def _compute_initial_strength(
        self,
        profile_a: CharacterProfile,
        profile_b: CharacterProfile,
        compatibility: float,
        rel_type: str,
    ) -> float:
        _time_module.sleep(0.001)

        extro_avg = (profile_a.extroversion + profile_b.extroversion) / 2.0
        base_strength = extro_avg * 0.30 + abs(compatibility) * 0.50 + 0.20

        type_multipliers = {
            RelationshipType.LOVER.value: 1.30,
            RelationshipType.FRIEND.value: 1.10,
            RelationshipType.FOE.value: 1.05,
            RelationshipType.RIVAL.value: 1.15,
            RelationshipType.MENTOR.value: 1.10,
            RelationshipType.STUDENT.value: 1.10,
            RelationshipType.NEUTRAL.value: 0.60,
        }
        multiplier = type_multipliers.get(rel_type, 0.80)

        return round(max(0.05, min(0.95, base_strength * multiplier)), 4)

    def _build_adjacency_matrix(
        self,
        profile_ids: List[str],
        relationships: Dict[str, SocialRelationship],
    ) -> Dict[str, Dict[str, float]]:
        _time_module.sleep(0.001)

        matrix: Dict[str, Dict[str, float]] = {}
        for pid in profile_ids:
            matrix[pid] = {}
            for other_pid in profile_ids:
                if pid == other_pid:
                    matrix[pid][other_pid] = 1.0
                else:
                    pair_key = self._relationship_key(pid, other_pid)
                    rel = relationships.get(pair_key)
                    matrix[pid][other_pid] = rel.strength if rel else 0.0

        return matrix

    def _build_faction_adjacency(
        self,
        network: SocialNetwork,
    ) -> Dict[str, Dict[str, float]]:
        _time_module.sleep(0.001)

        matrix: Dict[str, Dict[str, float]] = {}
        faction_ids = list(network.factions.keys())

        for fid_a in faction_ids:
            matrix[fid_a] = {}
            for fid_b in faction_ids:
                if fid_a == fid_b:
                    matrix[fid_a][fid_b] = 1.0
                    continue

                faction_rels = self.get_faction_relationships(
                    network.factions[fid_a], network.factions[fid_b], network
                )

                if faction_rels:
                    avg_strength = sum(r.strength for r in faction_rels) / len(faction_rels)
                    avg_trust = sum(r.trust_level for r in faction_rels) / len(faction_rels)
                    matrix[fid_a][fid_b] = round((avg_strength + avg_trust) / 2.0, 4)
                else:
                    matrix[fid_a][fid_b] = 0.0

        return matrix

    def _compute_raw_influence(
        self,
        source_pid: str,
        all_profile_ids: List[str],
        relationships: Dict[str, SocialRelationship],
    ) -> float:
        _time_module.sleep(0.001)

        total = 0.0
        count = 0

        for other_pid in all_profile_ids:
            if other_pid == source_pid:
                continue
            pair_key = self._relationship_key(source_pid, other_pid)
            rel = relationships.get(pair_key)
            if rel:
                total += rel.strength
                count += 1

        avg_connection = total / max(count, 1)
        return round(avg_connection * 0.7 + 0.15, 4)

    def _detect_conflict_hotspots(
        self,
        network: SocialNetwork,
    ) -> List[Tuple[str, str]]:
        _time_module.sleep(0.001)

        hotspots: List[Tuple[str, str]] = []

        for pair_key, rel in network.relationships.items():
            conflict_score = rel.tension_level * (1.0 + rel.strength) * (1.0 - rel.trust_level)
            if conflict_score > self._CONFLICT_ESCALATION_THRESHOLD:
                hotspots.append((rel.npc_a_id, rel.npc_b_id))

        hotspots.sort(
            key=lambda h: network.relationships.get(
                self._relationship_key(h[0], h[1]),
                SocialRelationship()
            ).tension_level,
            reverse=True,
        )

        return hotspots[:20]

    def _compute_event_impacts(
        self,
        event_type: str,
        rel: SocialRelationship,
        network: SocialNetwork,
    ) -> Dict[str, float]:
        _time_module.sleep(0.001)

        impacts: Dict[str, float] = {}

        impacts[rel.npc_a_id] = self._event_impact_on_npc(event_type, rel.npc_a_id, network)
        impacts[rel.npc_b_id] = self._event_impact_on_npc(event_type, rel.npc_b_id, network)

        return impacts

    def _event_impact_on_npc(
        self,
        event_type: str,
        npc_id: str,
        network: SocialNetwork,
    ) -> float:
        _time_module.sleep(0.001)

        profile = network.profiles.get(npc_id)
        base_impact = 0.25

        positive_events = {EventType.CELEBRATION.value, EventType.ALLIANCE.value,
                           EventType.RECONCILIATION.value, EventType.MENTORSHIP.value,
                           EventType.TRADE.value}
        negative_events = {EventType.BETRAYAL.value, EventType.CONFLICT.value}

        if event_type in positive_events:
            if profile is not None:
                base_impact = 0.30 + profile.agreeableness * 0.25 + profile.charisma * 0.15
        elif event_type in negative_events:
            agree = profile.agreeableness if profile is not None else 0.5
            base_impact = 0.35 + (1.0 - agree) * 0.30

        if event_type == EventType.RUMOR.value:
            chr_val = profile.charisma if profile is not None else 0.5
            base_impact = 0.15 + chr_val * 0.10

        return round(max(0.05, min(1.0, base_impact)), 4)

    def _compute_ripple_effects(
        self,
        event_type: str,
        rel: SocialRelationship,
        network: SocialNetwork,
    ) -> List[str]:
        _time_module.sleep(0.001)

        ripple: List[str] = []

        affected = {rel.npc_a_id, rel.npc_b_id}

        for other_pair, other_rel in network.relationships.items():
            if other_pair == self._relationship_key(rel.npc_a_id, rel.npc_b_id):
                continue
            if other_rel.npc_a_id in affected or other_rel.npc_b_id in affected:
                if other_rel.strength > 0.40:
                    ripple.append(f"affects_relationship_{other_rel.id[:8]}")

        return ripple[:self._MAX_EVENT_RIPPLE_DEPTH]

    def _generate_event_description(
        self,
        event_type: str,
        participants: List[str],
        network: SocialNetwork,
        rel: SocialRelationship,
    ) -> str:
        _time_module.sleep(0.001)

        name_a = network.profiles.get(participants[0], CharacterProfile(name="Unknown")).name
        name_b = network.profiles.get(participants[1], CharacterProfile(name="Unknown")).name if len(participants) > 1 else ""

        descriptions: Dict[str, str] = {
            EventType.BETRAYAL.value: f"{name_a} betrayed the trust of {name_b}; their bond is shattered by treachery",
            EventType.ALLIANCE.value: f"{name_a} and {name_b} forged a powerful alliance, shifting the balance of power",
            EventType.TRADE.value: f"{name_a} and {name_b} engaged in a significant exchange of resources and information",
            EventType.CONFLICT.value: f"Open conflict erupted between {name_a} and {name_b}, drawing in their allies",
            EventType.CELEBRATION.value: f"{name_a} and {name_b} celebrated a shared triumph, strengthening their bond",
            EventType.RECONCILIATION.value: f"{name_a} and {name_b} reconciled their differences through earnest dialogue",
            EventType.MENTORSHIP.value: f"{name_a} took {name_b} under their wing, beginning a mentorship journey",
            EventType.RUMOR.value: f"A rumor about {name_a} and {name_b} spread through the social network like wildfire",
        }

        return descriptions.get(event_type, f"Social event between {name_a} and {name_b}")

    def _apply_event_ripple(
        self,
        event: SocialEvent,
        network: SocialNetwork,
    ) -> None:
        _time_module.sleep(0.001)

        for pair_key, rel in network.relationships.items():
            if rel.npc_a_id in event.participants or rel.npc_b_id in event.participants:
                if not (rel.npc_a_id in event.participants and rel.npc_b_id in event.participants):
                    ripple_factor = rel.strength * 0.15

                    if event.event_type in (EventType.ALLIANCE.value, EventType.CELEBRATION.value):
                        rel.trust_level = min(0.99, rel.trust_level + ripple_factor * 0.3)
                    elif event.event_type in (EventType.BETRAYAL.value, EventType.CONFLICT.value):
                        rel.trust_level = max(0.01, rel.trust_level - ripple_factor * 0.3)
                        rel.tension_level = min(1.0, rel.tension_level + ripple_factor * 0.2)

    def _assess_faction_cohesion(
        self,
        faction: FactionNode,
        network: SocialNetwork,
    ) -> float:
        _time_module.sleep(0.001)

        if len(faction.members) < 2:
            return 0.5 if faction.members else 0.0

        strengths: List[float] = []
        trust_vals: List[float] = []

        for i, m_a in enumerate(faction.members):
            for m_b in faction.members[i + 1:]:
                pair_key = self._relationship_key(m_a, m_b)
                rel = network.relationships.get(pair_key)
                if rel:
                    strengths.append(rel.strength)
                    trust_vals.append(rel.trust_level)

        avg_strength = sum(strengths) / len(strengths) if strengths else 0.3
        avg_trust = sum(trust_vals) / len(trust_vals) if trust_vals else 0.3
        faction.cohesion = round((avg_strength * 0.5 + avg_trust * 0.5), 4)

        return faction.cohesion

    def _recompute_faction_cohesion(self, faction: FactionNode) -> None:
        _time_module.sleep(0.001)

        if len(faction.members) < 2:
            faction.cohesion = 0.5
            return

        strengths: List[float] = []
        trust_vals: List[float] = []

        for i, m_a in enumerate(faction.members):
            for m_b in faction.members[i + 1:]:
                pair_key = self._relationship_key(m_a, m_b)
                rel = self._relationships.get(pair_key)
                if rel:
                    strengths.append(rel.strength)
                    trust_vals.append(rel.trust_level)

        avg_strength = sum(strengths) / len(strengths) if strengths else 0.3
        avg_trust = sum(trust_vals) / len(trust_vals) if trust_vals else 0.3
        faction.cohesion = round((avg_strength * 0.5 + avg_trust * 0.5), 4)

    def _compute_external_pressure(
        self,
        faction: FactionNode,
        network: SocialNetwork,
    ) -> float:
        _time_module.sleep(0.001)

        total_pressure = 0.0
        opposing_faction_count = 0

        for other_fid, other_faction in network.factions.items():
            if other_fid == faction.id:
                continue

            adj = network.faction_adjacency.get(faction.id, {}).get(other_fid, 0.0)

            if other_faction.aggression_index > 0.5 and adj < 0.3:
                total_pressure += other_faction.aggression_index * (1.0 - adj)
                opposing_faction_count += 1
            elif adj < 0.2:
                total_pressure += (1.0 - adj) * other_faction.aggression_index * 0.5
                opposing_faction_count += 1

        if opposing_faction_count == 0:
            return max(0.0, 0.1 - faction.cohesion * 0.1)

        return round(max(0.0, min(1.0, total_pressure / max(opposing_faction_count, 1))), 4)

    def _compute_goal_alignment(
        self,
        faction: FactionNode,
        network: SocialNetwork,
    ) -> float:
        _time_module.sleep(0.001)

        total_alignment = 0.0
        comparisons = 0

        for other_fid, other_faction in network.factions.items():
            if other_fid == faction.id:
                continue

            shared_goals = len(
                set(faction.goals) & set(other_faction.goals)
            )
            total_possible = max(
                len(set(faction.goals) | set(other_faction.goals)), 1
            )
            alignment = shared_goals / total_possible
            total_alignment += alignment
            comparisons += 1

        if comparisons == 0:
            return 0.5

        return round(total_alignment / comparisons, 4)

    def _compute_internal_tension(
        self,
        faction: FactionNode,
        network: SocialNetwork,
    ) -> float:
        _time_module.sleep(0.001)

        if len(faction.members) < 2:
            return 0.1

        tensions: List[float] = []
        for i, m_a in enumerate(faction.members):
            for m_b in faction.members[i + 1:]:
                pair_key = self._relationship_key(m_a, m_b)
                rel = network.relationships.get(pair_key)
                if rel:
                    tensions.append(rel.tension_level)

        return round(sum(tensions) / len(tensions), 4) if tensions else 0.2

    def _compute_faction_threat(
        self,
        faction_a: FactionNode,
        faction_b: FactionNode,
        network: SocialNetwork,
    ) -> float:
        _time_module.sleep(0.001)

        power_b = self._compute_faction_power(faction_b, network)
        power_a = self._compute_faction_power(faction_a, network)

        adjacency = network.faction_adjacency.get(faction_a.id, {}).get(faction_b.id, 0.0)

        aggression_factor = faction_b.aggression_index

        threat = (
            (power_b / max(power_a + power_b, 0.01)) * 0.40
            + aggression_factor * 0.35
            + (1.0 - adjacency) * 0.25
        )

        return round(max(0.0, min(1.0, threat)), 4)

    def _compute_faction_power(
        self,
        faction: FactionNode,
        network: SocialNetwork,
    ) -> float:
        _time_module.sleep(0.001)

        member_power = len(faction.members) / max(1, self._MAX_NETWORK_SIZE)
        resource_power = faction.resource_pool
        cohesion_power = faction.cohesion
        influence_power = faction.influence_radius

        power = (
            member_power * 0.30
            + resource_power * 0.25
            + cohesion_power * 0.25
            + influence_power * 0.20
        )

        return round(max(0.01, min(1.0, power)), 4)

    def _maybe_shift_relationship_type(
        self,
        rel: SocialRelationship,
    ) -> None:
        _time_module.sleep(0.001)

        if rel.trust_level > 0.75 and rel.strength > 0.60:
            if rel.relationship_type in (RelationshipType.NEUTRAL.value, RelationshipType.RIVAL.value):
                rel.relationship_type = RelationshipType.FRIEND.value

        if rel.trust_level < 0.20 and rel.strength > 0.45:
            if rel.relationship_type == RelationshipType.NEUTRAL.value:
                rel.relationship_type = RelationshipType.FOE.value

    @staticmethod
    def _relationship_key(pid_a: str, pid_b: str) -> str:
        if pid_a < pid_b:
            return f"{pid_a}__{pid_b}"
        return f"{pid_b}__{pid_a}"


def get_agent_social_simulation() -> AgentSocialSimulation:
    return AgentSocialSimulation.get_instance()