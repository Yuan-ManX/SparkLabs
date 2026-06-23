"""
SparkLabs Agent - Social Cognition System

A social cognition system that models how agents understand and interact
with other agents in a social environment. Includes theory of mind for
modeling others' beliefs, relationship graphs for tracking social bonds,
reputation systems for agent credibility, social norm reasoning, and
coalition formation dynamics.

Architecture:
  SocialCognitionSystem (Singleton)
    |-- TheoryOfMind (modeling other agents' beliefs and intentions)
    |-- RelationshipGraph (social relationship tracking)
    |-- ReputationSystem (agent credibility and trust)
    |-- SocialNormEngine (norm reasoning and compliance)
    |-- AllianceFormation (coalition dynamics)
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class RelationshipType(Enum):
    """Types of social relationships between agents."""
    ALLY = "ally"
    FRIEND = "friend"
    ACQUAINTANCE = "acquaintance"
    NEUTRAL = "neutral"
    RIVAL = "rival"
    ENEMY = "enemy"
    MENTOR = "mentor"
    STUDENT = "student"
    SUPERIOR = "superior"
    SUBORDINATE = "subordinate"


class TrustLevel(Enum):
    """Level of trust in another agent."""
    DISTRUST = "distrust"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    COMPLETE = "complete"


class ReputationCategory(Enum):
    """Categories of reputation."""
    RELIABILITY = "reliability"
    COMPETENCE = "competence"
    HONESTY = "honesty"
    COOPERATION = "cooperation"
    AGGRESSION = "aggression"
    GENEROSITY = "generosity"
    FAIRNESS = "fairness"


class NormType(Enum):
    """Types of social norms."""
    PROHIBITION = "prohibition"
    OBLIGATION = "obligation"
    PERMISSION = "permission"
    CONVENTION = "convention"
    ETIQUETTE = "etiquette"


class AllianceType(Enum):
    """Types of alliances between agents."""
    DEFENSIVE = "defensive"
    OFFENSIVE = "offensive"
    ECONOMIC = "economic"
    KNOWLEDGE = "knowledge"
    TEMPORARY = "temporary"
    STRATEGIC = "strategic"


@dataclass
class BeliefModel:
    """A model of another agent's belief about a proposition."""
    belief_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    subject_id: str = ""
    proposition: str = ""
    believed_value: Any = None
    confidence: float = 0.5
    evidence: List[str] = field(default_factory=list)
    updated_at: float = field(default_factory=_time_module.time)
    source: str = "observation"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "belief_id": self.belief_id,
            "subject_id": self.subject_id,
            "proposition": self.proposition,
            "believed_value": self.believed_value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "updated_at": self.updated_at,
            "source": self.source,
        }


@dataclass
class IntentionModel:
    """A model of another agent's intention."""
    intention_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    subject_id: str = ""
    goal: str = ""
    priority: float = 0.5
    likelihood: float = 0.5
    expected_duration: float = 0.0
    inferred_from: List[str] = field(default_factory=list)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intention_id": self.intention_id,
            "subject_id": self.subject_id,
            "goal": self.goal,
            "priority": self.priority,
            "likelihood": self.likelihood,
            "expected_duration": self.expected_duration,
            "inferred_from": self.inferred_from,
            "updated_at": self.updated_at,
        }


