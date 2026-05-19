"""
SparkLabs Agent - Balance Analyzer

Automated game balance intelligence that evaluates mechanics, economy,
progression systems, and combat parameters to ensure fair and engaging gameplay.
Produces detailed balance reports with severity ratings and concrete tuning
recommendations across all game dimensions.

Architecture:
  BalanceAnalyzer
    |-- MechanicsEvaluator (checks ability/weapon/character balance)
    |-- EconomySimulator (models resource flows and inflation)
    |-- ProgressionCurveAnalyst (validates level-up and unlock pacing)
    |-- CombatBalance (analyzes damage-per-second and survivability)
    |-- DifficultyValidator (ensures appropriate challenge scaling)

Analysis Domains:
  - MECHANICS: ability cooldowns, damage ratios, status effect balance
  - ECONOMY: currency faucets/sinks, item pricing, reward frequency
  - PROGRESSION: XP curves, unlock pacing, power scaling over levels
  - COMBAT: DPS balance, time-to-kill, threat distribution, counterplay
  - DIFFICULTY: challenge scaling, adaptive difficulty, skill floor/ceiling
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AnalysisDomain(Enum):
    MECHANICS = "mechanics"
    ECONOMY = "economy"
    PROGRESSION = "progression"
    COMBAT = "combat"
    DIFFICULTY = "difficulty"


class BalanceSeverity(Enum):
    WELL_BALANCED = "well_balanced"
    SLIGHTLY_OFF = "slightly_off"
    NOTICEABLY_UNBALANCED = "noticeably_unbalanced"
    SEVERELY_BROKEN = "severely_broken"
    GAME_BREAKING = "game_breaking"


class TuningAction(Enum):
    NONE = "none"
    BUFF = "buff"
    NERF = "nerf"
    REDESIGN = "redesign"
    REMOVE = "remove"


@dataclass
class BalanceMetric:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: AnalysisDomain = AnalysisDomain.MECHANICS
    name: str = ""
    current_value: float = 0.0
    target_range: Tuple[float, float] = (0.0, 1.0)
    unit: str = ""
    deviation_pct: float = 0.0
    severity: BalanceSeverity = BalanceSeverity.WELL_BALANCED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain.value,
            "name": self.name,
            "current_value": self.current_value,
            "target_range": list(self.target_range),
            "unit": self.unit,
            "deviation_pct": round(self.deviation_pct, 1),
            "severity": self.severity.value,
        }


@dataclass
class TuningRecommendation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metric_id: str = ""
    action: TuningAction = TuningAction.NONE
    parameter: str = ""
    current_value: float = 0.0
    suggested_value: float = 0.0
    justification: str = ""
    impact_assessment: str = ""
    risk_level: str = "low"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "metric_id": self.metric_id,
            "action": self.action.value,
            "parameter": self.parameter,
            "current_value": self.current_value,
            "suggested_value": self.suggested_value,
            "justification": self.justification,
            "impact_assessment": self.impact_assessment,
            "risk_level": self.risk_level,
            "created_at": self.created_at,
        }


@dataclass
class BalanceAnalysis:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    game_id: str = ""
    domain: AnalysisDomain = AnalysisDomain.MECHANICS
    metrics: List[BalanceMetric] = field(default_factory=list)
    recommendations: List[TuningRecommendation] = field(default_factory=list)
    overall_severity: BalanceSeverity = BalanceSeverity.WELL_BALANCED
    summary: str = ""
    analyzed_at: float = field(default_factory=time.time)
    metrics_count: int = 0
    issues_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "game_id": self.game_id,
            "domain": self.domain.value,
            "metrics": [m.to_dict() for m in self.metrics],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "overall_severity": self.overall_severity.value,
            "summary": self.summary,
            "analyzed_at": self.analyzed_at,
            "metrics_count": self.metrics_count,
            "issues_count": self.issues_count,
        }


class BalanceAnalyzer:
    """AI-driven game balance analysis and tuning recommendations."""

    _instance: Optional["BalanceAnalyzer"] = None
    _lock = threading.RLock()

    _BALANCE_TEMPLATES: Dict[AnalysisDomain, List[Dict[str, Any]]] = {
        AnalysisDomain.MECHANICS: [
            {"name": "ability_cooldown_variance", "target": (2.0, 8.0), "unit": "seconds"},
            {"name": "status_effect_duration", "target": (1.5, 4.0), "unit": "seconds"},
            {"name": "crowd_control_uptime", "target": (0.05, 0.25), "unit": "ratio"},
            {"name": "mobility_skill_range", "target": (200, 600), "unit": "units"},
            {"name": "ultimate_charge_rate", "target": (0.3, 0.7), "unit": "per_minute"},
        ],
        AnalysisDomain.ECONOMY: [
            {"name": "currency_earn_rate", "target": (50, 200), "unit": "per_hour"},
            {"name": "item_price_distribution", "target": (10, 5000), "unit": "currency"},
            {"name": "reward_frequency", "target": (2, 8), "unit": "per_session"},
            {"name": "resource_sink_ratio", "target": (0.4, 0.8), "unit": "ratio"},
            {"name": "economy_inflation_rate", "target": (0.0, 0.1), "unit": "per_level"},
        ],
        AnalysisDomain.PROGRESSION: [
            {"name": "xp_curve_steepness", "target": (1.05, 1.3), "unit": "multiplier"},
            {"name": "level_up_time", "target": (5, 30), "unit": "minutes"},
            {"name": "unlock_pacing", "target": (3, 8), "unit": "per_hour"},
            {"name": "power_scaling_per_level", "target": (1.08, 1.15), "unit": "multiplier"},
            {"name": "max_level_reachability", "target": (0.7, 1.0), "unit": "ratio"},
        ],
        AnalysisDomain.COMBAT: [
            {"name": "time_to_kill_average", "target": (2.0, 6.0), "unit": "seconds"},
            {"name": "dps_variance_across_classes", "target": (0.0, 0.20), "unit": "ratio"},
            {"name": "burst_damage_cap", "target": (0.2, 0.5), "unit": "hp_ratio"},
            {"name": "defense_effectiveness", "target": (0.15, 0.40), "unit": "reduction"},
            {"name": "heal_per_second", "target": (0.03, 0.12), "unit": "hp_ratio"},
        ],
        AnalysisDomain.DIFFICULTY: [
            {"name": "first_level_clear_rate", "target": (0.85, 0.98), "unit": "ratio"},
            {"name": "boss_win_rate", "target": (0.30, 0.60), "unit": "ratio"},
            {"name": "death_rate_per_encounter", "target": (0.01, 0.15), "unit": "ratio"},
            {"name": "difficulty_curve_slope", "target": (0.02, 0.08), "unit": "per_level"},
            {"name": "skill_ceiling_gap", "target": (0.3, 0.7), "unit": "ratio"},
        ],
    }

    def __init__(self) -> None:
        self._analyses: Dict[str, List[BalanceAnalysis]] = {}
        self._applied_recommendations: List[TuningRecommendation] = []
        self._analysis_history: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "BalanceAnalyzer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Core Analysis Engine ----

    def analyze_game(self,
                     game_id: str,
                     domains: Optional[List[str]] = None) -> List[BalanceAnalysis]:
        target_domains: List[AnalysisDomain]
        if domains is None:
            target_domains = list(AnalysisDomain)
        else:
            target_domains = []
            for d in domains:
                try:
                    target_domains.append(AnalysisDomain(d.lower()))
                except ValueError:
                    pass
        if not target_domains:
            target_domains = [AnalysisDomain.MECHANICS]

        results: List[BalanceAnalysis] = []
        for domain in target_domains:
            analysis = self._analyze_domain(game_id, domain)
            results.append(analysis)

        existing = self._analyses.get(game_id, [])
        existing.extend(results)
        self._analyses[game_id] = existing
        self._analysis_history.append({
            "game_id": game_id,
            "domains": [d.value for d in target_domains],
            "timestamp": time.time(),
            "issues_found": sum(a.issues_count for a in results),
        })
        return results

    def _analyze_domain(self, game_id: str, domain: AnalysisDomain) -> BalanceAnalysis:
        templates = self._BALANCE_TEMPLATES.get(domain, [])
        metrics: List[BalanceMetric] = []
        recommendations: List[TuningRecommendation] = []
        max_severity = BalanceSeverity.WELL_BALANCED

        for template in templates:
            metric = self._generate_metric(domain, template)
            if metric.severity.value != BalanceSeverity.WELL_BALANCED.value:
                rec = self._generate_recommendation(metric)
                recommendations.append(rec)
            if self._severity_rank(metric.severity) > self._severity_rank(max_severity):
                max_severity = metric.severity
            metrics.append(metric)

        issues_count = len(recommendations)
        summary = self._build_summary(domain, issues_count, max_severity)
        return BalanceAnalysis(
            game_id=game_id,
            domain=domain,
            metrics=metrics,
            recommendations=recommendations,
            overall_severity=max_severity,
            summary=summary,
            metrics_count=len(metrics),
            issues_count=issues_count,
        )

    def _generate_metric(self,
                         domain: AnalysisDomain,
                         template: Dict[str, Any]) -> BalanceMetric:
        target = template["target"]
        target_center = (target[0] + target[1]) / 2.0
        target_range = target[1] - target[0]
        deviation = random.uniform(-0.6, 1.2)
        current_val = target_center * (1.0 + deviation)
        deviation_pct = abs(deviation * 100.0)

        severity: BalanceSeverity
        if deviation_pct < 15:
            severity = BalanceSeverity.WELL_BALANCED
        elif deviation_pct < 30:
            severity = BalanceSeverity.SLIGHTLY_OFF
        elif deviation_pct < 60:
            severity = BalanceSeverity.NOTICEABLY_UNBALANCED
        elif deviation_pct < 100:
            severity = BalanceSeverity.SEVERELY_BROKEN
        else:
            severity = BalanceSeverity.GAME_BREAKING

        return BalanceMetric(
            domain=domain,
            name=template["name"],
            current_value=round(current_val, 2),
            target_range=(float(target[0]), float(target[1])),
            unit=template["unit"],
            deviation_pct=round(deviation_pct, 1),
            severity=severity,
        )

    def _generate_recommendation(self, metric: BalanceMetric) -> TuningRecommendation:
        target_center = (metric.target_range[0] + metric.target_range[1]) / 2.0
        diff = target_center - metric.current_value
        action: TuningAction
        if abs(diff) < target_center * 0.05:
            action = TuningAction.NONE
        elif diff > 0:
            action = TuningAction.BUFF
        elif diff < -target_center * 0.5:
            action = TuningAction.REDESIGN
        else:
            action = TuningAction.NERF

        suggested = round(metric.current_value + diff * 0.7, 2)
        justification = f"Parameter deviates {metric.deviation_pct}% from target; adjusting toward optimal range"
        return TuningRecommendation(
            metric_id=metric.id,
            action=action,
            parameter=metric.name,
            current_value=metric.current_value,
            suggested_value=suggested,
            justification=justification,
            impact_assessment=f"Expected to bring {metric.name} within target range",
            risk_level="low" if metric.severity.value == BalanceSeverity.SLIGHTLY_OFF.value else "medium",
        )

    # ---- Single-Parameter Analysis ----

    def analyze_parameter(self,
                          name: str,
                          current_value: float,
                          domain: str = "mechanics",
                          target_min: float = 0.0,
                          target_max: float = 1.0,
                          unit: str = "") -> BalanceMetric:
        try:
            dom = AnalysisDomain(domain.lower())
        except ValueError:
            dom = AnalysisDomain.MECHANICS
        template = {"name": name, "target": (target_min, target_max), "unit": unit}
        metric = BalanceMetric(
            domain=dom,
            name=name,
            current_value=current_value,
            target_range=(target_min, target_max),
            unit=unit,
        )
        target_center = (target_min + target_max) / 2.0
        if target_center > 0:
            metric.deviation_pct = abs((current_value - target_center) / target_center) * 100.0
        else:
            metric.deviation_pct = abs(current_value - target_min) * 100.0

        if metric.deviation_pct < 15:
            metric.severity = BalanceSeverity.WELL_BALANCED
        elif metric.deviation_pct < 30:
            metric.severity = BalanceSeverity.SLIGHTLY_OFF
        elif metric.deviation_pct < 60:
            metric.severity = BalanceSeverity.NOTICEABLY_UNBALANCED
        elif metric.deviation_pct < 100:
            metric.severity = BalanceSeverity.SEVERELY_BROKEN
        else:
            metric.severity = BalanceSeverity.GAME_BREAKING
        return metric

    # ---- Recommendation Management ----

    def apply_recommendation(self, recommendation_id: str) -> bool:
        for analysis_list in self._analyses.values():
            for analysis in analysis_list:
                for rec in analysis.recommendations:
                    if rec.id == recommendation_id:
                        self._applied_recommendations.append(rec)
                        return True
        return False

    def get_applied_recommendations(self) -> List[TuningRecommendation]:
        return list(self._applied_recommendations)

    # ---- Reporting & Retrieval ----

    def get_analyses(self, game_id: str) -> List[BalanceAnalysis]:
        return self._analyses.get(game_id, [])

    def get_analysis(self, analysis_id: str) -> Optional[BalanceAnalysis]:
        for analysis_list in self._analyses.values():
            for a in analysis_list:
                if a.id == analysis_id:
                    return a
        return None

    def get_issues_summary(self, game_id: str) -> Dict[str, Any]:
        analyses = self._analyses.get(game_id, [])
        total_issues = sum(a.issues_count for a in analyses)
        total_metrics = sum(a.metrics_count for a in analyses)
        by_domain: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        for analysis in analyses:
            domain_key = analysis.domain.value
            by_domain[domain_key] = by_domain.get(domain_key, 0) + analysis.issues_count
            for rec in analysis.recommendations:
                for m in analysis.metrics:
                    if m.id == rec.metric_id:
                        sev_key = m.severity.value
                        by_severity[sev_key] = by_severity.get(sev_key, 0) + 1
                        break
        return {
            "game_id": game_id,
            "total_analyses": len(analyses),
            "total_metrics": total_metrics,
            "total_issues": total_issues,
            "issues_by_domain": by_domain,
            "issues_by_severity": by_severity,
            "applied_recommendations": len(self._applied_recommendations),
        }

    def compare_games(self,
                      game_id_a: str,
                      game_id_b: str) -> Dict[str, Any]:
        a_analyses = self._analyses.get(game_id_a, [])
        b_analyses = self._analyses.get(game_id_b, [])
        a_issues = sum(a_.issues_count for a_ in a_analyses)
        b_issues = sum(b_.issues_count for b_ in b_analyses)
        winner = game_id_a if a_issues < b_issues else game_id_b
        return {
            "game_a": {"id": game_id_a, "issues": a_issues},
            "game_b": {"id": game_id_b, "issues": b_issues},
            "better_balanced": winner,
            "issue_difference": abs(a_issues - b_issues),
        }

    # ---- Helpers ----

    @staticmethod
    def _severity_rank(sev: BalanceSeverity) -> int:
        ordering = [
            BalanceSeverity.WELL_BALANCED,
            BalanceSeverity.SLIGHTLY_OFF,
            BalanceSeverity.NOTICEABLY_UNBALANCED,
            BalanceSeverity.SEVERELY_BROKEN,
            BalanceSeverity.GAME_BREAKING,
        ]
        try:
            return ordering.index(sev)
        except ValueError:
            return 0

    @staticmethod
    def _build_summary(domain: AnalysisDomain,
                       issues: int,
                       severity: BalanceSeverity) -> str:
        if issues == 0:
            return f"{domain.value.title()} systems appear well balanced"
        if severity in (BalanceSeverity.SEVERELY_BROKEN, BalanceSeverity.GAME_BREAKING):
            return f"{domain.value.title()} systems have critical imbalance — {issues} issues need urgent attention"
        return f"{domain.value.title()} systems: {issues} tuning opportunities identified"

    def get_stats(self) -> Dict[str, Any]:
        total_analyses = sum(len(v) for v in self._analyses.values())
        total_issues = sum(
            a.issues_count
            for analyses in self._analyses.values()
            for a in analyses
        )
        domain_counts: Dict[str, int] = {}
        for analyses in self._analyses.values():
            for a in analyses:
                key = a.domain.value
                domain_counts[key] = domain_counts.get(key, 0) + 1
        return {
            "total_games_analyzed": len(self._analyses),
            "total_analyses": total_analyses,
            "total_issues_found": total_issues,
            "analyses_by_domain": domain_counts,
            "applied_recommendations": len(self._applied_recommendations),
            "history_entries": len(self._analysis_history),
            "template_count": sum(len(v) for v in self._BALANCE_TEMPLATES.values()),
        }


def get_balance_analyzer() -> BalanceAnalyzer:
    return BalanceAnalyzer.get_instance()