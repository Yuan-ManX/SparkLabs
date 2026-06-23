"""
SparkLabs Agent - Emotion & Affect Engine

NPC emotion simulation system that models emotional states, mood
dynamics, personality-driven responses, and social affect propagation.
The engine supports emotional contagion through social networks, mood
history tracking, and stimulus-driven emotional state transitions
grounded in personality profiles.

Architecture:
  EmotionEngine (Singleton)
    |-- EmotionVector (multi-dimensional emotion state per entity)
    |-- PersonalityProfile (OCEAN traits with mood baselines)
    |-- SocialEvent (emotional impact propagation between entities)
    |-- MoodHistory (temporal mood tracking with statistics)

Core Capabilities:
  - Set personality profiles with OCEAN trait dimensions
  - Apply emotional stimuli and compute state transitions
  - Model emotional contagion across social networks
  - Track mood history with statistics and trend analysis
  - Record social events with ripple effects on nearby entities
  - Simulate emotion propagation through social graphs
  - Compute current mood states from emotion vectors
  - Generate emotional state snapshots for AI-driven behavior
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EmotionType(Enum):
    """Primary emotion categories based on Plutchik's wheel."""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"


class PersonalityTrait(Enum):
    """OCEAN (Big Five) personality trait dimensions."""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


class MoodState(Enum):
    """Aggregated mood states derived from emotion vectors."""
    ECSTATIC = "ecstatic"
    HAPPY = "happy"
    NEUTRAL = "neutral"
    SAD = "sad"
    DEPRESSED = "depressed"
    ANGRY = "angry"
    CALM = "calm"
    ANXIOUS = "anxious"


class AffectIntensity(Enum):
    """Intensity levels for emotional stimuli and states."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    INTENSE = "intense"
    OVERWHELMING = "overwhelming"


# ---------------------------------------------------------------------------
# Intensity Values
# ---------------------------------------------------------------------------

_INTENSITY_VALUES: Dict[AffectIntensity, float] = {
    AffectIntensity.WEAK: 0.1,
    AffectIntensity.MODERATE: 0.3,
    AffectIntensity.STRONG: 0.55,
    AffectIntensity.INTENSE: 0.8,
    AffectIntensity.OVERWHELMING: 1.0,
}

# Emotion polarity: positive emotions increase mood, negative decrease it
_EMOTION_POLARITY: Dict[EmotionType, float] = {
    EmotionType.JOY: 1.0,
    EmotionType.SADNESS: -1.0,
    EmotionType.ANGER: -0.8,
    EmotionType.FEAR: -0.7,
    EmotionType.SURPRISE: 0.0,
    EmotionType.DISGUST: -0.6,
    EmotionType.TRUST: 0.8,
    EmotionType.ANTICIPATION: 0.3,
}

# Opposing emotion pairs for blending
_EMOTION_OPPOSITES: Dict[EmotionType, EmotionType] = {
    EmotionType.JOY: EmotionType.SADNESS,
    EmotionType.SADNESS: EmotionType.JOY,
    EmotionType.ANGER: EmotionType.FEAR,
    EmotionType.FEAR: EmotionType.ANGER,
    EmotionType.SURPRISE: EmotionType.ANTICIPATION,
    EmotionType.ANTICIPATION: EmotionType.SURPRISE,
    EmotionType.TRUST: EmotionType.DISGUST,
    EmotionType.DISGUST: EmotionType.TRUST,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class EmotionVector:
    """A multi-dimensional emotion state for a single entity.

    Tracks the intensity of each primary emotion type, identifies the
    dominant emotion, and applies time-based decay to return emotions
    to baseline over time.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    emotion_values: Dict[str, float] = field(default_factory=dict)
    dominant_emotion: str = ""
    intensity: float = 0.0
    timestamp: float = field(default_factory=time.time)
    decay_rate: float = 0.05
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "emotion_values": {k: round(v, 4) for k, v in self.emotion_values.items()},
            "dominant_emotion": self.dominant_emotion,
            "intensity": round(self.intensity, 4),
            "timestamp": self.timestamp,
            "decay_rate": self.decay_rate,
            "metadata": self.metadata,
        }

    def compute_dominant(self) -> str:
        if not self.emotion_values:
            self.dominant_emotion = ""
            self.intensity = 0.0
            return ""
        dominant = max(self.emotion_values, key=lambda k: self.emotion_values[k])
        self.dominant_emotion = dominant
        self.intensity = self.emotion_values[dominant]
        return dominant

    def apply_decay(self, now: float) -> None:
        if self.decay_rate <= 0.0:
            return
        elapsed = now - self.timestamp
        if elapsed <= 0.0:
            return
        decay_factor = math.exp(-self.decay_rate * elapsed)
        for emotion in self.emotion_values:
            self.emotion_values[emotion] *= decay_factor
        self.timestamp = now
        self.compute_dominant()

    def set_emotion(self, emotion_type: EmotionType, value: float) -> None:
        self.emotion_values[emotion_type.value] = max(0.0, min(1.0, value))
        self.compute_dominant()

    def get_emotion(self, emotion_type: EmotionType) -> float:
        return self.emotion_values.get(emotion_type.value, 0.0)


