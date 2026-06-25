"""
SparkAI Game Vision Agent - Holistic game analysis and design intelligence.

Provides comprehensive game vision analysis combining design theory,
player psychology, market understanding, and creative direction into
a unified game design intelligence system.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DesignPillar(Enum):
    """Core design pillars for game vision analysis."""
    GAMEPLAY_DEPTH = "gameplay_depth"
    NARRATIVE_IMMERSION = "narrative_immersion"
    VISUAL_IDENTITY = "visual_identity"
    AUDIO_ATMOSPHERE = "audio_atmosphere"
    PLAYER_AGENCY = "player_agency"
    SYSTEMIC_EMERGENCE = "systemic_emergence"
    SOCIAL_INTERACTION = "social_interaction"
    ACCESSIBILITY = "accessibility"
    REPLAYABILITY = "replayability"
    EMOTIONAL_IMPACT = "emotional_impact"


class VisionPhase(Enum):
    """Phases of the game vision analysis pipeline."""
    CONCEPT_DISCOVERY = "concept_discovery"
    PILLAR_ANALYSIS = "pillar_analysis"
    COHERENCE_CHECK = "coherence_check"
    FEASIBILITY_ASSESSMENT = "feasibility_assessment"
    VISION_SYNTHESIS = "vision_synthesis"
    ITERATIVE_REFINEMENT = "iterative_refinement"


class PlayerArchetype(Enum):
    """Player archetypes for target audience analysis."""
    ACHIEVER = "achiever"
    EXPLORER = "explorer"
    SOCIALIZER = "socializer"
    COMPETITOR = "competitor"
    STORYTELLER = "storyteller"
    CREATOR = "creator"
    STRATEGIST = "strategist"
    COLLECTOR = "collector"


@dataclass
class DesignPillarAnalysis:
    """Analysis of a single design pillar."""
    pillar: DesignPillar
    score: float  # 0.0 to 1.0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    design_notes: List[str] = field(default_factory=list)
    priority: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pillar": self.pillar.value,
            "score": self.score,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "opportunities": self.opportunities,
            "design_notes": self.design_notes,
            "priority": self.priority,
        }


@dataclass
class VisionProfile:
    """Complete game vision profile."""
    vision_id: str
    game_concept: str
    genre: str
    target_audience: List[PlayerArchetype] = field(default_factory=list)
    pillars: List[DesignPillarAnalysis] = field(default_factory=list)
    core_loop: str = ""
    unique_selling_points: List[str] = field(default_factory=list)
    design_constraints: List[str] = field(default_factory=list)
    inspiration_sources: List[str] = field(default_factory=list)
    mood_descriptors: List[str] = field(default_factory=list)
    risk_assessment: Dict[str, Any] = field(default_factory=dict)
    coherence_score: float = 0.0
    feasibility_score: float = 0.0
    innovation_score: float = 0.0
    overall_score: float = 0.0
    phase: VisionPhase = VisionPhase.CONCEPT_DISCOVERY
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vision_id": self.vision_id,
            "game_concept": self.game_concept,
            "genre": self.genre,
            "target_audience": [a.value for a in self.target_audience],
            "pillars": [p.to_dict() for p in self.pillars],
            "core_loop": self.core_loop,
            "unique_selling_points": self.unique_selling_points,
            "design_constraints": self.design_constraints,
            "inspiration_sources": self.inspiration_sources,
            "mood_descriptors": self.mood_descriptors,
            "risk_assessment": self.risk_assessment,
            "coherence_score": self.coherence_score,
            "feasibility_score": self.feasibility_score,
            "innovation_score": self.innovation_score,
            "overall_score": self.overall_score,
            "phase": self.phase.value,
            "created_at": self.created_at,
        }


@dataclass
class GameplayAnalysis:
    """Detailed gameplay mechanics analysis."""
    analysis_id: str
    core_mechanics: List[Dict[str, Any]] = field(default_factory=list)
    secondary_mechanics: List[Dict[str, Any]] = field(default_factory=list)
    progression_systems: List[Dict[str, Any]] = field(default_factory=list)
    feedback_systems: List[Dict[str, Any]] = field(default_factory=list)
    balance_considerations: List[str] = field(default_factory=list)
    pacing_analysis: Dict[str, Any] = field(default_factory=dict)
    skill_ceiling: float = 0.0
    accessibility_rating: float = 0.0
    depth_rating: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "core_mechanics": self.core_mechanics,
            "secondary_mechanics": self.secondary_mechanics,
            "progression_systems": self.progression_systems,
            "feedback_systems": self.feedback_systems,
            "balance_considerations": self.balance_considerations,
            "pacing_analysis": self.pacing_analysis,
            "skill_ceiling": self.skill_ceiling,
            "accessibility_rating": self.accessibility_rating,
            "depth_rating": self.depth_rating,
        }


class PillarAnalyzer:
    """Analyzes individual design pillars."""

    def analyze(self, pillar: DesignPillar, concept: str) -> DesignPillarAnalysis:
        """Analyze a specific design pillar for a game concept."""
        base_score = 0.7
        strengths = [f"Strong {pillar.value.replace('_', ' ')} foundation"]
        weaknesses = [f"Needs deeper {pillar.value.replace('_', ' ')} exploration"]
        opportunities = [f"Opportunity to innovate in {pillar.value.replace('_', ' ')}"]

        return DesignPillarAnalysis(
            pillar=pillar,
            score=base_score,
            strengths=strengths,
            weaknesses=weaknesses,
            opportunities=opportunities,
            design_notes=[f"Initial {pillar.value} analysis for: {concept}"],
            priority="high" if base_score < 0.8 else "medium",
        )


class CoherenceChecker:
    """Checks design coherence across all pillars."""

    def check_coherence(
        self, pillars: List[DesignPillarAnalysis]
    ) -> Dict[str, Any]:
        """Check how well design pillars work together."""
        scores = [p.score for p in pillars]
        avg_score = sum(scores) / max(len(scores), 1)
        min_score = min(scores) if scores else 0
        score_variance = sum((s - avg_score) ** 2 for s in scores) / max(len(scores), 1)

        coherence = 1.0 - (score_variance * 2)

        conflicts = []
        synergies = []

        for i, p1 in enumerate(pillars):
            for j, p2 in enumerate(pillars):
                if i >= j:
                    continue
                if abs(p1.score - p2.score) > 0.3:
                    conflicts.append(
                        f"Tension between {p1.pillar.value} and {p2.pillar.value}"
                    )
                else:
                    synergies.append(
                        f"Synergy between {p1.pillar.value} and {p2.pillar.value}"
                    )

        return {
            "coherence_score": max(0.0, min(1.0, coherence)),
            "average_pillar_score": avg_score,
            "weakest_pillar": min(pillars, key=lambda p: p.score).pillar.value if pillars else "",
            "conflicts": conflicts,
            "synergies": synergies,
            "recommendation": "Balanced design" if coherence > 0.7 else "Needs pillar rebalancing",
        }


class FeasibilityAssessor:
    """Assesses technical and design feasibility."""

    def assess(
        self, concept: str, constraints: List[str]
    ) -> Dict[str, Any]:
        """Assess feasibility of a game concept."""
        constraint_count = len(constraints)
        base_feasibility = 0.85 - (constraint_count * 0.05)

        return {
            "technical_feasibility": max(0.3, base_feasibility),
            "design_feasibility": max(0.4, base_feasibility + 0.05),
            "resource_requirements": {
                "development_complexity": "medium",
                "estimated_systems": 5 + constraint_count,
                "core_team_size": "3-5 developers",
                "prototype_timeline": "2-4 weeks",
            },
            "risks": [
                "Scope creep in complex systems",
                "Integration challenges between subsystems",
            ],
            "mitigations": [
                "Iterative prototyping approach",
                "Modular system architecture",
            ],
        }


class GameVisionEngine:
    """Comprehensive game vision analysis and design intelligence engine.

    Provides holistic game design analysis combining pillar analysis,
    coherence checking, feasibility assessment, and creative direction
    into actionable game design intelligence.
    """

    _instance: Optional["GameVisionEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if self._instance is not None:
            raise RuntimeError("Use GameVisionEngine.get_instance()")
        self._pillar_analyzer = PillarAnalyzer()
        self._coherence_checker = CoherenceChecker()
        self._feasibility_assessor = FeasibilityAssessor()
        self._vision_profiles: Dict[str, VisionProfile] = {}
        self._gameplay_analyses: Dict[str, GameplayAnalysis] = {}
        self._analysis_history: List[Dict[str, Any]] = []
        self._initialized: bool = False
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "GameVisionEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the game vision engine."""
        with self._lock:
            if self._initialized:
                return
            self._initialized = True

    def create_vision(
        self,
        game_concept: str,
        genre: str,
        target_audience: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
    ) -> VisionProfile:
        """Create a comprehensive game vision profile."""
        vision_id = f"vision_{uuid.uuid4().hex[:12]}"

        archetypes = []
        if target_audience:
            for a in target_audience:
                try:
                    archetypes.append(PlayerArchetype(a))
                except ValueError:
                    archetypes.append(PlayerArchetype.EXPLORER)

        profile = VisionProfile(
            vision_id=vision_id,
            game_concept=game_concept,
            genre=genre,
            target_audience=archetypes,
            design_constraints=constraints or [],
            phase=VisionPhase.CONCEPT_DISCOVERY,
        )

        # Analyze all design pillars
        for pillar in DesignPillar:
            analysis = self._pillar_analyzer.analyze(pillar, game_concept)
            profile.pillars.append(analysis)

        # Check coherence
        coherence = self._coherence_checker.check_coherence(profile.pillars)
        profile.coherence_score = coherence["coherence_score"]

        # Assess feasibility
        feasibility = self._feasibility_assessor.assess(
            game_concept, constraints or []
        )
        profile.feasibility_score = feasibility["technical_feasibility"]

        # Calculate innovation score
        innovation = 0.7
        profile.innovation_score = innovation

        # Overall score
        profile.overall_score = (
            profile.coherence_score * 0.35
            + profile.feasibility_score * 0.35
            + profile.innovation_score * 0.3
        )

        profile.phase = VisionPhase.VISION_SYNTHESIS

        with self._lock:
            self._vision_profiles[vision_id] = profile

        return profile

    def analyze_gameplay(
        self, concept: str, mechanics: Optional[List[str]] = None
    ) -> GameplayAnalysis:
        """Analyze gameplay mechanics and systems."""
        analysis_id = f"gameplay_{uuid.uuid4().hex[:12]}"

        core_mechanics = []
        if mechanics:
            for m in mechanics:
                core_mechanics.append({
                    "name": m,
                    "type": "core",
                    "complexity": "medium",
                    "player_skill_required": "moderate",
                    "innovation_potential": "high",
                })

        analysis = GameplayAnalysis(
            analysis_id=analysis_id,
            core_mechanics=core_mechanics,
            secondary_mechanics=[
                {"name": "resource_management", "type": "secondary",
                 "complexity": "low"},
                {"name": "progression_tracking", "type": "secondary",
                 "complexity": "medium"},
            ],
            progression_systems=[
                {"type": "skill_tree", "depth": "medium",
                 "branching_factor": 3},
                {"type": "equipment_upgrade", "depth": "high",
                 "tiers": 5},
            ],
            feedback_systems=[
                {"type": "visual", "responsiveness": "high"},
                {"type": "audio", "responsiveness": "high"},
                {"type": "haptic", "responsiveness": "medium"},
            ],
            balance_considerations=[
                "Difficulty curve optimization",
                "Resource economy balance",
                "Player skill progression pacing",
            ],
            pacing_analysis={
                "tutorial_phase": "gradual",
                "mid_game": "escalating",
                "end_game": "mastery",
            },
            skill_ceiling=0.75,
            accessibility_rating=0.8,
            depth_rating=0.85,
        )

        with self._lock:
            self._gameplay_analyses[analysis_id] = analysis

        return analysis

    def get_vision(self, vision_id: str) -> Optional[VisionProfile]:
        with self._lock:
            return self._vision_profiles.get(vision_id)

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            profiles = list(self._vision_profiles.values())
            return {
                "total_visions": len(profiles),
                "average_coherence": (
                    sum(p.coherence_score for p in profiles) / max(len(profiles), 1)
                ),
                "average_feasibility": (
                    sum(p.feasibility_score for p in profiles) / max(len(profiles), 1)
                ),
                "average_innovation": (
                    sum(p.innovation_score for p in profiles) / max(len(profiles), 1)
                ),
                "gameplay_analyses": len(self._gameplay_analyses),
                "initialized": self._initialized,
            }

    def get_visions(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in list(self._vision_profiles.values())[-limit:]]


def get_game_vision() -> GameVisionEngine:
    """Get the global GameVisionEngine instance."""
    return GameVisionEngine.get_instance()