class TheoryOfMind:
    """
    Models other agents' mental states including beliefs, intentions,
    and desires. Enables agents to reason about what others know,
    want, and plan to do.
    """

    def __init__(self) -> None:
        self._beliefs: Dict[str, Dict[str, BeliefModel]] = {}
        self._intentions: Dict[str, List[IntentionModel]] = {}
        self._lock = threading.RLock()

    def model_belief(self, subject_id: str, proposition: str,
                     believed_value: Any, confidence: float = 0.5,
                     evidence: Optional[List[str]] = None) -> BeliefModel:
        """Record or update a model of another agent's belief."""
        with self._lock:
            belief = BeliefModel(
                subject_id=subject_id,
                proposition=proposition,
                believed_value=believed_value,
                confidence=confidence,
                evidence=evidence or [],
            )
            if subject_id not in self._beliefs:
                self._beliefs[subject_id] = {}
            self._beliefs[subject_id][belief.belief_id] = belief
            return belief

    def get_beliefs(self, subject_id: str) -> List[BeliefModel]:
        with self._lock:
            return list(self._beliefs.get(subject_id, {}).values())

    def get_belief(self, subject_id: str, proposition: str) -> Optional[BeliefModel]:
        with self._lock:
            beliefs = self._beliefs.get(subject_id, {})
            for b in beliefs.values():
                if b.proposition == proposition:
                    return b
            return None

    def infer_intention(self, subject_id: str, goal: str,
                        likelihood: float = 0.5,
                        inferred_from: Optional[List[str]] = None) -> IntentionModel:
        """Record an inferred intention of another agent."""
        with self._lock:
            intention = IntentionModel(
                subject_id=subject_id,
                goal=goal,
                likelihood=likelihood,
                inferred_from=inferred_from or [],
            )
            if subject_id not in self._intentions:
                self._intentions[subject_id] = []
            self._intentions[subject_id].append(intention)
            return intention

    def get_intentions(self, subject_id: str) -> List[IntentionModel]:
        with self._lock:
            return self._intentions.get(subject_id, [])

    def predict_action(self, subject_id: str) -> Optional[str]:
        """Predict the most likely action another agent will take."""
        intentions = self.get_intentions(subject_id)
        if not intentions:
            return None
        best = max(intentions, key=lambda i: i.likelihood * i.priority)
        return best.goal

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "modeled_agents": list(self._beliefs.keys()),
                "total_beliefs": sum(len(b) for b in self._beliefs.values()),
                "total_intentions": sum(len(i) for i in self._intentions.values()),
            }


@dataclass
class Relationship:
    """A social relationship between two agents."""
    relationship_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_a: str = ""
    agent_b: str = ""
    relationship_type: RelationshipType = RelationshipType.NEUTRAL
    strength: float = 0.5
    trust: TrustLevel = TrustLevel.MODERATE
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    last_interaction: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "relationship_type": self.relationship_type.value,
            "strength": self.strength,
            "trust": self.trust.value,
            "history_count": len(self.history),
            "created_at": self.created_at,
            "last_interaction": self.last_interaction,
            "metadata": self.metadata,
        }


class RelationshipGraph:
    """
    Tracks social relationships between agents.
    Maintains an undirected graph of relationships with strength
    and trust metrics.
    """

    def __init__(self) -> None:
        self._relationships: Dict[str, Relationship] = {}
        self._adjacency: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()

    def set_relationship(
        self,
        agent_a: str,
        agent_b: str,
        relationship_type: RelationshipType,
        strength: float = 0.5,
        trust: TrustLevel = TrustLevel.MODERATE,
    ) -> Relationship:
        """Set or update a relationship between two agents."""
        with self._lock:
            key = self._make_key(agent_a, agent_b)
            if key in self._relationships:
                rel = self._relationships[key]
                rel.relationship_type = relationship_type
                rel.strength = strength
                rel.trust = trust
                rel.last_interaction = _time_module.time()
            else:
                rel = Relationship(
                    agent_a=agent_a,
                    agent_b=agent_b,
                    relationship_type=relationship_type,
                    strength=strength,
                    trust=trust,
                )
                self._relationships[key] = rel
                if agent_a not in self._adjacency:
                    self._adjacency[agent_a] = set()
                if agent_b not in self._adjacency:
                    self._adjacency[agent_b] = set()
                self._adjacency[agent_a].add(agent_b)
                self._adjacency[agent_b].add(agent_a)
            return rel

    def get_relationship(self, agent_a: str, agent_b: str) -> Optional[Relationship]:
        with self._lock:
            return self._relationships.get(self._make_key(agent_a, agent_b))

    def get_connections(self, agent_id: str) -> List[str]:
        with self._lock:
            return list(self._adjacency.get(agent_id, set()))

    def get_allies(self, agent_id: str) -> List[str]:
        with self._lock:
            allies: List[str] = []
            for neighbor in self._adjacency.get(agent_id, set()):
                rel = self._relationships.get(self._make_key(agent_id, neighbor))
                if rel and rel.relationship_type in (RelationshipType.ALLY, RelationshipType.FRIEND):
                    allies.append(neighbor)
            return allies

    def record_interaction(self, agent_a: str, agent_b: str,
                            interaction: Dict[str, Any]) -> None:
        with self._lock:
            rel = self.get_relationship(agent_a, agent_b)
            if rel:
                rel.history.append(interaction)
                rel.last_interaction = _time_module.time()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "relationship_count": len(self._relationships),
                "agent_count": len(self._adjacency),
                "relationships": [r.to_dict() for r in self._relationships.values()],
            }

    @staticmethod
    def _make_key(a: str, b: str) -> str:
        return "|".join(sorted([a, b]))


