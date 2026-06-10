"""
SparkLabs Agent - Predictive Intelligence System

An advanced forecasting and counterfactual reasoning engine that enables
agents to anticipate future game states, simulate alternative scenarios,
and make proactive decisions. This system powers the game engine's ability
to predict player behavior, forecast game economy trends, anticipate
narrative branching outcomes, and optimize resource allocation.

Architecture:
  AgentPredictiveIntelligence (Singleton)
    |-- ForecastModel (time-series prediction pipeline)
    |-- CounterfactualEngine (what-if scenario simulation)
    |-- TrendAnalyzer (pattern detection and extrapolation)
    |-- RiskPredictor (threat and opportunity forecasting)
    |-- ScenarioSimulator (branching outcome simulation)
    |-- PredictionRecord (outcome tracking and calibration)

Core Capabilities:
  - Time-series forecasting for game metrics and player behavior
  - Counterfactual reasoning for "what-if" scenario analysis
  - Pattern-based trend detection and extrapolation
  - Proactive risk and opportunity identification
  - Multi-path scenario simulation with probability distributions
  - Feedback-driven prediction accuracy improvement
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class ForecastHorizon(Enum):
    """Prediction time horizons for forecasting."""
    IMMEDIATE = "immediate"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"
    STRATEGIC = "strategic"


class ForecastDomain(Enum):
    """Domains suitable for predictive intelligence."""
    PLAYER_BEHAVIOR = "player_behavior"
    GAME_ECONOMY = "game_economy"
    NARRATIVE_OUTCOME = "narrative_outcome"
    RESOURCE_DEMAND = "resource_demand"
    DIFFICULTY_CURVE = "difficulty_curve"
    ENGAGEMENT_METRICS = "engagement_metrics"
    BALANCE_STABILITY = "balance_stability"
    CONTENT_PERFORMANCE = "content_performance"
    SOCIAL_DYNAMICS = "social_dynamics"
    TECHNICAL_PERFORMANCE = "technical_performance"


class TrendDirection(Enum):
    """Directional classification of detected trends."""
    STRONG_UPWARD = "strong_upward"
    MODERATE_UPWARD = "moderate_upward"
    STABLE = "stable"
    MODERATE_DOWNWARD = "moderate_downward"
    STRONG_DOWNWARD = "strong_downward"
    VOLATILE = "volatile"
    CYCLICAL = "cyclical"


class ScenarioOutcome(Enum):
    """Possible outcomes from scenario simulation."""
    FAVORABLE = "favorable"
    NEUTRAL = "neutral"
    UNFAVORABLE = "unfavorable"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class CounterfactualType(Enum):
    """Types of counterfactual reasoning queries."""
    ALTERNATIVE_ACTION = "alternative_action"
    PARAMETER_CHANGE = "parameter_change"
    TIMING_VARIATION = "timing_variation"
    AGENT_SUBSTITUTION = "agent_substitution"
    ENVIRONMENTAL_SHIFT = "environmental_shift"
    RULE_MODIFICATION = "rule_modification"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TimeSeriesPoint:
    """A single data point in a time series.

    Attributes:
        timestamp: When this data point was recorded.
        value: The measured value.
        confidence: Confidence weight for this data point.
        tags: Categorical tags for filtering.
        metadata: Additional contextual data.
    """
    timestamp: float = field(default_factory=_time_module.time)
    value: float = 0.0
    confidence: float = 1.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendAnalysis:
    """Comprehensive trend analysis result.

    Attributes:
        id: Unique analysis identifier.
        domain: The forecast domain analyzed.
        direction: Detected trend direction.
        strength: Trend strength coefficient (0.0-1.0).
        slope: Linear regression slope.
        intercept: Linear regression intercept.
        r_squared: Coefficient of determination.
        volatility: Standard deviation of residuals.
        turning_points: Detected inflection points.
        seasonality: Detected seasonal pattern length (0 = none).
        forecast_confidence: Overall confidence in the analysis.
        summary: Human-readable trend summary.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = ""
    direction: str = TrendDirection.STABLE.value
    strength: float = 0.0
    slope: float = 0.0
    intercept: float = 0.0
    r_squared: float = 0.0
    volatility: float = 0.0
    turning_points: List[Tuple[float, float]] = field(default_factory=list)
    seasonality: int = 0
    forecast_confidence: float = 0.5
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "direction": self.direction,
            "strength": round(self.strength, 4),
            "slope": round(self.slope, 6),
            "intercept": round(self.intercept, 4),
            "r_squared": round(self.r_squared, 4),
            "volatility": round(self.volatility, 4),
            "turning_points": [
                {"time": tp[0], "value": round(tp[1], 4)}
                for tp in self.turning_points
            ],
            "seasonality": self.seasonality,
            "forecast_confidence": round(self.forecast_confidence, 4),
            "summary": self.summary,
        }


