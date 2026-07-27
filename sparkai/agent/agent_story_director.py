"""
SparkLabs Agent - Story Director

The AgentStoryDirector is the narrative intelligence of the AI-native game
engine. It creates, manages, and adapts story content in real-time based on
game state, player behavior, and world events.

Unlike traditional narrative systems that use static scripts, the Story
Director treats story as a living, breathing entity that evolves with the
player's journey. It maintains:

  1. STORY ARCS - Multi-act narrative structures with branching paths.
     Each arc has a theme, tension curve, and resolution conditions.
  2. CHARACTER GRAPH - A relationship network where characters have
     dispositions, goals, secrets, and evolving dynamics.
  3. PLOT POINTS - Discrete narrative events that can be triggered by
     game state changes, player actions, or director initiative.
  4. TENSION MODEL - A real-time tension curve that paces story beats
     for maximum engagement (calm -> rising -> climax -> resolution).
  5. NARRATIVE MEMORY - Remembers what the player has experienced,
     preventing repetition and enabling callbacks.

The director runs a narrative cycle every 5 seconds:
  ASSESS -> SELECT -> COMPOSE -> DISPATCH -> TRACK

It uses the cognitive mesh to:
  - Receive ANOMALY signals when narrative breaks occur
  - Emit DECISION signals when story changes are needed
  - Listen to TELEMETRY for player engagement metrics
  - Request OPPORTUNITY signals for creative story moments

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class ArcStatus(Enum):
    """Status of a story arc."""
    DORMANT = "dormant"        # Not yet started
    RISING = "rising"          # Tension building
    ACTIVE = "active"          # In full swing
    CLIMAX = "climax"          # Peak tension
    RESOLVING = "resolving"    # Winding down
    COMPLETED = "completed"    # Finished
    ABANDONED = "abandoned"    # Player skipped


class PlotPointType(Enum):
    """Types of plot points the director can deploy."""
    INCITING_INCIDENT = "inciting_incident"
    RISING_ACTION = "rising_action"
    MIDPOINT_TWIST = "midpoint_twist"
    COMPLICATION = "complication"
    DARK_MOMENT = "dark_moment"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    CALLBACK = "callback"          # Reference to earlier event
    CHARACTER_BEAT = "character_beat"
    WORLD_EVENT = "world_event"
    DISCOVERY = "discovery"
    BETRAYAL = "betrayal"
    REUNION = "reunion"
    SACRIFICE = "sacrifice"
    REVELATION = "revelation"


class CharacterRole(Enum):
    """Archetypal character roles in the narrative."""
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    MENTOR = "mentor"
    ALLY = "ally"
    FOIL = "foil"
    TRICKSTER = "trickster"
    GUARDIAN = "guardian"
    SHADOW = "shadow"
    HERALD = "herald"
    SHAPE_SHIFTER = "shape_shifter"


class TensionPhase(Enum):
    """Phases of the narrative tension curve."""
    CALM = 0        # Low tension, exploration/breathing room
    BUILDING = 1    # Tension rising
    PEAK = 2        # Maximum tension
    RELEASE = 3     # Tension releasing
    REFLECT = 4     # Post-event reflection


class DirectorPhase(Enum):
    """Phases of the director's narrative cycle."""
    ASSESS = "assess"
    SELECT = "select"
    COMPOSE = "compose"
    DISPATCH = "dispatch"
    TRACK = "track"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class Character:
    """A character in the narrative."""
    character_id: str
    name: str
    role: CharacterRole
    disposition: float = 0.0  # -1.0 (hostile) to 1.0 (friendly)
    trust: float = 0.5        # 0.0 to 1.0
    goals: List[str] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)
    is_alive: bool = True
    location: str = "unknown"
    last_interaction: float = 0.0
    arc_count: int = 0


@dataclass
class CharacterRelationship:
    """A relationship between two characters."""
    char_a: str
    char_b: str
    relationship_type: str  # "ally", "rival", "family", "romantic", "mentor"
    strength: float = 0.5   # 0.0 to 1.0
    tension: float = 0.0    # 0.0 to 1.0
    history: List[str] = field(default_factory=list)


@dataclass
class PlotPoint:
    """A discrete narrative event."""
    plot_id: str
    plot_type: PlotPointType
    title: str
    description: str
    arc_id: Optional[str] = None
    involved_characters: List[str] = field(default_factory=list)
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    consequences: Dict[str, Any] = field(default_factory=dict)
    tension_delta: float = 0.0  # How much this changes tension
    deployed: bool = False
    deployed_at: Optional[float] = None
    player_seen: bool = False
    impact_score: float = 0.0  # How much it affected the player (tracked)


