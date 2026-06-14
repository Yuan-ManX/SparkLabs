"""
Agent Social Relationship - Social relationship graph for AI agents.
Models dynamic social networks, relationship evolution, reputation,
and social influence between game characters and NPCs.
"""

import threading
import uuid
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any


class RelationshipType(Enum):
    """Types of social relationships between agents."""
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    BEST_FRIEND = "best_friend"
    ALLY = "ally"
    RIVAL = "rival"
    ENEMY = "enemy"
    FAMILY = "family"
    ROMANTIC = "romantic"
    MENTOR = "mentor"
    STUDENT = "student"


class SocialAction(Enum):
    """Social actions that affect relationships."""
    GREET = "greet"
    HELP = "help"
    GIFT = "gift"
    COMPLIMENT = "compliment"
    INSULT = "insult"
    BETRAY = "betray"
    IGNORE = "ignore"
    SHARE = "share"
    COMPETE = "compete"
    COOPERATE = "cooperate"


@dataclass
class Relationship:
    """A directed relationship between two agents."""
    relationship_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_id: str = ""
    target_id: str = ""
    relationship_type: RelationshipType = RelationshipType.STRANGER
    affinity: float = 0.0
    trust: float = 0.0
    respect: float = 0.0
    familiarity: float = 0.0
    interaction_count: int = 0
    last_interaction: float = 0.0
    shared_experiences: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type.value,
            "affinity": self.affinity,
            "trust": self.trust,
            "respect": self.respect,
            "familiarity": self.familiarity,
            "interaction_count": self.interaction_count,
            "last_interaction": self.last_interaction,
            "tags": self.tags,
        }


@dataclass
class SocialGroup:
    """A social group or faction."""
    group_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    members: Set[str] = field(default_factory=set)
    leader_id: str = ""
    cohesion: float = 0.5
    influence: float = 0.5
    rival_groups: Set[str] = field(default_factory=set)
    allied_groups: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "name": self.name,
            "members": list(self.members),
            "leader_id": self.leader_id,
            "cohesion": self.cohesion,
            "influence": self.influence,
            "rival_groups": list(self.rival_groups),
            "allied_groups": list(self.allied_groups),
        }


@dataclass
class Reputation:
    """Reputation of an agent in the social network."""
    agent_id: str = ""
    overall_reputation: float = 0.0
    trait_reputations: Dict[str, float] = field(default_factory=lambda: {
        "bravery": 0.0, "honesty": 0.0, "generosity": 0.0,
        "cruelty": 0.0, "wisdom": 0.0, "loyalty": 0.0,
    })
    reputation_sources: Dict[str, float] = field(default_factory=dict)
    rumor_spread: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "overall_reputation": self.overall_reputation,
            "trait_reputations": self.trait_reputations,
            "reputation_sources": self.reputation_sources,
            "rumor_spread": self.rumor_spread,
        }