@dataclass
class ForecastResult:
    """A time-series forecast with confidence intervals.

    Attributes:
        id: Unique forecast identifier.
        domain: The forecast domain.
        horizon: Prediction time horizon.
        predicted_values: List of (timestamp, value, lower_bound, upper_bound).
        confidence: Overall forecast confidence.
        trend: Underlying trend used for the forecast.
        generated_at: When this forecast was generated.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = ""
    horizon: str = ForecastHorizon.SHORT_TERM.value
    predicted_values: List[Tuple[float, float, float, float]] = field(default_factory=list)
    confidence: float = 0.5
    trend: Optional[TrendAnalysis] = None
    generated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "horizon": self.horizon,
            "predicted_values": [
                {
                    "timestamp": pv[0],
                    "value": round(pv[1], 4),
                    "lower_bound": round(pv[2], 4),
                    "upper_bound": round(pv[3], 4),
                }
                for pv in self.predicted_values
            ],
            "confidence": round(self.confidence, 4),
            "trend": self.trend.to_dict() if self.trend else None,
            "generated_at": self.generated_at,
        }

    @property
    def final_prediction(self) -> Optional[float]:
        """The final predicted value in the forecast horizon."""
        if not self.predicted_values:
            return None
        return self.predicted_values[-1][1]

    @property
    def prediction_range(self) -> Optional[Tuple[float, float]]:
        """The confidence interval of the final prediction."""
        if not self.predicted_values:
            return None
        return (self.predicted_values[-1][2], self.predicted_values[-1][3])


@dataclass
class CounterfactualScenario:
    """A counterfactual (what-if) scenario definition and result.

    Attributes:
        id: Unique scenario identifier.
        query: Natural language description of the counterfactual.
        base_state: Description of the original state.
        modification: The specific parameter or action changed.
        predicted_outcome: The expected outcome of the modification.
        outcome_probability: Probability distribution across outcomes.
        confidence: Confidence in the counterfactual prediction.
        impacted_domains: Which domains are affected by this scenario.
        cascading_effects: Predicted secondary/tertiary effects.
        recommendation: Whether the modification is recommended.
        timestamp: When this scenario was analyzed.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    query: str = ""
    base_state: str = ""
    modification: str = ""
    predicted_outcome: str = ""
    outcome_probability: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.5
    impacted_domains: List[str] = field(default_factory=list)
    cascading_effects: List[str] = field(default_factory=list)
    recommendation: str = ""
    timestamp: float = field(default_factory=_time_module.time)

    @property
    def most_likely_outcome(self) -> str:
        if not self.outcome_probability:
            return ScenarioOutcome.UNKNOWN.value
        return max(self.outcome_probability, key=self.outcome_probability.get)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "base_state": self.base_state,
            "modification": self.modification,
            "predicted_outcome": self.predicted_outcome,
            "outcome_probability": {
                k: round(v, 4) for k, v in self.outcome_probability.items()
            },
            "most_likely_outcome": self.most_likely_outcome,
            "confidence": round(self.confidence, 4),
            "impacted_domains": list(self.impacted_domains),
            "cascading_effects": list(self.cascading_effects),
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
        }


@dataclass
class RiskAssessment:
    """Predictive risk and opportunity assessment.

    Attributes:
        id: Unique assessment identifier.
        domain: The assessed domain.
        risk_level: Overall risk level (0.0-1.0).
        opportunity_level: Overall opportunity level (0.0-1.0).
        identified_risks: List of specific risks with probabilities.
        identified_opportunities: List of specific opportunities.
        mitigation_strategies: Recommended risk mitigation actions.
        time_to_impact: Estimated time until risks/opportunities materialize.
        confidence: Confidence in this assessment.
        timestamp: When this assessment was generated.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = ""
    risk_level: float = 0.0
    opportunity_level: float = 0.0
    identified_risks: List[Dict[str, Any]] = field(default_factory=list)
    identified_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    mitigation_strategies: List[str] = field(default_factory=list)
    time_to_impact: float = 0.0
    confidence: float = 0.5
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "risk_level": round(self.risk_level, 4),
            "opportunity_level": round(self.opportunity_level, 4),
            "identified_risks": self.identified_risks,
            "identified_opportunities": self.identified_opportunities,
            "mitigation_strategies": list(self.mitigation_strategies),
            "time_to_impact": round(self.time_to_impact, 2),
            "confidence": round(self.confidence, 4),
            "timestamp": self.timestamp,
        }


@dataclass
class ScenarioBranch:
    """A single branch in a multi-path scenario simulation.

    Attributes:
        id: Unique branch identifier.
        path_label: Human-readable label for this branch.
        conditions: The conditions that lead to this branch.
        outcome: Expected outcome of this branch.
        probability: Probability of this branch occurring.
        utility_score: Expected utility/value of this branch.
        downstream_effects: Effects that cascade from this branch.
        is_preferred: Whether this is the recommended path.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    path_label: str = ""
    conditions: List[str] = field(default_factory=list)
    outcome: str = ""
    probability: float = 0.0
    utility_score: float = 0.0
    downstream_effects: List[str] = field(default_factory=list)
    is_preferred: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "path_label": self.path_label,
            "conditions": list(self.conditions),
            "outcome": self.outcome,
            "probability": round(self.probability, 4),
            "utility_score": round(self.utility_score, 4),
            "downstream_effects": list(self.downstream_effects),
            "is_preferred": self.is_preferred,
        }


