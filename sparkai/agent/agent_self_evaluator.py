"""
SparkLabs Agent - Self Evaluator

Autonomous quality assessment system for agent-generated game content.
Evaluates agent outputs — game designs, world structures, entity
configurations, generated code — against configurable quality criteria
and produces structured feedback for iterative improvement.

Architecture:
  SelfEvaluator
    |-- QualityDimension (scored aspect: correctness, completeness, creativity, etc.)
    |-- EvaluationRubric (weighted scoring schema per output type)
    |-- ScoringEngine (dimension-level scoring with evidence)
    |-- FeedbackGenerator (actionable suggestions from evaluation)

Output Types:
  - game_design: high-level game concept evaluation
  - world_layout: level design and spatial arrangement
  - entity_config: entity properties and behaviors
  - generated_code: sandbox code quality assessment
  - narrative_dialogue: story coherence and character voice
  - asset_description: visual/audio asset fitness

Usage:
    evaluator = SelfEvaluator()
    result = evaluator.evaluate(
        content=generated_game_design,
        output_type="game_design",
        context={"target_genre": "platformer", "audience": "casual"},
    )
    if result.overall_score < 0.7:
        for suggestion in result.suggestions:
            print(f"Improve: {suggestion}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class EvaluationGrade(Enum):
    EXCELLENT = (5, "Meets all criteria with distinction")
    GOOD = (4, "Meets most criteria well")
    ADEQUATE = (3, "Meets minimum requirements")
    NEEDS_WORK = (2, "Several deficiencies")
    POOR = (1, "Major issues across dimensions")
    UNEVALUABLE = (0, "Cannot be assessed with available evidence")


@dataclass
class DimensionScore:
    dimension: str = ""
    grade: EvaluationGrade = EvaluationGrade.ADEQUATE
    score: float = 0.5
    weight: float = 1.0
    evidence: str = ""
    suggestions: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    output_type: str = ""
    overall_score: float = 0.0
    overall_grade: EvaluationGrade = EvaluationGrade.ADEQUATE
    dimensions: List[DimensionScore] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 0.5
    evaluator_notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.overall_score >= 0.6

    @property
    def needs_revision(self) -> bool:
        return self.overall_score < 0.7

    def to_dict(self) -> dict:
        return {
            "type": self.output_type,
            "score": round(self.overall_score, 3),
            "grade": self.overall_grade.name,
            "dimensions": [
                {
                    "name": d.dimension, "score": round(d.score, 3),
                    "grade": d.grade.name, "evidence": d.evidence[:200],
                }
                for d in self.dimensions
            ],
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions[:5],
            "confidence": round(self.confidence, 3),
        }


RUBRICS: Dict[str, List[Tuple[str, float, str]]] = {
    "game_design": [
        ("Concept Clarity", 0.25, "Is the core game idea clearly articulated?"),
        ("Mechanical Cohesion", 0.25, "Do game mechanics work together logically?"),
        ("Engagement Potential", 0.20, "Would target audience find it compelling?"),
        ("Scope Feasibility", 0.15, "Can this be built with available resources?"),
        ("Originality", 0.15, "Does it offer a fresh perspective?"),
    ],
    "world_layout": [
        ("Spatial Logic", 0.25, "Is the level layout physically sensible?"),
        ("Flow & Pacing", 0.25, "Does level progression feel natural?"),
        ("Visual Balance", 0.15, "Is element distribution aesthetically balanced?"),
        ("Navigation Clarity", 0.20, "Can players understand where to go?"),
        ("Challenge Curve", 0.15, "Does difficulty progress appropriately?"),
    ],
    "entity_config": [
        ("Property Completeness", 0.30, "Are all necessary properties defined?"),
        ("Behavioral Consistency", 0.25, "Do behaviors match the entity's role?"),
        ("Interaction Readiness", 0.20, "Are entity interactions well-specified?"),
        ("Balance Appropriateness", 0.15, "Are stats balanced for the game context?"),
        ("Reusability", 0.10, "Can this entity be reused across scenes?"),
    ],
    "generated_code": [
        ("Functional Correctness", 0.30, "Does the code do what it claims?"),
        ("Safety Compliance", 0.25, "Does it pass sandbox validation?"),
        ("Performance Efficiency", 0.15, "Will it run efficiently at scale?"),
        ("Readability", 0.15, "Is the code clear and maintainable?"),
        ("Error Handling", 0.15, "Are edge cases and errors handled?"),
    ],
    "narrative_dialogue": [
        ("Character Voice", 0.25, "Is the voice distinct and consistent?"),
        ("Coherence", 0.20, "Does it make logical sense?"),
        ("Emotional Impact", 0.20, "Does it evoke the intended emotion?"),
        ("Pacing", 0.15, "Is the rhythm appropriate?"),
        ("Contextual Fit", 0.20, "Does it serve the game's narrative?"),
    ],
    "asset_description": [
        ("Clarity", 0.30, "Is the visual/audio clearly described?"),
        ("Style Consistency", 0.25, "Does it match the game's aesthetic?"),
        ("Completeness", 0.25, "Are all relevant details specified?"),
        ("Feasibility", 0.20, "Can this asset be generated/acquired?"),
    ],
}


class SelfEvaluator:
    """
    Autonomous quality evaluator for agent-generated game content.

    Applies dimension-based rubrics to score agent outputs and
    generate prioritized suggestions for improvement. Works as
    a fast, deterministic assessment before costly LLM review.

    Usage:
        se = SelfEvaluator()
        result = se.evaluate(
            content={"concept": "gravity-shifting puzzle", "mechanics": ["flip", "slide"]},
            output_type="game_design",
            context={"genre": "puzzle"},
        )
        if result.needs_revision:
            print("Consider: ", result.suggestions)
    """

    def __init__(self, min_word_count: int = 3):
        self._min_words = min_word_count
        self._evaluation_count: int = 0
        self._avg_score: float = 0.0
        self._history: List[EvaluationResult] = []

    def evaluate(
        self,
        content: Any,
        output_type: str = "game_design",
        context: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResult:
        self._evaluation_count += 1
        context = context or {}

        text = self._extract_text(content)
        rubric = RUBRICS.get(output_type, RUBRICS["game_design"])

        if not text or len(text.split()) < self._min_words:
            return EvaluationResult(
                output_type=output_type,
                overall_grade=EvaluationGrade.UNEVALUABLE,
                evaluator_notes="Content too short to evaluate",
            )

        dimensions: List[DimensionScore] = []
        total_weight = sum(w for _, w, _ in rubric)

        for dim_name, weight, _ in rubric:
            score, evidence = self._score_dimension(text, dim_name, output_type, context)
            normalized_weight = weight / total_weight if total_weight > 0 else 1.0 / len(rubric)
            grade = self._score_to_grade(score)
            suggestions = self._generate_dimension_suggestions(dim_name, score, context)
            dimensions.append(DimensionScore(
                dimension=dim_name,
                grade=grade,
                score=score,
                weight=normalized_weight,
                evidence=evidence,
                suggestions=suggestions,
            ))

        overall = sum(d.score * d.weight for d in dimensions)
        overall = max(0.0, min(1.0, overall))

        strengths, weaknesses = self._categorize_dimensions(dimensions)

        all_suggestions: List[str] = []
        for d in sorted(dimensions, key=lambda d: d.score):
            all_suggestions.extend(d.suggestions[:2])
        all_suggestions = all_suggestions[:5]

        confidence = min(1.0, len(text.split()) / 50.0)

        result = EvaluationResult(
            output_type=output_type,
            overall_score=overall,
            overall_grade=self._score_to_grade(overall),
            dimensions=dimensions,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=all_suggestions,
            confidence=confidence,
            evaluator_notes=f"Evaluated {len(dimensions)} dimensions",
        )

        self._avg_score = (
            self._avg_score * (self._evaluation_count - 1) + overall
        ) / self._evaluation_count
        self._history.append(result)
        if len(self._history) > 100:
            self._history = self._history[-100:]

        return result

    def evaluate_batch(
        self,
        items: List[Tuple[str, Any]],
        output_type: str = "game_design",
    ) -> List[EvaluationResult]:
        return [self.evaluate(content, output_type) for _, content in items]

    def get_best(self, output_type: str = "", n: int = 3) -> List[EvaluationResult]:
        relevant = [
            r for r in self._history
            if not output_type or r.output_type == output_type
        ]
        return sorted(relevant, key=lambda r: -r.overall_score)[:n]

    def get_stats(self) -> dict:
        return {
            "evaluations": self._evaluation_count,
            "avg_score": round(self._avg_score, 3),
            "pass_rate": round(
                sum(1 for r in self._history if r.passed)
                / max(len(self._history), 1) * 100, 1,
            ),
            "history_size": len(self._history),
        }

    def clear(self) -> None:
        self._evaluation_count = 0
        self._avg_score = 0.0
        self._history.clear()

    def list_rubric_types(self) -> List[str]:
        return list(RUBRICS.keys())

    @staticmethod
    def _extract_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            parts = []
            for k, v in content.items():
                if isinstance(v, (str, int, float, bool)):
                    parts.append(f"{k}: {v}")
                elif isinstance(v, list):
                    parts.append(f"{k}: {', '.join(str(x) for x in v[:10])}")
            return ". ".join(parts)
        if isinstance(content, list):
            return ". ".join(str(item) for item in content[:20])
        return str(content)

    @staticmethod
    def _score_dimension(
        text: str, dimension: str, output_type: str, context: Dict[str, Any],
    ) -> Tuple[float, str]:
        text_lower = text.lower()
        word_count = len(text.split())

        if dimension == "Concept Clarity":
            if word_count > 20:
                return (0.8, "Well-articulated concept with sufficient detail")
            return (0.4, "Concept description is brief")

        if dimension == "Mechanical Cohesion":
            mech_keywords = ["mechanic", "interact", "combine", "system", "rule"]
            hits = sum(1 for k in mech_keywords if k in text_lower)
            if hits >= 2:
                return (0.75, f"Mechanics described with {hits} systemic mentions")
            return (0.4, "Mechanical descriptions are sparse")

        if dimension == "Engagement Potential":
            engage_keywords = ["player", "challenge", "reward", "fun", "exciting", "compelling"]
            hits = sum(1 for k in engage_keywords if k in text_lower)
            if hits >= 2:
                return (0.7, f"Engagement considerations mentioned ({hits} keywords)")
            return (0.5, "Limited engagement analysis")

        if dimension == "Scope Feasibility":
            if word_count > 50:
                return (0.7, "Sufficient detail to assess feasibility")
            return (0.5, "Limited detail for feasibility assessment")

        if dimension == "Originality":
            common_words = {"player", "enemy", "level", "jump", "shoot", "run", "collect"}
            unique_count = sum(1 for w in text_lower.split() if w not in common_words)
            ratio = unique_count / max(1, word_count)
            if ratio > 0.7:
                return (0.75, "High proportion of distinctive vocabulary")
            return (0.55, "Uses common game development patterns")

        if dimension == "Spatial Logic":
            spatial_keywords = ["position", "distance", "between", "near", "path", "route"]
            hits = sum(1 for k in spatial_keywords if k in text_lower)
            if hits >= 2:
                return (0.7, f"Spatial relationships described ({hits} keywords)")
            return (0.45, "Spatial layout is not well specified")

        if dimension == "Flow & Pacing":
            if word_count > 30:
                return (0.65, "Adequate pacing description")
            return (0.4, "Pacing needs more development")

        if dimension == "Property Completeness":
            prop_keywords = ["property", "attribute", "value", "config", "setting"]
            hits = sum(1 for k in prop_keywords if k in text_lower)
            if hits >= 1:
                return (0.7, f"{hits} property-related terms found")
            return (0.4, "Properties are not well defined")

        if dimension == "Behavioral Consistency":
            if word_count > 15:
                return (0.65, "Behavior has sufficient description")
            return (0.4, "Behavior description is minimal")

        if dimension == "Functional Correctness":
            code_keywords = ["function", "return", "if", "for", "class", "def"]
            hits = sum(1 for k in code_keywords if k in text_lower)
            if hits >= 2:
                return (0.7, f"Code structure detected ({hits} keywords)")
            return (0.4, "Code may not be executable")

        if dimension == "Safety Compliance":
            dangerous = ["import os", "eval(", "exec(", "subprocess", "__import__"]
            violations = sum(1 for d in dangerous if d in text)
            if violations == 0 and word_count > 5:
                return (0.8, "No safety violations detected")
            return (0.3, f"{violations} potential safety issues found")

        if dimension == "Readability":
            if word_count > 20:
                return (0.7, "Code appears readable with adequate structure")
            return (0.5, "Limited content for readability assessment")

        if dimension == "Character Voice":
            voice_keywords = ["tone", "voice", "character", "personality", "speaks"]
            hits = sum(1 for k in voice_keywords if k in text_lower)
            if hits >= 1:
                return (0.7, "Character voice considerations present")
            return (0.5, "Voice is not explicitly characterized")

        if dimension == "Coherence":
            if word_count > 25:
                return (0.7, "Sufficient length for coherent narrative")
            return (0.5, "Brief content makes coherence hard to assess")

        return (0.6, "Default evaluation — adequate")

    @staticmethod
    def _score_to_grade(score: float) -> EvaluationGrade:
        if score >= 0.85:
            return EvaluationGrade.EXCELLENT
        if score >= 0.70:
            return EvaluationGrade.GOOD
        if score >= 0.55:
            return EvaluationGrade.ADEQUATE
        if score >= 0.40:
            return EvaluationGrade.NEEDS_WORK
        return EvaluationGrade.POOR

    @staticmethod
    def _generate_dimension_suggestions(
        dimension: str, score: float, context: Dict[str, Any],
    ) -> List[str]:
        if score >= 0.75:
            return []
        suggestions_map = {
            "Concept Clarity": "Elaborate on the core concept with specific examples",
            "Mechanical Cohesion": "Describe how mechanics interact and complement each other",
            "Engagement Potential": "Add player motivation and reward structures",
            "Scope Feasibility": "Break down implementation into smaller phases",
            "Originality": "Introduce a unique twist on existing gameplay patterns",
            "Spatial Logic": "Specify distances and spatial relationships between elements",
            "Flow & Pacing": "Outline the progression timing and rhythm of the level",
            "Property Completeness": "Ensure all entity properties have defined values",
            "Behavioral Consistency": "Make sure behaviors align with the entity's purpose",
            "Functional Correctness": "Verify the code logic handles expected inputs",
            "Safety Compliance": "Remove potentially unsafe function calls or imports",
            "Readability": "Add meaningful variable names and logical structure",
            "Character Voice": "Define the character's personality and speech patterns",
            "Coherence": "Ensure the narrative follows a logical sequence",
        }
        default = f"Improve the {dimension.replace('_', ' ').lower()} of this content"
        return [suggestions_map.get(dimension, default)]

    @staticmethod
    def _categorize_dimensions(
        dimensions: List[DimensionScore],
    ) -> Tuple[List[str], List[str]]:
        strengths = [
            f"{d.dimension}: {d.evidence}"
            for d in dimensions if d.score >= 0.7
        ]
        weaknesses = [
            f"{d.dimension}: {d.evidence}"
            for d in dimensions if d.score < 0.55
        ]
        return strengths, weaknesses


_global_self_evaluator: Optional[SelfEvaluator] = None


def get_self_evaluator() -> SelfEvaluator:
    global _global_self_evaluator
    if _global_self_evaluator is None:
        _global_self_evaluator = SelfEvaluator()
    return _global_self_evaluator
