"""
SparkLabs Agent - Social Simulation Engine

AI-driven multi-agent social dynamics simulation system that models
independent character agents with personality, emotions, needs, social
connections, episodic memory, and emergent narrative events. Characters
autonomously interact through a social action system, form relationships
via a weighted directed graph, and generate cascading narrative events
that propagate through the social network.

Architecture:
  AgentSocialSimulation (Singleton)
    |-- CharacterProfile (personality, backstory, traits, skills)
    |-- CharacterState (runtime state: location, emotion, needs, action)
    |-- SocialRelationship (weighted directed graph edges)
    |-- SocialAction (actor-initiated interactions with outcomes)
    |-- CharacterMemory (episodic memories with retrieval scoring)
    |-- SocialEvent (emergent narrative events with witnesses)
    |-- PersonalityTraits (Big Five model: 0-1 values)
    |-- EmotionState (valence-arousal two-dimensional model)
    |-- NeedState (decaying needs that drive behavior)

Personality Model:
  Big Five traits: openness, conscientiousness, extraversion,
  agreeableness, neuroticism — each 0.0 to 1.0.

Emotion Model:
  Two-dimensional: valence (-5 to +5) and arousal (0 to 10).
  EMA smoothing and natural decay toward neutral baseline.

Need System:
  Five need types: curiosity, social, achievement, safety, autonomy.
  Each decays over time; low values trigger compensatory behavior.

Relationship Network:
  Weighted directed graph with trust, familiarity, and affinity.
  Interaction count and history track relationship evolution.

Social Action Types:
  GREET, TRADE, FIGHT, HELP, GOSSIP, IGNORE, FLEE, COOPERATE,
  COMPETE, COMFORT, THREATEN, GIFT

Memory System:
  Episodic memories with multi-factor retrieval scoring:
  relevance, recency, importance, emotional intensity.

Usage:
    sim = get_agent_social_simulation()
    char = sim.create_character(name="Elena", role="Merchant")
    sim.update_emotion(char.character_id, event_valence=2.0, event_arousal=5.0)
    sim.add_relationship("char_a", "char_b", RelationshipType.ACQUAINTANCE)
    action = sim.execute_social_action("char_a", "char_b", SocialActionType.GREET, "First meeting")
    mem = sim.add_memory("char_a", MemoryType.SOCIAL, "Met char_b for the first time")
    memories = sim.retrieve_memories("char_a", ["char_b", "first"], top_k=5)
    sim.reflect("char_a")
    event = sim.generate_social_event(["char_a", "char_b"], "market_square", "A tense negotiation")
    sim.propagate_event(event.event_id)
    sim.tick()
    status = sim.get_status()
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


# =============================================================================
# Enums
# =============================================================================


class SocialActionType(Enum):
    """Types of social actions a character can initiate."""
    GREET = "greet"
    TRADE = "trade"
    FIGHT = "fight"
    HELP = "help"
    GOSSIP = "gossip"
    IGNORE = "ignore"
    FLEE = "flee"
    COOPERATE = "cooperate"
    COMPETE = "compete"
    COMFORT = "comfort"
    THREATEN = "threaten"
    GIFT = "gift"


class RelationshipType(Enum):
    """Categories of social relationships between characters."""
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    RIVAL = "rival"
    ENEMY = "enemy"
    ALLY = "ally"
    FAMILY = "family"
    ROMANTIC = "romantic"


class MemoryType(Enum):
    """Types of episodic memories a character can store."""
    OBSERVATION = "observation"
    CONVERSATION = "conversation"
    EXPERIENCE = "experience"
    REFLECTION = "reflection"
    EMOTION = "emotion"
    SOCIAL = "social"


class SocialStyle(Enum):
    """Social interaction style of a character."""
    EXTROVERT = "extrovert"
    INTROVERT_SELECTIVE = "introvert_selective"
    INTROVERT = "introvert"
    AMBIVERT = "ambivert"


class EmotionLabel(Enum):
    """Discrete emotion labels derived from valence-arousal space."""
    EXCITED = "excited"
    ANGRY = "angry"
    TENSE = "tense"
    CONTENT = "content"
    FRUSTRATED = "frustrated"
    CALM = "calm"
    PEACEFUL = "peaceful"
    SAD = "sad"
    BORED = "bored"
    JOYFUL = "joyful"
    ANXIOUS = "anxious"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PersonalityTraits:
    """Big Five personality traits for a character agent.

    All values are in range [0.0, 1.0].
    """
    openness: float = 0.50
    conscientiousness: float = 0.50
    extraversion: float = 0.50
    agreeableness: float = 0.50
    neuroticism: float = 0.50

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "openness": round(self.openness, 4),
            "conscientiousness": round(self.conscientiousness, 4),
            "extraversion": round(self.extraversion, 4),
            "agreeableness": round(self.agreeableness, 4),
            "neuroticism": round(self.neuroticism, 4),
        }


@dataclass
class EmotionState:
    """Two-dimensional emotion model with valence and arousal.

    Valence ranges from -5.0 (negative) to +5.0 (positive).
    Arousal ranges from 0.0 (calm) to 10.0 (excited).
    """
    valence: float = 0.0
    arousal: float = 5.0
    dominant_emotion: str = EmotionLabel.CALM.value
    intensity: float = 0.0
    last_update: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "valence": round(self.valence, 4),
            "arousal": round(self.arousal, 4),
            "dominant_emotion": self.dominant_emotion,
            "intensity": round(self.intensity, 4),
            "last_update": self.last_update,
        }


@dataclass
class NeedState:
    """A single need that decays over time and drives character behavior.

    Each need has a current value (0-100), decay rate, threshold below
    which the need becomes urgent, and a priority weight.
    """
    need_type: str = "curiosity"
    current_value: float = 100.0
    decay_rate: float = 0.5
    threshold: float = 30.0
    priority: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "need_type": self.need_type,
            "current_value": round(self.current_value, 4),
            "decay_rate": round(self.decay_rate, 4),
            "threshold": round(self.threshold, 4),
            "priority": round(self.priority, 4),
        }


@dataclass
class CharacterProfile:
    """Complete profile of a character agent including personality and backstory.

    Attributes:
        character_id: Unique identifier.
        name: Display name of the character.
        role: Character's role in the world (e.g., "Merchant", "Guard").
        backstory: Narrative backstory text.
        core_motivation: Primary drive (e.g., "seek_wealth", "protect_family").
        core_values: List of values the character holds (e.g., ["honor", "loyalty"]).
        speaking_style: Description of how the character speaks.
        fears: List of things the character fears.
        social_style: Social interaction style from SocialStyle enum.
        personality_traits: Big Five personality traits.
        skills: Dictionary of skill name to proficiency (0-100).
        anchor_location: Preferred location or home base.
    """
    character_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "UnnamedNPC"
    role: str = "villager"
    backstory: str = ""
    core_motivation: str = ""
    core_values: List[str] = field(default_factory=list)
    speaking_style: str = ""
    fears: List[str] = field(default_factory=list)
    social_style: str = SocialStyle.AMBIVERT.value
    personality_traits: PersonalityTraits = field(default_factory=PersonalityTraits)
    skills: Dict[str, float] = field(default_factory=dict)
    anchor_location: str = ""

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "character_id": self.character_id,
            "name": self.name,
            "role": self.role,
            "backstory": self.backstory,
            "core_motivation": self.core_motivation,
            "core_values": list(self.core_values),
            "speaking_style": self.speaking_style,
            "fears": list(self.fears),
            "social_style": self.social_style,
            "personality_traits": self.personality_traits.to_dict(),
            "skills": dict(self.skills),
            "anchor_location": self.anchor_location,
        }


@dataclass
class CharacterState:
    """Runtime state of a character agent during simulation.

    Tracks the character's current location, action, emotion, needs,
    conversation target, and last action timestamp.
    """
    character_id: str = ""
    location: str = ""
    current_action: str = ""
    action_target: str = ""
    emotion_valence: float = 0.0
    emotion_arousal: float = 5.0
    needs: Dict[str, NeedState] = field(default_factory=dict)
    conversation_target: str = ""
    last_action_time: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "character_id": self.character_id,
            "location": self.location,
            "current_action": self.current_action,
            "action_target": self.action_target,
            "emotion_valence": round(self.emotion_valence, 4),
            "emotion_arousal": round(self.emotion_arousal, 4),
            "needs": {k: v.to_dict() for k, v in self.needs.items()},
            "conversation_target": self.conversation_target,
            "last_action_time": self.last_action_time,
        }


@dataclass
class SocialRelationship:
    """Weighted directed relationship between two characters.

    Tracks trust (0-1), familiarity (0-1), affinity (-1 to 1),
    interaction count, and relationship type with history.
    """
    relationship_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_id: str = ""
    target_id: str = ""
    trust: float = 0.30
    familiarity: float = 0.10
    affinity: float = 0.00
    interaction_count: int = 0
    last_interaction: float = field(default_factory=_time_module.time)
    relationship_type: str = RelationshipType.STRANGER.value
    history: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "relationship_id": self.relationship_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "trust": round(self.trust, 4),
            "familiarity": round(self.familiarity, 4),
            "affinity": round(self.affinity, 4),
            "interaction_count": self.interaction_count,
            "last_interaction": self.last_interaction,
            "relationship_type": self.relationship_type,
            "history": list(self.history),
        }


@dataclass
class SocialAction:
    """A social action executed by an actor character toward a target.

    Records the action type, reason, outcome, timestamp, and the
    emotional impact on both participants.
    """
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    actor_id: str = ""
    target_id: str = ""
    action_type: str = SocialActionType.GREET.value
    reason: str = ""
    outcome: str = ""
    timestamp: float = field(default_factory=_time_module.time)
    emotional_impact: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "action_id": self.action_id,
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "action_type": self.action_type,
            "reason": self.reason,
            "outcome": self.outcome,
            "timestamp": self.timestamp,
            "emotional_impact": {k: round(v, 4) for k, v in self.emotional_impact.items()},
        }


@dataclass
class CharacterMemory:
    """An episodic memory belonging to a character.

    Features multi-factor retrieval scoring based on relevance, recency,
    importance, and emotional intensity. Memories decay over time and
    may be consolidated or forgotten.
    """
    memory_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    character_id: str = ""
    memory_type: str = MemoryType.OBSERVATION.value
    content: str = ""
    importance: float = 0.50
    emotional_intensity: float = 0.00
    timestamp: float = field(default_factory=_time_module.time)
    decay_factor: float = 0.995
    access_count: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "memory_id": self.memory_id,
            "character_id": self.character_id,
            "memory_type": self.memory_type,
            "content": self.content,
            "importance": round(self.importance, 4),
            "emotional_intensity": round(self.emotional_intensity, 4),
            "timestamp": self.timestamp,
            "decay_factor": round(self.decay_factor, 4),
            "access_count": self.access_count,
            "tags": list(self.tags),
        }


@dataclass
class SocialEvent:
    """An emergent narrative event generated by social interactions.

    Events involve actors and targets at a location, carry a dramatic
    score, and may cascade through the social network via witnesses.
    """
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = ""
    actors: List[str] = field(default_factory=list)
    targets: List[str] = field(default_factory=list)
    location: str = ""
    description: str = ""
    dram_score: float = 0.50
    timestamp: float = field(default_factory=_time_module.time)
    witnesses: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "actors": list(self.actors),
            "targets": list(self.targets),
            "location": self.location,
            "description": self.description,
            "dram_score": round(self.dram_score, 4),
            "timestamp": self.timestamp,
            "witnesses": list(self.witnesses),
        }


# =============================================================================
# Action Templates — emotional impact and relationship effects
# =============================================================================

_ACTION_EMOTIONAL_IMPACT: Dict[str, Dict[str, Tuple[float, float]]] = {
    SocialActionType.GREET.value: {"actor": (0.3, 0.5), "target": (0.2, 0.8)},
    SocialActionType.TRADE.value: {"actor": (0.5, 1.0), "target": (0.5, 1.0)},
    SocialActionType.FIGHT.value: {"actor": (-2.0, 6.0), "target": (-3.0, 7.0)},
    SocialActionType.HELP.value: {"actor": (0.8, 1.5), "target": (1.5, 2.0)},
    SocialActionType.GOSSIP.value: {"actor": (0.2, 2.0), "target": (-0.5, 3.0)},
    SocialActionType.IGNORE.value: {"actor": (0.0, 0.0), "target": (-0.8, 1.0)},
    SocialActionType.FLEE.value: {"actor": (-1.0, 4.0), "target": (0.0, 2.0)},
    SocialActionType.COOPERATE.value: {"actor": (0.6, 1.0), "target": (0.6, 1.0)},
    SocialActionType.COMPETE.value: {"actor": (0.0, 3.0), "target": (-0.5, 3.0)},
    SocialActionType.COMFORT.value: {"actor": (0.5, 0.5), "target": (1.5, -1.0)},
    SocialActionType.THREATEN.value: {"actor": (0.3, 3.0), "target": (-2.0, 5.0)},
    SocialActionType.GIFT.value: {"actor": (0.4, 1.0), "target": (1.0, 2.0)},
}

_ACTION_RELATIONSHIP_EFFECTS: Dict[str, Dict[str, float]] = {
    SocialActionType.GREET.value: {"trust": 0.01, "familiarity": 0.02, "affinity": 0.01},
    SocialActionType.TRADE.value: {"trust": 0.02, "familiarity": 0.03, "affinity": 0.01},
    SocialActionType.FIGHT.value: {"trust": -0.15, "familiarity": 0.05, "affinity": -0.20},
    SocialActionType.HELP.value: {"trust": 0.10, "familiarity": 0.05, "affinity": 0.10},
    SocialActionType.GOSSIP.value: {"trust": -0.03, "familiarity": 0.04, "affinity": -0.02},
    SocialActionType.IGNORE.value: {"trust": -0.01, "familiarity": 0.00, "affinity": -0.02},
    SocialActionType.FLEE.value: {"trust": -0.05, "familiarity": 0.01, "affinity": -0.05},
    SocialActionType.COOPERATE.value: {"trust": 0.08, "familiarity": 0.04, "affinity": 0.08},
    SocialActionType.COMPETE.value: {"trust": -0.04, "familiarity": 0.03, "affinity": -0.05},
    SocialActionType.COMFORT.value: {"trust": 0.08, "familiarity": 0.04, "affinity": 0.08},
    SocialActionType.THREATEN.value: {"trust": -0.12, "familiarity": 0.03, "affinity": -0.15},
    SocialActionType.GIFT.value: {"trust": 0.06, "familiarity": 0.04, "affinity": 0.08},
}

_NEED_DEFAULTS: Dict[str, Dict[str, float]] = {
    "curiosity": {"current_value": 100.0, "decay_rate": 0.3, "threshold": 25.0, "priority": 0.8},
    "social": {"current_value": 100.0, "decay_rate": 0.5, "threshold": 30.0, "priority": 1.0},
    "achievement": {"current_value": 100.0, "decay_rate": 0.4, "threshold": 20.0, "priority": 0.9},
    "safety": {"current_value": 100.0, "decay_rate": 0.2, "threshold": 40.0, "priority": 1.2},
    "autonomy": {"current_value": 100.0, "decay_rate": 0.35, "threshold": 25.0, "priority": 0.7},
}


# =============================================================================
# AgentSocialSimulation
# =============================================================================


class AgentSocialSimulation:
    """AI-driven multi-agent social dynamics simulation engine.

    Models independent character agents with personality, emotion, needs,
    social connections, episodic memory, and emergent narrative events.
    Characters autonomously interact through social actions, form
    relationships, and generate cascading narrative events.

    Usage:
        sim = get_agent_social_simulation()
        char = sim.create_character(name="Elena", role="Merchant")
        sim.update_emotion(char.character_id, event_valence=2.0, event_arousal=5.0)
        sim.add_relationship("char_a", "char_b", RelationshipType.ACQUAINTANCE)
        action = sim.execute_social_action("char_a", "char_b", SocialActionType.GREET, "Meeting")
        sim.tick()
        status = sim.get_status()
    """

    _instance: Optional["AgentSocialSimulation"] = None
    _lock: threading.RLock = threading.RLock()

    _DEFAULT_EMOTION_DECAY_RATE = 0.95
    _DEFAULT_NEED_DECAY_RATE = 0.98
    _DEFAULT_MEMORY_DECAY_RATE = 0.995
    _DEFAULT_MEMORY_CONSOLIDATION_THRESHOLD = 0.15
    _DEFAULT_REFLECTION_COOLDOWN = 30.0
    _DEFAULT_PROPAGATION_DEPTH = 3
    _MAX_MEMORIES_PER_CHARACTER = 200
    _EMA_SMOOTHING_ALPHA = 0.3

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
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return
            self._initialized = True

            self._profiles: Dict[str, CharacterProfile] = {}
            self._states: Dict[str, CharacterState] = {}
            self._relationships: Dict[str, SocialRelationship] = {}
            self._memories: Dict[str, List[CharacterMemory]] = {}
            self._actions: List[SocialAction] = []
            self._events: List[SocialEvent] = []
            self._tick_count: int = 0
            self._last_reflection: Dict[str, float] = {}
            self._config: Dict[str, Any] = {
                "emotion_decay_rate": self._DEFAULT_EMOTION_DECAY_RATE,
                "need_decay_rate": self._DEFAULT_NEED_DECAY_RATE,
                "memory_decay_rate": self._DEFAULT_MEMORY_DECAY_RATE,
                "memory_consolidation_threshold": self._DEFAULT_MEMORY_CONSOLIDATION_THRESHOLD,
                "reflection_cooldown": self._DEFAULT_REFLECTION_COOLDOWN,
                "propagation_depth": self._DEFAULT_PROPAGATION_DEPTH,
                "ema_alpha": self._EMA_SMOOTHING_ALPHA,
            }

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure(self, **kwargs: Any) -> None:
        """Update simulation configuration parameters.

        Accepts keyword arguments for any config key:
        emotion_decay_rate, need_decay_rate, memory_decay_rate,
        memory_consolidation_threshold, reflection_cooldown,
        propagation_depth, ema_alpha.
        """
        _time_module.sleep(0.001)
        with self._lock:
            for key, value in kwargs.items():
                if key in self._config:
                    self._config[key] = value

    # ------------------------------------------------------------------
    # Character Management
    # ------------------------------------------------------------------

    def create_character(
        self,
        name: str = "UnnamedNPC",
        role: str = "villager",
        personality_traits: Optional[PersonalityTraits] = None,
        backstory: str = "",
        core_motivation: str = "",
        core_values: Optional[List[str]] = None,
        speaking_style: str = "",
        fears: Optional[List[str]] = None,
        social_style: str = SocialStyle.AMBIVERT.value,
        skills: Optional[Dict[str, float]] = None,
        anchor_location: str = "",
    ) -> CharacterProfile:
        """Create a new character agent with the given profile.

        Args:
            name: Display name of the character.
            role: Character's role in the world.
            personality_traits: Big Five traits; defaults to balanced.
            backstory: Narrative backstory text.
            core_motivation: Primary drive.
            core_values: List of moral values.
            speaking_style: How the character speaks.
            fears: Things the character fears.
            social_style: SocialStyle enum value.
            skills: Dict of skill name to proficiency (0-100).
            anchor_location: Home base location.

        Returns:
            The created CharacterProfile.
        """
        _time_module.sleep(0.001)
        with self._lock:
            profile = CharacterProfile(
                name=name,
                role=role,
                personality_traits=personality_traits if personality_traits else PersonalityTraits(),
                backstory=backstory,
                core_motivation=core_motivation,
                core_values=core_values if core_values is not None else [],
                speaking_style=speaking_style,
                fears=fears if fears is not None else [],
                social_style=social_style,
                skills=skills if skills is not None else {},
                anchor_location=anchor_location,
            )
            self._profiles[profile.character_id] = profile

            needs: Dict[str, NeedState] = {}
            for need_key, defaults in _NEED_DEFAULTS.items():
                needs[need_key] = NeedState(
                    need_type=need_key,
                    current_value=defaults["current_value"],
                    decay_rate=defaults["decay_rate"],
                    threshold=defaults["threshold"],
                    priority=defaults["priority"],
                )
            self._states[profile.character_id] = CharacterState(
                character_id=profile.character_id,
                location=anchor_location,
                needs=needs,
            )
            self._memories[profile.character_id] = []

            return profile

    def get_character(self, character_id: str) -> Optional[CharacterProfile]:
        """Retrieve a character profile by ID.

        Args:
            character_id: The unique character identifier.

        Returns:
            The CharacterProfile, or None if not found.
        """
        _time_module.sleep(0.001)
        return self._profiles.get(character_id)

    def update_character_state(
        self,
        character_id: str,
        location: Optional[str] = None,
        current_action: Optional[str] = None,
        action_target: Optional[str] = None,
        conversation_target: Optional[str] = None,
    ) -> Optional[CharacterState]:
        """Update the runtime state of a character.

        Args:
            character_id: The character to update.
            location: New location (optional).
            current_action: Description of current action (optional).
            action_target: Target of the current action (optional).
            conversation_target: Current conversation partner (optional).

        Returns:
            The updated CharacterState, or None if character not found.
        """
        _time_module.sleep(0.001)
        with self._lock:
            state = self._states.get(character_id)
            if state is None:
                return None
            if location is not None:
                state.location = location
            if current_action is not None:
                state.current_action = current_action
            if action_target is not None:
                state.action_target = action_target
            if conversation_target is not None:
                state.conversation_target = conversation_target
            state.last_action_time = _time_module.time()
            return state

    # ------------------------------------------------------------------
    # Emotion System
    # ------------------------------------------------------------------

    def update_emotion(
        self,
        character_id: str,
        event_valence: float,
        event_arousal: float,
    ) -> Optional[EmotionState]:
        """Update a character's emotion using EMA smoothing.

        Applies exponential moving average to blend the new emotional
        event with the current emotional state.

        Args:
            character_id: The character to update.
            event_valence: Valence of the new event (-5 to +5).
            event_arousal: Arousal of the new event (0 to 10).

        Returns:
            The updated EmotionState, or None if character not found.
        """
        _time_module.sleep(0.001)
        with self._lock:
            state = self._states.get(character_id)
            if state is None:
                return None
            alpha = self._config["ema_alpha"]
            new_valence = state.emotion_valence * (1.0 - alpha) + event_valence * alpha
            new_arousal = state.emotion_arousal * (1.0 - alpha) + event_arousal * alpha
            new_valence = max(-5.0, min(5.0, new_valence))
            new_arousal = max(0.0, min(10.0, new_arousal))
            state.emotion_valence = new_valence
            state.emotion_arousal = new_arousal
            label = self._classify_emotion(new_valence, new_arousal)
            intensity = abs(new_valence) / 5.0 * 0.5 + new_arousal / 10.0 * 0.5
            return EmotionState(
                valence=new_valence,
                arousal=new_arousal,
                dominant_emotion=label,
                intensity=round(intensity, 4),
            )

    def decay_emotions(self) -> None:
        """Decay all character emotions toward the neutral baseline.

        Each tick, emotions drift toward valence=0, arousal=5 by the
        configured emotion_decay_rate.
        """
        _time_module.sleep(0.001)
        with self._lock:
            rate = self._config["emotion_decay_rate"]
            for state in self._states.values():
                state.emotion_valence *= rate
                state.emotion_arousal = 5.0 + (state.emotion_arousal - 5.0) * rate

    def get_character_emotion_label(self, character_id: str) -> Optional[str]:
        """Get the discrete emotion label for a character's current state.

        Args:
            character_id: The character to query.

        Returns:
            An EmotionLabel string value, or None if character not found.
        """
        _time_module.sleep(0.001)
        state = self._states.get(character_id)
        if state is None:
            return None
        return self._classify_emotion(state.emotion_valence, state.emotion_arousal)

    # ------------------------------------------------------------------
    # Need System
    # ------------------------------------------------------------------

    def decay_needs(self) -> None:
        """Decay all character needs by one tick.

        Each need's current_value is multiplied by the configured
        need_decay_rate, simulating natural need erosion over time.
        """
        _time_module.sleep(0.001)
        with self._lock:
            rate = self._config["need_decay_rate"]
            for state in self._states.values():
                for need in state.needs.values():
                    need.current_value = max(0.0, need.current_value * rate)

    # ------------------------------------------------------------------
    # Relationship System
    # ------------------------------------------------------------------

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str = RelationshipType.STRANGER.value,
        trust: float = 0.30,
        familiarity: float = 0.10,
        affinity: float = 0.00,
    ) -> Optional[SocialRelationship]:
        """Create a directed relationship from source to target.

        Args:
            source_id: The character initiating the relationship perspective.
            target_id: The target character.
            relationship_type: RelationshipType enum value.
            trust: Initial trust level (0-1).
            familiarity: Initial familiarity (0-1).
            affinity: Initial affinity (-1 to +1).

        Returns:
            The created SocialRelationship, or None if either character is missing.
        """
        _time_module.sleep(0.001)
        with self._lock:
            if source_id not in self._profiles or target_id not in self._profiles:
                return None
            rel = SocialRelationship(
                source_id=source_id,
                target_id=target_id,
                trust=trust,
                familiarity=familiarity,
                affinity=affinity,
                relationship_type=relationship_type,
            )
            self._relationships[rel.relationship_id] = rel
            return rel

    def update_relationship(
        self,
        source_id: str,
        target_id: str,
        trust_delta: float = 0.0,
        familiarity_delta: float = 0.0,
        affinity_delta: float = 0.0,
    ) -> Optional[SocialRelationship]:
        """Update an existing relationship between two characters.

        Finds the relationship by source and target IDs and applies
        deltas to trust, familiarity, and affinity.

        Args:
            source_id: Source character ID.
            target_id: Target character ID.
            trust_delta: Change in trust.
            familiarity_delta: Change in familiarity.
            affinity_delta: Change in affinity.

        Returns:
            The updated SocialRelationship, or None if not found.
        """
        _time_module.sleep(0.001)
        with self._lock:
            rel = self._find_relationship(source_id, target_id)
            if rel is None:
                return None
            rel.trust = max(0.0, min(1.0, rel.trust + trust_delta))
            rel.familiarity = max(0.0, min(1.0, rel.familiarity + familiarity_delta))
            rel.affinity = max(-1.0, min(1.0, rel.affinity + affinity_delta))
            rel.interaction_count += 1
            rel.last_interaction = _time_module.time()
            rel.history.append(
                f"updated_trust={round(rel.trust, 3)}_fam={round(rel.familiarity, 3)}_aff={round(rel.affinity, 3)}"
            )
            self._update_relationship_type(rel)
            return rel

    def get_relationships(self, character_id: str) -> List[SocialRelationship]:
        """Get all relationships where the character is either source or target.

        Args:
            character_id: The character to look up.

        Returns:
            List of SocialRelationship objects involving the character.
        """
        _time_module.sleep(0.001)
        results: List[SocialRelationship] = []
        for rel in self._relationships.values():
            if rel.source_id == character_id or rel.target_id == character_id:
                results.append(rel)
        return results

    def get_social_network(self) -> Dict[str, Any]:
        """Get the full relationship graph as a dictionary.

        Returns:
            Dict with 'nodes' (character IDs) and 'edges' (relationship dicts).
        """
        _time_module.sleep(0.001)
        nodes = list(self._profiles.keys())
        edges = [rel.to_dict() for rel in self._relationships.values()]
        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    # ------------------------------------------------------------------
    # Memory System
    # ------------------------------------------------------------------

    def add_memory(
        self,
        character_id: str,
        memory_type: str = MemoryType.OBSERVATION.value,
        content: str = "",
        importance: float = 0.50,
        emotional_intensity: float = 0.00,
        tags: Optional[List[str]] = None,
    ) -> Optional[CharacterMemory]:
        """Add an episodic memory for a character.

        Args:
            character_id: The character to add the memory to.
            memory_type: MemoryType enum value.
            content: The memory content text.
            importance: Importance score (0-1).
            emotional_intensity: Emotional intensity (0-1).
            tags: List of keyword tags for retrieval.

        Returns:
            The created CharacterMemory, or None if character not found.
        """
        _time_module.sleep(0.001)
        with self._lock:
            if character_id not in self._profiles:
                return None
            if character_id not in self._memories:
                self._memories[character_id] = []
            memory = CharacterMemory(
                character_id=character_id,
                memory_type=memory_type,
                content=content,
                importance=importance,
                emotional_intensity=emotional_intensity,
                tags=tags if tags is not None else [],
            )
            self._memories[character_id].append(memory)
            self._prune_memories(character_id)
            return memory

    def retrieve_memories(
        self,
        character_id: str,
        context_keywords: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[CharacterMemory]:
        """Retrieve the most relevant memories for a character.

        Uses multi-factor scoring: relevance (tag/keyword match),
        recency (time since memory), importance, and emotional intensity.

        Args:
            character_id: The character whose memories to query.
            context_keywords: Keywords to match against memory tags.
            top_k: Maximum number of memories to return.

        Returns:
            List of the top-k most relevant CharacterMemory objects.
        """
        _time_module.sleep(0.001)
        mems = self._memories.get(character_id, [])
        if not mems:
            return []
        keywords = context_keywords if context_keywords else []
        now = _time_module.time()
        scored: List[Tuple[float, CharacterMemory]] = []
        for mem in mems:
            relevance = self._compute_relevance(mem, keywords)
            recency = max(0.0, 1.0 - (now - mem.timestamp) / 3600.0)
            score = (
                relevance * 0.35
                + recency * 0.25
                + mem.importance * 0.25
                + mem.emotional_intensity * 0.15
            )
            scored.append((score, mem))
        scored.sort(key=lambda x: x[0], reverse=True)
        top_memories = [m for _, m in scored[:top_k]]
        for mem in top_memories:
            mem.access_count += 1
        return top_memories

    def decay_memories(self) -> None:
        """Decay and consolidate all character memories.

        Memories with importance below the consolidation threshold are
        removed. Remaining memories have their decay_factor applied.
        """
        _time_module.sleep(0.001)
        with self._lock:
            threshold = self._config["memory_consolidation_threshold"]
            for character_id, mems in list(self._memories.items()):
                kept: List[CharacterMemory] = []
                for mem in mems:
                    mem.importance *= self._config["memory_decay_rate"]
                    if mem.importance >= threshold:
                        kept.append(mem)
                self._memories[character_id] = kept

    # ------------------------------------------------------------------
    # Reflection System
    # ------------------------------------------------------------------

    def reflect(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Trigger reflection on recent memories for a character.

        The character reviews recent memories, generates insights,
        and adjusts their emotional state based on the reflection.

        Args:
            character_id: The character to reflect.

        Returns:
            Dict with 'insight', 'emotional_adjustment', 'memories_processed',
            or None if character not found or on cooldown.
        """
        _time_module.sleep(0.001)
        with self._lock:
            if character_id not in self._profiles:
                return None
            now = _time_module.time()
            last = self._last_reflection.get(character_id, 0.0)
            cooldown = self._config["reflection_cooldown"]
            if now - last < cooldown:
                return None
            self._last_reflection[character_id] = now

            mems = self._memories.get(character_id, [])
            if not mems:
                return {
                    "insight": "No memories to reflect on.",
                    "emotional_adjustment": (0.0, 0.0),
                    "memories_processed": 0,
                }
            recent = [m for m in mems if now - m.timestamp < 600.0]
            if not recent:
                recent = mems[-10:]
            avg_valence = 0.0
            avg_arousal = 0.0
            topics: Set[str] = set()
            for mem in recent:
                for tag in mem.tags:
                    topics.add(tag)
            for mem in recent:
                val = mem.emotional_intensity * (1.0 if "positive" in mem.tags else -0.5)
                avg_valence += val
                avg_arousal += mem.emotional_intensity * 0.5
            n = max(len(recent), 1)
            avg_valence /= n
            avg_arousal /= n

            self.update_emotion(character_id, avg_valence * 0.3, avg_arousal)

            insight_parts: List[str] = []
            if topics:
                insight_parts.append(f"Reflected on topics: {', '.join(sorted(topics)[:5])}")
            if avg_valence > 0.5:
                insight_parts.append("Overall positive memories dominate.")
            elif avg_valence < -0.3:
                insight_parts.append("Recent memories carry negative undertones.")
            else:
                insight_parts.append("Recent memories are emotionally neutral.")

            reflection_mem = self.add_memory(
                character_id=character_id,
                memory_type=MemoryType.REFLECTION.value,
                content=" ".join(insight_parts),
                importance=0.6,
                emotional_intensity=abs(avg_valence),
                tags=list(topics),
            )

            return {
                "insight": " ".join(insight_parts),
                "emotional_adjustment": (round(avg_valence, 4), round(avg_arousal, 4)),
                "memories_processed": len(recent),
                "reflection_memory_id": reflection_mem.memory_id if reflection_mem else "",
            }

    # ------------------------------------------------------------------
    # Social Action System
    # ------------------------------------------------------------------

    def execute_social_action(
        self,
        actor_id: str,
        target_id: str,
        action_type: str = SocialActionType.GREET.value,
        reason: str = "",
    ) -> Optional[SocialAction]:
        """Execute a social action from one character to another.

        Computes the emotional impact on both parties and updates
        the relationship between them based on the action type.

        Args:
            actor_id: The character performing the action.
            target_id: The target character.
            action_type: SocialActionType enum value.
            reason: Description of why the action was taken.

        Returns:
            The resulting SocialAction, or None if either character is missing.
        """
        _time_module.sleep(0.001)
        with self._lock:
            if actor_id not in self._profiles or target_id not in self._profiles:
                return None
            actor_profile = self._profiles[actor_id]
            target_profile = self._profiles[target_id]

            impact = _ACTION_EMOTIONAL_IMPACT.get(action_type, {"actor": (0.0, 0.0), "target": (0.0, 0.0)})
            actor_val = impact["actor"][0]
            actor_ar = impact["actor"][1]
            target_val = impact["target"][0]
            target_ar = impact["target"][1]

            neuroticism_mod = 1.0 + actor_profile.personality_traits.neuroticism * 0.5
            agreeableness_mod = 1.0 + target_profile.personality_traits.agreeableness * 0.3

            actor_val *= neuroticism_mod
            target_val *= agreeableness_mod

            self.update_emotion(actor_id, actor_val, actor_ar)
            self.update_emotion(target_id, target_val, target_ar)

            rel = self._find_or_create_relationship(actor_id, target_id)
            rel_effects = _ACTION_RELATIONSHIP_EFFECTS.get(action_type, {})
            rel.trust = max(0.0, min(1.0, rel.trust + rel_effects.get("trust", 0.0)))
            rel.familiarity = max(0.0, min(1.0, rel.familiarity + rel_effects.get("familiarity", 0.0)))
            rel.affinity = max(-1.0, min(1.0, rel.affinity + rel_effects.get("affinity", 0.0)))
            rel.interaction_count += 1
            rel.last_interaction = _time_module.time()
            rel.history.append(f"{action_type}_{actor_id[:8]}_{target_id[:8]}")
            self._update_relationship_type(rel)

            outcome = self._generate_action_outcome(action_type, actor_profile, target_profile)
            action = SocialAction(
                actor_id=actor_id,
                target_id=target_id,
                action_type=action_type,
                reason=reason,
                outcome=outcome,
                emotional_impact={
                    "actor_valence": round(actor_val, 4),
                    "actor_arousal": round(actor_ar, 4),
                    "target_valence": round(target_val, 4),
                    "target_arousal": round(target_ar, 4),
                },
            )
            self._actions.append(action)

            self.add_memory(
                character_id=actor_id,
                memory_type=MemoryType.SOCIAL.value,
                content=f"{action_type} {target_profile.name}: {outcome}",
                importance=0.5 + abs(actor_val) * 0.1,
                emotional_intensity=(abs(actor_val) / 5.0 + actor_ar / 10.0) / 2.0,
                tags=[action_type, target_id],
            )

            target_importance = 0.5 + abs(target_val) * 0.1
            self.add_memory(
                character_id=target_id,
                memory_type=MemoryType.SOCIAL.value,
                content=f"Received {action_type} from {actor_profile.name}: {outcome}",
                importance=target_importance,
                emotional_intensity=(abs(target_val) / 5.0 + target_ar / 10.0) / 2.0,
                tags=[action_type, actor_id],
            )

            self._update_state_after_action(actor_id, action_type, target_id)
            self._update_state_after_action(target_id, action_type, actor_id)

            return action

    # ------------------------------------------------------------------
    # Social Event System
    # ------------------------------------------------------------------

    def generate_social_event(
        self,
        actors: List[str],
        location: str,
        description: str = "",
        event_type: str = "",
    ) -> Optional[SocialEvent]:
        """Generate an emergent narrative event from social interactions.

        Args:
            actors: List of character IDs involved.
            location: Where the event takes place.
            description: Human-readable event description.
            event_type: Category label for the event.

        Returns:
            The created SocialEvent, or None if no valid actors.
        """
        _time_module.sleep(0.001)
        with self._lock:
            valid_actors = [a for a in actors if a in self._profiles]
            if not valid_actors:
                return None
            dram_score = self._compute_dram_score(valid_actors)
            if not event_type:
                event_type = "social_interaction"
            event = SocialEvent(
                event_type=event_type,
                actors=valid_actors,
                targets=[],
                location=location,
                description=description,
                dram_score=dram_score,
            )
            self._events.append(event)
            return event

    def propagate_event(self, event_id: str) -> Dict[str, Any]:
        """Propagate a social event through the social network.

        Cascades the event to connected characters up to the configured
        propagation depth, creating emotional ripples and witness memories.

        Args:
            event_id: The SocialEvent to propagate.

        Returns:
            Dict with 'propagated_to', 'affected_count', 'depth'.
        """
        _time_module.sleep(0.001)
        with self._lock:
            event = self._find_event(event_id)
            if event is None:
                return {"propagated_to": [], "affected_count": 0, "depth": 0}
            max_depth = self._config["propagation_depth"]
            visited: Set[str] = set(event.actors)
            frontier: Set[str] = set(event.actors)
            affected: List[str] = []

            for depth in range(max_depth):
                next_frontier: Set[str] = set()
                for char_id in frontier:
                    for rel in self._relationships.values():
                        if rel.source_id == char_id and rel.target_id not in visited:
                            next_frontier.add(rel.target_id)
                        elif rel.target_id == char_id and rel.source_id not in visited:
                            next_frontier.add(rel.source_id)
                if not next_frontier:
                    break
                for char_id in next_frontier:
                    visited.add(char_id)
                    affected.append(char_id)
                    event.witnesses.append(char_id)
                    self.add_memory(
                        character_id=char_id,
                        memory_type=MemoryType.OBSERVATION.value,
                        content=f"Witnessed: {event.description}",
                        importance=event.dram_score * 0.5,
                        emotional_intensity=event.dram_score * 0.3,
                        tags=["event", event.event_type],
                    )
                    self.update_emotion(
                        char_id,
                        event_valence=-0.5 * event.dram_score,
                        event_arousal=2.0 * event.dram_score,
                    )
                frontier = next_frontier

            return {
                "propagated_to": affected,
                "affected_count": len(affected),
                "depth": min(max_depth, len(affected)),
            }

    # ------------------------------------------------------------------
    # Simulation Tick
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        """Advance the simulation by one timestep.

        Decays emotions, needs, and memories. Triggers reflection for
        characters whose cooldown has elapsed.

        Returns:
            Dict with tick summary: tick_count, character_count, etc.
        """
        _time_module.sleep(0.001)
        self._tick_count += 1
        self.decay_emotions()
        self.decay_needs()
        self.decay_memories()

        now = _time_module.time()
        cooldown = self._config["reflection_cooldown"]
        for char_id in self._profiles:
            last = self._last_reflection.get(char_id, 0.0)
            if now - last >= cooldown:
                self.reflect(char_id)

        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        """Get the current simulation status.

        Returns:
            Dict with tick_count, character_count, relationship_count,
            memory_count, event_count, action_count, and config.
        """
        _time_module.sleep(0.001)
        total_memories = sum(len(m) for m in self._memories.values())
        return {
            "tick_count": self._tick_count,
            "character_count": len(self._profiles),
            "relationship_count": len(self._relationships),
            "memory_count": total_memories,
            "event_count": len(self._events),
            "action_count": len(self._actions),
            "config": dict(self._config),
        }

    def reset(self) -> None:
        """Reset all simulation data to initial state."""
        _time_module.sleep(0.001)
        with self._lock:
            self._profiles.clear()
            self._states.clear()
            self._relationships.clear()
            self._memories.clear()
            self._actions.clear()
            self._events.clear()
            self._tick_count = 0
            self._last_reflection.clear()
            self._config = {
                "emotion_decay_rate": self._DEFAULT_EMOTION_DECAY_RATE,
                "need_decay_rate": self._DEFAULT_NEED_DECAY_RATE,
                "memory_decay_rate": self._DEFAULT_MEMORY_DECAY_RATE,
                "memory_consolidation_threshold": self._DEFAULT_MEMORY_CONSOLIDATION_THRESHOLD,
                "reflection_cooldown": self._DEFAULT_REFLECTION_COOLDOWN,
                "propagation_depth": self._DEFAULT_PROPAGATION_DEPTH,
                "ema_alpha": self._EMA_SMOOTHING_ALPHA,
            }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _classify_emotion(self, valence: float, arousal: float) -> str:
        """Classify a valence-arousal pair into a discrete emotion label.

        Maps the two-dimensional emotion space to EmotionLabel values
        based on quadrant and intensity.
        """
        _time_module.sleep(0.001)
        if arousal > 7.0:
            if valence > 2.0:
                return EmotionLabel.EXCITED.value
            elif valence < -2.0:
                return EmotionLabel.ANGRY.value
            else:
                return EmotionLabel.TENSE.value
        elif arousal > 4.0:
            if valence > 2.0:
                return EmotionLabel.JOYFUL.value
            elif valence < -2.0:
                return EmotionLabel.FRUSTRATED.value
            elif valence < 0:
                return EmotionLabel.ANXIOUS.value
            else:
                return EmotionLabel.CONTENT.value
        else:
            if valence > 2.0:
                return EmotionLabel.CALM.value
            elif valence < -2.0:
                return EmotionLabel.SAD.value
            elif valence < 0:
                return EmotionLabel.PEACEFUL.value
            else:
                return EmotionLabel.BORED.value

    def _find_relationship(
        self, source_id: str, target_id: str
    ) -> Optional[SocialRelationship]:
        """Find a relationship by source and target IDs."""
        for rel in self._relationships.values():
            if rel.source_id == source_id and rel.target_id == target_id:
                return rel
        return None

    def _find_or_create_relationship(
        self, source_id: str, target_id: str
    ) -> SocialRelationship:
        """Find an existing relationship or create a default one."""
        rel = self._find_relationship(source_id, target_id)
        if rel is None:
            rel = SocialRelationship(
                source_id=source_id,
                target_id=target_id,
                relationship_type=RelationshipType.STRANGER.value,
            )
            self._relationships[rel.relationship_id] = rel
        return rel

    def _find_event(self, event_id: str) -> Optional[SocialEvent]:
        """Find a social event by ID."""
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None

    def _update_relationship_type(self, rel: SocialRelationship) -> None:
        """Update relationship type based on affinity and trust levels."""
        _time_module.sleep(0.001)
        if rel.affinity > 0.7 and rel.trust > 0.8:
            rel.relationship_type = RelationshipType.CLOSE_FRIEND.value
        elif rel.affinity > 0.4 and rel.trust > 0.5:
            rel.relationship_type = RelationshipType.FRIEND.value
        elif rel.affinity > 0.15 and rel.trust > 0.3:
            rel.relationship_type = RelationshipType.ACQUAINTANCE.value
        elif rel.affinity < -0.6 and rel.trust < 0.2:
            rel.relationship_type = RelationshipType.ENEMY.value
        elif rel.affinity < -0.3:
            rel.relationship_type = RelationshipType.RIVAL.value
        elif rel.trust > 0.7 and rel.affinity > 0.5:
            rel.relationship_type = RelationshipType.ALLY.value
        elif rel.familiarity < 0.05:
            rel.relationship_type = RelationshipType.STRANGER.value

    def _compute_relevance(
        self, memory: CharacterMemory, keywords: List[str]
    ) -> float:
        """Compute relevance score between memory tags and context keywords."""
        _time_module.sleep(0.001)
        if not keywords:
            return 0.5
        matches = 0
        for kw in keywords:
            kw_lower = kw.lower()
            for tag in memory.tags:
                if kw_lower in tag.lower():
                    matches += 1
                    break
            if kw_lower in memory.content.lower():
                matches += 0.5
        return min(1.0, matches / max(len(keywords), 1))

    def _compute_dram_score(self, actor_ids: List[str]) -> float:
        """Compute the dramatic score of a social event based on participants."""
        _time_module.sleep(0.001)
        if not actor_ids:
            return 0.5
        total_intensity = 0.0
        for aid in actor_ids:
            state = self._states.get(aid)
            if state:
                intensity = abs(state.emotion_valence) / 5.0 * 0.6 + state.emotion_arousal / 10.0 * 0.4
                total_intensity += intensity
        avg_intensity = total_intensity / len(actor_ids)
        relationships = 0
        total_affinity_mag = 0.0
        for i, a1 in enumerate(actor_ids):
            for a2 in actor_ids[i + 1:]:
                rel = self._find_relationship(a1, a2)
                if rel:
                    relationships += 1
                    total_affinity_mag += abs(rel.affinity)
        if relationships > 0:
            avg_affinity = total_affinity_mag / relationships
        else:
            avg_affinity = 0.3
        return round(avg_intensity * 0.5 + avg_affinity * 0.5, 4)

    def _generate_action_outcome(
        self,
        action_type: str,
        actor: CharacterProfile,
        target: CharacterProfile,
    ) -> str:
        """Generate a human-readable outcome description for a social action."""
        _time_module.sleep(0.001)
        outcomes: Dict[str, str] = {
            SocialActionType.GREET.value: f"{actor.name} greeted {target.name} warmly.",
            SocialActionType.TRADE.value: f"{actor.name} traded with {target.name}.",
            SocialActionType.FIGHT.value: f"{actor.name} and {target.name} clashed violently.",
            SocialActionType.HELP.value: f"{actor.name} helped {target.name}.",
            SocialActionType.GOSSIP.value: f"{actor.name} gossiped about {target.name}.",
            SocialActionType.IGNORE.value: f"{actor.name} ignored {target.name}.",
            SocialActionType.FLEE.value: f"{actor.name} fled from {target.name}.",
            SocialActionType.COOPERATE.value: f"{actor.name} cooperated with {target.name}.",
            SocialActionType.COMPETE.value: f"{actor.name} competed against {target.name}.",
            SocialActionType.COMFORT.value: f"{actor.name} comforted {target.name}.",
            SocialActionType.THREATEN.value: f"{actor.name} threatened {target.name}.",
            SocialActionType.GIFT.value: f"{actor.name} gave a gift to {target.name}.",
        }
        return outcomes.get(action_type, f"{actor.name} interacted with {target.name}.")

    def _update_state_after_action(
        self, character_id: str, action_type: str, other_id: str
    ) -> None:
        """Update character state after a social action."""
        state = self._states.get(character_id)
        if state is None:
            return
        state.current_action = action_type
        state.action_target = other_id
        state.last_action_time = _time_module.time()

    def _prune_memories(self, character_id: str) -> None:
        """Remove oldest memories if exceeding the maximum per character."""
        mems = self._memories.get(character_id, [])
        if len(mems) > self._MAX_MEMORIES_PER_CHARACTER:
            mems.sort(key=lambda m: m.importance)
            self._memories[character_id] = mems[-(self._MAX_MEMORIES_PER_CHARACTER):]


# =============================================================================
# Module-level accessor
# =============================================================================


def get_agent_social_simulation() -> AgentSocialSimulation:
    """Get the singleton instance of AgentSocialSimulation.

    Returns:
        The global AgentSocialSimulation instance.
    """
    return AgentSocialSimulation.get_instance()