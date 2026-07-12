"""
SparkLabs Engine - NPC Dream Simulation System

A novel AI-native module that simulates the inner dream life of non-player
characters while the player is logged off. When a player disconnects, the
world keeps breathing: NPCs retire to sleep, replay the events of their day,
weave those events into symbolic dream sequences, consolidate fragile
short-term impressions into durable long-term memory, and wake up with
shifted moods, modified behavioral tendencies, and occasionally a prophecy
they feel compelled to act upon.

The system is intentionally distinct from ordinary NPC scheduling. Rather
than freezing NPCs in place until the player returns, it treats offline time
as a generative phase where each NPC's accumulated experiences are
reprocessed through a layer of dream symbolism, archetypal themes, and
emotional resonance. The result is a cast of characters whose personalities
drift organically over many play sessions without any manual authoring.

Architecture:
  NPCDreamSimulationSystem (thread-safe singleton)
    |-- DreamMemory          - a single experience or recalled fragment
    |-- DreamSymbol          - symbolic stand-in for a class of experiences
    |-- DreamArchetype       - recurring thematic pattern woven into dreams
    |-- DreamSequence        - one full dream from onset to waking
    |-- DreamInterpretation  - analytical reading of a dream's meaning
    |-- DreamOutcome         - behavioral and mood deltas applied on waking
    |-- NPCDreamProfile      - per-NPC dream state, journal, and memory
    |-- NPCSleepSchedule     - sleep/wake timing and state machine
    |-- DreamConfig          - tunable system parameters
    |-- DreamStats           - rolled-up counters across the whole system
    |-- DreamSnapshot        - point-in-time capture of system state
    |-- DreamEvent           - recorded notification for auditing/tick log

Core Capabilities:
  - register_npc / remove_npc: manage the roster of dreaming NPCs
  - add_experience / process_experiences / consolidate_memories: feed daily
    events into the memory pipeline and fold them into long-term recall
  - start_dream / generate_dream_sequence / end_dream: drive a full dream
    lifecycle, producing a narrative, symbols, and an outcome
  - register_symbol / register_archetype: extend the symbolic vocabulary
  - interpret_dream: produce an analytical reading of a finished dream
  - apply_dream_outcome / get_npc_behavior_modifiers: push dream results
    back into NPC behavior so the waking world reflects what was dreamed
  - share_dream / get_shared_dreams: let NPCs exchange dreams socially
  - set_sleep_schedule / advance_sleep_state: manage the sleep state machine
  - tick: advance every NPC's sleep cycle and trigger dreams automatically
  - prophetic dreams, nightmares, and a per-NPC dream journal

Usage:
    system = get_npc_dream_simulation_system()
    ok, msg, profile = system.register_npc("npc_elve", "Elara")
    system.add_experience("npc_elve", MemoryType.SOCIAL,
                          "Shared a meal with the hero", EmotionType.JOY, 0.7)
    report = system.tick(120.0)        # advance two simulated minutes
    journal = system.get_dream_journal("npc_elve")
"""

from __future__ import annotations

import random
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DreamPhase(str, Enum):
    """Progressive stages a dream moves through from onset to waking."""
    ONSET = "onset"
    LIGHT = "light"
    DEEP = "deep"
    LUCID = "lucid"
    RESOLUTION = "resolution"
    WAKING = "waking"


class DreamType(str, Enum):
    """Broad classification of the narrative flavor of a dream."""
    ORDINARY = "ordinary"
    REPLAY = "replay"
    SYMBOLIC = "symbolic"
    NIGHTMARE = "nightmare"
    PROPHETIC = "prophetic"
    LUCID = "lucid"
    SHARED = "shared"
    RECURRING = "recurring"


class DreamIntensity(str, Enum):
    """How strongly a dream is felt, which scales its downstream effects."""
    FAINT = "faint"
    MILD = "mild"
    VIVID = "vivid"
    INTENSE = "intense"
    OVERWHELMING = "overwhelming"


