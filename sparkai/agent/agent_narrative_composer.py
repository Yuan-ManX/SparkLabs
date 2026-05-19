"""
SparkLabs Agent - Narrative Composer

Intelligent story construction agent that generates coherent game narratives —
complete with characters, branching dialogue trees, plot arcs, and world lore.
The composer maintains internal consistency across all narrative elements and
adapts to the game's genre, tone, and scope defined by the Game Director.

Architecture:
  NarrativeComposer
    |-- PlotArchitect (story structure: acts, beats, turning points)
    |-- CharacterForge (NPC personalities, backstories, motivations)
    |-- DialogueWeaver (branching conversation trees with consequence tracking)
    |-- LoreKeeper (world history, factions, artifacts, mythology)
    |-- ConsistencyEngine (cross-references characters, locations, events)

Narrative Elements:
  - PLOT: main storyline, side quests, world events, faction conflicts
  - CHARACTER: protagonists, antagonists, supporting cast, NPC templates
  - DIALOGUE: branching trees with conditions, tone variants, consequence flags
  - LORE: world history, mythology, factions, locations, item descriptions
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NarrativeElement(Enum):
    PLOT = "plot"
    CHARACTER = "character"
    DIALOGUE = "dialogue"
    LORE = "lore"


class PlotStructure(Enum):
    LINEAR = "linear"
    BRANCHING = "branching"
    EPISODIC = "episodic"
    OPEN_WORLD = "open_world"
    MYSTERY = "mystery"


class CharacterRole(Enum):
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SIDEKICK = "sidekick"
    MENTOR = "mentor"
    NPC = "npc"
    VENDOR = "vendor"
    QUEST_GIVER = "quest_giver"


class ToneVariant(Enum):
    FRIENDLY = "friendly"
    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    MYSTERIOUS = "mysterious"
    SARCASTIC = "sarcastic"
    FORMAL = "formal"


@dataclass
class PlotBeat:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    story_id: str = ""
    act_number: int = 1
    title: str = ""
    description: str = ""
    key_events: List[str] = field(default_factory=list)
    characters_involved: List[str] = field(default_factory=list)
    is_major_turning_point: bool = False
    order_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "story_id": self.story_id,
            "act_number": self.act_number,
            "title": self.title,
            "description": self.description,
            "key_events": self.key_events,
            "characters_involved": self.characters_involved,
            "is_major_turning_point": self.is_major_turning_point,
            "order_index": self.order_index,
        }


@dataclass
class CharacterProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    story_id: str = ""
    name: str = ""
    role: CharacterRole = CharacterRole.NPC
    archetype: str = ""
    motivation: str = ""
    backstory: str = ""
    personality_traits: List[str] = field(default_factory=list)
    default_tone: ToneVariant = ToneVariant.NEUTRAL
    faction: str = ""
    relationships: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "story_id": self.story_id,
            "name": self.name,
            "role": self.role.value,
            "archetype": self.archetype,
            "motivation": self.motivation,
            "backstory": self.backstory,
            "personality_traits": self.personality_traits,
            "default_tone": self.default_tone.value,
            "faction": self.faction,
            "relationships": self.relationships,
        }


@dataclass
class DialogueNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    story_id: str = ""
    character_id: str = ""
    text: str = ""
    tone: ToneVariant = ToneVariant.NEUTRAL
    condition: str = ""
    children: List[str] = field(default_factory=list)
    consequence: str = ""
    is_terminal: bool = False
    requires_quest_stage: str = ""
    grants_quest: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "story_id": self.story_id,
            "character_id": self.character_id,
            "text": self.text,
            "tone": self.tone.value,
            "condition": self.condition,
            "children": self.children,
            "consequence": self.consequence,
            "is_terminal": self.is_terminal,
            "requires_quest_stage": self.requires_quest_stage,
            "grants_quest": self.grants_quest,
        }


@dataclass
class LoreEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    story_id: str = ""
    title: str = ""
    category: str = ""
    content: str = ""
    related_characters: List[str] = field(default_factory=list)
    related_locations: List[str] = field(default_factory=list)
    is_public: bool = True
    discovery_condition: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "story_id": self.story_id,
            "title": self.title,
            "category": self.category,
            "content": self.content,
            "related_characters": self.related_characters,
            "related_locations": self.related_locations,
            "is_public": self.is_public,
            "discovery_condition": self.discovery_condition,
        }


@dataclass
class StoryProject:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    genre: str = "fantasy"
    tone: str = "epic"
    structure: PlotStructure = PlotStructure.LINEAR
    synopsis: str = ""
    target_playtime: str = "2-4 hours"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "genre": self.genre,
            "tone": self.tone,
            "structure": self.structure.value,
            "synopsis": self.synopsis,
            "target_playtime": self.target_playtime,
            "created_at": self.created_at,
        }


class NarrativeComposer:
    """AI agent for constructing game narratives, characters, and dialogue."""

    _instance: Optional["NarrativeComposer"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._stories: Dict[str, StoryProject] = {}
        self._plot_beats: Dict[str, List[PlotBeat]] = {}
        self._characters: Dict[str, List[CharacterProfile]] = {}
        self._dialogues: Dict[str, List[DialogueNode]] = {}
        self._lore: Dict[str, List[LoreEntry]] = {}
        self._composition_log: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "NarrativeComposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Story Project Management ----

    def create_story(self,
                     title: str = "Untitled Story",
                     genre: str = "fantasy",
                     tone: str = "epic",
                     synopsis: str = "",
                     structure: str = "linear",
                     target_playtime: str = "2-4 hours") -> StoryProject:
        try:
            st = PlotStructure(structure.lower())
        except ValueError:
            st = PlotStructure.LINEAR
        story = StoryProject(
            title=title,
            genre=genre,
            tone=tone,
            synopsis=synopsis,
            structure=st,
            target_playtime=target_playtime,
        )
        self._stories[story.id] = story
        self._plot_beats[story.id] = []
        self._characters[story.id] = []
        self._dialogues[story.id] = []
        self._lore[story.id] = []
        self._seed_default_beats(story.id)
        self._composition_log.append({
            "action": "story_created",
            "story_id": story.id,
            "title": title,
            "timestamp": time.time(),
        })
        return story

    def get_story(self, story_id: str) -> Optional[StoryProject]:
        return self._stories.get(story_id)

    def list_stories(self) -> List[StoryProject]:
        return list(self._stories.values())

    # ---- Plot Architecture ----

    def add_plot_beat(self,
                      story_id: str,
                      title: str,
                      act_number: int = 1,
                      description: str = "",
                      is_turning_point: bool = False,
                      characters: Optional[List[str]] = None,
                      key_events: Optional[List[str]] = None) -> Optional[PlotBeat]:
        story = self._stories.get(story_id)
        if story is None:
            return None
        existing = self._plot_beats.get(story_id, [])
        beat = PlotBeat(
            story_id=story_id,
            act_number=max(1, act_number),
            title=title,
            description=description,
            is_major_turning_point=is_turning_point,
            characters_involved=characters or [],
            key_events=key_events or [],
            order_index=len(existing),
        )
        existing.append(beat)
        self._plot_beats[story_id] = existing
        return beat

    def _seed_default_beats(self, story_id: str) -> None:
        beats = [
            ("The Ordinary World", 1, True, "Introduction to the setting and protagonist's daily life"),
            ("The Call to Adventure", 1, True, "An event disrupts the status quo and beckons the hero"),
            ("Crossing the Threshold", 1, False, "The protagonist commits to the journey"),
            ("Tests, Allies, and Enemies", 2, False, "Facing early challenges and forming relationships"),
            ("The Ordeal", 2, True, "A major crisis that tests everything the protagonist believes"),
            ("The Reward", 2, False, "Gaining something valuable after surviving the ordeal"),
            ("The Road Back", 3, False, "A final push toward resolution, often with restored urgency"),
            ("The Climax", 3, True, "The ultimate confrontation and decisive moment"),
            ("Resolution", 3, False, "Loose ends tied and the new status quo established"),
        ]
        for i, (title, act, is_turn, desc) in enumerate(beats):
            self.add_plot_beat(story_id, title, act, desc, is_turn, [])

    def get_plot_beats(self,
                       story_id: str,
                       act_number: Optional[int] = None) -> List[PlotBeat]:
        beats = self._plot_beats.get(story_id, [])
        if act_number is not None:
            return [b for b in beats if b.act_number == act_number]
        return sorted(beats, key=lambda b: (b.act_number, b.order_index))

    def get_turning_points(self, story_id: str) -> List[PlotBeat]:
        beats = self._plot_beats.get(story_id, [])
        return [b for b in beats if b.is_major_turning_point]

    # ---- Character Forge ----

    def create_character(self,
                         story_id: str,
                         name: str,
                         role: str = "npc",
                         archetype: str = "",
                         motivation: str = "",
                         backstory: str = "",
                         traits: Optional[List[str]] = None,
                         default_tone: str = "neutral",
                         faction: str = "") -> Optional[CharacterProfile]:
        story = self._stories.get(story_id)
        if story is None:
            return None
        try:
            char_role = CharacterRole(role.lower())
        except ValueError:
            char_role = CharacterRole.NPC
        try:
            tone = ToneVariant(default_tone.lower())
        except ValueError:
            tone = ToneVariant.NEUTRAL
        character = CharacterProfile(
            story_id=story_id,
            name=name,
            role=char_role,
            archetype=archetype,
            motivation=motivation,
            backstory=backstory,
            personality_traits=traits or [],
            default_tone=tone,
            faction=faction,
        )
        chars = self._characters.get(story_id, [])
        chars.append(character)
        self._characters[story_id] = chars
        return character

    def add_character_relationship(self,
                                   story_id: str,
                                   char_id: str,
                                   other_char_id: str,
                                   relationship_type: str) -> bool:
        chars = self._characters.get(story_id, [])
        for c in chars:
            if c.id == char_id:
                c.relationships[other_char_id] = relationship_type
                return True
        return False

    def get_characters(self,
                       story_id: str,
                       role: Optional[str] = None) -> List[CharacterProfile]:
        chars = self._characters.get(story_id, [])
        if role is not None:
            return [c for c in chars if c.role.value == role.lower()]
        return chars

    # ---- Dialogue Weaving ----

    def add_dialogue_node(self,
                          story_id: str,
                          character_id: str,
                          text: str,
                          tone: str = "neutral",
                          parent_id: str = "",
                          children: Optional[List[str]] = None,
                          condition: str = "",
                          consequence: str = "",
                          is_terminal: bool = False,
                          grants_quest: str = "",
                          requires_quest_stage: str = "") -> Optional[DialogueNode]:
        story = self._stories.get(story_id)
        if story is None:
            return None
        try:
            t = ToneVariant(tone.lower())
        except ValueError:
            t = ToneVariant.NEUTRAL
        node = DialogueNode(
            story_id=story_id,
            character_id=character_id,
            text=text,
            tone=t,
            condition=condition,
            children=children or [],
            consequence=consequence,
            is_terminal=is_terminal,
            grants_quest=grants_quest,
            requires_quest_stage=requires_quest_stage,
        )
        dialogs = self._dialogues.get(story_id, [])
        dialogs.append(node)
        self._dialogues[story_id] = dialogs
        if parent_id:
            for d in dialogs:
                if d.id == parent_id:
                    d.children.append(node.id)
                    break
        return node

    def build_dialogue_tree(self,
                            story_id: str,
                            character_id: str,
                            opening_line: str,
                            tone: str = "neutral") -> List[DialogueNode]:
        nodes: List[DialogueNode] = []
        root = self.add_dialogue_node(story_id, character_id, opening_line, tone)
        if root is None:
            return nodes
        nodes.append(root)

        options = [
            ("Tell me more about yourself.", "friendly", False, None),
            ("What can you help me with?", "neutral", False, None),
            ("I don't trust you.", "hostile", False, None),
            ("Goodbye.", "neutral", True, None),
        ]
        for opt_text, opt_tone, is_term, quest in options:
            child = self.add_dialogue_node(
                story_id, character_id, opt_text, opt_tone,
                parent_id=root.id, is_terminal=is_term, grants_quest=quest or "",
            )
            if child:
                nodes.append(child)
        return nodes

    def get_dialogue_nodes(self,
                           story_id: str,
                           character_id: Optional[str] = None) -> List[DialogueNode]:
        dialogs = self._dialogues.get(story_id, [])
        if character_id:
            return [d for d in dialogs if d.character_id == character_id]
        return dialogs

    def get_dialogue_tree(self,
                          story_id: str,
                          root_id: str) -> List[DialogueNode]:
        dialogs = self._dialogues.get(story_id, [])
        result: List[DialogueNode] = []
        visited: set = set()
        stack = [root_id]
        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue
            visited.add(node_id)
            for d in dialogs:
                if d.id == node_id:
                    result.append(d)
                    stack.extend(d.children)
                    break
        return result

    # ---- Lore Keeper ----

    def add_lore_entry(self,
                        story_id: str,
                        title: str,
                        category: str = "history",
                        content: str = "",
                        is_public: bool = True) -> Optional[LoreEntry]:
        story = self._stories.get(story_id)
        if story is None:
            return None
        entry = LoreEntry(
            story_id=story_id,
            title=title,
            category=category,
            content=content,
            is_public=is_public,
        )
        entries = self._lore.get(story_id, [])
        entries.append(entry)
        self._lore[story_id] = entries
        return entry

    def get_lore(self,
                 story_id: str,
                 category: Optional[str] = None) -> List[LoreEntry]:
        entries = self._lore.get(story_id, [])
        if category:
            return [e for e in entries if e.category == category]
        return entries

    # ---- Full Story Export ----

    def export_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        story = self._stories.get(story_id)
        if story is None:
            return None
        return {
            "project": story.to_dict(),
            "plot": {
                "structure": story.structure.value,
                "beats": [b.to_dict() for b in self._plot_beats.get(story_id, [])],
                "turning_points": [b.to_dict() for b in self.get_turning_points(story_id)],
            },
            "characters": {
                "count": len(self._characters.get(story_id, [])),
                "profiles": [c.to_dict() for c in self._characters.get(story_id, [])],
            },
            "dialogue": {
                "node_count": len(self._dialogues.get(story_id, [])),
                "nodes": [d.to_dict() for d in self._dialogues.get(story_id, [])],
            },
            "lore": {
                "entry_count": len(self._lore.get(story_id, [])),
                "entries": [l.to_dict() for l in self._lore.get(story_id, [])],
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        total_beats = sum(len(v) for v in self._plot_beats.values())
        total_characters = sum(len(v) for v in self._characters.values())
        total_dialogue = sum(len(v) for v in self._dialogues.values())
        total_lore = sum(len(v) for v in self._lore.values())
        return {
            "total_stories": len(self._stories),
            "total_plot_beats": total_beats,
            "total_characters": total_characters,
            "total_dialogue_nodes": total_dialogue,
            "total_lore_entries": total_lore,
            "composition_log_entries": len(self._composition_log),
        }


def get_narrative_composer() -> NarrativeComposer:
    return NarrativeComposer.get_instance()