# ---------------------------------------------------------------------------
# Agent Predictive Intelligence (Singleton)
# ---------------------------------------------------------------------------

class AgentPredictiveIntelligence:
    """
    Advanced forecasting and counterfactual reasoning engine for SparkLabs.

    Enables agents to anticipate future game states, simulate alternative
    scenarios, and make proactive decisions. Powers player behavior prediction,
    economy trend forecasting, narrative branching analysis, and resource
    optimization across the AI-native game engine.

    Combines time-series forecasting, pattern-based trend detection,
    Monte Carlo-style scenario simulation, and counterfactual reasoning
    into a unified predictive intelligence pipeline.
    """

    _instance: Optional["AgentPredictiveIntelligence"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "AgentPredictiveIntelligence":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Time series storage per domain
        self._time_series: Dict[str, deque[TimeSeriesPoint]] = defaultdict(
            lambda: deque(maxlen=2000)
        )

        # Forecast registry
        self._forecasts: Dict[str, ForecastResult] = {}
        self._forecast_history: deque[str] = deque(maxlen=500)

        # Trend analysis cache
        self._trend_cache: Dict[str, TrendAnalysis] = {}
        self._last_trend_update: Dict[str, float] = {}

        # Counterfactual scenarios
        self._scenarios: Dict[str, CounterfactualScenario] = {}
        self._scenario_history: deque[str] = deque(maxlen=200)

        # Risk assessments
        self._risk_assessments: Dict[str, RiskAssessment] = {}

        # Scenario simulations
        self._simulations: Dict[str, List[ScenarioBranch]] = {}

        # Prediction accuracy tracking
        self._prediction_accuracy: Dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=100)
        )

        # Default horizon steps
        self._horizon_steps: Dict[ForecastHorizon, int] = {
            ForecastHorizon.IMMEDIATE: 3,
            ForecastHorizon.SHORT_TERM: 10,
            ForecastHorizon.MEDIUM_TERM: 30,
            ForecastHorizon.LONG_TERM: 100,
            ForecastHorizon.STRATEGIC: 300,
        }

    # ------------------------------------------------------------------
    # Time Series Management
    # ------------------------------------------------------------------

    def record_datapoint(
        self,
        domain: str,
        value: float,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TimeSeriesPoint:
        """
        Record a data point into a domain-specific time series.

        Args:
            domain: The forecast domain (see ForecastDomain enum values).
            value: The measured value to record.
            confidence: Weight/confidence for this data point.
            tags: Optional categorical tags.
            metadata: Optional contextual data.

        Returns:
            The recorded TimeSeriesPoint.
        """
        point = TimeSeriesPoint(
            value=value,
            confidence=confidence,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._time_series[domain].append(point)

        # Invalidate trend cache for this domain
        self._trend_cache.pop(domain, None)

        return point

    def get_time_series(
        self, domain: str, limit: Optional[int] = None
    ) -> List[TimeSeriesPoint]:
        """Retrieve recorded time series data for a domain."""
        series = list(self._time_series.get(domain, []))
        if limit:
            return series[-limit:]
        return series

    # ------------------------------------------------------------------
    # Trend Analysis
    # ------------------------------------------------------------------

    def analyze_trend(self, domain: str, window: int = 50) -> TrendAnalysis:
        """
        Perform comprehensive trend analysis on a domain's time series.

        Uses linear regression, volatility calculation, and turning point
        detection to classify the trend and quantify its characteristics.

        Args:
            domain: The forecast domain to analyze.
            window: Number of recent data points to analyze.

        Returns:
            TrendAnalysis with direction, strength, and statistical metrics.
        """
        series = list(self._time_series.get(domain, []))
        if len(series) < 3:
            return TrendAnalysis(
                domain=domain,
                direction=TrendDirection.STABLE.value,
                summary=f"Insufficient data for trend analysis (need at least 3 points, have {len(series)})",
            )

        # Use the most recent window of points
        points = series[-window:]
        n = len(points)
        values = [p.value for p in points]
        times = [float(i) for i in range(n)]

        # Linear regression
        mean_x = sum(times) / n
        mean_y = sum(values) / n

        numerator = sum((times[i] - mean_x) * (values[i] - mean_y) for i in range(n))
        denominator = sum((times[i] - mean_x) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator

        intercept = mean_y - slope * mean_x

        # R-squared calculation
        ss_res = sum((values[i] - (intercept + slope * times[i])) ** 2 for i in range(n))
        ss_tot = sum((values[i] - mean_y) ** 2 for i in range(n))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Volatility (standard deviation of residuals)
        residuals = [values[i] - (intercept + slope * times[i]) for i in range(n)]
        volatility = math.sqrt(sum(r**2 for r in residuals) / max(1, n - 2))

        # Normalize slope by mean value for comparability
        avg_value = sum(values) / n
        normalized_slope = slope / max(abs(avg_value), 0.001)

        # Classify direction
        direction = self._classify_trend_direction(normalized_slope, volatility, values)

        # Detect turning points (local maxima/minima)
        turning_points = self._detect_turning_points(values, times, points)

        # Detect seasonality
        seasonality = self._detect_seasonality(values)

        # Compute trend strength
        strength = min(1.0, abs(normalized_slope) * 0.5 + r_squared * 0.5)

        # Confidence in this analysis
        confidence = min(1.0, r_squared * 0.6 + (n / 100.0) * 0.4)

        summary = self._generate_trend_summary(
            direction, strength, slope, r_squared, volatility, domain
        )

        analysis = TrendAnalysis(
            domain=domain,
            direction=direction.value,
            strength=strength,
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            volatility=volatility,
            turning_points=turning_points,
            seasonality=seasonality,
            forecast_confidence=confidence,
            summary=summary,
        )

        self._trend_cache[domain] = analysis
        self._last_trend_update[domain] = _time_module.time()

        return analysis

    def _classify_trend_direction(
        self, normalized_slope: float, volatility: float, values: List[float]
    ) -> TrendDirection:
        """Classify the trend direction from slope, volatility, and values."""
        if volatility > abs(normalized_slope) * 2:
            # Check for cyclical pattern
            if self._detect_seasonality(values) > 0:
                return TrendDirection.CYCLICAL
            return TrendDirection.VOLATILE

        if normalized_slope > 0.15:
            return TrendDirection.STRONG_UPWARD
        if normalized_slope > 0.03:
            return TrendDirection.MODERATE_UPWARD
        if normalized_slope < -0.15:
            return TrendDirection.STRONG_DOWNWARD
        if normalized_slope < -0.03:
            return TrendDirection.MODERATE_DOWNWARD
        return TrendDirection.STABLE

    def _detect_turning_points(
        self, values: List[float], times: List[float], points: List[TimeSeriesPoint]
    ) -> List[Tuple[float, float]]:
        """Detect local maxima and minima (turning points) in the series."""
        if len(values) < 5:
            return []

        turning_points = []
        for i in range(2, len(values) - 2):
            # Local maximum
            if values[i] > values[i - 1] and values[i] > values[i - 2] and \
               values[i] > values[i + 1] and values[i] > values[i + 2]:
                turning_points.append((points[i].timestamp, values[i]))
            # Local minimum
            elif values[i] < values[i - 1] and values[i] < values[i - 2] and \
                 values[i] < values[i + 1] and values[i] < values[i + 2]:
                turning_points.append((points[i].timestamp, values[i]))

        return turning_points

    def _detect_seasonality(self, values: List[float]) -> int:
        """Detect seasonal patterns in the time series using autocorrelation."""
        if len(values) < 20:
            return 0

        # Simple autocorrelation for lag detection
        n = len(values)
        max_lag = min(n // 3, 50)
        best_lag = 0
        best_corr = 0.3  # Minimum correlation threshold

        for lag in range(2, max_lag):
            series_a = values[:-lag]
            series_b = values[lag:]

            if len(series_a) < 5:
                continue

            mean_a = sum(series_a) / len(series_a)
            mean_b = sum(series_b) / len(series_b)

            cov = sum((series_a[i] - mean_a) * (series_b[i] - mean_b) for i in range(len(series_a)))
            std_a = math.sqrt(sum((x - mean_a)**2 for x in series_a))
            std_b = math.sqrt(sum((x - mean_b)**2 for x in series_b))

            if std_a == 0 or std_b == 0:
                continue

            corr = cov / (std_a * std_b)
            if corr > best_corr:
                best_corr = corr
                best_lag = lag

        return best_lag

    def _generate_trend_summary(
        self, direction: TrendDirection, strength: float,
        slope: float, r_squared: float, volatility: float, domain: str,
    ) -> str:
        """Generate a human-readable trend summary."""
        direction_text = direction.value.replace("_", " ").title()
        quality = "high confidence" if r_squared > 0.7 else "moderate confidence" if r_squared > 0.4 else "low confidence"

        return (
            f"{direction_text} trend detected in {domain} with {quality} "
            f"(R²={r_squared:.3f}, strength={strength:.2f}, "
            f"volatility={volatility:.3f})"
        )

    # ------------------------------------------------------------------
    # Forecasting
    # ------------------------------------------------------------------

    def forecast(
        self,
        domain: str,
        horizon: ForecastHorizon = ForecastHorizon.SHORT_TERM,
        window: int = 50,
    ) -> ForecastResult:
        """
        Generate a time-series forecast for a domain.

        Uses linear trend projection with confidence intervals based on
        historical volatility, combined with seasonal adjustments when
        detected.

        Args:
            domain: The forecast domain.
            horizon: How far into the future to predict.
            window: Number of historical data points to use.

        Returns:
            ForecastResult with predicted values and confidence intervals.
        """
        # Get or compute trend
        trend = self._trend_cache.get(domain)
        if not trend or _time_module.time() - self._last_trend_update.get(domain, 0) > 60:
            trend = self.analyze_trend(domain, window)

        series = list(self._time_series.get(domain, []))
        if len(series) < 3:
            return ForecastResult(
                domain=domain,
                horizon=horizon.value,
                predicted_values=[],
                confidence=0.0,
                trend=trend,
            )

        steps = self._horizon_steps.get(horizon, 10)
        last_time = series[-1].timestamp
        last_value = series[-1].value

        # Generate predictions with confidence intervals
        predicted_values: List[Tuple[float, float, float, float]] = []
        volatility = trend.volatility
        seasonality = trend.seasonality

        for i in range(1, steps + 1):
            future_time = last_time + i * (self._compute_avg_interval(series))

            # Trend-based prediction
            predicted = last_value + trend.slope * i

            # Seasonal adjustment
            if seasonality > 0 and len(series) >= seasonality:
                seasonal_offset = self._compute_seasonal_offset(series, i, seasonality)
                predicted += seasonal_offset * 0.3

            # Confidence interval (widens with forecast distance)
            uncertainty_multiplier = 1.0 + (i / steps) * 2.0
            margin = volatility * 1.96 * uncertainty_multiplier
            lower = predicted - margin
            upper = predicted + margin

            predicted_values.append((future_time, predicted, lower, upper))

        confidence = max(0.1, trend.forecast_confidence * (1.0 - 0.02 * steps))

        result = ForecastResult(
            domain=domain,
            horizon=horizon.value,
            predicted_values=predicted_values,
            confidence=confidence,
            trend=trend,
        )

        self._forecasts[result.id] = result
        self._forecast_history.append(result.id)

        return result

    def _compute_avg_interval(self, series: List[TimeSeriesPoint]) -> float:
        """Compute the average time interval between data points."""
        if len(series) < 2:
            return 1.0
        intervals = [
            series[i].timestamp - series[i - 1].timestamp
            for i in range(1, min(len(series), 20))
        ]
        return sum(intervals) / len(intervals) if intervals else 1.0

    def _compute_seasonal_offset(
        self, series: List[TimeSeriesPoint], step: int, seasonality: int
    ) -> float:
        """Compute seasonal adjustment for a forecast step."""
        if len(series) < seasonality:
            return 0.0
        idx = step % seasonality
        seasonal_values = [
            series[j].value
            for j in range(idx, len(series), seasonality)
            if j < len(series)
        ]
        if not seasonal_values:
            return 0.0
        overall_mean = sum(p.value for p in series[-seasonality:]) / seasonality if series else 0.0
        seasonal_mean = sum(seasonal_values) / len(seasonal_values)
        return seasonal_mean - overall_mean

    # ------------------------------------------------------------------
    # Counterfactual Reasoning
    # ------------------------------------------------------------------

    def simulate_counterfactual(
        self,
        query: str,
        base_state: str,
        modification: str,
        domain: str = "",
        impacted_domains: Optional[List[str]] = None,
    ) -> CounterfactualScenario:
        """
        Simulate a counterfactual (what-if) scenario.

        Uses historical patterns, trend data, and causal reasoning to
        predict what would happen under an alternative condition.

        Args:
            query: Natural language description of the counterfactual.
            base_state: Description of the original/actual state.
            modification: The specific change being evaluated.
            domain: Primary domain of the counterfactual.
            impacted_domains: Additional domains that may be affected.

        Returns:
            CounterfactualScenario with predicted outcomes and probabilities.
        """
        all_impacted = [domain] if domain else []
        if impacted_domains:
            all_impacted.extend(impacted_domains)

        # Compute outcome probabilities based on domain trends
        outcome_probs: Dict[str, float] = {}
        cascading_effects: List[str] = []

        for d in set(all_impacted):
            if not d:
                continue
            trend = self._trend_cache.get(d)
            if not trend:
                trend = self.analyze_trend(d)

            # Adjust probabilities based on trend direction
            if trend.direction in (TrendDirection.STRONG_UPWARD.value, TrendDirection.MODERATE_UPWARD.value):
                outcome_probs[ScenarioOutcome.FAVORABLE.value] = min(
                    1.0, outcome_probs.get(ScenarioOutcome.FAVORABLE.value, 0.0) + 0.3
                )
                cascading_effects.append(f"Positive momentum in {d} may amplify favorable outcomes")
            elif trend.direction in (TrendDirection.STRONG_DOWNWARD.value, TrendDirection.MODERATE_DOWNWARD.value):
                outcome_probs[ScenarioOutcome.UNFAVORABLE.value] = min(
                    1.0, outcome_probs.get(ScenarioOutcome.UNFAVORABLE.value, 0.0) + 0.3
                )
                cascading_effects.append(f"Negative trend in {d} may amplify unfavorable outcomes")
            else:
                outcome_probs[ScenarioOutcome.NEUTRAL.value] = min(
                    1.0, outcome_probs.get(ScenarioOutcome.NEUTRAL.value, 0.0) + 0.25
                )

            # Volatility-based risk
            if trend.volatility > 0.3:
                cascading_effects.append(f"High volatility in {d} introduces outcome uncertainty")

        # Normalize probabilities
        total = sum(outcome_probs.values())
        if total > 0:
            outcome_probs = {k: v / total for k, v in outcome_probs.items()}

        # Generate predicted outcome description
        most_likely = max(outcome_probs, key=outcome_probs.get) if outcome_probs else ScenarioOutcome.UNKNOWN.value
        predicted_outcome = f"Under the modification '{modification}', the most likely outcome is {most_likely}"

        # Determine recommendation
        if outcome_probs.get(ScenarioOutcome.FAVORABLE.value, 0) > 0.5:
            recommendation = "Proceed with the modification — favorable outcome probability is high"
        elif outcome_probs.get(ScenarioOutcome.UNFAVORABLE.value, 0) > 0.5:
            recommendation = "Avoid this modification — unfavorable outcome probability is high"
        else:
            recommendation = "Proceed with caution — outcomes are uncertain"

        confidence = 0.5
        if all_impacted:
            confidence = sum(
                self._trend_cache.get(d, TrendAnalysis()).forecast_confidence
                for d in all_impacted
            ) / len(all_impacted)

        scenario = CounterfactualScenario(
            query=query,
            base_state=base_state,
            modification=modification,
            predicted_outcome=predicted_outcome,
            outcome_probability=outcome_probs,
            confidence=confidence,
            impacted_domains=list(all_impacted),
            cascading_effects=cascading_effects,
            recommendation=recommendation,
        )

        self._scenarios[scenario.id] = scenario
        self._scenario_history.append(scenario.id)

        return scenario

    # ------------------------------------------------------------------
    # Risk Prediction
    # ------------------------------------------------------------------

    def assess_risks(
        self, domain: str, thresholds: Optional[Dict[str, float]] = None
    ) -> RiskAssessment:
        """
        Perform predictive risk and opportunity assessment for a domain.

        Analyzes trends, volatility, and historical patterns to identify
        upcoming risks and opportunities before they materialize.

        Args:
            domain: The domain to assess.
            thresholds: Optional threshold values for risk classification.

        Returns:
            RiskAssessment with identified risks, opportunities, and mitigations.
        """
        trend = self.analyze_trend(domain)
        series = list(self._time_series.get(domain, []))
        recent_values = [p.value for p in series[-20:]] if series else []

        # Compute risk level from trend and volatility
        risk_level = 0.0
        opportunity_level = 0.0

        if trend.direction in (TrendDirection.STRONG_DOWNWARD.value, TrendDirection.MODERATE_DOWNWARD.value):
            risk_level = trend.strength * 0.7 + trend.volatility * 0.3
        elif trend.direction in (TrendDirection.STRONG_UPWARD.value, TrendDirection.MODERATE_UPWARD.value):
            opportunity_level = trend.strength * 0.7
        elif trend.direction == TrendDirection.VOLATILE.value:
            risk_level = trend.volatility * 0.8
            opportunity_level = trend.volatility * 0.3

        # Identify specific risks
        risks = self._identify_domain_risks(domain, trend, recent_values, thresholds)
        opportunities = self._identify_domain_opportunities(domain, trend, recent_values)

        # Generate mitigation strategies
        mitigations = self._generate_mitigation_strategies(risks, domain)

        # Estimate time to impact
        time_to_impact = self._estimate_time_to_impact(trend, len(series))

        confidence = trend.forecast_confidence

        assessment = RiskAssessment(
            domain=domain,
            risk_level=min(1.0, risk_level),
            opportunity_level=min(1.0, opportunity_level),
            identified_risks=risks,
            identified_opportunities=opportunities,
            mitigation_strategies=mitigations,
            time_to_impact=time_to_impact,
            confidence=confidence,
        )

        self._risk_assessments[domain] = assessment
        return assessment

    def _identify_domain_risks(
        self, domain: str, trend: TrendAnalysis,
        recent_values: List[float], thresholds: Optional[Dict[str, float]],
    ) -> List[Dict[str, Any]]:
        """Identify specific risks based on domain and trend analysis."""
        risks: List[Dict[str, Any]] = []

        if trend.direction in (TrendDirection.STRONG_DOWNWARD.value, TrendDirection.MODERATE_DOWNWARD.value):
            risks.append({
                "type": "sustained_decline",
                "description": f"Sustained downward trajectory in {domain}",
                "severity": min(1.0, 0.5 + trend.strength),
                "probability": trend.forecast_confidence,
            })

        if trend.volatility > 0.3:
            risks.append({
                "type": "high_volatility",
                "description": f"Excessive volatility ({trend.volatility:.2f}) in {domain}",
                "severity": min(1.0, trend.volatility),
                "probability": 0.8,
            })

        if thresholds and recent_values:
            for thresh_name, thresh_value in thresholds.items():
                if recent_values[-1] < thresh_value:
                    risks.append({
                        "type": "threshold_breach",
                        "description": f"Value {recent_values[-1]:.2f} below threshold {thresh_value:.2f} for {thresh_name}",
                        "severity": 0.6,
                        "probability": 0.9,
                    })

        if trend.slope != 0 and len(recent_values) >= 5:
            recent_trend = sum(
                recent_values[i] - recent_values[i - 1]
                for i in range(1, len(recent_values))
            ) / (len(recent_values) - 1)
            if abs(recent_trend) > abs(trend.slope) * 2:
                risks.append({
                    "type": "accelerating_change",
                    "description": "Rate of change is accelerating beyond the long-term trend",
                    "severity": 0.5,
                    "probability": 0.6,
                })

        return risks

    def _identify_domain_opportunities(
        self, domain: str, trend: TrendAnalysis, recent_values: List[float],
    ) -> List[Dict[str, Any]]:
        """Identify specific opportunities based on trend analysis."""
        opportunities: List[Dict[str, Any]] = []

        if trend.direction in (TrendDirection.STRONG_UPWARD.value, TrendDirection.MODERATE_UPWARD.value):
            opportunities.append({
                "type": "growth_momentum",
                "description": f"Positive growth momentum in {domain} presents expansion opportunities",
                "potential_value": min(1.0, trend.strength * 1.2),
                "probability": trend.forecast_confidence,
            })

        if trend.turning_points and len(recent_values) >= 3:
            if recent_values[-1] > recent_values[-2] and recent_values[-2] < recent_values[-3]:
                opportunities.append({
                    "type": "inflection_point",
                    "description": "Detected potential upward inflection — early entry opportunity",
                    "potential_value": 0.7,
                    "probability": 0.5,
                })

        if trend.volatility > 0.2 and trend.direction == TrendDirection.STABLE.value:
            opportunities.append({
                "type": "volatility_arbitrage",
                "description": "Stable trend with high volatility creates arbitrage windows",
                "potential_value": 0.5,
                "probability": 0.4,
            })

        return opportunities

    def _generate_mitigation_strategies(
        self, risks: List[Dict[str, Any]], domain: str
    ) -> List[str]:
        """Generate risk mitigation strategies."""
        strategies = []

        for risk in risks:
            risk_type = risk.get("type", "")
            if risk_type == "sustained_decline":
                strategies.append(f"Implement intervention measures to reverse {domain} decline trend")
                strategies.append("Increase monitoring frequency to daily for early warning signals")
            elif risk_type == "high_volatility":
                strategies.append(f"Apply smoothing/dampening mechanisms to stabilize {domain}")
                strategies.append("Set up automated stabilization triggers at ±2 sigma thresholds")
            elif risk_type == "threshold_breach":
                strategies.append("Activate contingency plan for below-threshold conditions")
                strategies.append("Escalate to priority response for threshold recovery")
            elif risk_type == "accelerating_change":
                strategies.append("Investigate root cause of accelerating change rate")
                strategies.append("Deploy rate-limiting controls to prevent runaway dynamics")

        if not strategies:
            strategies.append(f"Maintain current monitoring posture for {domain}")

        return strategies

    def _estimate_time_to_impact(
        self, trend: TrendAnalysis, series_length: int
    ) -> float:
        """Estimate time until identified risks/opportunities materialize."""
        if trend.slope == 0:
            return float('inf')
        avg_change = abs(trend.slope)
        if avg_change < 0.001:
            return 100.0  # Very slow change
        # Estimate based on how much change is needed to reach a significant level
        return min(100.0, 0.3 / avg_change)

    # ------------------------------------------------------------------
    # Scenario Simulation
    # ------------------------------------------------------------------

    def simulate_scenarios(
        self,
        domain: str,
        decision_point: str,
        possible_choices: List[str],
        current_state: Optional[Dict[str, Any]] = None,
    ) -> List[ScenarioBranch]:
        """
        Simulate multiple branching scenarios from a decision point.

        Uses trend data, historical patterns, and stochastic modeling to
        generate a multi-path outcome tree with probability-weighted branches.

        Args:
            domain: The domain of the decision.
            decision_point: Description of the decision being evaluated.
            possible_choices: List of available choices.
            current_state: Optional current state parameters.

        Returns:
            List of ScenarioBranch with probabilities and utility scores.
        """
        trend = self.analyze_trend(domain)
        branches: List[ScenarioBranch] = []

        total_weight = len(possible_choices)
        for i, choice in enumerate(possible_choices):
            # Compute outcome probability based on trend alignment
            # Choices that align with positive trends get higher probability
            base_prob = 1.0 / total_weight

            if trend.direction in (TrendDirection.STRONG_UPWARD.value, TrendDirection.MODERATE_UPWARD.value):
                # Upward trend favors exploration/expansion-like choices
                base_prob *= 1.0 + (0.1 * (total_weight - i - 1))
            elif trend.direction in (TrendDirection.STRONG_DOWNWARD.value, TrendDirection.MODERATE_DOWNWARD.value):
                # Downward trend favors conservative/defensive choices
                base_prob *= 1.0 + (0.1 * i)

            # Estimate outcome
            if base_prob > 1.0 / total_weight:
                outcome = f"Choice '{choice}' aligns with {trend.direction.value} trend — likely positive outcome"
                utility = 0.6 + random.uniform(0.1, 0.3)
            else:
                outcome = f"Choice '{choice}' goes against {trend.direction.value} trend — uncertain outcome"
                utility = 0.3 + random.uniform(0.1, 0.3)

            # Downstream effects
            effects = [
                f"Immediate impact on {domain} metrics",
            ]
            if trend.volatility > 0.2:
                effects.append(f"Amplified market response due to high volatility ({trend.volatility:.2f})")
            if trend.seasonality > 0:
                effects.append(f"Seasonal pattern (period={trend.seasonality}) may modulate effects")

            branch = ScenarioBranch(
                path_label=choice,
                conditions=[f"Decision at: {decision_point}"],
                outcome=outcome,
                probability=base_prob,
                utility_score=min(0.95, max(0.05, utility)),
                downstream_effects=effects,
                is_preferred=False,
            )

            branches.append(branch)

        # Normalize probabilities
        total_prob = sum(b.probability for b in branches)
        if total_prob > 0:
            for branch in branches:
                branch.probability /= total_prob

        # Mark the preferred branch (highest utility)
        if branches:
            best = max(branches, key=lambda b: b.utility_score)
            best.is_preferred = True

        self._simulations[decision_point] = branches
        return branches

    # ------------------------------------------------------------------
    # Accuracy Feedback
    # ------------------------------------------------------------------

    def record_prediction_accuracy(
        self, domain: str, predicted: float, actual: float
    ) -> float:
        """
        Record the accuracy of a past prediction for continuous improvement.

        Args:
            domain: The forecast domain.
            predicted: The predicted value.
            actual: The actual observed value.

        Returns:
            The computed accuracy score (0.0-1.0).
        """
        # Compute relative accuracy
        if actual == 0:
            accuracy = 1.0 if predicted == 0 else 0.0
        else:
            relative_error = abs(predicted - actual) / abs(actual)
            accuracy = max(0.0, 1.0 - relative_error)

        self._prediction_accuracy[domain].append(accuracy)
        return accuracy

    def get_prediction_quality(self, domain: str) -> Dict[str, Any]:
        """Get prediction quality metrics for a domain."""
        accuracies = list(self._prediction_accuracy.get(domain, []))
        if not accuracies:
            return {"domain": domain, "samples": 0, "avg_accuracy": 0.0}

        return {
            "domain": domain,
            "samples": len(accuracies),
            "avg_accuracy": round(sum(accuracies) / len(accuracies), 4),
            "recent_accuracy": round(
                sum(accuracies[-10:]) / min(10, len(accuracies)), 4
            ),
            "best_accuracy": round(max(accuracies), 4),
            "worst_accuracy": round(min(accuracies), 4),
        }

    # ------------------------------------------------------------------
    # Status & Reporting
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive predictive intelligence system status."""
        return {
            "domains_tracked": len(self._time_series),
            "total_datapoints": sum(len(s) for s in self._time_series.values()),
            "active_forecasts": len(self._forecasts),
            "scenarios_analyzed": len(self._scenarios),
            "risk_assessments": len(self._risk_assessments),
            "simulations_active": len(self._simulations),
            "prediction_quality": {
                domain: self.get_prediction_quality(domain)
                for domain in self._prediction_accuracy
            },
            "trend_cache_size": len(self._trend_cache),
        }

    @classmethod
    def get_instance(cls) -> "AgentPredictiveIntelligence":
        """Return the singleton instance."""
        return cls()

    def reset(self) -> None:
        """Reset all predictive intelligence state."""
        with self._lock:
            self._time_series.clear()
            self._forecasts.clear()
            self._forecast_history.clear()
            self._trend_cache.clear()
            self._last_trend_update.clear()
            self._scenarios.clear()
            self._scenario_history.clear()
            self._risk_assessments.clear()
            self._simulations.clear()
            self._prediction_accuracy.clear()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_predictive_intelligence() -> AgentPredictiveIntelligence:
    """Return the singleton AgentPredictiveIntelligence instance."""
    return AgentPredictiveIntelligence()