class DreamStatus(str, Enum):
    """Lifecycle state of a DreamSequence record."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    INTERPRETED = "interpreted"


class MemoryType(str, Enum):
    """Functional category of an experience an NPC can accumulate."""
    SOCIAL = "social"
    COMBAT = "combat"
    EXPLORATION = "exploration"
    COMMERCE = "commerce"
    CRAFTING = "crafting"
    LOSS = "loss"
    DISCOVERY = "discovery"
    ROMANCE = "romance"
    FEAR = "fear"
    ACHIEVEMENT = "achievement"
    ROUTINE = "routine"
    MYSTICAL = "mystical"


class EmotionType(str, Enum):
    """Emotional valence tagged onto memories and dreams."""
    JOY = "joy"
    TRUST = "trust"
    FEAR = "fear"
    SURPRISE = "surprise"
    SADNESS = "sadness"
    DISGUST = "disgust"
    ANGER = "anger"
    ANTICIPATION = "anticipation"
    AWE = "awe"
    SERENITY = "serenity"
    LONGING = "longing"
    SHAME = "shame"


class DreamEventKind(str, Enum):
    """Kind of event emitted into the audit log by the system."""
    NPC_REGISTERED = "npc_registered"
    NPC_REMOVED = "npc_removed"
    DREAM_STARTED = "dream_started"
    DREAM_ENDED = "dream_ended"
    EXPERIENCE_ADDED = "experience_added"
    MEMORIES_CONSOLIDATED = "memories_consolidated"
    DREAM_INTERPRETED = "dream_interpreted"
    OUTCOME_APPLIED = "outcome_applied"
    DREAM_SHARED = "dream_shared"
    SLEEP_STATE_CHANGED = "sleep_state_changed"
    PROPHETIC_DREAM = "prophetic_dream"
    NIGHTMARE_TRIGGERED = "nightmare_triggered"
    SYSTEM_RESET = "system_reset"
    CONFIG_UPDATED = "config_updated"
    ARCHETYPE_REGISTERED = "archetype_registered"
    SYMBOL_REGISTERED = "symbol_registered"


class NPCSleepState(str, Enum):
    """States in the NPC sleep state machine driven by the tick loop."""
    AWAKE = "awake"
    DROWSY = "drowsy"
    SLEEPING = "sleeping"
    DREAMING = "dreaming"
    WAKING = "waking"


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

# Maps each MemoryType to the emotions most commonly associated with it.
# Used during dream generation to pick symbols whose emotional palette
# overlaps with the NPC's recent experiences.
_MEMORY_EMOTION_AFFINITY: Dict[MemoryType, List[EmotionType]] = {
    MemoryType.SOCIAL: [EmotionType.JOY, EmotionType.TRUST, EmotionType.LONGING],
    MemoryType.COMBAT: [EmotionType.FEAR, EmotionType.ANGER, EmotionType.SURPRISE],
    MemoryType.EXPLORATION: [EmotionType.SURPRISE, EmotionType.ANTICIPATION, EmotionType.AWE],
    MemoryType.COMMERCE: [EmotionType.ANTICIPATION, EmotionType.TRUST, EmotionType.JOY],
    MemoryType.CRAFTING: [EmotionType.SERENITY, EmotionType.JOY, EmotionType.ANTICIPATION],
    MemoryType.LOSS: [EmotionType.SADNESS, EmotionType.SHAME, EmotionType.LONGING],
    MemoryType.DISCOVERY: [EmotionType.SURPRISE, EmotionType.AWE, EmotionType.JOY],
    MemoryType.ROMANCE: [EmotionType.JOY, EmotionType.LONGING, EmotionType.TRUST],
    MemoryType.FEAR: [EmotionType.FEAR, EmotionType.SADNESS, EmotionType.SHAME],
    MemoryType.ACHIEVEMENT: [EmotionType.JOY, EmotionType.AWE, EmotionType.TRUST],
    MemoryType.ROUTINE: [EmotionType.SERENITY, EmotionType.ANTICIPATION, EmotionType.JOY],
    MemoryType.MYSTICAL: [EmotionType.AWE, EmotionType.FEAR, EmotionType.SURPRISE],
}

# Emotions considered negative for nightmare-threshold calculations.
_NEGATIVE_EMOTIONS: frozenset = frozenset({
    EmotionType.FEAR, EmotionType.SADNESS, EmotionType.DISGUST,
    EmotionType.ANGER, EmotionType.SHAME,
})

# Numeric intensity weight per DreamIntensity label, used when aggregating
# the emotional charge of a dream.
_INTENSITY_WEIGHT: Dict[DreamIntensity, float] = {
    DreamIntensity.FAINT: 0.2,
    DreamIntensity.MILD: 0.4,
    DreamIntensity.VIVID: 0.6,
    DreamIntensity.INTENSE: 0.8,
    DreamIntensity.OVERWHELMING: 1.0,
}

# Ordered sleep-state progression used by advance_sleep_state.
_SLEEP_ORDER: List[NPCSleepState] = [
    NPCSleepState.AWAKE,
    NPCSleepState.DROWSY,
    NPCSleepState.SLEEPING,
    NPCSleepState.DREAMING,
    NPCSleepState.WAKING,
]

# Ordered dream-phase progression used while a dream is active.
_PHASE_ORDER: List[DreamPhase] = [
    DreamPhase.ONSET,
    DreamPhase.LIGHT,
    DreamPhase.DEEP,
    DreamPhase.LUCID,
    DreamPhase.RESOLUTION,
    DreamPhase.WAKING,
]

# Mood delta applied per dream type when an outcome is computed. Values are
# additive to the NPC mood (clamped to [0, 1] afterwards).
_DREAM_TYPE_MOOD_DELTA: Dict[DreamType, float] = {
    DreamType.ORDINARY: 0.02,
    DreamType.REPLAY: 0.01,
    DreamType.SYMBOLIC: 0.04,
    DreamType.NIGHTMARE: -0.12,
    DreamType.PROPHETIC: 0.06,
    DreamType.LUCID: 0.08,
    DreamType.SHARED: 0.05,
    DreamType.RECURRING: 0.0,
}

# Fragments used to assemble dream narratives during generation.
_NARRATIVE_OPENERS: List[str] = [
    "A hush fell over the mindscape as",
    "In the soft light of the inner world,",
    "The dreamer drifted past a threshold where",
    "Shadows rearranged themselves until",
    "A familiar melody unravelled and",
]

_NARRATIVE_CLOSERS: List[str] = [
    "and the vision dissolved into morning light.",
    "before the scene folded quietly into stillness.",
    "leaving behind a single lingering image.",
    "as the dreamer turned toward the waking shore.",
    "and the last echo faded into white silence.",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DreamMemory:
    """A single experience or recalled fragment belonging to an NPC.

    Short-term experiences accumulate during the day and are later folded
    into long-term memory during the consolidation pass. Each memory
    carries an emotion and an intensity that influence dream generation.
    """
    memory_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    npc_id: str = ""
    memory_type: MemoryType = MemoryType.ROUTINE
    description: str = ""
    emotion: EmotionType = EmotionType.SERENITY
    intensity: float = 0.5
    timestamp: float = field(default_factory=time.time)
    consolidated: bool = False
    related_symbol_ids: List[str] = field(default_factory=list)
    source_sequence_id: Optional[str] = None

    def __post_init__(self) -> None:
        # Clamp intensity into a sane [0, 1] range.
        if self.intensity < 0.0:
            self.intensity = 0.0
        elif self.intensity > 1.0:
            self.intensity = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "npc_id": self.npc_id,
            "memory_type": self.memory_type.value,
            "description": self.description,
            "emotion": self.emotion.value,
            "intensity": round(self.intensity, 4),
            "timestamp": self.timestamp,
            "consolidated": self.consolidated,
            "related_symbol_ids": list(self.related_symbol_ids),
            "source_sequence_id": self.source_sequence_id,
        }


@dataclass
class DreamSymbol:
    """A symbolic stand-in that a dream uses to represent experiences.

    Symbols are the vocabulary of the dream layer. Each symbol is tied to a
    set of emotions and memory types so that the generator can pick the
    right symbols for a given batch of daily experiences.
    """
    symbol_id: str = ""
    name: str = ""
    description: str = ""
    associated_emotions: List[EmotionType] = field(default_factory=list)
    associated_memory_types: List[MemoryType] = field(default_factory=list)
    meaning: str = ""
    rarity: float = 0.5

    def __post_init__(self) -> None:
        if not self.symbol_id:
            self.symbol_id = uuid.uuid4().hex[:12]
        if self.rarity < 0.0:
            self.rarity = 0.0
        elif self.rarity > 1.0:
            self.rarity = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol_id": self.symbol_id,
            "name": self.name,
            "description": self.description,
            "associated_emotions": [e.value for e in self.associated_emotions],
            "associated_memory_types": [m.value for m in self.associated_memory_types],
            "meaning": self.meaning,
            "rarity": round(self.rarity, 4),
        }


@dataclass
class DreamArchetype:
    """A recurring thematic pattern that can be woven into a dream.

    Archetypes supply the narrative spine of a dream. When a batch of
    experiences aligns with an archetype's associated symbols, that
    archetype is selected and its mood and behavior modifiers contribute
    to the final dream outcome.
    """
    archetype_id: str = ""
    name: str = ""
    description: str = ""
    theme: str = ""
    associated_symbol_ids: List[str] = field(default_factory=list)
    mood_modifier: float = 0.0
    behavior_modifiers: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.archetype_id:
            self.archetype_id = uuid.uuid4().hex[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archetype_id": self.archetype_id,
            "name": self.name,
            "description": self.description,
            "theme": self.theme,
            "associated_symbol_ids": list(self.associated_symbol_ids),
            "mood_modifier": round(self.mood_modifier, 4),
            "behavior_modifiers": {k: round(v, 4) for k, v in self.behavior_modifiers.items()},
        }


@dataclass
class DreamSequence:
    """One full dream from onset through resolution to waking.

    Captures the symbols and archetypes used, the memories that fed it, the
    assembled narrative text, the classification of the dream, and links to
    its interpretation and outcome once those are produced.
    """
    sequence_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    npc_id: str = ""
    dream_type: DreamType = DreamType.ORDINARY
    intensity: DreamIntensity = DreamIntensity.MILD
    status: DreamStatus = DreamStatus.PENDING
    phase: DreamPhase = DreamPhase.ONSET
    symbol_ids: List[str] = field(default_factory=list)
    archetype_ids: List[str] = field(default_factory=list)
    memory_ids: List[str] = field(default_factory=list)
    narrative: str = ""
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    duration: float = 0.0
    is_prophetic: bool = False
    is_nightmare: bool = False
    is_recurring: bool = False
    interpretation_id: Optional[str] = None
    outcome_id: Optional[str] = None
    shared_with: List[str] = field(default_factory=list)
    prophecy_hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "npc_id": self.npc_id,
            "dream_type": self.dream_type.value,
            "intensity": self.intensity.value,
            "status": self.status.value,
            "phase": self.phase.value,
            "symbol_ids": list(self.symbol_ids),
            "archetype_ids": list(self.archetype_ids),
            "memory_ids": list(self.memory_ids),
            "narrative": self.narrative,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration": round(self.duration, 4),
            "is_prophetic": self.is_prophetic,
            "is_nightmare": self.is_nightmare,
            "is_recurring": self.is_recurring,
            "interpretation_id": self.interpretation_id,
            "outcome_id": self.outcome_id,
            "shared_with": list(self.shared_with),
            "prophecy_hint": self.prophecy_hint,
        }


@dataclass
class DreamInterpretation:
    """An analytical reading of a completed dream's meaning.

    Produced by interpret_dream, the interpretation summarizes the themes,
    scores the emotional resonance, and offers insights that the AI
    director or gameplay layer can act on.
    """
    interpretation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    sequence_id: str = ""
    summary: str = ""
    themes: List[str] = field(default_factory=list)
    emotional_resonance: float = 0.5
    predicted_outcome: str = ""
    confidence: float = 0.5
    insights: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        for attr in ("emotional_resonance", "confidence"):
            val = getattr(self, attr)
            if val < 0.0:
                setattr(self, attr, 0.0)
            elif val > 1.0:
                setattr(self, attr, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interpretation_id": self.interpretation_id,
            "sequence_id": self.sequence_id,
            "summary": self.summary,
            "themes": list(self.themes),
            "emotional_resonance": round(self.emotional_resonance, 4),
            "predicted_outcome": self.predicted_outcome,
            "confidence": round(self.confidence, 4),
            "insights": list(self.insights),
            "timestamp": self.timestamp,
        }


@dataclass
class DreamOutcome:
    """Behavioral and mood deltas applied to an NPC when a dream ends.

    The outcome translates the dream's symbols, archetypes, and type into
    concrete numeric modifiers that adjust the NPC's waking behavior.
    """
    outcome_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    sequence_id: str = ""
    npc_id: str = ""
    behavior_modifiers: Dict[str, float] = field(default_factory=dict)
    mood_delta: float = 0.0
    memory_ids_added: List[str] = field(default_factory=list)
    skill_deltas: Dict[str, float] = field(default_factory=dict)
    personality_shifts: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "sequence_id": self.sequence_id,
            "npc_id": self.npc_id,
            "behavior_modifiers": {k: round(v, 4) for k, v in self.behavior_modifiers.items()},
            "mood_delta": round(self.mood_delta, 4),
            "memory_ids_added": list(self.memory_ids_added),
            "skill_deltas": {k: round(v, 4) for k, v in self.skill_deltas.items()},
            "personality_shifts": {k: round(v, 4) for k, v in self.personality_shifts.items()},
            "timestamp": self.timestamp,
        }


@dataclass
class NPCSleepSchedule:
    """Sleep and wake timing plus the current state-machine position.

    The schedule determines when an NPC transitions between awake, drowsy,
    sleeping, dreaming, and waking states during the tick loop.
    """
    npc_id: str = ""
    sleep_start_hour: float = 22.0
    wake_hour: float = 6.0
    sleep_duration_hours: float = 8.0
    state: NPCSleepState = NPCSleepState.AWAKE
    state_timer: float = 0.0
    current_hour: float = 8.0
    day_length_hours: float = 24.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "npc_id": self.npc_id,
            "sleep_start_hour": round(self.sleep_start_hour, 4),
            "wake_hour": round(self.wake_hour, 4),
            "sleep_duration_hours": round(self.sleep_duration_hours, 4),
            "state": self.state.value,
            "state_timer": round(self.state_timer, 4),
            "current_hour": round(self.current_hour, 4),
            "day_length_hours": round(self.day_length_hours, 4),
        }


@dataclass
class NPCDreamProfile:
    """Per-NPC dream state, journal, and memory store.

    Holds the NPC's personality, mood, dream affinity, pending daily
    experiences, consolidated long-term memories, behavior modifiers
    accumulated from past dreams, and the ordered dream journal.
    """
    npc_id: str = ""
    name: str = "Unnamed NPC"
    personality_traits: Dict[str, float] = field(default_factory=dict)
    mood: float = 0.6
    lucidity: float = 0.1
    dream_affinity: float = 0.5
    prophetic_chance: float = 0.02
    nightmare_threshold: float = 0.6
    behavior_modifiers: Dict[str, float] = field(default_factory=dict)
    pending_experiences: List[DreamMemory] = field(default_factory=list)
    long_term_memories: List[DreamMemory] = field(default_factory=list)
    dream_journal: List[str] = field(default_factory=list)
    active_sequence_id: Optional[str] = None
    shared_dream_ids: List[str] = field(default_factory=list)
    recurring_symbol_ids: List[str] = field(default_factory=list)
    registered_at: float = field(default_factory=time.time)
    total_dreams: int = 0

    def __post_init__(self) -> None:
        for attr in ("mood", "lucidity", "dream_affinity", "prophetic_chance",
                     "nightmare_threshold"):
            val = getattr(self, attr)
            if val < 0.0:
                setattr(self, attr, 0.0)
            elif val > 1.0:
                setattr(self, attr, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "npc_id": self.npc_id,
            "name": self.name,
            "personality_traits": {k: round(v, 4) for k, v in self.personality_traits.items()},
            "mood": round(self.mood, 4),
            "lucidity": round(self.lucidity, 4),
            "dream_affinity": round(self.dream_affinity, 4),
            "prophetic_chance": round(self.prophetic_chance, 4),
            "nightmare_threshold": round(self.nightmare_threshold, 4),
            "behavior_modifiers": {k: round(v, 4) for k, v in self.behavior_modifiers.items()},
            "pending_experience_count": len(self.pending_experiences),
            "long_term_memory_count": len(self.long_term_memories),
            "dream_journal": list(self.dream_journal),
            "active_sequence_id": self.active_sequence_id,
            "shared_dream_ids": list(self.shared_dream_ids),
            "recurring_symbol_ids": list(self.recurring_symbol_ids),
            "registered_at": self.registered_at,
            "total_dreams": self.total_dreams,
        }


@dataclass
class DreamConfig:
    """Tunable parameters that shape dream generation and the tick loop."""
    dream_duration_base: float = 60.0
    prophetic_chance_base: float = 0.02
    nightmare_threshold_base: float = 0.6
    memory_consolidation_rate: float = 0.5
    symbol_resolution_rate: float = 0.7
    max_journal_entries: int = 200
    enable_dream_sharing: bool = True
    enable_prophetic_dreams: bool = True
    enable_nightmares: bool = True
    tick_speed: float = 1.0
    day_length_hours: float = 24.0
    mood_decay_per_tick: float = 0.001
    max_events: int = 500

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dream_duration_base": self.dream_duration_base,
            "prophetic_chance_base": self.prophetic_chance_base,
            "nightmare_threshold_base": self.nightmare_threshold_base,
            "memory_consolidation_rate": self.memory_consolidation_rate,
            "symbol_resolution_rate": self.symbol_resolution_rate,
            "max_journal_entries": self.max_journal_entries,
            "enable_dream_sharing": self.enable_dream_sharing,
            "enable_prophetic_dreams": self.enable_prophetic_dreams,
            "enable_nightmares": self.enable_nightmares,
            "tick_speed": self.tick_speed,
            "day_length_hours": self.day_length_hours,
            "mood_decay_per_tick": self.mood_decay_per_tick,
            "max_events": self.max_events,
        }


@dataclass
class DreamStats:
    """Rolled-up counters describing system-wide activity."""
    total_npcs: int = 0
    total_dreams: int = 0
    total_prophetic_dreams: int = 0
    total_nightmares: int = 0
    total_memories_consolidated: int = 0
    total_symbols_registered: int = 0
    total_archetypes_registered: int = 0
    total_dreams_shared: int = 0
    total_experiences_added: int = 0
    avg_dream_duration: float = 0.0
    avg_mood: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_npcs": self.total_npcs,
            "total_dreams": self.total_dreams,
            "total_prophetic_dreams": self.total_prophetic_dreams,
            "total_nightmares": self.total_nightmares,
            "total_memories_consolidated": self.total_memories_consolidated,
            "total_symbols_registered": self.total_symbols_registered,
            "total_archetypes_registered": self.total_archetypes_registered,
            "total_dreams_shared": self.total_dreams_shared,
            "total_experiences_added": self.total_experiences_added,
            "avg_dream_duration": round(self.avg_dream_duration, 4),
            "avg_mood": round(self.avg_mood, 4),
            "tick_count": self.tick_count,
        }


@dataclass
class DreamSnapshot:
    """Point-in-time capture of the whole system for snapshotting."""
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    tick_count: int = 0
    active_dreams: int = 0
    sleeping_npcs: int = 0
    npc_ids: List[str] = field(default_factory=list)
    sequence_ids: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "tick_count": self.tick_count,
            "active_dreams": self.active_dreams,
            "sleeping_npcs": self.sleeping_npcs,
            "npc_ids": list(self.npc_ids),
            "sequence_ids": list(self.sequence_ids),
            "timestamp": self.timestamp,
        }


@dataclass
class DreamEvent:
    """A single recorded notification for auditing and the tick log."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    kind: DreamEventKind = DreamEventKind.DREAM_STARTED
    npc_id: Optional[str] = None
    sequence_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "npc_id": self.npc_id,
            "sequence_id": self.sequence_id,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Seed data: dream symbols
# ---------------------------------------------------------------------------

