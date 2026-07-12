"""
SparkLabs Agent - AI Narrative Engine

A singleton AI-powered narrative engine that generates dynamic story arcs,
branching narratives, character-driven plots, and world events with rich
narrative context. The engine fuses AI agent reasoning with knowledge graph
connectivity and character simulation to produce emergent storytelling.

Core design principles:
  - Story arcs are dynamic, not fixed — they adapt to player choices and world state
  - Characters drive the narrative through motivations, relationships, and arcs
  - Plot threads weave together into cohesive story tapestries
  - Narrative beats emerge from character interactions and world events
  - Branching choices have meaningful consequences tracked over time
  - World lore is generated consistently with established canon
  - Quest narratives are contextualized within larger story frameworks

Architecture:
  NarrativeEngine (singleton)
    |-- NarrativeGenre, StoryArcStatus, PlotThreadStatus, CharacterRole,
       NarrativeBeatType, ChoiceConsequence, LoreCategory
    |-- StoryArc, PlotThread, NarrativeCharacter, NarrativeBeat,
       BranchingChoice, WorldLoreEntry, QuestNarrative, NarrativeSnapshot,
       NarrativeStats, NarrativeConfig, NarrativeEvent
    |-- get_narrative_engine

Core Capabilities:
  - create_story_arc / get_story_arc / list_story_arcs / remove_story_arc
  - advance_story_arc / complete_story_arc / abort_story_arc
  - register_character / get_character / list_characters / remove_character
  - advance_character_arc / update_character_relationship
  - create_plot_thread / get_plot_thread / list_plot_threads / resolve_plot_thread
  - add_narrative_beat / get_narrative_beat / list_narrative_beats
  - create_choice / resolve_choice / list_choices
  - generate_lore / get_lore / list_lore / search_lore
  - weave_quest_narrative / get_quest_narrative / list_quest_narratives
  - generate_story_summary / get_narrative_state
  - tick / set_config / get_config / list_events / get_stats
  - get_status / get_snapshot / reset
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_STORY_ARCS: int = 500
_MAX_PLOT_THREADS: int = 2000
_MAX_CHARACTERS: int = 1000
_MAX_NARRATIVE_BEATS: int = 10000
_MAX_CHOICES: int = 5000
_MAX_LORE_ENTRIES: int = 3000
_MAX_QUEST_NARRATIVES: int = 1000
_MAX_EVENTS: int = 10000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "__dataclass_fields__"):
                result[k] = _dataclass_to_dict(v)
            elif hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NarrativeGenre(str, Enum):
    """Story genre classification."""
    EPIC = "epic"
    HEROIC = "heroic"
    MYSTERY = "mystery"
    TRAGEDY = "tragedy"
    COMEDY = "comedy"
    ROMANCE = "romance"
    HORROR = "horror"
    ADVENTURE = "adventure"
    POLITICAL = "political"
    COMING_OF_AGE = "coming_of_age"
    REDEMPTION = "redemption"
    REVENGE = "revenge"


class StoryArcStatus(str, Enum):
    """Lifecycle status of a story arc."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    CLIMAX = "climax"
    RESOLVED = "resolved"
    ABORTED = "aborted"


class PlotThreadStatus(str, Enum):
    """Status of a plot thread within a story arc."""
    DORMANT = "dormant"
    INTRODUCED = "introduced"
    DEVELOPING = "developing"
    CLIMAXING = "climaxing"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"


class CharacterRole(str, Enum):
    """Narrative role of a character."""
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    DEUTERAGONIST = "deuteragonist"
    MENTOR = "mentor"
    ALLY = "ally"
    RIVAL = "rival"
    GUARDIAN = "guardian"
    TRICKSTER = "trickster"
    HERALD = "herald"
    SHAPESHIFTER = "shapeshifter"
    SHADOW = "shadow"
    SUPPORTING = "supporting"


class NarrativeBeatType(str, Enum):
    """Types of narrative beats."""
    INCITING_INCIDENT = "inciting_incident"
    RISING_ACTION = "rising_action"
    COMPLICATION = "complication"
    TURNING_POINT = "turning_point"
    MIDPOINT = "midpoint"
    CRISIS = "crisis"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"
    TWIST = "twist"
    REVELATION = "revelation"
    FORESHADOW = "foreshadow"
    CALLBACK = "callback"
    CHARACTER_MOMENT = "character_moment"
    WORLD_EVENT = "world_event"


