"""
SparkLabs Agent - Dynamic Narrative Adapter

Real-time narrative adaptation engine that responds to player behavior.
Dynamically adjusts story elements, character arcs, and plot branches
based on player actions, maintaining narrative coherence while allowing
meaningful player agency.

Architecture:
  AgentDynamicNarrative (Singleton)
    |-- Narrative Graph Builder (DAG construction from story templates)
    |-- Player Action Processor (impact computation from player behavior)
    |-- Story Adapter (real-time narrative element modification)
    |-- Character Arc Tracker (character development progression)
    |-- Coherence Evaluator (story consistency scoring)
    |-- Branch Manager (multi-path narrative branching)
    |-- Outcome Predictor (forward simulation of narrative possibilities)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple


# =============================================================================
# Enums
# =============================================================================


class NarrativeNodeType(Enum):
    """Types of nodes in the narrative graph."""
    EXPOSITION = "exposition"
    CONFLICT = "conflict"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    BRANCH = "branch"
    FORK = "fork"
    MERGE = "merge"
    EPILOGUE = "epilogue"


class PlotAdaptation(Enum):
    """Strategies for adapting the narrative in response to player actions."""
    INTENSIFY = "intensify"
    DEFUSE = "defuse"
    REDIRECT = "redirect"
    DELAY = "delay"
    ACCELERATE = "accelerate"
    REPLACE = "replace"
    ENRICH = "enrich"
    SIMPLIFY = "simplify"


class CharacterArcStage(Enum):
    """Stages in a character's developmental arc."""
    INTRODUCTION = "introduction"
    DEVELOPMENT = "development"
    CRISIS = "crisis"
    TRANSFORMATION = "transformation"
    RESOLUTION = "resolution"
    DEPARTURE = "departure"


class PlayerImpactLevel(Enum):
    """Magnitude of player impact on the narrative."""
    MINOR = "minor"
    NOTICEABLE = "noticeable"
    SIGNIFICANT = "significant"
    MAJOR = "major"
    WORLD_CHANGING = "world_changing"


class NarrativeMood(Enum):
    """Emotional tone of the current narrative segment."""
    TENSE = "tense"
    JOYFUL = "joyful"
    MYSTERIOUS = "mysterious"
    TRAGIC = "tragic"
    HOPEFUL = "hopeful"
    DARK = "dark"
    COMIC = "comic"
    SERENE = "serene"


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class NarrativeNode:
    """A single node in the narrative directed acyclic graph."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_type: NarrativeNodeType = NarrativeNodeType.EXPOSITION
    title: str = ""
    content: str = ""
    conditions: Dict[str, Any] = field(default_factory=dict)
    possible_next: List[str] = field(default_factory=list)
    adaptation_rules: Dict[str, Any] = field(default_factory=dict)
    emotional_weight: float = 0.0
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "title": self.title,
            "content": self.content,
            "conditions": self.conditions,
            "possible_next": self.possible_next,
            "adaptation_rules": self.adaptation_rules,
            "emotional_weight": round(self.emotional_weight, 2),
            "priority": self.priority,
            "metadata": self.metadata,
        }


@dataclass
class PlayerActionImpact:
    """Computed impact of a player action on the narrative."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action_name: str = ""
    impact_level: PlayerImpactLevel = PlayerImpactLevel.MINOR
    affected_nodes: List[str] = field(default_factory=list)
    narrative_shifts: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_name": self.action_name,
            "impact_level": self.impact_level.value,
            "affected_nodes": self.affected_nodes,
            "narrative_shifts": self.narrative_shifts,
            "description": self.description,
            "timestamp": self.timestamp,
        }


