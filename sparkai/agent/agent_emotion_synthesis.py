"""
SparkLabs Agent - Emotion Synthesis Engine

Computational emotion synthesis system for autonomous agents. Models
multi-dimensional emotional states, mood transitions, personality-driven
emotional responses, and emotional contagion in agent populations.

Architecture:
  AgentEmotionSynthesis (Singleton)
    |-- Emotion State Machine (PAD model: Pleasure-Arousal-Dominance)
    |-- Mood Controller (long-term mood with decay and inertia)
    |-- Emotion Trigger System (event-to-emotion mapping)
    |-- Expression Generator (behavioral/verbal emotional expression)
    |-- Emotion Contagion (spread of emotions in groups)
    |-- Emotion Memory (past emotional experiences and trauma)
    |-- Coping Strategy Engine (agent stress management)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class EmotionDimension(Enum):
    PLEASURE = "pleasure"
    AROUSAL = "arousal"
    DOMINANCE = "dominance"


class MoodType(Enum):
    JOYFUL = "joyful"
    MELANCHOLIC = "melancholic"
    IRRITABLE = "irritable"
    SERENE = "serene"
    ANXIOUS = "anxious"
    ENERGETIC = "energetic"
    FATIGUED = "fatigued"
    NEUTRAL = "neutral"


class EmotionEvent(Enum):
    SOCIAL_BOND = "social_bond"
    SOCIAL_REJECTION = "social_rejection"
    ACHIEVEMENT = "achievement"
    FAILURE = "failure"
    THREAT = "threat"
    SAFETY = "safety"
    SURPRISE = "surprise"
    LOSS = "loss"
    GAIN = "gain"
    INJUSTICE = "injustice"
    GRATITUDE = "gratitude"
    BETRAYAL = "betrayal"


class CopingStrategy(Enum):
    PROBLEM_FOCUSED = "problem_focused"
    EMOTION_FOCUSED = "emotion_focused"
    AVOIDANCE = "avoidance"
    SOCIAL_SUPPORT = "social_support"
    REAPPRAISAL = "reappraisal"
    ACCEPTANCE = "acceptance"


@dataclass
class EmotionState:
    """PAD (Pleasure-Arousal-Dominance) emotional state."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pleasure: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    def clamp(self) -> None:
        self.pleasure = max(-1.0, min(1.0, self.pleasure))
        self.arousal = max(-1.0, min(1.0, self.arousal))
        self.dominance = max(-1.0, min(1.0, self.dominance))

    def intensity(self) -> float:
        return math.sqrt(self.pleasure ** 2 + self.arousal ** 2 + self.dominance ** 2) / math.sqrt(3)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pleasure": round(self.pleasure, 3),
            "arousal": round(self.arousal, 3),
            "dominance": round(self.dominance, 3),
            "intensity": round(self.intensity(), 3),
            "timestamp": self.timestamp,
        }


@dataclass
class EmotionMemory:
    """Record of a past emotional experience."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    event: EmotionEvent = EmotionEvent.SURPRISE
    intensity: float = 0.5
    state_before: Optional[EmotionState] = None
    state_after: Optional[EmotionState] = None
    context: str = ""
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "event": self.event.value,
            "intensity": round(self.intensity, 3),
            "context": self.context,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentEmotionProfile:
    """Emotional profile for an individual agent."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    pleasure: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0
    mood: MoodType = MoodType.NEUTRAL
    mood_intensity: float = 0.5
    emotional_stability: float = 0.5
    empathy: float = 0.5
    expression_style: str = "moderate"
    memories: List[EmotionMemory] = field(default_factory=list)
    current_coping: Optional[CopingStrategy] = None
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "pleasure": round(self.pleasure, 3),
            "arousal": round(self.arousal, 3),
            "dominance": round(self.dominance, 3),
            "mood": self.mood.value,
            "mood_intensity": round(self.mood_intensity, 3),
            "emotional_stability": round(self.emotional_stability, 3),
            "empathy": round(self.empathy, 3),
            "expression_style": self.expression_style,
            "memory_count": len(self.memories),
        }


