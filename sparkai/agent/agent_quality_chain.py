"""
SparkLabs Agent - Quality Chain

Multi-stage quality verification chain subsystem for the SparkLabs
AI-native game engine. Orchestrates configurable quality pipelines
that validate game artifacts through syntax, lint, test, performance,
security, accessibility, and playtest stages. Provides automated
quality scoring, trend tracking, and regression detection.

Architecture:
  QualityChainEngine
    |-- QualityGate (individual stage check with pass/fail criteria)
    |-- GateResult (per-stage execution outcome)
    |-- QualityRun (full pipeline run with all stage results)
    |-- ScoringEngine (weighted dimension scoring)
    |-- RegressionDetector (cross-run comparison)
    |-- TrendTracker (over-time quality monitoring)

Pipeline Flow:
  SYNTAX_CHECK -> LINT_CHECK -> UNIT_TEST -> INTEGRATION_TEST
  -> PERFORMANCE_BENCHMARK -> SECURITY_SCAN -> ACCESSIBILITY_AUDIT
  -> PLAYTEST_VALIDATION -> VISUAL_REGRESSION -> ASSET_VALIDATION

Quality Dimensions:
  CORRECTNESS, PERFORMANCE, SECURITY, ACCESSIBILITY,
  MAINTAINABILITY, USABILITY, VISUAL_QUALITY, CODE_QUALITY
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class QualityStage(Enum):
    SYNTAX_CHECK = "syntax_check"
    LINT_CHECK = "lint_check"
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    PERFORMANCE_BENCHMARK = "performance_benchmark"
    SECURITY_SCAN = "security_scan"
    ACCESSIBILITY_AUDIT = "accessibility_audit"
    PLAYTEST_VALIDATION = "playtest_validation"
    VISUAL_REGRESSION = "visual_regression"
    ASSET_VALIDATION = "asset_validation"


class GateStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class QualityDimension(Enum):
    CORRECTNESS = "correctness"
    PERFORMANCE = "performance"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"
    MAINTAINABILITY = "maintainability"
    USABILITY = "usability"
    VISUAL_QUALITY = "visual_quality"
    CODE_QUALITY = "code_quality"


@dataclass
class QualityGate:
    gate_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    stage: QualityStage = QualityStage.SYNTAX_CHECK
    criteria: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    timeout_seconds: float = 60.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "stage": self.stage.value,
            "criteria": self.criteria,
            "weight": self.weight,
            "timeout_seconds": self.timeout_seconds,
            "enabled": self.enabled,
        }


@dataclass
class GateResult:
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    gate_id: str = ""
    status: GateStatus = GateStatus.PASSED
    score: float = 0.0
    details: List[str] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "gate_id": self.gate_id,
            "status": self.status.value,
            "score": round(self.score, 2),
            "details": self.details,
            "issues": self.issues,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class QualityRun:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    stages: List[QualityStage] = field(default_factory=list)
    results: List[GateResult] = field(default_factory=list)
    overall_score: float = 0.0
    started: float = field(default_factory=time.time)
    completed: Optional[float] = None
    status: GateStatus = GateStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "name": self.name,
            "stages": [s.value for s in self.stages],
            "results": [r.to_dict() for r in self.results],
            "overall_score": round(self.overall_score, 2),
            "started": self.started,
            "completed": self.completed,
            "status": self.status.value,
        }

    def to_summary(self) -> Dict[str, Any]:
        stage_statuses = {}
        for r in self.results:
            gate = self._find_gate_for_result(r)
            stage_name = gate.stage.value if gate else "unknown"
            stage_statuses[stage_name] = r.status.value

        return {
            "run_id": self.run_id,
            "name": self.name,
            "overall_score": round(self.overall_score, 2),
            "status": self.status.value,
            "stages": stage_statuses,
            "total_issues": sum(len(r.issues) for r in self.results),
            "duration_seconds": round(
                ((self.completed or time.time()) - self.started), 1
            ),
        }

    def _find_gate_for_result(self, _result: GateResult) -> Optional[QualityGate]:
        return None


DEFAULT_STAGE_WEIGHTS: Dict[QualityStage, float] = {
    QualityStage.SYNTAX_CHECK: 0.5,
    QualityStage.LINT_CHECK: 0.5,
    QualityStage.UNIT_TEST: 1.0,
    QualityStage.INTEGRATION_TEST: 1.0,
    QualityStage.PERFORMANCE_BENCHMARK: 1.0,
    QualityStage.SECURITY_SCAN: 1.5,
    QualityStage.ACCESSIBILITY_AUDIT: 1.0,
    QualityStage.PLAYTEST_VALIDATION: 2.0,
    QualityStage.VISUAL_REGRESSION: 1.0,
    QualityStage.ASSET_VALIDATION: 0.5,
}

DEFAULT_PIPELINE_STAGES: List[QualityStage] = [
    QualityStage.SYNTAX_CHECK,
    QualityStage.LINT_CHECK,
    QualityStage.UNIT_TEST,
    QualityStage.INTEGRATION_TEST,
    QualityStage.PERFORMANCE_BENCHMARK,
    QualityStage.SECURITY_SCAN,
    QualityStage.ACCESSIBILITY_AUDIT,
    QualityStage.PLAYTEST_VALIDATION,
]

STAGE_TO_DIMENSIONS: Dict[QualityStage, List[QualityDimension]] = {
    QualityStage.SYNTAX_CHECK: [
        QualityDimension.CORRECTNESS, QualityDimension.CODE_QUALITY,
    ],
    QualityStage.LINT_CHECK: [
        QualityDimension.CODE_QUALITY, QualityDimension.MAINTAINABILITY,
    ],
    QualityStage.UNIT_TEST: [
        QualityDimension.CORRECTNESS, QualityDimension.MAINTAINABILITY,
    ],
    QualityStage.INTEGRATION_TEST: [
        QualityDimension.CORRECTNESS, QualityDimension.USABILITY,
    ],
    QualityStage.PERFORMANCE_BENCHMARK: [
        QualityDimension.PERFORMANCE,
    ],
    QualityStage.SECURITY_SCAN: [
        QualityDimension.SECURITY,
    ],
    QualityStage.ACCESSIBILITY_AUDIT: [
        QualityDimension.ACCESSIBILITY,
    ],
    QualityStage.PLAYTEST_VALIDATION: [
        QualityDimension.USABILITY, QualityDimension.VISUAL_QUALITY,
    ],
    QualityStage.VISUAL_REGRESSION: [
        QualityDimension.VISUAL_QUALITY, QualityDimension.CORRECTNESS,
    ],
    QualityStage.ASSET_VALIDATION: [
        QualityDimension.VISUAL_QUALITY, QualityDimension.CODE_QUALITY,
    ],
}


class QualityChainEngine:
    """
    Multi-stage quality verification chain for game development artifacts.

    Orchestrates configurable quality pipelines that run artifacts through
    sequential validation stages. Each stage is implemented as a QualityGate
    with configurable pass/fail criteria. Supports weighted scoring across
    quality dimensions, trend tracking over time, and cross-run regression
    detection.

    Usage:
        chain = QualityChainEngine()
        run = chain.create_pipeline("release-v2", [...])
        chain.add_gate(run.run_id, QualityStage.UNIT_TEST, {"min_coverage": 80})
        completed = chain.execute_full_pipeline(run.run_id, artifact_data)
        scores = chain.get_overall_score(run.run_id)
    """

    _instance: Optional["QualityChainEngine"] = None

    def __init__(self):
        self._runs: Dict[str, QualityRun] = {}
        self._gates: Dict[str, QualityGate] = {}
        self._trend_history: Dict[str, List[float]] = {}
        self._stage_weights: Dict[QualityStage, float] = dict(DEFAULT_STAGE_WEIGHTS)
        self._pipeline_stages: List[QualityStage] = list(DEFAULT_PIPELINE_STAGES)
        self._total_runs: int = 0
        self._total_stages_executed: int = 0

    @classmethod
    def get_instance(cls) -> "QualityChainEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_pipeline(
        self,
        name: str,
        stages: Optional[List[QualityStage]] = None,
        gates_config: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> QualityRun:
        stages = stages or list(self._pipeline_stages)
        run = QualityRun(
            name=name,
            stages=stages,
        )
        self._runs[run.run_id] = run
        self._total_runs += 1

        gates_config = gates_config or {}
        for stage in stages:
            stage_key = stage.value
            config = gates_config.get(stage_key, {})
            criteria = config.get("criteria", {})
            weight = config.get("weight", self._stage_weights.get(stage, 1.0))
            timeout = config.get("timeout_seconds", 60.0)
            enabled = config.get("enabled", True)
            gate = QualityGate(
                stage=stage,
                criteria=criteria,
                weight=weight,
                timeout_seconds=timeout,
                enabled=enabled,
            )
            self._gates[gate.gate_id] = gate

        return run

    def add_gate(
        self,
        run_id: str,
        stage: QualityStage,
        criteria: Optional[Dict[str, Any]] = None,
        weight: Optional[float] = None,
        timeout_seconds: float = 60.0,
        enabled: bool = True,
    ) -> Optional[QualityGate]:
        run = self._runs.get(run_id)
        if run is None:
            return None

        if stage not in run.stages:
            run.stages.append(stage)

        gate = QualityGate(
            stage=stage,
            criteria=criteria or {},
            weight=weight if weight is not None else self._stage_weights.get(stage, 1.0),
            timeout_seconds=timeout_seconds,
            enabled=enabled,
        )
        self._gates[gate.gate_id] = gate
        return gate

    def execute_stage(
        self,
        run_id: str,
        stage: QualityStage,
        subject_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[GateResult]:
        run = self._runs.get(run_id)
        if run is None:
            return None

        gate = self._find_gate_for_stage(stage)
        if gate is None or not gate.enabled:
            skipped_result = GateResult(
                gate_id="",
                status=GateStatus.SKIPPED,
                details=[f"Stage '{stage.value}' has no enabled gate configured"],
            )
            run.results.append(skipped_result)
            return skipped_result

        start = time.time()
        subject_data = subject_data or {}

        score, details, issues = self._simulate_stage_execution(
            stage, gate.criteria, subject_data
        )

        duration = (time.time() - start) * 1000
        if duration > gate.timeout_seconds * 1000:
            status = GateStatus.WARNING
            details.append(
                f"Stage exceeded timeout ({duration:.0f}ms > "
                f"{gate.timeout_seconds * 1000:.0f}ms)"
            )
        elif score >= 80.0:
            status = GateStatus.PASSED
        elif score >= 50.0:
            status = GateStatus.WARNING
        else:
            status = GateStatus.FAILED

        result = GateResult(
            gate_id=gate.gate_id,
            status=status,
            score=score,
            details=details,
            issues=issues,
            duration_ms=duration,
        )
        run.results.append(result)
        self._total_stages_executed += 1

        self._record_trend(stage, score)

        return result

    def execute_full_pipeline(
        self,
        run_id: str,
        subject_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[QualityRun]:
        run = self._runs.get(run_id)
        if run is None:
            return None

        subject_data = subject_data or {}

        for stage in run.stages:
            self.execute_stage(run_id, stage, subject_data)

        run.completed = time.time()

        total_weighted_score = 0.0
        total_weight = 0.0
        for result in run.results:
            gate = self._gates.get(result.gate_id)
            if gate and result.status != GateStatus.SKIPPED:
                total_weighted_score += result.score * gate.weight
                total_weight += gate.weight

        run.overall_score = (
            total_weighted_score / total_weight if total_weight > 0 else 0.0
        )

        has_failed = any(
            r.status == GateStatus.FAILED for r in run.results
        )
        if has_failed:
            run.status = GateStatus.FAILED
        else:
            has_warning = any(
                r.status == GateStatus.WARNING for r in run.results
            )
            run.status = GateStatus.WARNING if has_warning else GateStatus.PASSED

        return run

    def get_overall_score(self, run_id: str) -> Optional[Dict[str, Any]]:
        run = self._runs.get(run_id)
        if run is None:
            return None

        dimension_scores: Dict[str, List[float]] = {}
        for result in run.results:
            gate = self._gates.get(result.gate_id)
            if gate is None or result.status == GateStatus.SKIPPED:
                continue
            dims = STAGE_TO_DIMENSIONS.get(gate.stage, [])
            for dim in dims:
                dimension_scores.setdefault(dim.value, []).append(result.score)

        aggregated: Dict[str, float] = {}
        for dim_key, scores in dimension_scores.items():
            aggregated[dim_key] = sum(scores) / len(scores) if scores else 0.0

        total = sum(aggregated.values()) / len(aggregated) if aggregated else 0.0

        return {
            "run_id": run_id,
            "name": run.name,
            "dimension_scores": aggregated,
            "total": round(total, 2),
            "status": run.status.value,
        }

    def detect_regressions(
        self,
        run_id_a: str,
        run_id_b: str,
    ) -> Optional[List[Dict[str, Any]]]:
        run_a = self._runs.get(run_id_a)
        run_b = self._runs.get(run_id_b)
        if run_a is None or run_b is None:
            return None

        regressions: List[Dict[str, Any]] = []

        scores_a: Dict[str, GateResult] = {}
        for r in run_a.results:
            gate = self._gates.get(r.gate_id)
            if gate:
                scores_a[gate.stage.value] = r

        for r_b in run_b.results:
            gate = self._gates.get(r_b.gate_id)
            if gate is None:
                continue
            stage_key = gate.stage.value
            r_a = scores_a.get(stage_key)
            if r_a is None:
                continue

            score_diff = round(r_b.score - r_a.score, 2)
            if score_diff < -5.0:
                new_issues = [
                    issue for issue in r_b.issues
                    if not any(
                        issue.get("fingerprint") == prev.get("fingerprint")
                        and issue.get("fingerprint") is not None
                        for prev in r_a.issues
                    )
                ]
                regressions.append({
                    "stage": stage_key,
                    "previous_score": r_a.score,
                    "current_score": r_b.score,
                    "score_diff": score_diff,
                    "previous_status": r_a.status.value,
                    "current_status": r_b.status.value,
                    "new_issues": new_issues,
                    "new_issue_count": len(new_issues),
                })

        regressions.sort(key=lambda x: x["score_diff"])
        return regressions

    def get_trend(
        self,
        dimension: str,
        window: int = 10,
    ) -> List[float]:
        key = dimension.lower()
        trend_key = f"dim:{key}"
        return list(self._trend_history.get(trend_key, [])[-window:])

    def configure_gate(
        self,
        stage: QualityStage,
        criteria: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        if criteria is not None:
            gate = self._find_gate_for_stage(stage)
            if gate:
                gate.criteria.update(criteria)
            else:
                new_gate = QualityGate(
                    stage=stage,
                    criteria=criteria,
                    weight=self._stage_weights.get(stage, 1.0),
                )
                self._gates[new_gate.gate_id] = new_gate

        if enabled is not None:
            gate = self._find_gate_for_stage(stage)
            if gate:
                gate.enabled = enabled

    def set_stage_weight(self, stage: QualityStage, weight: float) -> None:
        self._stage_weights[stage] = max(0.0, weight)

    def get_stats(self) -> Dict[str, Any]:
        total_runs = len(self._runs)
        passed_runs = sum(
            1 for r in self._runs.values() if r.status == GateStatus.PASSED
        )
        warning_runs = sum(
            1 for r in self._runs.values() if r.status == GateStatus.WARNING
        )
        failed_runs = sum(
            1 for r in self._runs.values() if r.status == GateStatus.FAILED
        )

        all_scores = [r.overall_score for r in self._runs.values() if r.completed]
        average_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

        per_stage_pass_rates: Dict[str, float] = {}
        stage_counts: Dict[str, int] = {}
        stage_passes: Dict[str, int] = {}
        for run in self._runs.values():
            for result in run.results:
                gate = self._gates.get(result.gate_id)
                if gate is None:
                    continue
                stage_key = gate.stage.value
                stage_counts[stage_key] = stage_counts.get(stage_key, 0) + 1
                if result.status == GateStatus.PASSED:
                    stage_passes[stage_key] = stage_passes.get(stage_key, 0) + 1

        for stage_key, count in stage_counts.items():
            passed = stage_passes.get(stage_key, 0)
            per_stage_pass_rates[stage_key] = round(passed / count * 100, 1) if count else 0.0

        pass_rate = round(passed_runs / total_runs * 100, 1) if total_runs else 0.0

        return {
            "total_runs": total_runs,
            "passed_runs": passed_runs,
            "warning_runs": warning_runs,
            "failed_runs": failed_runs,
            "pass_rate": pass_rate,
            "average_score": round(average_score, 2),
            "per_stage_pass_rates": per_stage_pass_rates,
            "total_stages_executed": self._total_stages_executed,
            "active_gates": sum(1 for g in self._gates.values() if g.enabled),
            "total_gates_configured": len(self._gates),
            "trend_dimensions_tracked": len(self._trend_history),
        }

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        run = self._runs.get(run_id)
        return run.to_dict() if run else None

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        runs = sorted(
            self._runs.values(), key=lambda r: r.started, reverse=True
        )
        return [r.to_summary() for r in runs[:limit]]

    def list_gates(self) -> List[Dict[str, Any]]:
        return [g.to_dict() for g in self._gates.values()]

    def clear_runs(self) -> None:
        self._runs.clear()
        self._total_runs = 0
        self._total_stages_executed = 0

    def _find_gate_for_stage(self, stage: QualityStage) -> Optional[QualityGate]:
        for gate in self._gates.values():
            if gate.stage == stage:
                return gate
        return None

    def _simulate_stage_execution(
        self,
        stage: QualityStage,
        criteria: Dict[str, Any],
        subject_data: Dict[str, Any],
    ) -> tuple:
        details: List[str] = []
        issues: List[Dict[str, Any]] = []

        if stage == QualityStage.SYNTAX_CHECK:
            errors = subject_data.get("syntax_errors", 0)
            max_errors = criteria.get("max_errors", 0)
            if errors > max_errors:
                score = max(0.0, 100.0 - errors * 20.0)
                issues.append({
                    "type": "syntax_error",
                    "count": errors,
                    "fingerprint": "syntax-errors",
                })
                details.append(f"Found {errors} syntax errors (max allowed: {max_errors})")
            else:
                score = 100.0
                details.append("No syntax errors detected")
        elif stage == QualityStage.LINT_CHECK:
            warnings_count = subject_data.get("lint_warnings", 0)
            max_warnings = criteria.get("max_warnings", 10)
            if warnings_count > max_warnings:
                score = max(0.0, 100.0 - (warnings_count - max_warnings) * 5.0)
                issues.append({
                    "type": "lint_warning",
                    "count": warnings_count,
                    "fingerprint": "lint-warnings",
                })
                details.append(
                    f"Found {warnings_count} lint warnings (max allowed: {max_warnings})"
                )
            else:
                score = 100.0
                details.append(f"{warnings_count} lint warnings (within threshold)")
        elif stage == QualityStage.UNIT_TEST:
            coverage = subject_data.get("test_coverage", 0.0)
            min_coverage = criteria.get("min_coverage", 70.0)
            failures = subject_data.get("test_failures", 0)
            if coverage < min_coverage:
                score = coverage
                issues.append({
                    "type": "coverage_gap",
                    "coverage": coverage,
                    "required": min_coverage,
                    "fingerprint": "coverage-gap",
                })
                details.append(
                    f"Coverage {coverage:.1f}% below threshold {min_coverage}%"
                )
            elif failures > 0:
                score = max(0.0, 100.0 - failures * 10.0)
                issues.append({
                    "type": "test_failure",
                    "count": failures,
                    "fingerprint": "test-failures",
                })
                details.append(f"{failures} test failures detected")
            else:
                score = 100.0
                details.append(f"All tests passed, coverage {coverage:.1f}%")
        elif stage == QualityStage.INTEGRATION_TEST:
            pass_rate = subject_data.get("integration_pass_rate", 100.0)
            min_pass_rate = criteria.get("min_pass_rate", 90.0)
            if pass_rate < min_pass_rate:
                score = pass_rate
                issues.append({
                    "type": "integration_failure",
                    "pass_rate": pass_rate,
                    "fingerprint": "integration-fail",
                })
                details.append(
                    f"Integration pass rate {pass_rate:.1f}% below threshold {min_pass_rate}%"
                )
            else:
                score = 100.0
                details.append(f"Integration tests passed at {pass_rate:.1f}%")
        elif stage == QualityStage.PERFORMANCE_BENCHMARK:
            fps = subject_data.get("fps", 60.0)
            min_fps = criteria.get("min_fps", 30.0)
            memory_mb = subject_data.get("memory_mb", 0)
            max_memory = criteria.get("max_memory_mb", 512)
            score = 100.0
            if fps < min_fps:
                factor = fps / min_fps
                score *= factor
                issues.append({
                    "type": "low_fps",
                    "fps": fps,
                    "required": min_fps,
                    "fingerprint": "low-fps",
                })
                details.append(f"FPS {fps:.0f} below minimum {min_fps}")
            if memory_mb > max_memory:
                factor = max_memory / memory_mb
                score *= factor
                issues.append({
                    "type": "high_memory",
                    "memory_mb": memory_mb,
                    "max": max_memory,
                    "fingerprint": "high-memory",
                })
                details.append(
                    f"Memory {memory_mb:.0f}MB exceeds limit {max_memory}MB"
                )
            if score >= 99.0:
                details.append("Performance benchmarks within acceptable range")
        elif stage == QualityStage.SECURITY_SCAN:
            vulns = subject_data.get("vulnerabilities", [])
            max_vulns = criteria.get("max_vulnerabilities", 0)
            if len(vulns) > max_vulns:
                score = max(0.0, 100.0 - len(vulns) * 15.0)
                for vuln in vulns[:5]:
                    issues.append({
                        "type": "vulnerability",
                        "severity": vuln.get("severity", "unknown"),
                        "fingerprint": f"vuln-{vuln.get('id', uuid.uuid4().hex[:6])}",
                    })
                details.append(
                    f"Found {len(vulns)} security vulnerabilities (max allowed: {max_vulns})"
                )
            else:
                score = 100.0
                details.append("No security vulnerabilities found")
        elif stage == QualityStage.ACCESSIBILITY_AUDIT:
            violations = subject_data.get("a11y_violations", 0)
            max_violations = criteria.get("max_violations", 3)
            if violations > max_violations:
                score = max(0.0, 100.0 - (violations - max_violations) * 10.0)
                issues.append({
                    "type": "accessibility_violation",
                    "count": violations,
                    "fingerprint": "a11y-violations",
                })
                details.append(
                    f"Found {violations} accessibility violations (max allowed: {max_violations})"
                )
            else:
                score = 100.0
                details.append(f"{violations} accessibility violations (within threshold)")
        elif stage == QualityStage.PLAYTEST_VALIDATION:
            playability = subject_data.get("playability_score", 100.0)
            completion = subject_data.get("completion_rate", 100.0)
            min_playability = criteria.get("min_playability", 70.0)
            score = (playability * 0.6 + completion * 0.4)
            if score < min_playability:
                issues.append({
                    "type": "low_playability",
                    "score": score,
                    "fingerprint": "low-playability",
                })
                details.append(
                    f"Playtest score {score:.1f} below threshold {min_playability}"
                )
            else:
                details.append(f"Playtest passed with score {score:.1f}")
        elif stage == QualityStage.VISUAL_REGRESSION:
            diff_pct = subject_data.get("visual_diff_percent", 0.0)
            max_diff = criteria.get("max_diff_percent", 5.0)
            if diff_pct > max_diff:
                score = max(0.0, 100.0 - (diff_pct - max_diff) * 10.0)
                issues.append({
                    "type": "visual_regression",
                    "diff_percent": diff_pct,
                    "fingerprint": "visual-regression",
                })
                details.append(
                    f"Visual diff {diff_pct:.1f}% exceeds threshold {max_diff}%"
                )
            else:
                score = 100.0
                details.append(f"Visual diff {diff_pct:.1f}% within threshold")
        elif stage == QualityStage.ASSET_VALIDATION:
            corrupt = subject_data.get("corrupt_assets", 0)
            missing = subject_data.get("missing_assets", 0)
            total_issues = corrupt + missing
            if total_issues > 0:
                score = max(0.0, 100.0 - total_issues * 25.0)
                if corrupt > 0:
                    issues.append({
                        "type": "corrupt_asset",
                        "count": corrupt,
                        "fingerprint": "corrupt-assets",
                    })
                if missing > 0:
                    issues.append({
                        "type": "missing_asset",
                        "count": missing,
                        "fingerprint": "missing-assets",
                    })
                details.append(
                    f"Found {corrupt} corrupt and {missing} missing assets"
                )
            else:
                score = 100.0
                details.append("All assets validated successfully")
        else:
            score = 100.0
            details.append(f"No specific checks for stage '{stage.value}'")

        return score, details, issues

    def _record_trend(self, stage: QualityStage, score: float) -> None:
        dims = STAGE_TO_DIMENSIONS.get(stage, [])
        for dim in dims:
            key = f"dim:{dim.value}"
            self._trend_history.setdefault(key, []).append(score)
            if len(self._trend_history[key]) > 1000:
                self._trend_history[key] = self._trend_history[key][-1000:]


_quality_chain_instance: Optional[QualityChainEngine] = None


def get_quality_chain() -> QualityChainEngine:
    global _quality_chain_instance
    if _quality_chain_instance is None:
        _quality_chain_instance = QualityChainEngine()
    return _quality_chain_instance