# Ten curated symbols that give the system a working vocabulary out of the
# box. Each symbol maps to emotions and memory types so the generator can
# match symbols to an NPC's recent experiences.
_SEED_SYMBOLS: List[Dict[str, Any]] = [
    {
        "symbol_id": "sym_water",
        "name": "Endless River",
        "description": "A wide, slow river that flows through every scene.",
        "associated_emotions": [EmotionType.SERENITY, EmotionType.LONGING, EmotionType.FEAR],
        "associated_memory_types": [MemoryType.EXPLORATION, MemoryType.ROUTINE, MemoryType.LOSS],
        "meaning": "The passage of time and the things carried away by it.",
        "rarity": 0.3,
    },
    {
        "symbol_id": "sym_door",
        "name": "Locked Door",
        "description": "A heavy oak door with no key in sight.",
        "associated_emotions": [EmotionType.FEAR, EmotionType.ANTICIPATION, EmotionType.SHAME],
        "associated_memory_types": [MemoryType.DISCOVERY, MemoryType.FEAR, MemoryType.MYSTICAL],
        "meaning": "A choice or truth the dreamer is not yet ready to face.",
        "rarity": 0.4,
    },
    {
        "symbol_id": "sym_fire",
        "name": "Hearth Flame",
        "description": "A warm fire that burns without consuming its fuel.",
        "associated_emotions": [EmotionType.JOY, EmotionType.TRUST, EmotionType.AWE],
        "associated_memory_types": [MemoryType.SOCIAL, MemoryType.CRAFTING, MemoryType.ACHIEVEMENT],
        "meaning": "Community, creation, and the spark of inspiration.",
        "rarity": 0.25,
    },
    {
        "symbol_id": "sym_mirror",
        "name": "Cracked Mirror",
        "description": "A tall mirror split by a single jagged line.",
        "associated_emotions": [EmotionType.SHAME, EmotionType.SURPRISE, EmotionType.SADNESS],
        "associated_memory_types": [MemoryType.LOSS, MemoryType.COMBAT, MemoryType.ROMANCE],
        "meaning": "A fractured sense of self or a hidden regret.",
        "rarity": 0.5,
    },
    {
        "symbol_id": "sym_storm",
        "name": "Black Storm",
        "description": "A wall of cloud and lightning rolling over the horizon.",
        "associated_emotions": [EmotionType.FEAR, EmotionType.ANGER, EmotionType.AWE],
        "associated_memory_types": [MemoryType.COMBAT, MemoryType.FEAR, MemoryType.EXPLORATION],
        "meaning": "Approaching conflict or suppressed rage seeking release.",
        "rarity": 0.45,
    },
    {
        "symbol_id": "sym_garden",
        "name": "Overgrown Garden",
        "description": "A wild tangle of flowers and vines once carefully kept.",
        "associated_emotions": [EmotionType.JOY, EmotionType.LONGING, EmotionType.SERENITY],
        "associated_memory_types": [MemoryType.ROMANCE, MemoryType.CRAFTING, MemoryType.ROUTINE],
        "meaning": "Tenderness left untended, still growing on its own.",
        "rarity": 0.35,
    },
    {
        "symbol_id": "sym_tower",
        "name": "Falling Tower",
        "description": "A stone tower that leans and begins to topple.",
        "associated_emotions": [EmotionType.FEAR, EmotionType.SADNESS, EmotionType.SURPRISE],
        "associated_memory_types": [MemoryType.LOSS, MemoryType.COMBAT, MemoryType.ACHIEVEMENT],
        "meaning": "An ambition or structure whose foundation is failing.",
        "rarity": 0.55,
    },
    {
        "symbol_id": "sym_star",
        "name": "Single Star",
        "description": "One bright star fixed in an otherwise empty sky.",
        "associated_emotions": [EmotionType.AWE, EmotionType.ANTICIPATION, EmotionType.LONGING],
        "associated_memory_types": [MemoryType.DISCOVERY, MemoryType.MYSTICAL, MemoryType.ACHIEVEMENT],
        "meaning": "A distant goal or a guiding conviction.",
        "rarity": 0.4,
    },
    {
        "symbol_id": "sym_mask",
        "name": "Porcelain Mask",
        "description": "A white mask that smiles no matter the scene around it.",
        "associated_emotions": [EmotionType.SHAME, EmotionType.DISGUST, EmotionType.FEAR],
        "associated_memory_types": [MemoryType.SOCIAL, MemoryType.LOSS, MemoryType.FEAR],
        "meaning": "A persona worn to hide a truer feeling beneath.",
        "rarity": 0.5,
    },
    {
        "symbol_id": "sym_key",
        "name": "Rusted Key",
        "description": "A heavy iron key too large for any visible lock.",
        "associated_emotions": [EmotionType.ANTICIPATION, EmotionType.TRUST, EmotionType.SURPRISE],
        "associated_memory_types": [MemoryType.DISCOVERY, MemoryType.COMMERCE, MemoryType.MYSTICAL],
        "meaning": "An opportunity or responsibility waiting to be claimed.",
        "rarity": 0.3,
    },
]


# ---------------------------------------------------------------------------
# Seed data: dream archetypes
# ---------------------------------------------------------------------------

# Eight archetypal themes that supply the narrative spine for generated
# dreams. Each lists the symbols it commonly draws upon and the behavior
# modifiers it contributes to the resulting dream outcome.
_SEED_ARCHETYPES: List[Dict[str, Any]] = [
    {
        "archetype_id": "arch_hero",
        "name": "The Reluctant Hero",
        "description": "A call to action the dreamer tries to refuse.",
        "theme": "courage",
        "associated_symbol_ids": ["sym_door", "sym_fire", "sym_key"],
        "mood_modifier": 0.05,
        "behavior_modifiers": {"bravery": 0.04, "impulsiveness": 0.02},
    },
    {
        "archetype_id": "arch_shadow",
        "name": "The Shadow Self",
        "description": "A confrontation with the parts of the self that are denied.",
        "theme": "self_knowledge",
        "associated_symbol_ids": ["sym_mirror", "sym_mask", "sym_storm"],
        "mood_modifier": -0.03,
        "behavior_modifiers": {"introspection": 0.05, "caution": 0.03},
    },
    {
        "archetype_id": "arch_home",
        "name": "The Long Road Home",
        "description": "A journey back toward a place that may no longer exist.",
        "theme": "belonging",
        "associated_symbol_ids": ["sym_water", "sym_garden", "sym_star"],
        "mood_modifier": 0.02,
        "behavior_modifiers": {"loyalty": 0.04, "patience": 0.03},
    },
    {
        "archetype_id": "arch_loss",
        "name": "The Empty Chair",
        "description": "An absence felt in a place where someone used to be.",
        "theme": "grief",
        "associated_symbol_ids": ["sym_mirror", "sym_garden", "sym_tower"],
        "mood_modifier": -0.06,
        "behavior_modifiers": {"melancholy": 0.05, "empathy": 0.03},
    },
    {
        "archetype_id": "arch_quest",
        "name": "The Hidden Prize",
        "description": "A search for something precious and barely reachable.",
        "theme": "ambition",
        "associated_symbol_ids": ["sym_key", "sym_star", "sym_door"],
        "mood_modifier": 0.04,
        "behavior_modifiers": {"curiosity": 0.05, "determination": 0.04},
    },
    {
        "archetype_id": "arch_storm",
        "name": "The Gathering Storm",
        "description": "A pressure building toward an inevitable breaking point.",
        "theme": "conflict",
        "associated_symbol_ids": ["sym_storm", "sym_tower", "sym_fire"],
        "mood_modifier": -0.04,
        "behavior_modifiers": {"alertness": 0.05, "aggression": 0.03},
    },
    {
        "archetype_id": "arch_hearth",
        "name": "The Shared Table",
        "description": "A gathering of faces around warmth and food.",
        "theme": "community",
        "associated_symbol_ids": ["sym_fire", "sym_garden", "sym_water"],
        "mood_modifier": 0.06,
        "behavior_modifiers": {"gregariousness": 0.05, "trust": 0.03},
    },
    {
        "archetype_id": "arch_prophecy",
        "name": "The Voice in the Dark",
        "description": "A disembodied message that lingers after waking.",
        "theme": "fate",
        "associated_symbol_ids": ["sym_star", "sym_door", "sym_mirror"],
        "mood_modifier": 0.03,
        "behavior_modifiers": {"intuition": 0.06, "recklessness": 0.02},
    },
]


# ---------------------------------------------------------------------------
# Seed data: NPC dream profiles
# ---------------------------------------------------------------------------

# Five pre-built NPC profiles so the system demonstrates dreams out of the
# box. Each has a distinct personality, mood, and dream affinity that shape
# the dreams it generates.
_SEED_NPCS: List[Dict[str, Any]] = [
    {
        "npc_id": "npc_elara",
        "name": "Elara the Herbalist",
        "personality_traits": {"calm": 0.8, "curiosity": 0.6, "bravery": 0.3},
        "mood": 0.7,
        "lucidity": 0.15,
        "dream_affinity": 0.6,
        "prophetic_chance": 0.03,
        "nightmare_threshold": 0.55,
        "sleep_start_hour": 21.0,
        "wake_hour": 5.0,
    },
    {
        "npc_id": "npc_borin",
        "name": "Borin the Smith",
        "personality_traits": {"calm": 0.4, "curiosity": 0.3, "bravery": 0.8, "loyalty": 0.7},
        "mood": 0.55,
        "lucidity": 0.05,
        "dream_affinity": 0.4,
        "prophetic_chance": 0.01,
        "nightmare_threshold": 0.7,
        "sleep_start_hour": 22.0,
        "wake_hour": 6.0,
    },
    {
        "npc_id": "npc_lyra",
        "name": "Lyra the Bard",
        "personality_traits": {"curiosity": 0.8, "gregariousness": 0.8, "bravery": 0.4},
        "mood": 0.75,
        "lucidity": 0.3,
        "dream_affinity": 0.8,
        "prophetic_chance": 0.05,
        "nightmare_threshold": 0.45,
        "sleep_start_hour": 1.0,
        "wake_hour": 9.0,
    },
    {
        "npc_id": "npc_kael",
        "name": "Kael the Ranger",
        "personality_traits": {"alertness": 0.9, "caution": 0.7, "bravery": 0.6},
        "mood": 0.5,
        "lucidity": 0.1,
        "dream_affinity": 0.45,
        "prophetic_chance": 0.02,
        "nightmare_threshold": 0.6,
        "sleep_start_hour": 23.0,
        "wake_hour": 5.0,
    },
    {
        "npc_id": "npc_mira",
        "name": "Mira the Seer",
        "personality_traits": {"intuition": 0.9, "introspection": 0.8, "caution": 0.5},
        "mood": 0.6,
        "lucidity": 0.5,
        "dream_affinity": 0.9,
        "prophetic_chance": 0.12,
        "nightmare_threshold": 0.5,
        "sleep_start_hour": 20.0,
        "wake_hour": 4.0,
    },
]


# ---------------------------------------------------------------------------
# Seed data: sample dream sequences
# ---------------------------------------------------------------------------

# Three pre-authored dream sequences that show the shape of a finished
# dream and populate the journal of the seed NPCs on initialization.
_SEED_SEQUENCES: List[Dict[str, Any]] = [
    {
        "sequence_id": "seq_seed_1",
        "npc_id": "npc_mira",
        "dream_type": DreamType.PROPHETIC,
        "intensity": DreamIntensity.VIVID,
        "status": DreamStatus.INTERPRETED,
        "phase": DreamPhase.WAKING,
        "symbol_ids": ["sym_star", "sym_door"],
        "archetype_ids": ["arch_prophecy"],
        "narrative": (
            "In the soft light of the inner world, a single star opened like "
            "an eye above a locked door. A voice without a mouth said the "
            "name of a road not yet taken, and the last echo faded into white "
            "silence."
        ),
        "is_prophetic": True,
        "prophecy_hint": "A traveler will arrive from the eastern road before the next moon.",
    },
    {
        "sequence_id": "seq_seed_2",
        "npc_id": "npc_borin",
        "dream_type": DreamType.NIGHTMARE,
        "intensity": DreamIntensity.INTENSE,
        "status": DreamStatus.COMPLETED,
        "phase": DreamPhase.WAKING,
        "symbol_ids": ["sym_tower", "sym_storm"],
        "archetype_ids": ["arch_storm"],
        "narrative": (
            "Shadows rearranged themselves until a stone tower leaned against "
            "a black storm and began to topple. The dreamer gripped a hammer "
            "that turned to sand, leaving behind a single lingering image."
        ),
        "is_nightmare": True,
    },
    {
        "sequence_id": "seq_seed_3",
        "npc_id": "npc_lyra",
        "dream_type": DreamType.SHARED,
        "intensity": DreamIntensity.VIVID,
        "status": DreamStatus.COMPLETED,
        "phase": DreamPhase.WAKING,
        "symbol_ids": ["sym_fire", "sym_garden"],
        "archetype_ids": ["arch_hearth", "arch_home"],
        "narrative": (
            "A hush fell over the mindscape as a shared table appeared in an "
            "overgrown garden, and a hearth flame burned without consuming its "
            "fuel. Faces from many lives sat down together before the scene "
            "folded quietly into stillness."
        ),
        "shared_with": ["npc_elara"],
    },
]