@dataclass
class PersonalityProfile:
    """OCEAN personality profile for an entity.

    Defines the baseline mood, emotional volatility (how quickly
    emotions change), empathy (how strongly emotions are received
    from others), and social influence (how strongly emotions are
    projected to others).
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    traits: Dict[str, float] = field(default_factory=dict)
    baseline_mood: float = 0.0
    emotional_volatility: float = 0.5
    empathy: float = 0.5
    social_influence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "traits": {k: round(v, 4) for k, v in self.traits.items()},
            "baseline_mood": round(self.baseline_mood, 4),
            "emotional_volatility": round(self.emotional_volatility, 4),
            "empathy": round(self.empathy, 4),
            "social_influence": round(self.social_influence, 4),
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def get_trait(self, trait: PersonalityTrait) -> float:
        return self.traits.get(trait.value, 0.5)

    def set_trait(self, trait: PersonalityTrait, value: float) -> None:
        self.traits[trait.value] = max(0.0, min(1.0, value))


@dataclass
class SocialEvent:
    """An emotional social event between entities.

    Records the source and target of an emotional interaction, the
    event type, the emotional impact vector, and the ripple radius
    for contagion propagation to nearby entities.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_id: str = ""
    target_id: str = ""
    event_type: str = ""
    emotional_impact: Dict[str, float] = field(default_factory=dict)
    ripple_radius: float = 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "event_type": self.event_type,
            "emotional_impact": {k: round(v, 4) for k, v in self.emotional_impact.items()},
            "ripple_radius": self.ripple_radius,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    def get_impact_magnitude(self) -> float:
        if not self.emotional_impact:
            return 0.0
        return sum(abs(v) for v in self.emotional_impact.values()) / len(self.emotional_impact)