@dataclass
class ReputationProfile:
    """Reputation profile for an agent."""
    agent_id: str = ""
    scores: Dict[ReputationCategory, float] = field(default_factory=dict)
    testimonials: int = 0
    last_updated: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "scores": {c.value: s for c, s in self.scores.items()},
            "testimonials": self.testimonials,
            "last_updated": self.last_updated,
        }

    def overall_standing(self) -> float:
        if not self.scores:
            return 0.5
        return sum(self.scores.values()) / len(self.scores)


class ReputationSystem:
    """
    Tracks agent reputation across multiple dimensions.
    Accumulates testimonials from interactions and provides
    aggregate standing scores.
    """

    def __init__(self) -> None:
        self._profiles: Dict[str, ReputationProfile] = {}
        self._lock = threading.RLock()

    def get_profile(self, agent_id: str) -> ReputationProfile:
        with self._lock:
            if agent_id not in self._profiles:
                self._profiles[agent_id] = ReputationProfile(agent_id=agent_id)
            return self._profiles[agent_id]

    def update_reputation(
        self,
        agent_id: str,
        category: ReputationCategory,
        score: float,
    ) -> None:
        """Update an agent's reputation score in a category."""
        with self._lock:
            profile = self.get_profile(agent_id)
            if category in profile.scores:
                profile.scores[category] = (
                    profile.scores[category] * 0.7 + score * 0.3
                )
            else:
                profile.scores[category] = score
            profile.testimonials += 1
            profile.last_updated = _time_module.time()

    def get_standing(self, agent_id: str) -> float:
        with self._lock:
            return self.get_profile(agent_id).overall_standing()

    def compare(self, agent_a: str, agent_b: str) -> float:
        """Compare reputation between two agents (positive = a has better rep)."""
        return self.get_standing(agent_a) - self.get_standing(agent_b)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "profiled_agents": len(self._profiles),
                "profiles": [p.to_dict() for p in self._profiles.values()],
            }


@dataclass
class SocialNorm:
    """A social norm that governs behavior."""
    norm_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    norm_type: NormType = NormType.CONVENTION
    condition: str = ""
    expected_behavior: str = ""
    violation_penalty: float = 0.1
    compliance_benefit: float = 0.05
    salience: float = 0.5
    domain: str = "general"
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "norm_id": self.norm_id,
            "name": self.name,
            "description": self.description,
            "norm_type": self.norm_type.value,
            "condition": self.condition,
            "expected_behavior": self.expected_behavior,
            "violation_penalty": self.violation_penalty,
            "compliance_benefit": self.compliance_benefit,
            "salience": self.salience,
            "domain": self.domain,
            "created_at": self.created_at,
        }