@dataclass
class StoryArc:
    """A multi-act narrative structure."""
    arc_id: str
    title: str
    theme: str  # e.g., "redemption", "discovery", "conflict", "growth"
    description: str
    status: ArcStatus = ArcStatus.DORMANT
    acts_total: int = 3
    acts_completed: int = 0
    current_act: int = 0
    plot_points: List[str] = field(default_factory=list)  # plot IDs
    involved_characters: List[str] = field(default_factory=list)
    tension_start: float = 0.2
    tension_target: float = 0.8
    tension_current: float = 0.2
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    priority: float = 0.5
    tags: Set[str] = field(default_factory=set)


@dataclass
class NarrativeMemory:
    """Memory of past narrative events."""
    event_id: str
    description: str
    timestamp: float
    characters_involved: List[str]
    location: str
    emotional_valence: float  # -1.0 (negative) to 1.0 (positive)
    callback_count: int = 0  # How many times this has been referenced


@dataclass
class TensionState:
    """Current state of the narrative tension curve."""
    phase: TensionPhase = TensionPhase.CALM
    current_tension: float = 0.2  # 0.0 to 1.0
    target_tension: float = 0.3
    trend: float = 0.0  # Positive = rising, negative = falling
    last_peak: float = 0.0
    last_release: float = 0.0
    time_since_peak: float = 0.0
    beats_since_release: int = 0


@dataclass
class DirectorStats:
    """Aggregate statistics for the story director."""
    total_arcs: int = 0
    active_arcs: int = 0
    completed_arcs: int = 0
    total_plot_points: int = 0
    deployed_plot_points: int = 0
    total_characters: int = 0
    total_relationships: int = 0
    memory_events: int = 0
    total_cycles: int = 0
    avg_tension: float = 0.2
    last_cycle_at: float = 0.0
    cycle_interval_s: float = 5.0
    callbacks_used: int = 0


# =============================================================================
# Story Director
# =============================================================================

