"""
SparkAI Agent - Game Evaluator Engine

A comprehensive game quality evaluation pipeline for the AI-native
game engine. Scores games across Build Health, Visual Usability,
and Intent Alignment dimensions with detailed metrics and reports.

Architecture:
  GameEvaluatorEngine
    |-- EvaluationDimension (scoring dimension)
    |-- EvaluationMetric (individual metric within a dimension)
    |-- EvaluationReport (comprehensive evaluation results)
    |-- EvaluationBenchmark (reference benchmark for scoring)
    |-- EvaluationComparison (cross-game comparison)
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EvalDimension(Enum):
    BUILD_HEALTH = "build_health"
    VISUAL_USABILITY = "visual_usability"
    INTENT_ALIGNMENT = "intent_alignment"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    ENGAGEMENT = "engagement"


class MetricType(Enum):
    BINARY = "binary"
    PERCENTAGE = "percentage"
    SCORE = "score"
    RATING = "rating"
    COUNT = "count"
    DURATION = "duration"


class ReportStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SeverityLevel(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class EvaluationMetric:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    dimension: EvalDimension = EvalDimension.BUILD_HEALTH
    metric_type: MetricType = MetricType.SCORE
    value: float = 0.0
    max_value: float = 100.0
    weight: float = 1.0
    threshold_pass: float = 60.0
    threshold_good: float = 80.0
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "dimension": self.dimension.value,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "max_value": self.max_value,
            "weight": self.weight,
            "normalized_score": self.value / self.max_value if self.max_value > 0 else 0.0,
            "severity": self._severity().value,
            "passed": self.value >= self.threshold_pass,
            "good": self.value >= self.threshold_good,
            "description": self.description,
            "details": self.details,
        }

    def _severity(self) -> SeverityLevel:
        ratio = self.value / self.max_value if self.max_value > 0 else 0.0
        if ratio >= 0.9:
            return SeverityLevel.EXCELLENT
        elif ratio >= 0.75:
            return SeverityLevel.GOOD
        elif ratio >= 0.6:
            return SeverityLevel.ACCEPTABLE
        elif ratio >= 0.4:
            return SeverityLevel.POOR
        else:
            return SeverityLevel.CRITICAL


@dataclass
class EvaluationReport:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    game_id: str = ""
    game_name: str = ""
    prompt: str = ""
    status: ReportStatus = ReportStatus.PENDING
    metrics: List[EvaluationMetric] = field(default_factory=list)
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    build_passed: bool = False
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    evaluated_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "game_id": self.game_id,
            "game_name": self.game_name,
            "prompt": self.prompt,
            "status": self.status.value,
            "metric_count": len(self.metrics),
            "metrics": [m.to_dict() for m in self.metrics],
            "dimension_scores": self.dimension_scores,
            "overall_score": round(self.overall_score, 2),
            "build_passed": self.build_passed,
            "summary": self.summary,
            "recommendations": self.recommendations,
            "evaluated_at": self.evaluated_at,
            "created_at": self.created_at,
        }


@dataclass
class EvaluationBenchmark:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    dimension: EvalDimension = EvalDimension.BUILD_HEALTH
    metric_name: str = ""
    min_score: float = 0.0
    avg_score: float = 50.0
    max_score: float = 100.0
    sample_count: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "dimension": self.dimension.value,
            "metric_name": self.metric_name,
            "min_score": self.min_score,
            "avg_score": self.avg_score,
            "max_score": self.max_score,
            "sample_count": self.sample_count,
            "created_at": self.created_at,
        }


class GameEvaluatorEngine:
    """
    Central game quality evaluation system for the SparkLabs AI-native game engine.

    Scores games across Build Health, Visual Usability, and Intent Alignment
    dimensions with detailed metrics and actionable recommendations.
    """

    def __init__(self) -> None:
        self._reports: List[EvaluationReport] = {}
        self._benchmarks: Dict[str, EvaluationBenchmark] = {}
        self._report_count: int = 0
        self._seed_benchmarks()

    def _seed_benchmarks(self) -> None:
        benchmarks = [
            ("build_success", "Build Success Rate", EvalDimension.BUILD_HEALTH,
             "build_success_rate", 0.0, 85.0, 100.0, 150),
            ("zero_errors", "Zero Runtime Errors", EvalDimension.BUILD_HEALTH,
             "runtime_error_count", 0.0, 90.0, 100.0, 150),
            ("asset_load", "Asset Load Success", EvalDimension.BUILD_HEALTH,
             "asset_load_rate", 50.0, 88.0, 100.0, 120),
            ("visual_coherence", "Visual Coherence", EvalDimension.VISUAL_USABILITY,
             "visual_coherence_score", 20.0, 65.0, 95.0, 100),
            ("ui_responsiveness", "UI Responsiveness", EvalDimension.VISUAL_USABILITY,
             "ui_response_score", 30.0, 70.0, 98.0, 100),
            ("visual_polish", "Visual Polish", EvalDimension.VISUAL_USABILITY,
             "visual_polish_score", 10.0, 55.0, 90.0, 100),
            ("prompt_match", "Prompt Match", EvalDimension.INTENT_ALIGNMENT,
             "prompt_alignment_score", 15.0, 60.0, 95.0, 150),
            ("genre_match", "Genre Match", EvalDimension.INTENT_ALIGNMENT,
             "genre_alignment_score", 20.0, 65.0, 92.0, 150),
            ("feature_coverage", "Feature Coverage", EvalDimension.INTENT_ALIGNMENT,
             "feature_coverage_score", 10.0, 55.0, 88.0, 150),
            ("fps_stable", "FPS Stability", EvalDimension.PERFORMANCE,
             "fps_stability_score", 30.0, 72.0, 98.0, 100),
            ("load_time", "Load Time", EvalDimension.PERFORMANCE,
             "load_time_score", 20.0, 68.0, 95.0, 100),
        ]

        for bid, name, dim, metric, min_s, avg_s, max_s, samples in benchmarks:
            benchmark = EvaluationBenchmark(
                id=bid,
                name=name,
                dimension=dim,
                metric_name=metric,
                min_score=min_s,
                avg_score=avg_s,
                max_score=max_s,
                sample_count=samples,
            )
            self._benchmarks[bid] = benchmark

    def evaluate_game(
        self,
        game_id: str,
        game_name: str = "",
        prompt: str = "",
        build_passed: bool = True,
        runtime_errors: int = 0,
        asset_load_rate: float = 100.0,
        visual_coherence: float = 70.0,
        ui_responsiveness: float = 75.0,
        visual_polish: float = 60.0,
        prompt_alignment: float = 65.0,
        genre_alignment: float = 70.0,
        feature_coverage: float = 55.0,
        fps_stability: float = 80.0,
        load_time_score: float = 75.0,
    ) -> EvaluationReport:
        report = EvaluationReport(
            game_id=game_id,
            game_name=game_name,
            prompt=prompt,
            status=ReportStatus.RUNNING,
            build_passed=build_passed,
        )

        metrics_data = [
            ("Build Success", EvalDimension.BUILD_HEALTH, 100.0 if build_passed else 0.0, 100.0, 3.0, 60.0, 80.0),
            ("Runtime Error Count", EvalDimension.BUILD_HEALTH, max(0, 100 - runtime_errors * 20), 100.0, 2.0, 60.0, 80.0),
            ("Asset Load Rate", EvalDimension.BUILD_HEALTH, asset_load_rate, 100.0, 1.5, 70.0, 90.0),
            ("Visual Coherence", EvalDimension.VISUAL_USABILITY, visual_coherence, 100.0, 2.0, 50.0, 75.0),
            ("UI Responsiveness", EvalDimension.VISUAL_USABILITY, ui_responsiveness, 100.0, 1.5, 60.0, 80.0),
            ("Visual Polish", EvalDimension.VISUAL_USABILITY, visual_polish, 100.0, 1.0, 40.0, 70.0),
            ("Prompt Alignment", EvalDimension.INTENT_ALIGNMENT, prompt_alignment, 100.0, 3.0, 50.0, 75.0),
            ("Genre Alignment", EvalDimension.INTENT_ALIGNMENT, genre_alignment, 100.0, 2.0, 55.0, 80.0),
            ("Feature Coverage", EvalDimension.INTENT_ALIGNMENT, feature_coverage, 100.0, 2.5, 40.0, 70.0),
            ("FPS Stability", EvalDimension.PERFORMANCE, fps_stability, 100.0, 1.5, 60.0, 85.0),
            ("Load Time", EvalDimension.PERFORMANCE, load_time_score, 100.0, 1.0, 55.0, 80.0),
        ]

        for name, dim, value, max_v, weight, thresh_pass, thresh_good in metrics_data:
            metric = EvaluationMetric(
                name=name,
                dimension=dim,
                value=value,
                max_value=max_v,
                weight=weight,
                threshold_pass=thresh_pass,
                threshold_good=thresh_good,
            )
            report.metrics.append(metric)

        dimension_weights: Dict[str, List[Tuple[float, float]]] = {}
        for metric in report.metrics:
            dim = metric.dimension.value
            dimension_weights.setdefault(dim, []).append((metric.value / metric.max_value, metric.weight))

        for dim, scores_weights in dimension_weights.items():
            total_weight = sum(w for _, w in scores_weights)
            if total_weight > 0:
                weighted_sum = sum(s * w for s, w in scores_weights)
                report.dimension_scores[dim] = round(weighted_sum / total_weight * 100, 2)
            else:
                report.dimension_scores[dim] = 0.0

        total_weight = sum(m.weight for m in report.metrics)
        if total_weight > 0:
            weighted_sum = sum((m.value / m.max_value) * m.weight for m in report.metrics)
            report.overall_score = round(weighted_sum / total_weight * 100, 2)
        else:
            report.overall_score = 0.0

        report.recommendations = self._generate_recommendations(report)
        report.summary = self._generate_summary(report)
        report.status = ReportStatus.COMPLETED
        report.evaluated_at = time.time()

        self._reports[report.id] = report
        self._report_count += 1
        return report

    def _generate_recommendations(self, report: EvaluationReport) -> List[str]:
        recs: List[str] = []
        for metric in report.metrics:
            if metric.value < metric.threshold_pass:
                if metric.dimension == EvalDimension.BUILD_HEALTH:
                    recs.append(f"Fix {metric.name}: current score {metric.value:.0f}% is below passing threshold")
                elif metric.dimension == EvalDimension.VISUAL_USABILITY:
                    recs.append(f"Improve {metric.name}: consider adjusting visual elements and layout")
                elif metric.dimension == EvalDimension.INTENT_ALIGNMENT:
                    recs.append(f"Realign {metric.name}: game output does not match the intended design")
                elif metric.dimension == EvalDimension.PERFORMANCE:
                    recs.append(f"Optimize {metric.name}: performance is below acceptable levels")
            elif metric.value < metric.threshold_good:
                if metric.dimension == EvalDimension.VISUAL_USABILITY:
                    recs.append(f"Polish {metric.name}: minor improvements would elevate quality")
        return recs

    def _generate_summary(self, report: EvaluationReport) -> str:
        dims = report.dimension_scores
        parts: List[str] = []

        if EvalDimension.BUILD_HEALTH.value in dims:
            score = dims[EvalDimension.BUILD_HEALTH.value]
            parts.append(f"Build Health: {score:.0f}%")
        if EvalDimension.VISUAL_USABILITY.value in dims:
            score = dims[EvalDimension.VISUAL_USABILITY.value]
            parts.append(f"Visual Usability: {score:.0f}%")
        if EvalDimension.INTENT_ALIGNMENT.value in dims:
            score = dims[EvalDimension.INTENT_ALIGNMENT.value]
            parts.append(f"Intent Alignment: {score:.0f}%")
        if EvalDimension.PERFORMANCE.value in dims:
            score = dims[EvalDimension.PERFORMANCE.value]
            parts.append(f"Performance: {score:.0f}%")

        overall = report.overall_score
        grade = "A" if overall >= 90 else "B" if overall >= 75 else "C" if overall >= 60 else "D" if overall >= 40 else "F"

        return f"Overall: {overall:.0f}% (Grade {grade}) | {' | '.join(parts)}"

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        report = self._reports.get(report_id)
        if report:
            return report.to_dict()
        return None

    def list_reports(self, game_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        reports = list(self._reports.values())
        if game_id:
            reports = [r for r in reports if r.game_id == game_id]
        reports.sort(key=lambda r: r.created_at, reverse=True)
        return [r.to_dict() for r in reports[:limit]]

    def list_benchmarks(self, dimension: Optional[EvalDimension] = None) -> List[Dict[str, Any]]:
        benchmarks = list(self._benchmarks.values())
        if dimension:
            benchmarks = [b for b in benchmarks if b.dimension == dimension]
        return [b.to_dict() for b in benchmarks]

    def compare_games(self, report_ids: List[str]) -> Optional[Dict[str, Any]]:
        reports = [self._reports.get(rid) for rid in report_ids]
        reports = [r for r in reports if r is not None]

        if len(reports) < 2:
            return None

        comparison: Dict[str, Any] = {
            "game_count": len(reports),
            "games": [],
            "dimension_comparison": {},
        }

        for report in reports:
            comparison["games"].append({
                "game_id": report.game_id,
                "game_name": report.game_name,
                "overall_score": report.overall_score,
                "dimension_scores": report.dimension_scores,
            })

        all_dimensions: Set[str] = set()
        for report in reports:
            all_dimensions.update(report.dimension_scores.keys())

        for dim in all_dimensions:
            scores = [r.dimension_scores.get(dim, 0.0) for r in reports]
            comparison["dimension_comparison"][dim] = {
                "scores": scores,
                "average": round(sum(scores) / len(scores), 2),
                "best": max(scores),
                "worst": min(scores),
                "range": round(max(scores) - min(scores), 2),
            }

        return comparison

    def get_stats(self) -> Dict[str, Any]:
        dimension_avgs: Dict[str, List[float]] = {}
        for report in self._reports.values():
            for dim, score in report.dimension_scores.items():
                dimension_avgs.setdefault(dim, []).append(score)

        avg_by_dim = {dim: round(sum(scores) / len(scores), 2) for dim, scores in dimension_avgs.items()}

        overall_scores = [r.overall_score for r in self._reports.values()]
        avg_overall = round(sum(overall_scores) / len(overall_scores), 2) if overall_scores else 0.0

        return {
            "total_reports": self._report_count,
            "total_benchmarks": len(self._benchmarks),
            "avg_overall_score": avg_overall,
            "avg_by_dimension": avg_by_dim,
            "grade_distribution": self._grade_distribution(),
        }

    def _grade_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for report in self._reports.values():
            score = report.overall_score
            grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"
            dist[grade] += 1
        return dist


_global_evaluator: Optional[GameEvaluatorEngine] = None


def get_game_evaluator() -> GameEvaluatorEngine:
    global _global_evaluator
    if _global_evaluator is None:
        _global_evaluator = GameEvaluatorEngine()
    return _global_evaluator