@dataclass
class CharacterArc:
    """Developmental trajectory of a story character."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    character_name: str = ""
    current_stage: CharacterArcStage = CharacterArcStage.INTRODUCTION
    stage_progress: float = 0.0
    arc_trajectory: List[str] = field(default_factory=list)
    key_events: List[str] = field(default_factory=list)
    emotional_state: Dict[str, float] = field(default_factory=dict)
    relationship_changes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "character_name": self.character_name,
            "current_stage": self.current_stage.value,
            "stage_progress": round(self.stage_progress, 2),
            "arc_trajectory": self.arc_trajectory,
            "key_events": self.key_events,
            "emotional_state": self.emotional_state,
            "relationship_changes": self.relationship_changes,
        }


@dataclass
class NarrativeState:
    """Snapshot of the current narrative condition."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    current_node_id: str = ""
    mood: NarrativeMood = NarrativeMood.TENSE
    tension_level: float = 0.0
    player_agency_score: float = 0.0
    active_threads: int = 0
    completed_threads: int = 0
    branching_depth: int = 0
    story_coherence: float = 0.0
    player_impacts: List[PlayerActionImpact] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "current_node_id": self.current_node_id,
            "mood": self.mood.value,
            "tension_level": round(self.tension_level, 2),
            "player_agency_score": round(self.player_agency_score, 2),
            "active_threads": self.active_threads,
            "completed_threads": self.completed_threads,
            "branching_depth": self.branching_depth,
            "story_coherence": round(self.story_coherence, 2),
            "player_impacts": [p.to_dict() for p in self.player_impacts],
        }


# =============================================================================
# Story Template Definitions
# =============================================================================

_STORY_TEMPLATES: Dict[str, List[Tuple[str, NarrativeNodeType, float]]] = {
    "hero_journey": [
        ("The ordinary world is established.", NarrativeNodeType.EXPOSITION, 0.1),
        ("A call to adventure disrupts the status quo.", NarrativeNodeType.CONFLICT, 0.3),
        ("Allies gather and the journey begins.", NarrativeNodeType.BRANCH, 0.4),
        ("The first major obstacle is encountered.", NarrativeNodeType.CONFLICT, 0.5),
        ("The darkest hour arrives — all seems lost.", NarrativeNodeType.CLIMAX, 0.9),
        ("A revelation turns the tide.", NarrativeNodeType.FORK, 0.7),
        ("The final confrontation unfolds.", NarrativeNodeType.CLIMAX, 1.0),
        ("The world is transformed by the outcome.", NarrativeNodeType.RESOLUTION, 0.3),
        ("Loose threads are tied and farewells are said.", NarrativeNodeType.EPILOGUE, 0.1),
    ],
    "mystery": [
        ("A puzzling event sets the investigation in motion.", NarrativeNodeType.EXPOSITION, 0.2),
        ("Clues are gathered and suspects emerge.", NarrativeNodeType.CONFLICT, 0.4),
        ("A red herring leads the investigation astray.", NarrativeNodeType.BRANCH, 0.5),
        ("A breakthrough discovery reorients the case.", NarrativeNodeType.FORK, 0.6),
        ("The true culprit is confronted.", NarrativeNodeType.CLIMAX, 0.9),
        ("The mystery is resolved — but at what cost?", NarrativeNodeType.RESOLUTION, 0.4),
        ("The aftermath reveals lingering questions.", NarrativeNodeType.EPILOGUE, 0.2),
    ],
    "tragedy": [
        ("A character of noble standing is introduced.", NarrativeNodeType.EXPOSITION, 0.1),
        ("A fatal flaw begins to surface.", NarrativeNodeType.CONFLICT, 0.3),
        ("Choices narrow and the trap tightens.", NarrativeNodeType.BRANCH, 0.5),
        ("The point of no return is crossed.", NarrativeNodeType.FORK, 0.7),
        ("The inevitable catastrophe strikes.", NarrativeNodeType.CLIMAX, 1.0),
        ("Consequences cascade through the world.", NarrativeNodeType.RESOLUTION, 0.6),
        ("Survivors reckon with the aftermath.", NarrativeNodeType.EPILOGUE, 0.3),
    ],
}

# Impact magnitude multipliers for each PlayerImpactLevel
_IMPACT_MULTIPLIERS: Dict[PlayerImpactLevel, float] = {
    PlayerImpactLevel.MINOR: 0.1,
    PlayerImpactLevel.NOTICEABLE: 0.25,
    PlayerImpactLevel.SIGNIFICANT: 0.45,
    PlayerImpactLevel.MAJOR: 0.7,
    PlayerImpactLevel.WORLD_CHANGING: 0.95,
}

