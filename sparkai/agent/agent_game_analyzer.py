"""
SparkLabs Agent - Game Design Analyzer

AI-driven game design quality analysis evaluating core gameplay
pillars. Assesses fun factor, balance, pacing, difficulty curves,
progression systems, and accessibility to produce actionable
design recommendations for AI-native game creation.

Architecture:
  GameAnalyzer
    |-- FunFactorHeuristic (engagement potential scoring)
    |-- BalanceChecker (multi-entity equilibrium analysis)
    |-- PacingProfiler (tension/rest cycle evaluation)
    |-- DifficultyCurveMapper (skill-to-challenge alignment)
    |-- ProgressionValidator (unlock sequencing review)
    |-- DesignReport (aggregated findings with severity)

Dimensions:
  - FUN_FACTOR: core loop engagement and reward satisfaction
  - BALANCE: entity/mechanic fairness across player options
  - PACING: tension-release rhythm and content density
  - DIFFICULTY: challenge ramp matching player skill growth
  - PROGRESSION: unlock sequence coherence and motivation
  - ACCESSIBILITY: barrier analysis for entry and mastery
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AnalysisDimension(Enum):
    FUN_FACTOR = "fun_factor"
    BALANCE = "balance"
    PACING = "pacing"
    DIFFICULTY_CURVE = "difficulty_curve"
    PROGRESSION = "progression"
    ACCESSIBILITY = "accessibility"
    REPLAYABILITY = "replayability"


class IssueSeverity(Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    SUGGESTION = "suggestion"


@dataclass
class DesignIssue:
    dimension: AnalysisDimension
    severity: IssueSeverity
    title: str
    description: str
    recommendation: str
    confidence: float = 1.0


@dataclass
class GameAnalysisReport:
    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    game_title: str = ""
    analyzed_at: float = field(default_factory=time.time)
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    issues: List[DesignIssue] = field(default_factory=list)
    overall_score: float = 0.0
    summary: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "game_title": self.game_title,
            "analyzed_at": self.analyzed_at,
            "dimension_scores": self.dimension_scores,
            "issues": [
                {
                    "dimension": i.dimension.value,
                    "severity": i.severity.value,
                    "title": i.title,
                    "description": i.description,
                    "recommendation": i.recommendation,
                }
                for i in self.issues
            ],
            "overall_score": self.overall_score,
            "summary": self.summary,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
        }


class GameAnalyzer:
    """
    Automated game design analysis for AI-native game creation.
    Evaluates core gameplay pillars and generates recommendations.
    """

    _instance: Optional[GameAnalyzer] = None

    @classmethod
    def get_instance(cls) -> GameAnalyzer:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._analysis_count: int = 0
        self._reports: List[GameAnalysisReport] = []
        self._dimension_weights: Dict[AnalysisDimension, float] = {
            AnalysisDimension.FUN_FACTOR: 0.30,
            AnalysisDimension.BALANCE: 0.25,
            AnalysisDimension.PACING: 0.15,
            AnalysisDimension.DIFFICULTY_CURVE: 0.10,
            AnalysisDimension.PROGRESSION: 0.10,
            AnalysisDimension.ACCESSIBILITY: 0.05,
            AnalysisDimension.REPLAYABILITY: 0.05,
        }

    def analyze(
        self,
        game_data: Dict[str, Any],
        dimensions: Optional[List[AnalysisDimension]] = None,
    ) -> GameAnalysisReport:
        if dimensions is None:
            dimensions = list(AnalysisDimension)

        report = GameAnalysisReport(
            game_title=game_data.get("title", "Untitled Game"),
        )
        issues: List[DesignIssue] = []

        if AnalysisDimension.FUN_FACTOR in dimensions:
            score, fun_issues = self._evaluate_fun_factor(game_data)
            report.dimension_scores["fun_factor"] = score
            issues.extend(fun_issues)

        if AnalysisDimension.BALANCE in dimensions:
            score, bal_issues = self._evaluate_balance(game_data)
            report.dimension_scores["balance"] = score
            issues.extend(bal_issues)

        if AnalysisDimension.PACING in dimensions:
            score, pac_issues = self._evaluate_pacing(game_data)
            report.dimension_scores["pacing"] = score
            issues.extend(pac_issues)

        if AnalysisDimension.DIFFICULTY_CURVE in dimensions:
            score, dif_issues = self._evaluate_difficulty(game_data)
            report.dimension_scores["difficulty_curve"] = score
            issues.extend(dif_issues)

        if AnalysisDimension.PROGRESSION in dimensions:
            score, pro_issues = self._evaluate_progression(game_data)
            report.dimension_scores["progression"] = score
            issues.extend(pro_issues)

        report.issues = issues
        report.overall_score = self._compute_overall(report.dimension_scores)
        report.strengths = self._extract_strengths(game_data)
        report.weaknesses = self._identify_weaknesses(issues)
        report.summary = self._generate_summary(report)

        self._analysis_count += 1
        self._reports.append(report)
        return report

    def _evaluate_fun_factor(
        self, game_data: Dict[str, Any]
    ) -> Tuple[float, List[DesignIssue]]:
        issues: List[DesignIssue] = []
        score = 0.7
        mechanics = game_data.get("mechanics", [])
        if not mechanics:
            issues.append(
                DesignIssue(
                    dimension=AnalysisDimension.FUN_FACTOR,
                    severity=IssueSeverity.MAJOR,
                    title="Undefined core mechanics",
                    description="No game mechanics specified. A clear core loop is essential for engagement.",
                    recommendation="Define 1-3 primary mechanics that form the core gameplay loop.",
                )
            )
            score -= 0.3

        feedback = game_data.get("feedback_systems", [])
        if not feedback:
            issues.append(
                DesignIssue(
                    dimension=AnalysisDimension.FUN_FACTOR,
                    severity=IssueSeverity.MINOR,
                    title="Limited player feedback",
                    description="No visual/audio feedback systems defined.",
                    recommendation="Add juice elements: screen shake, particles, sound effects for key actions.",
                )
            )
            score -= 0.1

        return max(0.0, min(1.0, score)), issues

    def _evaluate_balance(
        self, game_data: Dict[str, Any]
    ) -> Tuple[float, List[DesignIssue]]:
        issues: List[DesignIssue] = []
        score = 0.7
        entities = game_data.get("entities", [])
        if len(entities) > 5:
            score += 0.1
        if game_data.get("player_abilities", 0) > game_data.get("enemy_abilities", 0) * 2:
            issues.append(
                DesignIssue(
                    dimension=AnalysisDimension.BALANCE,
                    severity=IssueSeverity.MAJOR,
                    title="Ability imbalance",
                    description="Player has significantly more abilities than enemies. Risk of trivial gameplay.",
                    recommendation="Match enemy complexity to player toolset or limit player options per encounter.",
                )
            )
            score -= 0.15
        return max(0.0, min(1.0, score)), issues

    def _evaluate_pacing(
        self, game_data: Dict[str, Any]
    ) -> Tuple[float, List[DesignIssue]]:
        issues: List[DesignIssue] = []
        score = 0.7
        levels = game_data.get("levels", [])
        if not levels:
            issues.append(
                DesignIssue(
                    dimension=AnalysisDimension.PACING,
                    severity=IssueSeverity.MAJOR,
                    title="No level structure",
                    description="Without level definitions, pacing cannot be evaluated.",
                    recommendation="Define level sequence with alternating tension and rest phases.",
                )
            )
            score -= 0.2
        return max(0.0, min(1.0, score)), issues

    def _evaluate_difficulty(
        self, game_data: Dict[str, Any]
    ) -> Tuple[float, List[DesignIssue]]:
        score = 0.7
        issues: List[DesignIssue] = []
        if not game_data.get("difficulty_settings"):
            issues.append(
                DesignIssue(
                    dimension=AnalysisDimension.DIFFICULTY_CURVE,
                    severity=IssueSeverity.MINOR,
                    title="No difficulty configuration",
                    description="Difficulty settings help tailor experience.",
                    recommendation="Define difficulty tiers or adaptive difficulty parameters.",
                )
            )
            score -= 0.1
        return max(0.0, min(1.0, score)), issues

    def _evaluate_progression(
        self, game_data: Dict[str, Any]
    ) -> Tuple[float, List[DesignIssue]]:
        score = 0.7
        issues: List[DesignIssue] = []
        if not game_data.get("progression_system"):
            issues.append(
                DesignIssue(
                    dimension=AnalysisDimension.PROGRESSION,
                    severity=IssueSeverity.MAJOR,
                    title="No progression system",
                    description="Progression systems drive long-term player engagement.",
                    recommendation="Design unlockable content, skill trees, or narrative progression arcs.",
                )
            )
            score -= 0.2
        return max(0.0, min(1.0, score)), issues

    def _compute_overall(self, scores: Dict[str, float]) -> float:
        if not scores:
            return 0.0
        total = 0.0
        for dim, weight in self._dimension_weights.items():
            dim_name = dim.value
            if dim_name in scores:
                total += scores[dim_name] * weight
        return round(total, 3)

    def _extract_strengths(self, game_data: Dict[str, Any]) -> List[str]:
        strengths: List[str] = []
        if len(game_data.get("mechanics", [])) >= 2:
            strengths.append("Strong mechanical foundation with multiple interactive systems.")
        if game_data.get("narrative_elements"):
            strengths.append("Narrative integration enhances player immersion and motivation.")
        if game_data.get("multiplayer_support"):
            strengths.append("Multiplayer support significantly extends replayability.")
        return strengths

    def _identify_weaknesses(self, issues: List[DesignIssue]) -> List[str]:
        critical = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        major = [i for i in issues if i.severity == IssueSeverity.MAJOR]
        result: List[str] = []
        for i in critical:
            result.append(f"[CRITICAL] {i.title}")
        for i in major[:3]:
            result.append(f"[MAJOR] {i.title}")
        return result

    def _generate_summary(self, report: GameAnalysisReport) -> str:
        if report.overall_score >= 0.8:
            return f"Strong design foundation ({report.overall_score:.2f}). Minor refinements recommended."
        elif report.overall_score >= 0.6:
            return f"Adequate design ({report.overall_score:.2f}). Several areas need attention."
        else:
            return f"Significant design work needed ({report.overall_score:.2f}). Focus on core loop and balance."

    def get_stats(self) -> Dict[str, Any]:
        critical_issues = sum(
            1 for r in self._reports for i in r.issues if i.severity == IssueSeverity.CRITICAL
        )
        return {
            "total_analyses": self._analysis_count,
            "cached_reports": len(self._reports),
            "dimensions": [d.value for d in AnalysisDimension],
            "total_critical_issues": critical_issues,
        }

    def quick_scan(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        report = self.analyze(game_data, [AnalysisDimension.FUN_FACTOR, AnalysisDimension.BALANCE])
        return {
            "overall_score": report.overall_score,
            "issue_count": len(report.issues),
            "critical_issues": [i.title for i in report.issues if i.severity == IssueSeverity.CRITICAL],
        }


_game_analyzer = GameAnalyzer.get_instance()


def get_game_analyzer() -> GameAnalyzer:
    return _game_analyzer