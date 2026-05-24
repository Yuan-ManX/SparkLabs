"""
SparkLabs Agent - Experiment Framework

A/B testing and behavioral parameter experimentation for agents.
Provides creation and management of experiments with multiple variant
groups, trial recording, statistical comparison between variants,
and comprehensive reporting across latency, accuracy, creativity,
token usage, and user satisfaction metrics.

Architecture:
  AgentExperimentFramework
    |-- ExperimentConfig (defines experiment name, variants, metrics)
    |-- VariantGroup (isolated parameter set for a single variant)
    |-- TrialResult (individual trial outcome with metric snapshots)
    |-- ExperimentReport (aggregated results with statistical analysis)
"""

from __future__ import annotations

import math
import statistics
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ExperimentStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ANALYZED = "analyzed"


class VariantStrategy(Enum):
    RANDOM = "random"
    ROUND_ROBIN = "round_robin"
    THOMPSON_SAMPLING = "thompson_sampling"
    EPSILON_GREEDY = "epsilon_greedy"


class MetricTarget(Enum):
    LATENCY = "latency"
    ACCURACY = "accuracy"
    CREATIVITY = "creativity"
    TOKEN_USAGE = "token_usage"
    USER_SATISFACTION = "user_satisfaction"


@dataclass
class ExperimentConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    status: ExperimentStatus = ExperimentStatus.DRAFT
    variant_ids: List[str] = field(default_factory=list)
    metric_targets: List[MetricTarget] = field(default_factory=list)
    strategy: VariantStrategy = VariantStrategy.ROUND_ROBIN
    epsilon: float = 0.1
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "variant_ids": self.variant_ids,
            "metric_targets": [m.value for m in self.metric_targets],
            "strategy": self.strategy.value,
            "epsilon": self.epsilon,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


@dataclass
class VariantGroup:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    experiment_id: str = ""
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    trial_count: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "weight": self.weight,
            "trial_count": self.trial_count,
            "created_at": self.created_at,
        }


@dataclass
class TrialResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    experiment_id: str = ""
    variant_id: str = ""
    session_id: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    success: bool = True
    recorded_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "variant_id": self.variant_id,
            "session_id": self.session_id,
            "metrics": self.metrics,
            "tags": self.tags,
            "success": self.success,
            "recorded_at": self.recorded_at,
        }


@dataclass
class ExperimentReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    experiment_id: str = ""
    total_trials: int = 0
    variant_summaries: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    pairwise_comparisons: List[Dict[str, Any]] = field(default_factory=list)
    winning_variant_id: str = ""
    confidence_level: float = 0.0
    statistical_tests: Dict[str, Any] = field(default_factory=dict)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "total_trials": self.total_trials,
            "variant_summaries": self.variant_summaries,
            "pairwise_comparisons": self.pairwise_comparisons,
            "winning_variant_id": self.winning_variant_id,
            "confidence_level": self.confidence_level,
            "statistical_tests": self.statistical_tests,
            "generated_at": self.generated_at,
        }


