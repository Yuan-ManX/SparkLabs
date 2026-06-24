"""
SparkLabs Agent - Utility Calculation Engine

A multi-criteria utility calculation engine for AI agent decision-making.
Provides configurable utility curves, aggregation strategies, and
context-dependent modifiers. The engine supports rational choice theory
with bounded rationality adaptations for game AI environments.

Architecture:
  UtilityEngine (Singleton)
    |-- UtilityFunction (multi-criteria evaluation)
    |-- UtilityCurve (linear, exponential, logarithmic, sigmoid)
    |-- UtilityAggregator (weighted and non-linear combination)
    |-- ContextualUtilityModifier (context-dependent adjustments)
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class CurveType(Enum):
    """Types of utility mapping curves."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    SIGMOID = "sigmoid"
    STEP = "step"
    QUADRATIC = "quadratic"
    INVERSE = "inverse"


class AggregationMethod(Enum):
    """Methods for combining multiple utility values."""
    WEIGHTED_SUM = "weighted_sum"
    WEIGHTED_PRODUCT = "weighted_product"
    MINIMAX = "minimax"
    MAXIMIN = "maximin"
    HARMONIC_MEAN = "harmonic_mean"
    GEOMETRIC_MEAN = "geometric_mean"
    LEXICOGRAPHIC = "lexicographic"


class ContextDomain(Enum):
    """Domains for contextual utility modification."""
    RESOURCE_ABUNDANCE = "resource_abundance"
    TIME_PRESSURE = "time_pressure"
    RISK_TOLERANCE = "risk_tolerance"
    SOCIAL_CONTEXT = "social_context"
    EXPLORATION_NEED = "exploration_need"
    SAFETY_REQUIREMENT = "safety_requirement"
    NOVELTY_SEEKING = "novelty_seeking"


@dataclass
class UtilityConfig:
    """Configuration for a utility curve."""
    curve_type: CurveType = CurveType.LINEAR
    min_value: float = 0.0
    max_value: float = 1.0
    midpoint: float = 0.5
    steepness: float = 1.0
    offset: float = 0.0
    invert: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "curve_type": self.curve_type.value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "midpoint": self.midpoint,
            "steepness": self.steepness,
            "offset": self.offset,
            "invert": self.invert,
        }


class UtilityCurve:
    """
    Maps raw input values to utility scores using configurable curves.
    Supports linear, exponential, logarithmic, sigmoid, step, quadratic,
    and inverse mappings.
    """

    def __init__(self, config: Optional[UtilityConfig] = None) -> None:
        self._config = config or UtilityConfig()

    def evaluate(self, value: float) -> float:
        """Map a raw input value to a utility score."""
        cfg = self._config
        normalized = (value - cfg.min_value) / max(cfg.max_value - cfg.min_value, 0.001)
        normalized = max(0.0, min(1.0, normalized))

        if cfg.curve_type == CurveType.LINEAR:
            result = normalized
        elif cfg.curve_type == CurveType.EXPONENTIAL:
            result = (math.exp(cfg.steepness * normalized) - 1) / (math.exp(cfg.steepness) - 1) if cfg.steepness > 0 else normalized
        elif cfg.curve_type == CurveType.LOGARITHMIC:
            result = math.log(1 + cfg.steepness * normalized) / math.log(1 + cfg.steepness) if cfg.steepness > 0 else normalized
        elif cfg.curve_type == CurveType.SIGMOID:
            x = cfg.steepness * (normalized - cfg.midpoint)
            try:
                result = 1.0 / (1.0 + math.exp(-x))
            except OverflowError:
                result = 1.0 if x > 0 else 0.0
        elif cfg.curve_type == CurveType.STEP:
            result = 1.0 if normalized >= cfg.midpoint else 0.0
        elif cfg.curve_type == CurveType.QUADRATIC:
            result = normalized ** 2
        elif cfg.curve_type == CurveType.INVERSE:
            result = 1.0 - normalized
        else:
            result = normalized

        result = result * (1.0 + cfg.offset)
        if cfg.invert:
            result = 1.0 - result
        return max(0.0, min(1.0, result))

    def to_dict(self) -> Dict[str, Any]:
        return self._config.to_dict()

    @classmethod
    def linear(cls, min_val: float = 0.0, max_val: float = 1.0) -> "UtilityCurve":
        return cls(UtilityConfig(curve_type=CurveType.LINEAR, min_value=min_val, max_value=max_val))

    @classmethod
    def exponential(cls, steepness: float = 2.0, min_val: float = 0.0,
                    max_val: float = 1.0) -> "UtilityCurve":
        return cls(UtilityConfig(curve_type=CurveType.EXPONENTIAL, steepness=steepness,
                                  min_value=min_val, max_value=max_val))

    @classmethod
    def logarithmic(cls, steepness: float = 2.0, min_val: float = 0.0,
                    max_val: float = 1.0) -> "UtilityCurve":
        return cls(UtilityConfig(curve_type=CurveType.LOGARITHMIC, steepness=steepness,
                                  min_value=min_val, max_value=max_val))

    @classmethod
    def sigmoid(cls, midpoint: float = 0.5, steepness: float = 10.0) -> "UtilityCurve":
        return cls(UtilityConfig(curve_type=CurveType.SIGMOID, midpoint=midpoint,
                                  steepness=steepness))


