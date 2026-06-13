"""
SparkLabs Agent - Game Vision System

A unified creative vision system that integrates game design direction,
narrative architecture, and aesthetic coherence into a single guiding
intelligence. The Game Vision System ensures all creative decisions align
with the core design pillars and maintain tonal consistency.

Architecture:
  GameVision
    |-- DesignPillarManager (core design tenets, gameplay values, target experience)
    |-- NarrativeArchitect (story structure, character arcs, world building)
    |-- AestheticDirector (visual style, audio direction, emotional palette)
    |-- CoherenceValidator (cross-domain consistency checks, tonal alignment)
    |-- VisionEvolution (adaptive refinement as the game develops)

Capabilities:
  - Define and maintain core design pillars throughout development
  - Architectural narrative design with branching story structures
  - Aesthetic direction encompassing visual, audio, and emotional design
  - Cross-domain coherence validation between mechanics, story, and art
  - Adaptive vision evolution responding to playtest feedback
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class DesignPillar(Enum):
    GAMEPLAY_FIRST = "gameplay_first"
    NARRATIVE_DRIVEN = "narrative_driven"
    IMMERSIVE_SIMULATION = "immersive_simulation"
    SOCIAL_EXPERIENCE = "social_experience"
    COMPETITIVE_EXCELLENCE = "competitive_excellence"
    ACCESSIBLE_DESIGN = "accessible_design"
    ARTISTIC_EXPRESSION = "artistic_expression"
    TECHNICAL_INNOVATION = "technical_innovation"


class NarrativeStructure(Enum):
    LINEAR = "linear"
    BRANCHING = "branching"
    EMERGENT = "emergent"
    EPISODIC = "episodic"
    MODULAR = "modular"
    PLAYER_DRIVEN = "player_driven"


class VisualStyle(Enum):
    REALISTIC = "realistic"
    STYLIZED = "stylized"
    PIXEL_ART = "pixel_art"
    LOW_POLY = "low_poly"
    CELL_SHADED = "cell_shaded"
    HAND_DRAWN = "hand_drawn"
    MINIMALIST = "minimalist"
    RETRO = "retro"


class EmotionalTone(Enum):
    JOYFUL = "joyful"
    MYSTERIOUS = "mysterious"
    DARK = "dark"
    HOPEFUL = "hopeful"
    TENSE = "tense"
    WHIMSICAL = "whimsical"
    EPIC = "epic"
    INTIMATE = "intimate"


class CoherenceLevel(Enum):
    FULLY_ALIGNED = "fully_aligned"
    MOSTLY_ALIGNED = "mostly_aligned"
    PARTIALLY_ALIGNED = "partially_aligned"
    MISALIGNED = "misaligned"
    CONFLICTING = "conflicting"


@dataclass
class VisionElement:
    """A single element of the creative vision."""
    element_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    category: str = ""
    name: str = ""
    description: str = ""
    priority: int = 5
    dependencies: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class DesignDecision:
    """A recorded design decision with rationale."""
    decision_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    element_id: str = ""
    decision: str = ""
    rationale: str = ""
    alternatives: List[str] = field(default_factory=list)
    impact: Dict[str, Any] = field(default_factory=dict)
    pillars_affected: List[DesignPillar] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class CoherenceReport:
    """Cross-domain coherence analysis report."""
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    overall_coherence: CoherenceLevel = CoherenceLevel.FULLY_ALIGNED
    domain_scores: Dict[str, float] = field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class GameVision:
    """Unified creative vision system for game development."""

    def __init__(self):
        self._lock = threading.RLock()
        self._project_name: str = ""
        self._primary_pillars: List[DesignPillar] = []
        self._secondary_pillars: List[DesignPillar] = []
        self._narrative_structure: NarrativeStructure = NarrativeStructure.BRANCHING
        self._visual_style: VisualStyle = VisualStyle.STYLIZED
        self._emotional_tone: EmotionalTone = EmotionalTone.EPIC
        self._target_audience: str = ""
        self._elements: Dict[str, VisionElement] = {}
        self._decisions: List[DesignDecision] = []
        self._coherence_history: List[CoherenceReport] = []

    # ---- Vision Setup ----

    def set_project_identity(self, name: str, target_audience: str = "",
                             pillars: List[DesignPillar] = None,
                             narrative: NarrativeStructure = None,
                             visual: VisualStyle = None,
                             emotional: EmotionalTone = None):
        with self._lock:
            self._project_name = name
            self._target_audience = target_audience
            if pillars:
                self._primary_pillars = pillars[:3]
                self._secondary_pillars = pillars[3:]
            if narrative:
                self._narrative_structure = narrative
            if visual:
                self._visual_style = visual
            if emotional:
                self._emotional_tone = emotional

    # ---- Element Management ----

    def add_element(self, category: str, name: str, description: str = "",
                    priority: int = 5, dependencies: List[str] = None,
                    constraints: Dict[str, Any] = None) -> VisionElement:
        element = VisionElement(
            category=category,
            name=name,
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            constraints=constraints or {}
        )
        with self._lock:
            self._elements[element.element_id] = element
        return element

    def update_element(self, element_id: str, **kwargs):
        with self._lock:
            if element_id in self._elements:
                el = self._elements[element_id]
                for key, value in kwargs.items():
                    if hasattr(el, key):
                        setattr(el, key, value)
                el.updated_at = time.time()

    def remove_element(self, element_id: str) -> bool:
        with self._lock:
            if element_id in self._elements:
                del self._elements[element_id]
                return True
            return False

    # ---- Decision Recording ----

    def record_decision(self, element_id: str, decision: str, rationale: str = "",
                        alternatives: List[str] = None,
                        pillars_affected: List[DesignPillar] = None,
                        impact: Dict[str, Any] = None) -> DesignDecision:
        dd = DesignDecision(
            element_id=element_id,
            decision=decision,
            rationale=rationale,
            alternatives=alternatives or [],
            pillars_affected=pillars_affected or [],
            impact=impact or {}
        )
        with self._lock:
            self._decisions.append(dd)
        return dd

    # ---- Coherence Validation ----

    def validate_coherence(self) -> CoherenceReport:
        with self._lock:
            report = CoherenceReport()
            conflicts = []
            suggestions = []
            domain_scores = {}

            # Check pillar alignment
            if len(self._primary_pillars) > 3:
                conflicts.append({
                    "type": "too_many_primary_pillars",
                    "message": "Too many primary pillars may dilute focus",
                    "severity": "medium"
                })
                suggestions.append("Consider reducing primary pillars to 3 for sharper focus")

            # Check narrative-visual alignment
            narrative_visual_score = self._check_narrative_visual_alignment()
            domain_scores["narrative_visual"] = narrative_visual_score
            if narrative_visual_score < 0.5:
                conflicts.append({
                    "type": "narrative_visual_mismatch",
                    "message": "Narrative structure and visual style may conflict",
                    "severity": "high"
                })

            # Check emotional coherence
            emotional_score = self._check_emotional_coherence()
            domain_scores["emotional_coherence"] = emotional_score

            # Check element dependencies
            element_score = self._check_element_dependencies()
            domain_scores["element_dependencies"] = element_score
            if element_score < 0.7:
                conflicts.append({
                    "type": "unresolved_dependencies",
                    "message": "Some vision elements have unresolved dependencies",
                    "severity": "medium"
                })

            # Compute overall
            avg_score = sum(domain_scores.values()) / max(1, len(domain_scores))
            if avg_score >= 0.9:
                report.overall_coherence = CoherenceLevel.FULLY_ALIGNED
            elif avg_score >= 0.7:
                report.overall_coherence = CoherenceLevel.MOSTLY_ALIGNED
            elif avg_score >= 0.5:
                report.overall_coherence = CoherenceLevel.PARTIALLY_ALIGNED
            elif avg_score >= 0.3:
                report.overall_coherence = CoherenceLevel.MISALIGNED
            else:
                report.overall_coherence = CoherenceLevel.CONFLICTING

            report.domain_scores = domain_scores
            report.conflicts = conflicts
            report.suggestions = suggestions
            self._coherence_history.append(report)
            return report

    def _check_narrative_visual_alignment(self) -> float:
        pairings = {
            (NarrativeStructure.LINEAR, VisualStyle.REALISTIC): 0.9,
            (NarrativeStructure.BRANCHING, VisualStyle.STYLIZED): 0.9,
            (NarrativeStructure.EMERGENT, VisualStyle.LOW_POLY): 0.9,
            (NarrativeStructure.EPISODIC, VisualStyle.CELL_SHADED): 0.9,
            (NarrativeStructure.PLAYER_DRIVEN, VisualStyle.MINIMALIST): 0.9,
            (NarrativeStructure.MODULAR, VisualStyle.PIXEL_ART): 0.8,
        }
        return pairings.get((self._narrative_structure, self._visual_style), 0.6)

    def _check_emotional_coherence(self) -> float:
        tone_visual_map = {
            EmotionalTone.DARK: [VisualStyle.REALISTIC, VisualStyle.STYLIZED],
            EmotionalTone.JOYFUL: [VisualStyle.CELL_SHADED, VisualStyle.HAND_DRAWN],
            EmotionalTone.EPIC: [VisualStyle.REALISTIC, VisualStyle.STYLIZED],
            EmotionalTone.WHIMSICAL: [VisualStyle.HAND_DRAWN, VisualStyle.PIXEL_ART],
            EmotionalTone.MYSTERIOUS: [VisualStyle.REALISTIC, VisualStyle.LOW_POLY],
        }
        compatible = tone_visual_map.get(self._emotional_tone, [])
        if self._visual_style in compatible:
            return 0.9
        return 0.5

    def _check_element_dependencies(self) -> float:
        if not self._elements:
            return 1.0
        existing_ids = set(self._elements.keys())
        unresolved = 0
        for el in self._elements.values():
            for dep in el.dependencies:
                if dep not in existing_ids:
                    unresolved += 1
        total_deps = sum(len(el.dependencies) for el in self._elements.values())
        if total_deps == 0:
            return 1.0
        return 1.0 - (unresolved / total_deps)

    # ---- Vision Export ----

    def get_vision_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "project_name": self._project_name,
                "target_audience": self._target_audience,
                "primary_pillars": [p.value for p in self._primary_pillars],
                "secondary_pillars": [p.value for p in self._secondary_pillars],
                "narrative_structure": self._narrative_structure.value,
                "visual_style": self._visual_style.value,
                "emotional_tone": self._emotional_tone.value,
                "element_count": len(self._elements),
                "decision_count": len(self._decisions),
                "coherence_reports": len(self._coherence_history),
            }

    def get_elements(self, category: str = None) -> List[Dict[str, Any]]:
        with self._lock:
            elements = self._elements.values()
            if category:
                elements = [e for e in elements if e.category == category]
            return [
                {
                    "element_id": e.element_id,
                    "category": e.category,
                    "name": e.name,
                    "description": e.description,
                    "priority": e.priority,
                    "dependencies": e.dependencies,
                    "status": e.status,
                }
                for e in sorted(elements, key=lambda x: x.priority)
            ]

    def get_decisions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "decision_id": d.decision_id,
                    "element_id": d.element_id,
                    "decision": d.decision,
                    "rationale": d.rationale,
                    "pillars_affected": [p.value for p in d.pillars_affected],
                    "timestamp": d.timestamp,
                }
                for d in self._decisions[-limit:]
            ]

    def get_stats(self) -> Dict[str, Any]:
        return self.get_vision_summary()


# Singleton instance
_game_vision: Optional[GameVision] = None
_vision_lock = threading.RLock()


def get_game_vision() -> GameVision:
    global _game_vision
    with _vision_lock:
        if _game_vision is None:
            _game_vision = GameVision()
        return _game_vision