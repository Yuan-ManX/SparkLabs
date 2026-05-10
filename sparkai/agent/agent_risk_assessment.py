"""
SparkLabs Agent - Risk Assessment Engine

Proactive safety evaluation for AI-generated game content and
engine configurations. Assesses risks across technical stability,
gameplay integrity, content appropriateness, and performance
impact domains to ensure AI-native game generation produces
reliable, appropriate, and performant results.

Architecture:
  RiskAssessmentEngine
    |-- TechnicalRiskAnalyzer (crash/stability forecaster)
    |-- GameplayRiskAnalyzer (balance-breaking change detection)
    |-- ContentRiskAnalyzer (appropriateness screening)
    |-- PerformanceRiskAnalyzer (frame budget impact scoring)
    |-- RiskAggregator (cross-domain risk synthesis)
    |-- MitigationPlanner (remediation suggestion generation)

Risk Categories:
  - TECHNICAL: crashes, memory leaks, infinite loops
  - GAMEPLAY: balance disruption, progression breaking
  - CONTENT: inappropriate material, cultural insensitivity
  - PERFORMANCE: frame drops, load spikes, memory pressure
  - SECURITY: injection risks, data exposure, unsafe operations
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class RiskCategory(Enum):
    TECHNICAL = "technical"
    GAMEPLAY = "gameplay"
    CONTENT = "content"
    PERFORMANCE = "performance"
    SECURITY = "security"


class RiskLevel(Enum):
    NONE = (0, "none")
    LOW = (1, "low")
    MODERATE = (2, "moderate")
    HIGH = (3, "high")
    CRITICAL = (4, "critical")

    def __new__(cls, score, label):
        obj = object.__new__(cls)
        obj._value_ = label
        obj.score = score
        return obj


class MitigationType(Enum):
    BLOCK = "block"
    WARN = "warn"
    SANITIZE = "sanitize"
    CAP = "cap"
    REVIEW = "review"


@dataclass
class RiskFinding:
    finding_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    category: RiskCategory = RiskCategory.TECHNICAL
    level: RiskLevel = RiskLevel.LOW
    title: str = ""
    description: str = ""
    location: str = ""
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "category": self.category.value,
            "level": self.level.value,
            "title": self.title,
            "location": self.location,
            "confidence": self.confidence,
        }


@dataclass
class RiskAssessmentReport:
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    target: str = ""
    findings: List[RiskFinding] = field(default_factory=list)
    overall_level: RiskLevel = RiskLevel.LOW
    is_approved: bool = True
    blocked_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "target": self.target,
            "findings_count": len(self.findings),
            "overall_level": self.overall_level.value,
            "approved": self.is_approved,
            "blocked_reasons": self.blocked_reasons,
            "critical_findings": sum(1 for f in self.findings if f.level.score >= RiskLevel.HIGH.score),
        }


class RiskAssessmentEngine:
    _instance: Optional[RiskAssessmentEngine] = None

    @classmethod
    def get_instance(cls) -> RiskAssessmentEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._category_thresholds: Dict[RiskCategory, RiskLevel] = {
            RiskCategory.TECHNICAL: RiskLevel.HIGH,
            RiskCategory.GAMEPLAY: RiskLevel.MODERATE,
            RiskCategory.CONTENT: RiskLevel.MODERATE,
            RiskCategory.PERFORMANCE: RiskLevel.MODERATE,
            RiskCategory.SECURITY: RiskLevel.HIGH,
        }
        self._auto_block_categories: List[RiskCategory] = [RiskCategory.SECURITY]
        self._reports: List[RiskAssessmentReport] = []
        self._total_assessments: int = 0

    def assess_technical(self, code_snippet: str, context: Optional[Dict[str, Any]] = None) -> List[RiskFinding]:
        findings = []
        dangerous_patterns = [
            ("eval(", "Runtime code execution detected"),
            ("exec(", "Dynamic code execution detected"),
            ("while True:", "Potential infinite loop"),
            ("os.system(", "System command invocation"),
            ("__import__", "Dynamic import detected"),
        ]
        for pattern, desc in dangerous_patterns:
            if pattern in code_snippet:
                findings.append(RiskFinding(
                    category=RiskCategory.TECHNICAL,
                    level=RiskLevel.HIGH,
                    title=desc,
                    description=f"Found potentially unsafe pattern: {pattern}",
                    location=f"code:{code_snippet[:50]}",
                    confidence=0.8,
                ))
        return findings

    def assess_gameplay(self, changes: Dict[str, Any]) -> List[RiskFinding]:
        findings = []
        substantial_changes = []
        for key, value in changes.items():
            if isinstance(value, (int, float)):
                if abs(value) > 10.0:
                    substantial_changes.append(key)
        if len(substantial_changes) > 3:
            findings.append(RiskFinding(
                category=RiskCategory.GAMEPLAY,
                level=RiskLevel.MODERATE,
                title="Multiple substantial parameter changes",
                description=f"Significant changes to {len(substantial_changes)} parameters may disrupt balance",
                location=",".join(substantial_changes[:3]),
                confidence=0.6,
            ))
        return findings

    def assess_content(self, text: str) -> List[RiskFinding]:
        findings = []
        sensitive_terms = ["violence", "gore", "explicit", "graphic"]
        if any(term in text.lower() for term in sensitive_terms):
            findings.append(RiskFinding(
                category=RiskCategory.CONTENT,
                level=RiskLevel.MODERATE,
                title="Potentially sensitive content detected",
                description="Content contains flagged terms requiring review",
                location=f"text:{text[:80]}",
                confidence=0.5,
            ))
        return findings

    def assess_performance(self, resource_estimate: Dict[str, Any]) -> List[RiskFinding]:
        findings = []
        if resource_estimate.get("estimated_entities", 0) > 1000:
            findings.append(RiskFinding(
                category=RiskCategory.PERFORMANCE,
                level=RiskLevel.MODERATE,
                title="High entity count risk",
                description=f"Estimated {resource_estimate['estimated_entities']} entities may cause performance issues",
                location="scene",
                confidence=0.7,
            ))
        if resource_estimate.get("estimated_memory_mb", 0) > 500:
            findings.append(RiskFinding(
                category=RiskCategory.PERFORMANCE,
                level=RiskLevel.HIGH,
                title="High memory usage risk",
                description=f"Estimated {resource_estimate['estimated_memory_mb']}MB memory usage",
                location="memory",
                confidence=0.8,
            ))
        return findings

    def run_assessment(self, target: str, code: str = "", changes: Optional[Dict[str, Any]] = None,
                       text: str = "", resources: Optional[Dict[str, Any]] = None) -> RiskAssessmentReport:
        report = RiskAssessmentReport(target=target)
        report.findings.extend(self.assess_technical(code))
        if changes:
            report.findings.extend(self.assess_gameplay(changes))
        if text:
            report.findings.extend(self.assess_content(text))
        if resources:
            report.findings.extend(self.assess_performance(resources))

        max_score = 0
        for finding in report.findings:
            if finding.category in self._auto_block_categories and finding.level.score >= RiskLevel.HIGH.score:
                report.is_approved = False
                report.blocked_reasons.append(finding.title)
            if finding.level.score >= self._category_thresholds.get(finding.category, RiskLevel.MODERATE).score:
                report.warnings.append(f"[{finding.category.value}] {finding.title}")
            max_score = max(max_score, finding.level.score)

        report.overall_level = RiskLevel(max((rl for rl in RiskLevel if rl.score == max_score), key=lambda r: r.score))
        self._reports.append(report)
        self._total_assessments += 1
        if len(self._reports) > 50:
            self._reports = self._reports[-50:]
        return report

    def get_recent_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._reports[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        blocked = sum(1 for r in self._reports if not r.is_approved)
        return {
            "total_assessments": self._total_assessments,
            "recent_reports": len(self._reports),
            "blocked_count": blocked,
            "blocked_rate": blocked / max(1, self._total_assessments),
            "auto_block_categories": [c.value for c in self._auto_block_categories],
        }


def get_risk_assessor() -> RiskAssessmentEngine:
    return RiskAssessmentEngine.get_instance()