@dataclass
class UtilityCriterion:
    """A single criterion in a multi-criteria utility function."""
    criterion_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    weight: float = 1.0
    curve: UtilityCurve = field(default_factory=UtilityCurve.linear)
    min_acceptable: float = 0.0
    threshold: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "name": self.name,
            "weight": self.weight,
            "curve": self.curve.to_dict(),
            "min_acceptable": self.min_acceptable,
            "threshold": self.threshold,
        }


class UtilityFunction:
    """
    Multi-criteria utility evaluation function.
    Aggregates utility scores from multiple weighted criteria
    using configurable aggregation methods.
    """

    def __init__(self, name: str = "") -> None:
        self._name = name
        self._criteria: Dict[str, UtilityCriterion] = {}
        self._aggregation: AggregationMethod = AggregationMethod.WEIGHTED_SUM
        self._lock = threading.RLock()

    def add_criterion(self, name: str, weight: float = 1.0,
                      curve: Optional[UtilityCurve] = None,
                      min_acceptable: float = 0.0,
                      threshold: Optional[float] = None) -> UtilityCriterion:
        """Add a criterion to the function."""
        with self._lock:
            criterion = UtilityCriterion(
                name=name,
                weight=weight,
                curve=curve or UtilityCurve.linear(),
                min_acceptable=min_acceptable,
                threshold=threshold,
            )
            self._criteria[criterion.criterion_id] = criterion
            return criterion

    def remove_criterion(self, criterion_id: str) -> bool:
        with self._lock:
            if criterion_id in self._criteria:
                del self._criteria[criterion_id]
                return True
            return False

    def set_aggregation(self, method: AggregationMethod) -> None:
        with self._lock:
            self._aggregation = method

    def evaluate(self, values: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
        """
        Evaluate utility given a dictionary of criterion_name -> raw_value.
        Returns (total_utility, details).
        """
        with self._lock:
            scores: Dict[str, float] = {}
            details: Dict[str, Any] = {}
            total_weight = 0.0

            for crit in self._criteria.values():
                raw = values.get(crit.name, 0.0)
                score = crit.curve.evaluate(raw)
                if crit.threshold is not None and score < crit.threshold:
                    score = 0.0
                scores[crit.name] = score
                details[crit.name] = {
                    "raw_value": raw,
                    "utility_score": round(score, 4),
                    "weight": crit.weight,
                }
                total_weight += crit.weight

            if total_weight <= 0:
                return 0.0, {"scores": details, "aggregation": self._aggregation.value}

            if self._aggregation == AggregationMethod.WEIGHTED_SUM:
                total = sum(crit.weight * scores.get(crit.name, 0.0)
                            for crit in self._criteria.values()) / total_weight
            elif self._aggregation == AggregationMethod.WEIGHTED_PRODUCT:
                product = 1.0
                for crit in self._criteria.values():
                    product *= scores.get(crit.name, 0.0) ** (crit.weight / total_weight)
                total = product
            elif self._aggregation == AggregationMethod.MINIMAX:
                total = max(scores.values()) if scores else 0.0
            elif self._aggregation == AggregationMethod.MAXIMIN:
                total = min(scores.values()) if scores else 0.0
            elif self._aggregation == AggregationMethod.HARMONIC_MEAN:
                valid = [s for s in scores.values() if s > 0]
                total = len(valid) / sum(1.0 / s for s in valid) if valid else 0.0
            elif self._aggregation == AggregationMethod.GEOMETRIC_MEAN:
                valid = [s for s in scores.values() if s > 0]
                if valid:
                    product = math.prod(valid)
                    total = product ** (1.0 / len(valid))
                else:
                    total = 0.0
            elif self._aggregation == AggregationMethod.LEXICOGRAPHIC:
                sorted_crits = sorted(self._criteria.values(), key=lambda c: c.weight, reverse=True)
                total = scores.get(sorted_crits[0].name, 0.0) if sorted_crits else 0.0
            else:
                total = 0.0

            total = max(0.0, min(1.0, total))
            details["total_utility"] = round(total, 4)
            details["aggregation"] = self._aggregation.value
            return total, details

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "name": self._name,
                "criteria": [c.to_dict() for c in self._criteria.values()],
                "aggregation": self._aggregation.value,
                "criterion_count": len(self._criteria),
            }


