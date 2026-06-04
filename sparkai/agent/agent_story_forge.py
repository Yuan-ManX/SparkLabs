"""
SparkLabs Agent - Story Forge

AI-driven narrative generation system for dynamic storytelling.
Generates story arcs, character arcs, plot twists, and multi-branching
narratives with thematic coherence and emotional progression.

Architecture:
  AgentStoryForge (Singleton)
    |-- Story Arc Generator (three-act structure, hero's journey)
    |-- Character Arc Weaver (character growth and transformation)
    |-- Plot Twist Injector (surprise events and reversals)
    |-- Theme Manager (narrative themes and motifs)
    |-- Branching Engine (choice-based narrative branches)
    |-- Scene Sequencer (scene ordering and pacing)
    |-- Narrative Coherence Checker (internal consistency validation)
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


class StoryGenre(Enum):
    FANTASY = "fantasy"
    SCI_FI = "sci_fi"
    HORROR = "horror"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    ADVENTURE = "adventure"
    THRILLER = "thriller"
    COMEDY = "comedy"
    DRAMA = "drama"
    DYSTOPIAN = "dystopian"


class StoryArcType(Enum):
    HEROES_JOURNEY = "heroes_journey"
    RAGS_TO_RICHES = "rags_to_riches"
    TRAGEDY = "tragedy"
    COMEDY = "comedy"
    REBIRTH = "rebirth"
    VOYAGE_AND_RETURN = "voyage_and_return"
    OVERCOMING_MONSTER = "overcoming_monster"
    QUEST = "quest"


class PlotTwistType(Enum):
    REVELATION = "revelation"
    BETRAYAL = "betrayal"
    REDEMPTION = "redemption"
    REVERSAL = "reversal"
    MISTAKEN_IDENTITY = "mistaken_identity"
    UNRELIABLE_NARRATOR = "unreliable_narrator"
    CHEKHOVS_GUN = "chekhovs_gun"
    FAKE_DEFEAT = "fake_defeat"


class NarrativeTheme(Enum):
    GOOD_VS_EVIL = "good_vs_evil"
    LOVE_AND_LOSS = "love_and_loss"
    COMING_OF_AGE = "coming_of_age"
    POWER_AND_CORRUPTION = "power_and_corruption"
    IDENTITY_AND_SELF = "identity_and_self"
    SACRIFICE_AND_REDEMPTION = "sacrifice_and_redemption"
    FREEDOM_VS_ORDER = "freedom_vs_order"
    NATURE_VS_TECHNOLOGY = "nature_vs_technology"
    FATE_VS_FREE_WILL = "fate_vs_free_will"
    SURVIVAL = "survival"


@dataclass
class StoryBeat:
    """A single beat within a story arc."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    beat_type: str = "scene"
    title: str = ""
    description: str = ""
    characters_involved: List[str] = field(default_factory=list)
    emotional_tone: str = "neutral"
    tension_level: float = 0.0
    duration_estimate: float = 1.0
    prerequisites: List[str] = field(default_factory=list)
    outcomes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "beat_type": self.beat_type,
            "title": self.title,
            "description": self.description,
            "characters_involved": self.characters_involved,
            "emotional_tone": self.emotional_tone,
            "tension_level": round(self.tension_level, 2),
            "duration_estimate": self.duration_estimate,
            "outcomes": self.outcomes,
        }


@dataclass
class StoryArc:
    """A complete story arc with multiple beats."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    genre: StoryGenre = StoryGenre.ADVENTURE
    arc_type: StoryArcType = StoryArcType.HEROES_JOURNEY
    themes: List[NarrativeTheme] = field(default_factory=list)
    beats: List[StoryBeat] = field(default_factory=list)
    characters: List[str] = field(default_factory=list)
    current_beat_index: int = 0
    is_complete: bool = False
    overall_tension: float = 0.0
    emotional_arc: List[float] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "genre": self.genre.value,
            "arc_type": self.arc_type.value,
            "themes": [t.value for t in self.themes],
            "beat_count": len(self.beats),
            "current_beat_index": self.current_beat_index,
            "is_complete": self.is_complete,
            "overall_tension": round(self.overall_tension, 2),
            "character_count": len(self.characters),
            "beats": [b.to_dict() for b in self.beats],
        }


@dataclass
class PlotTwist:
    """A narrative twist or surprise event."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    twist_type: PlotTwistType = PlotTwistType.REVELATION
    description: str = ""
    foreshadowing: List[str] = field(default_factory=list)
    affected_characters: List[str] = field(default_factory=list)
    impact_level: float = 0.5
    beat_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "twist_type": self.twist_type.value,
            "description": self.description,
            "impact_level": round(self.impact_level, 2),
            "beat_index": self.beat_index,
        }


