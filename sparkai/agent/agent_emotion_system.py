"""
Agent Emotion System - Emotional state modeling for AI-driven NPCs and game characters.
Provides dynamic emotional responses, mood transitions, and personality-driven behavior.
"""

import threading
import uuid
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Callable


class EmotionType(Enum):
    """Core emotion categories for agent emotional modeling."""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    NEUTRAL = "neutral"


class MoodState(Enum):
    """Long-term mood states that influence emotional responses."""
    ELATED = "elated"
    HAPPY = "happy"
    CONTENT = "content"
    NEUTRAL = "neutral"
    MELANCHOLY = "melancholy"
    SAD = "sad"
    DEPRESSED = "depressed"
    ANXIOUS = "anxious"
    IRRITABLE = "irritable"
    ANGRY = "angry"


class PersonalityTrait(Enum):
    """Big Five personality traits for character modeling."""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


@dataclass
class EmotionValue:
    """Single emotion instance with intensity and decay."""
    emotion_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    emotion_type: EmotionType = EmotionType.NEUTRAL
    intensity: float = 0.0
    decay_rate: float = 0.1
    created_at: float = field(default_factory=_time_module.time)
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "emotion_id": self.emotion_id,
            "emotion_type": self.emotion_type.value,
            "intensity": self.intensity,
            "decay_rate": self.decay_rate,
            "created_at": self.created_at,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class EmotionalState:
    """Complete emotional state of an agent."""
    agent_id: str = ""
    emotions: Dict[str, EmotionValue] = field(default_factory=dict)
    mood: MoodState = MoodState.NEUTRAL
    mood_intensity: float = 0.5
    personality: Dict[str, float] = field(default_factory=lambda: {
        PersonalityTrait.OPENNESS.value: 0.5,
        PersonalityTrait.CONSCIENTIOUSNESS.value: 0.5,
        PersonalityTrait.EXTRAVERSION.value: 0.5,
        PersonalityTrait.AGREEABLENESS.value: 0.5,
        PersonalityTrait.NEUROTICISM.value: 0.5,
    })
    emotional_memory: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "emotions": {k: v.to_dict() for k, v in self.emotions.items()},
            "mood": self.mood.value,
            "mood_intensity": self.mood_intensity,
            "personality": self.personality,
            "emotional_memory": self.emotional_memory[-10:],
            "last_updated": self.last_updated,
        }


