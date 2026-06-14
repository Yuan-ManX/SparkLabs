"""
Agent Procedural Storyteller - AI-driven procedural storytelling system.
Generates dynamic narratives, quests, character arcs, and world events
that adapt to player actions and agent interactions.
"""

import threading
import uuid
import random
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any


class StoryArc(Enum):
    """Classic story arc types."""
    HEROES_JOURNEY = "heroes_journey"
    RAGS_TO_RICHES = "rags_to_riches"
    TRAGEDY = "tragedy"
    REDEMPTION = "redemption"
    REVENGE = "revenge"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    COMING_OF_AGE = "coming_of_age"


class StoryBeat(Enum):
    """Types of story beats in a narrative."""
    EXPOSITION = "exposition"
    INCITING_INCIDENT = "inciting_incident"
    RISING_ACTION = "rising_action"
    MIDPOINT = "midpoint"
    CRISIS = "crisis"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"
    EPILOGUE = "epilogue"


class NarrativeTone(Enum):
    """Tone of the narrative."""
    EPIC = "epic"
    DARK = "dark"
    WHIMSICAL = "whimsical"
    DRAMATIC = "dramatic"
    COMEDIC = "comedic"
    MYSTERIOUS = "mysterious"
    HEROIC = "heroic"
    GRIMDARK = "grimdark"


@dataclass
class StoryNode:
    """A node in the story graph."""
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    beat_type: StoryBeat = StoryBeat.EXPOSITION
    title: str = ""
    description: str = ""
    characters_involved: List[str] = field(default_factory=list)
    location: str = ""
    conditions: Dict[str, Any] = field(default_factory=dict)
    outcomes: List[Dict[str, Any]] = field(default_factory=list)
    next_nodes: List[str] = field(default_factory=list)
    is_completed: bool = False
    order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "beat_type": self.beat_type.value,
            "title": self.title,
            "description": self.description,
            "characters_involved": self.characters_involved,
            "location": self.location,
            "conditions": self.conditions,
            "next_nodes": self.next_nodes,
            "is_completed": self.is_completed,
            "order": self.order,
        }


@dataclass
class StoryLine:
    """A complete storyline with narrative structure."""
    storyline_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    arc: StoryArc = StoryArc.HEROES_JOURNEY
    tone: NarrativeTone = NarrativeTone.EPIC
    nodes: Dict[str, StoryNode] = field(default_factory=dict)
    current_node: str = ""
    protagonist_id: str = ""
    antagonist_id: str = ""
    themes: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: float = field(default_factory=_time_module.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "storyline_id": self.storyline_id,
            "name": self.name,
            "arc": self.arc.value,
            "tone": self.tone.value,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "current_node": self.current_node,
            "protagonist_id": self.protagonist_id,
            "antagonist_id": self.antagonist_id,
            "themes": self.themes,
            "is_active": self.is_active,
            "node_count": len(self.nodes),
        }


