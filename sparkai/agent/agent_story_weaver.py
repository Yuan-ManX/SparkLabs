"""
SparkLabs Agent - Story Weaver

Procedural storyline weaving system for the AI-native game engine.
Generates, manages, and interleaves complex narrative structures with
branching paths, character arcs, and dynamic plot progression.

Architecture:
  StoryWeaver
    |-- StoryNode (individual narrative beat with conditions and outcomes)
    |-- StoryThread (linear narrative sequence with branching paths)
    |-- CharacterArc (character growth trajectory across the narrative)
    |-- BranchManager (conditional branching between story nodes)
    |-- CoherenceAnalyzer (narrative consistency validation)
    |-- PathSimulator (player choice-driven path walkthrough)

Supports 8 distinct story arcs and 7 plot point types for diverse
narrative generation within AI-native interactive storytelling.
"""

from __future__ import annotations

import random
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class StoryArc(Enum):
    HEROS_JOURNEY = "heros_journey"
    RAGS_TO_RICHES = "rags_to_riches"
    TRAGEDY = "tragedy"
    REBIRTH = "rebirth"
    QUEST = "quest"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    REVENGE = "revenge"


class PlotPointType(Enum):
    INCITING_INCIDENT = "inciting_incident"
    RISING_ACTION = "rising_action"
    MIDPOINT = "midpoint"
    CRISIS = "crisis"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    DENOUEMENT = "denouement"


class CharacterRole(Enum):
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    MENTOR = "mentor"
    ALLY = "ally"
    TRICKSTER = "trickster"
    HERALD = "herald"
    GUARDIAN = "guardian"
    SHADOW = "shadow"


class BranchCondition(Enum):
    PLAYER_CHOICE = "player_choice"
    SKILL_CHECK = "skill_check"
    REPUTATION = "reputation"
    INVENTORY = "inventory"
    RELATIONSHIP = "relationship"
    RANDOM = "random"
    TIMED = "timed"


ARC_PLOT_TEMPLATES: Dict[StoryArc, List[PlotPointType]] = {
    StoryArc.HEROS_JOURNEY: [
        PlotPointType.INCITING_INCIDENT,
        PlotPointType.RISING_ACTION,
        PlotPointType.MIDPOINT,
        PlotPointType.CRISIS,
        PlotPointType.CLIMAX,
        PlotPointType.RESOLUTION,
        PlotPointType.DENOUEMENT,
    ],
    StoryArc.RAGS_TO_RICHES: [
        PlotPointType.INCITING_INCIDENT,
        PlotPointType.RISING_ACTION,
        PlotPointType.RISING_ACTION,
        PlotPointType.MIDPOINT,
        PlotPointType.CLIMAX,
        PlotPointType.RESOLUTION,
    ],
    StoryArc.TRAGEDY: [
        PlotPointType.INCITING_INCIDENT,
        PlotPointType.RISING_ACTION,
        PlotPointType.MIDPOINT,
        PlotPointType.CRISIS,
        PlotPointType.CLIMAX,
    ],
    StoryArc.REBIRTH: [
        PlotPointType.INCITING_INCIDENT,
        PlotPointType.RISING_ACTION,
        PlotPointType.CRISIS,
        PlotPointType.MIDPOINT,
        PlotPointType.RISING_ACTION,
        PlotPointType.CLIMAX,
        PlotPointType.RESOLUTION,
        PlotPointType.DENOUEMENT,
    ],
    StoryArc.QUEST: [
        PlotPointType.INCITING_INCIDENT,
        PlotPointType.RISING_ACTION,
        PlotPointType.RISING_ACTION,
        PlotPointType.MIDPOINT,
        PlotPointType.RISING_ACTION,
        PlotPointType.CLIMAX,
        PlotPointType.RESOLUTION,
    ],
    StoryArc.MYSTERY: [
        PlotPointType.INCITING_INCIDENT,
        PlotPointType.RISING_ACTION,
        PlotPointType.RISING_ACTION,
        PlotPointType.MIDPOINT,
        PlotPointType.CRISIS,
        PlotPointType.CLIMAX,
        PlotPointType.RESOLUTION,
        PlotPointType.DENOUEMENT,
    ],
    StoryArc.ROMANCE: [
        PlotPointType.INCITING_INCIDENT,
        PlotPointType.RISING_ACTION,
        PlotPointType.MIDPOINT,
        PlotPointType.CRISIS,
        PlotPointType.CLIMAX,
        PlotPointType.RESOLUTION,
        PlotPointType.DENOUEMENT,
    ],
    StoryArc.REVENGE: [
        PlotPointType.INCITING_INCIDENT,
        PlotPointType.RISING_ACTION,
        PlotPointType.MIDPOINT,
        PlotPointType.CRISIS,
        PlotPointType.RISING_ACTION,
        PlotPointType.CLIMAX,
        PlotPointType.RESOLUTION,
    ],
}