class ChoiceConsequence(str, Enum):
    """Classification of choice consequences."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"
    CATALYST = "catalyst"
    IRREVERSIBLE = "irreversible"


class LoreCategory(str, Enum):
    """Categories of world lore."""
    HISTORY = "history"
    GEOGRAPHY = "geography"
    CULTURE = "culture"
    RELIGION = "religion"
    MAGIC_SYSTEM = "magic_system"
    POLITICS = "politics"
    ECONOMY = "economy"
    MYTHOLOGY = "mythology"
    BESTIARY = "bestiary"
    ARTIFACT = "artifact"
    LANGUAGE = "language"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class StoryArc:
    """A complete story arc with beginning, middle, and end."""
    arc_id: str
    title: str
    description: str = ""
    genre: str = NarrativeGenre.ADVENTURE.value
    status: str = StoryArcStatus.DRAFT.value
    theme: str = ""
    central_conflict: str = ""
    premise: str = ""
    protagonist_ids: List[str] = field(default_factory=list)
    antagonist_ids: List[str] = field(default_factory=list)
    supporting_character_ids: List[str] = field(default_factory=list)
    plot_thread_ids: List[str] = field(default_factory=list)
    beat_ids: List[str] = field(default_factory=list)
    lore_entry_ids: List[str] = field(default_factory=list)
    quest_narrative_ids: List[str] = field(default_factory=list)
    current_act: int = 1
    total_acts: int = 3
    tension_level: float = 0.3
    stakes_level: float = 0.3
    player_involvement: float = 0.5
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    resolved_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlotThread:
    """A thread of plot within a story arc."""
    thread_id: str
    arc_id: str
    title: str
    description: str = ""
    status: str = PlotThreadStatus.DORMANT.value
    thread_type: str = ""
    involved_character_ids: List[str] = field(default_factory=list)
    related_thread_ids: List[str] = field(default_factory=list)
    key_events: List[str] = field(default_factory=list)
    resolution_condition: str = ""
    tension_contribution: float = 0.2
    priority: int = 1
    introduced_at_beat: str = ""
    resolved_at_beat: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NarrativeCharacter:
    """A character within the narrative system."""
    character_id: str
    name: str
    role: str = CharacterRole.SUPPORTING.value
    description: str = ""
    personality: str = ""
    motivation: str = ""
    backstory: str = ""
    arc_summary: str = ""
    current_arc_phase: str = ""
    relationships: Dict[str, str] = field(default_factory=dict)
    arc_ids: List[str] = field(default_factory=list)
    appearance: str = ""
    speech_pattern: str = ""
    values: List[str] = field(default_factory=list)
    flaws: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)
    is_player: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NarrativeBeat:
    """A single beat in the narrative rhythm."""
    beat_id: str
    arc_id: str
    title: str
    beat_type: str = NarrativeBeatType.RISING_ACTION.value
    description: str = ""
    involved_character_ids: List[str] = field(default_factory=list)
    thread_ids: List[str] = field(default_factory=list)
    location: str = ""
    emotional_tone: str = ""
    tension_delta: float = 0.0
    stakes_delta: float = 0.0
    choices_offered: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    lore_referenced: List[str] = field(default_factory=list)
    act_number: int = 1
    sequence_order: int = 0
    is_key_moment: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BranchingChoice:
    """A branching choice presented to the player."""
    choice_id: str
    arc_id: str
    beat_id: str
    prompt: str
    description: str = ""
    options: List[Dict[str, Any]] = field(default_factory=list)
    selected_option_index: int = -1
    consequence_type: str = ChoiceConsequence.NEUTRAL.value
    consequences: List[str] = field(default_factory=list)
    affected_character_ids: List[str] = field(default_factory=list)
    affected_thread_ids: List[str] = field(default_factory=list)
    unlocks_thread_ids: List[str] = field(default_factory=list)
    locks_thread_ids: List[str] = field(default_factory=list)
    tension_impact: float = 0.0
    is_resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    resolved_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WorldLoreEntry:
    """An entry in the world lore database."""
    lore_id: str
    title: str
    category: str = LoreCategory.HISTORY.value
    content: str = ""
    summary: str = ""
    tags: List[str] = field(default_factory=list)
    related_lore_ids: List[str] = field(default_factory=list)
    referenced_by_arcs: List[str] = field(default_factory=list)
    referenced_by_beats: List[str] = field(default_factory=list)
    is_canon: bool = True
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class QuestNarrative:
    """Narrative context wrapped around a quest."""
    quest_narrative_id: str
    quest_id: str
    arc_id: str = ""
    title: str = ""
    introduction: str = ""
    background: str = ""
    objectives_narrative: List[str] = field(default_factory=list)
    completion_narrative: str = ""
    failure_narrative: str = ""
    involved_character_ids: List[str] = field(default_factory=list)
    lore_entry_ids: List[str] = field(default_factory=list)
    emotional_tone: str = ""
    stakes: str = ""
    rewards_narrative: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NarrativeConfig:
    """Global tuning parameters."""
    max_story_arcs: int = 500
    max_plot_threads_per_arc: int = 20
    max_characters: int = 1000
    max_beats_per_arc: int = 100
    max_choices_per_arc: int = 50
    max_lore_entries: int = 3000
    auto_generate_beats: bool = True
    tension_decay_rate: float = 0.05
    stake_escalation_rate: float = 0.1
    enable_emergent_narrative: bool = True
    narrative_tick_interval: float = 60.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NarrativeStats:
    """Aggregate statistics."""
    total_story_arcs: int = 0
    active_story_arcs: int = 0
    resolved_story_arcs: int = 0
    total_plot_threads: int = 0
    active_plot_threads: int = 0
    total_characters: int = 0
    total_beats: int = 0
    total_choices: int = 0
    resolved_choices: int = 0
    total_lore_entries: int = 0
    total_quest_narratives: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NarrativeSnapshot:
    """Full state snapshot."""
    story_arcs: List[Dict[str, Any]] = field(default_factory=list)
    plot_threads: List[Dict[str, Any]] = field(default_factory=list)
    characters: List[Dict[str, Any]] = field(default_factory=list)
    beats: List[Dict[str, Any]] = field(default_factory=list)
    choices: List[Dict[str, Any]] = field(default_factory=list)
    lore: List[Dict[str, Any]] = field(default_factory=list)
    quest_narratives: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NarrativeEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    arc_id: str = ""
    character_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Narrative Engine
# ---------------------------------------------------------------------------

class NarrativeEngine:
    """AI-powered narrative generation engine."""

    _instance: Optional["NarrativeEngine"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._story_arcs: Dict[str, StoryArc] = {}
        self._plot_threads: Dict[str, PlotThread] = {}
        self._characters: Dict[str, NarrativeCharacter] = {}
        self._beats: Dict[str, NarrativeBeat] = {}
        self._choices: Dict[str, BranchingChoice] = {}
        self._lore: Dict[str, WorldLoreEntry] = {}
        self._quest_narratives: Dict[str, QuestNarrative] = {}
        self._events: List[NarrativeEvent] = []
        self._stats = NarrativeStats()
        self._config = NarrativeConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "NarrativeEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        with self._init_lock:
            if self._initialized:
                return

            # Seed world lore
            lore_entries = [
                ("lore_sundering", "The Great Sundering", LoreCategory.HISTORY.value,
                 "An ancient cataclysm that shattered the primordial continent into the known world. "
                 "The Sundering was caused by the Overmages' failed ritual to contain the Void, "
                 "releasing energies that reshaped land, sea, and sky. The scars of this event "
                 "still pulse with residual magic, forming the Ley Lines that crisscross the world.",
                 "Ancient cataclysm that shaped the world"),
                ("lore_veilwright", "The Veilwright Compact", LoreCategory.RELIGION.value,
                 "A sacred order founded after the Sundering to maintain the barrier between the "
                 "material world and the Void. The Compact's members swear oaths to guard the "
                 "thin places where reality frays. Their rituals reinforce the Veil, but each "
                 "casting weakens the Veilwright's own connection to the material plane.",
                 "Sacred order that guards reality's barrier"),
                ("lore_ley_lines", "The Ley Network", LoreCategory.MAGIC_SYSTEM.value,
                 "Rivers of raw magical energy flowing beneath the earth, remnants of the Sundering. "
                 "Where ley lines converge, magic is abundant and reality is pliable. These nexuses "
                 "are sites of great power and great danger, attracting spellcasters, creatures, "
                 "and cataclysms alike.",
                 "Magical energy network beneath the world"),
                ("lore_first_kingdoms", "The Five First Kingdoms", LoreCategory.POLITICS.value,
                 "The five nations founded in the aftermath of the Sundering: Aethelgard in the "
                 "north, Valdoria in the east, Marrakesh in the south, Thalor in the west, and "
                 "the free city-state of Nexus at the world's center. Each kingdom controls a "
                 "ley convergence, making them both prosperous and perpetually contested.",
                 "The five founding nations"),
                ("lore_void_creatures", "Void Entities", LoreCategory.BESTIARY.value,
                 "Beings from beyond the Veil that slip through thin places in reality. They are "
                 "not truly alive nor dead, driven by alien hungers that mortals cannot comprehend. "
                 "Void entities range from minor wisps that drain warmth to arch-entities that "
                 "can unmake cities. The Veilwright Compact hunts them relentlessly.",
                 "Creatures from beyond the Veil"),
                ("lore_star_forge", "The Star Forge", LoreCategory.ARTIFACT.value,
                 "An ancient precursor device discovered beneath Nexus. The Star Forge can shape "
                 "raw ley energy into permanent magical constructs. Its rediscovery sparked the "
                 "current age of expansion and conflict, as every kingdom vies for control of "
                 "its power. The Forge's true purpose remains unknown.",
                 "Ancient artifact of immense power"),
                ("lore_skylands", "The Floating Skylands", LoreCategory.GEOGRAPHY.value,
                 "Islands of earth suspended in the sky, held aloft by crystallized ley energy. "
                 "The Skylands are home to reclusive sky-nomads and ancient ruins inaccessible "
                 "to those without flight. Reachable only by airship or teleportation, they are "
                 "the last uncharted frontier.",
                 "Floating islands held by crystal magic"),
                ("lore_dreamweave", "The Dreamweave", LoreCategory.MAGIC_SYSTEM.value,
                 "A parallel plane of existence overlaying the material world, accessible through "
                 "dreams and deep meditation. The Dreamweave is the source of divination magic "
                 "and is inhabited by dream-spirits that sometimes cross into waking reality. "
                 "Prolonged exposure to the Dreamweave can blur the boundary between dream and life.",
                 "Dream dimension parallel to reality"),
            ]
            for lore_id, title, category, content, summary in lore_entries:
                self._lore[lore_id] = WorldLoreEntry(
                    lore_id=lore_id, title=title, category=category,
                    content=content, summary=summary,
                )

            # Seed characters
            characters = [
                ("char_lyra", "Lyra Ashbound", CharacterRole.PROTAGONIST.value,
                 "A young Veilwright apprentice who discovered she can see the Ley Lines with her "
                 "naked eye, a gift unseen in a thousand years.",
                 "Determined, compassionate, and haunted by visions of the Void breaking through. "
                 "Speaks with quiet intensity and rarely raises her voice.",
                 "To prevent a second Sundering and find her missing mentor.",
                 "Raised by the Veilwright Compact after her village was consumed by a Void breach. "
                 "Her mentor, Master Corwin, vanished while investigating the Star Forge."),
                ("char_maltheris", "Maltheris the Unbound", CharacterRole.ANTAGONIST.value,
                 "A former Veilwright who believes the Veil must be torn down, not maintained. "
                 "He seeks to merge the material world with the Void, claiming it will elevate "
                 "humanity to a new state of being.",
                 "Charismatic, brilliant, and utterly convinced of his righteousness. "
                 "He genuinely believes his plan will save the world, even as it threatens to destroy it.",
                 "To unmake the Veil and reshape reality.",
                 "Once the Compact's greatest scholar, he peered too long into the Void and saw "
                 "something that changed him. He now leads a cult of Void-worshippers."),
                ("char_corwin", "Master Corwin Veilheart", CharacterRole.MENTOR.value,
                 "Lyra's missing mentor and the Compact's foremost expert on ley line theory. "
                 "His disappearance is connected to the Star Forge.",
                 "Patient, wise, and secretly burdened by knowledge he dare not share. "
                 "He has walked the Dreamweave more deeply than any living mortal.",
                 "To protect the world from the truth he discovered beneath Nexus.",
                 "Corwin found something in the Star Forge that terrified him. He went into "
                 "hiding to prevent the knowledge from being used."),
                ("char_kael", "Kael Stormrider", CharacterRole.DEUTERAGONIST.value,
                 "A sky-nomad pilot whose airship was shot down over Aethelgard. He joins Lyra's "
                 "quest seeking passage home but discovers a deeper purpose.",
                 "Reckless, loyal, and quick to laugh. He masks deep grief over his fallen clan "
                 "with bravado and humor.",
                 "To find a new home for his scattered people.",
                 "The last pilot of the Stormrider clan, whose skyland was destroyed by a Void entity. "
                 "He carries the clan's last sky-crystal as a keepsake."),
                ("char_seren", "Seren Nightwhisper", CharacterRole.ALLY.value,
                 "A Dreamweave walker who can manifest dream-spirits into reality. She speaks in "
                 "riddles and sees futures that may never come to pass.",
                 "Ethereal, cryptic, and deeply empathetic. She struggles to distinguish her own "
                 "emotions from those of the dream-spirits she channels.",
                 "To find a stable boundary between dream and reality.",
                 "Born with the ability to walk the Dreamweave awake, Seren was feared by her "
                 "village and taken in by the Compact."),
                ("char_thane", "Thane Ironheart", CharacterRole.RIVAL.value,
                 "A Valdorian knight tasked with securing the Star Forge for his kingdom. "
                 "He and Lyra share the same goal but opposing methods.",
                 "Honorable, rigid, and secretly doubting his kingdom's cause. He believes order "
                 "must be maintained at any cost.",
                 "To fulfill his oath and bring honor to his family name.",
                 "Third son of a minor noble house, Thane earned his knighthood through valor "
                 "in the border wars. He sees the Star Forge as his chance for greatness."),
            ]
            for char_id, name, role, desc, personality, motivation, backstory in characters:
                self._characters[char_id] = NarrativeCharacter(
                    character_id=char_id, name=name, role=role,
                    description=desc, personality=personality,
                    motivation=motivation, backstory=backstory,
                    arc_summary="", current_arc_phase="introduction",
                )

            # Set up initial relationships
            self._characters["char_lyra"].relationships = {
                "char_corwin": "mentor",
                "char_maltheris": "enemy",
                "char_kael": "ally",
                "char_seren": "friend",
                "char_thane": "rival",
            }
            self._characters["char_maltheris"].relationships = {
                "char_lyra": "enemy",
                "char_corwin": "former_colleague",
            }

            # Seed the main story arc
            arc = StoryArc(
                arc_id="arc_veilbreaker",
                title="The Veilbreaker Saga",
                description="A sweeping epic about a young Veilwright who must prevent a second "
                            "Sundering while uncovering the truth behind the Star Forge.",
                genre=NarrativeGenre.EPIC.value,
                status=StoryArcStatus.ACTIVE.value,
                theme="The cost of knowledge and the courage to bear it",
                central_conflict="Lyra must stop Maltheris from tearing the Veil while discovering "
                                 "the terrifying truth her mentor hid from the world.",
                premise="When a young Veilwright apprentice discovers she can see Ley Lines, she is "
                        "drawn into a conflict that will determine the fate of reality itself.",
                protagonist_ids=["char_lyra"],
                antagonist_ids=["char_maltheris"],
                supporting_character_ids=["char_corwin", "char_kael", "char_seren", "char_thane"],
                lore_entry_ids=["lore_sundering", "lore_veilwright", "lore_ley_lines",
                                "lore_star_forge", "lore_void_creatures"],
                current_act=1,
                total_acts=3,
                tension_level=0.4,
                stakes_level=0.5,
                player_involvement=0.6,
                tags=["epic", "void", "ley_lines", "veilwright"],
            )
            self._story_arcs[arc.arc_id] = arc

            for char_id in ["char_lyra", "char_corwin", "char_maltheris"]:
                if char_id in self._characters:
                    self._characters[char_id].arc_ids.append(arc.arc_id)

            # Seed plot threads
            threads = [
                ("thread_mentor_search", arc.arc_id, "The Missing Mentor",
                 "Lyra searches for Master Corwin, uncovering clues that lead to the Star Forge.",
                 PlotThreadStatus.DEVELOPING.value, "investigation",
                 ["char_lyra", "char_corwin"], 0.3, 2),
                ("thread_void_cult", arc.arc_id, "The Void Cult Rising",
                 "Maltheris's cult grows in power, conducting rituals that weaken the Veil.",
                 PlotThreadStatus.DEVELOPING.value, "antagonist",
                 ["char_maltheris", "char_lyra"], 0.4, 3),
                ("thread_star_forge_secret", arc.arc_id, "The Star Forge's True Purpose",
                 "The Star Forge is not a tool but a prison, containing something that must never be freed.",
                 PlotThreadStatus.INTRODUCED.value, "mystery",
                 ["char_corwin", "char_lyra"], 0.2, 2),
                ("thread_skyland_refugees", arc.arc_id, "The Fallen Sky",
                 "Kael's people search for a new home as Void entities hunt the scattered sky-nomads.",
                 PlotThreadStatus.INTRODUCED.value, "side",
                 ["char_kael"], 0.15, 1),
                ("thread_dreamweave_thinning", arc.arc_id, "The Dreaming Veil",
                 "The boundary between the Dreamweave and reality is thinning, causing dream-spirits to cross over.",
                 PlotThreadStatus.DORMANT.value, "mystery",
                 ["char_seren"], 0.1, 1),
            ]
            for tid, aid, title, desc, status, ttype, chars, tension, priority in threads:
                self._plot_threads[tid] = PlotThread(
                    thread_id=tid, arc_id=aid, title=title, description=desc,
                    status=status, thread_type=ttype,
                    involved_character_ids=chars,
                    tension_contribution=tension, priority=priority,
                )
                arc.plot_thread_ids.append(tid)

            # Seed narrative beats
            beats = [
                ("beat_inciting", arc.arc_id, NarrativeBeatType.INCITING_INCIDENT.value,
                 "The Vision at the Ley Convergence",
                 "Lyra sees the Ley Lines for the first time during a Veilwright ritual, "
                 "and witnesses a vision of the Veil tearing apart.",
                 ["char_lyra"], ["thread_void_cult"], "Nexus Ley Convergence",
                 "awe and dread", 0.3, 0.2, 1, 0, True),
                ("beat_call_to_adventure", arc.arc_id, NarrativeBeatType.RISING_ACTION.value,
                 "The Master's Farewell",
                 "Master Corwin leaves Lyra a cryptic message and disappears, leaving only a "
                 "fragment of a Star Forge map.",
                 ["char_lyra", "char_corwin"], ["thread_mentor_search"],
                 "Veilwright Sanctum", "concern and determination", 0.1, 0.1, 1, 1, False),
                ("beat_first_obstacle", arc.arc_id, NarrativeBeatType.COMPLICATION.value,
                 "Ambush at the Crossroads",
                 "Void cultists ambush Lyra on the road to Aethelgard, revealing the cult's "
                 "reach extends far beyond Nexus.",
                 ["char_lyra"], ["thread_void_cult"],
                 "Aethelgard Road", "danger and urgency", 0.2, 0.15, 1, 2, False),
                ("beat_ally_intro", arc.arc_id, NarrativeBeatType.CHARACTER_MOMENT.value,
                 "The Fallen Pilot",
                 "Lyra discovers Kael crashed in the highlands and helps repair his airship "
                 "in exchange for passage north.",
                 ["char_lyra", "char_kael"], ["thread_skyland_refugees"],
                 "Northern Highlands", "camaraderie", 0.05, 0.0, 1, 3, False),
                ("beat_revelation", arc.arc_id, NarrativeBeatType.REVELATION.value,
                 "The Corwin Journals",
                 "In the Aethelgard archive, Lyra finds Corwin's hidden journals revealing "
                 "his research into the Star Forge's true nature.",
                 ["char_lyra"], ["thread_mentor_search", "thread_star_forge_secret"],
                 "Aethelgard Archive", "shock and understanding", 0.15, 0.2, 1, 4, True),
            ]
            for bid, aid, btype, title, desc, chars, tids, loc, tone, tdelta, sdelta, act, seq, key in beats:
                self._beats[bid] = NarrativeBeat(
                    beat_id=bid, arc_id=aid, beat_type=btype,
                    title=title, description=desc,
                    involved_character_ids=chars, thread_ids=tids,
                    location=loc, emotional_tone=tone,
                    tension_delta=tdelta, stakes_delta=sdelta,
                    act_number=act, sequence_order=seq, is_key_moment=key,
                )
                arc.beat_ids.append(bid)

            # Seed a branching choice
            choice = BranchingChoice(
                choice_id="choice_journals", arc_id=arc.arc_id, beat_id="beat_revelation",
                prompt="What does Lyra do with Corwin's journals?",
                description="The journals reveal the Star Forge is a prison. Lyra must decide "
                            "how to use this explosive knowledge.",
                options=[
                    {"label": "Share with the Veilwright Compact", "consequence": "trust",
                     "description": "Inform the Compact leadership, gaining allies but risking the secret spreading."},
                    {"label": "Keep them secret", "consequence": "burden",
                     "description": "Hide the journals, protecting the secret but bearing it alone."},
                    {"label": "Confront Maltheris", "consequence": "confrontation",
                     "description": "Use the knowledge to challenge Maltheris directly, risking everything."},
                ],
                consequence_type=ChoiceConsequence.CATALYST.value,
                affected_character_ids=["char_lyra", "char_corwin", "char_maltheris"],
                affected_thread_ids=["thread_star_forge_secret", "thread_mentor_search"],
                tension_impact=0.2,
            )
            self._choices[choice.choice_id] = choice

            # Seed a quest narrative
            qnarr = QuestNarrative(
                quest_narrative_id="qnarr_find_corwin",
                quest_id="quest_find_corwin",
                arc_id=arc.arc_id,
                title="In the Mentor's Footsteps",
                introduction="Lyra stands in the empty sanctum, reading Corwin's farewell message "
                             "for the third time. The map fragment trembles in her hands.",
                background="Master Corwin Veilheart, the Compact's foremost ley scholar, vanished "
                           "three days ago. His last communication was a cryptic note and a fragment "
                           "of a map pointing toward the Star Forge beneath Nexus.",
                objectives_narrative=[
                    "Search Corwin's sanctum for clues to his disappearance",
                    "Follow the map fragment to the Aethelgard archive",
                    "Decipher Corwin's encrypted journals",
                    "Find the hidden entrance Corwin described",
                ],
                completion_narrative="The journals lay open before Lyra, their terrible truth "
                                     "illuminated by candlelight. The Star Forge is not a tool. "
                                     "It never was.",
                failure_narrative="The archive burns behind Lyra as she flees empty-handed. "
                                  "Whatever Corwin hid here is lost to the flames, and with it, "
                                  "her last hope of finding him.",
                involved_character_ids=["char_lyra", "char_corwin"],
                lore_entry_ids=["lore_star_forge", "lore_veilwright"],
                emotional_tone="determination tinged with dread",
                stakes="If Lyra cannot find Corwin, she will face the Void cult alone.",
                rewards_narrative="Corwin's journals, a map to the Star Forge, and a truth "
                                  "that changes everything.",
            )
            self._quest_narratives[qnarr.quest_narrative_id] = qnarr
            arc.quest_narrative_ids.append(qnarr.quest_narrative_id)

            # Update stats
            self._stats.total_story_arcs = len(self._story_arcs)
            self._stats.active_story_arcs = sum(
                1 for a in self._story_arcs.values() if a.status == StoryArcStatus.ACTIVE.value
            )
            self._stats.total_plot_threads = len(self._plot_threads)
            self._stats.active_plot_threads = sum(
                1 for t in self._plot_threads.values()
                if t.status in (PlotThreadStatus.DEVELOPING.value, PlotThreadStatus.CLIMAXING.value)
            )
            self._stats.total_characters = len(self._characters)
            self._stats.total_beats = len(self._beats)
            self._stats.total_choices = len(self._choices)
            self._stats.total_lore_entries = len(self._lore)
            self._stats.total_quest_narratives = len(self._quest_narratives)

            self._initialized = True

    def _emit(self, kind: str, **kwargs: Any) -> None:
        self._event_counter += 1
        event = NarrativeEvent(
            event_id=f"nevt_{self._event_counter:08d}",
            kind=kind, timestamp=_now(), **kwargs,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Story Arc Management
    # ------------------------------------------------------------------

    def create_story_arc(
        self, title: str, description: str = "", genre: str = NarrativeGenre.ADVENTURE.value,
        theme: str = "", central_conflict: str = "", premise: str = "",
        total_acts: int = 3, tags: List[str] = None,
    ) -> Tuple[bool, str, Optional[StoryArc]]:
        with _LOCK:
            if len(self._story_arcs) >= _MAX_STORY_ARCS:
                return False, "capacity_reached", None
            arc_id = _new_id("arc")
            arc = StoryArc(
                arc_id=arc_id, title=title, description=description,
                genre=genre, theme=theme, central_conflict=central_conflict,
                premise=premise, total_acts=max(1, total_acts),
                tags=tags or [],
            )
            self._story_arcs[arc_id] = arc
            self._stats.total_story_arcs = len(self._story_arcs)
            self._stats.active_story_arcs += 1
            self._emit("arc_created", arc_id=arc_id, description=title)
            return True, "created", arc

    def get_story_arc(self, arc_id: str) -> Optional[StoryArc]:
        return self._story_arcs.get(arc_id)

    def list_story_arcs(self, status: str = "", genre: str = "") -> List[StoryArc]:
        results = list(self._story_arcs.values())
        if status:
            results = [a for a in results if a.status == status]
        if genre:
            results = [a for a in results if a.genre == genre]
        return results

    def remove_story_arc(self, arc_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if arc_id not in self._story_arcs:
                return False, "not_found"
            arc = self._story_arcs.pop(arc_id)
            for tid in arc.plot_thread_ids:
                self._plot_threads.pop(tid, None)
            for bid in arc.beat_ids:
                self._beats.pop(bid, None)
            for cid in arc.quest_narrative_ids:
                self._quest_narratives.pop(cid, None)
            for cid, choice in list(self._choices.items()):
                if choice.arc_id == arc_id:
                    self._choices.pop(cid, None)
            self._stats.total_story_arcs = len(self._story_arcs)
            self._emit("arc_removed", arc_id=arc_id)
            return True, "removed"

    def advance_story_arc(self, arc_id: str) -> Tuple[bool, str, Optional[StoryArc]]:
        with _LOCK:
            arc = self._story_arcs.get(arc_id)
            if not arc:
                return False, "not_found", None
            if arc.status in (StoryArcStatus.RESOLVED.value, StoryArcStatus.ABORTED.value):
                return False, "already_finished", arc

            transitions = {
                StoryArcStatus.DRAFT.value: StoryArcStatus.ACTIVE,
                StoryArcStatus.ACTIVE.value: StoryArcStatus.CLIMAX,
                StoryArcStatus.PAUSED.value: StoryArcStatus.ACTIVE,
                StoryArcStatus.CLIMAX.value: StoryArcStatus.RESOLVED,
            }
            new_status = transitions.get(arc.status)
            if not new_status:
                return False, "no_transition", arc

            arc.status = new_status.value
            arc.updated_at = _now()
            if new_status == StoryArcStatus.RESOLVED:
                arc.resolved_at = _now()
                self._stats.active_story_arcs = max(0, self._stats.active_story_arcs - 1)
                self._stats.resolved_story_arcs += 1

            if new_status == StoryArcStatus.CLIMAX:
                arc.tension_level = _clamp(arc.tension_level + 0.3, 0.0, 1.0)
                arc.stakes_level = _clamp(arc.stakes_level + 0.2, 0.0, 1.0)
                arc.current_act = arc.total_acts

            self._emit("arc_advanced", arc_id=arc_id, description=new_status.value)
            return True, "advanced", arc

    def complete_story_arc(self, arc_id: str, resolution: str = "") -> Tuple[bool, str, Optional[StoryArc]]:
        with _LOCK:
            arc = self._story_arcs.get(arc_id)
            if not arc:
                return False, "not_found", None
            arc.status = StoryArcStatus.RESOLVED.value
            arc.resolved_at = _now()
            arc.updated_at = _now()
            if resolution:
                arc.metadata["resolution"] = resolution
            for tid in arc.plot_thread_ids:
                thread = self._plot_threads.get(tid)
                if thread and thread.status not in (PlotThreadStatus.RESOLVED.value, PlotThreadStatus.ABANDONED.value):
                    thread.status = PlotThreadStatus.RESOLVED.value
                    thread.updated_at = _now()
            self._stats.active_story_arcs = max(0, self._stats.active_story_arcs - 1)
            self._stats.resolved_story_arcs += 1
            self._emit("arc_completed", arc_id=arc_id, description=resolution)
            return True, "resolved", arc

    def abort_story_arc(self, arc_id: str, reason: str = "") -> Tuple[bool, str, Optional[StoryArc]]:
        with _LOCK:
            arc = self._story_arcs.get(arc_id)
            if not arc:
                return False, "not_found", None
            arc.status = StoryArcStatus.ABORTED.value
            arc.updated_at = _now()
            if reason:
                arc.metadata["abort_reason"] = reason
            self._stats.active_story_arcs = max(0, self._stats.active_story_arcs - 1)
            self._emit("arc_aborted", arc_id=arc_id, description=reason)
            return True, "aborted", arc

    # ------------------------------------------------------------------
    # Character Management
    # ------------------------------------------------------------------

    def register_character(
        self, character_id: str, name: str, role: str = CharacterRole.SUPPORTING.value,
        description: str = "", personality: str = "", motivation: str = "",
        backstory: str = "", is_player: bool = False,
    ) -> Tuple[bool, str, Optional[NarrativeCharacter]]:
        with _LOCK:
            if character_id in self._characters:
                return False, "already_exists", None
            if len(self._characters) >= _MAX_CHARACTERS:
                return False, "capacity_reached", None
            char = NarrativeCharacter(
                character_id=character_id, name=name, role=role,
                description=description, personality=personality,
                motivation=motivation, backstory=backstory, is_player=is_player,
            )
            self._characters[character_id] = char
            self._stats.total_characters = len(self._characters)
            self._emit("character_registered", character_id=character_id, description=name)
            return True, "registered", char

    def get_character(self, character_id: str) -> Optional[NarrativeCharacter]:
        return self._characters.get(character_id)

    def list_characters(self, role: str = "", arc_id: str = "") -> List[NarrativeCharacter]:
        results = list(self._characters.values())
        if role:
            results = [c for c in results if c.role == role]
        if arc_id:
            results = [c for c in results if arc_id in c.arc_ids]
        return results

    def remove_character(self, character_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if character_id not in self._characters:
                return False, "not_found"
            self._characters.pop(character_id)
            self._stats.total_characters = len(self._characters)
            self._emit("character_removed", character_id=character_id)
            return True, "removed"

    def advance_character_arc(
        self, character_id: str, new_phase: str = "", arc_summary: str = "",
    ) -> Tuple[bool, str, Optional[NarrativeCharacter]]:
        with _LOCK:
            char = self._characters.get(character_id)
            if not char:
                return False, "not_found", None
            if new_phase:
                char.current_arc_phase = new_phase
            if arc_summary:
                char.arc_summary = arc_summary
            char.updated_at = _now()
            self._emit("character_arc_advanced", character_id=character_id, description=new_phase)
            return True, "advanced", char

    def update_character_relationship(
        self, character_id: str, other_character_id: str, relationship: str,
    ) -> Tuple[bool, str, Optional[NarrativeCharacter]]:
        with _LOCK:
            char = self._characters.get(character_id)
            if not char:
                return False, "not_found", None
            char.relationships[other_character_id] = relationship
            char.updated_at = _now()
            self._emit("character_relationship_updated", character_id=character_id,
                       description=f"{other_character_id}: {relationship}")
            return True, "updated", char

    # ------------------------------------------------------------------
    # Plot Thread Management
    # ------------------------------------------------------------------

    def create_plot_thread(
        self, arc_id: str, title: str, description: str = "",
        thread_type: str = "", involved_character_ids: List[str] = None,
        tension_contribution: float = 0.2, priority: int = 1,
        resolution_condition: str = "",
    ) -> Tuple[bool, str, Optional[PlotThread]]:
        with _LOCK:
            arc = self._story_arcs.get(arc_id)
            if not arc:
                return False, "arc_not_found", None
            if len(self._plot_threads) >= _MAX_PLOT_THREADS:
                return False, "capacity_reached", None
            thread_id = _new_id("thread")
            thread = PlotThread(
                thread_id=thread_id, arc_id=arc_id, title=title,
                description=description, thread_type=thread_type,
                involved_character_ids=involved_character_ids or [],
                tension_contribution=_clamp(tension_contribution, 0.0, 1.0),
                priority=max(1, priority),
                resolution_condition=resolution_condition,
            )
            self._plot_threads[thread_id] = thread
            arc.plot_thread_ids.append(thread_id)
            self._stats.total_plot_threads = len(self._plot_threads)
            self._stats.active_plot_threads += 1
            self._emit("thread_created", arc_id=arc_id, description=title)
            return True, "created", thread

    def get_plot_thread(self, thread_id: str) -> Optional[PlotThread]:
        return self._plot_threads.get(thread_id)

    def list_plot_threads(self, arc_id: str = "", status: str = "") -> List[PlotThread]:
        results = list(self._plot_threads.values())
        if arc_id:
            results = [t for t in results if t.arc_id == arc_id]
        if status:
            results = [t for t in results if t.status == status]
        return sorted(results, key=lambda t: -t.priority)

    def resolve_plot_thread(self, thread_id: str, resolution: str = "") -> Tuple[bool, str, Optional[PlotThread]]:
        with _LOCK:
            thread = self._plot_threads.get(thread_id)
            if not thread:
                return False, "not_found", None
            thread.status = PlotThreadStatus.RESOLVED.value
            thread.updated_at = _now()
            if resolution:
                thread.metadata["resolution"] = resolution
            self._stats.active_plot_threads = max(0, self._stats.active_plot_threads - 1)
            self._emit("thread_resolved", arc_id=thread.arc_id, description=thread.title)
            return True, "resolved", thread

    # ------------------------------------------------------------------
    # Narrative Beat Management
    # ------------------------------------------------------------------

    def add_narrative_beat(
        self, arc_id: str, beat_type: str = NarrativeBeatType.RISING_ACTION.value,
        title: str = "", description: str = "",
        involved_character_ids: List[str] = None, thread_ids: List[str] = None,
        location: str = "", emotional_tone: str = "",
        tension_delta: float = 0.0, stakes_delta: float = 0.0,
        act_number: int = 1, is_key_moment: bool = False,
    ) -> Tuple[bool, str, Optional[NarrativeBeat]]:
        with _LOCK:
            arc = self._story_arcs.get(arc_id)
            if not arc:
                return False, "arc_not_found", None
            if len(self._beats) >= _MAX_NARRATIVE_BEATS:
                return False, "capacity_reached", None
            beat_id = _new_id("beat")
            beat = NarrativeBeat(
                beat_id=beat_id, arc_id=arc_id, beat_type=beat_type,
                title=title, description=description,
                involved_character_ids=involved_character_ids or [],
                thread_ids=thread_ids or [],
                location=location, emotional_tone=emotional_tone,
                tension_delta=tension_delta, stakes_delta=stakes_delta,
                act_number=max(1, act_number),
                sequence_order=len(arc.beat_ids),
                is_key_moment=is_key_moment,
            )
            self._beats[beat_id] = beat
            arc.beat_ids.append(beat_id)
            arc.tension_level = _clamp(arc.tension_level + tension_delta, 0.0, 1.0)
            arc.stakes_level = _clamp(arc.stakes_level + stakes_delta, 0.0, 1.0)
            arc.updated_at = _now()
            self._stats.total_beats = len(self._beats)
            self._emit("beat_added", arc_id=arc_id, description=title)
            return True, "added", beat

    def get_narrative_beat(self, beat_id: str) -> Optional[NarrativeBeat]:
        return self._beats.get(beat_id)

    def list_narrative_beats(self, arc_id: str = "", beat_type: str = "") -> List[NarrativeBeat]:
        results = list(self._beats.values())
        if arc_id:
            results = [b for b in results if b.arc_id == arc_id]
        if beat_type:
            results = [b for b in results if b.beat_type == beat_type]
        return sorted(results, key=lambda b: b.sequence_order)

    # ------------------------------------------------------------------
    # Branching Choice Management
    # ------------------------------------------------------------------

    def create_choice(
        self, arc_id: str, beat_id: str, prompt: str,
        description: str = "", options: List[Dict[str, Any]] = None,
        consequence_type: str = ChoiceConsequence.NEUTRAL.value,
        affected_character_ids: List[str] = None,
        affected_thread_ids: List[str] = None,
        tension_impact: float = 0.0,
    ) -> Tuple[bool, str, Optional[BranchingChoice]]:
        with _LOCK:
            if arc_id not in self._story_arcs:
                return False, "arc_not_found", None
            if len(self._choices) >= _MAX_CHOICES:
                return False, "capacity_reached", None
            choice_id = _new_id("choice")
            choice = BranchingChoice(
                choice_id=choice_id, arc_id=arc_id, beat_id=beat_id,
                prompt=prompt, description=description,
                options=options or [],
                consequence_type=consequence_type,
                affected_character_ids=affected_character_ids or [],
                affected_thread_ids=affected_thread_ids or [],
                tension_impact=_clamp(tension_impact, -1.0, 1.0),
            )
            self._choices[choice_id] = choice
            beat = self._beats.get(beat_id)
            if beat:
                beat.choices_offered.append(choice_id)
            self._stats.total_choices = len(self._choices)
            self._emit("choice_created", arc_id=arc_id, description=prompt)
            return True, "created", choice

    def resolve_choice(
        self, choice_id: str, selected_option_index: int,
    ) -> Tuple[bool, str, Optional[BranchingChoice]]:
        with _LOCK:
            choice = self._choices.get(choice_id)
            if not choice:
                return False, "not_found", None
            if choice.is_resolved:
                return False, "already_resolved", choice
            if selected_option_index < 0 or selected_option_index >= len(choice.options):
                return False, "invalid_option", choice
            choice.selected_option_index = selected_option_index
            choice.is_resolved = True
            choice.resolved_at = _now()
            arc = self._story_arcs.get(choice.arc_id)
            if arc:
                arc.tension_level = _clamp(arc.tension_level + choice.tension_impact, 0.0, 1.0)
            self._stats.resolved_choices += 1
            option_label = choice.options[selected_option_index].get("label", "")
            self._emit("choice_resolved", arc_id=choice.arc_id, description=option_label)
            return True, "resolved", choice

    def list_choices(self, arc_id: str = "", resolved: Optional[bool] = None) -> List[BranchingChoice]:
        results = list(self._choices.values())
        if arc_id:
            results = [c for c in results if c.arc_id == arc_id]
        if resolved is not None:
            results = [c for c in results if c.is_resolved == resolved]
        return results

    # ------------------------------------------------------------------
    # World Lore Management
    # ------------------------------------------------------------------

    def generate_lore(
        self, title: str, category: str = LoreCategory.HISTORY.value,
        content: str = "", summary: str = "", tags: List[str] = None,
        is_canon: bool = True, confidence: float = 1.0,
    ) -> Tuple[bool, str, Optional[WorldLoreEntry]]:
        with _LOCK:
            if len(self._lore) >= _MAX_LORE_ENTRIES:
                return False, "capacity_reached", None
            lore_id = _new_id("lore")
            entry = WorldLoreEntry(
                lore_id=lore_id, title=title, category=category,
                content=content, summary=summary or content[:200] if content else "",
                tags=tags or [], is_canon=is_canon,
                confidence=_clamp(confidence, 0.0, 1.0),
            )
            self._lore[lore_id] = entry
            self._stats.total_lore_entries = len(self._lore)
            self._emit("lore_generated", description=title)
            return True, "generated", entry

    def get_lore(self, lore_id: str) -> Optional[WorldLoreEntry]:
        return self._lore.get(lore_id)

    def list_lore(self, category: str = "", is_canon: Optional[bool] = None) -> List[WorldLoreEntry]:
        results = list(self._lore.values())
        if category:
            results = [l for l in results if l.category == category]
        if is_canon is not None:
            results = [l for l in results if l.is_canon == is_canon]
        return results

    def search_lore(self, query: str) -> List[WorldLoreEntry]:
        query_lower = query.lower()
        results = []
        for entry in self._lore.values():
            if (query_lower in entry.title.lower() or
                query_lower in entry.content.lower() or
                query_lower in entry.summary.lower() or
                any(query_lower in tag.lower() for tag in entry.tags)):
                results.append(entry)
        return results

    # ------------------------------------------------------------------
    # Quest Narrative Management
    # ------------------------------------------------------------------

    def weave_quest_narrative(
        self, quest_id: str, arc_id: str = "", title: str = "",
        introduction: str = "", background: str = "",
        objectives_narrative: List[str] = None,
        completion_narrative: str = "", failure_narrative: str = "",
        involved_character_ids: List[str] = None,
        lore_entry_ids: List[str] = None,
        emotional_tone: str = "", stakes: str = "",
        rewards_narrative: str = "",
    ) -> Tuple[bool, str, Optional[QuestNarrative]]:
        with _LOCK:
            if len(self._quest_narratives) >= _MAX_QUEST_NARRATIVES:
                return False, "capacity_reached", None
            qnarr_id = _new_id("qnarr")
            qnarr = QuestNarrative(
                quest_narrative_id=qnarr_id, quest_id=quest_id, arc_id=arc_id,
                title=title, introduction=introduction, background=background,
                objectives_narrative=objectives_narrative or [],
                completion_narrative=completion_narrative,
                failure_narrative=failure_narrative,
                involved_character_ids=involved_character_ids or [],
                lore_entry_ids=lore_entry_ids or [],
                emotional_tone=emotional_tone, stakes=stakes,
                rewards_narrative=rewards_narrative,
            )
            self._quest_narratives[qnarr_id] = qnarr
            if arc_id:
                arc = self._story_arcs.get(arc_id)
                if arc:
                    arc.quest_narrative_ids.append(qnarr_id)
            self._stats.total_quest_narratives = len(self._quest_narratives)
            self._emit("quest_narrative_woven", arc_id=arc_id, description=title)
            return True, "woven", qnarr

    def get_quest_narrative(self, quest_narrative_id: str) -> Optional[QuestNarrative]:
        return self._quest_narratives.get(quest_narrative_id)

    def list_quest_narratives(self, arc_id: str = "") -> List[QuestNarrative]:
        results = list(self._quest_narratives.values())
        if arc_id:
            results = [q for q in results if q.arc_id == arc_id]
        return results

    # ------------------------------------------------------------------
    # Narrative Summary & State
    # ------------------------------------------------------------------

    def generate_story_summary(self, arc_id: str) -> Tuple[bool, str, str]:
        arc = self._story_arcs.get(arc_id)
        if not arc:
            return False, "not_found", ""
        beats = self.list_narrative_beats(arc_id)
        threads = self.list_plot_threads(arc_id)
        characters = [self._characters[cid] for cid in arc.protagonist_ids + arc.supporting_character_ids
                      if cid in self._characters]

        parts = [f"Story: {arc.title}", f"Genre: {arc.genre}", f"Status: {arc.status}", ""]
        if arc.premise:
            parts.append(f"Premise: {arc.premise}")
        if arc.central_conflict:
            parts.append(f"Central Conflict: {arc.central_conflict}")
        parts.append("")

        parts.append(f"Characters ({len(characters)}):")
        for char in characters[:5]:
            parts.append(f"  - {char.name} ({char.role}): {char.motivation}")

        parts.append("")
        parts.append(f"Plot Threads ({len(threads)}):")
        for thread in threads[:5]:
            parts.append(f"  - [{thread.status}] {thread.title}")

        parts.append("")
        parts.append(f"Narrative Beats ({len(beats)}):")
        for beat in beats[:5]:
            parts.append(f"  - Act {beat.act_number}: {beat.title}")

        parts.append("")
        parts.append(f"Tension: {arc.tension_level:.2f} | Stakes: {arc.stakes_level:.2f} | "
                     f"Act: {arc.current_act}/{arc.total_acts}")

        summary = "\n".join(parts)
        return True, "generated", summary

    def get_narrative_state(self, arc_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        arc = self._story_arcs.get(arc_id)
        if not arc:
            return False, "not_found", {}
        beats = self.list_narrative_beats(arc_id)
        threads = self.list_plot_threads(arc_id)
        unresolved_choices = self.list_choices(arc_id, resolved=False)
        state = {
            "arc_id": arc_id,
            "title": arc.title,
            "status": arc.status,
            "current_act": arc.current_act,
            "total_acts": arc.total_acts,
            "tension_level": arc.tension_level,
            "stakes_level": arc.stakes_level,
            "player_involvement": arc.player_involvement,
            "total_beats": len(beats),
            "total_threads": len(threads),
            "active_threads": sum(1 for t in threads if t.status in (
                PlotThreadStatus.DEVELOPING.value, PlotThreadStatus.CLIMAXING.value)),
            "unresolved_choices": len(unresolved_choices),
            "last_beat": beats[-1].title if beats else "",
        }
        return True, "ok", state

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            self._stats.tick_count = self._tick_count

            results: Dict[str, Any] = {
                "tick_count": self._tick_count,
                "arcs_processed": 0,
                "threads_advanced": 0,
                "beats_generated": 0,
                "tension_adjustments": 0,
            }

            if self._config.auto_generate_beats:
                for arc in self._story_arcs.values():
                    if arc.status != StoryArcStatus.ACTIVE.value:
                        continue
                    results["arcs_processed"] += 1

                    decay = self._config.tension_decay_rate
                    if arc.tension_level > 0.1:
                        arc.tension_level = _clamp(arc.tension_level - decay, 0.0, 1.0)
                        results["tension_adjustments"] += 1

                    for tid in arc.plot_thread_ids:
                        thread = self._plot_threads.get(tid)
                        if not thread:
                            continue
                        if thread.status == PlotThreadStatus.INTRODUCED.value:
                            thread.status = PlotThreadStatus.DEVELOPING.value
                            thread.updated_at = _now()
                            results["threads_advanced"] += 1
                        elif thread.status == PlotThreadStatus.DEVELOPING.value:
                            if arc.tension_level > 0.6:
                                thread.status = PlotThreadStatus.CLIMAXING.value
                                thread.updated_at = _now()
                                results["threads_advanced"] += 1

            self._emit("tick", description=f"tick_{self._tick_count}")
            return results

    def set_config(self, config: Dict[str, Any]) -> Tuple[bool, str, NarrativeConfig]:
        with _LOCK:
            if "max_story_arcs" in config:
                self._config.max_story_arcs = _safe_int(config["max_story_arcs"], 500)
            if "auto_generate_beats" in config:
                self._config.auto_generate_beats = bool(config["auto_generate_beats"])
            if "tension_decay_rate" in config:
                self._config.tension_decay_rate = _clamp(
                    _safe_float(config["tension_decay_rate"], 0.05), 0.0, 1.0)
            if "stake_escalation_rate" in config:
                self._config.stake_escalation_rate = _clamp(
                    _safe_float(config["stake_escalation_rate"], 0.1), 0.0, 1.0)
            if "enable_emergent_narrative" in config:
                self._config.enable_emergent_narrative = bool(config["enable_emergent_narrative"])
            if "narrative_tick_interval" in config:
                self._config.narrative_tick_interval = _safe_float(
                    config["narrative_tick_interval"], 60.0)
            self._emit("config_updated")
            return True, "updated", self._config

    def get_config(self) -> NarrativeConfig:
        return self._config

    def list_events(self, limit: int = 100) -> List[NarrativeEvent]:
        return list(reversed(self._events[-limit:]))

    def get_stats(self) -> NarrativeStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_story_arcs": len(self._story_arcs),
            "active_story_arcs": sum(
                1 for a in self._story_arcs.values()
                if a.status == StoryArcStatus.ACTIVE.value),
            "total_plot_threads": len(self._plot_threads),
            "total_characters": len(self._characters),
            "total_beats": len(self._beats),
            "total_choices": len(self._choices),
            "unresolved_choices": sum(1 for c in self._choices.values() if not c.is_resolved),
            "total_lore_entries": len(self._lore),
            "total_quest_narratives": len(self._quest_narratives),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> NarrativeSnapshot:
        return NarrativeSnapshot(
            story_arcs=[a.to_dict() for a in list(self._story_arcs.values())[:20]],
            plot_threads=[t.to_dict() for t in list(self._plot_threads.values())[:30]],
            characters=[c.to_dict() for c in list(self._characters.values())[:20]],
            beats=[b.to_dict() for b in list(self._beats.values())[:30]],
            choices=[c.to_dict() for c in list(self._choices.values())[:20]],
            lore=[l.to_dict() for l in list(self._lore.values())[:20]],
            quest_narratives=[q.to_dict() for q in list(self._quest_narratives.values())[:20]],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> Tuple[bool, str]:
        with _LOCK:
            self._story_arcs.clear()
            self._plot_threads.clear()
            self._characters.clear()
            self._beats.clear()
            self._choices.clear()
            self._lore.clear()
            self._quest_narratives.clear()
            self._events.clear()
            self._stats = NarrativeStats()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()
            self._emit("reset")
            return True, "reset"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_narrative_engine() -> NarrativeEngine:
    return NarrativeEngine.get_instance()