@dataclass
class WorldEvent:
    """A world event that affects the story."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    event_type: str = ""
    affected_regions: List[str] = field(default_factory=list)
    affected_characters: List[str] = field(default_factory=list)
    story_impact: float = 0.5
    timestamp: float = field(default_factory=_time_module.time)
    is_resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "name": self.name,
            "description": self.description,
            "event_type": self.event_type,
            "affected_regions": self.affected_regions,
            "affected_characters": self.affected_characters,
            "story_impact": self.story_impact,
            "timestamp": self.timestamp,
            "is_resolved": self.is_resolved,
        }


class AgentProceduralStoryteller:
    """
    Procedural storytelling system for AI-driven narratives.
    Generates dynamic storylines, world events, and character arcs
    that respond to player choices and agent interactions.
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
            self._storylines: Dict[str, StoryLine] = {}
            self._world_events: Dict[str, WorldEvent] = {}
            self._story_templates: Dict[StoryArc, List[Dict[str, Any]]] = self._init_templates()
            self._character_arcs: Dict[str, List[Dict[str, Any]]] = {}
            self._narrative_context: Dict[str, Any] = {}
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'AgentProceduralStoryteller':
        return cls()

    def _init_templates(self) -> Dict[StoryArc, List[Dict[str, Any]]]:
        """Initialize story structure templates."""
        return {
            StoryArc.HEROES_JOURNEY: [
                {"beat": StoryBeat.EXPOSITION, "template": "The hero {name} lives in {location}, unaware of the adventure ahead."},
                {"beat": StoryBeat.INCITING_INCIDENT, "template": "A {event} forces {name} to leave their home."},
                {"beat": StoryBeat.RISING_ACTION, "template": "{name} faces {challenge} and meets {ally}."},
                {"beat": StoryBeat.MIDPOINT, "template": "A revelation about {secret} changes everything for {name}."},
                {"beat": StoryBeat.CRISIS, "template": "{name} suffers a devastating {loss} at the hands of {antagonist}."},
                {"beat": StoryBeat.CLIMAX, "template": "The final confrontation between {name} and {antagonist} at {location}."},
                {"beat": StoryBeat.RESOLUTION, "template": "{name} emerges victorious, having learned {lesson}."},
            ],
            StoryArc.MYSTERY: [
                {"beat": StoryBeat.EXPOSITION, "template": "Detective {name} is called to investigate {crime} at {location}."},
                {"beat": StoryBeat.INCITING_INCIDENT, "template": "A new {clue} surfaces, pointing to {suspect}."},
                {"beat": StoryBeat.RISING_ACTION, "template": "{name} interviews {witness} and discovers {evidence}."},
                {"beat": StoryBeat.MIDPOINT, "template": "The prime suspect {suspect} is found {state}, complicating the case."},
                {"beat": StoryBeat.CRISIS, "template": "{name} realizes the true culprit is {antagonist}."},
                {"beat": StoryBeat.CLIMAX, "template": "A tense confrontation at {location} reveals the full {truth}."},
                {"beat": StoryBeat.RESOLUTION, "template": "Justice is served as {name} presents the evidence to {authority}."},
            ],
            StoryArc.REDEMPTION: [
                {"beat": StoryBeat.EXPOSITION, "template": "{name} lives with the burden of {past_mistake}."},
                {"beat": StoryBeat.INCITING_INCIDENT, "template": "An opportunity to make amends appears when {event} occurs."},
                {"beat": StoryBeat.RISING_ACTION, "template": "{name} struggles to help {beneficiary} while fighting inner demons."},
                {"beat": StoryBeat.MIDPOINT, "template": "A setback occurs when {antagonist} exposes {name}'s past."},
                {"beat": StoryBeat.CRISIS, "template": "{name} must choose between {choice_a} and {choice_b}."},
                {"beat": StoryBeat.CLIMAX, "template": "In a moment of truth, {name} sacrifices {sacrifice} for {beneficiary}."},
                {"beat": StoryBeat.RESOLUTION, "template": "{name} finds peace, having finally {resolution_action}."},
            ],
        }

    def create_storyline(self, name: str, arc: StoryArc, protagonist_id: str,
                         tone: NarrativeTone = NarrativeTone.EPIC,
                         themes: List[str] = None) -> StoryLine:
        """Create a new storyline for a character."""
        storyline = StoryLine(
            name=name,
            arc=arc,
            tone=tone,
            protagonist_id=protagonist_id,
            themes=themes or [],
        )

        templates = self._story_templates.get(arc, self._story_templates[StoryArc.HEROES_JOURNEY])
        for i, template in enumerate(templates):
            node = StoryNode(
                beat_type=template["beat"],
                title=f"{template['beat'].value.replace('_', ' ').title()}",
                description=template["template"],
                characters_involved=[protagonist_id],
                order=i,
            )
            storyline.nodes[node.node_id] = node
            if i == 0:
                storyline.current_node = node.node_id
            if i > 0:
                prev_nodes = [n.node_id for n in storyline.nodes.values() if n.order == i - 1]
                for pn in prev_nodes:
                    storyline.nodes[pn].next_nodes.append(node.node_id)

        self._storylines[storyline.storyline_id] = storyline
        return storyline

    def advance_story(self, storyline_id: str, choices: Dict[str, Any] = None) -> Optional[StoryNode]:
        """Advance the story to the next node."""
        storyline = self._storylines.get(storyline_id)
        if not storyline:
            return None

        current = storyline.nodes.get(storyline.current_node)
        if not current:
            return None

        current.is_completed = True

        if not current.next_nodes:
            storyline.is_active = False
            storyline.completed_at = _time_module.time()
            return None

        next_id = current.next_nodes[0]
        if choices and len(current.next_nodes) > 1:
            choice_key = choices.get("choice", 0)
            next_id = current.next_nodes[min(choice_key, len(current.next_nodes) - 1)]

        storyline.current_node = next_id
        return storyline.nodes.get(next_id)

    def generate_world_event(self, event_type: str, description: str,
                             affected_regions: List[str] = None,
                             affected_characters: List[str] = None) -> WorldEvent:
        """Generate a world event that impacts the story."""
        event = WorldEvent(
            name=f"{event_type.replace('_', ' ').title()} Event",
            description=description,
            event_type=event_type,
            affected_regions=affected_regions or [],
            affected_characters=affected_characters or [],
            story_impact=random.uniform(0.3, 0.9),
        )
        self._world_events[event.event_id] = event

        for storyline in self._storylines.values():
            if storyline.is_active:
                affected = set(affected_characters or [])
                if storyline.protagonist_id in affected:
                    current = storyline.nodes.get(storyline.current_node)
                    if current:
                        current.description += f" [World Event: {description}]"

        return event

    def resolve_event(self, event_id: str, resolution: str):
        """Resolve a world event."""
        event = self._world_events.get(event_id)
        if event:
            event.is_resolved = True
            event.description += f" Resolution: {resolution}"

    def generate_character_arc(self, character_id: str, arc_type: StoryArc,
                               context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Generate a character arc narrative."""
        arc_stages = [
            {"stage": "origin", "description": f"Character {character_id} begins their journey."},
            {"stage": "challenge", "description": f"Character {character_id} faces their first major challenge."},
            {"stage": "transformation", "description": f"Character {character_id} undergoes a significant change."},
            {"stage": "resolution", "description": f"Character {character_id} reaches their destiny."},
        ]

        if context:
            arc_stages[0]["description"] = context.get("origin", arc_stages[0]["description"])
            arc_stages[1]["description"] = context.get("challenge", arc_stages[1]["description"])
            arc_stages[2]["description"] = context.get("transformation", arc_stages[2]["description"])
            arc_stages[3]["description"] = context.get("resolution", arc_stages[3]["description"])

        self._character_arcs[character_id] = arc_stages
        return arc_stages

    def get_narrative_summary(self, storyline_id: str) -> Dict[str, Any]:
        """Get a summary of the current narrative state."""
        storyline = self._storylines.get(storyline_id)
        if not storyline:
            return {"error": "Storyline not found"}

        completed = [n for n in storyline.nodes.values() if n.is_completed]
        remaining = [n for n in storyline.nodes.values() if not n.is_completed]

        return {
            "storyline_name": storyline.name,
            "arc": storyline.arc.value,
            "tone": storyline.tone.value,
            "progress": f"{len(completed)}/{len(storyline.nodes)}",
            "completed_beats": [n.beat_type.value for n in completed],
            "upcoming_beats": [n.beat_type.value for n in remaining],
            "is_active": storyline.is_active,
            "protagonist": storyline.protagonist_id,
            "themes": storyline.themes,
        }

    def get_active_events(self) -> List[WorldEvent]:
        """Get all unresolved world events."""
        return [e for e in self._world_events.values() if not e.is_resolved]

    def get_storyline(self, storyline_id: str) -> Optional[StoryLine]:
        """Get a storyline by ID."""
        return self._storylines.get(storyline_id)

    def list_storylines(self, protagonist_id: str = "") -> List[StoryLine]:
        """List all storylines, optionally filtered by protagonist."""
        if protagonist_id:
            return [s for s in self._storylines.values() if s.protagonist_id == protagonist_id]
        return list(self._storylines.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get storyteller system statistics."""
        return {
            "total_storylines": len(self._storylines),
            "active_storylines": sum(1 for s in self._storylines.values() if s.is_active),
            "total_events": len(self._world_events),
            "active_events": sum(1 for e in self._world_events.values() if not e.is_resolved),
            "total_character_arcs": len(self._character_arcs),
            "arc_distribution": self._get_arc_distribution(),
        }

    def _get_arc_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for s in self._storylines.values():
            arc = s.arc.value
            dist[arc] = dist.get(arc, 0) + 1
        return dist


def get_procedural_storyteller() -> AgentProceduralStoryteller:
    return AgentProceduralStoryteller.get_instance()