class SocialNormEngine:
    """
    Manages social norms and evaluates behavior compliance.
    Provides norm reasoning to determine whether actions align
    with expected social standards.
    """

    def __init__(self) -> None:
        self._norms: Dict[str, SocialNorm] = {}
        self._violation_log: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def define_norm(
        self,
        name: str,
        description: str = "",
        norm_type: str = "convention",
        condition: str = "",
        expected_behavior: str = "",
        violation_penalty: float = 0.1,
        domain: str = "general",
    ) -> SocialNorm:
        """Define a new social norm."""
        with self._lock:
            norm = SocialNorm(
                name=name,
                description=description,
                norm_type=NormType(norm_type),
                condition=condition,
                expected_behavior=expected_behavior,
                violation_penalty=violation_penalty,
                domain=domain,
            )
            self._norms[norm.norm_id] = norm
            return norm

    def evaluate(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate whether an action complies with known norms."""
        with self._lock:
            violations: List[Dict[str, Any]] = []
            compliances: List[Dict[str, Any]] = []

            for norm in self._norms.values():
                if norm.condition and norm.condition.lower() in context.get("situation", "").lower():
                    if norm.expected_behavior.lower() in action.lower():
                        compliances.append({"norm": norm.name, "benefit": norm.compliance_benefit})
                    else:
                        violations.append({"norm": norm.name, "penalty": norm.violation_penalty})
                        self._violation_log.append({
                            "norm_id": norm.norm_id,
                            "action": action,
                            "timestamp": _time_module.time(),
                        })

            total_penalty = sum(v["penalty"] for v in violations)
            total_benefit = sum(c["benefit"] for c in compliances)
            return {
                "compliant": len(violations) == 0,
                "violations": violations,
                "compliances": compliances,
                "total_penalty": total_penalty,
                "total_benefit": total_benefit,
                "score": max(0.0, 1.0 - total_penalty + total_benefit),
            }

    def get_norms_by_domain(self, domain: str) -> List[SocialNorm]:
        with self._lock:
            return [n for n in self._norms.values() if n.domain == domain]

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "norm_count": len(self._norms),
                "violation_count": len(self._violation_log),
                "norms": [n.to_dict() for n in self._norms.values()],
            }


@dataclass
class Alliance:
    """A coalition of agents formed for a shared purpose."""
    alliance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    alliance_type: AllianceType = AllianceType.STRATEGIC
    members: List[str] = field(default_factory=list)
    leader_id: str = ""
    strength: float = 0.5
    cohesion: float = 0.5
    shared_goal: str = ""
    formed_at: float = field(default_factory=_time_module.time)
    dissolved_at: Optional[float] = None
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alliance_id": self.alliance_id,
            "name": self.name,
            "alliance_type": self.alliance_type.value,
            "members": self.members,
            "leader_id": self.leader_id,
            "strength": self.strength,
            "cohesion": self.cohesion,
            "shared_goal": self.shared_goal,
            "formed_at": self.formed_at,
            "dissolved_at": self.dissolved_at,
            "active": self.active,
            "member_count": len(self.members),
        }


class AllianceFormation:
    """
    Manages coalition formation and dissolution.
    Models how agents form alliances based on shared goals,
    relationship strength, and mutual benefit.
    """

    def __init__(self) -> None:
        self._alliances: Dict[str, Alliance] = {}
        self._agent_alliances: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()

    def form_alliance(
        self,
        name: str,
        members: List[str],
        alliance_type: str = "strategic",
        leader_id: str = "",
        shared_goal: str = "",
    ) -> Alliance:
        """Form a new alliance."""
        with self._lock:
            alliance = Alliance(
                name=name,
                alliance_type=AllianceType(alliance_type),
                members=members,
                leader_id=leader_id or (members[0] if members else ""),
                shared_goal=shared_goal,
            )
            self._alliances[alliance.alliance_id] = alliance
            for member in members:
                if member not in self._agent_alliances:
                    self._agent_alliances[member] = set()
                self._agent_alliances[member].add(alliance.alliance_id)
            return alliance

    def dissolve_alliance(self, alliance_id: str) -> bool:
        with self._lock:
            alliance = self._alliances.get(alliance_id)
            if not alliance or not alliance.active:
                return False
            alliance.active = False
            alliance.dissolved_at = _time_module.time()
            for member in alliance.members:
                if member in self._agent_alliances:
                    self._agent_alliances[member].discard(alliance_id)
            return True

    def get_alliance(self, alliance_id: str) -> Optional[Alliance]:
        with self._lock:
            return self._alliances.get(alliance_id)

    def get_agent_alliances(self, agent_id: str) -> List[Alliance]:
        with self._lock:
            alliance_ids = self._agent_alliances.get(agent_id, set())
            return [self._alliances[aid] for aid in alliance_ids if aid in self._alliances]

    def get_alliance_members(self, alliance_id: str) -> List[str]:
        with self._lock:
            alliance = self._alliances.get(alliance_id)
            return alliance.members if alliance else []

    def propose_alliance(
        self,
        name: str,
        proposer: str,
        targets: List[str],
        relationship_graph: RelationshipGraph,
        min_relationship_strength: float = 0.3,
    ) -> Optional[Alliance]:
        """Propose an alliance based on existing relationships."""
        with self._lock:
            viable = []
            for target in targets:
                rel = relationship_graph.get_relationship(proposer, target)
                if rel and rel.strength >= min_relationship_strength:
                    viable.append(target)
            if len(viable) < 2:
                return None
            return self.form_alliance(
                name=name,
                members=[proposer] + viable,
                leader_id=proposer,
            )

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "alliance_count": len(self._alliances),
                "active_count": sum(1 for a in self._alliances.values() if a.active),
                "alliances": [a.to_dict() for a in self._alliances.values()],
            }


class SocialCognitionSystem:
    """
    Social cognition system for AI agents.

    Models how agents understand and interact with others through
    theory of mind, relationship tracking, reputation management,
    social norm reasoning, and coalition formation.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._theory_of_mind = TheoryOfMind()
        self._relationship_graph = RelationshipGraph()
        self._reputation_system = ReputationSystem()
        self._norm_engine = SocialNormEngine()
        self._alliance_formation = AllianceFormation()

    @classmethod
    def get_instance(cls) -> "SocialCognitionSystem":
        return cls()

    @property
    def theory_of_mind(self) -> TheoryOfMind:
        return self._theory_of_mind

    @property
    def relationships(self) -> RelationshipGraph:
        return self._relationship_graph

    @property
    def reputation(self) -> ReputationSystem:
        return self._reputation_system

    @property
    def norms(self) -> SocialNormEngine:
        return self._norm_engine

    @property
    def alliances(self) -> AllianceFormation:
        return self._alliance_formation

    def assess_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get a comprehensive social assessment of an agent."""
        with self._lock:
            standing = self._reputation_system.get_standing(agent_id)
            connections = self._relationships.get_connections(agent_id)
            alliances = self._alliance_formation.get_agent_alliances(agent_id)
            beliefs = self._theory_of_mind.get_beliefs(agent_id)
            return {
                "agent_id": agent_id,
                "reputation_standing": standing,
                "connection_count": len(connections),
                "alliance_count": len(alliances),
                "believed_propositions": len(beliefs),
                "profile": self._reputation_system.get_profile(agent_id).to_dict(),
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "theory_of_mind": self._theory_of_mind.to_dict(),
                "relationships": self._relationship_graph.to_dict(),
                "reputation": self._reputation_system.to_dict(),
                "norms": self._norm_engine.to_dict(),
                "alliances": self._alliance_formation.to_dict(),
            }


_global_social_cognition: Optional[SocialCognitionSystem] = None


def get_social_cognition() -> SocialCognitionSystem:
    global _global_social_cognition
    if _global_social_cognition is None:
        _global_social_cognition = SocialCognitionSystem()
    return _global_social_cognition