# ---------------------------------------------------------------------------
# Seed data: sample experiences
# ---------------------------------------------------------------------------

# A small set of pending experiences seeded into one NPC so that
# generate_dream_sequence has material to work with on first use.
_SEED_EXPERIENCES: List[Dict[str, Any]] = [
    {
        "npc_id": "npc_elara",
        "memory_type": MemoryType.SOCIAL,
        "description": "Traded herbs with a passing caravan and shared stories.",
        "emotion": EmotionType.JOY,
        "intensity": 0.6,
    },
    {
        "npc_id": "npc_elara",
        "memory_type": MemoryType.DISCOVERY,
        "description": "Found a patch of moonpetal flowers growing by the old well.",
        "emotion": EmotionType.AWE,
        "intensity": 0.7,
    },
    {
        "npc_id": "npc_elara",
        "memory_type": MemoryType.LOSS,
        "description": "Remembered a friend who left the village last winter.",
        "emotion": EmotionType.SADNESS,
        "intensity": 0.5,
    },
    {
        "npc_id": "npc_kael",
        "memory_type": MemoryType.COMBAT,
        "description": "Drove off a wolf pack at the forest edge.",
        "emotion": EmotionType.FEAR,
        "intensity": 0.8,
    },
    {
        "npc_id": "npc_kael",
        "memory_type": MemoryType.EXPLORATION,
        "description": "Mapped a new trail toward the northern ridge.",
        "emotion": EmotionType.ANTICIPATION,
        "intensity": 0.55,
    },
]


# ---------------------------------------------------------------------------
# NPC Dream Simulation System (singleton)
# ---------------------------------------------------------------------------

