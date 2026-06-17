"""
SparkLabs Agent Emergent Storyteller

Provides autonomous emergent narrative generation for AI-native game worlds.
Stories emerge from entity interactions, world events, and character decisions
rather than being pre-scripted. The system tracks narrative arcs, generates
story beats, and adapts to player actions.

Core architecture:
  - Narrative Tracking: Monitors world state for story-worthy events
  - Arc Management: Tracks character arcs, plot lines, and themes
  - Beat Generation: Creates story beats from significant interactions
  - Player Impact: Adapts narrative based on player choices and actions
  - Story Synthesis: Composes coherent narratives from emergent events
  - Theme Detection: Identifies and reinforces narrative themes
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NarrativeTheme(Enum):
    """Thematic categories for emergent narratives."""
    REDEMPTION = "redemption"
    DISCOVERY = "discovery"
    CONFLICT = "conflict"
    COOPERATION = "cooperation"
    SURVIVAL = "survival"
    BETRAYAL = "betrayal"
    SACRIFICE = "sacrifice"
    ASCENSION = "ascension"
    FALL = "fall"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    REVENGE = "revenge"
    LEGACY = "legacy"
    TRANSFORMATION = "transformation"


class StoryArcType(Enum):
    """Types of narrative arcs."""
    HERO_JOURNEY = "hero_journey"
    TRAGIC_FALL = "tragic_fall"
    COMING_OF_AGE = "coming_of_age"
    RAGS_TO_RICHES = "rags_to_riches"
    OVERCOMING_MONSTER = "overcoming_monster"
    VOYAGE_AND_RETURN = "voyage_and_return"
    REBIRTH = "rebirth"
    MYSTERY_UNRAVEL = "mystery_unravel"
    RIVALRY = "rivalry"
    QUEST = "quest"


class StoryBeatType(Enum):
    """Types of story beats in the narrative."""
    INCITING_INCIDENT = "inciting_incident"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"
    TWIST = "twist"
    REVELATION = "revelation"
    CHARACTER_MOMENT = "character_moment"
    WORLD_EVENT = "world_event"
    PLAYER_CHOICE = "player_choice"


class ArcStage(Enum):
    """Stages of a narrative arc."""
    SETUP = "setup"
    DEVELOPMENT = "development"
    CRISIS = "crisis"
    CLIMAX = "climax"
    AFTERMATH = "aftermath"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class PlayerImpactLevel(Enum):
    """Level of player impact on the narrative."""
    NONE = "none"
    MINOR = "minor"
    SIGNIFICANT = "significant"
    MAJOR = "major"
    DEFINING = "defining"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class StoryBeat:
    """A single beat in the emergent narrative."""
    beat_id: str
    beat_type: StoryBeatType
    title: str
    description: str
    involved_entities: List[str] = field(default_factory=list)
    parent_arc_id: Optional[str] = None
    themes: List[str] = field(default_factory=list)
    player_impact: PlayerImpactLevel = PlayerImpactLevel.NONE
    significance: float = 0.5
    sequence_number: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class NarrativeArc:
    """A narrative arc tracking a character or plot development."""
    arc_id: str
    arc_type: StoryArcType
    title: str
    protagonist_id: str
    description: str
    stage: ArcStage = ArcStage.SETUP
    beats: List[StoryBeat] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    antagonist_id: Optional[str] = None
    importance: float = 0.5
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


@dataclass
class WorldChronicle:
    """A chronicle of significant world events forming a narrative."""
    chronicle_id: str
    title: str
    description: str
    events: List[Dict[str, Any]] = field(default_factory=list)
    key_entities: List[str] = field(default_factory=list)
    dominant_themes: List[str] = field(default_factory=list)
    time_span_ticks: int = 0
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Emergent Storyteller Engine
# ---------------------------------------------------------------------------

class EmergentStorytellerEngine:
    """Autonomous emergent narrative generation for AI-native game worlds.

    Stories emerge naturally from the simulation rather than being
    pre-scripted. The engine tracks significant events, character arcs,
    and player actions to weave coherent narratives.

    Usage:
        engine = get_emergent_storyteller_engine()
        beat = engine.generate_story_beat(
            entity_id="hero_1",
            beat_type="rising_action",
            description="The hero discovered the ancient ruins"
        )
        arc = engine.create_character_arc(
            protagonist_id="hero_1",
            arc_type="hero_journey",
            title="The Hero's Awakening"
        )
    """

    _instance: Optional["EmergentStorytellerEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_ARCS: int = 500
    MAX_BEATS_PER_ARC: int = 50
    MAX_CHRONICLES: int = 100
    SIGNIFICANCE_THRESHOLD: float = 0.4

    def __new__(cls) -> "EmergentStorytellerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EmergentStorytellerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        time.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._arcs: Dict[str, NarrativeArc] = {}
            self._beats: Dict[str, StoryBeat] = {}
            self._chronicles: Dict[str, WorldChronicle] = {}
            self._entity_arcs: Dict[str, List[str]] = {}  # entity_id -> arc_ids
            self._theme_index: Dict[str, List[str]] = {}
            self._total_beats_generated: int = 0
            self._total_arcs_created: int = 0
            self._initialized = True

    # ------------------------------------------------------------------
    # Story Beat Generation
    # ------------------------------------------------------------------

    def generate_story_beat(
        self,
        entity_id: str,
        beat_type: str,
        title: str,
        description: str,
        involved_entities: Optional[List[str]] = None,
        parent_arc_id: Optional[str] = None,
        themes: Optional[List[str]] = None,
        player_impact: str = "none",
        significance: float = 0.5,
    ) -> StoryBeat:
        """Generate a new story beat from an emergent event.

        Args:
            entity_id: Primary entity driving the beat.
            beat_type: Category of the story beat.
            title: Short title for the beat.
            description: Detailed description of what happened.
            involved_entities: Other entities involved.
            parent_arc_id: Parent narrative arc ID.
            themes: Thematic tags.
            player_impact: Level of player impact.
            significance: How significant this beat is (0.0 to 1.0).

        Returns:
            The generated StoryBeat.
        """
        time.sleep(0.001)
        with self._lock:
            beat = StoryBeat(
                beat_id=uuid.uuid4().hex,
                beat_type=StoryBeatType(beat_type),
                title=title,
                description=description,
                involved_entities=involved_entities or [entity_id],
                parent_arc_id=parent_arc_id,
                themes=themes or [],
                player_impact=PlayerImpactLevel(player_impact),
                significance=significance,
            )

            self._beats[beat.beat_id] = beat
            self._total_beats_generated += 1

            # Add to parent arc
            if parent_arc_id and parent_arc_id in self._arcs:
                arc = self._arcs[parent_arc_id]
                beat.sequence_number = len(arc.beats)
                arc.beats.append(beat)

                # Update arc stage based on beats
                self._update_arc_stage(arc)

            # Index themes
            for theme in beat.themes:
                self._theme_index.setdefault(theme, []).append(beat.beat_id)

            return beat

    def _update_arc_stage(self, arc: NarrativeArc) -> None:
        """Update the narrative arc stage based on beat progression."""
        total = len(arc.beats)
        if total == 0:
            arc.stage = ArcStage.SETUP
        elif total <= 5:
            arc.stage = ArcStage.DEVELOPMENT
        elif any(b.beat_type == StoryBeatType.CLIMAX for b in arc.beats):
            arc.stage = ArcStage.CLIMAX
        elif any(b.beat_type == StoryBeatType.RESOLUTION for b in arc.beats):
            arc.stage = ArcStage.AFTERMATH
        elif total > 10:
            arc.stage = ArcStage.CRISIS

        if arc.stage == ArcStage.AFTERMATH:
            arc.is_active = False
            arc.completed_at = time.time()

    # ------------------------------------------------------------------
    # Narrative Arc Management
    # ------------------------------------------------------------------

    def create_character_arc(
        self,
        protagonist_id: str,
        arc_type: str,
        title: str,
        description: str = "",
        antagonist_id: Optional[str] = None,
        themes: Optional[List[str]] = None,
        importance: float = 0.5,
    ) -> NarrativeArc:
        """Create a narrative arc for a character.

        Args:
            protagonist_id: The main character's entity ID.
            arc_type: Type of narrative arc.
            title: Arc title.
            description: Arc description.
            antagonist_id: Optional antagonist entity ID.
            themes: Thematic tags.
            importance: Arc importance (0.0 to 1.0).

        Returns:
            The created NarrativeArc.
        """
        time.sleep(0.001)
        with self._lock:
            arc = NarrativeArc(
                arc_id=uuid.uuid4().hex,
                arc_type=StoryArcType(arc_type),
                title=title,
                protagonist_id=protagonist_id,
                description=description,
                antagonist_id=antagonist_id,
                themes=themes or [],
                importance=importance,
            )

            self._arcs[arc.arc_id] = arc
            self._entity_arcs.setdefault(protagonist_id, []).append(arc.arc_id)
            self._total_arcs_created += 1

            # Index themes
            for theme in arc.themes:
                self._theme_index.setdefault(theme, []).append(arc.arc_id)

            return arc

    def advance_arc(
        self,
        arc_id: str,
        new_stage: Optional[str] = None,
    ) -> Optional[NarrativeArc]:
        """Manually advance a narrative arc to a new stage.

        Args:
            arc_id: The arc to advance.
            new_stage: Target stage, or None to auto-advance.

        Returns:
            The updated arc, or None if not found.
        """
        with self._lock:
            if arc_id not in self._arcs:
                return None

            arc = self._arcs[arc_id]

            if new_stage:
                arc.stage = ArcStage(new_stage)
            else:
                self._update_arc_stage(arc)

            if arc.stage == ArcStage.COMPLETED:
                arc.is_active = False
                arc.completed_at = time.time()

            return arc

    def get_character_arcs(
        self,
        entity_id: str,
        active_only: bool = True,
    ) -> List[NarrativeArc]:
        """Get all narrative arcs for a character.

        Args:
            entity_id: The character's entity ID.
            active_only: If True, only return active arcs.

        Returns:
            List of NarrativeArc instances.
        """
        with self._lock:
            arc_ids = self._entity_arcs.get(entity_id, [])
            arcs = [self._arcs[aid] for aid in arc_ids if aid in self._arcs]
            if active_only:
                arcs = [a for a in arcs if a.is_active]
            return sorted(arcs, key=lambda a: a.importance, reverse=True)

    # ------------------------------------------------------------------
    # Chronicle Management
    # ------------------------------------------------------------------

    def create_chronicle(
        self,
        title: str,
        description: str,
        key_entities: Optional[List[str]] = None,
        time_span_ticks: int = 0,
    ) -> WorldChronicle:
        """Create a chronicle of world events.

        Args:
            title: Chronicle title.
            description: Chronicle description.
            key_entities: Key entities involved.
            time_span_ticks: Duration of the chronicle in ticks.

        Returns:
            The created WorldChronicle.
        """
        time.sleep(0.001)
        with self._lock:
            chronicle = WorldChronicle(
                chronicle_id=uuid.uuid4().hex,
                title=title,
                description=description,
                key_entities=key_entities or [],
                time_span_ticks=time_span_ticks,
            )

            self._chronicles[chronicle.chronicle_id] = chronicle
            return chronicle

    def add_event_to_chronicle(
        self,
        chronicle_id: str,
        event_data: Dict[str, Any],
    ) -> Optional[WorldChronicle]:
        """Add an event to an existing chronicle.

        Args:
            chronicle_id: The chronicle to add to.
            event_data: Event data to record.

        Returns:
            The updated chronicle, or None if not found.
        """
        with self._lock:
            if chronicle_id not in self._chronicles:
                return None

            chronicle = self._chronicles[chronicle_id]
            event_data["timestamp"] = time.time()
            chronicle.events.append(event_data)

            # Update dominant themes
            theme_counts: Dict[str, int] = {}
            for event in chronicle.events:
                for theme in event.get("themes", []):
                    theme_counts[theme] = theme_counts.get(theme, 0) + 1

            chronicle.dominant_themes = sorted(
                theme_counts.keys(),
                key=lambda t: theme_counts[t],
                reverse=True,
            )[:5]

            return chronicle

    # ------------------------------------------------------------------
    # Narrative Synthesis
    # ------------------------------------------------------------------

    def synthesize_narrative(
        self,
        entity_id: Optional[str] = None,
        time_range_ticks: Optional[int] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Synthesize a coherent narrative from emergent events.

        Args:
            entity_id: Optional entity to focus the narrative on.
            time_range_ticks: Optional time range in ticks.
            limit: Maximum number of beats to include.

        Returns:
            Synthesized narrative summary.
        """
        with self._lock:
            beats = list(self._beats.values())

            if entity_id:
                beats = [
                    b for b in beats
                    if entity_id in b.involved_entities
                ]

            if time_range_ticks:
                cutoff = time.time() - time_range_ticks
                beats = [b for b in beats if b.timestamp >= cutoff]

            # Sort by significance
            beats.sort(key=lambda b: b.significance, reverse=True)
            beats = beats[:limit]

            # Sort by timestamp for narrative flow
            beats.sort(key=lambda b: b.timestamp)

            return {
                "narrative_title": self._generate_narrative_title(beats),
                "beats": [
                    {
                        "beat_id": b.beat_id,
                        "type": b.beat_type.value,
                        "title": b.title,
                        "description": b.description,
                        "significance": b.significance,
                        "player_impact": b.player_impact.value,
                        "themes": b.themes,
                        "timestamp": b.timestamp,
                    }
                    for b in beats
                ],
                "dominant_themes": self._extract_dominant_themes(beats),
                "total_beats": len(beats),
            }

    def _generate_narrative_title(self, beats: List[StoryBeat]) -> str:
        """Generate a descriptive title from a set of beats."""
        if not beats:
            return "Untold Story"

        themes = self._extract_dominant_themes(beats)
        primary_type = beats[-1].beat_type.value if beats else "event"

        if themes:
            return f"The {themes[0]} of {primary_type.replace('_', ' ').title()}"
        return f"A Tale of {primary_type.replace('_', ' ').title()}"

    def _extract_dominant_themes(self, beats: List[StoryBeat]) -> List[str]:
        """Extract dominant themes from a set of beats."""
        theme_counts: Dict[str, int] = {}
        for beat in beats:
            for theme in beat.themes:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1

        return sorted(
            theme_counts.keys(),
            key=lambda t: theme_counts[t],
            reverse=True,
        )[:3]

    # ------------------------------------------------------------------
    # Player Impact
    # ------------------------------------------------------------------

    def record_player_action(
        self,
        action_description: str,
        affected_entities: List[str],
        impact_level: str = "minor",
        themes: Optional[List[str]] = None,
    ) -> StoryBeat:
        """Record a player action that impacts the narrative.

        Args:
            action_description: What the player did.
            affected_entities: Entities affected by the action.
            impact_level: How significant the impact is.
            themes: Thematic tags.

        Returns:
            The generated StoryBeat for the player action.
        """
        return self.generate_story_beat(
            entity_id=affected_entities[0] if affected_entities else "player",
            beat_type="player_choice",
            title="Player Action",
            description=action_description,
            involved_entities=affected_entities,
            themes=themes,
            player_impact=impact_level,
            significance=0.8,
        )

    def get_player_impact_summary(
        self,
        entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get a summary of player impact on the narrative.

        Args:
            entity_id: Optional entity to focus on.

        Returns:
            Summary of player impact.
        """
        with self._lock:
            player_beats = [
                b for b in self._beats.values()
                if b.beat_type == StoryBeatType.PLAYER_CHOICE
            ]

            if entity_id:
                player_beats = [
                    b for b in player_beats
                    if entity_id in b.involved_entities
                ]

            impact_levels = {
                "none": 0,
                "minor": 0,
                "significant": 0,
                "major": 0,
                "defining": 0,
            }
            for beat in player_beats:
                impact_levels[beat.player_impact.value] += 1

            return {
                "total_player_actions": len(player_beats),
                "impact_distribution": impact_levels,
                "recent_actions": [
                    {
                        "description": b.description,
                        "impact": b.player_impact.value,
                        "timestamp": b.timestamp,
                    }
                    for b in sorted(player_beats, key=lambda x: x.timestamp, reverse=True)[:5]
                ],
            }

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_storyteller_stats(self) -> Dict[str, Any]:
        """Get comprehensive storyteller statistics."""
        with self._lock:
            active_arcs = sum(1 for a in self._arcs.values() if a.is_active)
            completed_arcs = sum(1 for a in self._arcs.values() if not a.is_active)

            return {
                "total_beats": self._total_beats_generated,
                "total_arcs": self._total_arcs_created,
                "active_arcs": active_arcs,
                "completed_arcs": completed_arcs,
                "chronicles": len(self._chronicles),
                "stored_beats": len(self._beats),
                "stored_arcs": len(self._arcs),
            }

    def get_active_arcs(self) -> List[Dict[str, Any]]:
        """Get all currently active narrative arcs."""
        with self._lock:
            return [
                {
                    "arc_id": a.arc_id,
                    "title": a.title,
                    "arc_type": a.arc_type.value,
                    "protagonist_id": a.protagonist_id,
                    "stage": a.stage.value,
                    "beat_count": len(a.beats),
                    "importance": a.importance,
                    "themes": a.themes,
                }
                for a in self._arcs.values()
                if a.is_active
            ]

    def get_recent_beats(
        self,
        limit: int = 20,
        entity_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent story beats."""
        with self._lock:
            beats = list(self._beats.values())
            if entity_id:
                beats = [b for b in beats if entity_id in b.involved_entities]

            beats.sort(key=lambda b: b.timestamp, reverse=True)
            return [
                {
                    "beat_id": b.beat_id,
                    "type": b.beat_type.value,
                    "title": b.title,
                    "description": b.description,
                    "significance": b.significance,
                    "player_impact": b.player_impact.value,
                    "themes": b.themes,
                    "timestamp": b.timestamp,
                }
                for b in beats[:limit]
            ]


# ---------------------------------------------------------------------------
# Singleton Accessor
# ---------------------------------------------------------------------------

def get_emergent_storyteller_engine() -> EmergentStorytellerEngine:
    """Get the singleton EmergentStorytellerEngine instance."""
    return EmergentStorytellerEngine.get_instance()