class AgentStoryDirector:
    """
    Singleton narrative intelligence that creates and manages dynamic story
    content in real-time.

    The director:
      1. Maintains a roster of characters with evolving relationships
      2. Manages multiple concurrent story arcs with different themes
      3. Paces narrative tension using a 5-phase model
      4. Deploys plot points based on game state and player behavior
      5. Remembers past events to enable narrative callbacks
      6. Adapts story content based on player engagement metrics
    """

    _instance: Optional["AgentStoryDirector"] = None
    _instance_lock = threading.Lock()

    # Plot point templates by type
    PLOT_TEMPLATES: Dict[PlotPointType, List[Dict[str, Any]]] = {
        PlotPointType.INCITING_INCIDENT: [
            {"title": "The Call", "description": "A mysterious message arrives, setting events in motion.", "tension_delta": 0.15},
            {"title": "The Discovery", "description": "An ancient relic is unearthed, revealing a hidden threat.", "tension_delta": 0.20},
            {"title": "The Loss", "description": "Something precious is taken, demanding action.", "tension_delta": 0.25},
        ],
        PlotPointType.RISING_ACTION: [
            {"title": "The First Obstacle", "description": "A challenge tests the protagonist's resolve.", "tension_delta": 0.10},
            {"title": "The Alliance", "description": "An unexpected ally offers aid.", "tension_delta": 0.05},
            {"title": "The Warning", "description": "A cryptic warning hints at danger ahead.", "tension_delta": 0.12},
        ],
        PlotPointType.MIDPOINT_TWIST: [
            {"title": "The Revelation", "description": "A shocking truth changes everything.", "tension_delta": 0.20},
            {"title": "The Betrayal", "description": "A trusted ally reveals their true allegiance.", "tension_delta": 0.25},
            {"title": "The Mirror", "description": "The protagonist confronts a dark reflection of themselves.", "tension_delta": 0.18},
        ],
        PlotPointType.COMPLICATION: [
            {"title": "The Cost", "description": "Progress comes at a personal price.", "tension_delta": 0.15},
            {"title": "The Deadline", "description": "Time runs short, raising the stakes.", "tension_delta": 0.12},
            {"title": "The Dilemma", "description": "Two paths forward, neither without sacrifice.", "tension_delta": 0.14},
        ],
        PlotPointType.DARK_MOMENT: [
            {"title": "The Fall", "description": "Everything falls apart; hope seems lost.", "tension_delta": 0.30},
            {"title": "The Isolation", "description": "The protagonist stands alone against the darkness.", "tension_delta": 0.25},
            {"title": "The Confession", "description": "A buried secret comes to light.", "tension_delta": 0.20},
        ],
        PlotPointType.CLIMAX: [
            {"title": "The Confrontation", "description": "The final showdown begins.", "tension_delta": 0.35},
            {"title": "The Choice", "description": "A irreversible decision must be made.", "tension_delta": 0.30},
            {"title": "The Sacrifice", "description": "Something must be given up to prevail.", "tension_delta": 0.28},
        ],
        PlotPointType.RESOLUTION: [
            {"title": "The Aftermath", "description": "The dust settles; consequences unfold.", "tension_delta": -0.25},
            {"title": "The Reward", "description": "The protagonist reaps what they have sown.", "tension_delta": -0.20},
            {"title": "The New Dawn", "description": "A new chapter begins.", "tension_delta": -0.30},
        ],
        PlotPointType.CALLBACK: [
            {"title": "The Echo", "description": "A past event resurfaces in a new light.", "tension_delta": 0.10},
            {"title": "The Promise Kept", "description": "A vow made long ago is fulfilled.", "tension_delta": -0.05},
            {"title": "The Reunion", "description": "Faces from the past return.", "tension_delta": 0.08},
        ],
        PlotPointType.CHARACTER_BEAT: [
            {"title": "The Growth", "description": "A character undergoes meaningful change.", "tension_delta": 0.03},
            {"title": "The Conflict", "description": "Inner turmoil surfaces.", "tension_delta": 0.08},
            {"title": "The Bond", "description": "Two characters grow closer.", "tension_delta": -0.05},
        ],
        PlotPointType.WORLD_EVENT: [
            {"title": "The Shift", "description": "The world itself changes.", "tension_delta": 0.12},
            {"title": "The Migration", "description": "Populations move, reshaping the landscape.", "tension_delta": 0.06},
            {"title": "The Awakening", "description": "Something ancient stirs.", "tension_delta": 0.15},
        ],
        PlotPointType.DISCOVERY: [
            {"title": "The Hidden Path", "description": "A secret route opens new possibilities.", "tension_delta": 0.08},
            {"title": "The Forgotten Lore", "description": "Ancient knowledge resurfaces.", "tension_delta": 0.10},
            {"title": "The Map", "description": "A chart reveals the way forward.", "tension_delta": 0.06},
        ],
        PlotPointType.BETRAYAL: [
            {"title": "The Turn", "description": "A trusted companion reveals their true allegiance.", "tension_delta": 0.28},
            {"title": "The Knife", "description": "An ally strikes when least expected.", "tension_delta": 0.30},
            {"title": "The Lie Unraveled", "description": "A long-held deception is exposed.", "tension_delta": 0.25},
        ],
        PlotPointType.REUNION: [
            {"title": "The Return", "description": "One thought lost comes back.", "tension_delta": -0.08},
            {"title": "The Recognition", "description": "Two figures meet again under new circumstances.", "tension_delta": -0.05},
            {"title": "The Reconciliation", "description": "Old wounds begin to heal.", "tension_delta": -0.10},
        ],
        PlotPointType.SACRIFICE: [
            {"title": "The Offering", "description": "Something precious is given up for the greater good.", "tension_delta": 0.20},
            {"title": "The Last Stand", "description": "One holds the line so others may escape.", "tension_delta": 0.25},
            {"title": "The Trade", "description": "A painful exchange secures survival.", "tension_delta": 0.18},
        ],
        PlotPointType.REVELATION: [
            {"title": "The Truth", "description": "A hidden fact comes to light.", "tension_delta": 0.22},
            {"title": "The Vision", "description": "A glimpse beyond the veil reveals what was unseen.", "tension_delta": 0.18},
            {"title": "The Confession", "description": "A long-buried secret is spoken aloud.", "tension_delta": 0.20},
        ],
    }

    # Story arc themes
    ARC_THEMES = [
        ("Redemption", "A fallen hero seeks to reclaim their honor"),
        ("Discovery", "Hidden truths reshape understanding of the world"),
        ("Conflict", "Two forces collide in an escalating struggle"),
        ("Growth", "A character evolves through adversity"),
        ("Betrayal", "Trust is broken and alliances shift"),
        ("Sacrifice", "Something precious must be given up"),
        ("Unity", "Fragmented groups must come together"),
        ("Legacy", "The past reaches forward to shape the future"),
        ("Freedom", "Chains are broken, but at what cost"),
        ("Power", "The corrupting influence of strength"),
    ]

    # Default character roster
    DEFAULT_CHARACTERS = [
        ("protagonist", "The Hero", CharacterRole.PROTAGONIST),
        ("antagonist", "The Shadow", CharacterRole.ANTAGONIST),
        ("mentor", "The Guide", CharacterRole.MENTOR),
        ("ally", "The Companion", CharacterRole.ALLY),
        ("foil", "The Mirror", CharacterRole.FOIL),
    ]

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._characters: Dict[str, Character] = {}
        self._relationships: Dict[str, CharacterRelationship] = {}
        self._arcs: Dict[str, StoryArc] = {}
        self._plot_points: Dict[str, PlotPoint] = {}
        self._memory: Deque[NarrativeMemory] = deque(maxlen=200)
        self._tension = TensionState()
        self._stats = DirectorStats()
        self._cycle_count: int = 0
        self._active: bool = False
        self._cycle_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._player_engagement: float = 0.5
        self._player_location: str = "start"
        self._deployed_log: Deque[Dict[str, Any]] = deque(maxlen=50)

        self._initialize_default_world()

    @classmethod
    def get_instance(cls) -> "AgentStoryDirector":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _initialize_default_world(self) -> None:
        """Initialize the default character roster and relationships."""
        for char_id, name, role in self.DEFAULT_CHARACTERS:
            self._characters[char_id] = Character(
                character_id=char_id,
                name=name,
                role=role,
                disposition=0.0 if role != CharacterRole.ANTAGONIST else -0.5,
                trust=0.5,
                goals=self._default_goals(role),
            )

        # Default relationships
        self._relationships["protagonist_mentor"] = CharacterRelationship(
            char_a="protagonist", char_b="mentor",
            relationship_type="mentor", strength=0.7, tension=0.1,
        )
        self._relationships["protagonist_ally"] = CharacterRelationship(
            char_a="protagonist", char_b="ally",
            relationship_type="ally", strength=0.6, tension=0.05,
        )
        self._relationships["protagonist_antagonist"] = CharacterRelationship(
            char_a="protagonist", char_b="antagonist",
            relationship_type="rival", strength=0.8, tension=0.6,
        )
        self._relationships["protagonist_foil"] = CharacterRelationship(
            char_a="protagonist", char_b="foil",
            relationship_type="foil", strength=0.4, tension=0.3,
        )

        self._stats.total_characters = len(self._characters)
        self._stats.total_relationships = len(self._relationships)

    def _default_goals(self, role: CharacterRole) -> List[str]:
        """Generate default goals for a character role."""
        goals = {
            CharacterRole.PROTAGONIST: ["Uncover the truth", "Protect the innocent"],
            CharacterRole.ANTAGONIST: ["Acquire power", "Eliminate opposition"],
            CharacterRole.MENTOR: ["Guide the protagonist", "Atone for past mistakes"],
            CharacterRole.ALLY: ["Support the protagonist", "Find belonging"],
            CharacterRole.FOIL: ["Challenge the protagonist", "Prove their methods"],
        }
        return goals.get(role, ["Survive"])

    # -------------------------------------------------------------------------
    # Character Management
    # -------------------------------------------------------------------------

    def add_character(self, name: str, role: CharacterRole,
                      disposition: float = 0.0, trust: float = 0.5,
                      goals: Optional[List[str]] = None) -> Dict[str, Any]:
        """Add a new character to the narrative."""
        char_id = f"char_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._characters[char_id] = Character(
                character_id=char_id,
                name=name,
                role=role,
                disposition=disposition,
                trust=trust,
                goals=goals or [],
            )
            self._stats.total_characters = len(self._characters)
        return {"character_id": char_id, "name": name, "role": role.value}

    def add_relationship(self, char_a: str, char_b: str,
                         rel_type: str, strength: float = 0.5,
                         tension: float = 0.0) -> Dict[str, Any]:
        """Add a relationship between two characters."""
        rel_id = f"{char_a}_{char_b}"
        with self._lock:
            self._relationships[rel_id] = CharacterRelationship(
                char_a=char_a, char_b=char_b,
                relationship_type=rel_type,
                strength=strength, tension=tension,
            )
            self._stats.total_relationships = len(self._relationships)
        return {"relationship_id": rel_id, "type": rel_type}

    def update_character(self, char_id: str, disposition: Optional[float] = None,
                         trust: Optional[float] = None,
                         location: Optional[str] = None) -> bool:
        """Update a character's state."""
        with self._lock:
            char = self._characters.get(char_id)
            if not char:
                return False
            if disposition is not None:
                char.disposition = max(-1.0, min(1.0, disposition))
            if trust is not None:
                char.trust = max(0.0, min(1.0, trust))
            if location is not None:
                char.location = location
            char.last_interaction = time.time()
            return True

    def get_characters(self) -> List[Dict[str, Any]]:
        """Get all characters."""
        with self._lock:
            return [
                {
                    "character_id": c.character_id,
                    "name": c.name,
                    "role": c.role.value,
                    "disposition": round(c.disposition, 2),
                    "trust": round(c.trust, 2),
                    "is_alive": c.is_alive,
                    "location": c.location,
                    "goals": c.goals,
                    "secrets": c.secrets,
                    "arc_count": c.arc_count,
                    "last_interaction": c.last_interaction,
                }
                for c in self._characters.values()
            ]

    def get_relationships(self) -> List[Dict[str, Any]]:
        """Get all relationships."""
        with self._lock:
            return [
                {
                    "relationship_id": f"{r.char_a}_{r.char_b}",
                    "char_a": r.char_a,
                    "char_b": r.char_b,
                    "type": r.relationship_type,
                    "strength": round(r.strength, 2),
                    "tension": round(r.tension, 2),
                    "history_count": len(r.history),
                }
                for r in self._relationships.values()
            ]

    # -------------------------------------------------------------------------
    # Story Arc Management
    # -------------------------------------------------------------------------

    def create_arc(self, title: str, theme: str, description: str = "",
                   acts: int = 3, priority: float = 0.5,
                   characters: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new story arc."""
        arc_id = f"arc_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._arcs[arc_id] = StoryArc(
                arc_id=arc_id,
                title=title,
                theme=theme,
                description=description,
                acts_total=acts,
                involved_characters=characters or ["protagonist"],
                priority=priority,
                tension_start=self._tension.current_tension,
                tension_target=min(1.0, self._tension.current_tension + 0.4),
            )
            self._stats.total_arcs = len(self._arcs)
        return {"arc_id": arc_id, "title": title, "theme": theme}

    def start_arc(self, arc_id: str) -> bool:
        """Start a dormant story arc."""
        with self._lock:
            arc = self._arcs.get(arc_id)
            if not arc or arc.status != ArcStatus.DORMANT:
                return False
            arc.status = ArcStatus.RISING
            arc.started_at = time.time()
            arc.current_act = 1
            self._stats.active_arcs = sum(
                1 for a in self._arcs.values()
                if a.status in (ArcStatus.RISING, ArcStatus.ACTIVE, ArcStatus.CLIMAX)
            )
            # Deploy inciting incident
            self._deploy_plot_point(PlotPointType.INCITING_INCIDENT, arc_id)
            return True

    def complete_arc(self, arc_id: str) -> bool:
        """Complete a story arc."""
        with self._lock:
            arc = self._arcs.get(arc_id)
            if not arc:
                return False
            arc.status = ArcStatus.COMPLETED
            arc.completed_at = time.time()
            arc.acts_completed = arc.acts_total
            # Deploy resolution
            self._deploy_plot_point(PlotPointType.RESOLUTION, arc_id)
            self._stats.completed_arcs = sum(
                1 for a in self._arcs.values() if a.status == ArcStatus.COMPLETED
            )
            self._stats.active_arcs = sum(
                1 for a in self._arcs.values()
                if a.status in (ArcStatus.RISING, ArcStatus.ACTIVE, ArcStatus.CLIMAX)
            )
            return True

    def get_arcs(self) -> List[Dict[str, Any]]:
        """Get all story arcs."""
        with self._lock:
            return [
                {
                    "arc_id": a.arc_id,
                    "title": a.title,
                    "theme": a.theme,
                    "description": a.description,
                    "status": a.status.value,
                    "current_act": a.current_act,
                    "acts_total": a.acts_total,
                    "acts_completed": a.acts_completed,
                    "tension_current": round(a.tension_current, 2),
                    "tension_target": round(a.tension_target, 2),
                    "plot_points": len(a.plot_points),
                    "involved_characters": a.involved_characters,
                    "priority": a.priority,
                    "started_at": a.started_at,
                    "completed_at": a.completed_at,
                }
                for a in self._arcs.values()
            ]

    # -------------------------------------------------------------------------
    # Plot Point Management
    # ----------------------------------------------------------------============

    def _deploy_plot_point(self, plot_type: PlotPointType,
                           arc_id: Optional[str] = None,
                           characters: Optional[List[str]] = None) -> Dict[str, Any]:
        """Deploy a plot point of the given type."""
        templates = self.PLOT_TEMPLATES.get(plot_type, [])
        if not templates:
            return {"error": f"No templates for {plot_type.value}"}

        template = random.choice(templates)
        plot_id = f"plot_{uuid.uuid4().hex[:8]}"
        arc = self._arcs.get(arc_id) if arc_id else None
        involved = characters or (arc.involved_characters if arc else ["protagonist"])

        plot = PlotPoint(
            plot_id=plot_id,
            plot_type=plot_type,
            title=template["title"],
            description=template["description"],
            arc_id=arc_id,
            involved_characters=involved,
            tension_delta=template.get("tension_delta", 0.1),
            deployed=True,
            deployed_at=time.time(),
        )

        with self._lock:
            self._plot_points[plot_id] = plot
            if arc:
                arc.plot_points.append(plot_id)
            self._stats.total_plot_points = len(self._plot_points)
            self._stats.deployed_plot_points = sum(
                1 for p in self._plot_points.values() if p.deployed
            )

            # Update tension
            self._apply_tension_delta(plot.tension_delta)

            # Store in memory
            self._memory.append(NarrativeMemory(
                event_id=plot_id,
                description=f"{plot.title}: {plot.description}",
                timestamp=time.time(),
                characters_involved=involved,
                location=self._player_location,
                emotional_valence=plot.tension_delta * -0.5,  # High tension = negative valence
            ))
            self._stats.memory_events = len(self._memory)

            # Log deployment
            self._deployed_log.append({
                "plot_id": plot_id,
                "type": plot_type.value,
                "title": plot.title,
                "arc_id": arc_id,
                "tension_delta": plot.tension_delta,
                "timestamp": time.time(),
            })

        return {
            "plot_id": plot_id,
            "type": plot_type.value,
            "title": plot.title,
            "description": plot.description,
            "tension_delta": plot.tension_delta,
            "characters": involved,
        }

    def deploy_plot_point(self, plot_type: str, arc_id: Optional[str] = None,
                          characters: Optional[List[str]] = None) -> Dict[str, Any]:
        """Public API to deploy a plot point.

        Case-insensitive: accepts both the enum name (e.g. "MIDPOINT_TWIST")
        and the enum value (e.g. "midpoint_twist").
        """
        pt = self._resolve_plot_type(plot_type)
        if pt is None:
            return {"error": f"Invalid plot type: {plot_type}"}
        return self._deploy_plot_point(pt, arc_id, characters)

    @staticmethod
    def _resolve_plot_type(name: str) -> Optional[PlotPointType]:
        """Resolve a plot type string case-insensitively (name or value)."""
        if not name:
            return None
        key = name.strip()
        for pt in PlotPointType:
            if pt.value == key.lower() or pt.name == key.upper():
                return pt
        return None

    def get_plot_points(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent plot points."""
        with self._lock:
            plots = sorted(
                self._plot_points.values(),
                key=lambda p: p.deployed_at or 0,
                reverse=True,
            )
            return [
                {
                    "plot_id": p.plot_id,
                    "type": p.plot_type.value,
                    "title": p.title,
                    "description": p.description,
                    "arc_id": p.arc_id,
                    "deployed": p.deployed,
                    "deployed_at": p.deployed_at,
                    "tension_delta": p.tension_delta,
                    "characters": p.involved_characters,
                    "player_seen": p.player_seen,
                    "impact_score": p.impact_score,
                }
                for p in plots[:limit]
            ]

    # -------------------------------------------------------------------------
    # Tension Management
    # -------------------------------------------------------------------------

    def _apply_tension_delta(self, delta: float) -> None:
        """Apply a tension change and update the phase."""
        self._tension.current_tension = max(0.0, min(1.0, self._tension.current_tension + delta))
        self._tension.trend = delta

        # Update phase based on tension level
        t = self._tension.current_tension
        if t < 0.2:
            self._tension.phase = TensionPhase.CALM
        elif t < 0.5:
            self._tension.phase = TensionPhase.BUILDING
        elif t < 0.8:
            self._tension.phase = TensionPhase.PEAK
        elif t < 0.6:
            self._tension.phase = TensionPhase.RELEASE
        else:
            self._tension.phase = TensionPhase.REFLECT

        if t > 0.7:
            self._tension.last_peak = time.time()

        self._stats.avg_tension = (
            self._stats.avg_tension * 0.9 + self._tension.current_tension * 0.1
        )

    def get_tension(self) -> Dict[str, Any]:
        """Get the current tension state."""
        with self._lock:
            return {
                "phase": self._tension.phase.name,
                "current_tension": round(self._tension.current_tension, 3),
                "target_tension": round(self._tension.target_tension, 3),
                "trend": round(self._tension.trend, 3),
                "time_since_peak": time.time() - self._tension.last_peak if self._tension.last_peak > 0 else 0,
                "beats_since_release": self._tension.beats_since_release,
            }

    def set_target_tension(self, target: float) -> None:
        """Set the target tension level."""
        with self._lock:
            self._tension.target_tension = max(0.0, min(1.0, target))

    # -------------------------------------------------------------------------
    # Narrative Cycle
    # -------------------------------------------------------------------------

    def run_cycle(self) -> Dict[str, Any]:
        """
        Run a single narrative cycle:
          ASSESS -> SELECT -> COMPOSE -> DISPATCH -> TRACK
        """
        cycle_start = time.time()
        result = {
            "phase": "",
            "assessed": False,
            "selected": False,
            "deployed": None,
            "tracked": False,
        }

        with self._lock:
            # 1. ASSESS - Evaluate current narrative state
            active_arcs = [
                a for a in self._arcs.values()
                if a.status in (ArcStatus.RISING, ArcStatus.ACTIVE, ArcStatus.CLIMAX)
            ]
            result["phase"] = "assess"
            result["assessed"] = True

            # 2. SELECT - Choose what plot point to deploy, if any
            should_deploy = False
            plot_type = None
            target_arc = None

            if active_arcs:
                arc = max(active_arcs, key=lambda a: a.priority)
                # Check if arc needs a new plot point
                time_since_last = time.time() - (arc.started_at or time.time())
                if arc.status == ArcStatus.RISING and arc.current_act < arc.acts_total:
                    # Advance arc
                    if self._tension.current_tension < arc.tension_target:
                        should_deploy = True
                        if arc.current_act == 1:
                            plot_type = PlotPointType.RISING_ACTION
                        elif arc.current_act == arc.acts_total // 2:
                            plot_type = PlotPointType.MIDPOINT_TWIST
                        else:
                            plot_type = PlotPointType.COMPLICATION
                        target_arc = arc
                elif arc.status == ArcStatus.RISING and arc.current_act >= arc.acts_total:
                    # Move to climax
                    arc.status = ArcStatus.CLIMAX
                    should_deploy = True
                    plot_type = PlotPointType.CLIMAX
                    target_arc = arc
                elif arc.status == ArcStatus.CLIMAX:
                    # Complete the arc
                    arc.status = ArcStatus.RESOLVING
                    should_deploy = True
                    plot_type = PlotPointType.RESOLUTION
                    target_arc = arc
                    arc.status = ArcStatus.COMPLETED
                    arc.completed_at = time.time()
            else:
                # No active arcs - maybe start one or deploy a character beat
                if random.random() < 0.3:
                    should_deploy = True
                    plot_type = random.choice([
                        PlotPointType.CHARACTER_BEAT,
                        PlotPointType.WORLD_EVENT,
                        PlotPointType.DISCOVERY,
                    ])

            # Tension regulation
            if self._tension.current_tension > 0.8 and not should_deploy:
                # Too tense - deploy a release
                should_deploy = True
                plot_type = PlotPointType.CALLBACK
            elif self._tension.current_tension < 0.15 and not should_deploy:
                # Too calm - raise tension
                should_deploy = True
                plot_type = PlotPointType.WORLD_EVENT

            result["phase"] = "select"
            result["selected"] = should_deploy

            # 3. COMPOSE & 4. DISPATCH
            if should_deploy and plot_type:
                deployed = self._deploy_plot_point(
                    plot_type,
                    target_arc.arc_id if target_arc else None,
                )
                result["deployed"] = deployed
                if target_arc and plot_type == PlotPointType.RISING_ACTION:
                    target_arc.current_act = min(target_arc.current_act + 1, target_arc.acts_total)

            result["phase"] = "dispatch"

            # 5. TRACK
            self._cycle_count += 1
            self._stats.total_cycles = self._cycle_count
            self._stats.last_cycle_at = time.time()
            self._stats.active_arcs = len(active_arcs)
            result["tracked"] = True
            result["phase"] = "track"

        result["cycle_ms"] = round((time.time() - cycle_start) * 1000, 2)
        return result

    def start(self) -> None:
        """Start the automatic narrative cycle."""
        if self._active:
            return
        self._active = True
        self._stop_event.clear()
        self._cycle_thread = threading.Thread(
            target=self._cycle_loop, daemon=True, name="story-director"
        )
        self._cycle_thread.start()
        logger.info("Story director started")

    def stop(self) -> None:
        """Stop the automatic narrative cycle."""
        self._active = False
        self._stop_event.set()
        if self._cycle_thread:
            self._cycle_thread.join(timeout=2.0)

    def _cycle_loop(self) -> None:
        """Background loop."""
        while not self._stop_event.is_set():
            try:
                self.run_cycle()
            except Exception as e:
                logger.error("Story director cycle error: %s", e)
            self._stop_event.wait(self._stats.cycle_interval_s)

    # -------------------------------------------------------------------------
    # Player Feedback
    # -------------------------------------------------------------------------

    def update_player_state(self, engagement: float, location: str = "") -> None:
        """Update player state from telemetry."""
        with self._lock:
            self._player_engagement = max(0.0, min(1.0, engagement))
            if location:
                self._player_location = location

    def mark_plot_seen(self, plot_id: str, impact: float = 0.5) -> bool:
        """Mark a plot point as seen by the player and record impact."""
        with self._lock:
            plot = self._plot_points.get(plot_id)
            if not plot:
                return False
            plot.player_seen = True
            plot.impact_score = max(0.0, min(1.0, impact))
            return True

    # -------------------------------------------------------------------------
    # Memory and Callbacks
    # -------------------------------------------------------------------------

    def get_memory(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get narrative memory events."""
        with self._lock:
            return [
                {
                    "event_id": m.event_id,
                    "description": m.description,
                    "timestamp": m.timestamp,
                    "characters": m.characters_involved,
                    "location": m.location,
                    "emotional_valence": round(m.emotional_valence, 2),
                    "callback_count": m.callback_count,
                }
                for m in list(self._memory)[-limit:]
            ]

    def get_callbacks(self) -> List[Dict[str, Any]]:
        """Get memory events that could be used for callbacks."""
        with self._lock:
            return [
                {
                    "event_id": m.event_id,
                    "description": m.description,
                    "callback_count": m.callback_count,
                }
                for m in self._memory
                if m.callback_count < 2  # Can still be referenced
            ]

    # -------------------------------------------------------------------------
    # Status and API
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the director status."""
        with self._lock:
            return {
                "active": self._active,
                "cycle_count": self._cycle_count,
                "last_cycle_at": self._stats.last_cycle_at,
                "cycle_interval_s": self._stats.cycle_interval_s,
                "stats": {
                    "total_arcs": self._stats.total_arcs,
                    "active_arcs": self._stats.active_arcs,
                    "completed_arcs": self._stats.completed_arcs,
                    "total_plot_points": self._stats.total_plot_points,
                    "deployed_plot_points": self._stats.deployed_plot_points,
                    "total_characters": self._stats.total_characters,
                    "total_relationships": self._stats.total_relationships,
                    "memory_events": self._stats.memory_events,
                    "total_cycles": self._stats.total_cycles,
                    "avg_tension": round(self._stats.avg_tension, 3),
                    "callbacks_used": self._stats.callbacks_used,
                },
                "tension": self.get_tension(),
                "player_engagement": round(self._player_engagement, 2),
                "player_location": self._player_location,
            }

    def get_deployed_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the deployment log."""
        with self._lock:
            return list(self._deployed_log)[-limit:]

    def simulate(self, cycles: int = 5) -> Dict[str, Any]:
        """Run multiple cycles for simulation/testing."""
        results = []
        for _ in range(cycles):
            result = self.run_cycle()
            results.append(result)
        return {
            "cycles_run": len(results),
            "deployed": sum(1 for r in results if r.get("deployed")),
            "results": results,
        }

    def reset(self) -> None:
        """Reset the director to initial state."""
        with self._lock:
            self._arcs.clear()
            self._plot_points.clear()
            self._memory.clear()
            self._tension = TensionState()
            self._stats = DirectorStats()
            self._stats.total_characters = len(self._characters)
            self._stats.total_relationships = len(self._relationships)
            self._cycle_count = 0
            self._deployed_log.clear()
            for char in self._characters.values():
                char.disposition = 0.0 if char.role != CharacterRole.ANTAGONIST else -0.5
                char.trust = 0.5
                char.arc_count = 0


# =============================================================================
# Module-level accessor
# =============================================================================

def get_story_director() -> AgentStoryDirector:
    """Return the singleton story director instance."""
    return AgentStoryDirector.get_instance()