# Stage transition order for character arcs
_STAGE_ORDER: List[CharacterArcStage] = [
    CharacterArcStage.INTRODUCTION,
    CharacterArcStage.DEVELOPMENT,
    CharacterArcStage.CRISIS,
    CharacterArcStage.TRANSFORMATION,
    CharacterArcStage.RESOLUTION,
    CharacterArcStage.DEPARTURE,
]

# Mood-to-tension base mapping
_MOOD_TENSION: Dict[NarrativeMood, float] = {
    NarrativeMood.TENSE: 0.7,
    NarrativeMood.JOYFUL: 0.15,
    NarrativeMood.MYSTERIOUS: 0.45,
    NarrativeMood.TRAGIC: 0.8,
    NarrativeMood.HOPEFUL: 0.2,
    NarrativeMood.DARK: 0.85,
    NarrativeMood.COMIC: 0.1,
    NarrativeMood.SERENE: 0.05,
}


# =============================================================================
# AgentDynamicNarrative (Singleton)
# =============================================================================


class AgentDynamicNarrative:
    """
    Real-time narrative adaptation engine.

    Dynamically adjusts story elements, character arcs, and plot branches
    in response to player actions, maintaining narrative coherence while
    preserving meaningful player agency.
    """

    _instance: Optional["AgentDynamicNarrative"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "AgentDynamicNarrative":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentDynamicNarrative":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # Narrative graph: node_id -> NarrativeNode
        self._graph: Dict[str, NarrativeNode] = {}

        # Thread tracking
        self._active_threads: List[str] = []
        self._completed_threads: List[str] = []

        # Character arcs: character_name -> CharacterArc
        self._characters: Dict[str, CharacterArc] = {}

        # Player action history (bounded)
        self._player_actions: Deque[PlayerActionImpact] = deque(maxlen=200)

        # Current narrative state
        self._narrative_state: NarrativeState = NarrativeState()

        # Adaptation history for auditing
        self._adaptation_history: List[Dict[str, Any]] = []

        # Statistics
        self._stats: Dict[str, Any] = {
            "total_nodes_created": 0,
            "total_adaptations": 0,
            "total_player_actions": 0,
            "adaptation_by_type": {pt.value: 0 for pt in PlotAdaptation},
            "mood_distribution": {m.value: 0.0 for m in NarrativeMood},
        }

    # ------------------------------------------------------------------
    # Narrative Graph Building
    # ------------------------------------------------------------------

    def build_narrative_graph(
        self,
        root_story: str = "hero_journey",
        branching_factor: int = 2,
        max_depth: int = 10,
    ) -> str:
        """
        Build the initial narrative directed acyclic graph from a story
        template. Returns the root node ID.
        """
        with self._lock:
            self._graph.clear()
            self._active_threads.clear()
            self._completed_threads.clear()

            template = _STORY_TEMPLATES.get(root_story, _STORY_TEMPLATES["hero_journey"])
            if max_depth < len(template):
                template = template[:max_depth]

            nodes: List[NarrativeNode] = []
            for i, (content, node_type, emotional_weight) in enumerate(template):
                node = NarrativeNode(
                    node_type=node_type,
                    title=f"{root_story.replace('_', ' ').title()} — Beat {i + 1}",
                    content=content,
                    emotional_weight=emotional_weight,
                    priority=i,
                    conditions={},
                    possible_next=[],
                    metadata={"template": root_story, "depth": i},
                )
                self._graph[node.id] = node
                nodes.append(node)
                self._stats["total_nodes_created"] += 1

            # Link nodes sequentially as base path
            for i in range(len(nodes) - 1):
                nodes[i].possible_next.append(nodes[i + 1].id)

            # Add branching at mid-story fork/branch nodes
            branch_count = min(branching_factor, 3)
            for i in range(len(nodes)):
                ntype = nodes[i].node_type
                if ntype in (NarrativeNodeType.BRANCH, NarrativeNodeType.FORK):
                    current_depth = i
                    if current_depth + 1 < max_depth:
                        for b in range(branch_count - 1):
                            branch_node = NarrativeNode(
                                node_type=NarrativeNodeType.BRANCH if b % 2 == 0 else NarrativeNodeType.CONFLICT,
                                title=f"Branch {b + 1} from Beat {i + 1}",
                                content=f"Alternate path diverging from beat {i + 1}.",
                                emotional_weight=nodes[i].emotional_weight + random.uniform(-0.1, 0.1),
                                priority=nodes[i].priority + 1,
                                metadata={"parent_beat": i + 1, "branch_index": b},
                            )
                            self._graph[branch_node.id] = branch_node
                            nodes[i].possible_next.append(branch_node.id)
                            self._stats["total_nodes_created"] += 1

                            # Bridge branch back to merge point
                            merge_target = nodes[i + 2] if i + 2 < len(nodes) else nodes[-1]
                            branch_node.possible_next.append(merge_target.id)

            # Set root node
            root_id = nodes[0].id

            # Initialize narrative state
            self._narrative_state = NarrativeState(
                current_node_id=root_id,
                mood=NarrativeMood.TENSE,
                tension_level=nodes[0].emotional_weight,
                player_agency_score=0.5,
                active_threads=1,
                completed_threads=0,
                branching_depth=0,
                story_coherence=0.95,
            )
            self._active_threads.append(root_id)

            return root_id

    # ------------------------------------------------------------------
    # Player Action Processing
    # ------------------------------------------------------------------

    def process_player_action(
        self,
        action_name: str,
        context: Optional[Dict[str, Any]] = None,
        intensity: float = 0.5,
    ) -> PlayerActionImpact:
        """
        Process a player action and compute its narrative impact.
        Intensity in [0.0, 1.0] scales the impact magnitude.
        """
        intensity = max(0.0, min(1.0, intensity))

        # Determine impact level from intensity
        if intensity < 0.15:
            impact_level = PlayerImpactLevel.MINOR
        elif intensity < 0.35:
            impact_level = PlayerImpactLevel.NOTICEABLE
        elif intensity < 0.55:
            impact_level = PlayerImpactLevel.SIGNIFICANT
        elif intensity < 0.8:
            impact_level = PlayerImpactLevel.MAJOR
        else:
            impact_level = PlayerImpactLevel.WORLD_CHANGING

        multiplier = _IMPACT_MULTIPLIERS[impact_level]

        # Identify affected nodes (current node and its descendants)
        current_id = self._narrative_state.current_node_id
        affected: List[str] = [current_id]
        visited: set = set()
        queue: Deque[str] = deque([current_id])
        while queue:
            nid = queue.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            node = self._graph.get(nid)
            if node:
                for next_id in node.possible_next:
                    if next_id not in visited:
                        affected.append(next_id)
                        queue.append(next_id)

        # Compute narrative shifts
        tension_shift = (random.uniform(-1.0, 1.0)) * multiplier * intensity
        agency_shift = (random.uniform(0.0, 1.0)) * multiplier * intensity
        mood_shift = random.uniform(-0.5, 0.5) * multiplier * intensity

        narrative_shifts = {
            "tension_delta": round(tension_shift, 3),
            "agency_delta": round(agency_shift, 3),
            "mood_delta": round(mood_shift, 3),
            "coherence_delta": round(-abs(tension_shift) * 0.3 + multiplier * 0.1, 3),
        }

        impact = PlayerActionImpact(
            action_name=action_name,
            impact_level=impact_level,
            affected_nodes=affected,
            narrative_shifts=narrative_shifts,
            description=f"Player performed '{action_name}' with intensity {intensity:.2f} "
            f"({impact_level.value} impact).",
        )

        # Update narrative state
        new_tension = max(0.0, min(1.0, self._narrative_state.tension_level + tension_shift))
        new_agency = max(0.0, min(1.0, self._narrative_state.player_agency_score + agency_shift))
        new_coherence = max(0.0, min(1.0, self._narrative_state.story_coherence + narrative_shifts["coherence_delta"]))

        self._narrative_state.tension_level = new_tension
        self._narrative_state.player_agency_score = new_agency
        self._narrative_state.story_coherence = new_coherence

        # Shift mood if the shift is significant
        if abs(mood_shift) > 0.3:
            moods = list(NarrativeMood)
            current_idx = moods.index(self._narrative_state.mood)
            new_idx = (current_idx + int(mood_shift * 3)) % len(moods)
            self._narrative_state.mood = moods[new_idx]

        # Record
        impact_list = self._narrative_state.player_impacts
        impact_list.append(impact)
        if len(impact_list) > 50:
            self._narrative_state.player_impacts = impact_list[-50:]

        self._player_actions.append(impact)
        self._stats["total_player_actions"] += 1

        return impact

    # ------------------------------------------------------------------
    # Narrative Adaptation
    # ------------------------------------------------------------------

    def adapt_narrative(self, impact: PlayerActionImpact) -> List[NarrativeNode]:
        """
        Dynamically adapt the story based on a player impact.
        Returns the modified narrative nodes.
        """
        with self._lock:
            modified: List[NarrativeNode] = []
            multiplier = _IMPACT_MULTIPLIERS.get(impact.impact_level, 0.1)

            # Select adaptation strategy based on impact characteristics
            tension_delta = impact.narrative_shifts.get("tension_delta", 0.0)

            if abs(tension_delta) > 0.3:
                adaptation = PlotAdaptation.INTENSIFY if tension_delta > 0 else PlotAdaptation.DEFUSE
            elif impact.impact_level in (PlayerImpactLevel.MAJOR, PlayerImpactLevel.WORLD_CHANGING):
                adaptation = PlotAdaptation.REDIRECT
            elif random.random() < 0.3:
                adaptation = PlotAdaptation.ENRICH
            else:
                adaptation = PlotAdaptation.ACCELERATE

            self._stats["total_adaptations"] += 1
            self._stats["adaptation_by_type"][adaptation.value] += 1

            # Apply adaptation to affected nodes
            for node_id in impact.affected_nodes[:10]:
                node = self._graph.get(node_id)
                if node is None:
                    continue

                if adaptation == PlotAdaptation.INTENSIFY:
                    node.emotional_weight = min(1.0, node.emotional_weight + multiplier * 0.25)
                    node.priority += 1
                    node.adaptation_rules["intensified"] = True

                elif adaptation == PlotAdaptation.DEFUSE:
                    node.emotional_weight = max(0.0, node.emotional_weight - multiplier * 0.2)
                    node.content = node.content.replace("confrontation", "tension")
                    node.adaptation_rules["defused"] = True

                elif adaptation == PlotAdaptation.REDIRECT:
                    old_content = node.content
                    node.content = f"[Redirected] {old_content}"
                    node.adaptation_rules["redirected"] = True
                    node.metadata["redirect_source"] = impact.action_name

                elif adaptation == PlotAdaptation.ACCELERATE:
                    node.priority = max(0, node.priority - 1)
                    node.emotional_weight = min(1.0, node.emotional_weight + 0.1)
                    node.adaptation_rules["accelerated"] = True

                elif adaptation == PlotAdaptation.ENRICH:
                    enrichment = f"Enriched by player action: {impact.action_name}."
                    node.content = f"{node.content} {enrichment}"
                    node.adaptation_rules["enriched"] = True

                elif adaptation == PlotAdaptation.SIMPLIFY:
                    node.content = node.content.split(".")[0] + "."
                    node.adaptation_rules["simplified"] = True

                elif adaptation == PlotAdaptation.REPLACE:
                    node.content = f"New direction driven by player: {impact.action_name}."
                    node.adaptation_rules["replaced"] = True

                elif adaptation == PlotAdaptation.DELAY:
                    node.priority += 2
                    node.adaptation_rules["delayed"] = True

                modified.append(node)

            # Log adaptation
            self._adaptation_history.append({
                "adaptation": adaptation.value,
                "impact_id": impact.id,
                "modified_count": len(modified),
                "timestamp": _time_module.time(),
            })

            return modified

    # ------------------------------------------------------------------
    # Narrative Advancement
    # ------------------------------------------------------------------

    def advance_narrative(self, choice_id: str = "") -> NarrativeNode:
        """
        Advance the story to the next node. If choice_id is provided,
        follow that specific branch; otherwise auto-select.
        """
        current_id = self._narrative_state.current_node_id
        current_node = self._graph.get(current_id)

        if current_node is None:
            # Initialize fresh
            root_id = self.build_narrative_graph()
            return self._graph[root_id]

        next_options = current_node.possible_next

        if not next_options:
            # End of graph reached
            self._completed_threads.append(current_id)
            self._narrative_state.completed_threads += 1
            self._narrative_state.active_threads = max(0, self._narrative_state.active_threads - 1)
            return current_node

        # Select next node
        next_id: str
        if choice_id and choice_id in next_options:
            next_id = choice_id
        else:
            # Auto-select: prefer highest priority, break ties with emotional weight
            best = next_options[0]
            best_node = self._graph.get(best)
            for nid in next_options[1:]:
                candidate = self._graph.get(nid)
                if candidate and best_node:
                    if candidate.priority > best_node.priority:
                        best = nid
                        best_node = candidate
                    elif candidate.priority == best_node.priority:
                        if candidate.emotional_weight > best_node.emotional_weight:
                            best = nid
                            best_node = candidate
            next_id = best

        next_node = self._graph.get(next_id)
        if next_node is None:
            return current_node

        # Update state
        self._narrative_state.current_node_id = next_id
        self._narrative_state.tension_level = (
            self._narrative_state.tension_level * 0.7 + next_node.emotional_weight * 0.3
        )
        self._narrative_state.branching_depth = max(
            self._narrative_state.branching_depth,
            next_node.metadata.get("depth", 0),
        )

        # Update active threads count from branches
        live_count = sum(1 for n in self._graph.values() if n.possible_next)
        self._narrative_state.active_threads = live_count

        return next_node

    # ------------------------------------------------------------------
    # Character Arc Tracking
    # ------------------------------------------------------------------

    def track_character_arc(
        self,
        character_name: str,
        event_description: str,
        emotional_impact: Optional[Dict[str, float]] = None,
    ) -> CharacterArc:
        """
        Update or initialize a character's developmental arc with a new event.
        Returns the updated CharacterArc.
        """
        with self._lock:
            arc = self._characters.get(character_name)

            if arc is None:
                arc = CharacterArc(
                    character_name=character_name,
                    current_stage=CharacterArcStage.INTRODUCTION,
                    stage_progress=0.0,
                    arc_trajectory=[CharacterArcStage.INTRODUCTION.value],
                    key_events=[],
                    emotional_state={
                        "joy": 0.5,
                        "fear": 0.3,
                        "anger": 0.2,
                        "sadness": 0.1,
                        "trust": 0.5,
                        "anticipation": 0.4,
                    },
                    relationship_changes=[],
                )
                self._characters[character_name] = arc

            # Record the event
            arc.key_events.append(event_description)

            # Apply emotional impact
            if emotional_impact:
                for emotion, delta in emotional_impact.items():
                    current = arc.emotional_state.get(emotion, 0.5)
                    arc.emotional_state[emotion] = max(0.0, min(1.0, current + delta))

            # Advance stage progress
            progress_increment = 0.05 + random.uniform(0.02, 0.08)
            arc.stage_progress = min(1.0, arc.stage_progress + progress_increment)

            # Transition to next stage when progress exceeds threshold
            if arc.stage_progress >= 1.0:
                current_idx = _STAGE_ORDER.index(arc.current_stage)
                if current_idx < len(_STAGE_ORDER) - 1:
                    arc.current_stage = _STAGE_ORDER[current_idx + 1]
                    arc.stage_progress = 0.0
                    arc.arc_trajectory.append(arc.current_stage.value)

            # Detect relationship changes from emotional shifts
            if emotional_impact:
                trust_change = emotional_impact.get("trust", 0.0)
                if abs(trust_change) > 0.2:
                    direction = "grew closer to" if trust_change > 0 else "grew distant from"
                    arc.relationship_changes.append(
                        f"{character_name} {direction} others ({event_description})"
                    )

            # Trim events
            if len(arc.key_events) > 100:
                arc.key_events = arc.key_events[-75:]
            if len(arc.relationship_changes) > 50:
                arc.relationship_changes = arc.relationship_changes[-30:]

            return arc

    # ------------------------------------------------------------------
    # Story Coherence
    # ------------------------------------------------------------------

    def evaluate_story_coherence(self) -> float:
        """
        Calculate the overall story coherence score.
        Scored in [0.0, 1.0] considering graph connectivity, adaptation
        consistency, and character arc alignment.
        """
        with self._lock:
            if not self._graph:
                return 0.0

            # Connectivity score: fraction of nodes reachable from root
            root_id = self._narrative_state.current_node_id
            reachable: set = set()
            queue: Deque[str] = deque()
            if root_id and root_id in self._graph:
                queue.append(root_id)

            while queue:
                nid = queue.popleft()
                if nid in reachable:
                    continue
                reachable.add(nid)
                node = self._graph.get(nid)
                if node:
                    for next_id in node.possible_next:
                        if next_id not in reachable:
                            queue.append(next_id)

            connectivity = len(reachable) / len(self._graph) if self._graph else 1.0

            # Adaptation stability: recent adaptations should not conflict
            recent_adaptations = self._adaptation_history[-20:]
            adaptation_score = 1.0
            if len(recent_adaptations) >= 2:
                types_count: Dict[str, int] = {}
                for entry in recent_adaptations:
                    atype = entry["adaptation"]
                    types_count[atype] = types_count.get(atype, 0) + 1
                # Penalize rapid switching between conflicting adaptations
                conflicting_pairs = [("intensify", "defuse"), ("accelerate", "delay"),
                                     ("enrich", "simplify"), ("replace", "enrich")]
                conflict_count = 0
                for a, b in conflicting_pairs:
                    conflict_count += min(types_count.get(a, 0), types_count.get(b, 0))
                adaptation_score = max(0.3, 1.0 - conflict_count * 0.1)

            # Character arc alignment
            char_score = 1.0
            if self._characters:
                progressed = sum(
                    1 for c in self._characters.values()
                    if c.stage_progress > 0.3
                )
                char_score = progressed / len(self._characters)

            coherence = (
                connectivity * 0.35
                + adaptation_score * 0.35
                + char_score * 0.3
            )

            self._narrative_state.story_coherence = round(coherence, 2)
            return round(coherence, 2)

    # ------------------------------------------------------------------
    # Branch Access
    # ------------------------------------------------------------------

    def get_available_branches(self) -> List[NarrativeNode]:
        """Get the currently available narrative branches."""
        current_id = self._narrative_state.current_node_id
        current_node = self._graph.get(current_id)

        if current_node is None:
            return []

        branches: List[NarrativeNode] = []
        for next_id in current_node.possible_next:
            node = self._graph.get(next_id)
            if node:
                branches.append(node)

        return branches

    # ------------------------------------------------------------------
    # Outcome Prediction
    # ------------------------------------------------------------------

    def predict_narrative_outcomes(self, depth: int = 3) -> List[Dict[str, Any]]:
        """
        Predict possible narrative outcomes by forward-simulating
        the graph up to the given depth.
        """
        current_id = self._narrative_state.current_node_id
        if current_id not in self._graph:
            return []

        outcomes: List[Dict[str, Any]] = []

        def _simulate(nid: str, remaining: int, path: List[str], cumulative_tension: float):
            if remaining <= 0 or nid not in self._graph:
                node = self._graph.get(nid)
                resolution_type = "incomplete" if remaining <= 0 else "terminal"
                outcomes.append({
                    "terminal_node_id": nid,
                    "path_length": len(path),
                    "path": path[:],
                    "final_tension": round(cumulative_tension, 2),
                    "resolution_type": resolution_type,
                    "terminal_title": node.title if node else "",
                })
                return

            node = self._graph.get(nid)
            if node is None:
                return

            new_path = path + [nid]
            new_tension = cumulative_tension + node.emotional_weight

            if not node.possible_next:
                outcomes.append({
                    "terminal_node_id": nid,
                    "path_length": len(new_path),
                    "path": new_path,
                    "final_tension": round(new_tension / max(len(new_path), 1), 2),
                    "resolution_type": "terminal",
                    "terminal_title": node.title,
                })
                return

            for next_id in node.possible_next[:3]:
                _simulate(next_id, remaining - 1, new_path, new_tension)

            if not node.possible_next:
                outcomes.append({
                    "terminal_node_id": nid,
                    "path_length": len(new_path),
                    "path": new_path,
                    "final_tension": round(new_tension / max(len(new_path), 1), 2),
                    "resolution_type": "dead_end",
                    "terminal_title": node.title,
                })

        _simulate(current_id, depth, [], 0.0)

        # Sort by final tension, descending
        outcomes.sort(key=lambda o: o["final_tension"], reverse=True)
        return outcomes

    # ------------------------------------------------------------------
    # State Access
    # ------------------------------------------------------------------

    def get_narrative_state(self) -> NarrativeState:
        """Get the current narrative snapshot."""
        self.evaluate_story_coherence()
        return self._narrative_state

    # ------------------------------------------------------------------
    # Status & Reporting
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Comprehensive status of the dynamic narrative engine."""
        with self._lock:
            self.evaluate_story_coherence()

            # Compute mood distribution from graph nodes
            mood_dist: Dict[str, float] = {m.value: 0.0 for m in NarrativeMood}
            if self._graph:
                for node in self._graph.values():
                    # Classify node weight into a mood
                    if node.emotional_weight > 0.7:
                        mood_dist[NarrativeMood.DARK.value] += 1
                    elif node.emotional_weight > 0.5:
                        mood_dist[NarrativeMood.TENSE.value] += 1
                    elif node.emotional_weight > 0.3:
                        mood_dist[NarrativeMood.MYSTERIOUS.value] += 1
                    elif node.emotional_weight > 0.15:
                        mood_dist[NarrativeMood.HOPEFUL.value] += 1
                    else:
                        mood_dist[NarrativeMood.SERENE.value] += 1

                total = sum(mood_dist.values())
                if total > 0:
                    for k in mood_dist:
                        mood_dist[k] = round(mood_dist[k] / total, 2)

            branching_factor = 0.0
            if self._graph:
                total_edges = sum(len(n.possible_next) for n in self._graph.values())
                branching_factor = round(total_edges / len(self._graph), 2)

            return {
                "total_nodes": len(self._graph),
                "active_threads": self._narrative_state.active_threads,
                "completed_threads": self._narrative_state.completed_threads,
                "total_adaptations": self._stats["total_adaptations"],
                "character_count": len(self._characters),
                "branching_factor": branching_factor,
                "coherence_score": self._narrative_state.story_coherence,
                "mood_distribution": mood_dist,
                "current_mood": self._narrative_state.mood.value,
                "tension_level": round(self._narrative_state.tension_level, 2),
                "player_agency": round(self._narrative_state.player_agency_score, 2),
                "total_player_actions": self._stats["total_player_actions"],
                "adaptation_by_type": dict(self._stats["adaptation_by_type"]),
            }

    def reset(self) -> None:
        """Reset all dynamic narrative state."""
        with self._lock:
            self._graph.clear()
            self._active_threads.clear()
            self._completed_threads.clear()
            self._characters.clear()
            self._player_actions.clear()
            self._narrative_state = NarrativeState()
            self._adaptation_history.clear()
            self._stats = {
                "total_nodes_created": 0,
                "total_adaptations": 0,
                "total_player_actions": 0,
                "adaptation_by_type": {pt.value: 0 for pt in PlotAdaptation},
                "mood_distribution": {m.value: 0.0 for m in NarrativeMood},
            }


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_dynamic_narrative() -> AgentDynamicNarrative:
    """Return the singleton AgentDynamicNarrative instance."""
    return AgentDynamicNarrative.get_instance()