@dataclass
class EmotionalEvent:
    """Event that triggers emotional responses."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = ""
    intensity: float = 0.5
    target_emotions: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    timestamp: float = field(default_factory=_time_module.time)


class AgentEmotionSystem:
    """
    Comprehensive emotional simulation system for AI agents.
    Models dynamic emotions, mood transitions, personality influences,
    and emotional memory for believable NPC behavior.
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
            self._agent_states: Dict[str, EmotionalState] = {}
            self._emotion_relationships: Dict[Tuple[str, str], float] = {}
            self._emotion_transition_rules: List[Dict[str, Any]] = []
            self._event_handlers: Dict[str, List[Callable]] = {}
            self._mood_history: Dict[str, List[Dict[str, Any]]] = {}
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'AgentEmotionSystem':
        return cls()

    def register_agent(self, agent_id: str, personality: Optional[Dict[str, float]] = None) -> EmotionalState:
        """Register an agent with the emotion system."""
        with self._lock:
            state = EmotionalState(agent_id=agent_id)
            if personality:
                state.personality.update(personality)
            state.emotions = {
                EmotionType.JOY.value: EmotionValue(emotion_type=EmotionType.JOY, intensity=0.3),
                EmotionType.SADNESS.value: EmotionValue(emotion_type=EmotionType.SADNESS, intensity=0.1),
                EmotionType.ANGER.value: EmotionValue(emotion_type=EmotionType.ANGER, intensity=0.1),
                EmotionType.FEAR.value: EmotionValue(emotion_type=EmotionType.FEAR, intensity=0.1),
                EmotionType.SURPRISE.value: EmotionValue(emotion_type=EmotionType.SURPRISE, intensity=0.1),
                EmotionType.TRUST.value: EmotionValue(emotion_type=EmotionType.TRUST, intensity=0.2),
                EmotionType.ANTICIPATION.value: EmotionValue(emotion_type=EmotionType.ANTICIPATION, intensity=0.2),
            }
            self._agent_states[agent_id] = state
            self._mood_history[agent_id] = []
            return state

    def process_event(self, agent_id: str, event: EmotionalEvent) -> EmotionalState:
        """Process an emotional event and update agent state."""
        with self._lock:
            state = self._agent_states.get(agent_id)
            if not state:
                state = self.register_agent(agent_id)

            personality = state.personality
            neuroticism = personality.get(PersonalityTrait.NEUROTICISM.value, 0.5)
            openness = personality.get(PersonalityTrait.OPENNESS.value, 0.5)

            for emotion_name, delta in event.target_emotions.items():
                if emotion_name in state.emotions:
                    emotion = state.emotions[emotion_name]
                    personality_mod = 1.0 + (neuroticism - 0.5) * 0.5
                    if emotion_name in (EmotionType.JOY.value, EmotionType.SURPRISE.value):
                        personality_mod = 1.0 + (openness - 0.5) * 0.5

                    emotion.intensity = min(1.0, max(0.0, emotion.intensity + delta * event.intensity * personality_mod))
                    emotion.source = event.event_type
                    emotion.created_at = event.timestamp
                    emotion.metadata["last_event"] = event.description

            state.emotional_memory.append({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "emotions": dict(event.target_emotions),
                "timestamp": event.timestamp,
            })

            if len(state.emotional_memory) > 100:
                state.emotional_memory = state.emotional_memory[-50:]

            self._update_mood(state)
            state.last_updated = _time_module.time()
            return state

    def _update_mood(self, state: EmotionalState):
        """Update mood based on current emotional state."""
        joy = state.emotions.get(EmotionType.JOY.value, EmotionValue(intensity=0.0)).intensity
        sadness = state.emotions.get(EmotionType.SADNESS.value, EmotionValue(intensity=0.0)).intensity
        anger = state.emotions.get(EmotionType.ANGER.value, EmotionValue(intensity=0.0)).intensity
        fear = state.emotions.get(EmotionType.FEAR.value, EmotionValue(intensity=0.0)).intensity

        valence = joy - sadness - anger * 0.5 - fear * 0.3
        arousal = joy * 0.5 + anger * 0.7 + fear * 0.8 + sadness * 0.2

        if valence > 0.6 and arousal > 0.5:
            state.mood = MoodState.ELATED
        elif valence > 0.3 and arousal > 0.3:
            state.mood = MoodState.HAPPY
        elif valence > 0.1:
            state.mood = MoodState.CONTENT
        elif valence > -0.1:
            state.mood = MoodState.NEUTRAL
        elif valence > -0.3:
            state.mood = MoodState.MELANCHOLY
        elif valence > -0.6 and arousal < 0.5:
            state.mood = MoodState.SAD
        elif valence <= -0.6:
            state.mood = MoodState.DEPRESSED
        elif arousal > 0.6 and fear > 0.4:
            state.mood = MoodState.ANXIOUS
        elif arousal > 0.5 and anger > 0.4:
            state.mood = MoodState.IRRITABLE
        elif anger > 0.6:
            state.mood = MoodState.ANGRY

        state.mood_intensity = abs(valence) * 0.7 + arousal * 0.3

        self._mood_history.setdefault(state.agent_id, []).append({
            "mood": state.mood.value,
            "intensity": state.mood_intensity,
            "timestamp": _time_module.time(),
        })

    def decay_emotions(self, agent_id: str, delta_time: float = 0.1):
        """Apply natural decay to all emotions over time."""
        with self._lock:
            state = self._agent_states.get(agent_id)
            if not state:
                return
            for emotion in state.emotions.values():
                if emotion.intensity > 0.05:
                    emotion.intensity *= (1.0 - emotion.decay_rate * delta_time)
                    emotion.intensity = max(0.0, emotion.intensity)
            self._update_mood(state)
            state.last_updated = _time_module.time()

    def get_dominant_emotion(self, agent_id: str) -> Optional[EmotionValue]:
        """Get the currently dominant emotion for an agent."""
        state = self._agent_states.get(agent_id)
        if not state or not state.emotions:
            return None
        return max(state.emotions.values(), key=lambda e: e.intensity)

    def get_emotional_response(self, agent_id: str, situation: str) -> Dict[str, Any]:
        """Generate an emotional response to a described situation."""
        state = self._agent_states.get(agent_id)
        if not state:
            return {"mood": "neutral", "reaction": "neutral", "intensity": 0.0}

        personality = state.personality
        agreeableness = personality.get(PersonalityTrait.AGREEABLENESS.value, 0.5)
        neuroticism = personality.get(PersonalityTrait.NEUROTICISM.value, 0.5)

        mood_valence = {
            MoodState.ELATED: 1.0, MoodState.HAPPY: 0.7, MoodState.CONTENT: 0.4,
            MoodState.NEUTRAL: 0.0, MoodState.MELANCHOLY: -0.2, MoodState.SAD: -0.5,
            MoodState.DEPRESSED: -0.8, MoodState.ANXIOUS: -0.3, MoodState.IRRITABLE: -0.4,
            MoodState.ANGRY: -0.6,
        }.get(state.mood, 0.0)

        situation_keywords = {
            "threat": {"fear": 0.7, "anger": 0.3},
            "reward": {"joy": 0.8, "anticipation": 0.3},
            "loss": {"sadness": 0.8, "fear": 0.2},
            "social": {"trust": 0.5, "joy": 0.3},
            "betrayal": {"anger": 0.8, "sadness": 0.5},
            "discovery": {"surprise": 0.7, "joy": 0.4},
            "challenge": {"anticipation": 0.6, "fear": 0.2},
        }

        reaction_intensity = 0.5 + (neuroticism - 0.5) * 0.4 + (agreeableness - 0.5) * 0.3
        reaction_intensity += mood_valence * 0.2
        reaction_intensity = max(0.1, min(1.0, reaction_intensity))

        return {
            "agent_id": agent_id,
            "mood": state.mood.value,
            "reaction_intensity": reaction_intensity,
            "dominant_emotion": self.get_dominant_emotion(agent_id).emotion_type.value if self.get_dominant_emotion(agent_id) else "neutral",
            "personality_influence": {
                "agreeableness": agreeableness,
                "neuroticism": neuroticism,
            },
        }

    def set_relationship(self, agent_a: str, agent_b: str, affinity: float):
        """Set emotional relationship affinity between two agents."""
        self._emotion_relationships[(agent_a, agent_b)] = max(-1.0, min(1.0, affinity))
        self._emotion_relationships[(agent_b, agent_a)] = max(-1.0, min(1.0, affinity))

    def get_relationship(self, agent_a: str, agent_b: str) -> float:
        """Get the emotional affinity between two agents."""
        return self._emotion_relationships.get((agent_a, agent_b), 0.0)

    def get_agent_state(self, agent_id: str) -> Optional[EmotionalState]:
        """Get the full emotional state of an agent."""
        return self._agent_states.get(agent_id)

    def get_mood_history(self, agent_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get mood history for an agent."""
        history = self._mood_history.get(agent_id, [])
        return history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get emotion system statistics."""
        return {
            "total_agents": len(self._agent_states),
            "total_relationships": len(self._emotion_relationships),
            "mood_distribution": self._get_mood_distribution(),
            "active_agents": sum(1 for s in self._agent_states.values() if s.last_updated > _time_module.time() - 300),
        }

    def _get_mood_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for state in self._agent_states.values():
            mood = state.mood.value
            dist[mood] = dist.get(mood, 0) + 1
        return dist


def get_emotion_system() -> AgentEmotionSystem:
    return AgentEmotionSystem.get_instance()