class UtilityAggregator:
    """
    Aggregates utilities from multiple functions into a composite score.
    Supports hierarchical aggregation with configurable weighting.
    """

    def __init__(self) -> None:
        self._functions: Dict[str, Tuple[UtilityFunction, float]] = {}
        self._lock = threading.RLock()

    def register(self, name: str, function: UtilityFunction, weight: float = 1.0) -> None:
        with self._lock:
            self._functions[name] = (function, weight)

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name in self._functions:
                del self._functions[name]
                return True
            return False

    def aggregate(self, all_values: Dict[str, Dict[str, float]]) -> Tuple[float, Dict[str, Any]]:
        """
        Aggregate utilities from all registered functions.
        all_values: {function_name: {criterion_name: raw_value, ...}, ...}
        """
        with self._lock:
            results: Dict[str, Any] = {}
            total_weight = 0.0
            weighted_sum = 0.0

            for name, (func, weight) in self._functions.items():
                values = all_values.get(name, {})
                score, details = func.evaluate(values)
                results[name] = {"score": round(score, 4), "weight": weight, "details": details}
                weighted_sum += score * weight
                total_weight += weight

            if total_weight <= 0:
                return 0.0, {"functions": results}

            composite = weighted_sum / total_weight
            results["composite_utility"] = round(composite, 4)
            return composite, results

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "function_count": len(self._functions),
                "functions": [{"name": n, "weight": w, "config": f.to_dict()}
                              for n, (f, w) in self._functions.items()],
            }


class ContextualUtilityModifier:
    """
    Modifies utility scores based on contextual factors.
    Applies domain-specific adjustments to reflect changing
    environmental conditions and agent states.
    """

    def __init__(self) -> None:
        self._modifiers: Dict[ContextDomain, Tuple[float, Callable[[float], float]]] = {}
        self._lock = threading.RLock()

    def set_modifier(self, domain: ContextDomain, weight: float,
                     transform: Callable[[float], float]) -> None:
        """Register a contextual modifier."""
        with self._lock:
            self._modifiers[domain] = (weight, transform)

    def remove_modifier(self, domain: ContextDomain) -> bool:
        with self._lock:
            if domain in self._modifiers:
                del self._modifiers[domain]
                return True
            return False

    def apply(self, base_utility: float, context: Dict[ContextDomain, float]) -> float:
        """Apply contextual modifiers to a base utility score."""
        with self._lock:
            modified = base_utility
            total_weight = 0.0

            for domain, (weight, transform) in self._modifiers.items():
                context_value = context.get(domain, 0.5)
                adjustment = transform(context_value)
                modified += weight * adjustment * (1.0 - abs(base_utility - 0.5) * 2.0)
                total_weight += abs(weight)

            return max(0.0, min(1.0, modified))

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "modifier_count": len(self._modifiers),
                "domains": [d.value for d in self._modifiers.keys()],
            }


class UtilityEngine:
    """
    Multi-criteria utility calculation engine for AI agent decision-making.

    Provides configurable utility curves, aggregation strategies, and
    context-dependent modifiers for rational choice modeling.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._aggregator = UtilityAggregator()
        self._context_modifier = ContextualUtilityModifier()
        self._default_function = UtilityFunction("default")

    @classmethod
    def get_instance(cls) -> "UtilityEngine":
        return cls()

    @property
    def aggregator(self) -> UtilityAggregator:
        return self._aggregator

    @property
    def context_modifier(self) -> ContextualUtilityModifier:
        return self._context_modifier

    def create_function(self, name: str) -> UtilityFunction:
        func = UtilityFunction(name=name)
        self._aggregator.register(name, func)
        return func

    def evaluate_simple(self, values: Dict[str, float]) -> float:
        """Quick single-function utility evaluation."""
        score, _ = self._default_function.evaluate(values)
        return score

    def evaluate_with_context(
        self,
        values: Dict[str, float],
        context: Optional[Dict[ContextDomain, float]] = None,
    ) -> float:
        """Evaluate utility with contextual modifiers."""
        score, _ = self._default_function.evaluate(values)
        if context:
            score = self._context_modifier.apply(score, context)
        return score

    def get_stats(self) -> Dict[str, Any]:
        return {
            "aggregator": self._aggregator.to_dict(),
            "context_modifier": self._context_modifier.to_dict(),
        }


_global_utility_engine: Optional[UtilityEngine] = None


def get_utility_engine() -> UtilityEngine:
    global _global_utility_engine
    if _global_utility_engine is None:
        _global_utility_engine = UtilityEngine()
    return _global_utility_engine