TONE_PRESETS: Dict[StoryArc, Tuple[float, float]] = {
    StoryArc.HEROS_JOURNEY: (0.6, 0.3),
    StoryArc.RAGS_TO_RICHES: (0.7, 0.2),
    StoryArc.TRAGEDY: (-0.5, 0.4),
    StoryArc.REBIRTH: (0.4, 0.3),
    StoryArc.QUEST: (0.5, 0.2),
    StoryArc.MYSTERY: (0.0, 0.5),
    StoryArc.ROMANCE: (0.6, 0.2),
    StoryArc.REVENGE: (-0.3, 0.5),
}


@dataclass
class StoryNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    arc_position: int = 0
    plot_type: PlotPointType = PlotPointType.RISING_ACTION
    summary: str = ""
    required_characters: List[str] = field(default_factory=list)
    unlock_conditions: List[Dict[str, Any]] = field(default_factory=list)
    outcomes: List[Dict[str, Any]] = field(default_factory=list)
    tone_modifier: float = 0.0
    child_nodes: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "arc_position": self.arc_position,
            "plot_type": self.plot_type.value,
            "summary": self.summary[:200],
            "required_characters": self.required_characters,
            "unlock_conditions": self.unlock_conditions,
            "outcomes": self.outcomes,
            "tone_modifier": self.tone_modifier,
            "child_count": len(self.child_nodes),
        }


@dataclass
class StoryThread:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    arc: StoryArc = StoryArc.QUEST
    title: str = ""
    nodes_list: List[str] = field(default_factory=list)
    current_node_index: int = 0
    branching_paths: Dict[str, List[Tuple[BranchCondition, str]]] = field(
        default_factory=dict
    )
    emotional_arc: List[float] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    is_complete: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "arc": self.arc.value,
            "title": self.title,
            "node_count": len(self.nodes_list),
            "current_node_index": self.current_node_index,
            "branch_count": len(self.branching_paths),
            "emotional_arc_length": len(self.emotional_arc),
            "is_complete": self.is_complete,
        }


@dataclass
class CharacterArc:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    character_id: str = ""
    role: CharacterRole = CharacterRole.ALLY
    motivation: str = ""
    growth_trajectory: List[float] = field(default_factory=list)
    key_decisions: List[Dict[str, Any]] = field(default_factory=list)
    thread_assignments: List[str] = field(default_factory=list)
    current_state: str = "initial"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "character_id": self.character_id,
            "role": self.role.value,
            "motivation": self.motivation[:100],
            "growth_trajectory": self.growth_trajectory,
            "decision_count": len(self.key_decisions),
            "assigned_threads": len(self.thread_assignments),
            "current_state": self.current_state,
        }


class StoryWeaver:
    """
    Procedural storyline weaving system for AI-native game engine.

    Generates narrative frameworks from story arcs, manages branching
    paths through conditional logic, interleaves multiple story threads,
    and provides analysis tools for narrative coherence and player
    path simulation.
    """

    _instance: Optional[StoryWeaver] = None
    _lock = threading.Lock()

    MAX_THREADS = 50
    MAX_NODES_PER_THREAD = 200

    def __init__(self) -> None:
        self._threads: Dict[str, StoryThread] = {}
        self