class NPCDreamSimulationSystem:
    """Central registry and simulator for NPC dream life.

    Owns the canonical collections of NPC profiles, dream symbols,
    archetypes, dream sequences, interpretations, and outcomes. The tick
    loop advances each NPC's sleep schedule, launches dreams when an NPC
    enters the dreaming state, and finalizes dreams with outcomes when
    they wake.

    The class is a thread-safe singleton built with double-checked locking
    on a reentrant lock. Use get_npc_dream_simulation_system() at module
    scope to obtain the auto-initialized instance.
    """

    _instance: Optional["NPCDreamSimulationSystem"] = None
    _lock: threading.RLock = threading.RLock()
    _init_lock: threading.RLock = threading.RLock()

    # -- internal constants ------------------------------------------------
    EPSILON: float = 1e-9
    MAX_DREAMS_PER_TICK: int = 50

    def __init__(self) -> None:
        # Guard so repeated construction does not wipe an existing instance.
        if getattr(self, "_initialized", False):
            return
        with self._init_lock:
            if getattr(self, "_initialized", False):
                return

            # -- Registries --
            self._npcs: Dict[str, NPCDreamProfile] = {}
            self._symbols: Dict[str, DreamSymbol] = {}
            self._archetypes: Dict[str, DreamArchetype] = {}
            self._sequences: Dict[str, DreamSequence] = {}
            self._interpretations: Dict[str, DreamInterpretation] = {}
            self._outcomes: Dict[str, DreamOutcome] = {}
            self._schedules: Dict[str, NPCSleepSchedule] = {}

            # -- Cross-NPC shared dream links --
            # Maps a recipient npc_id to the list of sequence ids shared with them.
            self._shared_dreams: Dict[str, List[str]] = defaultdict(list)

            # -- Event log --
            self._events: List[DreamEvent] = []

            # -- Configuration and counters --
            self._config: DreamConfig = DreamConfig()
            self._tick_count: int = 0
            self._total_dreams: int = 0
            self._total_prophetic_dreams: int = 0
            self._total_nightmares: int = 0
            self._total_memories_consolidated: int = 0
            self._total_dreams_shared: int = 0
            self._total_experiences_added: int = 0
            self._total_dream_duration: float = 0.0

            self._seeded: bool = False
            self._initialized: bool = True

    # ------------------------------------------------------------------
    # Singleton lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "NPCDreamSimulationSystem":
        """Return the singleton instance, creating it if needed.

        Uses double-checked locking so that under contention only one
        instance is ever constructed.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Tear down the singleton so a fresh instance can be built.

        Primarily useful for tests. After calling this, the next
        get_instance() call builds a new, unseeded instance.
        """
        with cls._lock:
            cls._instance = None

    def initialize(self) -> Tuple[bool, str]:
        """Load seed data so the system works out of the box.

        Idempotent: calling initialize() multiple times is safe and will
        not duplicate seed entries.
        """
        with self._init_lock:
            if self._seeded:
                return True, "Already initialized"
            self._load_seed_symbols()
            self._load_seed_archetypes()
            self._load_seed_npcs()
            self._load_seed_sequences()
            self._load_seed_experiences()
            self._seeded = True
        self._emit(
            DreamEventKind.SYSTEM_RESET,
            {"action": "initialize",
             "npcs": len(self._npcs),
             "symbols": len(self._symbols),
             "archetypes": len(self._archetypes),
             "sequences": len(self._sequences)},
        )
        return True, (
            f"Initialized with {len(self._npcs)} NPCs, "
            f"{len(self._symbols)} symbols, "
            f"{len(self._archetypes)} archetypes, "
            f"{len(self._sequences)} seed sequences"
        )

    # ------------------------------------------------------------------
    # NPC lifecycle
    # ------------------------------------------------------------------

    def register_npc(
        self,
        npc_id: str,
        name: str,
        personality_traits: Optional[Dict[str, float]] = None,
        mood: float = 0.6,
        lucidity: float = 0.1,
        dream_affinity: float = 0.5,
        prophetic_chance: Optional[float] = None,
        nightmare_threshold: Optional[float] = None,
        sleep_start_hour: float = 22.0,
        wake_hour: float = 6.0,
    ) -> Tuple[bool, str, Optional[NPCDreamProfile]]:
        """Register a new NPC dream profile.

        If an NPC with the given id already exists the call is rejected.
        A sleep schedule is created alongside the profile so the tick loop
        can begin driving the NPC immediately.
        """
        if not npc_id:
            return False, "npc_id must not be empty", None
        with self._lock:
            if npc_id in self._npcs:
                return False, f"NPC already registered: {npc_id}", None
            profile = NPCDreamProfile(
                npc_id=npc_id,
                name=name or "Unnamed NPC",
                personality_traits=dict(personality_traits or {}),
                mood=mood,
                lucidity=lucidity,
                dream_affinity=dream_affinity,
                prophetic_chance=(
                    prophetic_chance
                    if prophetic_chance is not None
                    else self._config.prophetic_chance_base
                ),
                nightmare_threshold=(
                    nightmare_threshold
                    if nightmare_threshold is not None
                    else self._config.nightmare_threshold_base
                ),
            )
            self._npcs[npc_id] = profile
            self._schedules[npc_id] = NPCSleepSchedule(
                npc_id=npc_id,
                sleep_start_hour=sleep_start_hour,
                wake_hour=wake_hour,
                sleep_duration_hours=max(
                    1.0,
                    (wake_hour - sleep_start_hour) % self._config.day_length_hours,
                ),
                day_length_hours=self._config.day_length_hours,
            )
        self._emit(
            DreamEventKind.NPC_REGISTERED,
            {"npc_id": npc_id, "name": profile.name},
            npc_id=npc_id,
        )
        return True, f"Registered NPC: {profile.name}", profile

    def remove_npc(self, npc_id: str) -> Tuple[bool, str]:
        """Remove an NPC and its schedule from the system.

        Dream sequences and memories authored for the NPC are retained so
        that shared dreams and journal history remain queryable.
        """
        if not npc_id:
            return False, "npc_id must not be empty"
        with self._lock:
            if npc_id not in self._npcs:
                return False, f"NPC not found: {npc_id}"
            del self._npcs[npc_id]
            self._schedules.pop(npc_id, None)
            self._shared_dreams.pop(npc_id, None)
        self._emit(
            DreamEventKind.NPC_REMOVED,
            {"npc_id": npc_id},
            npc_id=npc_id,
        )
        return True, f"Removed NPC: {npc_id}"

    def get_npc(self, npc_id: str) -> Optional[NPCDreamProfile]:
        """Return the dream profile for an NPC, or None if not registered."""
        with self._lock:
            return self._npcs.get(npc_id)

    def list_npcs(self) -> List[NPCDreamProfile]:
        """Return all registered NPC profiles."""
        with self._lock:
            return list(self._npcs.values())

    # ------------------------------------------------------------------
    # Experience and memory pipeline
    # ------------------------------------------------------------------

    def add_experience(
        self,
        npc_id: str,
        memory_type: MemoryType,
        description: str,
        emotion: EmotionType,
        intensity: float = 0.5,
    ) -> Tuple[bool, str, Optional[DreamMemory]]:
        """Add a daily experience to an NPC's pending experiences.

        Pending experiences feed dream generation and are later folded into
        long-term memory by consolidate_memories.
        """
        if isinstance(memory_type, str):
            try:
                memory_type = MemoryType(memory_type)
            except ValueError:
                return False, f"Unknown memory type '{memory_type}'", None
        if isinstance(emotion, str):
            try:
                emotion = EmotionType(emotion)
            except ValueError:
                return False, f"Unknown emotion '{emotion}'", None
        if not npc_id:
            return False, "npc_id must not be empty", None
        with self._lock:
            profile = self._npcs.get(npc_id)
            if profile is None:
                return False, f"NPC not found: {npc_id}", None
            memory = DreamMemory(
                npc_id=npc_id,
                memory_type=memory_type,
                description=description,
                emotion=emotion,
                intensity=intensity,
            )
            profile.pending_experiences.append(memory)
            self._total_experiences_added += 1
        self._emit(
            DreamEventKind.EXPERIENCE_ADDED,
            {"npc_id": npc_id, "memory_type": memory_type.value,
             "emotion": emotion.value, "intensity": round(intensity, 4)},
            npc_id=npc_id,
        )
        return True, f"Added experience to {npc_id}", memory

    def process_experiences(self, npc_id: str) -> Tuple[bool, str, List[DreamMemory]]:
        """Resolve pending experiences into dream-ready memories.

        For each pending experience the method attaches the ids of symbols
        whose emotional and memory-type palette overlaps with it, then
        returns the prepared memories. The experiences remain pending until
        consolidate_memories is called.
        """
        if not npc_id:
            return False, "npc_id must not be empty", []
        with self._lock:
            profile = self._npcs.get(npc_id)
            if profile is None:
                return False, f"NPC not found: {npc_id}", []
            prepared: List[DreamMemory] = []
            for memory in profile.pending_experiences:
                matched = self._match_symbols_for_memory(memory)
                memory.related_symbol_ids = matched
                prepared.append(memory)
        return True, f"Processed {len(prepared)} experiences for {npc_id}", prepared

    def consolidate_memories(self, npc_id: str) -> Tuple[bool, str, List[DreamMemory]]:
        """Fold pending experiences into long-term memory.

        Each pending experience is converted into a consolidated long-term
        memory with its intensity decayed according to the configured
        consolidation rate. Consolidated memories persist across dreams and
        contribute to recurring-symbol tracking.
        """
        if not npc_id:
            return False, "npc_id must not be empty", []
        with self._lock:
            profile = self._npcs.get(npc_id)
            if profile is None:
                return False, f"NPC not found: {npc_id}", []
            if not profile.pending_experiences:
                return True, f"No pending experiences for {npc_id}", []
            consolidated: List[DreamMemory] = []
            decay = 1.0 - self._config.memory_consolidation_rate
            for memory in profile.pending_experiences:
                memory.consolidated = True
                memory.intensity = max(0.0, memory.intensity * decay)
                profile.long_term_memories.append(memory)
                consolidated.append(memory)
                self._total_memories_consolidated += 1
                # Track symbols that recur across consolidated memories.
                for sym_id in memory.related_symbol_ids:
                    if sym_id not in profile.recurring_symbol_ids:
                        profile.recurring_symbol_ids.append(sym_id)
            profile.pending_experiences.clear()
            # Cap long-term memory storage to avoid unbounded growth.
            cap = self._config.max_journal_entries * 4
            if len(profile.long_term_memories) > cap:
                overflow = len(profile.long_term_memories) - cap
                del profile.long_term_memories[:overflow]
        self._emit(
            DreamEventKind.MEMORIES_CONSOLIDATED,
            {"npc_id": npc_id, "count": len(consolidated)},
            npc_id=npc_id,
        )
        return True, f"Consolidated {len(consolidated)} memories for {npc_id}", consolidated

    # ------------------------------------------------------------------
    # Dream lifecycle
    # ------------------------------------------------------------------

    def start_dream(self, npc_id: str) -> Tuple[bool, str, Optional[DreamSequence]]:
        """Begin a dream for an NPC if one is not already active.

        The dream is generated from the NPC's pending experiences and
        long-term memories, then placed in the ACTIVE state. The NPC's
        schedule is moved into the DREAMING state.
        """
        if not npc_id:
            return False, "npc_id must not be empty", None
        with self._lock:
            profile = self._npcs.get(npc_id)
            if profile is None:
                return False, f"NPC not found: {npc_id}", None
            if profile.active_sequence_id is not None:
                existing = self._sequences.get(profile.active_sequence_id)
                if existing is not None and existing.status == DreamStatus.ACTIVE:
                    return False, "NPC already dreaming", existing
            sequence = self.generate_dream_sequence(npc_id)
            if sequence is None:
                return False, "Could not generate a dream", None
            sequence.status = DreamStatus.ACTIVE
            sequence.phase = DreamPhase.ONSET
            sequence.started_at = time.time()
            profile.active_sequence_id = sequence.sequence_id
            profile.total_dreams += 1
            self._total_dreams += 1
            schedule = self._schedules.get(npc_id)
            if schedule is not None:
                schedule.state = NPCSleepState.DREAMING
                schedule.state_timer = 0.0
        self._emit(
            DreamEventKind.DREAM_STARTED,
            {"npc_id": npc_id, "sequence_id": sequence.sequence_id,
             "dream_type": sequence.dream_type.value,
             "is_prophetic": sequence.is_prophetic,
             "is_nightmare": sequence.is_nightmare},
            npc_id=npc_id,
            sequence_id=sequence.sequence_id,
        )
        if sequence.is_prophetic:
            self._emit(
                DreamEventKind.PROPHETIC_DREAM,
                {"npc_id": npc_id, "sequence_id": sequence.sequence_id,
                 "prophecy_hint": sequence.prophecy_hint},
                npc_id=npc_id,
                sequence_id=sequence.sequence_id,
            )
        if sequence.is_nightmare:
            self._emit(
                DreamEventKind.NIGHTMARE_TRIGGERED,
                {"npc_id": npc_id, "sequence_id": sequence.sequence_id},
                npc_id=npc_id,
                sequence_id=sequence.sequence_id,
            )
        return True, f"Started dream for {npc_id}", sequence

    def generate_dream_sequence(
        self,
        npc_id: str,
        force_type: Optional[DreamType] = None,
    ) -> Optional[DreamSequence]:
        """Generate a dream sequence from an NPC's experiences and memories.

        Selects symbols whose palette overlaps with the NPC's recent
        experiences, picks matching archetypes, classifies the dream, and
        assembles a narrative string. Prophetic and nightmare flags are
        rolled according to the NPC's thresholds and the system config.
        """
        if not npc_id:
            return None
        with self._lock:
            profile = self._npcs.get(npc_id)
            if profile is None:
                return None

            # Gather the memories that will feed this dream.
            source_memories: List[DreamMemory] = list(profile.pending_experiences)
            if not source_memories and profile.long_term_memories:
                # Replay a slice of long-term memory when nothing is pending.
                source_memories = profile.long_term_memories[-3:]

            # Match symbols to the gathered memories.
            candidate_symbol_ids: List[str] = []
            for memory in source_memories:
                candidate_symbol_ids.extend(self._match_symbols_for_memory(memory))
            if not candidate_symbol_ids:
                # Fall back to a random sample of known symbols.
                candidate_symbol_ids = [
                    s.symbol_id for s in random.sample(
                        list(self._symbols.values()),
                        k=min(3, len(self._symbols)),
                    )
                ] if self._symbols else []
            # De-duplicate while preserving order, then trim.
            seen: set = set()
            chosen_symbol_ids: List[str] = []
            for sid in candidate_symbol_ids:
                if sid not in seen and sid in self._symbols:
                    seen.add(sid)
                    chosen_symbol_ids.append(sid)
                if len(chosen_symbol_ids) >= 4:
                    break

            # Select archetypes whose associated symbols overlap.
            chosen_archetype_ids: List[str] = []
            for arch in self._archetypes.values():
                overlap = set(arch.associated_symbol_ids) & set(chosen_symbol_ids)
                if overlap:
                    chosen_archetype_ids.append(arch.archetype_id)
            if not chosen_archetype_ids and self._archetypes:
                # Pick a random archetype as a fallback spine.
                fallback = random.choice(list(self._archetypes.values()))
                chosen_archetype_ids.append(fallback.archetype_id)
            chosen_archetype_ids = chosen_archetype_ids[:3]

            # Classify the dream and compute its intensity.
            dream_type, intensity, is_nightmare, is_prophetic = self._classify_dream(
                profile, source_memories, force_type
            )

            # Build the narrative text from the chosen symbols and archetypes.
            narrative = self._build_narrative(
                chosen_symbol_ids, chosen_archetype_ids, dream_type
            )

            # Determine whether this is a recurring dream.
            is_recurring = any(
                sid in profile.recurring_symbol_ids for sid in chosen_symbol_ids
            ) and profile.total_dreams > 0 and random.random() < 0.25

            memory_ids = [m.memory_id for m in source_memories]
            sequence = DreamSequence(
                npc_id=npc_id,
                dream_type=dream_type,
                intensity=intensity,
                status=DreamStatus.PENDING,
                phase=DreamPhase.ONSET,
                symbol_ids=chosen_symbol_ids,
                archetype_ids=chosen_archetype_ids,
                memory_ids=memory_ids,
                narrative=narrative,
                is_prophetic=is_prophetic,
                is_nightmare=is_nightmare,
                is_recurring=is_recurring,
                prophecy_hint=self._roll_prophecy_hint() if is_prophetic else None,
            )
            self._sequences[sequence.sequence_id] = sequence
            # Append to the NPC's journal, respecting the cap.
            profile.dream_journal.append(sequence.sequence_id)
            if len(profile.dream_journal) > self._config.max_journal_entries:
                overflow = len(profile.dream_journal) - self._config.max_journal_entries
                del profile.dream_journal[:overflow]
        return sequence

    def end_dream(
        self,
        npc_id: str,
        sequence_id: str,
    ) -> Tuple[bool, str, Optional[DreamOutcome]]:
        """Finalize a dream and apply its outcome to the NPC.

        Computes the dream outcome (mood and behavior deltas), marks the
        sequence as completed, and moves the NPC toward the waking state.
        """
        if not npc_id or not sequence_id:
            return False, "npc_id and sequence_id are required", None
        with self._lock:
            profile = self._npcs.get(npc_id)
            if profile is None:
                return False, f"NPC not found: {npc_id}", None
            sequence = self._sequences.get(sequence_id)
            if sequence is None or sequence.npc_id != npc_id:
                return False, f"Sequence not found for NPC: {sequence_id}", None
            if sequence.status == DreamStatus.COMPLETED:
                return False, "Dream already completed", None
            outcome = self._compute_outcome(profile, sequence)
            self._outcomes[outcome.outcome_id] = outcome
            sequence.outcome_id = outcome.outcome_id
            sequence.status = DreamStatus.COMPLETED
            sequence.phase = DreamPhase.WAKING
            sequence.ended_at = time.time()
            sequence.duration = max(0.0, sequence.ended_at - sequence.started_at)
            self._total_dream_duration += sequence.duration
            # Apply the outcome to the NPC profile.
            self._apply_outcome_to_profile(profile, outcome)
            # Clear the active dream pointer if it matches.
            if profile.active_sequence_id == sequence_id:
                profile.active_sequence_id = None
            # Move the schedule toward waking.
            schedule = self._schedules.get(npc_id)
            if schedule is not None:
                schedule.state = NPCSleepState.WAKING
                schedule.state_timer = 0.0
        self._emit(
            DreamEventKind.DREAM_ENDED,
            {"npc_id": npc_id, "sequence_id": sequence_id,
             "duration": round(sequence.duration, 4),
             "outcome_id": outcome.outcome_id},
            npc_id=npc_id,
            sequence_id=sequence_id,
        )
        return True, f"Ended dream {sequence_id} for {npc_id}", outcome

    # ------------------------------------------------------------------
    # Archetype management
    # ------------------------------------------------------------------

    def register_archetype(
        self,
        archetype_id: str,
        name: str,
        description: str = "",
        theme: str = "",
        associated_symbol_ids: Optional[List[str]] = None,
        mood_modifier: float = 0.0,
        behavior_modifiers: Optional[Dict[str, float]] = None,
    ) -> Tuple[bool, str, Optional[DreamArchetype]]:
        """Register a new dream archetype.

        Re-registering an existing archetype_id updates its fields in place.
        """
        if not archetype_id:
            return False, "archetype_id must not be empty", None
        with self._lock:
            archetype = DreamArchetype(
                archetype_id=archetype_id,
                name=name,
                description=description,
                theme=theme,
                associated_symbol_ids=list(associated_symbol_ids or []),
                mood_modifier=mood_modifier,
                behavior_modifiers=dict(behavior_modifiers or {}),
            )
            self._archetypes[archetype_id] = archetype
        self._emit(
            DreamEventKind.ARCHETYPE_REGISTERED,
            {"archetype_id": archetype_id, "name": name},
        )
        return True, f"Registered archetype: {name}", archetype

    def get_archetype(self, archetype_id: str) -> Optional[DreamArchetype]:
        """Return an archetype by id, or None if not found."""
        with self._lock:
            return self._archetypes.get(archetype_id)

    def list_archetypes(self) -> List[DreamArchetype]:
        """Return all registered archetypes."""
        with self._lock:
            return list(self._archetypes.values())

    # ------------------------------------------------------------------
    # Symbol management
    # ------------------------------------------------------------------

    def register_symbol(
        self,
        symbol_id: str,
        name: str,
        description: str = "",
        associated_emotions: Optional[List[EmotionType]] = None,
        associated_memory_types: Optional[List[MemoryType]] = None,
        meaning: str = "",
        rarity: float = 0.5,
    ) -> Tuple[bool, str, Optional[DreamSymbol]]:
        """Register a new dream symbol.

        Re-registering an existing symbol_id updates its fields in place.
        """
        if not symbol_id:
            return False, "symbol_id must not be empty", None
        with self._lock:
            symbol = DreamSymbol(
                symbol_id=symbol_id,
                name=name,
                description=description,
                associated_emotions=list(associated_emotions or []),
                associated_memory_types=list(associated_memory_types or []),
                meaning=meaning,
                rarity=rarity,
            )
            self._symbols[symbol_id] = symbol
        self._emit(
            DreamEventKind.SYMBOL_REGISTERED,
            {"symbol_id": symbol_id, "name": name},
        )
        return True, f"Registered symbol: {name}", symbol

    def get_symbol(self, symbol_id: str) -> Optional[DreamSymbol]:
        """Return a symbol by id, or None if not found."""
        with self._lock:
            return self._symbols.get(symbol_id)

    def list_symbols(self) -> List[DreamSymbol]:
        """Return all registered symbols."""
        with self._lock:
            return list(self._symbols.values())

    # ------------------------------------------------------------------
    # Dream interpretation
    # ------------------------------------------------------------------

    def interpret_dream(
        self,
        sequence_id: str,
    ) -> Tuple[bool, str, Optional[DreamInterpretation]]:
        """Produce an analytical reading of a completed dream.

        Examines the dream's symbols, archetypes, and type to summarize its
        themes, score its emotional resonance, and offer insights.
        """
        if not sequence_id:
            return False, "sequence_id must not be empty", None
        with self._lock:
            sequence = self._sequences.get(sequence_id)
            if sequence is None:
                return False, f"Sequence not found: {sequence_id}", None
            profile = self._npcs.get(sequence.npc_id)

            # Gather themes from archetypes.
            themes: List[str] = []
            for aid in sequence.archetype_ids:
                arch = self._archetypes.get(aid)
                if arch and arch.theme:
                    themes.append(arch.theme)

            # Collect the meanings of the symbols used.
            symbol_meanings: List[str] = []
            for sid in sequence.symbol_ids:
                sym = self._symbols.get(sid)
                if sym and sym.meaning:
                    symbol_meanings.append(sym.meaning)

            # Score emotional resonance from intensity and symbol rarity.
            intensity_weight = _INTENSITY_WEIGHT.get(sequence.intensity, 0.5)
            avg_rarity = 0.5
            if sequence.symbol_ids:
                rarities = [
                    self._symbols[sid].rarity
                    for sid in sequence.symbol_ids
                    if sid in self._symbols
                ]
                if rarities:
                    avg_rarity = sum(rarities) / len(rarities)
            resonance = min(1.0, (intensity_weight + avg_rarity) / 2.0)

            # Confidence rises with the number of symbols and themes.
            confidence = min(
                1.0,
                0.3 + 0.1 * len(sequence.symbol_ids) + 0.1 * len(themes),
            )

            # Assemble the summary and insights.
            npc_name = profile.name if profile else "The dreamer"
            summary = self._build_interpretation_summary(
                npc_name, sequence, themes, symbol_meanings
            )
            insights = self._build_insights(sequence, themes, symbol_meanings)
            predicted = self._predict_outcome(sequence)

            interpretation = DreamInterpretation(
                sequence_id=sequence_id,
                summary=summary,
                themes=themes,
                emotional_resonance=resonance,
                predicted_outcome=predicted,
                confidence=confidence,
                insights=insights,
            )
            self._interpretations[interpretation.interpretation_id] = interpretation
            sequence.interpretation_id = interpretation.interpretation_id
            if sequence.status == DreamStatus.COMPLETED:
                sequence.status = DreamStatus.INTERPRETED
        self._emit(
            DreamEventKind.DREAM_INTERPRETED,
            {"sequence_id": sequence_id,
             "interpretation_id": interpretation.interpretation_id},
            sequence_id=sequence_id,
        )
        return True, f"Interpreted dream {sequence_id}", interpretation

    def get_dream_interpretation(self, sequence_id: str) -> Optional[DreamInterpretation]:
        """Return the interpretation for a dream, or None if not interpreted."""
        with self._lock:
            sequence = self._sequences.get(sequence_id)
            if sequence is None or sequence.interpretation_id is None:
                return None
            return self._interpretations.get(sequence.interpretation_id)

    # ------------------------------------------------------------------
    # Dream outcomes and behavior modifiers
    # ------------------------------------------------------------------

    def apply_dream_outcome(
        self,
        npc_id: str,
        sequence_id: str,
    ) -> Tuple[bool, str, Optional[DreamOutcome]]:
        """Apply a dream's outcome to an NPC's waking behavior.

        If the dream has not yet been ended, this will compute and apply its
        outcome. Otherwise the existing outcome is returned.
        """
        if not npc_id or not sequence_id:
            return False, "npc_id and sequence_id are required", None
        with self._lock:
            profile = self._npcs.get(npc_id)
            if profile is None:
                return False, f"NPC not found: {npc_id}", None
            sequence = self._sequences.get(sequence_id)
            if sequence is None or sequence.npc_id != npc_id:
                return False, f"Sequence not found for NPC: {sequence_id}", None
            if sequence.outcome_id is not None:
                outcome = self._outcomes.get(sequence.outcome_id)
                if outcome is not None:
                    return True, "Outcome already applied", outcome
            outcome = self._compute_outcome(profile, sequence)
            self._outcomes[outcome.outcome_id] = outcome
            sequence.outcome_id = outcome.outcome_id
            self._apply_outcome_to_profile(profile, outcome)
        self._emit(
            DreamEventKind.OUTCOME_APPLIED,
            {"npc_id": npc_id, "sequence_id": sequence_id,
             "outcome_id": outcome.outcome_id,
             "mood_delta": round(outcome.mood_delta, 4)},
            npc_id=npc_id,
            sequence_id=sequence_id,
        )
        return True, f"Applied outcome for {npc_id}", outcome

    def get_npc_behavior_modifiers(self, npc_id: str) -> Dict[str, float]:
        """Return the accumulated behavior modifiers for an NPC.

        These modifiers are the sum of every dream outcome applied to the
        NPC and can be consulted by gameplay systems to vary NPC behavior.
        """
        with self._lock:
            profile = self._npcs.get(npc_id)
            if profile is None:
                return {}
            return dict(profile.behavior_modifiers)

    # ------------------------------------------------------------------
    # Dream sharing
    # ------------------------------------------------------------------

    def share_dream(
        self,
        npc_id: str,
        sequence_id: str,
        target_npc_id: str,
    ) -> Tuple[bool, str]:
        """Share a dream from one NPC with another.

        The target NPC receives the sequence in its shared-dream list and
        gains a small mood lift from the social bond. A shared copy of the
        sequence is recorded so it appears in the recipient's journal.
        """
        if not npc_id or not sequence_id or not target_npc_id:
            return False, "npc_id, sequence_id, and target_npc_id are required"
        if npc_id == target_npc_id:
            return False, "Cannot share a dream with oneself"
        if not self._config.enable_dream_sharing:
            return False, "Dream sharing is disabled in config"
        with self._lock:
            sequence = self._sequences.get(sequence_id)
            if sequence is None or sequence.npc_id != npc_id:
                return False, f"Sequence not found for NPC: {sequence_id}"
            target = self._npcs.get(target_npc_id)
            if target is None:
                return False, f"Target NPC not found: {target_npc_id}"
            if sequence_id not in sequence.shared_with:
                sequence.shared_with.append(target_npc_id)
            self._shared_dreams[target_npc_id].append(sequence_id)
            # The recipient gains a modest mood boost from the shared bond.
            target.mood = min(1.0, target.mood + 0.03)
            self._total_dreams_shared += 1
        self._emit(
            DreamEventKind.DREAM_SHARED,
            {"npc_id": npc_id, "sequence_id": sequence_id,
             "target_npc_id": target_npc_id},
            npc_id=npc_id,
            sequence_id=sequence_id,
        )
        return True, f"Shared dream {sequence_id} with {target_npc_id}"

    def get_shared_dreams(self, npc_id: str) -> List[DreamSequence]:
        """Return the dream sequences shared with an NPC by others."""
        with self._lock:
            ids = self._shared_dreams.get(npc_id, [])
            results: List[DreamSequence] = []
            for sid in ids:
                seq = self._sequences.get(sid)
                if seq is not None:
                    results.append(seq)
            return results

    # ------------------------------------------------------------------
    # Sleep schedule management
    # ------------------------------------------------------------------

    def set_sleep_schedule(
        self,
        npc_id: str,
        sleep_start_hour: Optional[float] = None,
        wake_hour: Optional[float] = None,
        sleep_duration_hours: Optional[float] = None,
        day_length_hours: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[NPCSleepSchedule]]:
        """Set or update an NPC's sleep schedule."""
        if not npc_id:
            return False, "npc_id must not be empty", None
        with self._lock:
            schedule = self._schedules.get(npc_id)
            if schedule is None:
                return False, f"Schedule not found for NPC: {npc_id}", None
            if sleep_start_hour is not None:
                schedule.sleep_start_hour = sleep_start_hour
            if wake_hour is not None:
                schedule.wake_hour = wake_hour
            if sleep_duration_hours is not None:
                schedule.sleep_duration_hours = max(1.0, sleep_duration_hours)
            if day_length_hours is not None:
                schedule.day_length_hours = max(1.0, day_length_hours)
            # Recompute the duration from the start/wake hours if both present.
            if sleep_start_hour is not None and wake_hour is not None:
                span = (wake_hour - sleep_start_hour) % schedule.day_length_hours
                if span > 0:
                    schedule.sleep_duration_hours = span
        return True, f"Updated sleep schedule for {npc_id}", schedule

    def get_sleep_schedule(self, npc_id: str) -> Optional[NPCSleepSchedule]:
        """Return the sleep schedule for an NPC, or None if not registered."""
        with self._lock:
            return self._schedules.get(npc_id)

    def advance_sleep_state(
        self,
        npc_id: str,
        dt: float = 1.0,
    ) -> Tuple[bool, str, NPCSleepState]:
        """Advance an NPC's sleep state machine by dt simulated time.

        The state machine moves AWAKE -> DROWSY -> SLEEPING -> DREAMING ->
        WAKING -> AWAKE based on the current hour of day and the elapsed
        time in each state. When entering DREAMING, a dream is started
        automatically; when leaving DREAMING, the active dream is ended.
        """
        if not npc_id:
            return False, "npc_id must not be empty", NPCSleepState.AWAKE
        with self._lock:
            schedule = self._schedules.get(npc_id)
            profile = self._npcs.get(npc_id)
            if schedule is None or profile is None:
                return False, f"NPC not found: {npc_id}", NPCSleepState.AWAKE

            # Advance the in-day clock.
            schedule.current_hour = (
                schedule.current_hour + dt
            ) % max(self.EPSILON, schedule.day_length_hours)
            schedule.state_timer += dt

            prev_state = schedule.state
            new_state = self._compute_sleep_state(schedule)

            if new_state != prev_state:
                schedule.state = new_state
                schedule.state_timer = 0.0
                # Handle transitions into and out of dreaming.
                if new_state == NPCSleepState.DREAMING and profile.active_sequence_id is None:
                    self.start_dream(npc_id)
                elif prev_state == NPCSleepState.DREAMING and new_state == NPCSleepState.WAKING:
                    if profile.active_sequence_id is not None:
                        self.end_dream(npc_id, profile.active_sequence_id)
                elif new_state == NPCSleepState.AWAKE and prev_state == NPCSleepState.WAKING:
                    # Fully awake; nothing further to do here.
                    pass
                self._emit(
                    DreamEventKind.SLEEP_STATE_CHANGED,
                    {"npc_id": npc_id, "from": prev_state.value,
                     "to": new_state.value},
                    npc_id=npc_id,
                )
            final_state = schedule.state
        return True, f"Advanced sleep state for {npc_id} to {final_state.value}", final_state

    # ------------------------------------------------------------------
    # Dream journal and sequence queries
    # ------------------------------------------------------------------

    def get_dream_journal(self, npc_id: str) -> List[DreamSequence]:
        """Return the ordered dream journal for an NPC, newest last."""
        with self._lock:
            profile = self._npcs.get(npc_id)
            if profile is None:
                return []
            results: List[DreamSequence] = []
            for sid in profile.dream_journal:
                seq = self._sequences.get(sid)
                if seq is not None:
                    results.append(seq)
            return results

    def list_dream_sequences(self) -> List[DreamSequence]:
        """Return all dream sequences known to the system."""
        with self._lock:
            return list(self._sequences.values())

    def get_active_dreams(self) -> List[DreamSequence]:
        """Return all dreams currently in the ACTIVE state."""
        with self._lock:
            return [
                seq for seq in self._sequences.values()
                if seq.status == DreamStatus.ACTIVE
            ]

    def clear_journal(self, npc_id: str) -> Tuple[bool, str]:
        """Clear an NPC's dream journal and recurring-symbol memory."""
        if not npc_id:
            return False, "npc_id must not be empty"
        with self._lock:
            profile = self._npcs.get(npc_id)
            if profile is None:
                return False, f"NPC not found: {npc_id}"
            profile.dream_journal.clear()
            profile.recurring_symbol_ids.clear()
        return True, f"Cleared journal for {npc_id}"

    # ------------------------------------------------------------------
    # System status, stats, snapshot, config
    # ------------------------------------------------------------------

    def get_stats(self) -> DreamStats:
        """Return rolled-up statistics for the system."""
        with self._lock:
            moods = [p.mood for p in self._npcs.values()]
            avg_mood = sum(moods) / len(moods) if moods else 0.0
            avg_duration = (
                self._total_dream_duration / self._total_dreams
                if self._total_dreams > 0 else 0.0
            )
            return DreamStats(
                total_npcs=len(self._npcs),
                total_dreams=self._total_dreams,
                total_prophetic_dreams=self._total_prophetic_dreams,
                total_nightmares=self._total_nightmares,
                total_memories_consolidated=self._total_memories_consolidated,
                total_symbols_registered=len(self._symbols),
                total_archetypes_registered=len(self._archetypes),
                total_dreams_shared=self._total_dreams_shared,
                total_experiences_added=self._total_experiences_added,
                avg_dream_duration=avg_duration,
                avg_mood=avg_mood,
                tick_count=self._tick_count,
            )

    def get_snapshot(self) -> DreamSnapshot:
        """Return a point-in-time snapshot of the whole system."""
        with self._lock:
            active = sum(
                1 for s in self._sequences.values()
                if s.status == DreamStatus.ACTIVE
            )
            sleeping = sum(
                1 for sch in self._schedules.values()
                if sch.state in (NPCSleepState.SLEEPING, NPCSleepState.DREAMING)
            )
            return DreamSnapshot(
                tick_count=self._tick_count,
                active_dreams=active,
                sleeping_npcs=sleeping,
                npc_ids=list(self._npcs.keys()),
                sequence_ids=list(self._sequences.keys()),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a concise status report for monitoring."""
        with self._lock:
            return {
                "initialized": self._seeded,
                "tick_count": self._tick_count,
                "npc_count": len(self._npcs),
                "symbol_count": len(self._symbols),
                "archetype_count": len(self._archetypes),
                "sequence_count": len(self._sequences),
                "active_dreams": sum(
                    1 for s in self._sequences.values()
                    if s.status == DreamStatus.ACTIVE
                ),
                "total_dreams": self._total_dreams,
                "total_prophetic_dreams": self._total_prophetic_dreams,
                "total_nightmares": self._total_nightmares,
                "total_memories_consolidated": self._total_memories_consolidated,
                "total_dreams_shared": self._total_dreams_shared,
                "total_experiences_added": self._total_experiences_added,
            }

    def get_config(self) -> DreamConfig:
        """Return the current configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, DreamConfig]:
        """Update one or more configuration fields by keyword."""
        valid_fields = {
            "dream_duration_base",
            "prophetic_chance_base",
            "nightmare_threshold_base",
            "memory_consolidation_rate",
            "symbol_resolution_rate",
            "max_journal_entries",
            "enable_dream_sharing",
            "enable_prophetic_dreams",
            "enable_nightmares",
            "tick_speed",
            "day_length_hours",
            "mood_decay_per_tick",
            "max_events",
        }
        unknown = [k for k in kwargs if k not in valid_fields]
        if unknown:
            return False, f"Unknown config fields: {', '.join(unknown)}", self._config
        with self._lock:
            for key, value in kwargs.items():
                setattr(self._config, key, value)
        self._emit(
            DreamEventKind.CONFIG_UPDATED,
            {"fields": list(kwargs.keys())},
        )
        return True, f"Config updated: {len(kwargs)} field(s)", self._config

    # ------------------------------------------------------------------
    # Tick loop and events
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the whole system by dt simulated time units.

        Each NPC's sleep schedule is advanced. NPCs entering the DREAMING
        state start a dream automatically; NPCs leaving it end their dream.
        Mood decays slightly each tick so that old moods drift toward
        neutral unless refreshed by new dreams.
        """
        if dt <= 0:
            return {"tick": self._tick_count, "skipped": True, "reason": "dt <= 0"}
        scaled_dt = dt * self._config.tick_speed
        self._tick_count += 1

        dreams_started = 0
        dreams_ended = 0
        state_changes = 0

        with self._lock:
            npc_ids = list(self._npcs.keys())

        for npc_id in npc_ids:
            with self._lock:
                schedule = self._schedules.get(npc_id)
                profile = self._npcs.get(npc_id)
                if schedule is None or profile is None:
                    continue
                prev_state = schedule.state
            ok, _msg, new_state = self.advance_sleep_state(npc_id, scaled_dt)
            if not ok:
                continue
            with self._lock:
                schedule = self._schedules.get(npc_id)
                if schedule is not None and schedule.state != prev_state:
                    state_changes += 1
                    if schedule.state == NPCSleepState.DREAMING:
                        dreams_started += 1
                    elif prev_state == NPCSleepState.DREAMING:
                        dreams_ended += 1
                # Apply a small mood decay toward neutral.
                profile = self._npcs.get(npc_id)
                if profile is not None:
                    decay = self._config.mood_decay_per_tick
                    if profile.mood > 0.5:
                        profile.mood = max(0.5, profile.mood - decay)
                    elif profile.mood < 0.5:
                        profile.mood = min(0.5, profile.mood + decay)

        return {
            "tick": self._tick_count,
            "dt": dt,
            "scaled_dt": round(scaled_dt, 4),
            "npcs_processed": len(npc_ids),
            "dreams_started": dreams_started,
            "dreams_ended": dreams_ended,
            "state_changes": state_changes,
            "active_dreams": len(self.get_active_dreams()),
        }

    def list_events(self) -> List[DreamEvent]:
        """Return all recorded events, oldest first."""
        with self._lock:
            return list(self._events)

    def reset(self) -> Tuple[bool, str]:
        """Clear all runtime data and reload seed data.

        Restores the system to the state it would be in immediately after
        a fresh initialize() call.
        """
        with self._lock:
            self._npcs.clear()
            self._symbols.clear()
            self._archetypes.clear()
            self._sequences.clear()
            self._interpretations.clear()
            self._outcomes.clear()
            self._schedules.clear()
            self._shared_dreams.clear()
            self._events.clear()
            self._tick_count = 0
            self._total_dreams = 0
            self._total_prophetic_dreams = 0
            self._total_nightmares = 0
            self._total_memories_consolidated = 0
            self._total_dreams_shared = 0
            self._total_experiences_added = 0
            self._total_dream_duration = 0.0
            self._seeded = False
        # Reload seed data outside the lock to avoid re-entrancy issues.
        self._load_seed_symbols()
        self._load_seed_archetypes()
        self._load_seed_npcs()
        self._load_seed_sequences()
        self._load_seed_experiences()
        with self._init_lock:
            self._seeded = True
        self._emit(
            DreamEventKind.SYSTEM_RESET,
            {"action": "reset",
             "npcs": len(self._npcs),
             "symbols": len(self._symbols),
             "archetypes": len(self._archetypes)},
        )
        return True, "System reset and seed data reloaded"

    # ------------------------------------------------------------------
    # Internal helpers: seed loading
    # ------------------------------------------------------------------

    def _load_seed_symbols(self) -> None:
        """Load the curated seed symbols into the registry."""
        for entry in _SEED_SYMBOLS:
            symbol = DreamSymbol(
                symbol_id=entry["symbol_id"],
                name=entry["name"],
                description=entry["description"],
                associated_emotions=list(entry["associated_emotions"]),
                associated_memory_types=list(entry["associated_memory_types"]),
                meaning=entry["meaning"],
                rarity=entry["rarity"],
            )
            self._symbols[symbol.symbol_id] = symbol

    def _load_seed_archetypes(self) -> None:
        """Load the curated seed archetypes into the registry."""
        for entry in _SEED_ARCHETYPES:
            archetype = DreamArchetype(
                archetype_id=entry["archetype_id"],
                name=entry["name"],
                description=entry["description"],
                theme=entry["theme"],
                associated_symbol_ids=list(entry["associated_symbol_ids"]),
                mood_modifier=entry["mood_modifier"],
                behavior_modifiers=dict(entry["behavior_modifiers"]),
            )
            self._archetypes[archetype.archetype_id] = archetype

    def _load_seed_npcs(self) -> None:
        """Load the seed NPC profiles and their sleep schedules."""
        for entry in _SEED_NPCS:
            profile = NPCDreamProfile(
                npc_id=entry["npc_id"],
                name=entry["name"],
                personality_traits=dict(entry["personality_traits"]),
                mood=entry["mood"],
                lucidity=entry["lucidity"],
                dream_affinity=entry["dream_affinity"],
                prophetic_chance=entry["prophetic_chance"],
                nightmare_threshold=entry["nightmare_threshold"],
            )
            self._npcs[entry["npc_id"]] = profile
            self._schedules[entry["npc_id"]] = NPCSleepSchedule(
                npc_id=entry["npc_id"],
                sleep_start_hour=entry["sleep_start_hour"],
                wake_hour=entry["wake_hour"],
                sleep_duration_hours=max(
                    1.0,
                    (entry["wake_hour"] - entry["sleep_start_hour"])
                    % self._config.day_length_hours,
                ),
                day_length_hours=self._config.day_length_hours,
            )

    def _load_seed_sequences(self) -> None:
        """Load the sample dream sequences and link them to NPC journals."""
        for entry in _SEED_SEQUENCES:
            sequence = DreamSequence(
                sequence_id=entry["sequence_id"],
                npc_id=entry["npc_id"],
                dream_type=entry["dream_type"],
                intensity=entry["intensity"],
                status=entry["status"],
                phase=entry["phase"],
                symbol_ids=list(entry["symbol_ids"]),
                archetype_ids=list(entry["archetype_ids"]),
                narrative=entry["narrative"],
                is_prophetic=entry.get("is_prophetic", False),
                is_nightmare=entry.get("is_nightmare", False),
                prophecy_hint=entry.get("prophecy_hint"),
                shared_with=list(entry.get("shared_with", [])),
            )
            self._sequences[sequence.sequence_id] = sequence
            profile = self._npcs.get(sequence.npc_id)
            if profile is not None:
                profile.dream_journal.append(sequence.sequence_id)
                profile.total_dreams += 1
            self._total_dreams += 1
            if sequence.is_prophetic:
                self._total_prophetic_dreams += 1
            if sequence.is_nightmare:
                self._total_nightmares += 1
            # Register any shared-dream links.
            for target_id in sequence.shared_with:
                self._shared_dreams[target_id].append(sequence.sequence_id)
                self._total_dreams_shared += 1

    def _load_seed_experiences(self) -> None:
        """Load seed pending experiences into the relevant NPC profiles."""
        for entry in _SEED_EXPERIENCES:
            profile = self._npcs.get(entry["npc_id"])
            if profile is None:
                continue
            memory = DreamMemory(
                npc_id=entry["npc_id"],
                memory_type=entry["memory_type"],
                description=entry["description"],
                emotion=entry["emotion"],
                intensity=entry["intensity"],
            )
            profile.pending_experiences.append(memory)
            self._total_experiences_added += 1

    # ------------------------------------------------------------------
    # Internal helpers: symbol and archetype matching
    # ------------------------------------------------------------------

    def _match_symbols_for_memory(self, memory: DreamMemory) -> List[str]:
        """Return symbol ids whose palette overlaps with a memory.

        A symbol matches if it shares either an associated emotion or an
        associated memory type with the given memory. Rarer symbols are
        less likely to be picked when multiple candidates exist.
        """
        matched: List[str] = []
        for symbol in self._symbols.values():
            emotion_overlap = memory.emotion in symbol.associated_emotions
            type_overlap = memory.memory_type in symbol.associated_memory_types
            if emotion_overlap or type_overlap:
                # Rarer symbols are selected with probability proportional
                # to (1 - rarity) so they appear less often.
                if random.random() <= max(0.1, 1.0 - symbol.rarity):
                    matched.append(symbol.symbol_id)
        return matched

    # ------------------------------------------------------------------
    # Internal helpers: dream classification
    # ------------------------------------------------------------------

    def _classify_dream(
        self,
        profile: NPCDreamProfile,
        memories: List[DreamMemory],
        force_type: Optional[DreamType],
    ) -> Tuple[DreamType, DreamIntensity, bool, bool]:
        """Classify a dream and roll its special flags.

        Returns the dream type, an intensity label, and the nightmare and
        prophetic boolean flags. Nightmares are rolled when the share of
        negative-emotion memories crosses the NPC's threshold. Prophetic
        dreams are rolled against the NPC's prophetic chance.
        """
        if force_type is not None:
            dream_type = force_type
        else:
            dream_type = DreamType.SYMBOLIC

        # Compute the emotional charge of the source memories.
        if memories:
            negative_count = sum(1 for m in memories if m.emotion in _NEGATIVE_EMOTIONS)
            negative_share = negative_count / len(memories)
            avg_intensity = sum(m.intensity for m in memories) / len(memories)
        else:
            negative_share = 0.0
            avg_intensity = 0.4

        # Determine nightmare status.
        is_nightmare = (
            self._config.enable_nightmares
            and negative_share >= profile.nightmare_threshold
        )
        if is_nightmare and force_type is None:
            dream_type = DreamType.NIGHTMARE

        # Determine intensity label from the average experience intensity,
        # nudged upward by the NPC's dream affinity.
        charge = min(1.0, avg_intensity * (0.5 + profile.dream_affinity))
        if charge >= 0.85:
            intensity = DreamIntensity.OVERWHELMING
        elif charge >= 0.65:
            intensity = DreamIntensity.INTENSE
        elif charge >= 0.45:
            intensity = DreamIntensity.VIVID
        elif charge >= 0.25:
            intensity = DreamIntensity.MILD
        else:
            intensity = DreamIntensity.FAINT

        # Roll for a prophetic dream.
        is_prophetic = False
        if self._config.enable_prophetic_dreams and not is_nightmare:
            # Prophetic chance scales with lucidity and dream affinity.
            chance = profile.prophetic_chance * (0.5 + profile.lucidity)
            if random.random() < chance:
                is_prophetic = True
                if force_type is None:
                    dream_type = DreamType.PROPHETIC
                self._total_prophetic_dreams += 1

        if is_nightmare:
            self._total_nightmares += 1

        # A highly lucid NPC may turn an ordinary dream lucid.
        if (
            force_type is None
            and not is_prophetic
            and not is_nightmare
            and random.random() < profile.lucidity * 0.5
        ):
            dream_type = DreamType.LUCID

        return dream_type, intensity, is_nightmare, is_prophetic

    # ------------------------------------------------------------------
    # Internal helpers: narrative assembly
    # ------------------------------------------------------------------

    def _build_narrative(
        self,
        symbol_ids: List[str],
        archetype_ids: List[str],
        dream_type: DreamType,
    ) -> str:
        """Assemble a short narrative string for a dream.

        Combines a random opener, the names of the chosen symbols and
        archetypes, and a random closer into a single evocative sentence.
        """
        opener = random.choice(_NARRATIVE_OPENERS)
        closer = random.choice(_NARRATIVE_CLOSERS)

        symbol_names = [
            self._symbols[sid].name
            for sid in symbol_ids
            if sid in self._symbols
        ]
        archetype_names = [
            self._archetypes[aid].name
            for aid in archetype_ids
            if aid in self._archetypes
        ]

        fragments: List[str] = []
        if symbol_names:
            fragments.append(
                "the shapes of " + ", ".join(symbol_names[:3]) + " took form"
            )
        if archetype_names:
            label = "a motif of " if len(archetype_names) == 1 else "motifs of "
            fragments.append(label + ", ".join(archetype_names[:2]) + " wove through it")

        if not fragments:
            fragments.append("a single shifting image held the dreamer's gaze")

        body = "; ".join(fragments)
        if dream_type == DreamType.NIGHTMARE:
            body += ", darkening at the edges"
        elif dream_type == DreamType.PROPHETIC:
            body += ", charged with a weight beyond itself"
        elif dream_type == DreamType.LUCID:
            body += ", yet the dreamer knew it for a dream"

        return f"{opener} {body}, {closer}"

    # ------------------------------------------------------------------
    # Internal helpers: outcome computation
    # ------------------------------------------------------------------

    def _compute_outcome(
        self,
        profile: NPCDreamProfile,
        sequence: DreamSequence,
    ) -> DreamOutcome:
        """Compute the behavioral and mood deltas a dream produces."""
        # Start from the base mood delta for the dream type.
        mood_delta = _DREAM_TYPE_MOOD_DELTA.get(sequence.dream_type, 0.0)

        # Scale the delta by the dream's intensity weight.
        intensity_weight = _INTENSITY_WEIGHT.get(sequence.intensity, 0.5)
        mood_delta *= 0.5 + intensity_weight

        # Add mood contributions from the archetypes used.
        behavior_modifiers: Dict[str, float] = {}
        for aid in sequence.archetype_ids:
            arch = self._archetypes.get(aid)
            if arch is None:
                continue
            mood_delta += arch.mood_modifier * intensity_weight
            for key, val in arch.behavior_modifiers.items():
                behavior_modifiers[key] = (
                    behavior_modifiers.get(key, 0.0) + val * intensity_weight
                )

        # Nightmares pull mood down further; prophetic dreams lift it.
        if sequence.is_nightmare:
            mood_delta -= 0.05
        if sequence.is_prophetic:
            mood_delta += 0.03

        # Lucid dreams sharpen intuition slightly.
        skill_deltas: Dict[str, float] = {}
        if sequence.dream_type == DreamType.LUCID:
            skill_deltas["focus"] = 0.02

        # Recurring dreams produce small personality drifts.
        personality_shifts: Dict[str, float] = {}
        if sequence.is_recurring:
            for trait, base in profile.personality_traits.items():
                # Drift the trait by a small random amount scaled by intensity.
                drift = (random.random() - 0.5) * 0.04 * intensity_weight
                personality_shifts[trait] = round(drift, 4)

        # Memories added are the dream's source memories, now consolidated.
        memory_ids_added = list(sequence.memory_ids)

        return DreamOutcome(
            sequence_id=sequence.sequence_id,
            npc_id=sequence.npc_id,
            behavior_modifiers=behavior_modifiers,
            mood_delta=mood_delta,
            memory_ids_added=memory_ids_added,
            skill_deltas=skill_deltas,
            personality_shifts=personality_shifts,
        )

    def _apply_outcome_to_profile(
        self,
        profile: NPCDreamProfile,
        outcome: DreamOutcome,
    ) -> None:
        """Apply a computed outcome to an NPC profile in place."""
        # Adjust mood, clamped to [0, 1].
        profile.mood = max(0.0, min(1.0, profile.mood + outcome.mood_delta))

        # Accumulate behavior modifiers, decaying old values slightly so the
        # most recent dreams carry the most weight.
        decay = 0.95
        for key in list(profile.behavior_modifiers.keys()):
            profile.behavior_modifiers[key] *= decay
        for key, val in outcome.behavior_modifiers.items():
            profile.behavior_modifiers[key] = (
                profile.behavior_modifiers.get(key, 0.0) + val
            )
            # Clamp individual modifiers to a reasonable range.
            if profile.behavior_modifiers[key] > 1.0:
                profile.behavior_modifiers[key] = 1.0
            elif profile.behavior_modifiers[key] < -1.0:
                profile.behavior_modifiers[key] = -1.0

        # Apply personality shifts.
        for trait, drift in outcome.personality_shifts.items():
            if trait in profile.personality_traits:
                new_val = profile.personality_traits[trait] + drift
                profile.personality_traits[trait] = max(0.0, min(1.0, new_val))

        # Lucid practice slowly raises lucidity over time.
        if outcome.skill_deltas.get("focus", 0.0) > 0.0:
            profile.lucidity = min(1.0, profile.lucidity + 0.005)

    # ------------------------------------------------------------------
    # Internal helpers: interpretation assembly
    # ------------------------------------------------------------------

    def _build_interpretation_summary(
        self,
        npc_name: str,
        sequence: DreamSequence,
        themes: List[str],
        symbol_meanings: List[str],
    ) -> str:
        """Assemble a human-readable summary of a dream's meaning."""
        parts: List[str] = []
        type_label = sequence.dream_type.value
        parts.append(f"{npc_name}'s {type_label} dream")
        if themes:
            parts.append("turned on the themes of " + ", ".join(themes))
        else:
            parts.append("moved without a single clear theme")
        if symbol_meanings:
            parts.append(
                "its symbols speaking of " + "; ".join(symbol_meanings[:2])
            )
        if sequence.is_prophetic:
            parts.append("and carried the unmistakable charge of a prophecy")
        if sequence.is_nightmare:
            parts.append("though shadowed throughout by dread")
        return ", ".join(parts) + "."

    def _build_insights(
        self,
        sequence: DreamSequence,
        themes: List[str],
        symbol_meanings: List[str],
    ) -> List[str]:
        """Produce a list of concise insights about a dream."""
        insights: List[str] = []
        if sequence.is_prophetic:
            insights.append(
                "The dream bears the marks of foresight; its imagery may "
                "prefigure a near-future event."
            )
        if sequence.is_nightmare:
            insights.append(
                "The nightmare points to anxieties the NPC has not yet "
                "processed while awake."
            )
        if sequence.is_recurring:
            insights.append(
                "This dream has returned before, suggesting an unresolved "
                "thread in the NPC's inner life."
            )
        for theme in themes[:2]:
            insights.append(f"The theme of {theme} is active and shaping behavior.")
        for meaning in symbol_meanings[:1]:
            insights.append(f"A central symbol suggests: {meaning}")
        if not insights:
            insights.append(
                "The dream was quiet and ordinary, leaving only a faint impression."
            )
        return insights

    def _predict_outcome(self, sequence: DreamSequence) -> str:
        """Produce a short predicted-outcome string for an interpretation."""
        if sequence.is_prophetic:
            return (
                "Expect the dreamer to act on the prophecy soon, possibly "
                "seeking out the people or places seen in the vision."
            )
        if sequence.is_nightmare:
            return (
                "Expect a withdrawn or irritable mood upon waking, softening "
                "over the following day."
            )
        if sequence.dream_type == DreamType.LUCID:
            return (
                "Expect sharper focus and a measure of calm confidence after "
                "waking."
            )
        return (
            "Expect a subtle shift in temperament, with no dramatic change "
            "in immediate plans."
        )

    # ------------------------------------------------------------------
    # Internal helpers: sleep state machine
    # ------------------------------------------------------------------

    def _compute_sleep_state(self, schedule: NPCSleepSchedule) -> NPCSleepState:
        """Determine the next sleep state from the current hour and timer.

        The state machine uses the in-day clock to decide whether the NPC
        should be in the asleep block (drowsy -> sleeping -> dreaming) or
        awake, and uses the state timer to pace transitions within each
        block.
        """
        hour = schedule.current_hour
        start = schedule.sleep_start_hour
        wake = schedule.wake_hour

        # Determine whether the current hour falls inside the sleep window,
        # accounting for windows that wrap past midnight.
        if start <= wake:
            in_sleep_window = start <= hour < wake
        else:
            in_sleep_window = hour >= start or hour < wake

        current = schedule.state

        if not in_sleep_window:
            # The NPC should be awake or moving toward waking.
            if current == NPCSleepState.DREAMING:
                return NPCSleepState.WAKING
            if current == NPCSleepState.SLEEPING:
                return NPCSleepState.WAKING
            if current == NPCSleepState.WAKING:
                # Stay in waking briefly, then go fully awake.
                if schedule.state_timer >= self._config.dream_duration_base * 0.2:
                    return NPCSleepState.AWAKE
                return NPCSleepState.WAKING
            return NPCSleepState.AWAKE

        # Inside the sleep window: pace the descent into dreaming.
        if current == NPCSleepState.AWAKE:
            return NPCSleepState.DROWSY
        if current == NPCSleepState.DROWSY:
            if schedule.state_timer >= self._config.dream_duration_base * 0.15:
                return NPCSleepState.SLEEPING
            return NPCSleepState.DROWSY
        if current == NPCSleepState.SLEEPING:
            if schedule.state_timer >= self._config.dream_duration_base * 0.3:
                return NPCSleepState.DREAMING
            return NPCSleepState.SLEEPING
        if current == NPCSleepState.DREAMING:
            # Dreams run for the base duration before resolution.
            if schedule.state_timer >= self._config.dream_duration_base:
                return NPCSleepState.WAKING
            return NPCSleepState.DREAMING
        if current == NPCSleepState.WAKING:
            if schedule.state_timer >= self._config.dream_duration_base * 0.2:
                return NPCSleepState.AWAKE
            return NPCSleepState.WAKING
        return NPCSleepState.AWAKE

    # ------------------------------------------------------------------
    # Internal helpers: prophecy and events
    # ------------------------------------------------------------------

    def _roll_prophecy_hint(self) -> str:
        """Generate a short, evocative prophecy hint string."""
        subjects = [
            "a stranger", "an old friend", "a closed gate", "a distant fire",
            "a fallen star", "a spoken name", "a hidden path", "a broken blade",
        ]
        actions = [
            "will arrive", "will be revealed", "will open", "will burn out",
            "will fall", "will be spoken", "will be found", "will be mended",
        ]
        timings = [
            "before the next dawn", "within three turns of the hourglass",
            "when the moon is full", "before the season turns",
            "at the moment of greatest need", "sooner than expected",
        ]
        return (
            f"{random.choice(subjects)} {random.choice(actions)} "
            f"{random.choice(timings)}."
        )

    def _emit(
        self,
        kind: DreamEventKind,
        payload: Optional[Dict[str, Any]] = None,
        npc_id: Optional[str] = None,
        sequence_id: Optional[str] = None,
    ) -> None:
        """Record an event, capping the total stored to max_events."""
        event = DreamEvent(
            kind=kind,
            payload=dict(payload or {}),
            npc_id=npc_id,
            sequence_id=sequence_id,
        )
        self._events.append(event)
        cap = self._config.max_events
        if len(self._events) > cap:
            overflow = len(self._events) - cap
            del self._events[:overflow]


# ---------------------------------------------------------------------------
# Module-level factory
# ---------------------------------------------------------------------------

def get_npc_dream_simulation_system() -> NPCDreamSimulationSystem:
    """Return the singleton NPCDreamSimulationSystem instance, seeding on first use.

    This is the primary entry point for callers. On the first invocation it
    creates the singleton and loads all seed data so the system is ready to
    use immediately.
    """
    inst = NPCDreamSimulationSystem.get_instance()
    if not getattr(inst, "_seeded", False):
        inst.initialize()
    return inst
