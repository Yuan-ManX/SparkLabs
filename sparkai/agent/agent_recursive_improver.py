"""
SparkLabs Agent - Recursive Improver

A recursive self-improvement system for the SparkLabs AI-native game engine.
Iteratively analyzes artifacts across quality domains, applies improvement
strategies, measures deltas, and converges toward target quality thresholds.
Provides regression detection and historical tracking of all improvement cycles.

Architecture:
  RecursiveImprover
    |-- ImprovementDomain (quality assessment domain)
    |-- ImprovementStrategy (transformation approach)
    |-- QualityMetric (dimension-level measurement)
    |-- ImprovementCycle (single iteration record)
    |-- QualityReport (domain-level quality snapshot)
    |-- ImprovementArtifact (tracked improvement target)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ImprovementDomain(Enum):
    CODE_QUALITY = "code_quality"
    GAME_DESIGN = "game_design"
    ASSET_QUALITY = "asset_quality"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    NARRATIVE_COHERENCE = "narrative_coherence"


class ImprovementStrategy(Enum):
    REFACTOR = "refactor"
    OPTIMIZE = "optimize"
    ENHANCE = "enhance"
    SIMPLIFY = "simplify"
    DIVERSIFY = "diversify"


class QualityMetric(Enum):
    READABILITY = "readability"
    MAINTAINABILITY = "maintainability"
    EFFICIENCY = "efficiency"
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"


@dataclass
class ImprovementCycle:
    iteration: int = 0
    domain: ImprovementDomain = ImprovementDomain.CODE_QUALITY
    baseline_score: float = 0.0
    target_score: float = 0.8
    strategy_applied: ImprovementStrategy = ImprovementStrategy.REFACTOR
    result_score: float = 0.0
    delta: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def improved(self) -> bool:
        return self.delta > 0.0

    @property
    def converged(self) -> bool:
        return self.result_score >= self.target_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "domain": self.domain.value,
            "baseline_score": round(self.baseline_score, 4),
            "target_score": round(self.target_score, 4),
            "strategy_applied": self.strategy_applied.value,
            "result_score": round(self.result_score, 4),
            "delta": round(self.delta, 4),
            "improved": self.improved,
            "converged": self.converged,
            "timestamp": self.timestamp,
        }


@dataclass
class QualityReport:
    domain_scores: Dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    regressions: List[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_scores": {k: round(v, 4) for k, v in self.domain_scores.items()},
            "overall_score": round(self.overall_score, 4),
            "recommendations": self.recommendations,
            "regressions": self.regressions,
            "generated_at": self.generated_at,
        }


@dataclass
class ImprovementArtifact:
    artifact_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    artifact_type: str = ""
    before_state: Dict[str, Any] = field(default_factory=dict)
    after_state: Dict[str, Any] = field(default_factory=dict)
    transformation_log: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "transformation_log": self.transformation_log,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# Domain-specific baseline score profiles
_DOMAIN_BASELINES: Dict[ImprovementDomain, Dict[str, float]] = {
    ImprovementDomain.CODE_QUALITY: {
        QualityMetric.READABILITY.value: 0.6,
        QualityMetric.MAINTAINABILITY.value: 0.55,
        QualityMetric.EFFICIENCY.value: 0.5,
        QualityMetric.CORRECTNESS.value: 0.7,
        QualityMetric.COMPLETENESS.value: 0.6,
    },
    ImprovementDomain.GAME_DESIGN: {
        QualityMetric.READABILITY.value: 0.65,
        QualityMetric.MAINTAINABILITY.value: 0.55,
        QualityMetric.EFFICIENCY.value: 0.5,
        QualityMetric.CORRECTNESS.value: 0.6,
        QualityMetric.COMPLETENESS.value: 0.7,
    },
    ImprovementDomain.ASSET_QUALITY: {
        QualityMetric.READABILITY.value: 0.5,
        QualityMetric.MAINTAINABILITY.value: 0.5,
        QualityMetric.EFFICIENCY.value: 0.6,
        QualityMetric.CORRECTNESS.value: 0.55,
        QualityMetric.COMPLETENESS.value: 0.65,
    },
    ImprovementDomain.PERFORMANCE: {
        QualityMetric.READABILITY.value: 0.5,
        QualityMetric.MAINTAINABILITY.value: 0.5,
        QualityMetric.EFFICIENCY.value: 0.7,
        QualityMetric.CORRECTNESS.value: 0.6,
        QualityMetric.COMPLETENESS.value: 0.5,
    },
    ImprovementDomain.ACCESSIBILITY: {
        QualityMetric.READABILITY.value: 0.7,
        QualityMetric.MAINTAINABILITY.value: 0.55,
        QualityMetric.EFFICIENCY.value: 0.5,
        QualityMetric.CORRECTNESS.value: 0.6,
        QualityMetric.COMPLETENESS.value: 0.65,
    },
    ImprovementDomain.NARRATIVE_COHERENCE: {
        QualityMetric.READABILITY.value: 0.65,
        QualityMetric.MAINTAINABILITY.value: 0.5,
        QualityMetric.EFFICIENCY.value: 0.5,
        QualityMetric.CORRECTNESS.value: 0.6,
        QualityMetric.COMPLETENESS.value: 0.7,
    },
}

# Strategy impact factors per domain
_STRATEGY_IMPACT: Dict[ImprovementStrategy, float] = {
    ImprovementStrategy.REFACTOR: 0.08,
    ImprovementStrategy.OPTIMIZE: 0.06,
    ImprovementStrategy.ENHANCE: 0.10,
    ImprovementStrategy.SIMPLIFY: 0.07,
    ImprovementStrategy.DIVERSIFY: 0.05,
}


class RecursiveImprover:
    """
    Recursive self-improvement engine for iterative quality enhancement.

    Manages improvement artifacts through cycles of analysis, strategy
    application, and evaluation. Tracks convergence across quality domains
    and detects regressions. Uses thread-safe state management for
    concurrent agent workflows.
    """

    _instance: Optional["RecursiveImprover"] = None

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._artifacts: Dict[str, ImprovementArtifact] = {}
        self._cycles: Dict[str, List[ImprovementCycle]] = {}
        self._reports: Dict[str, List[QualityReport]] = {}
        self._regressions: List[Tuple[str, str, float]] = []
        self._total_cycles: int = 0
        self._converged_count: int = 0
        self._convergence_threshold: float = 0.001
        self._max_history_per_artifact: int = 200

    @classmethod
    def get_instance(cls) -> "RecursiveImprover":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def analyze_quality(
        self,
        artifact_id: str,
        domain: ImprovementDomain = ImprovementDomain.CODE_QUALITY,
    ) -> QualityReport:
        """
        Assess the current quality baseline for an artifact within a given domain.

        Evaluates all quality metrics and produces a QualityReport with
        per-dimension scores, an overall composite score, and recommendations
        for dimensions falling below acceptable thresholds.
        """
        baselines = _DOMAIN_BASELINES.get(domain, _DOMAIN_BASELINES[ImprovementDomain.CODE_QUALITY])
        domain_scores: Dict[str, float] = {}

        with self._lock:
            artifact = self._artifacts.get(artifact_id)
            state_hint = len(artifact.after_state) if artifact and artifact.after_state else 0

        for metric in QualityMetric:
            base = baselines.get(metric.value, 0.5)
            # Adjust score based on artifact maturity
            adjusted = min(1.0, base + state_hint * 0.02)
            domain_scores[metric.value] = adjusted

        overall = self._compute_overall_score(domain_scores)
        recommendations = self._generate_recommendations(domain_scores, domain)
        regressions = [
            desc for aid, desc, _ in self._regressions if aid == artifact_id
        ]

        report = QualityReport(
            domain_scores=domain_scores,
            overall_score=overall,
            recommendations=recommendations,
            regressions=regressions,
        )

        with self._lock:
            if artifact_id not in self._reports:
                self._reports[artifact_id] = []
            self._reports[artifact_id].append(report)

        return report

    def propose_improvements(
        self,
        artifact_id: str,
    ) -> List[Tuple[ImprovementStrategy, float]]:
        """
        Generate ranked improvement suggestions for an artifact.

        Returns a list of (strategy, expected_impact) tuples sorted
        by expected impact descending, based on the latest quality
        assessment.
        """
        reports = self._reports.get(artifact_id, [])
        if not reports:
            return [
                (ImprovementStrategy.ENHANCE, 0.1),
                (ImprovementStrategy.REFACTOR, 0.08),
                (ImprovementStrategy.OPTIMIZE, 0.06),
            ]

        latest = reports[-1]
        proposals: List[Tuple[ImprovementStrategy, float]] = []

        for strategy in ImprovementStrategy:
            impact = _STRATEGY_IMPACT.get(strategy, 0.05)
            # Boost impact for strategies recommended by the report
            for rec in latest.recommendations:
                if strategy.value in rec.lower():
                    impact *= 1.3
                    break
            proposals.append((strategy, min(impact, 0.15)))

        proposals.sort(key=lambda x: x[1], reverse=True)
        return proposals

    def apply_improvement(
        self,
        artifact_id: str,
        strategy: ImprovementStrategy = ImprovementStrategy.REFACTOR,
    ) -> Optional[ImprovementCycle]:
        """
        Execute one improvement iteration for an artifact using the given strategy.

        Captures the before-state, applies the strategy to compute a new score,
        and records the resulting ImprovementCycle.
        """
        with self._lock:
            artifact = self._artifacts.get(artifact_id)
            if artifact is None:
                artifact = ImprovementArtifact(
                    artifact_id=artifact_id,
                    artifact_type="generic",
                    before_state={"score": 0.5},
                )
                self._artifacts[artifact_id] = artifact

            existing_cycles = self._cycles.get(artifact_id, [])
            iteration = len(existing_cycles) + 1

            # Determine the active domain from the last report
            reports = self._reports.get(artifact_id, [])
            if reports:
                domain_name = max(reports[-1].domain_scores, key=reports[-1].domain_scores.get)
                # Map metric name to ImprovementDomain
                domain = self._metric_to_domain(domain_name)
            else:
                domain = ImprovementDomain.CODE_QUALITY

            baseline_score = existing_cycles[-1].result_score if existing_cycles else 0.5
            target_score = max(0.8, baseline_score + 0.05)

            # Compute result score with diminishing returns
            impact = _STRATEGY_IMPACT.get(strategy, 0.05)
            result_score = min(1.0, baseline_score + impact * (1.0 - baseline_score))
            delta = result_score - baseline_score

            cycle = ImprovementCycle(
                iteration=iteration,
                domain=domain,
                baseline_score=baseline_score,
                target_score=target_score,
                strategy_applied=strategy,
                result_score=result_score,
                delta=delta,
            )

            if artifact_id not in self._cycles:
                self._cycles[artifact_id] = []
            self._cycles[artifact_id].append(cycle)
            if len(self._cycles[artifact_id]) > self._max_history_per_artifact:
                self._cycles[artifact_id] = self._cycles[artifact_id][-self._max_history_per_artifact:]

            # Update artifact state
            artifact.after_state["score"] = result_score
            artifact.after_state["iteration"] = iteration
            artifact.transformation_log.append(
                f"Iteration {iteration}: {strategy.value} -> {result_score:.4f} (delta: {delta:+.4f})"
            )
            artifact.updated_at = time.time()

            self._total_cycles += 1
            if cycle.converged:
                self._converged_count += 1

        return cycle

    def evaluate_improvement(
        self,
        artifact_id: str,
    ) -> Optional[float]:
        """
        Measure the quality delta for an artifact's most recent improvement.

        Returns the delta score of the latest cycle, or None if no cycles exist.
        """
        with self._lock:
            cycles = self._cycles.get(artifact_id, [])
            if not cycles:
                return None
            return cycles[-1].delta

    def run_improvement_cycle(
        self,
        artifact_id: str,
        max_iterations: int = 10,
    ) -> List[ImprovementCycle]:
        """
        Run recursive improvement until convergence or max iterations reached.

        Repeatedly analyzes quality, proposes strategies, applies the best one,
        and evaluates results. Stops when the delta falls below the convergence
        threshold or the maximum iteration count is reached.
        """
        results: List[ImprovementCycle] = []

        for i in range(max_iterations):
            report = self.analyze_quality(artifact_id)

            proposals = self.propose_improvements(artifact_id)
            if not proposals:
                break

            best_strategy, _ = proposals[0]
            cycle = self.apply_improvement(artifact_id, best_strategy)
            if cycle is None:
                break

            results.append(cycle)

            # Check convergence
            if abs(cycle.delta) < self._convergence_threshold:
                break

        return results

    def detect_regressions(self) -> List[Tuple[str, str, float]]:
        """
        Identify quality drops across all tracked artifacts.

        Scans all improvement cycles and flags any where the result score
        is lower than the baseline score (negative delta), indicating a
        regression in quality.
        """
        with self._lock:
            self._regressions.clear()

            for artifact_id, cycles in self._cycles.items():
                if len(cycles) < 2:
                    continue
                for i in range(1, len(cycles)):
                    prev_score = cycles[i - 1].result_score
                    curr_score = cycles[i].result_score
                    if curr_score < prev_score:
                        drop = prev_score - curr_score
                        description = (
                            f"Quality dropped from {prev_score:.4f} to {curr_score:.4f} "
                            f"at iteration {cycles[i].iteration} using {cycles[i].strategy_applied.value}"
                        )
                        self._regressions.append((artifact_id, description, drop))

            return list(self._regressions)

    def get_improvement_history(
        self,
        artifact_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Return all improvement cycles for a given artifact.

        Returns a chronologically ordered list of cycle dictionaries.
        """
        with self._lock:
            cycles = self._cycles.get(artifact_id, [])
            return [c.to_dict() for c in cycles]

    def get_stats(self) -> Dict[str, Any]:
        """
        Return aggregate statistics about the improvement system.

        Includes total cycles, convergence rate, artifact count,
        regression count, and per-domain cycle distribution.
        """
        with self._lock:
            domain_counts: Dict[str, int] = {}
            for cycles in self._cycles.values():
                for c in cycles:
                    domain_counts[c.domain.value] = domain_counts.get(c.domain.value, 0) + 1

            strategy_counts: Dict[str, int] = {}
            for cycles in self._cycles.values():
                for c in cycles:
                    strategy_counts[c.strategy_applied.value] = (
                        strategy_counts.get(c.strategy_applied.value, 0) + 1
                    )

            return {
                "total_cycles": self._total_cycles,
                "total_artifacts": len(self._artifacts),
                "converged_count": self._converged_count,
                "convergence_rate": round(
                    self._converged_count / max(self._total_cycles, 1), 4
                ),
                "regression_count": len(self._regressions),
                "by_domain": domain_counts,
                "by_strategy": strategy_counts,
                "threshold": self._convergence_threshold,
            }

    @staticmethod
    def _compute_overall_score(domain_scores: Dict[str, float]) -> float:
        if not domain_scores:
            return 0.0
        return round(sum(domain_scores.values()) / len(domain_scores), 4)

    @staticmethod
    def _generate_recommendations(
        domain_scores: Dict[str, float],
        domain: ImprovementDomain,
    ) -> List[str]:
        recommendations: List[str] = []

        metric_strategy_map = {
            QualityMetric.READABILITY.value: (ImprovementStrategy.REFACTOR, "Consider refactoring for clearer structure"),
            QualityMetric.MAINTAINABILITY.value: (ImprovementStrategy.SIMPLIFY, "Simplify the design to improve maintainability"),
            QualityMetric.EFFICIENCY.value: (ImprovementStrategy.OPTIMIZE, "Optimize performance-sensitive sections"),
            QualityMetric.CORRECTNESS.value: (ImprovementStrategy.ENHANCE, "Enhance with additional validation logic"),
            QualityMetric.COMPLETENESS.value: (ImprovementStrategy.DIVERSIFY, "Diversify the coverage to improve completeness"),
        }

        for metric_name, score in domain_scores.items():
            if score < 0.6:
                strategy, message = metric_strategy_map.get(
                    metric_name,
                    (ImprovementStrategy.ENHANCE, f"Improve {metric_name}"),
                )
                recommendations.append(
                    f"[{metric_name}: {score:.2f}] {message} via {strategy.value}"
                )

        if not recommendations:
            recommendations.append("All metrics are at acceptable levels — maintain current quality")

        return recommendations

    @staticmethod
    def _metric_to_domain(metric_name: str) -> ImprovementDomain:
        metric_domain_map = {
            QualityMetric.READABILITY.value: ImprovementDomain.CODE_QUALITY,
            QualityMetric.MAINTAINABILITY.value: ImprovementDomain.CODE_QUALITY,
            QualityMetric.EFFICIENCY.value: ImprovementDomain.PERFORMANCE,
            QualityMetric.CORRECTNESS.value: ImprovementDomain.CODE_QUALITY,
            QualityMetric.COMPLETENESS.value: ImprovementDomain.GAME_DESIGN,
        }
        return metric_domain_map.get(metric_name, ImprovementDomain.CODE_QUALITY)


def get_recursive_improver() -> RecursiveImprover:
    return RecursiveImprover.get_instance()