class AgentExperimentFramework:
    """A/B testing and behavioral parameter experimentation for agents."""

    _instance: Optional["AgentExperimentFramework"] = None
    _lock = threading.RLock()

    _DEFAULT_EPSILON: float = 0.1
    _DEFAULT_WEIGHT: float = 1.0
    _MIN_TRIALS_FOR_ANALYSIS: int = 10
    _MAX_EXPERIMENTS: int = 100
    _CONFIDENCE_THRESHOLD: float = 0.95

    def __init__(self) -> None:
        self._experiments: Dict[str, ExperimentConfig] = {}
        self._variants: Dict[str, VariantGroup] = {}
        self._trials: Dict[str, List[TrialResult]] = {}
        self._reports: Dict[str, ExperimentReport] = {}
        self._round_robin_counters: Dict[str, int] = {}
        self._bandit_counters: Dict[str, Dict[str, int]] = {}

    @classmethod
    def get_instance(cls) -> "AgentExperimentFramework":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Experiment Lifecycle ----

    def create_experiment(self,
                          name: str,
                          variants: Optional[List[Dict[str, Any]]] = None,
                          metrics: Optional[List[str]] = None,
                          strategy: str = "round_robin") -> ExperimentConfig:
        with self._lock:
            if len(self._experiments) >= self._MAX_EXPERIMENTS:
                oldest_id = min(
                    self._experiments.keys(),
                    key=lambda eid: self._experiments[eid].created_at,
                )
                del self._experiments[oldest_id]

            strategy_enum = self._parse_strategy(strategy)
            metric_enums = self._parse_metrics(metrics or [])

            experiment = ExperimentConfig(
                name=name,
                status=ExperimentStatus.DRAFT,
                metric_targets=metric_enums,
                strategy=strategy_enum,
            )
            self._experiments[experiment.id] = experiment
            self._trials[experiment.id] = []
            self._round_robin_counters[experiment.id] = 0
            self._bandit_counters[experiment.id] = {}

            for variant_data in (variants or []):
                variant = VariantGroup(
                    experiment_id=experiment.id,
                    name=variant_data.get("name", ""),
                    description=variant_data.get("description", ""),
                    parameters=variant_data.get("parameters", {}),
                    weight=variant_data.get("weight", self._DEFAULT_WEIGHT),
                )
                self._variants[variant.id] = variant
                experiment.variant_ids.append(variant.id)
                self._bandit_counters[experiment.id][variant.id] = 0

            return experiment

    def start_experiment(self, experiment_id: str) -> bool:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return False
        if experiment.status != ExperimentStatus.DRAFT:
            return False
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = time.time()
        return True

    def pause_experiment(self, experiment_id: str) -> bool:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return False
        if experiment.status != ExperimentStatus.RUNNING:
            return False
        experiment.status = ExperimentStatus.PAUSED
        return True

    def resume_experiment(self, experiment_id: str) -> bool:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return False
        if experiment.status != ExperimentStatus.PAUSED:
            return False
        experiment.status = ExperimentStatus.RUNNING
        return True

    def complete_experiment(self, experiment_id: str) -> bool:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return False
        if experiment.status not in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
            return False
        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = time.time()
        return True

    # ---- Variant Assignment ----

    def assign_variant(self,
                       experiment_id: str,
                       session_id: str) -> Optional[VariantGroup]:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return None
        if experiment.status not in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
            return None
        if not experiment.variant_ids:
            return None

        variant_id = self._select_variant(experiment)
        return self._variants.get(variant_id)

    def _select_variant(self, experiment: ExperimentConfig) -> str:
        variant_ids = experiment.variant_ids
        if not variant_ids:
            return ""

        if experiment.strategy == VariantStrategy.RANDOM:
            import random
            return variant_ids[random.randint(0, len(variant_ids) - 1)]

        if experiment.strategy == VariantStrategy.ROUND_ROBIN:
            counter = self._round_robin_counters.get(experiment.id, 0)
            selected = variant_ids[counter % len(variant_ids)]
            self._round_robin_counters[experiment.id] = counter + 1
            return selected

        if experiment.strategy == VariantStrategy.EPSILON_GREEDY:
            return self._select_epsilon_greedy(experiment)

        if experiment.strategy == VariantStrategy.THOMPSON_SAMPLING:
            return self._select_thompson_sampling(experiment)

        return variant_ids[0]

    def _select_epsilon_greedy(self, experiment: ExperimentConfig) -> str:
        import random
        variant_ids = experiment.variant_ids
        if random.random() < experiment.epsilon:
            return variant_ids[random.randint(0, len(variant_ids) - 1)]

        best_id = variant_ids[0]
        best_mean = 0.0
        for vid in variant_ids:
            mean = self._compute_variant_mean(experiment.id, vid)
            if mean > best_mean:
                best_mean = mean
                best_id = vid
        return best_id

    def _select_thompson_sampling(self, experiment: ExperimentConfig) -> str:
        import random
        variant_ids = experiment.variant_ids
        best_id = variant_ids[0]
        best_score = 0.0

        for vid in variant_ids:
            successes, total = self._count_variant_outcomes(experiment.id, vid)
            failures = total - successes
            alpha = max(successes + 1, 1)
            beta = max(failures + 1, 1)
            score = random.betavariate(alpha, beta)
            if score > best_score:
                best_score = score
                best_id = vid

        return best_id

    def _compute_variant_mean(self, experiment_id: str, variant_id: str) -> float:
        trials = self._trials.get(experiment_id, [])
        variant_trials = [t for t in trials if t.variant_id == variant_id]
        if not variant_trials:
            return 0.0
        metric_mean = 0.0
        count = 0
        for trial in variant_trials:
            for value in trial.metrics.values():
                metric_mean += value
                count += 1
        if count == 0:
            return 0.0
        return metric_mean / count

    def _count_variant_outcomes(self,
                                experiment_id: str,
                                variant_id: str) -> Tuple[int, int]:
        trials = self._trials.get(experiment_id, [])
        variant_trials = [t for t in trials if t.variant_id == variant_id]
        successes = sum(1 for t in variant_trials if t.success)
        return successes, len(variant_trials)

    # ---- Trial Recording ----

    def record_trial(self,
                     experiment_id: str,
                     variant_id: str,
                     metrics: Optional[Dict[str, float]] = None,
                     tags: Optional[Dict[str, str]] = None,
                     session_id: str = "",
                     success: bool = True) -> Optional[TrialResult]:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return None
        variant = self._variants.get(variant_id)
        if variant is None or variant.experiment_id != experiment_id:
            return None

        trial = TrialResult(
            experiment_id=experiment_id,
            variant_id=variant_id,
            session_id=session_id,
            metrics=metrics or {},
            tags=tags or {},
            success=success,
        )

        with self._lock:
            self._trials[experiment_id].append(trial)
            variant.trial_count += 1
            self._bandit_counters[experiment_id][variant_id] = (
                self._bandit_counters.get(experiment_id, {}).get(variant_id, 0) + 1
            )

        return trial

    def get_trials(self,
                   experiment_id: str,
                   variant_id: str = "") -> List[TrialResult]:
        trials = self._trials.get(experiment_id, [])
        if variant_id:
            return [t for t in trials if t.variant_id == variant_id]
        return list(trials)

    # ---- Results & Analysis ----

    def compute_results(self, experiment_id: str) -> Optional[ExperimentReport]:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return None

        trials = self._trials.get(experiment_id, [])
        if len(trials) < self._MIN_TRIALS_FOR_ANALYSIS:
            return None

        report = ExperimentReport(experiment_id=experiment_id)
        report.total_trials = len(trials)
        report.variant_summaries = {}

        for variant_id in experiment.variant_ids:
            variant_trials = [t for t in trials if t.variant_id == variant_id]
            if not variant_trials:
                continue

            summaries: Dict[str, Any] = {
                "count": len(variant_trials),
                "success_rate": sum(1 for t in variant_trials if t.success) / len(variant_trials),
            }

            for metric in experiment.metric_targets:
                metric_key = metric.value
                values = [
                    t.metrics[metric_key]
                    for t in variant_trials
                    if metric_key in t.metrics
                ]
                if values:
                    summaries[metric_key] = {
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
                        "min": min(values),
                        "max": max(values),
                    }
            report.variant_summaries[variant_id] = summaries

        report.pairwise_comparisons = self._build_pairwise_comparisons(
            experiment, trials
        )
        report.winning_variant_id = self._determine_winner(experiment, trials)
        report.confidence_level = self._estimate_confidence(experiment, trials)
        report.statistical_tests = self._run_statistical_tests(experiment, trials)

        with self._lock:
            self._reports[experiment_id] = report
            experiment.status = ExperimentStatus.ANALYZED

        return report

    def compare_variants(self, experiment_id: str) -> Dict[str, Any]:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return {}

        trials = self._trials.get(experiment_id, [])
        comparisons: Dict[str, Any] = {
            "experiment_id": experiment_id,
            "experiment_name": experiment.name,
            "status": experiment.status.value,
            "total_trials": len(trials),
            "variants": {},
        }

        for variant_id in experiment.variant_ids:
            variant = self._variants.get(variant_id)
            if variant is None:
                continue
            variant_trials = [t for t in trials if t.variant_id == variant_id]

            variant_info: Dict[str, Any] = {
                "name": variant.name,
                "trial_count": len(variant_trials),
                "parameters": variant.parameters,
                "weight": variant.weight,
            }

            for metric in experiment.metric_targets:
                metric_key = metric.value
                values = [
                    t.metrics[metric_key]
                    for t in variant_trials
                    if metric_key in t.metrics
                ]
                if values:
                    variant_info[metric_key] = {
                        "mean": round(statistics.mean(values), 4),
                        "median": round(statistics.median(values), 4),
                        "std": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
                    }

            comparisons["variants"][variant_id] = variant_info

        comparisons["pairwise_comparisons"] = self._build_pairwise_comparisons(
            experiment, trials
        )

        return comparisons

    def _build_pairwise_comparisons(self,
                                     experiment: ExperimentConfig,
                                     trials: List[TrialResult]) -> List[Dict[str, Any]]:
        comparisons: List[Dict[str, Any]] = []
        variant_ids = experiment.variant_ids
        for i in range(len(variant_ids)):
            for j in range(i + 1, len(variant_ids)):
                a_id = variant_ids[i]
                b_id = variant_ids[j]
                a_name = (self._variants.get(a_id) or VariantGroup()).name
                b_name = (self._variants.get(b_id) or VariantGroup()).name

                comparison: Dict[str, Any] = {
                    "variant_a_id": a_id,
                    "variant_a_name": a_name,
                    "variant_b_id": b_id,
                    "variant_b_name": b_name,
                    "metrics": {},
                }

                for metric in experiment.metric_targets:
                    metric_key = metric.value
                    a_vals = [
                        t.metrics[metric_key]
                        for t in trials
                        if t.variant_id == a_id and metric_key in t.metrics
                    ]
                    b_vals = [
                        t.metrics[metric_key]
                        for t in trials
                        if t.variant_id == b_id and metric_key in t.metrics
                    ]
                    if a_vals and b_vals:
                        a_mean = statistics.mean(a_vals)
                        b_mean = statistics.mean(b_vals)
                        delta = b_mean - a_mean
                        comparison["metrics"][metric_key] = {
                            "a_mean": round(a_mean, 4),
                            "b_mean": round(b_mean, 4),
                            "delta": round(delta, 4),
                            "improvement_pct": round((delta / a_mean) * 100, 2) if a_mean != 0 else 0.0,
                            "p_value": self._welch_ttest(a_vals, b_vals),
                        }

                comparisons.append(comparison)

        return comparisons

    def _determine_winner(self,
                          experiment: ExperimentConfig,
                          trials: List[TrialResult]) -> str:
        if not experiment.variant_ids or not experiment.metric_targets:
            return ""

        best_id = experiment.variant_ids[0]
        best_score = 0.0

        for variant_id in experiment.variant_ids:
            variant_trials = [t for t in trials if t.variant_id == variant_id]
            if not variant_trials:
                continue

            score = 0.0
            for metric in experiment.metric_targets:
                metric_key = metric.value
                values = [
                    t.metrics[metric_key]
                    for t in variant_trials
                    if metric_key in t.metrics
                ]
                if values:
                    score += statistics.mean(values)

            if score > best_score:
                best_score = score
                best_id = variant_id

        return best_id

    def _estimate_confidence(self,
                              experiment: ExperimentConfig,
                              trials: List[TrialResult]) -> float:
        winner_id = self._determine_winner(experiment, trials)
        if not winner_id:
            return 0.0

        all_p_values: List[float] = []
        for variant_id in experiment.variant_ids:
            if variant_id == winner_id:
                continue
            for metric in experiment.metric_targets:
                metric_key = metric.value
                winner_vals = [
                    t.metrics[metric_key]
                    for t in trials
                    if t.variant_id == winner_id and metric_key in t.metrics
                ]
                other_vals = [
                    t.metrics[metric_key]
                    for t in trials
                    if t.variant_id == variant_id and metric_key in t.metrics
                ]
                if winner_vals and other_vals:
                    p_val = self._welch_ttest(winner_vals, other_vals)
                    all_p_values.append(p_val)

        if not all_p_values:
            return 0.0

        return 1.0 - (sum(all_p_values) / len(all_p_values))

    def _run_statistical_tests(self,
                                experiment: ExperimentConfig,
                                trials: List[TrialResult]) -> Dict[str, Any]:
        tests: Dict[str, Any] = {
            "method": "welch_t_test",
            "significance_level": 0.05,
            "results": {},
        }

        for metric in experiment.metric_targets:
            metric_key = metric.value
            metric_results: List[Dict[str, Any]] = []

            variant_ids = experiment.variant_ids
            for i in range(len(variant_ids)):
                for j in range(i + 1, len(variant_ids)):
                    a_vals = [
                        t.metrics[metric_key]
                        for t in trials
                        if t.variant_id == variant_ids[i] and metric_key in t.metrics
                    ]
                    b_vals = [
                        t.metrics[metric_key]
                        for t in trials
                        if t.variant_id == variant_ids[j] and metric_key in t.metrics
                    ]
                    if a_vals and b_vals:
                        p_val = self._welch_ttest(a_vals, b_vals)
                        metric_results.append({
                            "a_variant": variant_ids[i],
                            "b_variant": variant_ids[j],
                            "p_value": round(p_val, 6),
                            "significant": p_val < 0.05,
                        })

            tests["results"][metric_key] = metric_results

        return tests

    @staticmethod
    def _welch_ttest(a: List[float], b: List[float]) -> float:
        if len(a) < 2 or len(b) < 2:
            return 1.0

        mean_a = statistics.mean(a)
        mean_b = statistics.mean(b)
        var_a = statistics.variance(a)
        var_b = statistics.variance(b)

        n_a = len(a)
        n_b = len(b)

        se = math.sqrt(var_a / n_a + var_b / n_b)
        if se == 0:
            return 1.0

        t_stat = (mean_a - mean_b) / se

        df_num = (var_a / n_a + var_b / n_b) ** 2
        df_den = ((var_a / n_a) ** 2) / (n_a - 1) + ((var_b / n_b) ** 2) / (n_b - 1)
        if df_den == 0:
            return 1.0
        df = df_num / df_den

        p_value = 2.0 * (1.0 - AgentExperimentFramework._student_t_cdf(abs(t_stat), df))
        return p_value

    @staticmethod
    def _student_t_cdf(t: float, df: float) -> float:
        if df <= 0:
            return 0.5
        x = df / (df + t * t)
        return 1.0 - 0.5 * AgentExperimentFramework._regularized_incomplete_beta(
            df / 2.0, 0.5, x
        )

    @staticmethod
    def _regularized_incomplete_beta(a: float, b: float, x: float) -> float:
        if x < 0.0 or x > 1.0:
            return 0.0
        if x == 0.0 or x == 1.0:
            return x
        return math.exp(
            math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
            + a * math.log(x) + b * math.log(1.0 - x)
        )

    # ---- Listing & Querying ----

    def list_experiments(self,
                         status: str = "") -> List[ExperimentConfig]:
        experiments = list(self._experiments.values())
        if status:
            try:
                status_enum = ExperimentStatus(status)
                experiments = [e for e in experiments if e.status == status_enum]
            except ValueError:
                pass
        experiments.sort(key=lambda e: e.created_at, reverse=True)
        return experiments

    def get_experiment(self, experiment_id: str) -> Optional[ExperimentConfig]:
        return self._experiments.get(experiment_id)

    def get_variant(self, variant_id: str) -> Optional[VariantGroup]:
        return self._variants.get(variant_id)

    def get_report(self, experiment_id: str) -> Optional[ExperimentReport]:
        return self._reports.get(experiment_id)

    def list_variants(self, experiment_id: str) -> List[VariantGroup]:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            return []
        return [self._variants[vid] for vid in experiment.variant_ids if vid in self._variants]

    # ---- Stats & Reset ----

    def get_stats(self) -> Dict[str, Any]:
        status_counts: Dict[str, int] = {}
        for exp in self._experiments.values():
            key = exp.status.value
            status_counts[key] = status_counts.get(key, 0) + 1

        strategy_counts: Dict[str, int] = {}
        for exp in self._experiments.values():
            key = exp.strategy.value
            strategy_counts[key] = strategy_counts.get(key, 0) + 1

        total_trials = sum(len(t) for t in self._trials.values())
        total_variants = len(self._variants)
        total_reports = len(self._reports)

        return {
            "total_experiments": len(self._experiments),
            "experiments_by_status": status_counts,
            "experiments_by_strategy": strategy_counts,
            "total_variants": total_variants,
            "total_trials_recorded": total_trials,
            "total_reports_generated": total_reports,
        }

    def reset(self) -> None:
        with self._lock:
            self._experiments.clear()
            self._variants.clear()
            self._trials.clear()
            self._reports.clear()
            self._round_robin_counters.clear()
            self._bandit_counters.clear()

    # ---- Helpers ----

    @staticmethod
    def _parse_strategy(strategy: str) -> VariantStrategy:
        strategy_lower = strategy.lower().replace(" ", "_")
        for item in VariantStrategy:
            if item.value == strategy_lower:
                return item
        return VariantStrategy.ROUND_ROBIN

    @staticmethod
    def _parse_metrics(metrics: List[str]) -> List[MetricTarget]:
        result: List[MetricTarget] = []
        for m in metrics:
            m_lower = m.lower().replace(" ", "_")
            for item in MetricTarget:
                if item.value == m_lower:
                    result.append(item)
                    break
        return result


def get_experiment_framework() -> AgentExperimentFramework:
    return AgentExperimentFramework.get_instance()