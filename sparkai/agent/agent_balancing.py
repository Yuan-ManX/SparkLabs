"""
SparkLabs Agent - Game Balance Tuner

Automated game balance analysis and parameter optimization.
Continuously monitors gameplay metrics to identify imbalance
patterns and applies corrective tuning to game parameters,
maintaining competitive fairness and engagement across all
player segments.

Architecture:
  GameBalanceTuner
    |-- MetricCollector (real-time gameplay statistic aggregation)
    |-- ImbalanceDetector (anomaly and disparity identification)
    |-- ParameterOptimizer (gradient-free parameter tuning)
    |-- FairnessValidator (competitive equilibrium verification)
    |-- TuningProfile (per-game-mode balance configuration)

Tuning Domains:
  - COMBAT: weapon/ability damage, health, defense ratios
  - ECONOMY: resource generation rates, pricing curves
  - PROGRESSION: XP curves, unlock pacing, difficulty scaling
  - SPAWNING: enemy distribution, loot drop frequencies
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TuningDomain(Enum):
    COMBAT = "combat"
    ECONOMY = "economy"
    PROGRESSION = "progression"
    SPAWNING = "spawning"


class BalanceStatus(Enum):
    OPTIMAL = "optimal"
    ACCEPTABLE = "acceptable"
    IMBALANCED = "imbalanced"
    CRITICAL = "critical"


@dataclass
class GameParameter:
    param_id: str
    name: str = ""
    domain: TuningDomain = TuningDomain.COMBAT
    current_value: float = 1.0
    min_value: float = 0.1
    max_value: float = 10.0
    ideal_range: Tuple[float, float] = (0.8, 1.2)
    weight: float = 1.0
    locked: bool = False
    history: List[float] = field(default_factory=list)


@dataclass
class BalanceMetric:
    metric_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    domain: TuningDomain = TuningDomain.COMBAT
    player_segment: str = "all"
    current_value: float = 0.0
    target_value: float = 0.0
    tolerance: float = 0.15
    sample_count: int = 0


@dataclass
class BalanceReport:
    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    domain: TuningDomain = TuningDomain.COMBAT
    status: BalanceStatus = BalanceStatus.OPTIMAL
    metrics: List[BalanceMetric] = field(default_factory=list)
    recommended_changes: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class GameBalanceTuner:
    _instance: Optional[GameBalanceTuner] = None

    def __init__(self):
        self._parameters: Dict[str, GameParameter] = {}
        self._metrics: List[BalanceMetric] = []
        self._reports: List[BalanceReport] = []
        self._tuning_count: int = 0
        self._sensitivity: float = 0.3

    @classmethod
    def get_instance(cls) -> GameBalanceTuner:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_parameter(self, param: GameParameter) -> str:
        self._parameters[param.param_id] = param
        return param.param_id

    def set_sensitivity(self, sensitivity: float):
        self._sensitivity = max(0.05, min(1.0, sensitivity))

    def report_metric(self, metric: BalanceMetric):
        self._metrics.append(metric)

    def analyze_domain(self, domain: TuningDomain) -> BalanceReport:
        domain_metrics = [m for m in self._metrics if m.domain == domain]
        domain_params = {
            pid: p for pid, p in self._parameters.items() if p.domain == domain
        }

        if not domain_metrics:
            return BalanceReport(domain=domain, status=BalanceStatus.OPTIMAL)

        imbalances = []
        for metric in domain_metrics:
            deviation = abs(metric.current_value - metric.target_value)
            if deviation > metric.tolerance * metric.target_value:
                imbalances.append(metric)

        status = BalanceStatus.OPTIMAL
        if len(imbalances) > len(domain_metrics) * 0.5:
            status = BalanceStatus.CRITICAL
        elif len(imbalances) > len(domain_metrics) * 0.3:
            status = BalanceStatus.IMBALANCED
        elif imbalances:
            status = BalanceStatus.ACCEPTABLE

        recommended = {}
        for metric in imbalances:
            for param_id, param in domain_params.items():
                if param.locked:
                    continue
                deviation = metric.current_value - metric.target_value
                adjustment = -deviation * self._sensitivity * param.weight
                new_value = max(param.min_value, min(param.max_value, param.current_value + adjustment))
                recommended[param_id] = new_value

        report = BalanceReport(
            domain=domain,
            status=status,
            metrics=imbalances,
            recommended_changes=recommended,
            confidence=1.0 - min(1.0, len(imbalances) / max(1, len(domain_metrics))),
        )
        self._reports.append(report)
        return report

    def apply_tuning(self, report: BalanceReport) -> int:
        count = 0
        for param_id, value in report.recommended_changes.items():
            param = self._parameters.get(param_id)
            if param and not param.locked:
                param.history.append(param.current_value)
                param.current_value = round(value, 4)
                count += 1
                self._tuning_count += 1
        return count

    def analyze_all(self) -> Dict[TuningDomain, BalanceReport]:
        results = {}
        for domain in TuningDomain:
            results[domain] = self.analyze_domain(domain)
        return results

    def get_parameter_snapshot(self, domain: Optional[TuningDomain] = None) -> Dict[str, Any]:
        params = {}
        for pid, param in self._parameters.items():
            if domain and param.domain != domain:
                continue
            params[pid] = {
                "name": param.name,
                "domain": param.domain.value,
                "value": param.current_value,
                "ideal_range": param.ideal_range,
                "locked": param.locked,
                "history_length": len(param.history),
            }
        return params

    def get_stats(self) -> Dict[str, Any]:
        domain_imbalances = {}
        for domain in TuningDomain:
            domain_params = [p for p in self._parameters.values() if p.domain == domain]
            in_ideal = sum(
                1 for p in domain_params
                if p.ideal_range[0] <= p.current_value <= p.ideal_range[1]
            )
            domain_imbalances[domain.value] = {
                "total": len(domain_params),
                "in_ideal_range": in_ideal,
                "health": round(in_ideal / max(1, len(domain_params)), 3),
            }
        return {
            "total_parameters": len(self._parameters),
            "total_tunings": self._tuning_count,
            "sensitivity": self._sensitivity,
            "metrics_collected": len(self._metrics),
            "domain_health": domain_imbalances,
        }


def get_game_balancer() -> GameBalanceTuner:
    return GameBalanceTuner.get_instance()