@dataclass
class MoodHistory:
    """Temporal mood tracking for an entity.

    Maintains a history of mood entries with timestamps, computes
    average mood and mood variance, and supports trend analysis
    for detecting mood shifts over time.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    entries: List[Dict[str, Any]] = field(default_factory=list)
    average_mood: float = 0.0
    mood_variance: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "entry_count": len(self.entries),
            "entries": self.entries[-20:],
            "average_mood": round(self.average_mood, 4),
            "mood_variance": round(self.mood_variance, 4),
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def record_mood(self, mood: float, mood_state: str = "") -> None:
        self.entries.append({
            "mood": round(mood, 4),
            "mood_state": mood_state,
            "timestamp": time.time(),
        })
        self._recompute_statistics()

    def _recompute_statistics(self) -> None:
        if not self.entries:
            self.average_mood = 0.0
            self.mood_variance = 0.0
            return
        moods = [e["mood"] for e in self.entries]
        avg = sum(moods) / len(moods)
        self.average_mood = avg
        variance = sum((m - avg) ** 2 for m in moods) / len(moods)
        self.mood_variance = variance

    def get_trend(self, window: int = 10) -> float:
        if len(self.entries) < 2:
            return 0.0
        recent = self.entries[-window:]
        if len(recent) < 2:
            return 0.0
        first = recent[0]["mood"]
        last = recent[-1]["mood"]
        return round(last - first, 4)


# ---------------------------------------------------------------------------
# EmotionEngine
# ---------------------------------------------------------------------------

class EmotionEngine:
    """Thread-safe singleton engine for emotion and affect simulation.

    Manages emotion vectors, personality profiles, social events, and
    mood history for NPC entities. Supports emotional stimulus
    application, contagion computation, ripple propagation, and
    comprehensive mood state analysis.
    """

    _instance: Optional["EmotionEngine"] = None
    _lock = threading.RLock()

    _MAX_EMOTION_VECTORS: int = 5000
    _MAX_PERSONALITIES: int = 5000
    _MAX_SOCIAL_EVENTS: int = 50000
    _MAX_MOOD_HISTORIES: int = 5000
    _MAX_HISTORY_ENTRIES: int = 200
    _DEFAULT_DECAY_RATE: float = 0.05
    _CONTAGION_RADIUS: float = 3.0

    def __init__(self) -> None:
        self._emotion_vectors: Dict[str, EmotionVector] = {}
        self._vectors_by_entity: Dict[str, str] = {}
        self._personalities: Dict[str, PersonalityProfile] = {}
        self._personalities_by_entity: Dict[str, str] = {}
        self._social_events: Dict[str, SocialEvent] = {}
        self._events_by_source: Dict[str, List[str]] = {}
        self._events_by_target: Dict[str, List[str]] = {}
        self._mood_histories: Dict[str, MoodHistory] = {}
        self._histories_by_entity: Dict[str, str] = {}
        self._total_vectors_created: int = 0
        self._total_personalities_created: int = 0
        self._total_events_recorded: int = 0
        self._total_contagions_computed: int = 0
        self._total_ripples_simulated: int = 0

    @classmethod
    def get_instance(cls) -> "EmotionEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Personality Management
    # ------------------------------------------------------------------

    def set_personality(
        self,
        entity_id: str,
        traits: Optional[Dict[str, float]] = None,
        baseline_mood: float = 0.0,
        emotional_volatility: float = 0.5,
        empathy: float = 0.5,
        social_influence: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PersonalityProfile:
        with self._lock:
            self._enforce_max_personalities()

            existing_id = self._personalities_by_entity.get(entity_id)
            if existing_id is not None and existing_id in self._personalities:
                profile = self._personalities[existing_id]
                if traits is not None:
                    profile.traits = {k: max(0.0, min(1.0, v)) for k, v in traits.items()}
                profile.baseline_mood = max(-1.0, min(1.0, baseline_mood))
                profile.emotional_volatility = max(0.0, min(1.0, emotional_volatility))
                profile.empathy = max(0.0, min(1.0, empathy))
                profile.social_influence = max(0.0, min(1.0, social_influence))
                if metadata is not None:
                    profile.metadata.update(metadata)
                return profile

            default_traits = {
                PersonalityTrait.OPENNESS.value: 0.5,
                PersonalityTrait.CONSCIENTIOUSNESS.value: 0.5,
                PersonalityTrait.EXTRAVERSION.value: 0.5,
                PersonalityTrait.AGREEABLENESS.value: 0.5,
                PersonalityTrait.NEUROTICISM.value: 0.5,
            }
            if traits:
                default_traits.update({k: max(0.0, min(1.0, v)) for k, v in traits.items()})

            profile = PersonalityProfile(
                entity_id=entity_id,
                traits=default_traits,
                baseline_mood=max(-1.0, min(1.0, baseline_mood)),
                emotional_volatility=max(0.0, min(1.0, emotional_volatility)),
                empathy=max(0.0, min(1.0, empathy)),
                social_influence=max(0.0, min(1.0, social_influence)),
                metadata=metadata or {},
            )
            self._personalities[profile.id] = profile
            self._personalities_by_entity[entity_id] = profile.id
            self._total_personalities_created += 1
            return profile

    def get_personality(self, entity_id: str) -> Optional[PersonalityProfile]:
        with self._lock:
            pid = self._personalities_by_entity.get(entity_id)
            if pid is None:
                return None
            return self._personalities.get(pid)

    # ------------------------------------------------------------------
    # Emotion Management
    # ------------------------------------------------------------------

    def set_emotion(
        self,
        entity_id: str,
        emotion_type: EmotionType,
        value: float,
        decay_rate: Optional[float] = None,
    ) -> EmotionVector:
        with self._lock:
            self._enforce_max_emotion_vectors()

            existing_id = self._vectors_by_entity.get(entity_id)
            if existing_id is not None and existing_id in self._emotion_vectors:
                vector = self._emotion_vectors[existing_id]
            else:
                vector = EmotionVector(
                    entity_id=entity_id,
                    decay_rate=decay_rate if decay_rate is not None else self._DEFAULT_DECAY_RATE,
                )
                self._emotion_vectors[vector.id] = vector
                self._vectors_by_entity[entity_id] = vector.id
                self._total_vectors_created += 1

            vector.set_emotion(emotion_type, max(0.0, min(1.0, value)))
            if decay_rate is not None:
                vector.decay_rate = decay_rate
            vector.timestamp = time.time()
            return vector

    def apply_stimulus(
        self,
        entity_id: str,
        stimulus: Dict[str, float],
        intensity: AffectIntensity = AffectIntensity.MODERATE,
    ) -> Optional[EmotionVector]:
        with self._lock:
            vector = self._get_or_create_vector(entity_id)
            personality = self.get_personality(entity_id)

            intensity_value = _INTENSITY_VALUES.get(intensity, 0.3)
            volatility = personality.emotional_volatility if personality else 0.5

            effective_scale = intensity_value * volatility

            for emotion_key, raw_value in stimulus.items():
                current = vector.emotion_values.get(emotion_key, 0.0)
                new_value = current + raw_value * effective_scale
                vector.emotion_values[emotion_key] = max(0.0, min(1.0, new_value))

                opposite = _EMOTION_OPPOSITES.get(
                    EmotionType(emotion_key) if emotion_key in [e.value for e in EmotionType] else None,
                    None,
                )
                if opposite is not None and opposite.value != emotion_key:
                    opp_current = vector.emotion_values.get(opposite.value, 0.0)
                    opp_new = opp_current - raw_value * effective_scale * 0.5
                    vector.emotion_values[opposite.value] = max(0.0, min(1.0, opp_new))

            vector.timestamp = time.time()
            vector.compute_dominant()

            self._update_mood_history(entity_id, vector)

            return vector

    def get_emotional_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            vector_id = self._vectors_by_entity.get(entity_id)
            if vector_id is None:
                return None
            vector = self._emotion_vectors.get(vector_id)
            if vector is None:
                return None
            return vector.to_dict()

    # ------------------------------------------------------------------
    # Mood Computation
    # ------------------------------------------------------------------

    def get_current_mood(self, entity_id: str) -> Dict[str, Any]:
        with self._lock:
            vector_id = self._vectors_by_entity.get(entity_id)
            if vector_id is None:
                return {"entity_id": entity_id, "mood": 0.0, "mood_state": MoodState.NEUTRAL.value}

            vector = self._emotion_vectors.get(vector_id)
            if vector is None:
                return {"entity_id": entity_id, "mood": 0.0, "mood_state": MoodState.NEUTRAL.value}

            mood_value = self._compute_mood_from_vector(vector)
            mood_state = self._classify_mood(mood_value)

            return {
                "entity_id": entity_id,
                "mood": round(mood_value, 4),
                "mood_state": mood_state.value,
                "dominant_emotion": vector.dominant_emotion,
                "intensity": round(vector.intensity, 4),
                "timestamp": vector.timestamp,
            }

    def get_mood_history(self, entity_id: str) -> Optional[MoodHistory]:
        with self._lock:
            history_id = self._histories_by_entity.get(entity_id)
            if history_id is None:
                return None
            return self._mood_histories.get(history_id)

    # ------------------------------------------------------------------
    # Social Events
    # ------------------------------------------------------------------

    def record_social_event(
        self,
        source_id: str,
        target_id: str,
        event_type: str = "",
        emotional_impact: Optional[Dict[str, float]] = None,
        ripple_radius: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SocialEvent:
        with self._lock:
            self._enforce_max_social_events()

            event = SocialEvent(
                source_id=source_id,
                target_id=target_id,
                event_type=event_type,
                emotional_impact=emotional_impact or {},
                ripple_radius=ripple_radius,
                metadata=metadata or {},
            )
            self._social_events[event.id] = event
            self._total_events_recorded += 1

            self._list_append(self._events_by_source, source_id, event.id)
            self._list_append(self._events_by_target, target_id, event.id)

            return event

    # ------------------------------------------------------------------
    # Contagion and Ripple
    # ------------------------------------------------------------------

    def compute_contagion(
        self,
        source_id: str,
        target_ids: List[str],
        radius: float = 3.0,
    ) -> Dict[str, Any]:
        with self._lock:
            self._total_contagions_computed += 1

            source_vector = self._get_or_create_vector(source_id)
            source_personality = self.get_personality(source_id)

            influence = source_personality.social_influence if source_personality else 0.5

            results: List[Dict[str, Any]] = []
            for target_id in target_ids:
                if target_id == source_id:
                    continue

                target_vector = self._get_or_create_vector(target_id)
                target_personality = self.get_personality(target_id)
                empathy = target_personality.empathy if target_personality else 0.5

                contagion_strength = influence * empathy * 0.3

                distance_factor = 1.0 / max(1.0, radius)
                effective_strength = contagion_strength * distance_factor

                for emotion_key, source_value in source_vector.emotion_values.items():
                    if source_value < 0.1:
                        continue
                    current = target_vector.emotion_values.get(emotion_key, 0.0)
                    delta = source_value * effective_strength * 0.3
                    target_vector.emotion_values[emotion_key] = max(0.0, min(1.0, current + delta))

                target_vector.timestamp = time.time()
                target_vector.compute_dominant()

                results.append({
                    "target_id": target_id,
                    "contagion_strength": round(effective_strength, 4),
                    "dominant_emotion": target_vector.dominant_emotion,
                    "intensity": round(target_vector.intensity, 4),
                })

                self._update_mood_history(target_id, target_vector)

            return {
                "source_id": source_id,
                "target_count": len(results),
                "radius": radius,
                "results": results,
            }

    def simulate_ripple(
        self,
        event_id: str,
        all_entity_ids: List[str],
    ) -> Dict[str, Any]:
        with self._lock:
            self._total_ripples_simulated += 1

            event = self._social_events.get(event_id)
            if event is None:
                return {"error": "Event not found"}

            affected: List[Dict[str, Any]] = []

            for entity_id in all_entity_ids:
                if entity_id == event.source_id or entity_id == event.target_id:
                    continue

                distance = abs(hash(entity_id) % 100) / 100.0 * event.ripple_radius
                if distance > event.ripple_radius:
                    continue

                vector = self._get_or_create_vector(entity_id)
                personality = self.get_personality(entity_id)
                empathy = personality.empathy if personality else 0.5

                ripple_factor = (1.0 - distance / event.ripple_radius) * empathy * 0.15

                for emotion_key, impact_value in event.emotional_impact.items():
                    current = vector.emotion_values.get(emotion_key, 0.0)
                    new_value = current + impact_value * ripple_factor
                    vector.emotion_values[emotion_key] = max(0.0, min(1.0, new_value))

                vector.timestamp = time.time()
                vector.compute_dominant()

                affected.append({
                    "entity_id": entity_id,
                    "distance": round(distance, 4),
                    "ripple_factor": round(ripple_factor, 4),
                    "dominant_emotion": vector.dominant_emotion,
                })

                if abs(ripple_factor) > 0.01:
                    self._update_mood_history(entity_id, vector)

            return {
                "event_id": event_id,
                "event_type": event.event_type,
                "source_id": event.source_id,
                "target_id": event.target_id,
                "ripple_radius": event.ripple_radius,
                "affected_count": len(affected),
                "affected_entities": affected,
            }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            emotion_dist: Dict[str, int] = {}
            for vector in self._emotion_vectors.values():
                dom = vector.dominant_emotion or "none"
                emotion_dist[dom] = emotion_dist.get(dom, 0) + 1

            mood_state_dist: Dict[str, int] = {}
            for entity_id in self._vectors_by_entity:
                mood_info = self.get_current_mood(entity_id)
                ms = mood_info.get("mood_state", "unknown")
                mood_state_dist[ms] = mood_state_dist.get(ms, 0) + 1

            return {
                "total_emotion_vectors_created": self._total_vectors_created,
                "total_emotion_vectors_stored": len(self._emotion_vectors),
                "total_personalities_created": self._total_personalities_created,
                "total_personalities_stored": len(self._personalities),
                "total_social_events_recorded": self._total_events_recorded,
                "total_social_events_stored": len(self._social_events),
                "total_contagions_computed": self._total_contagions_computed,
                "total_ripples_simulated": self._total_ripples_simulated,
                "total_mood_histories": len(self._mood_histories),
                "dominant_emotion_distribution": emotion_dist,
                "mood_state_distribution": mood_state_dist,
                "max_emotion_vectors": self._MAX_EMOTION_VECTORS,
                "max_personalities": self._MAX_PERSONALITIES,
                "max_social_events": self._MAX_SOCIAL_EVENTS,
            }

    def reset(self) -> None:
        with self._lock:
            self._emotion_vectors.clear()
            self._vectors_by_entity.clear()
            self._personalities.clear()
            self._personalities_by_entity.clear()
            self._social_events.clear()
            self._events_by_source.clear()
            self._events_by_target.clear()
            self._mood_histories.clear()
            self._histories_by_entity.clear()
            self._total_vectors_created = 0
            self._total_personalities_created = 0
            self._total_events_recorded = 0
            self._total_contagions_computed = 0
            self._total_ripples_simulated = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _get_or_create_vector(self, entity_id: str) -> EmotionVector:
        existing_id = self._vectors_by_entity.get(entity_id)
        if existing_id is not None and existing_id in self._emotion_vectors:
            return self._emotion_vectors[existing_id]

        self._enforce_max_emotion_vectors()
        vector = EmotionVector(
            entity_id=entity_id,
            decay_rate=self._DEFAULT_DECAY_RATE,
        )
        self._emotion_vectors[vector.id] = vector
        self._vectors_by_entity[entity_id] = vector.id
        self._total_vectors_created += 1
        return vector

    def _compute_mood_from_vector(self, vector: EmotionVector) -> float:
        if not vector.emotion_values:
            return 0.0
        total_polarity = 0.0
        total_weight = 0.0
        for emotion_key, value in vector.emotion_values.items():
            try:
                emotion_type = EmotionType(emotion_key)
                polarity = _EMOTION_POLARITY.get(emotion_type, 0.0)
            except ValueError:
                polarity = 0.0
            total_polarity += polarity * value
            total_weight += value
        if total_weight == 0.0:
            return 0.0
        return max(-1.0, min(1.0, total_polarity / total_weight))

    def _classify_mood(self, mood_value: float) -> MoodState:
        if mood_value >= 0.8:
            return MoodState.ECSTATIC
        if mood_value >= 0.4:
            return MoodState.HAPPY
        if mood_value >= 0.1:
            return MoodState.CALM
        if mood_value >= -0.1:
            return MoodState.NEUTRAL
        if mood_value >= -0.4:
            return MoodState.ANXIOUS
        if mood_value >= -0.6:
            return MoodState.SAD
        if mood_value >= -0.8:
            return MoodState.ANGRY
        return MoodState.DEPRESSED

    def _update_mood_history(self, entity_id: str, vector: EmotionVector) -> None:
        mood = self._compute_mood_from_vector(vector)
        mood_state = self._classify_mood(mood)

        history_id = self._histories_by_entity.get(entity_id)
        if history_id is None:
            self._enforce_max_mood_histories()
            history = MoodHistory(entity_id=entity_id)
            self._mood_histories[history.id] = history
            self._histories_by_entity[entity_id] = history.id
            history_id = history.id

        history = self._mood_histories.get(history_id)
        if history is not None:
            history.record_mood(mood, mood_state.value)
            if len(history.entries) > self._MAX_HISTORY_ENTRIES:
                history.entries = history.entries[-self._MAX_HISTORY_ENTRIES:]

    def _enforce_max_emotion_vectors(self) -> None:
        if len(self._emotion_vectors) >= self._MAX_EMOTION_VECTORS:
            sorted_vectors = sorted(
                self._emotion_vectors.items(),
                key=lambda item: item[1].timestamp,
            )
            overflow = len(self._emotion_vectors) - self._MAX_EMOTION_VECTORS + 1
            for vid, vector in sorted_vectors[:overflow]:
                self._emotion_vectors.pop(vid, None)
                if self._vectors_by_entity.get(vector.entity_id) == vid:
                    del self._vectors_by_entity[vector.entity_id]

    def _enforce_max_personalities(self) -> None:
        if len(self._personalities) >= self._MAX_PERSONALITIES:
            sorted_profiles = sorted(
                self._personalities.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._personalities) - self._MAX_PERSONALITIES + 1
            for pid, profile in sorted_profiles[:overflow]:
                self._personalities.pop(pid, None)
                if self._personalities_by_entity.get(profile.entity_id) == pid:
                    del self._personalities_by_entity[profile.entity_id]

    def _enforce_max_social_events(self) -> None:
        if len(self._social_events) >= self._MAX_SOCIAL_EVENTS:
            sorted_events = sorted(
                self._social_events.items(),
                key=lambda item: item[1].timestamp,
            )
            overflow = len(self._social_events) - self._MAX_SOCIAL_EVENTS + 1
            for eid, event in sorted_events[:overflow]:
                self._social_events.pop(eid, None)
                for lst in [self._events_by_source.get(event.source_id),
                           self._events_by_target.get(event.target_id)]:
                    if lst and eid in lst:
                        lst.remove(eid)

    def _enforce_max_mood_histories(self) -> None:
        if len(self._mood_histories) >= self._MAX_MOOD_HISTORIES:
            sorted_histories = sorted(
                self._mood_histories.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._mood_histories) - self._MAX_MOOD_HISTORIES + 1
            for hid, history in sorted_histories[:overflow]:
                self._mood_histories.pop(hid, None)
                if self._histories_by_entity.get(history.entity_id) == hid:
                    del self._histories_by_entity[history.entity_id]

    @staticmethod
    def _list_append(index: Dict[str, List[str]], key: str, entry_id: str) -> None:
        if key not in index:
            index[key] = []
        if entry_id not in index[key]:
            index[key].append(entry_id)


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_emotion_engine() -> EmotionEngine:
    """Return the singleton EmotionEngine instance."""
    return EmotionEngine.get_instance()