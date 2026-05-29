"""
SparkLabs Agent - AB Test Runner

A singleton system for AI-driven A/B testing of game features.
Designs experiments, splits player cohorts, collects metrics,
and determines statistical significance for game design decisions.

Architecture:
  ABTestRunner (singleton)
    |-- ExperimentConfig (experiment definition and metadata)
    |-- CohortResult (per-variant aggregated metric data)
    |-- TestReport (statistical analysis and recommendations)
"""

from __future__ import annotations

import math
import random
import statistics
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class ExperimentStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CohortSplit(Enum):
    EQUAL = "equal"
    WEIGHTED_A = "weighted_a"
    WEIGHTED_B = "weighted_b"
    ADAPTIVE = "adaptive"


class MetricType(Enum):
    RETENTION = "retention"
    ENGAGEMENT = "engagement"
    REVENUE = "revenue"
    COMPLETION_RATE = "completion_rate"
    SESSION_LENGTH = "session_length"
    FUNNEL_CONVERSION = "funnel_conversion"
    CUSTOM = "custom"


class SignificanceLevel(Enum):
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"
    P999 = "p999"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class ExperimentConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    hypothesis: str = ""
    variant_a: str = ""
    variant_b: str = ""
    cohort_split: CohortSplit = CohortSplit.EQUAL
    target_metric: MetricType = MetricType.ENGAGEMENT
    min_sample_size: int = 100
    duration_days: int = 7
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "hypothesis": self.hypothesis,
            "variant_a": self.variant_a,
            "variant_b": self.variant_b,
            "cohort_split": self.cohort_split.value,
            "target_metric": self.target_metric.value,
            "min_sample_size": self.min_sample_size,
            "duration_days": self.duration_days,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class CohortResult:
    experiment_id: str = ""
    variant: str = ""
    sample_count: int = 0
    metric_values: List[float] = field(default_factory=list)
    mean: float = 0.0
    std_dev: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    computed_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "variant": self.variant,
            "sample_count": self.sample_count,
            "metric_values": list(self.metric_values),
            "mean": self.mean,
            "std_dev": self.std_dev,
            "confidence_interval": list(self.confidence_interval),
            "computed_at": self.computed_at,
        }

    def recompute(self) -> None:
        if not self.metric_values:
            self.mean = 0.0
            self.std_dev = 0.0
            self.confidence_interval = (0.0, 0.0)
            self.sample_count = 0
            return

        self.sample_count = len(self.metric_values)
        self.mean = statistics.mean(self.metric_values)

        if self.sample_count >= 2:
            self.std_dev = statistics.stdev(self.metric_values)
            margin = 1.96 * self.std_dev / math.sqrt(self.sample_count)
            self.confidence_interval = (
                max(0.0, self.mean - margin),
                self.mean + margin,
            )
        else:
            self.std_dev = 0.0
            self.confidence_interval = (self.mean, self.mean)

        self.computed_at = _time_module.time()


@dataclass
class TestReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    experiment_id: str = ""
    winner: str = ""
    significance_level: SignificanceLevel = SignificanceLevel.P95
    recommendation: str = ""
    p_value: float = 1.0
    effect_size: float = 0.0
    is_significant: bool = False
    generated_at: float = field(default_factory=_time_module.time)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "winner": self.winner,
            "significance_level": self.significance_level.value,
            "recommendation": self.recommendation,
            "p_value": self.p_value,
            "effect_size": self.effect_size,
            "is_significant": self.is_significant,
            "generated_at": self.generated_at,
            "details": dict(self.details),
        }


# ------------------------------------------------------------------
# ABTestRunner Singleton
# ------------------------------------------------------------------


