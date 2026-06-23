"""
SparkLabs Agent - Procedural Story Engine

AI-driven narrative generation system that constructs branching story
graphs, manages character arcs, maintains plot coherence, and builds
world-building lore. Stories are modeled as traversable directed graphs
where each node represents a scene, choice, branch, merge point, or
ending. The engine tracks emotional tone, tension levels, and narrative
arc progression across the entire story structure.

Architecture:
  StoryEngine (Singleton)
    |-- StoryGraph (narrative graph with nodes and arcs)
    |-- PlotNode (scene, choice, branch, merge, or ending)
    |-- CharacterArc (character transformation over time)
    |-- WorldLore (history, factions, locations, rules)

Core Capabilities:
  - Create stories with genre classification and arc tracking
  - Add scenes, choices, branches, and endings to the story graph
  - Traverse the story graph along different narrative paths
  - Manage character arcs with starting/ending states and milestones
  - Build world lore entries with history, factions, and locations
  - Track emotional tone and tension levels across scenes
  - Generate coherent endings based on story state and character arcs
  - Export full story graphs with metadata for external rendering
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

class StoryArc(Enum):
    """The five classical stages of narrative structure."""
    EXPOSITION = "exposition"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"


class StoryGenre(Enum):
    """Broad genre categories for story classification."""
    FANTASY = "fantasy"
    SCI_FI = "sci_fi"
    HORROR = "horror"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    ADVENTURE = "adventure"


class PlotNodeType(Enum):
    """Types of nodes in the story graph."""
    SCENE = "scene"
    CHOICE = "choice"
    BRANCH = "branch"
    MERGE = "merge"
    ENDING = "ending"


class StoryState(Enum):
    """Lifecycle states of a story graph."""
    DRAFT = "draft"
    DRAFTING = "drafting"
    REVIEWING = "reviewing"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# Arc Ordering
# ---------------------------------------------------------------------------

_ARC_ORDER: Dict[StoryArc, int] = {
    StoryArc.EXPOSITION: 0,
    StoryArc.RISING_ACTION: 1,
    StoryArc.CLIMAX: 2,
    StoryArc.FALLING_ACTION: 3,
    StoryArc.RESOLUTION: 4,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PlotNode:
    """A single node in the story graph representing a narrative unit.

    Plot nodes can be scenes (narrative content), choices (decision
    points), branches (alternative paths), merges (convergence points),
    or endings (terminal states). Each node tracks its emotional tone
    and tension level for pacing analysis.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    story_id: str = ""
    node_type: PlotNodeType = PlotNodeType.SCENE
    title: str = ""
    content: str = ""
    choices: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    arc: StoryArc = StoryArc.EXPOSITION
    emotional_tone: float = 0.0
    tension_level: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "story_id": self.story_id,
            "node_type": self.node_type.value,
            "title": self.title,
            "content": self.content[:300],
            "choices": self.choices,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "arc": self.arc.value,
            "emotional_tone": round(self.emotional_tone, 4),
            "tension_level": round(self.tension_level, 4),
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def add_child(self, child_id: str) -> None:
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)

    def remove_child(self, child_id: str) -> bool:
        if child_id in self.children_ids:
            self.children_ids.remove(child_id)
            return True
        return False

    def is_terminal(self) -> bool:
        return self.node_type == PlotNodeType.ENDING


