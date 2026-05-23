"""
SparkLabs Agent - Self-Optimization Engine

Automated behavioral calibration and prompt refinement for game
development agents. Tracks optimization profiles, runs phased
calibration sessions, records performance metrics, and selects
the best prompt variants based on accumulated evidence.

Architecture:
  SelfOptimizationEngine
    |-- OptimizationProfile (per-agent target configuration)
    |-- CalibrationRun (benchmark/adjust/validate/lock cycle)
    |-- PerformanceMetric (quantitative feedback record)
    |-- PromptVariant (competing prompt configuration)

Calibration Flow:
  1. Create an optimization profile with target dimensions
  2. Start a benchmark calibration run to establish baseline
  3. Record accuracy, latency, conciseness, creativity, and
     user satisfaction metrics against the current prompt
  4. Generate prompt variants with alternative adjustments
  5. Run adjust/validate phases to score each variant
  6. Select the best variant and lock the optimization
  7. Compare profile performance across agent instances

Targets:
  - PROMPT_STRUCTURE: layout, sectioning, instruction ordering
  - RESPONSE_STYLE: tone, verbosity, formatting conventions
  - TOOL_USAGE: tool selection, invocation sequencing
  - REASONING_DEPTH: chain-of-thought granularity
  - CREATIVITY: novelty, divergence, idea generation breadth
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class OptimizationTarget(Enum):
    PROMPT_STRUCTURE = "prompt_structure"
    RESPONSE_STYLE = "response_style"
    TOOL_USAGE = "tool_usage"
    REASONING_DEPTH = "reasoning_depth"
    CREATIVITY = "creativity"


class CalibrationPhase(Enum):
    BENCHMARK = "benchmark"
    ADJUST = "adjust"
    VALIDATE = "validate"
    LOCK = "lock"


class MetricType(Enum):
    ACCURACY = "accuracy"
    LATENCY = "latency"
    CONCISENESS = "conciseness"
    CREATIVITY = "creativity"
    USER_SATISFACTION = "user_satisfaction"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class OptimizationProfile:
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    targets: List[str] = field(default_factory=list)
    status: str = "active"
    current_variant_id: str = ""
    total_runs: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "agent_id": self.agent_id,
            "targets": list(self.targets),
            "status": self.status,
            "current_variant_id": self.current_variant_id,
            "total_runs": self.total_runs,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class CalibrationRun:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    profile_id: str = ""
    phase: str = CalibrationPhase.BENCHMARK.value
    status: str = "running"
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    metrics_count: int = 0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "profile_id": self.profile_id,
            "phase": self.phase,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metrics_count": self.metrics_count,
            "notes": self.notes,
        }


@dataclass
class PerformanceMetric:
    metric_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    run_id: str = ""
    metric_type: str = MetricType.ACCURACY.value
    value: float = 0.0
    context: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "run_id": self.run_id,
            "metric_type": self.metric_type,
            "value": self.value,
            "context": self.context,
            "timestamp": self.timestamp,
        }


@dataclass
class PromptVariant:
    variant_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    profile_id: str = ""
    base_prompt: str = ""
    adjustments: Dict[str, str] = field(default_factory=dict)
    score: float = 0.0
    usage_count: int = 0
    is_applied: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "profile_id": self.profile_id,
            "base_prompt": self.base_prompt,
            "adjustments": dict(self.adjustments),
            "score": self.score,
            "usage_count": self.usage_count,
            "is_applied": self.is_applied,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# SelfOptimizationEngine
# ---------------------------------------------------------------------------


class SelfOptimizationEngine:
    """
    Automated behavioral calibration engine for agent prompt tuning.

    Drives a benchmark-adjust-validate-lock cycle per agent profile,
    recording quantitative metrics to score competing prompt variants.
    The best variant is selected and applied to the target agent.

    Usage:
        engine = get_self_optimization()
        profile = engine.create_profile("agent_42", [
            OptimizationTarget.PROMPT_STRUCTURE.value,
            OptimizationTarget.RESPONSE_STYLE.value,
        ])
        run = engine.run_calibration(profile.profile_id, "benchmark")
        engine.record_metric(run.run_id, MetricType.ACCURACY.value, 0.85)
        engine.record_metric(run.run_id, MetricType.LATENCY.value, 120.0)
        variant = engine.generate_prompt_variant(
            profile.profile_id,
            "You are a game design assistant.",
            {"tone": "concise", "format": "numbered_steps"},
        )
        best = engine.select_best_variant(profile.profile_id)
        engine.apply_optimization(profile.profile_id, best.variant_id)
    """

    _instance: Optional["SelfOptimizationEngine"] = None

    @classmethod
    def get_instance(cls) -> "SelfOptimizationEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._profiles: Dict[str, OptimizationProfile] = {}
        self._runs: Dict[str, CalibrationRun] = {}
        self._metrics: Dict[str, List[PerformanceMetric]] = {}
        self._variants: Dict[str, PromptVariant] = {}

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def create_profile(
        self,
        agent_id: str,
        targets: Optional[List[str]] = None,
    ) -> OptimizationProfile:
        """
        Create a new optimization profile for an agent.

        Args:
            agent_id: Unique identifier for the target agent.
            targets: List of OptimizationTarget string values to pursue.
                     Defaults to all five targets.

        Returns:
            A new OptimizationProfile ready for calibration.
        """
        if targets is None:
            targets = [t.value for t in OptimizationTarget]

        profile = OptimizationProfile(
            agent_id=agent_id,
            targets=[t for t in targets if t in self._valid_targets()],
            status="active",
        )
        self._profiles[profile.profile_id] = profile
        return profile

    def get_profile(self, profile_id: str) -> Optional[OptimizationProfile]:
        return self._profiles.get(profile_id)

    # ------------------------------------------------------------------
    # Calibration Runs
    # ------------------------------------------------------------------

    def run_calibration(
        self,
        profile_id: str,
        phase: str = CalibrationPhase.BENCHMARK.value,
    ) -> Optional[CalibrationRun]:
        """
        Start a calibration run for the given profile.

        Phases proceed in order: benchmark -> adjust -> validate -> lock.
        When lock is reached, the profile status becomes locked.

        Args:
            profile_id: The profile to calibrate.
            phase: One of benchmark, adjust, validate, lock.

        Returns:
            A CalibrationRun instance, or None if the profile is not found.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None

        valid_phases = [p.value for p in CalibrationPhase]
        if phase not in valid_phases:
            phase = CalibrationPhase.BENCHMARK.value

        run = CalibrationRun(
            profile_id=profile_id,
            phase=phase,
        )
        self._runs[run.run_id] = run
        profile.total_runs += 1
        profile.updated_at = time.time()

        if phase == CalibrationPhase.LOCK.value:
            profile.status = "locked"

        return run

    def get_run(self, run_id: str) -> Optional[CalibrationRun]:
        return self._runs.get(run_id)

    # ------------------------------------------------------------------
    # Metric Recording
    # ------------------------------------------------------------------

    def record_metric(
        self,
        run_id: str,
        metric_type: str,
        value: float,
        context: str = "",
    ) -> Optional[PerformanceMetric]:
        """
        Record a performance metric against a calibration run.

        Args:
            run_id: The calibration run to attach the metric to.
            metric_type: One of MetricType string values.
            value: Numeric metric value (normalized 0.0-1.0 recommended).
            context: Optional description of the measurement context.

        Returns:
            A PerformanceMetric instance, or None if the run is not found.
        """
        run = self._runs.get(run_id)
        if run is None:
            return None

        clamped = max(0.0, min(1.0, value))

        metric = PerformanceMetric(
            run_id=run_id,
            metric_type=metric_type,
            value=clamped,
            context=context,
        )
        if run_id not in self._metrics:
            self._metrics[run_id] = []
        self._metrics[run_id].append(metric)
        run.metrics_count += 1

        return metric

    def get_metrics_for_run(self, run_id: str) -> List[PerformanceMetric]:
        return list(self._metrics.get(run_id, []))

    # ------------------------------------------------------------------
    # Prompt Variants
    # ------------------------------------------------------------------

    def generate_prompt_variant(
        self,
        profile_id: str,
        base_prompt: str,
        adjustments: Optional[Dict[str, str]] = None,
    ) -> Optional[PromptVariant]:
        """
        Create a new prompt variant for a profile.

        Adjustments are key-value pairs describing modifications to
        the base prompt (e.g., tone=concise, format=numbered_steps).

        Args:
            profile_id: The profile to attach the variant to.
            base_prompt: The original prompt text.
            adjustments: Optional dict of modification descriptors.

        Returns:
            A PromptVariant instance, or None if the profile is not found.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None

        variant = PromptVariant(
            profile_id=profile_id,
            base_prompt=base_prompt,
            adjustments=adjustments or {},
        )
        self._variants[variant.variant_id] = variant
        profile.updated_at = time.time()

        return variant

    def get_variant(self, variant_id: str) -> Optional[PromptVariant]:
        return self._variants.get(variant_id)

    def get_variants_for_profile(self, profile_id: str) -> List[PromptVariant]:
        return [
            v for v in self._variants.values()
            if v.profile_id == profile_id
        ]

    # ------------------------------------------------------------------
    # Scoring Helpers
    # ------------------------------------------------------------------

    def _score_variant(self, variant: PromptVariant) -> float:
        """
        Compute a composite score for a variant from all metrics
        recorded across calibration runs for its profile.

        Walks through each run linked to the profile, collects all
        metrics, and averages them with equal weighting per type.
        """
        profile_runs = [
            r for r in self._runs.values()
            if r.profile_id == variant.profile_id
        ]
        if not profile_runs:
            return 0.0

        type_sums: Dict[str, float] = {}
        type_counts: Dict[str, int] = {}

        for run in profile_runs:
            run_metrics = self._metrics.get(run.run_id, [])
            for m in run_metrics:
                key = m.metric_type
                type_sums[key] = type_sums.get(key, 0.0) + m.value
                type_counts[key] = type_counts.get(key, 0) + 1

        if not type_sums:
            return 0.0

        averages = [
            type_sums[k] / type_counts[k]
            for k in type_sums
        ]
        return sum(averages) / len(averages)

    # ------------------------------------------------------------------
    # Variant Selection & Application
    # ------------------------------------------------------------------

    def select_best_variant(
        self,
        profile_id: str,
    ) -> Optional[PromptVariant]:
        """
        Select the highest-scoring prompt variant for a profile.

        Scores are computed from all metrics collected during the
        profile's calibration runs. If no variants exist or no
        metrics have been recorded, returns None.

        Args:
            profile_id: The profile whose variants should be compared.

        Returns:
            The PromptVariant with the highest computed score, or None.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            return None

        candidates = self.get_variants_for_profile(profile_id)
        if not candidates:
            return None

        scored: List[PromptVariant] = []
        for variant in candidates:
            variant.score = self._score_variant(variant)
            scored.append(variant)

        scored.sort(key=lambda v: -v.score)
        return scored[0]

    def apply_optimization(
        self,
        profile_id: str,
        variant_id: str,
    ) -> bool:
        """
        Apply the selected variant to the profile.

        Marks the variant as applied and sets it as the profile's
        current active variant. Unmarks any previously applied variant.

        Args:
            profile_id: The profile to update.
            variant_id: The variant to activate.

        Returns:
            True if the optimization was applied, False otherwise.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            return False

        variant = self._variants.get(variant_id)
        if variant is None or variant.profile_id != profile_id:
            return False

        for v in self.get_variants_for_profile(profile_id):
            v.is_applied = False

        variant.is_applied = True
        profile.current_variant_id = variant_id
        profile.updated_at = time.time()

        return True

    # ------------------------------------------------------------------
    # Profile Comparison
    # ------------------------------------------------------------------

    def compare_profiles(
        self,
        profile_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Compare multiple optimization profiles side by side.

        For each profile, aggregates metrics across all calibration
        runs and produces per-type average scores along with profile
        metadata.

        Args:
            profile_ids: List of profile IDs to compare.

        Returns:
            A dict mapping profile_id -> comparison data including
            agent_id, targets, status, run count, variant count,
            metric averages, and total average score.
        """
        result: Dict[str, Any] = {}

        for pid in profile_ids:
            profile = self._profiles.get(pid)
            if profile is None:
                result[pid] = {"error": "profile not found"}
                continue

            profile_runs = [
                r for r in self._runs.values()
                if r.profile_id == pid
            ]

            type_sums: Dict[str, float] = {}
            type_counts: Dict[str, int] = {}

            for run in profile_runs:
                run_metrics = self._metrics.get(run.run_id, [])
                for m in run_metrics:
                    key = m.metric_type
                    type_sums[key] = type_sums.get(key, 0.0) + m.value
                    type_counts[key] = type_counts.get(key, 0) + 1

            metric_averages: Dict[str, float] = {}
            for key in type_sums:
                metric_averages[key] = round(
                    type_sums[key] / type_counts[key], 3,
                )

            total_avg = 0.0
            if metric_averages:
                total_avg = round(
                    sum(metric_averages.values()) / len(metric_averages), 3,
                )

            variant_count = sum(
                1 for v in self._variants.values()
                if v.profile_id == pid
            )

            result[pid] = {
                "agent_id": profile.agent_id,
                "targets": list(profile.targets),
                "status": profile.status,
                "total_runs": profile.total_runs,
                "variant_count": variant_count,
                "metric_averages": metric_averages,
                "total_avg_score": total_avg,
                "current_variant_id": profile.current_variant_id,
            }

        return result

    # ------------------------------------------------------------------
    # History & Queries
    # ------------------------------------------------------------------

    def get_optimization_history(
        self,
        agent_id: str,
    ) -> List[CalibrationRun]:
        """
        Retrieve all calibration runs for a given agent, sorted by
        start time descending (most recent first).

        Args:
            agent_id: The agent identifier to look up.

        Returns:
            A list of CalibrationRun instances for the agent's profiles.
        """
        profile_ids = [
            pid for pid, p in self._profiles.items()
            if p.agent_id == agent_id
        ]

        runs: List[CalibrationRun] = []
        for rid, run in self._runs.items():
            if run.profile_id in profile_ids:
                runs.append(run)

        runs.sort(key=lambda r: -r.started_at)
        return runs

    # ------------------------------------------------------------------
    # Stats & Reset
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Return aggregate statistics about the optimization engine.

        Includes profile counts by status, target distribution,
        calibration phase distribution, metric type distribution,
        variant counts, and overall totals.
        """
        status_counts: Dict[str, int] = {}
        for profile in self._profiles.values():
            key = profile.status
            status_counts[key] = status_counts.get(key, 0) + 1

        target_counts: Dict[str, int] = {}
        for profile in self._profiles.values():
            for t in profile.targets:
                target_counts[t] = target_counts.get(t, 0) + 1

        phase_counts: Dict[str, int] = {}
        run_status_counts: Dict[str, int] = {}
        for run in self._runs.values():
            phase_counts[run.phase] = phase_counts.get(run.phase, 0) + 1
            run_status_counts[run.status] = run_status_counts.get(run.status, 0) + 1

        total_metrics = 0
        metric_type_counts: Dict[str, int] = {}
        metric_type_sums: Dict[str, float] = {}
        for run_metrics in self._metrics.values():
            for m in run_metrics:
                total_metrics += 1
                metric_type_counts[m.metric_type] = (
                    metric_type_counts.get(m.metric_type, 0) + 1
                )
                metric_type_sums[m.metric_type] = (
                    metric_type_sums.get(m.metric_type, 0.0) + m.value
                )

        metric_averages: Dict[str, float] = {}
        for key in metric_type_counts:
            metric_averages[key] = round(
                metric_type_sums[key] / metric_type_counts[key], 3,
            )

        applied_variants = sum(
            1 for v in self._variants.values() if v.is_applied
        )
        locked_profiles = sum(
            1 for p in self._profiles.values() if p.status == "locked"
        )

        return {
            "total_profiles": len(self._profiles),
            "total_runs": len(self._runs),
            "total_metrics": total_metrics,
            "total_variants": len(self._variants),
            "applied_variants": applied_variants,
            "locked_profiles": locked_profiles,
            "profiles_by_status": status_counts,
            "target_distribution": target_counts,
            "runs_by_phase": phase_counts,
            "runs_by_status": run_status_counts,
            "metrics_by_type": metric_type_counts,
            "metric_averages": metric_averages,
        }

    def reset(self) -> None:
        """
        Clear all state: profiles, runs, metrics, and variants.

        The singleton instance remains alive but all accumulated
        data is discarded.
        """
        self._profiles.clear()
        self._runs.clear()
        self._metrics.clear()
        self._variants.clear()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _valid_targets() -> List[str]:
        return [t.value for t in OptimizationTarget]


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

_global_self_optimization: Optional[SelfOptimizationEngine] = None


def get_self_optimization() -> SelfOptimizationEngine:
    """
    Return the global singleton instance of SelfOptimizationEngine.

    Creates the instance on first access and reuses it on subsequent
    calls. Thread-safe access is delegated to the class-level
    get_instance method.

    Returns:
        The shared SelfOptimizationEngine instance.
    """
    global _global_self_optimization
    if _global_self_optimization is None:
        _global_self_optimization = SelfOptimizationEngine.get_instance()
    return _global_self_optimization