class AgentEmotionSynthesis:
    """
    Emotion synthesis engine for autonomous agents.
    Singleton pattern with thread-safe initialization.
    """

    _instance: Optional["AgentEmotionSynthesis"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "AgentEmotionSynthesis":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentEmotionSynthesis":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._profiles: Dict[str, AgentEmotionProfile] = {}
        self._event_handlers: Dict[EmotionEvent, Callable] = {}
        self._contagion_radius: float = 50.0
        self._contagion_rate: float = 0.15
        self._mood_decay_rate: float = 0.01
        self._total_events: int = 0
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        self._event_handlers = {
            EmotionEvent.SOCIAL_BOND: lambda p: (0.3, 0.2, 0.1),
            EmotionEvent.SOCIAL_REJECTION: lambda p: (-0.3, 0.1, -0.2),
            EmotionEvent.ACHIEVEMENT: lambda p: (0.4, 0.3, 0.3),
            EmotionEvent.FAILURE: lambda p: (-0.3, -0.1, -0.3),
            EmotionEvent.THREAT: lambda p: (-0.2, 0.4, -0.3),
            EmotionEvent.SAFETY: lambda p: (0.3, -0.3, 0.2),
            EmotionEvent.SURPRISE: lambda p: (0.0, 0.5, 0.0),
            EmotionEvent.LOSS: lambda p: (-0.5, -0.2, -0.4),
            EmotionEvent.GAIN: lambda p: (0.4, 0.2, 0.2),
            EmotionEvent.INJUSTICE: lambda p: (-0.4, 0.3, -0.3),
            EmotionEvent.GRATITUDE: lambda p: (0.3, 0.1, 0.1),
            EmotionEvent.BETRAYAL: lambda p: (-0.5, 0.3, -0.4),
        }

    def register_agent(
        self,
        agent_id: str,
        initial_pleasure: float = 0.0,
        initial_arousal: float = 0.0,
        initial_dominance: float = 0.0,
        emotional_stability: float = 0.5,
        empathy: float = 0.5,
        expression_style: str = "moderate",
    ) -> AgentEmotionProfile:
        with self._lock:
            profile = AgentEmotionProfile(
                agent_id=agent_id,
                pleasure=initial_pleasure,
                arousal=initial_arousal,
                dominance=initial_dominance,
                emotional_stability=emotional_stability,
                empathy=empathy,
                expression_style=expression_style,
            )
            self._profiles[agent_id] = profile
            return profile

    def trigger_event(
        self,
        agent_id: str,
        event: EmotionEvent,
        intensity: float = 0.5,
        context: str = "",
    ) -> Optional[EmotionState]:
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                return None

            handler = self._event_handlers.get(event)
            if handler is None:
                return None

            dp, da, dd = handler(profile)
            stability_factor = 1.0 - profile.emotional_stability * 0.5
            intensity_scaled = intensity * stability_factor

            state_before = EmotionState(
                pleasure=profile.pleasure,
                arousal=profile.arousal,
                dominance=profile.dominance,
            )

            profile.pleasure += dp * intensity_scaled
            profile.arousal += da * intensity_scaled
            profile.dominance += dd * intensity_scaled

            state_after = EmotionState(
                pleasure=profile.pleasure,
                arousal=profile.arousal,
                dominance=profile.dominance,
            )
            state_after.clamp()
            profile.pleasure = state_after.pleasure
            profile.arousal = state_after.arousal
            profile.dominance = state_after.dominance

            memory = EmotionMemory(
                agent_id=agent_id,
                event=event,
                intensity=intensity,
                state_before=state_before,
                state_after=state_after,
                context=context,
            )
            profile.memories.append(memory)
            if len(profile.memories) > 100:
                profile.memories = profile.memories[-100:]

            self._total_events += 1
            self._update_mood(profile)
            return state_after

    def _update_mood(self, profile: AgentEmotionProfile) -> None:
        p = profile.pleasure
        a = profile.arousal
        d = profile.dominance

        if p > 0.3 and a > 0.3:
            profile.mood = MoodType.JOYFUL
        elif p > 0.3 and a < -0.3:
            profile.mood = MoodType.SERENE
        elif p < -0.3 and a > 0.3:
            profile.mood = MoodType.IRRITABLE
        elif p < -0.3 and a < -0.3:
            profile.mood = MoodType.MELANCHOLIC
        elif a > 0.3 and d < -0.3:
            profile.mood = MoodType.ANXIOUS
        elif a > 0.3:
            profile.mood = MoodType.ENERGETIC
        elif a < -0.3:
            profile.mood = MoodType.FATIGUED
        else:
            profile.mood = MoodType.NEUTRAL

        profile.mood_intensity = (abs(p) + abs(a) + abs(d)) / 3.0

    def apply_decay(self, agent_id: str) -> None:
        with self._lock:
            profile = self._profiles.get(agent_id)
            if profile is None:
                return
            decay = self._mood_decay_rate * (1.0 - profile.emotional_stability * 0.5)
            profile.pleasure *= (1.0 - decay)
            profile.arousal *= (1.0 - decay)
            profile.dominance *= (1.0 - decay)

    def apply_contagion(
        self,
        target_id: str,
        source_id: str,
        distance: float,
    ) -> None:
        with self._lock:
            target = self._profiles.get(target_id)
            source = self._profiles.get(source_id)
            if target is None or source is None:
                return
            if distance > self._contagion_radius:
                return

            factor = (1.0 - distance / self._contagion_radius) * self._contagion_rate * target.empathy
            target.pleasure += (source.pleasure - target.pleasure) * factor
            target.arousal += (source.arousal - target.arousal) * factor
            target.dominance += (source.dominance - target.dominance) * factor * 0.5

    def get_profile(self, agent_id: str) -> Optional[AgentEmotionProfile]:
        return self._profiles.get(agent_id)

    def get_emotion_state(self, agent_id: str) -> Optional[EmotionState]:
        profile = self._profiles.get(agent_id)
        if profile is None:
            return None
        return EmotionState(
            pleasure=profile.pleasure,
            arousal=profile.arousal,
            dominance=profile.dominance,
        )

    def get_mood(self, agent_id: str) -> Optional[MoodType]:
        profile = self._profiles.get(agent_id)
        if profile is None:
            return None
        return profile.mood

    def get_memories(
        self, agent_id: str, limit: int = 10
    ) -> List[EmotionMemory]:
        profile = self._profiles.get(agent_id)
        if profile is None:
            return []
        return profile.memories[-limit:]

    def get_group_mood(
        self, agent_ids: List[str]
    ) -> Dict[str, Any]:
        profiles = [self._profiles.get(aid) for aid in agent_ids if self._profiles.get(aid)]
        if not profiles:
            return {"dominant_mood": "neutral", "average_intensity": 0.0, "agent_count": 0}

        avg_p = sum(p.pleasure for p in profiles) / len(profiles)
        avg_a = sum(p.arousal for p in profiles) / len(profiles)
        avg_i = sum(p.mood_intensity for p in profiles) / len(profiles)

        mood_counts: Dict[MoodType, int] = {}
        for p in profiles:
            mood_counts[p.mood] = mood_counts.get(p.mood, 0) + 1
        dominant_mood = max(mood_counts, key=mood_counts.get)

        return {
            "dominant_mood": dominant_mood.value,
            "average_pleasure": round(avg_p, 3),
            "average_arousal": round(avg_a, 3),
            "average_intensity": round(avg_i, 3),
            "agent_count": len(profiles),
            "mood_distribution": {k.value: v for k, v in mood_counts.items()},
        }

    def recommend_coping(self, agent_id: str) -> Optional[CopingStrategy]:
        profile = self._profiles.get(agent_id)
        if profile is None:
            return None
        if profile.pleasure < -0.5:
            if profile.arousal > 0.3:
                return CopingStrategy.EMOTION_FOCUSED
            return CopingStrategy.SOCIAL_SUPPORT
        if profile.dominance < -0.5:
            return CopingStrategy.PROBLEM_FOCUSED
        return None

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_agents": len(self._profiles),
                "total_events": self._total_events,
                "total_memories": sum(len(p.memories) for p in self._profiles.values()),
                "contagion_radius": self._contagion_radius,
                "contagion_rate": self._contagion_rate,
                "mood_decay_rate": self._mood_decay_rate,
            }

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._profiles.values()]


def get_emotion_synthesis() -> AgentEmotionSynthesis:
    return AgentEmotionSynthesis.get_instance()