"""
SparkLabs Agent - Social Dynamics Engine

Sociodynamic simulation engine for autonomous agent populations.
Models personality-driven interactions, emotional states, relationship
networks, and emergent social behavior in game worlds.

Architecture:
  AgentSocialDynamics (Singleton)
    |-- Personality Matrix (trait-based agent personalities)
    |-- Emotion Engine (valence-arousal emotional modeling)
    |-- Relationship Graph (weighted social network)
    |-- Interaction Director (context-aware social interaction)
    |-- Group Dynamics (crowd/group behavior modeling)
    |-- Social Memory (interaction history and reputation)
    |-- Rumor Engine (information propagation through networks)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class PersonalityTrait(Enum):
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


class SocialStyle(Enum):
    INTROVERT = "introvert"
    AMBIVERT = "ambivert"
    EXTROVERT = "extrovert"


class EmotionalState(Enum):
    EXCITED = "excited"
    ANGRY = "angry"
    TENSE = "tense"
    CONTENT = "content"
    FRUSTRATED = "frustrated"
    CALM = "calm"
    SERENE = "serene"
    SAD = "sad"
    BORED = "bored"


class RelationshipType(Enum):
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    RIVAL = "rival"
    ALLY = "ally"
    FAMILY = "family"
    ROMANTIC = "romantic"


class InteractionType(Enum):
    GREETING = "greeting"
    CONVERSATION = "conversation"
    TRADE = "trade"
    COOPERATION = "cooperation"
    CONFLICT = "conflict"
    GIFT = "gift"
    GOSSIP = "gossip"
    HELP = "help"
    THREATEN = "threaten"
    IGNORE = "ignore"


@dataclass
class PersonalityProfile:
    """Trait-based personality model for social agents."""
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_name: str = ""
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5
    social_style: SocialStyle = SocialStyle.AMBIVERT
    core_motivation: str = ""
    speaking_style: str = ""
    quirks: List[str] = field(default_factory=list)
    cultural_background: str = ""

    @property
    def trait_vector(self) -> Dict[str, float]:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "agent_name": self.agent_name,
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
            "social_style": self.social_style.value,
            "core_motivation": self.core_motivation,
            "speaking_style": self.speaking_style,
            "quirks": self.quirks,
            "cultural_background": self.cultural_background,
        }


@dataclass
class EmotionState:
    """Valence-arousal emotional model."""
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    valence: float = 0.0  # -1.0 (negative) to 1.0 (positive)
    arousal: float = 0.0  # 0.0 (calm) to 1.0 (excited)
    current_emotion: EmotionalState = EmotionalState.CALM
    emotion_history: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: float = field(default_factory=_time_module.time)
    dominant_emotion: str = "calm"
    emotion_stability: float = 0.8  # how quickly emotions change

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "agent_id": self.agent_id,
            "valence": self.valence,
            "arousal": self.arousal,
            "current_emotion": self.current_emotion.value,
            "dominant_emotion": self.dominant_emotion,
            "emotion_stability": self.emotion_stability,
            "last_updated": self.last_updated,
        }


@dataclass
class SocialRelationship:
    """Weighted relationship between two agents."""
    relationship_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_a_id: str = ""
    agent_b_id: str = ""
    relationship_type: RelationshipType = RelationshipType.STRANGER
    affinity: float = 0.0  # -1.0 (hostile) to 1.0 (friendly)
    trust: float = 0.0  # 0.0 to 1.0
    respect: float = 0.0  # 0.0 to 1.0
    interaction_count: int = 0
    last_interaction: float = field(default_factory=_time_module.time)
    shared_experiences: List[str] = field(default_factory=list)
    known_secrets: List[str] = field(default_factory=list)
    first_met: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "agent_a_id": self.agent_a_id,
            "agent_b_id": self.agent_b_id,
            "relationship_type": self.relationship_type.value,
            "affinity": self.affinity,
            "trust": self.trust,
            "respect": self.respect,
            "interaction_count": self.interaction_count,
            "last_interaction": self.last_interaction,
            "shared_experiences": self.shared_experiences,
        }


@dataclass
class SocialInteraction:
    """Record of a social interaction between agents."""
    interaction_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    interaction_type: InteractionType = InteractionType.GREETING
    initiator_id: str = ""
    target_id: str = ""
    location: str = ""
    content: str = ""
    outcome: str = ""
    affinity_change: float = 0.0
    emotional_impact: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)
    witnessed_by: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "interaction_type": self.interaction_type.value,
            "initiator_id": self.initiator_id,
            "target_id": self.target_id,
            "location": self.location,
            "content": self.content,
            "outcome": self.outcome,
            "affinity_change": self.affinity_change,
            "emotional_impact": self.emotional_impact,
            "timestamp": self.timestamp,
            "witnessed_by": self.witnessed_by,
        }


@dataclass
class Rumor:
    """Information propagating through the social network."""
    rumor_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_agent_id: str = ""
    content: str = ""
    topic: str = ""
    spread_count: int = 0
    spread_path: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    last_spread: float = field(default_factory=_time_module.time)
    mutation: str = ""  # how the rumor changed during propagation
    credibility: float = 1.0  # decreases with spread

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rumor_id": self.rumor_id,
            "source_agent_id": self.source_agent_id,
            "content": self.content,
            "topic": self.topic,
            "spread_count": self.spread_count,
            "spread_path": self.spread_path,
            "created_at": self.created_at,
            "credibility": self.credibility,
            "mutation": self.mutation,
        }


class AgentSocialDynamics:
    """
    Multi-agent social dynamics simulation engine.

    Models personality-driven social interactions, emotional states,
    relationship networks, and emergent social behaviors. Agents
    interact based on their personality traits, emotional states,
    and existing relationships, creating dynamic social ecosystems.
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
        self._profiles: Dict[str, PersonalityProfile] = {}
        self._emotions: Dict[str, EmotionState] = {}
        self._relationships: Dict[str, SocialRelationship] = {}
        self._interactions: List[SocialInteraction] = []
        self._rumors: Dict[str, Rumor] = {}
        self._total_interactions: int = 0
        self._social_context: str = "neutral"

        # Predefined personality archetypes
        self._archetypes: Dict[str, Dict[str, float]] = {
            "guardian": {"openness": 0.3, "conscientiousness": 0.9, "extraversion": 0.4, "agreeableness": 0.8, "neuroticism": 0.3},
            "explorer": {"openness": 0.9, "conscientiousness": 0.4, "extraversion": 0.6, "agreeableness": 0.6, "neuroticism": 0.4},
            "diplomat": {"openness": 0.6, "conscientiousness": 0.7, "extraversion": 0.8, "agreeableness": 0.9, "neuroticism": 0.3},
            "rebel": {"openness": 0.8, "conscientiousness": 0.2, "extraversion": 0.7, "agreeableness": 0.3, "neuroticism": 0.7},
            "scholar": {"openness": 0.9, "conscientiousness": 0.8, "extraversion": 0.2, "agreeableness": 0.5, "neuroticism": 0.5},
            "merchant": {"openness": 0.5, "conscientiousness": 0.7, "extraversion": 0.7, "agreeableness": 0.6, "neuroticism": 0.4},
            "warrior": {"openness": 0.3, "conscientiousness": 0.8, "extraversion": 0.5, "agreeableness": 0.3, "neuroticism": 0.2},
            "mystic": {"openness": 0.9, "conscientiousness": 0.5, "extraversion": 0.3, "agreeableness": 0.7, "neuroticism": 0.6},
        }

    @classmethod
    def get_instance(cls) -> "AgentSocialDynamics":
        return cls()

    # ---- Personality Management ----

    def create_profile(
        self,
        agent_name: str,
        archetype: str = "",
        openness: float = 0.5,
        conscientiousness: float = 0.5,
        extraversion: float = 0.5,
        agreeableness: float = 0.5,
        neuroticism: float = 0.5,
        core_motivation: str = "",
        speaking_style: str = "",
        quirks: Optional[List[str]] = None,
    ) -> PersonalityProfile:
        """Create a personality profile for an agent."""
        with self._lock:
            if archetype and archetype in self._archetypes:
                traits = self._archetypes[archetype]
                openness = traits["openness"]
                conscientiousness = traits["conscientiousness"]
                extraversion = traits["extraversion"]
                agreeableness = traits["agreeableness"]
                neuroticism = traits["neuroticism"]

            social_style = SocialStyle.AMBIVERT
            if extraversion < 0.35:
                social_style = SocialStyle.INTROVERT
            elif extraversion > 0.65:
                social_style = SocialStyle.EXTROVERT

            profile = PersonalityProfile(
                agent_name=agent_name,
                openness=openness,
                conscientiousness=conscientiousness,
                extraversion=extraversion,
                agreeableness=agreeableness,
                neuroticism=neuroticism,
                social_style=social_style,
                core_motivation=core_motivation,
                speaking_style=speaking_style,
                quirks=quirks or [],
            )
            self._profiles[profile.profile_id] = profile

            # Initialize emotion state
            self._emotions[profile.profile_id] = EmotionState(
                agent_id=profile.profile_id,
                valence=0.5,
                arousal=0.3,
                current_emotion=EmotionalState.CALM,
            )

            return profile

    def get_profile(self, profile_id: str) -> Optional[PersonalityProfile]:
        return self._profiles.get(profile_id)

    # ---- Emotion Management ----

    def compute_emotion(self, profile_id: str) -> Optional[EmotionState]:
        """
        Compute current emotional state based on valence-arousal model.

        Maps valence and arousal values to emotional categories:
        - High arousal + positive valence = EXCITED
        - High arousal + negative valence = ANGRY
        - Medium arousal + negative valence = TENSE
        - Medium arousal + positive valence = CONTENT
        - Low arousal + negative valence = FRUSTRATED
        - Low arousal + neutral valence = CALM
        - Low arousal + positive valence = SERENE
        - Very low arousal + negative valence = SAD
        - Very low arousal + neutral valence = BORED
        """
        with self._lock:
            state = self._emotions.get(profile_id)
            if state is None:
                return None

            v, a = state.valence, state.arousal

            if a > 0.7:
                state.current_emotion = EmotionalState.EXCITED if v > 0 else EmotionalState.ANGRY
            elif a > 0.4:
                state.current_emotion = EmotionalState.CONTENT if v > 0 else EmotionalState.TENSE
            elif a > 0.2:
                state.current_emotion = EmotionalState.SERENE if v > 0.3 else EmotionalState.FRUSTRATED
            else:
                state.current_emotion = EmotionalState.CALM if v > -0.3 else EmotionalState.SAD

            state.last_updated = _time_module.time()
            state.dominant_emotion = state.current_emotion.value
            return state

    def update_emotion(
        self,
        profile_id: str,
        valence_delta: float = 0.0,
        arousal_delta: float = 0.0,
    ) -> Optional[EmotionState]:
        """Update emotional state with deltas."""
        with self._lock:
            state = self._emotions.get(profile_id)
            if state is None:
                return None

            stability = state.emotion_stability
            state.valence = max(-1.0, min(1.0, state.valence + valence_delta * (1 - stability)))
            state.arousal = max(0.0, min(1.0, state.arousal + arousal_delta * (1 - stability)))

            state.emotion_history.append({
                "time": _time_module.time(),
                "valence": state.valence,
                "arousal": state.arousal,
                "valence_delta": valence_delta,
                "arousal_delta": arousal_delta,
            })
            if len(state.emotion_history) > 100:
                state.emotion_history = state.emotion_history[-50:]

            return self.compute_emotion(profile_id)

    def get_emotion(self, profile_id: str) -> Optional[EmotionState]:
        return self._emotions.get(profile_id)

    # ---- Relationship Management ----

    def _get_relationship_key(self, a_id: str, b_id: str) -> str:
        """Generate a deterministic key for a pair of agents."""
        return f"{min(a_id, b_id)}:{max(a_id, b_id)}"

    def get_or_create_relationship(
        self, agent_a_id: str, agent_b_id: str,
    ) -> SocialRelationship:
        """Get existing relationship or create a new one."""
        with self._lock:
            key = self._get_relationship_key(agent_a_id, agent_b_id)
            if key in self._relationships:
                return self._relationships[key]

            rel = SocialRelationship(
                agent_a_id=agent_a_id,
                agent_b_id=agent_b_id,
            )
            self._relationships[key] = rel
            return rel

    def update_relationship(
        self,
        agent_a_id: str,
        agent_b_id: str,
        affinity_delta: float = 0.0,
        trust_delta: float = 0.0,
        respect_delta: float = 0.0,
    ) -> SocialRelationship:
        """Update relationship metrics between two agents."""
        rel = self.get_or_create_relationship(agent_a_id, agent_b_id)
        with self._lock:
            rel.affinity = max(-1.0, min(1.0, rel.affinity + affinity_delta))
            rel.trust = max(0.0, min(1.0, rel.trust + trust_delta))
            rel.respect = max(0.0, min(1.0, rel.respect + respect_delta))
            rel.interaction_count += 1
            rel.last_interaction = _time_module.time()
            self._update_relationship_type(rel)
            return rel

    def _update_relationship_type(self, rel: SocialRelationship):
        """Update relationship type based on affinity and trust."""
        if rel.affinity > 0.8 and rel.trust > 0.8:
            rel.relationship_type = RelationshipType.CLOSE_FRIEND
        elif rel.affinity > 0.5:
            rel.relationship_type = RelationshipType.FRIEND
        elif rel.affinity < -0.5:
            rel.relationship_type = RelationshipType.RIVAL
        elif rel.interaction_count > 5:
            rel.relationship_type = RelationshipType.ACQUAINTANCE
        else:
            rel.relationship_type = RelationshipType.STRANGER

    def get_relationships(
        self, agent_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all relationships for an agent."""
        with self._lock:
            results = []
            for rel in self._relationships.values():
                if rel.agent_a_id == agent_id or rel.agent_b_id == agent_id:
                    results.append(rel.to_dict())
            return results

    def get_relationship_network(self) -> Dict[str, Any]:
        """Get the full relationship graph."""
        with self._lock:
            nodes = list(self._profiles.keys())
            edges = []
            for rel in self._relationships.values():
                if rel.interaction_count > 0:
                    edges.append({
                        "source": rel.agent_a_id,
                        "target": rel.agent_b_id,
                        "affinity": rel.affinity,
                        "type": rel.relationship_type.value,
                    })
            return {"nodes": nodes, "edges": edges}

    # ---- Social Interaction ----

    def simulate_interaction(
        self,
        initiator_id: str,
        target_id: str,
        interaction_type: InteractionType,
        location: str = "",
        content: str = "",
        witnesses: Optional[List[str]] = None,
    ) -> SocialInteraction:
        """
        Simulate a social interaction between two agents.

        Computes personality compatibility, emotional impact,
        relationship changes, and generates an interaction record.
        """
        with self._lock:
            profile_a = self._profiles.get(initiator_id)
            profile_b = self._profiles.get(target_id)

            # Compute compatibility
            compatibility = 0.5
            if profile_a and profile_b:
                compatibility = self._compute_compatibility(profile_a, profile_b)

            # Compute emotional impact
            emotional_impact = self._compute_emotional_impact(
                interaction_type, compatibility,
            )

            # Compute affinity change
            affinity_change = self._compute_affinity_change(
                interaction_type, compatibility,
            )

            # Update relationship
            self.update_relationship(
                initiator_id, target_id,
                affinity_delta=affinity_change,
            )

            # Update emotions
            if profile_a:
                self.update_emotion(
                    initiator_id,
                    valence_delta=emotional_impact.get("valence", 0.0),
                    arousal_delta=emotional_impact.get("arousal", 0.0),
                )
            if profile_b:
                self.update_emotion(
                    target_id,
                    valence_delta=emotional_impact.get("target_valence", 0.0),
                    arousal_delta=emotional_impact.get("target_arousal", 0.0),
                )

            interaction = SocialInteraction(
                interaction_type=interaction_type,
                initiator_id=initiator_id,
                target_id=target_id,
                location=location,
                content=content,
                outcome=f"compatibility={compatibility:.2f}",
                affinity_change=affinity_change,
                emotional_impact=emotional_impact,
                witnessed_by=witnesses or [],
            )
            self._interactions.append(interaction)
            self._total_interactions += 1

            # Trim interaction history
            if len(self._interactions) > 1000:
                self._interactions = self._interactions[-500:]

            return interaction

    def _compute_compatibility(
        self, a: PersonalityProfile, b: PersonalityProfile,
    ) -> float:
        """Compute personality compatibility between two agents."""
        # Higher agreeableness = higher compatibility
        agree = (a.agreeableness + b.agreeableness) / 2
        # Similar openness = higher compatibility
        openness_diff = 1.0 - abs(a.openness - b.openness)
        # Similar extraversion = higher compatibility
        extra_diff = 1.0 - abs(a.extraversion - b.extraversion)

        return (agree * 0.4 + openness_diff * 0.3 + extra_diff * 0.3)

    def _compute_emotional_impact(
        self, interaction_type: InteractionType, compatibility: float,
    ) -> Dict[str, float]:
        """Compute emotional impact of an interaction."""
        impact = {
            "valence": 0.0,
            "arousal": 0.1,
            "target_valence": 0.0,
            "target_arousal": 0.1,
        }

        base = compatibility * 0.2

        if interaction_type == InteractionType.GREETING:
            impact["valence"] = base * 0.5
            impact["target_valence"] = base * 0.5
        elif interaction_type == InteractionType.CONVERSATION:
            impact["valence"] = base
            impact["target_valence"] = base
        elif interaction_type == InteractionType.GIFT:
            impact["valence"] = base * 0.3
            impact["target_valence"] = base * 1.5
        elif interaction_type == InteractionType.HELP:
            impact["valence"] = base * 0.5
            impact["target_valence"] = base * 2.0
        elif interaction_type == InteractionType.CONFLICT:
            impact["valence"] = -0.2
            impact["target_valence"] = -0.3
            impact["arousal"] = 0.3
            impact["target_arousal"] = 0.4
        elif interaction_type == InteractionType.GOSSIP:
            impact["arousal"] = 0.2
            impact["target_arousal"] = 0.15

        return impact

    def _compute_affinity_change(
        self, interaction_type: InteractionType, compatibility: float,
    ) -> float:
        """Compute affinity change from an interaction."""
        base = compatibility * 0.1

        affinity_map = {
            InteractionType.GREETING: 0.02,
            InteractionType.CONVERSATION: 0.05,
            InteractionType.GIFT: 0.15,
            InteractionType.HELP: 0.2,
            InteractionType.COOPERATION: 0.1,
            InteractionType.CONFLICT: -0.2,
            InteractionType.THREATEN: -0.3,
            InteractionType.IGNORE: -0.05,
            InteractionType.TRADE: 0.03,
            InteractionType.GOSSIP: 0.01,
        }

        return affinity_map.get(interaction_type, 0.0) + (base - 0.05)

    # ---- Rumor Engine ----

    def create_rumor(
        self, source_agent_id: str, content: str, topic: str = "",
    ) -> Rumor:
        """Create a new rumor in the social network."""
        rumor = Rumor(
            source_agent_id=source_agent_id,
            content=content,
            topic=topic,
            spread_path=[source_agent_id],
        )
        self._rumors[rumor.rumor_id] = rumor
        return rumor

    def spread_rumor(
        self, rumor_id: str, spreader_id: str, mutation: str = "",
    ) -> Optional[Rumor]:
        """Spread a rumor to a new agent with optional mutation."""
        rumor = self._rumors.get(rumor_id)
        if rumor is None:
            return None

        rumor.spread_count += 1
        rumor.spread_path.append(spreader_id)
        rumor.last_spread = _time_module.time()
        rumor.credibility = max(0.1, 1.0 - rumor.spread_count * 0.1)

        if mutation:
            rumor.mutation = mutation
            rumor.content = mutation

        return rumor

    # ---- Group Dynamics ----

    def compute_group_cohesion(
        self, agent_ids: List[str],
    ) -> float:
        """Compute the cohesion of a group of agents."""
        if len(agent_ids) < 2:
            return 1.0

        total_affinity = 0.0
        count = 0
        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                rel = self.get_or_create_relationship(agent_ids[i], agent_ids[j])
                total_affinity += rel.affinity
                count += 1

        return total_affinity / count if count > 0 else 0.0

    def find_natural_groups(
        self, min_affinity: float = 0.3,
    ) -> List[List[str]]:
        """Find naturally forming groups based on relationship affinity."""
        with self._lock:
            visited: Set[str] = set()
            groups: List[List[str]] = []

            for agent_id in self._profiles:
                if agent_id in visited:
                    continue
                group = self._explore_group(agent_id, visited, min_affinity)
                if len(group) > 1:
                    groups.append(group)

            return groups

    def _explore_group(
        self, start_id: str, visited: Set[str], min_affinity: float,
    ) -> List[str]:
        """BFS exploration of a social group."""
        group: List[str] = []
        queue = [start_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            group.append(current)

            for rel in self._relationships.values():
                other = None
                if rel.agent_a_id == current:
                    other = rel.agent_b_id
                elif rel.agent_b_id == current:
                    other = rel.agent_a_id
                if other and other not in visited and rel.affinity >= min_affinity:
                    queue.append(other)

        return group

    def get_interaction_history(
        self,
        agent_id: str = "",
        interaction_type: Optional[InteractionType] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query interaction history."""
        with self._lock:
            results = self._interactions
            if agent_id:
                results = [
                    i for i in results
                    if i.initiator_id == agent_id or i.target_id == agent_id
                ]
            if interaction_type is not None:
                results = [i for i in results if i.interaction_type == interaction_type]
            results.sort(key=lambda i: i.timestamp, reverse=True)
            return [i.to_dict() for i in results[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        """Get social dynamics statistics."""
        with self._lock:
            return {
                "total_profiles": len(self._profiles),
                "total_relationships": len(self._relationships),
                "total_interactions": self._total_interactions,
                "active_rumors": len(self._rumors),
                "social_context": self._social_context,
                "archetypes_available": list(self._archetypes.keys()),
                "natural_groups": len(self.find_natural_groups()),
                "average_group_cohesion": self._compute_global_cohesion(),
            }

    def _compute_global_cohesion(self) -> float:
        """Compute global social cohesion."""
        groups = self.find_natural_groups()
        if not groups:
            return 0.0
        return sum(self.compute_group_cohesion(g) for g in groups) / len(groups)


# Module-level accessor
_social_dynamics: Optional[AgentSocialDynamics] = None


def get_social_dynamics() -> AgentSocialDynamics:
    global _social_dynamics
    if _social_dynamics is None:
        _social_dynamics = AgentSocialDynamics()
    return _social_dynamics