class AgentSocialRelationship:
    """
    Social relationship graph system for AI agents.
    Models dynamic social networks, relationship evolution,
    reputation propagation, and group dynamics.
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._relationships: Dict[str, Relationship] = {}
            self._reputations: Dict[str, Reputation] = {}
            self._social_groups: Dict[str, SocialGroup] = {}
            self._interaction_history: Dict[str, List[Dict[str, Any]]] = {}
            self._social_network: Dict[str, Set[str]] = {}
            self._action_effects: Dict[SocialAction, Dict[str, float]] = self._init_action_effects()
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'AgentSocialRelationship':
        return cls()

    def _init_action_effects(self) -> Dict[SocialAction, Dict[str, float]]:
        """Initialize the effects of social actions on relationships."""
        return {
            SocialAction.GREET: {"affinity": 0.02, "familiarity": 0.05},
            SocialAction.HELP: {"affinity": 0.15, "trust": 0.1, "respect": 0.05},
            SocialAction.GIFT: {"affinity": 0.2, "trust": 0.05},
            SocialAction.COMPLIMENT: {"affinity": 0.08, "respect": 0.02},
            SocialAction.INSULT: {"affinity": -0.15, "respect": -0.1},
            SocialAction.BETRAY: {"affinity": -0.5, "trust": -0.4},
            SocialAction.IGNORE: {"affinity": -0.03, "familiarity": -0.02},
            SocialAction.SHARE: {"affinity": 0.1, "trust": 0.08},
            SocialAction.COMPETE: {"affinity": -0.05, "respect": 0.05},
            SocialAction.COOPERATE: {"affinity": 0.12, "trust": 0.1, "respect": 0.03},
        }

    def register_agent(self, agent_id: str):
        """Register an agent in the social network."""
        if agent_id not in self._social_network:
            self._social_network[agent_id] = set()
        if agent_id not in self._reputations:
            self._reputations[agent_id] = Reputation(agent_id=agent_id)

    def create_relationship(self, source_id: str, target_id: str,
                            initial_type: RelationshipType = RelationshipType.STRANGER) -> Relationship:
        """Create a relationship between two agents."""
        self.register_agent(source_id)
        self.register_agent(target_id)

        rel = Relationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=initial_type,
        )
        self._relationships[rel.relationship_id] = rel
        self._social_network[source_id].add(target_id)
        self._social_network[target_id].add(source_id)
        return rel

    def process_interaction(self, source_id: str, target_id: str,
                            action: SocialAction, context: Dict[str, Any] = None) -> Relationship:
        """Process a social interaction between two agents."""
        rel = self.get_relationship(source_id, target_id)
        if not rel:
            rel = self.create_relationship(source_id, target_id)

        effects = self._action_effects.get(action, {})
        rel.affinity = max(-1.0, min(1.0, rel.affinity + effects.get("affinity", 0.0)))
        rel.trust = max(-1.0, min(1.0, rel.trust + effects.get("trust", 0.0)))
        rel.respect = max(-1.0, min(1.0, rel.respect + effects.get("respect", 0.0)))
        rel.familiarity = max(0.0, min(1.0, rel.familiarity + effects.get("familiarity", 0.0)))
        rel.interaction_count += 1
        rel.last_interaction = _time_module.time()

        if context:
            rel.shared_experiences.append({
                "action": action.value,
                "context": context,
                "timestamp": _time_module.time(),
            })

        self._update_relationship_type(rel)
        self._update_reputation(source_id, target_id, action)
        self._propagate_rumor(source_id, target_id, action)

        self._interaction_history.setdefault(source_id, []).append({
            "target": target_id,
            "action": action.value,
            "timestamp": _time_module.time(),
        })

        return rel

    def _update_relationship_type(self, rel: Relationship):
        """Update relationship type based on affinity and interaction metrics."""
        score = rel.affinity * 0.4 + rel.trust * 0.3 + rel.familiarity * 0.2 + rel.respect * 0.1

        if score > 0.8:
            rel.relationship_type = RelationshipType.BEST_FRIEND
        elif score > 0.6:
            rel.relationship_type = RelationshipType.CLOSE_FRIEND
        elif score > 0.4:
            rel.relationship_type = RelationshipType.FRIEND
        elif score > 0.2:
            rel.relationship_type = RelationshipType.ALLY
        elif score > 0.05:
            rel.relationship_type = RelationshipType.ACQUAINTANCE
        elif score > -0.2:
            rel.relationship_type = RelationshipType.STRANGER
        elif score > -0.5:
            rel.relationship_type = RelationshipType.RIVAL
        else:
            rel.relationship_type = RelationshipType.ENEMY

    def _update_reputation(self, source_id: str, target_id: str, action: SocialAction):
        """Update reputation based on social actions."""
        rep = self._reputations.get(source_id)
        if not rep:
            return

        trait_effects = {
            SocialAction.HELP: {"generosity": 0.05, "loyalty": 0.03},
            SocialAction.BETRAY: {"honesty": -0.1, "loyalty": -0.15},
            SocialAction.INSULT: {"honesty": 0.02, "cruelty": 0.05},
            SocialAction.COMPLIMENT: {"generosity": 0.02},
            SocialAction.COOPERATE: {"loyalty": 0.04, "wisdom": 0.02},
            SocialAction.COMPETE: {"bravery": 0.03},
        }

        effects = trait_effects.get(action, {})
        for trait, delta in effects.items():
            if trait in rep.trait_reputations:
                rep.trait_reputations[trait] = max(-1.0, min(1.0, rep.trait_reputations[trait] + delta))

        rep.overall_reputation = sum(rep.trait_reputations.values()) / len(rep.trait_reputations)

    def _propagate_rumor(self, source_id: str, target_id: str, action: SocialAction):
        """Propagate information about actions through the social network."""
        connections = self._social_network.get(source_id, set())
        rumor_spread = 0.0

        significant_actions = {SocialAction.HELP, SocialAction.BETRAY, SocialAction.INSULT, SocialAction.GIFT}
        if action in significant_actions:
            rumor_spread = 0.3
            for conn_id in connections:
                if conn_id != target_id:
                    conn_rep = self._reputations.get(conn_id)
                    if conn_rep:
                        conn_rep.rumor_spread = min(1.0, conn_rep.rumor_spread + 0.01)

    def create_social_group(self, name: str, leader_id: str,
                            members: List[str] = None) -> SocialGroup:
        """Create a social group or faction."""
        group = SocialGroup(name=name, leader_id=leader_id)
        if members:
            group.members.update(members)
        group.members.add(leader_id)
        self._social_groups[group.group_id] = group
        return group

    def add_to_group(self, group_id: str, agent_id: str):
        """Add an agent to a social group."""
        group = self._social_groups.get(group_id)
        if group:
            group.members.add(agent_id)
            self.register_agent(agent_id)

    def set_group_relation(self, group_a: str, group_b: str, relation: str):
        """Set relationship between two groups."""
        ga = self._social_groups.get(group_a)
        gb = self._social_groups.get(group_b)
        if not ga or not gb:
            return

        if relation == "rival":
            ga.rival_groups.add(group_b)
            gb.rival_groups.add(group_a)
        elif relation == "ally":
            ga.allied_groups.add(group_b)
            gb.allied_groups.add(group_a)

    def get_relationship(self, source_id: str, target_id: str) -> Optional[Relationship]:
        """Get the relationship between two agents."""
        for rel in self._relationships.values():
            if rel.source_id == source_id and rel.target_id == target_id:
                return rel
        return None

    def get_relationships(self, agent_id: str) -> List[Relationship]:
        """Get all relationships for an agent."""
        return [rel for rel in self._relationships.values()
                if rel.source_id == agent_id or rel.target_id == agent_id]

    def get_reputation(self, agent_id: str) -> Optional[Reputation]:
        """Get the reputation of an agent."""
        return self._reputations.get(agent_id)

    def get_social_network(self, agent_id: str, depth: int = 1) -> Dict[str, Any]:
        """Get the social network around an agent up to specified depth."""
        visited: Set[str] = set()
        network: Dict[str, List[str]] = {}

        def explore(current: str, current_depth: int):
            if current_depth > depth or current in visited:
                return
            visited.add(current)
            connections = self._social_network.get(current, set())
            network[current] = list(connections)
            for conn in connections:
                explore(conn, current_depth + 1)

        explore(agent_id, 0)
        return {"agent_id": agent_id, "network": network, "depth": depth}

    def get_group(self, group_id: str) -> Optional[SocialGroup]:
        """Get a social group by ID."""
        return self._social_groups.get(group_id)

    def list_groups(self) -> List[SocialGroup]:
        """List all social groups."""
        return list(self._social_groups.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get social relationship system statistics."""
        return {
            "total_agents": len(self._social_network),
            "total_relationships": len(self._relationships),
            "total_groups": len(self._social_groups),
            "total_interactions": sum(len(h) for h in self._interaction_history.values()),
            "relationship_distribution": self._get_relationship_distribution(),
            "avg_network_density": self._calculate_network_density(),
        }

    def _get_relationship_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for rel in self._relationships.values():
            rt = rel.relationship_type.value
            dist[rt] = dist.get(rt, 0) + 1
        return dist

    def _calculate_network_density(self) -> float:
        if len(self._social_network) < 2:
            return 0.0
        total_edges = sum(len(conns) for conns in self._social_network.values())
        max_edges = len(self._social_network) * (len(self._social_network) - 1)
        return total_edges / max(max_edges, 1)


def get_social_relationship() -> AgentSocialRelationship:
    return AgentSocialRelationship.get_instance()