@dataclass
class StoryGraph:
    """A complete narrative graph with nodes, arcs, and metadata.

    The story graph is the core data structure for procedural narrative
    generation. It tracks the root node, current traversal position,
    genre classification, arc progression, and overall story state.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    genre: StoryGenre = StoryGenre.ADVENTURE
    arcs: List[StoryArc] = field(default_factory=lambda: list(StoryArc))
    nodes: Dict[str, PlotNode] = field(default_factory=dict)
    root_node_id: Optional[str] = None
    current_node_id: Optional[str] = None
    state: StoryState = StoryState.DRAFT
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "genre": self.genre.value,
            "arcs": [a.value for a in self.arcs],
            "node_count": len(self.nodes),
            "root_node_id": self.root_node_id,
            "current_node_id": self.current_node_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["nodes"] = [n.to_dict() for n in self.nodes.values()]
        return result

    def get_node(self, node_id: str) -> Optional[PlotNode]:
        return self.nodes.get(node_id)

    def get_root(self) -> Optional[PlotNode]:
        if self.root_node_id is None:
            return None
        return self.nodes.get(self.root_node_id)

    def get_current(self) -> Optional[PlotNode]:
        if self.current_node_id is None:
            return self.get_root()
        return self.nodes.get(self.current_node_id)

    def get_leaf_nodes(self) -> List[PlotNode]:
        return [n for n in self.nodes.values() if not n.children_ids]

    def get_nodes_by_arc(self, arc: StoryArc) -> List[PlotNode]:
        return [n for n in self.nodes.values() if n.arc == arc]

    def get_nodes_by_type(self, node_type: PlotNodeType) -> List[PlotNode]:
        return [n for n in self.nodes.values() if n.node_type == node_type]

    def get_path_to(self, node_id: str) -> List[PlotNode]:
        path: List[PlotNode] = []
        current = self.nodes.get(node_id)
        visited: set = set()
        while current is not None and current.id not in visited:
            visited.add(current.id)
            path.insert(0, current)
            if current.parent_id is None:
                break
            current = self.nodes.get(current.parent_id)
        return path

    def get_all_paths(self) -> List[List[PlotNode]]:
        leaves = self.get_leaf_nodes()
        return [self.get_path_to(leaf.id) for leaf in leaves]

    def get_tension_profile(self) -> List[Dict[str, Any]]:
        profile: List[Dict[str, Any]] = []
        for node in self.nodes.values():
            profile.append({
                "node_id": node.id,
                "title": node.title,
                "arc": node.arc.value,
                "tension": round(node.tension_level, 4),
                "emotional_tone": round(node.emotional_tone, 4),
            })
        profile.sort(key=lambda x: x["tension"])
        return profile

    def get_arc_distribution(self) -> Dict[str, int]:
        distribution: Dict[str, int] = {}
        for node in self.nodes.values():
            key = node.arc.value
            distribution[key] = distribution.get(key, 0) + 1
        return distribution


@dataclass
class CharacterArc:
    """A character's transformation journey across the story.

    Tracks the character's starting state, ending state, the type of
    arc (growth, fall, flat, redemption), and key milestones that mark
    significant turning points in the character's development.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    character_name: str = ""
    starting_state: str = ""
    ending_state: str = ""
    arc_type: str = "growth"
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    story_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "character_name": self.character_name,
            "starting_state": self.starting_state,
            "ending_state": self.ending_state,
            "arc_type": self.arc_type,
            "milestone_count": len(self.milestones),
            "milestones": self.milestones,
            "story_id": self.story_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def add_milestone(self, description: str, node_id: str = "", significance: float = 0.5) -> None:
        self.milestones.append({
            "description": description,
            "node_id": node_id,
            "significance": round(max(0.0, min(1.0, significance)), 4),
            "timestamp": time.time(),
        })
        self.updated_at = time.time()

    def get_progress(self) -> float:
        if not self.milestones:
            return 0.0
        total_significance = sum(m["significance"] for m in self.milestones)
        return min(1.0, total_significance / len(self.milestones))


