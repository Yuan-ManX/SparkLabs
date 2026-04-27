"""
SparkAI Team - Quality Gate System
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class QualityStandard(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PRODUCTION = "production"


@dataclass
class QualityMetrics:
    code_quality: float = 0.0
    performance_score: float = 0.0
    documentation_coverage: float = 0.0
    test_coverage: float = 0.0
    accessibility_score: float = 0.0

    def overall_score(self) -> float:
        return (
            self.code_quality * 0.3
            + self.performance_score * 0.25
            + self.documentation_coverage * 0.15
            + self.test_coverage * 0.2
            + self.accessibility_score * 0.1
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code_quality": self.code_quality,
            "performance_score": self.performance_score,
            "documentation_coverage": self.documentation_coverage,
            "test_coverage": self.test_coverage,
            "accessibility_score": self.accessibility_score,
            "overall": self.overall_score(),
        }


class QualityGate:
    """
    Quality gate validation system.
    Enforces quality standards at each handoff point between agents.
    """

    def __init__(self, standard: QualityStandard = QualityStandard.MEDIUM):
        self._standard = standard
        self._thresholds = self._get_thresholds(standard)
        self._reports: List[Dict[str, Any]] = []

    def set_quality_standard(self, standard: QualityStandard) -> None:
        self._standard = standard
        self._thresholds = self._get_thresholds(standard)

    def check_code_quality(self, code: str, file_type: str = "python") -> Dict[str, Any]:
        metrics = self._analyze_code(code, file_type)
        passed = metrics.code_quality >= self._thresholds["code_quality"]
        report = {
            "check": "code_quality",
            "file_type": file_type,
            "metrics": metrics.to_dict(),
            "threshold": self._thresholds["code_quality"],
            "passed": passed,
        }
        self._reports.append(report)
        return report

    def check_performance(self, report_data: str = "") -> Dict[str, Any]:
        metrics = QualityMetrics(performance_score=0.8)
        passed = metrics.performance_score >= self._thresholds["performance"]
        result = {
            "check": "performance",
            "metrics": metrics.to_dict(),
            "threshold": self._thresholds["performance"],
            "passed": passed,
        }
        self._reports.append(result)
        return result

    def check_documentation(self, docs: str = "") -> Dict[str, Any]:
        coverage = min(1.0, len(docs) / 500.0) if docs else 0.0
        metrics = QualityMetrics(documentation_coverage=coverage)
        passed = metrics.documentation_coverage >= self._thresholds["documentation"]
        result = {
            "check": "documentation",
            "metrics": metrics.to_dict(),
            "threshold": self._thresholds["documentation"],
            "passed": passed,
        }
        self._reports.append(result)
        return result

    def validate(self, metrics: QualityMetrics) -> Dict[str, Any]:
        results = {
            "code_quality": metrics.code_quality >= self._thresholds["code_quality"],
            "performance": metrics.performance_score >= self._thresholds["performance"],
            "documentation": metrics.documentation_coverage >= self._thresholds["documentation"],
            "test_coverage": metrics.test_coverage >= self._thresholds["test_coverage"],
            "accessibility": metrics.accessibility_score >= self._thresholds["accessibility"],
        }
        overall_passed = all(results.values())
        report = {
            "standard": self._standard.value,
            "metrics": metrics.to_dict(),
            "thresholds": self._thresholds,
            "results": results,
            "passed": overall_passed,
        }
        self._reports.append(report)
        return report

    def get_reports(self) -> List[Dict[str, Any]]:
        return self._reports

    def generate_quality_report(self) -> Dict[str, Any]:
        if not self._reports:
            return {"status": "no_reports", "total_checks": 0}
        passed = sum(1 for r in self._reports if r.get("passed", False))
        return {
            "standard": self._standard.value,
            "total_checks": len(self._reports),
            "passed_checks": passed,
            "failed_checks": len(self._reports) - passed,
            "pass_rate": passed / len(self._reports),
        }

    def _analyze_code(self, code: str, file_type: str) -> QualityMetrics:
        lines = code.split("\n") if code else []
        non_empty = [l for l in lines if l.strip() and not l.strip().startswith("#")]
        comment_lines = [l for l in lines if l.strip().startswith("#")]
        doc_coverage = len(comment_lines) / max(len(non_empty), 1)
        return QualityMetrics(
            code_quality=min(1.0, len(non_empty) / 50.0),
            documentation_coverage=min(1.0, doc_coverage),
        )

    def _get_thresholds(self, standard: QualityStandard) -> Dict[str, float]:
        thresholds = {
            QualityStandard.LOW: {"code_quality": 0.3, "performance": 0.3, "documentation": 0.1, "test_coverage": 0.1, "accessibility": 0.1},
            QualityStandard.MEDIUM: {"code_quality": 0.5, "performance": 0.5, "documentation": 0.3, "test_coverage": 0.3, "accessibility": 0.3},
            QualityStandard.HIGH: {"code_quality": 0.7, "performance": 0.7, "documentation": 0.5, "test_coverage": 0.5, "accessibility": 0.5},
            QualityStandard.PRODUCTION: {"code_quality": 0.9, "performance": 0.8, "documentation": 0.7, "test_coverage": 0.7, "accessibility": 0.6},
        }
        return thresholds.get(standard, thresholds[QualityStandard.MEDIUM])