class ABTestRunner:
    """
    Singleton system for AI-driven A/B testing of game features.

    Manages the full experiment lifecycle: designing experiments,
    assigning players to cohorts, collecting metrics, performing
    statistical analysis, and generating actionable recommendations
    for game design decisions.
    """

    _instance: Optional[ABTestRunner] = None
    _lock = threading.RLock()

    def __new__(cls) -> ABTestRunner:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> ABTestRunner:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return
            self._experiments: Dict[str, ExperimentConfig] = {}
            self._cohorts: Dict[str, Dict[str, List[str]]] = {}
            self._results: Dict[str, Dict[str, CohortResult]] = {}
            self._player_assignments: Dict[str, Dict[str, str]] = {}
            self._stats: Dict[str, Any] = {
                "total_experiments_run": 0,
                "total_players_assigned": 0,
                "total_metrics_recorded": 0,
                "significant_results": 0,
                "inconclusive_results": 0,
            }
            self._initialized = True

    # ------------------------------------------------------------------
    # Experiment Management
    # ------------------------------------------------------------------

    def create_experiment(
        self,
        name: str,
        hypothesis: str,
        variant_a: str,
        variant_b: str,
        target_metric: MetricType = MetricType.ENGAGEMENT,
        cohort_split: CohortSplit = CohortSplit.EQUAL,
        min_sample_size: int = 100,
        duration_days: int = 7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExperimentConfig:
        with self._lock:
            config = ExperimentConfig(
                name=name,
                hypothesis=hypothesis,
                variant_a=variant_a,
                variant_b=variant_b,
                target_metric=target_metric,
                cohort_split=cohort_split,
                min_sample_size=min_sample_size,
                duration_days=duration_days,
                metadata=metadata or {},
            )
            self._experiments[config.id] = config

            self._cohorts[config.id] = {
                "A": [],
                "B": [],
            }
            self._results[config.id] = {
                "A": CohortResult(experiment_id=config.id, variant="A"),
                "B": CohortResult(experiment_id=config.id, variant="B"),
            }

            return config

    def get_experiment(self, experiment_id: str) -> Optional[ExperimentConfig]:
        return self._experiments.get(experiment_id)

    def list_experiments(
        self, status: Optional[ExperimentStatus] = None
    ) -> List[ExperimentConfig]:
        results = list(self._experiments.values())
        if status is not None:
            results = [e for e in results if e.status == status]
        return results

    def update_experiment(
        self,
        experiment_id: str,
        name: Optional[str] = None,
        hypothesis: Optional[str] = None,
        min_sample_size: Optional[int] = None,
        duration_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ExperimentConfig]:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return None

            if experiment.status not in (ExperimentStatus.DRAFT, ExperimentStatus.PAUSED):
                return None

            if name is not None:
                experiment.name = name
            if hypothesis is not None:
                experiment.hypothesis = hypothesis
            if min_sample_size is not None:
                experiment.min_sample_size = min_sample_size
            if duration_days is not None:
                experiment.duration_days = duration_days
            if metadata is not None:
                experiment.metadata.update(metadata)

            experiment.updated_at = _time_module.time()
            return experiment

    def delete_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            if experiment_id in self._experiments:
                del self._experiments[experiment_id]
                self._cohorts.pop(experiment_id, None)
                self._results.pop(experiment_id, None)
                keys_to_remove = [
                    pid
                    for pid, assignments in self._player_assignments.items()
                    if experiment_id in assignments
                ]
                for pid in keys_to_remove:
                    self._player_assignments[pid].pop(experiment_id, None)
                    if not self._player_assignments[pid]:
                        del self._player_assignments[pid]
                return True
            return False

    # ------------------------------------------------------------------
    # Experiment Lifecycle
    # ------------------------------------------------------------------

    def start_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return False
            if experiment.status not in (ExperimentStatus.DRAFT, ExperimentStatus.PAUSED):
                return False
            experiment.status = ExperimentStatus.RUNNING
            experiment.updated_at = _time_module.time()
            self._stats["total_experiments_run"] += 1
            return True

    def pause_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return False
            if experiment.status != ExperimentStatus.RUNNING:
                return False
            experiment.status = ExperimentStatus.PAUSED
            experiment.updated_at = _time_module.time()
            return True

    def resume_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return False
            if experiment.status != ExperimentStatus.PAUSED:
                return False
            experiment.status = ExperimentStatus.RUNNING
            experiment.updated_at = _time_module.time()
            return True

    def stop_experiment(self, experiment_id: str) -> Optional[TestReport]:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return None
            if experiment.status == ExperimentStatus.COMPLETED:
                return self._generate_report(experiment_id)

            experiment.status = ExperimentStatus.COMPLETED
            experiment.updated_at = _time_module.time()

            report = self._generate_report(experiment_id)
            if report.is_significant:
                self._stats["significant_results"] += 1
            else:
                self._stats["inconclusive_results"] += 1

            return report

    def archive_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return False
            if experiment.status != ExperimentStatus.COMPLETED:
                return False
            experiment.status = ExperimentStatus.ARCHIVED
            experiment.updated_at = _time_module.time()
            return True

    # ------------------------------------------------------------------
    # Cohort Assignment
    # ------------------------------------------------------------------

    def assign_cohort(self, player_id: str, experiment_id: str) -> Optional[str]:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return None
            if experiment.status != ExperimentStatus.RUNNING:
                return None

            if player_id not in self._player_assignments:
                self._player_assignments[player_id] = {}

            if experiment_id in self._player_assignments[player_id]:
                return self._player_assignments[player_id][experiment_id]

            variant = self._determine_variant(experiment)
            self._player_assignments[player_id][experiment_id] = variant
            self._cohorts[experiment_id][variant].append(player_id)
            self._stats["total_players_assigned"] += 1

            return variant

    def get_player_variant(
        self, player_id: str, experiment_id: str
    ) -> Optional[str]:
        assignments = self._player_assignments.get(player_id, {})
        return assignments.get(experiment_id)

    def get_cohort_members(
        self, experiment_id: str, variant: str
    ) -> List[str]:
        cohorts = self._cohorts.get(experiment_id, {})
        return list(cohorts.get(variant, []))

    def get_cohort_sizes(self, experiment_id: str) -> Dict[str, int]:
        cohorts = self._cohorts.get(experiment_id, {})
        return {v: len(players) for v, players in cohorts.items()}

    # ------------------------------------------------------------------
    # Metric Recording
    # ------------------------------------------------------------------

    def record_metric(
        self,
        player_id: str,
        experiment_id: str,
        metric_name: str,
        value: float,
    ) -> bool:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return False
            if experiment.status != ExperimentStatus.RUNNING:
                return False

            variant = self._player_assignments.get(player_id, {}).get(experiment_id)
            if variant is None:
                return False

            result = self._results[experiment_id][variant]
            result.metric_values.append(value)
            self._stats["total_metrics_recorded"] += 1
            return True

    def record_metrics_batch(
        self,
        experiment_id: str,
        entries: List[Dict[str, Any]],
    ) -> int:
        recorded = 0
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return 0
            if experiment.status != ExperimentStatus.RUNNING:
                return 0

            for entry in entries:
                player_id = entry.get("player_id", "")
                metric_name = entry.get("metric_name", "")
                value = entry.get("value", 0.0)
                if not player_id:
                    continue

                variant = self._player_assignments.get(player_id, {}).get(experiment_id)
                if variant is None:
                    continue

                result = self._results[experiment_id][variant]
                result.metric_values.append(float(value))
                recorded += 1

            self._stats["total_metrics_recorded"] += recorded
            return recorded

    # ------------------------------------------------------------------
    # Statistical Analysis
    # ------------------------------------------------------------------

    def analyze_results(self, experiment_id: str) -> Optional[TestReport]:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return None

            results = self._results.get(experiment_id)
            if results is None:
                return None

            result_a = results["A"]
            result_b = results["B"]

            result_a.recompute()
            result_b.recompute()

            report = self._compute_significance(experiment, result_a, result_b)
            return report

    def get_recommendation(self, experiment_id: str) -> Optional[str]:
        report = self.analyze_results(experiment_id)
        if report is None:
            return None
        return report.recommendation

    # ------------------------------------------------------------------
    # Stats and Summaries
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            active_count = len(
                [e for e in self._experiments.values() if e.status == ExperimentStatus.RUNNING]
            )
            completed_count = len(
                [e for e in self._experiments.values() if e.status == ExperimentStatus.COMPLETED]
            )
            draft_count = len(
                [e for e in self._experiments.values() if e.status == ExperimentStatus.DRAFT]
            )

            experiment_summaries = []
            for exp in self._experiments.values():
                cohorts = self._cohorts.get(exp.id, {})
                experiment_summaries.append({
                    "id": exp.id,
                    "name": exp.name,
                    "status": exp.status.value,
                    "target_metric": exp.target_metric.value,
                    "cohort_a_size": len(cohorts.get("A", [])),
                    "cohort_b_size": len(cohorts.get("B", [])),
                    "duration_days": exp.duration_days,
                })

            return {
                "total_experiments": len(self._experiments),
                "active_experiments": active_count,
                "completed_experiments": completed_count,
                "draft_experiments": draft_count,
                "total_experiments_run": self._stats["total_experiments_run"],
                "total_players_assigned": self._stats["total_players_assigned"],
                "total_metrics_recorded": self._stats["total_metrics_recorded"],
                "significant_results": self._stats["significant_results"],
                "inconclusive_results": self._stats["inconclusive_results"],
                "experiments": experiment_summaries,
            }

    def get_experiment_summary(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return None

            results = self._results.get(experiment_id, {})
            result_a = results.get("A")
            result_b = results.get("B")

            if result_a is not None:
                result_a.recompute()
            if result_b is not None:
                result_b.recompute()

            cohort_sizes = self.get_cohort_sizes(experiment_id)

            return {
                "experiment": experiment.to_dict(),
                "cohort_sizes": cohort_sizes,
                "result_a": result_a.to_dict() if result_a else None,
                "result_b": result_b.to_dict() if result_b else None,
                "total_samples": sum(cohort_sizes.values()),
                "is_sufficient_sample": sum(cohort_sizes.values()) >= experiment.min_sample_size,
            }

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def check_sample_sufficiency(self, experiment_id: str) -> bool:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return False
            cohort_sizes = self.get_cohort_sizes(experiment_id)
            total = sum(cohort_sizes.values())
            return total >= experiment.min_sample_size

    def get_minimum_detectable_effect(
        self, experiment_id: str, significance: SignificanceLevel = SignificanceLevel.P95
    ) -> Optional[float]:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return None

            results = self._results.get(experiment_id)
            if results is None:
                return None

            z_value = self._z_score_for_level(significance)
            n_a = len(results["A"].metric_values)
            n_b = len(results["B"].metric_values)

            if n_a < 2 or n_b < 2:
                return None

            pooled_std = math.sqrt(
                (statistics.variance(results["A"].metric_values) * (n_a - 1)
                 + statistics.variance(results["B"].metric_values) * (n_b - 1))
                / (n_a + n_b - 2)
            )

            return z_value * pooled_std * math.sqrt(1.0 / n_a + 1.0 / n_b)

    def reset(self) -> None:
        with self._lock:
            self._experiments.clear()
            self._cohorts.clear()
            self._results.clear()
            self._player_assignments.clear()
            self._stats = {
                "total_experiments_run": 0,
                "total_players_assigned": 0,
                "total_metrics_recorded": 0,
                "significant_results": 0,
                "inconclusive_results": 0,
            }

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_all_data(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "experiments": [e.to_dict() for e in self._experiments.values()],
                "cohorts": {
                    eid: {v: list(players) for v, players in cohorts.items()}
                    for eid, cohorts in self._cohorts.items()
                },
                "results": {
                    eid: {v: r.to_dict() for v, r in variant_results.items()}
                    for eid, variant_results in self._results.items()
                },
                "player_assignments": {
                    pid: dict(assignments)
                    for pid, assignments in self._player_assignments.items()
                },
                "stats": dict(self._stats),
                "exported_at": _time_module.time(),
                "version": "1.0",
            }

    def import_data(self, data: Dict[str, Any]) -> int:
        with self._lock:
            count = 0

            for edata in data.get("experiments", []):
                config = ExperimentConfig(
                    id=edata.get("id", uuid.uuid4().hex),
                    name=edata.get("name", ""),
                    hypothesis=edata.get("hypothesis", ""),
                    variant_a=edata.get("variant_a", ""),
                    variant_b=edata.get("variant_b", ""),
                    cohort_split=CohortSplit(edata.get("cohort_split", "equal")),
                    target_metric=MetricType(edata.get("target_metric", "engagement")),
                    min_sample_size=edata.get("min_sample_size", 100),
                    duration_days=edata.get("duration_days", 7),
                    status=ExperimentStatus(edata.get("status", "draft")),
                    created_at=edata.get("created_at", _time_module.time()),
                    updated_at=edata.get("updated_at", _time_module.time()),
                    metadata=edata.get("metadata", {}),
                )
                self._experiments[config.id] = config
                count += 1

            for eid, cohorts in data.get("cohorts", {}).items():
                if eid not in self._cohorts:
                    self._cohorts[eid] = {}
                for variant, players in cohorts.items():
                    self._cohorts[eid][variant] = list(players)
                    count += 1

            for eid, variant_results in data.get("results", {}).items():
                if eid not in self._results:
                    self._results[eid] = {}
                for variant, rdata in variant_results.items():
                    result = CohortResult(
                        experiment_id=rdata.get("experiment_id", eid),
                        variant=rdata.get("variant", variant),
                        metric_values=rdata.get("metric_values", []),
                        computed_at=rdata.get("computed_at", _time_module.time()),
                    )
                    result.recompute()
                    self._results[eid][variant] = result
                    count += 1

            for pid, assignments in data.get("player_assignments", {}).items():
                self._player_assignments[pid] = dict(assignments)
                count += 1

            imported_stats = data.get("stats", {})
            for key in self._stats:
                if key in imported_stats:
                    self._stats[key] = imported_stats[key]

            return count

    # ------------------------------------------------------------------
    # Internal: Cohort Determination
    # ------------------------------------------------------------------

    def _determine_variant(self, experiment: ExperimentConfig) -> str:
        split = experiment.cohort_split
        cohorts = self._cohorts.get(experiment.id, {})
        count_a = len(cohorts.get("A", []))
        count_b = len(cohorts.get("B", []))

        if split == CohortSplit.EQUAL:
            if count_a <= count_b:
                return "A"
            return "B"

        if split == CohortSplit.WEIGHTED_A:
            target_ratio = 0.7
            return self._weighted_assign(count_a, count_b, target_ratio)

        if split == CohortSplit.WEIGHTED_B:
            target_ratio = 0.3
            return self._weighted_assign(count_a, count_b, target_ratio)

        if split == CohortSplit.ADAPTIVE:
            return self._adaptive_assign(experiment.id)

        return "A"

    def _weighted_assign(
        self, count_a: int, count_b: int, target_ratio_a: float
    ) -> str:
        total = count_a + count_b
        if total == 0:
            current_ratio = 0.5
        else:
            current_ratio = count_a / total

        if current_ratio < target_ratio_a:
            if random.random() < 0.8:
                return "A"
            return "B"
        else:
            if random.random() < 0.8:
                return "B"
            return "A"

    def _adaptive_assign(self, experiment_id: str) -> str:
        results = self._results.get(experiment_id, {})
        result_a = results.get("A")
        result_b = results.get("B")

        if result_a is None or result_b is None:
            return random.choice(["A", "B"])

        n_a = len(result_a.metric_values)
        n_b = len(result_b.metric_values)

        if n_a < 10 or n_b < 10:
            if count_a := n_a <= n_b:
                return "A"
            return "B"

        mean_a = statistics.mean(result_a.metric_values) if result_a.metric_values else 0.0
        mean_b = statistics.mean(result_b.metric_values) if result_b.metric_values else 0.0

        if mean_a > mean_b:
            if random.random() < 0.75:
                return "A"
            return "B"
        elif mean_b > mean_a:
            if random.random() < 0.75:
                return "B"
            return "A"
        else:
            return random.choice(["A", "B"])

    # ------------------------------------------------------------------
    # Internal: Statistical Computation
    # ------------------------------------------------------------------

    def _generate_report(self, experiment_id: str) -> Optional[TestReport]:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return None

        results = self._results.get(experiment_id)
        if results is None:
            return None

        result_a = results["A"]
        result_b = results["B"]
        result_a.recompute()
        result_b.recompute()

        return self._compute_significance(experiment, result_a, result_b)

    def _compute_significance(
        self,
        experiment: ExperimentConfig,
        result_a: CohortResult,
        result_b: CohortResult,
    ) -> TestReport:
        n_a = result_a.sample_count
        n_b = result_b.sample_count
        mean_a = result_a.mean
        mean_b = result_b.mean
        std_a = result_a.std_dev
        std_b = result_b.std_dev

        report = TestReport(experiment_id=experiment.id)

        if n_a < 2 or n_b < 2:
            report.winner = "inconclusive"
            report.recommendation = (
                f"Insufficient sample data for experiment '{experiment.name}'. "
                f"Cohort A has {n_a} samples, Cohort B has {n_b} samples. "
                f"Need at least 2 samples per cohort for analysis."
            )
            report.p_value = 1.0
            report.effect_size = 0.0
            report.is_significant = False
            report.details = {
                "sample_a": n_a,
                "sample_b": n_b,
                "mean_a": mean_a,
                "mean_b": mean_b,
                "reason": "insufficient_data",
            }
            return report

        t_stat, p_value = self._welch_t_test(
            mean_a, std_a, n_a, mean_b, std_b, n_b
        )

        pooled_std = math.sqrt(
            ((n_a - 1) * std_a ** 2 + (n_b - 1) * std_b ** 2) / (n_a + n_b - 2)
        )

        if pooled_std > 0:
            effect_size = abs(mean_a - mean_b) / pooled_std
        else:
            effect_size = 0.0

        report.p_value = p_value
        report.effect_size = effect_size

        significance = self._determine_significance(p_value)
        report.significance_level = significance

        is_significant = p_value <= self._significance_thresholds()[significance]
        report.is_significant = is_significant

        if is_significant:
            if mean_a > mean_b:
                report.winner = "A"
                winner_label = experiment.variant_a
            else:
                report.winner = "B"
                winner_label = experiment.variant_b

            effect_desc = self._describe_effect_size(effect_size)
            report.recommendation = (
                f"Variant {report.winner} ('{winner_label}') is the statistically "
                f"significant winner for experiment '{experiment.name}' "
                f"(p={p_value:.4f}, d={effect_size:.3f}). "
                f"The observed effect is {effect_desc}. "
                f"Recommend adopting Variant {report.winner} as the preferred design."
            )
        else:
            report.winner = "inconclusive"
            if n_a + n_b < experiment.min_sample_size:
                report.recommendation = (
                    f"Results for '{experiment.name}' are not yet significant "
                    f"(p={p_value:.4f}). Current sample ({n_a + n_b}) is below "
                    f"the minimum ({experiment.min_sample_size}). "
                    f"Continue collecting data before making a decision."
                )
            else:
                min_diff = self._minimum_detectable_difference(
                    std_a, std_b, n_a, n_b
                )
                report.recommendation = (
                    f"No statistically significant difference detected for "
                    f"'{experiment.name}' (p={p_value:.4f}, d={effect_size:.3f}). "
                    f"With current sample sizes the minimum detectable effect is "
                    f"{min_diff:.3f}. Consider that the variants may be equivalent "
                    f"or run a larger experiment to detect smaller differences."
                )

        report.details = {
            "sample_a": n_a,
            "sample_b": n_b,
            "mean_a": mean_a,
            "mean_b": mean_b,
            "std_a": std_a,
            "std_b": std_b,
            "conf_interval_a": list(result_a.confidence_interval),
            "conf_interval_b": list(result_b.confidence_interval),
            "t_statistic": t_stat,
            "p_value": p_value,
            "effect_size_cohens_d": effect_size,
            "sufficient_sample": n_a + n_b >= experiment.min_sample_size,
        }

        report.generated_at = _time_module.time()
        return report

    @staticmethod
    def _welch_t_test(
        mean_a: float, std_a: float, n_a: int,
        mean_b: float, std_b: float, n_b: int,
    ) -> Tuple[float, float]:
        se_a_sq = (std_a ** 2) / n_a if n_a > 0 else 0.0
        se_b_sq = (std_b ** 2) / n_b if n_b > 0 else 0.0
        se_diff = math.sqrt(se_a_sq + se_b_sq)

        if se_diff == 0:
            return 0.0, 1.0

        t_stat = (mean_a - mean_b) / se_diff

        df_num = (se_a_sq + se_b_sq) ** 2
        df_den = (se_a_sq ** 2) / (n_a - 1) + (se_b_sq ** 2) / (n_b - 1)
        df = df_num / df_den if df_den > 0 else 1.0

        p_value = ABTestRunner._t_distribution_p_value(abs(t_stat), df)

        return t_stat, p_value

    @staticmethod
    def _t_distribution_p_value(t: float, df: float) -> float:
        if df <= 0:
            return 1.0

        x = df / (df + t * t)
        p = ABTestRunner._incomplete_beta(df / 2.0, 0.5, x)
        return p

    @staticmethod
    def _incomplete_beta(a: float, b: float, x: float) -> float:
        if x < 0.0 or x > 1.0:
            return 0.0
        if x == 0.0 or x == 1.0:
            return x

        max_iterations = 200
        eps = 1e-12

        if x > (a + 1.0) / (a + b + 2.0):
            return 1.0 - ABTestRunner._incomplete_beta(b, a, 1.0 - x)

        front = math.exp(
            math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
            + a * math.log(x) + b * math.log(1.0 - x)
        )

        f = 1.0
        c = 1.0
        d = 1.0 / (1.0 - (a + b) * x / (a + 1.0)) if abs(1.0 - (a + b) * x / (a + 1.0)) > eps else 1.0 / eps

        for n in range(1, max_iterations + 1):
            nf = float(n)

            d1 = -(nf * (b - nf) * x) / ((a + 2.0 * nf - 1.0) * (a + 2.0 * nf))
            d2 = (nf * (a + nf) * x) / ((a + 2.0 * nf) * (a + 2.0 * nf + 1.0))

            d = 1.0 / (d1 * d + 1.0) if abs(d1 * d + 1.0) > eps else 1.0 / eps
            c = d2 / c + 1.0 if abs(c) > eps else 1.0 + d2 / eps
            f *= c * d

            d = 1.0 / (d2 * d + 1.0) if abs(d2 * d + 1.0) > eps else 1.0 / eps
            c = d1 / c + 1.0 if abs(c) > eps else 1.0 + d1 / eps

            if abs(c * d - 1.0) < eps:
                break

        return front / (a * f)

    @staticmethod
    def _z_score_for_level(level: SignificanceLevel) -> float:
        thresholds = {
            SignificanceLevel.P90: 1.645,
            SignificanceLevel.P95: 1.960,
            SignificanceLevel.P99: 2.576,
            SignificanceLevel.P999: 3.291,
        }
        return thresholds.get(level, 1.960)

    @staticmethod
    def _significance_thresholds() -> Dict[SignificanceLevel, float]:
        return {
            SignificanceLevel.P90: 0.10,
            SignificanceLevel.P95: 0.05,
            SignificanceLevel.P99: 0.01,
            SignificanceLevel.P999: 0.001,
        }

    @staticmethod
    def _determine_significance(p_value: float) -> SignificanceLevel:
        if p_value <= 0.001:
            return SignificanceLevel.P999
        if p_value <= 0.01:
            return SignificanceLevel.P99
        if p_value <= 0.05:
            return SignificanceLevel.P95
        if p_value <= 0.10:
            return SignificanceLevel.P90
        return SignificanceLevel.P90

    @staticmethod
    def _describe_effect_size(d: float) -> str:
        if d < 0.2:
            return "negligible"
        if d < 0.5:
            return "small"
        if d < 0.8:
            return "medium"
        return "large"

    @staticmethod
    def _minimum_detectable_difference(
        std_a: float, std_b: float, n_a: int, n_b: int
    ) -> float:
        z = 1.96
        pooled_var = (std_a ** 2 / n_a) + (std_b ** 2 / n_b)
        if pooled_var <= 0:
            return 0.0
        return z * math.sqrt(pooled_var)

    def run_synthetic_trial(
        self,
        experiment_id: str,
        num_players: int = 200,
        effect_size_a: float = 0.0,
        effect_size_b: float = 0.3,
        noise_std: float = 0.5,
    ) -> Optional[TestReport]:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return None

            if experiment.status not in (ExperimentStatus.DRAFT, ExperimentStatus.PAUSED):
                return None

            experiment.status = ExperimentStatus.RUNNING
            experiment.updated_at = _time_module.time()
            self._stats["total_experiments_run"] += 1

            results_a = self._results[experiment_id]["A"]
            results_b = self._results[experiment_id]["B"]
            results_a.metric_values.clear()
            results_b.metric_values.clear()

            for i in range(num_players):
                player_id = f"synth_{experiment_id}_{i}"
                variant = self._determine_variant(experiment)
                self._player_assignments[player_id] = {experiment_id: variant}
                self._cohorts[experiment_id][variant].append(player_id)
                self._stats["total_players_assigned"] += 1

                if variant == "A":
                    value = effect_size_a + random.gauss(0, noise_std)
                    results_a.metric_values.append(value)
                else:
                    value = effect_size_b + random.gauss(0, noise_std)
                    results_b.metric_values.append(value)
                self._stats["total_metrics_recorded"] += 1

            report = self.stop_experiment(experiment_id)
            return report


# ------------------------------------------------------------------
# Module-level accessor
# ------------------------------------------------------------------


def get_ab_test_runner() -> ABTestRunner:
    return ABTestRunner.get_instance()