@dataclass
class WorldLore:
    """World-building knowledge for the story's setting.

    Contains the world's history, faction definitions, location
    descriptions, and the rules that govern the world's internal
    logic (magic systems, technology constraints, social norms).
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_name: str = ""
    history: str = ""
    factions: List[Dict[str, Any]] = field(default_factory=list)
    locations: List[Dict[str, Any]] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    story_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "world_name": self.world_name,
            "history": self.history[:500],
            "factions": self.factions,
            "faction_count": len(self.factions),
            "locations": self.locations,
            "location_count": len(self.locations),
            "rules": self.rules,
            "rule_count": len(self.rules),
            "story_id": self.story_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def add_faction(self, name: str, description: str = "", alignment: str = "neutral") -> None:
        self.factions.append({
            "name": name,
            "description": description,
            "alignment": alignment,
            "added_at": time.time(),
        })
        self.updated_at = time.time()

    def add_location(self, name: str, description: str = "", location_type: str = "general") -> None:
        self.locations.append({
            "name": name,
            "description": description,
            "location_type": location_type,
            "added_at": time.time(),
        })
        self.updated_at = time.time()

    def add_rule(self, rule: str) -> None:
        if rule not in self.rules:
            self.rules.append(rule)
            self.updated_at = time.time()


# ---------------------------------------------------------------------------
# StoryEngine
# ---------------------------------------------------------------------------

class StoryEngine:
    """Thread-safe singleton engine for procedural story generation.

    Manages the full lifecycle of story graphs, character arcs, and
    world lore. Supports story creation, scene addition, branching
    narrative construction, graph traversal, ending generation, and
    comprehensive story state export.
    """

    _instance: Optional["StoryEngine"] = None
    _lock = threading.RLock()

    _MAX_STORIES: int = 200
    _MAX_NODES_PER_STORY: int = 500
    _MAX_CHARACTER_ARCS: int = 2000
    _MAX_WORLD_LORE: int = 2000
    _MAX_TENSION: float = 1.0
    _MIN_TENSION: float = 0.0

    def __init__(self) -> None:
        self._stories: Dict[str, StoryGraph] = {}
        self._character_arcs: Dict[str, CharacterArc] = {}
        self._world_lore_entries: Dict[str, WorldLore] = {}
        self._arcs_by_story: Dict[str, List[str]] = {}
        self._lore_by_story: Dict[str, List[str]] = {}
        self._total_stories_created: int = 0
        self._total_nodes_created: int = 0
        self._total_endings_generated: int = 0
        self._total_arcs_created: int = 0
        self._total_lore_created: int = 0

    @classmethod
    def get_instance(cls) -> "StoryEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Story Lifecycle
    # ------------------------------------------------------------------

    def create_story(
        self,
        title: str = "",
        genre: StoryGenre = StoryGenre.ADVENTURE,
        arcs: Optional[List[StoryArc]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StoryGraph:
        with self._lock:
            self._enforce_max_stories()

            story = StoryGraph(
                title=title or f"Untitled Story {self._total_stories_created + 1}",
                genre=genre,
                arcs=list(arcs) if arcs else list(StoryArc),
                state=StoryState.DRAFT,
                metadata=metadata or {},
            )
            self._stories[story.id] = story
            self._arcs_by_story[story.id] = []
            self._lore_by_story[story.id] = []
            self._total_stories_created += 1
            return story

    def get_story(self, story_id: str) -> Optional[StoryGraph]:
        with self._lock:
            return self._stories.get(story_id)

    def list_stories(
        self,
        state: Optional[StoryState] = None,
        genre: Optional[StoryGenre] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            results = list(self._stories.values())
            if state is not None:
                results = [s for s in results if s.state == state]
            if genre is not None:
                results = [s for s in results if s.genre == genre]
            return [s.to_dict() for s in results]

    def update_story_state(
        self,
        story_id: str,
        new_state: StoryState,
    ) -> Optional[StoryGraph]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return None
            story.state = new_state
            story.updated_at = time.time()
            return story

    # ------------------------------------------------------------------
    # Node Operations
    # ------------------------------------------------------------------

    def add_scene(
        self,
        story_id: str,
        title: str = "",
        content: str = "",
        arc: StoryArc = StoryArc.EXPOSITION,
        emotional_tone: float = 0.0,
        tension_level: float = 0.0,
        parent_id: Optional[str] = None,
    ) -> Optional[PlotNode]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return None
            if story.state in (StoryState.PUBLISHED, StoryState.ARCHIVED):
                return None
            if len(story.nodes) >= self._MAX_NODES_PER_STORY:
                return None

            node = PlotNode(
                story_id=story_id,
                node_type=PlotNodeType.SCENE,
                title=title,
                content=content,
                arc=arc,
                emotional_tone=max(-1.0, min(1.0, emotional_tone)),
                tension_level=max(self._MIN_TENSION, min(self._MAX_TENSION, tension_level)),
            )

            effective_parent = parent_id or story.root_node_id
            if effective_parent is not None:
                parent_node = story.nodes.get(effective_parent)
                if parent_node is not None:
                    node.parent_id = effective_parent
                    parent_node.add_child(node.id)

            story.nodes[node.id] = node
            self._total_nodes_created += 1

            if story.root_node_id is None:
                story.root_node_id = node.id
                story.current_node_id = node.id

            story.state = StoryState.DRAFTING
            story.updated_at = time.time()
            return node

    def add_choice(
        self,
        story_id: str,
        parent_id: str,
        title: str = "",
        content: str = "",
        choice_text: str = "",
        arc: StoryArc = StoryArc.RISING_ACTION,
        emotional_tone: float = 0.0,
        tension_level: float = 0.0,
        choice_options: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[PlotNode]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return None
            if story.state in (StoryState.PUBLISHED, StoryState.ARCHIVED):
                return None
            if len(story.nodes) >= self._MAX_NODES_PER_STORY:
                return None

            parent_node = story.nodes.get(parent_id)
            if parent_node is None:
                return None

            node = PlotNode(
                story_id=story_id,
                node_type=PlotNodeType.CHOICE,
                title=title or f"Choice at {parent_node.title[:30]}",
                content=content,
                choices=choice_text,
                parent_id=parent_id,
                arc=arc,
                emotional_tone=max(-1.0, min(1.0, emotional_tone)),
                tension_level=max(self._MIN_TENSION, min(self._MAX_TENSION, tension_level)),
                metadata={"choice_options": choice_options or []},
            )

            story.nodes[node.id] = node
            parent_node.add_child(node.id)
            self._total_nodes_created += 1
            story.updated_at = time.time()
            return node

    def add_branch(
        self,
        story_id: str,
        parent_id: str,
        title: str = "",
        content: str = "",
        branch_label: str = "",
        arc: StoryArc = StoryArc.RISING_ACTION,
        emotional_tone: float = 0.0,
        tension_level: float = 0.0,
    ) -> Optional[PlotNode]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return None
            if story.state in (StoryState.PUBLISHED, StoryState.ARCHIVED):
                return None
            if len(story.nodes) >= self._MAX_NODES_PER_STORY:
                return None

            parent_node = story.nodes.get(parent_id)
            if parent_node is None:
                return None

            node = PlotNode(
                story_id=story_id,
                node_type=PlotNodeType.BRANCH,
                title=title or f"Branch: {branch_label}",
                content=content,
                parent_id=parent_id,
                arc=arc,
                emotional_tone=max(-1.0, min(1.0, emotional_tone)),
                tension_level=max(self._MIN_TENSION, min(self._MAX_TENSION, tension_level)),
                metadata={"branch_label": branch_label},
            )

            story.nodes[node.id] = node
            parent_node.add_child(node.id)
            self._total_nodes_created += 1
            story.updated_at = time.time()
            return node

    def add_merge(
        self,
        story_id: str,
        parent_ids: List[str],
        title: str = "",
        content: str = "",
        arc: StoryArc = StoryArc.CLIMAX,
        emotional_tone: float = 0.0,
        tension_level: float = 0.5,
    ) -> Optional[PlotNode]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return None
            if story.state in (StoryState.PUBLISHED, StoryState.ARCHIVED):
                return None
            if len(story.nodes) >= self._MAX_NODES_PER_STORY:
                return None

            node = PlotNode(
                story_id=story_id,
                node_type=PlotNodeType.MERGE,
                title=title or "Merge Point",
                content=content,
                parent_id=None,
                arc=arc,
                emotional_tone=max(-1.0, min(1.0, emotional_tone)),
                tension_level=max(self._MIN_TENSION, min(self._MAX_TENSION, tension_level)),
                metadata={"parent_ids": parent_ids},
            )

            valid_parents = 0
            for pid in parent_ids:
                parent_node = story.nodes.get(pid)
                if parent_node is not None:
                    parent_node.add_child(node.id)
                    valid_parents += 1

            if valid_parents == 0:
                return None

            story.nodes[node.id] = node
            self._total_nodes_created += 1
            story.updated_at = time.time()
            return node

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def traverse(
        self,
        story_id: str,
        choice_index: int = 0,
    ) -> Optional[PlotNode]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return None

            current = story.get_current()
            if current is None:
                return None

            if not current.children_ids:
                return None

            if choice_index < 0 or choice_index >= len(current.children_ids):
                return None

            next_id = current.children_ids[choice_index]
            next_node = story.nodes.get(next_id)
            if next_node is None:
                return None

            story.current_node_id = next_id
            story.updated_at = time.time()
            return next_node

    def traverse_to(self, story_id: str, node_id: str) -> Optional[PlotNode]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return None
            node = story.nodes.get(node_id)
            if node is None:
                return None
            story.current_node_id = node_id
            story.updated_at = time.time()
            return node

    def get_available_choices(self, story_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return []
            current = story.get_current()
            if current is None:
                return []

            choices: List[Dict[str, Any]] = []
            for i, child_id in enumerate(current.children_ids):
                child = story.nodes.get(child_id)
                if child is not None:
                    choices.append({
                        "index": i,
                        "node_id": child.id,
                        "title": child.title,
                        "content": child.content[:200],
                        "node_type": child.node_type.value,
                        "arc": child.arc.value,
                    })
            return choices

    # ------------------------------------------------------------------
    # Endings
    # ------------------------------------------------------------------

    def generate_ending(
        self,
        story_id: str,
        parent_id: str,
        title: str = "",
        content: str = "",
        ending_type: str = "resolution",
        emotional_tone: float = 0.0,
        tension_level: float = 0.0,
    ) -> Optional[PlotNode]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return None
            if story.state in (StoryState.PUBLISHED, StoryState.ARCHIVED):
                return None
            if len(story.nodes) >= self._MAX_NODES_PER_STORY:
                return None

            parent_node = story.nodes.get(parent_id)
            if parent_node is None:
                return None

            node = PlotNode(
                story_id=story_id,
                node_type=PlotNodeType.ENDING,
                title=title or "Ending",
                content=content,
                parent_id=parent_id,
                arc=StoryArc.RESOLUTION,
                emotional_tone=max(-1.0, min(1.0, emotional_tone)),
                tension_level=max(self._MIN_TENSION, min(self._MAX_TENSION, tension_level)),
                metadata={"ending_type": ending_type},
            )

            story.nodes[node.id] = node
            parent_node.add_child(node.id)
            self._total_nodes_created += 1
            self._total_endings_generated += 1
            story.updated_at = time.time()
            return node

    def get_all_endings(self, story_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return []
            endings = story.get_nodes_by_type(PlotNodeType.ENDING)
            return [e.to_dict() for e in endings]

    # ------------------------------------------------------------------
    # Character Arcs
    # ------------------------------------------------------------------

    def add_character_arc(
        self,
        story_id: str,
        character_name: str,
        starting_state: str = "",
        ending_state: str = "",
        arc_type: str = "growth",
    ) -> Optional[CharacterArc]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return None
            if len(self._character_arcs) >= self._MAX_CHARACTER_ARCS:
                return None

            arc = CharacterArc(
                character_name=character_name,
                starting_state=starting_state,
                ending_state=ending_state,
                arc_type=arc_type,
                story_id=story_id,
            )
            self._character_arcs[arc.id] = arc
            if story_id in self._arcs_by_story:
                self._arcs_by_story[story_id].append(arc.id)
            self._total_arcs_created += 1
            return arc

    def get_character_arcs(self, story_id: str) -> List[CharacterArc]:
        with self._lock:
            arc_ids = self._arcs_by_story.get(story_id, [])
            return [self._character_arcs[aid] for aid in arc_ids if aid in self._character_arcs]

    def add_milestone_to_arc(
        self,
        arc_id: str,
        description: str,
        node_id: str = "",
        significance: float = 0.5,
    ) -> Optional[CharacterArc]:
        with self._lock:
            arc = self._character_arcs.get(arc_id)
            if arc is None:
                return None
            arc.add_milestone(description, node_id, significance)
            return arc

    # ------------------------------------------------------------------
    # World Lore
    # ------------------------------------------------------------------

    def add_world_lore(
        self,
        story_id: str,
        world_name: str = "",
        history: str = "",
        factions: Optional[List[Dict[str, Any]]] = None,
        locations: Optional[List[Dict[str, Any]]] = None,
        rules: Optional[List[str]] = None,
    ) -> Optional[WorldLore]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return None
            if len(self._world_lore_entries) >= self._MAX_WORLD_LORE:
                return None

            lore = WorldLore(
                world_name=world_name or f"World of {story.title}",
                history=history,
                factions=list(factions) if factions else [],
                locations=list(locations) if locations else [],
                rules=list(rules) if rules else [],
                story_id=story_id,
            )
            self._world_lore_entries[lore.id] = lore
            if story_id in self._lore_by_story:
                self._lore_by_story[story_id].append(lore.id)
            self._total_lore_created += 1
            return lore

    def get_world_lore(self, story_id: str) -> List[WorldLore]:
        with self._lock:
            lore_ids = self._lore_by_story.get(story_id, [])
            return [self._world_lore_entries[lid] for lid in lore_ids if lid in self._world_lore_entries]

    def add_faction_to_lore(
        self,
        lore_id: str,
        name: str,
        description: str = "",
        alignment: str = "neutral",
    ) -> Optional[WorldLore]:
        with self._lock:
            lore = self._world_lore_entries.get(lore_id)
            if lore is None:
                return None
            lore.add_faction(name, description, alignment)
            return lore

    def add_location_to_lore(
        self,
        lore_id: str,
        name: str,
        description: str = "",
        location_type: str = "general",
    ) -> Optional[WorldLore]:
        with self._lock:
            lore = self._world_lore_entries.get(lore_id)
            if lore is None:
                return None
            lore.add_location(name, description, location_type)
            return lore

    def add_rule_to_lore(self, lore_id: str, rule: str) -> Optional[WorldLore]:
        with self._lock:
            lore = self._world_lore_entries.get(lore_id)
            if lore is None:
                return None
            lore.add_rule(rule)
            return lore

    # ------------------------------------------------------------------
    # Story Analysis
    # ------------------------------------------------------------------

    def analyze_story(self, story_id: str) -> Dict[str, Any]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return {}

            arcs = story.get_arc_distribution()
            endings = story.get_nodes_by_type(PlotNodeType.ENDING)
            choices = story.get_nodes_by_type(PlotNodeType.CHOICE)
            branches = story.get_nodes_by_type(PlotNodeType.BRANCH)
            tension_profile = story.get_tension_profile()

            character_arcs = self.get_character_arcs(story_id)
            lore_entries = self.get_world_lore(story_id)

            all_paths = story.get_all_paths()
            path_lengths = [len(p) for p in all_paths]

            avg_tension = 0.0
            avg_tone = 0.0
            if story.nodes:
                avg_tension = sum(n.tension_level for n in story.nodes.values()) / len(story.nodes)
                avg_tone = sum(n.emotional_tone for n in story.nodes.values()) / len(story.nodes)

            return {
                "story_id": story_id,
                "title": story.title,
                "genre": story.genre.value,
                "state": story.state.value,
                "total_nodes": len(story.nodes),
                "total_scenes": len(story.nodes) - len(endings) - len(choices) - len(branches),
                "total_choices": len(choices),
                "total_branches": len(branches),
                "total_endings": len(endings),
                "total_paths": len(all_paths),
                "avg_path_length": round(sum(path_lengths) / len(path_lengths), 2) if path_lengths else 0,
                "max_path_length": max(path_lengths) if path_lengths else 0,
                "arc_distribution": arcs,
                "avg_tension": round(avg_tension, 4),
                "avg_emotional_tone": round(avg_tone, 4),
                "tension_profile": tension_profile[:20],
                "character_arcs": len(character_arcs),
                "world_lore_entries": len(lore_entries),
                "story_age_seconds": round(time.time() - story.created_at, 2),
            }

    def export_story(self, story_id: str) -> Dict[str, Any]:
        with self._lock:
            story = self._stories.get(story_id)
            if story is None:
                return {}

            result = story.to_full_dict()
            result["character_arcs"] = [
                a.to_dict() for a in self.get_character_arcs(story_id)
            ]
            result["world_lore"] = [
                l.to_dict() for l in self.get_world_lore(story_id)
            ]
            result["analysis"] = self.analyze_story(story_id)
            return result

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            genre_dist: Dict[str, int] = {}
            state_dist: Dict[str, int] = {}
            for story in self._stories.values():
                g = story.genre.value
                genre_dist[g] = genre_dist.get(g, 0) + 1
                s = story.state.value
                state_dist[s] = state_dist.get(s, 0) + 1

            total_nodes = sum(len(s.nodes) for s in self._stories.values())
            total_endings = sum(
                len(s.get_nodes_by_type(PlotNodeType.ENDING))
                for s in self._stories.values()
            )

            return {
                "total_stories_created": self._total_stories_created,
                "total_stories_stored": len(self._stories),
                "total_nodes_created": self._total_nodes_created,
                "total_nodes_active": total_nodes,
                "total_endings_generated": self._total_endings_generated,
                "total_endings_active": total_endings,
                "total_character_arcs_created": self._total_arcs_created,
                "total_character_arcs_stored": len(self._character_arcs),
                "total_world_lore_created": self._total_lore_created,
                "total_world_lore_stored": len(self._world_lore_entries),
                "genre_distribution": genre_dist,
                "state_distribution": state_dist,
                "max_stories": self._MAX_STORIES,
                "max_nodes_per_story": self._MAX_NODES_PER_STORY,
            }

    def reset(self) -> None:
        with self._lock:
            self._stories.clear()
            self._character_arcs.clear()
            self._world_lore_entries.clear()
            self._arcs_by_story.clear()
            self._lore_by_story.clear()
            self._total_stories_created = 0
            self._total_nodes_created = 0
            self._total_endings_generated = 0
            self._total_arcs_created = 0
            self._total_lore_created = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _enforce_max_stories(self) -> None:
        if len(self._stories) >= self._MAX_STORIES:
            sorted_stories = sorted(
                self._stories.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._stories) - self._MAX_STORIES + 1
            for story_id, story in sorted_stories[:overflow]:
                self._stories.pop(story_id, None)
                for arc_id in self._arcs_by_story.pop(story_id, []):
                    self._character_arcs.pop(arc_id, None)
                for lore_id in self._lore_by_story.pop(story_id, []):
                    self._world_lore_entries.pop(lore_id, None)


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_story_engine() -> StoryEngine:
    """Return the singleton StoryEngine instance."""
    return StoryEngine.get_instance()