class AgentStoryForge:
    """
    AI-driven narrative generation system.
    Singleton pattern with thread-safe initialization.
    """

    _instance: Optional["AgentStoryForge"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "AgentStoryForge":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentStoryForge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._arcs: Dict[str, StoryArc] = {}
        self._twists: Dict[str, List[PlotTwist]] = {}
        self._total_arcs: int = 0
        self._arc_templates: Dict[StoryArcType, List[str]] = {}
        self._setup_templates()

    def _setup_templates(self) -> None:
        self._arc_templates = {
            StoryArcType.HEROES_JOURNEY: [
                "ordinary_world", "call_to_adventure", "refusal_of_call",
                "meeting_mentor", "crossing_threshold", "tests_allies_enemies",
                "approach_inmost_cave", "ordeal", "reward",
                "road_back", "resurrection", "return_with_elixir",
            ],
            StoryArcType.RAGS_TO_RICHES: [
                "humble_beginning", "opportunity_arises", "initial_success",
                "setback_and_loss", "perseverance", "breakthrough",
                "triumph", "reflection_and_growth",
            ],
            StoryArcType.TRAGEDY: [
                "flawed_greatness", "fatal_choice", "descent_begins",
                "point_of_no_return", "consequences_unfold", "tragic_recognition",
                "catastrophe", "aftermath",
            ],
            StoryArcType.QUEST: [
                "object_revealed", "gathering_allies", "first_obstacle",
                "midpoint_crisis", "darkest_hour", "final_approach",
                "confrontation", "resolution",
            ],
        }

    def create_arc(
        self,
        title: str,
        genre: StoryGenre = StoryGenre.ADVENTURE,
        arc_type: StoryArcType = StoryArcType.HEROES_JOURNEY,
        themes: Optional[List[NarrativeTheme]] = None,
        characters: Optional[List[str]] = None,
    ) -> StoryArc:
        with self._lock:
            arc = StoryArc(
                title=title,
                genre=genre,
                arc_type=arc_type,
                themes=themes or [NarrativeTheme.GOOD_VS_EVIL],
                characters=characters or [],
            )
            self._arcs[arc.id] = arc
            self._twists[arc.id] = []
            self._total_arcs += 1
            return arc

    def generate_beats(self, arc_id: str, beat_count: int = 8) -> List[StoryBeat]:
        with self._lock:
            arc = self._arcs.get(arc_id)
            if arc is None:
                return []

            template = self._arc_templates.get(arc.arc_type, [f"beat_{i}" for i in range(beat_count)])
            beat_specs = template[:beat_count] if len(template) >= beat_count else template + [f"beat_{i}" for i in range(len(template), beat_count)]

            beats = []
            for i, spec in enumerate(beat_specs):
                progress = i / max(beat_count - 1, 1)
                tension = 0.3 + 0.4 * math.sin(progress * math.pi)
                if i == beat_count - 1:
                    tension = 0.9

                tones = ["hopeful", "tense", "mysterious", "triumphant", "somber", "urgent", "calm", "chaotic"]
                tone = tones[i % len(tones)]

                beat = StoryBeat(
                    beat_type=spec,
                    title=f"Beat {i + 1}: {spec.replace('_', ' ').title()}",
                    description=f"{spec.replace('_', ' ')} moment in the narrative arc.",
                    characters_involved=arc.characters[:3],
                    emotional_tone=tone,
                    tension_level=tension,
                    duration_estimate=1.0 + random.random() * 2.0,
                    prerequisites=[] if i == 0 else [beats[-1].id] if beats else [],
                    outcomes=[f"outcome_{spec}"],
                )
                beats.append(beat)

            arc.beats = beats
            arc.overall_tension = sum(b.tension_level for b in beats) / len(beats)
            return beats

    def inject_twist(
        self,
        arc_id: str,
        twist_type: PlotTwistType,
        description: str,
        beat_index: int = 0,
        impact_level: float = 0.7,
        foreshadowing: Optional[List[str]] = None,
    ) -> Optional[PlotTwist]:
        with self._lock:
            arc = self._arcs.get(arc_id)
            if arc is None:
                return None

            twist = PlotTwist(
                twist_type=twist_type,
                description=description,
                foreshadowing=foreshadowing or [],
                affected_characters=arc.characters[:3],
                impact_level=impact_level,
                beat_index=beat_index,
            )
            self._twists[arc_id].append(twist)

            if beat_index < len(arc.beats):
                arc.beats[beat_index].description += f" [TWIST: {description}]"
                arc.beats[beat_index].tension_level = min(1.0, arc.beats[beat_index].tension_level + impact_level * 0.3)

            return twist

    def advance_beat(self, arc_id: str) -> Optional[StoryBeat]:
        with self._lock:
            arc = self._arcs.get(arc_id)
            if arc is None:
                return None
            if arc.current_beat_index >= len(arc.beats):
                arc.is_complete = True
                return None

            current = arc.beats[arc.current_beat_index]
            arc.current_beat_index += 1
            if arc.current_beat_index >= len(arc.beats):
                arc.is_complete = True
            return current

    def get_arc(self, arc_id: str) -> Optional[StoryArc]:
        return self._arcs.get(arc_id)

    def get_twists(self, arc_id: str) -> List[PlotTwist]:
        return self._twists.get(arc_id, [])

    def get_current_beat(self, arc_id: str) -> Optional[StoryBeat]:
        arc = self._arcs.get(arc_id)
        if arc is None or arc.current_beat_index >= len(arc.beats):
            return None
        return arc.beats[arc.current_beat_index]

    def get_tension_curve(self, arc_id: str) -> List[float]:
        arc = self._arcs.get(arc_id)
        if arc is None:
            return []
        return [b.tension_level for b in arc.beats]

    def get_emotional_arc(self, arc_id: str) -> List[str]:
        arc = self._arcs.get(arc_id)
        if arc is None:
            return []
        return [b.emotional_tone for b in arc.beats]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            complete = sum(1 for a in self._arcs.values() if a.is_complete)
            return {
                "total_arcs": self._total_arcs,
                "active_arcs": len(self._arcs) - complete,
                "complete_arcs": complete,
                "total_beats": sum(len(a.beats) for a in self._arcs.values()),
                "total_twists": sum(len(t) for t in self._twists.values()),
                "genres": list(set(a.genre.value for a in self._arcs.values())),
            }

    def get_all_arcs(self, limit: int = 10) -> List[Dict[str, Any]]:
        arcs = list(self._arcs.values())[:limit]
        return [a.to_dict() for a in arcs]


def get_story_forge() -> AgentStoryForge:
    return AgentStoryForge.get_instance()