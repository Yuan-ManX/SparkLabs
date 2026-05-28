"""
SparkLabs Agent - Game Forecaster

Predictive game state simulation system for AI-assisted game design
decisions. Forecasts balance outcomes, player progression curves,
economy stability, and difficulty pacing before the game is even run.
Supports multiple simulation depths from quick sketches to full Monte Carlo
analysis with anomaly detection across game design domains.

Architecture:
  GameForecaster (Singleton)
    |-- GameStateSnapshot (discrete state capture for simulation)
    |-- ForecastResult (aggregated prediction output)
    |-- BalanceAnalysis (single-parameter balance evaluation)
    |-- ProgressionSimulator (level-based player advancement modeling)
    |-- EconomyPredictor (multi-step resource flow simulation)
    |-- DifficultyEstimator (skill-gated challenge curve mapping)
    |-- MonteCarloEngine (randomized variable perturbation runner)
    |-- AnomalyDetector (forecast deviation analysis)

Forecast Domains:
  BALANCE, PROGRESSION, ECONOMY, DIFFICULTY, RETENTION,
  MONETIZATION, PERFORMANCE

Simulation Depths:
  QUICK_SKETCH (single-pass heuristic), STANDARD (iterative model),
  DEEP_ANALYSIS (multi-phase simulation), MONTE_CARLO (randomized sampling)

Usage:
    forecaster = get_game_forecaster()
    result = forecaster.simulate_progression(
        current_state, parameters, SimulationDepth.STANDARD, TimeHorizon.MID_TERM
    )
    balance = forecaster.analyze_balance("damage_multiplier", 1.5, {"min": 0.8, "max": 2.0})
    anomalies = forecaster.detect_anomalies([result])
    stats = forecaster.get_stats()
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

_time_module = time


class ForecastDomain(Enum):
    BALANCE = "balance"
    PROGRESSION = "progression"
    ECONOMY = "economy"
    DIFFICULTY = "difficulty"
    RETENTION = "retention"
    MONETIZATION = "monetization"
    PERFORMANCE = "performance"


class SimulationDepth(Enum):
    QUICK_SKETCH = "quick_sketch"
    STANDARD = "standard"
    DEEP_ANALYSIS = "deep_analysis"
    MONTE_CARLO = "monte_carlo"


class ForecastConfidence(Enum):
    SPECULATIVE = "speculative"
    LIKELY = "likely"
    HIGH_CONFIDENCE = "high_confidence"
    VALIDATED = "validated"


class TimeHorizon(Enum):
    SHORT_TERM = "short_term"
    MID_TERM = "mid_term"
    LONG_TERM = "long_term"
    FULL_GAME = "full_game"


_HORIZON_STEPS: Dict[str, int] = {
    TimeHorizon.SHORT_TERM.value: 10,
    TimeHorizon.MID_TERM.value: 50,
    TimeHorizon.LONG_TERM.value: 200,
    TimeHorizon.FULL_GAME.value: 500,
}

_DEPTH_PASSES: Dict[str, int] = {
    SimulationDepth.QUICK_SKETCH.value: 1,
    SimulationDepth.STANDARD.value: 3,
    SimulationDepth.DEEP_ANALYSIS.value: 8,
    SimulationDepth.MONTE_CARLO.value: 1,
}

_DOMAIN_DEFAULT_CONFIDENCE: Dict[str, str] = {
    ForecastDomain.BALANCE.value: ForecastConfidence.LIKELY.value,
    ForecastDomain.PROGRESSION.value: ForecastConfidence.HIGH_CONFIDENCE.value,
    ForecastDomain.ECONOMY.value: ForecastConfidence.LIKELY.value,
    ForecastDomain.DIFFICULTY.value: ForecastConfidence.HIGH_CONFIDENCE.value,
    ForecastDomain.RETENTION.value: ForecastConfidence.SPECULATIVE.value,
    ForecastDomain.MONETIZATION.value: ForecastConfidence.SPECULATIVE.value,
    ForecastDomain.PERFORMANCE.value: ForecastConfidence.LIKELY.value,
}

_ECONOMY_SINK_TYPES: List[str] = [
    "item_purchase", "upgrade_cost", "repair_fee",
    "travel_expense", "cosmetic_purchase", "tax",
]

_ECONOMY_FAUCET_TYPES: List[str] = [
    "quest_reward", "enemy_drop", "daily_bonus",
    "achievement_reward", "sell_vendor", "passive_income",
]

_DIFFICULTY_CURVE_TEMPLATES: Dict[str, List[float]] = {
    "linear": [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60],
    "steep": [0.10, 0.15, 0.22, 0.31, 0.42, 0.55, 0.70, 0.85, 0.95, 1.00],
    "gentle": [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50],
    "wave": [0.30, 0.50, 0.30, 0.55, 0.35, 0.60, 0.40, 0.65, 0.45, 0.70],
}

_ANOMALY_THRESHOLDS: Dict[str, float] = {
    "economy_inflation": 0.25,
    "progression_stall": 0.05,
    "difficulty_spike": 0.60,
    "retention_drop": -0.30,
    "balance_outlier": 0.40,
}


@dataclass
class GameStateSnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    variables: Dict[str, float] = field(default_factory=dict)
    entities_count: int = 0
    elapsed_time: float = 0.0
    player_stats: Dict[str, float] = field(default_factory=dict)
    economy_indicators: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "variables": dict(self.variables),
            "entities_count": self.entities_count,
            "elapsed_time": self.elapsed_time,
            "player_stats": dict(self.player_stats),
            "economy_indicators": dict(self.economy_indicators),
        }


@dataclass
class ForecastResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain: str = ForecastDomain.BALANCE.value
    predicted_states: List[GameStateSnapshot] = field(default_factory=list)
    confidence: str = ForecastConfidence.SPECULATIVE.value
    risks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    simulation_iterations: int = 0
    generated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "predicted_state_count": len(self.predicted_states),
            "predicted_states": [s.to_dict() for s in self.predicted_states],
            "confidence": self.confidence,
            "risks": list(self.risks),
            "recommendations": list(self.recommendations),
            "simulation_iterations": self.simulation_iterations,
            "generated_at": self.generated_at,
        }


@dataclass
class BalanceAnalysis:
    parameter_name: str = ""
    current_value: float = 0.0
    predicted_range: Tuple[float, float] = (0.0, 1.0)
    sensitivity_score: float = 0.0
    breaking_point: float = 0.0
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_name": self.parameter_name,
            "current_value": self.current_value,
            "predicted_range": list(self.predicted_range),
            "sensitivity_score": round(self.sensitivity_score, 4),
            "breaking_point": round(self.breaking_point, 2),
            "suggestions": list(self.suggestions),
        }


class GameForecaster:
    """
    Predictive game state simulation for AI-assisted game design.

    Forecasts balance outcomes, player progression curves, economy stability,
    and difficulty pacing across multiple simulation depths and time horizons.
    Supports Monte Carlo sampling for uncertainty quantification and anomaly
    detection across forecast results.

    Usage:
        forecaster = get_game_forecaster()
        result = forecaster.simulate_progression(state, params,
            SimulationDepth.STANDARD, TimeHorizon.MID_TERM)
        balance = forecaster.analyze_balance("damage", 1.5,
            {"min": 0.8, "max": 2.0})
        scores = forecaster.estimate_difficulty_curve(levels, skill_profile)
    """

    _instance: Optional["GameForecaster"] = None
    _lock: threading.RLock = threading.RLock()

    _DEFAULT_PLAYER_LEVEL_CAP = 100
    _DEFAULT_ECONOMY_STARTING_CURRENCY = 1000.0
    _DEFAULT_SIMULATION_SEED_OFFSET = 42
    _MAX_DIFFICULTY_SCORE = 1.0
    _MIN_DIFFICULTY_SCORE = 0.01
    _MONTE_CARLO_MIN_ITERATIONS = 10
    _MONTE_CARLO_MAX_ITERATIONS = 1000
    _PROGRESSION_XP_BASE = 100.0
    _PROGRESSION_XP_GROWTH = 1.12

    def __new__(cls) -> "GameForecaster":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GameForecaster":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._game_models: Dict[str, Dict[str, Any]] = {}
        self._forecast_history: List[ForecastResult] = []
        self._simulation_config: Dict[str, Any] = {
            "default_depth": SimulationDepth.STANDARD.value,
            "default_horizon": TimeHorizon.MID_TERM.value,
            "progression_xp_base": self._PROGRESSION_XP_BASE,
            "progression_xp_growth": self._PROGRESSION_XP_GROWTH,
            "economy_starting_currency": self._DEFAULT_ECONOMY_STARTING_CURRENCY,
            "economy_inflation_rate": 0.02,
            "economy_sink_rate": 0.15,
            "difficulty_default_curve": "linear",
            "monte_carlo_default_iterations": 100,
            "anomaly_detection_enabled": True,
            "forecast_history_limit": 500,
        }
        self._stats: Dict[str, Any] = {
            "total_forecasts": 0,
            "forecasts_by_domain": {},
            "total_monte_carlo_runs": 0,
            "total_anomalies_detected": 0,
            "balance_analyses_performed": 0,
            "difficulty_curves_estimated": 0,
            "economy_simulations_run": 0,
        }

    # ---- Progression Simulation ----

    def simulate_progression(
        self,
        current_state: GameStateSnapshot,
        parameters: Dict[str, Any],
        depth: SimulationDepth = SimulationDepth.STANDARD,
        horizon: TimeHorizon = TimeHorizon.MID_TERM,
    ) -> ForecastResult:
        step_count = _HORIZON_STEPS.get(horizon.value, 50)
        pass_count = _DEPTH_PASSES.get(depth.value, 3)
        domain = ForecastDomain.PROGRESSION.value

        predicted_states: List[GameStateSnapshot] = []

        xp_base = parameters.get("xp_base", self._simulation_config["progression_xp_base"])
        xp_growth = parameters.get("xp_growth", self._simulation_config["progression_xp_growth"])
        level_cap = parameters.get("level_cap", self._DEFAULT_PLAYER_LEVEL_CAP)
        current_level = max(1, int(current_state.player_stats.get("level", 1)))
        current_xp = current_state.player_stats.get("xp", 0.0)
        playtime = current_state.elapsed_time

        for sim_pass in range(pass_count):
            sim_level = current_level
            sim_xp = current_xp
            sim_time = playtime
            xp_required = xp_base * (xp_growth ** (sim_level - 1))

            for step in range(step_count):
                xp_earned = xp_base * (0.8 + random.uniform(0.0, 0.4)) * (1.0 + sim_pass * 0.1)
                sim_xp += xp_earned
                sim_time += 1.0

                while sim_xp >= xp_required and sim_level < level_cap:
                    sim_xp -= xp_required
                    sim_level += 1
                    xp_required = xp_base * (xp_growth ** (sim_level - 1))

                stats = dict(current_state.player_stats)
                stats["level"] = float(sim_level)
                stats["xp"] = round(sim_xp, 2)
                stats["xp_to_next"] = round(max(0.0, xp_required - sim_xp), 2)
                stats["playtime_hours"] = round(sim_time, 2)

                econ = dict(current_state.economy_indicators)
                econ["level_scaled_income"] = round(xp_base * sim_level * 0.5, 2)
                econ["cumulative_playtime"] = round(sim_time, 2)

                snapshot = GameStateSnapshot(
                    variables=dict(current_state.variables),
                    entities_count=current_state.entities_count,
                    elapsed_time=round(sim_time, 2),
                    player_stats=stats,
                    economy_indicators=econ,
                )
                predicted_states.append(snapshot)

        confidence = self._compute_confidence(depth, domain, pass_count)
        risks = self._assess_progression_risks(predicted_states, level_cap)
        recommendations = self._generate_progression_recommendations(risks, current_level, level_cap)

        result = ForecastResult(
            domain=domain,
            predicted_states=predicted_states,
            confidence=confidence,
            risks=risks,
            recommendations=recommendations,
            simulation_iterations=pass_count * step_count,
        )

        self._store_forecast(result)
        return result

    def _assess_progression_risks(
        self,
        states: List[GameStateSnapshot],
        level_cap: int,
    ) -> List[str]:
        risks: List[str] = []
        if not states:
            return ["No states generated during progression simulation"]

        final_level = states[-1].player_stats.get("level", 1)
        if final_level < level_cap * 0.3:
            risks.append(
                f"Slow progression: final level {int(final_level)} far below cap {level_cap}"
            )
        if final_level >= level_cap * 0.95:
            risks.append(
                f"Rapid progression: level cap {level_cap} reached within simulation window"
            )

        levels = [s.player_stats.get("level", 1) for s in states]
        if len(levels) >= 10:
            first_half = sum(levels[: len(levels) // 2]) / max(1, len(levels) // 2)
            second_half = sum(levels[len(levels) // 2 :]) / max(1, len(levels) - len(levels) // 2)
            if second_half - first_half < 1.0:
                risks.append("Progression stall detected: minimal level gain in second half")

        xp_gain_rate = (
            (states[-1].player_stats.get("xp", 0) - states[0].player_stats.get("xp", 0))
            / max(1, len(states))
        )
        if xp_gain_rate < 1.0:
            risks.append("Critically low XP gain rate; players may feel unrewarded")

        return risks

    def _generate_progression_recommendations(
        self,
        risks: List[str],
        current_level: int,
        level_cap: int,
    ) -> List[str]:
        recommendations: List[str] = []
        for risk in risks:
            if "Slow progression" in risk:
                recommendations.append(
                    f"Reduce XP curve steepness or increase XP rewards between level {current_level} and {level_cap}"
                )
            elif "Rapid progression" in risk:
                recommendations.append(
                    f"Introduce XP scaling breakpoints after level {current_level + 10} to extend progression"
                )
            elif "stall" in risk:
                recommendations.append(
                    "Add mid-game content milestones to break progression plateaus"
                )
            elif "low XP" in risk:
                recommendations.append(
                    "Increase XP multiplier on core activities by 20-30%"
                )
        if not recommendations:
            recommendations.append(
                f"Progression curve appears well-tuned for level range {current_level}-{level_cap}"
            )
        return recommendations

    # ---- Balance Analysis ----

    def analyze_balance(
        self,
        parameter_name: str,
        current_value: float,
        constraints: Dict[str, Any],
    ) -> BalanceAnalysis:
        min_val = float(constraints.get("min", current_value * 0.5))
        max_val = float(constraints.get("max", current_value * 2.0))
        target = float(constraints.get("target", (min_val + max_val) / 2.0))

        if min_val >= max_val:
            min_val, max_val = max_val, min_val

        center = (min_val + max_val) / 2.0
        range_width = max_val - min_val

        deviation = (
            abs(current_value - target) / max(range_width * 0.5, 0.001)
        )
        sensitivity_score = min(1.0, deviation * 0.5 + 0.15)

        high_side = current_value + range_width * 0.3
        low_side = current_value - range_width * 0.3
        if high_side > max_val:
            breaking_point = max_val
        elif low_side < min_val:
            breaking_point = min_val
        else:
            breaking_point = target + (current_value - target) * random.uniform(1.1, 1.5)

        breaking_point = max(min_val, min(max_val, breaking_point))

        predicted_range = self._compute_predicted_range(
            current_value, min_val, max_val, sensitivity_score
        )

        suggestions = self._generate_balance_suggestions(
            parameter_name, current_value, target, sensitivity_score, breaking_point
        )

        self._stats["balance_analyses_performed"] += 1

        return BalanceAnalysis(
            parameter_name=parameter_name,
            current_value=round(current_value, 4),
            predicted_range=predicted_range,
            sensitivity_score=round(sensitivity_score, 4),
            breaking_point=round(breaking_point, 2),
            suggestions=suggestions,
        )

    def _compute_predicted_range(
        self,
        current_value: float,
        min_val: float,
        max_val: float,
        sensitivity: float,
    ) -> Tuple[float, float]:
        margin = (max_val - min_val) * sensitivity * 0.4
        lower = current_value - margin
        upper = current_value + margin
        lower = max(min_val, lower)
        upper = min(max_val, upper)
        return (round(lower, 4), round(upper, 4))

    def _generate_balance_suggestions(
        self,
        parameter_name: str,
        current_value: float,
        target: float,
        sensitivity: float,
        breaking_point: float,
    ) -> List[str]:
        suggestions: List[str] = []
        diff_pct = (current_value - target) / max(abs(target), 0.001)

        if abs(diff_pct) < 0.05:
            suggestions.append(
                f"'{parameter_name}' is within optimal range; no tuning needed"
            )
        elif diff_pct > 0:
            suggestions.append(
                f"'{parameter_name}' is {abs(diff_pct)*100:.1f}% above target "
                f"({target:.2f}); consider reducing toward optimal value"
            )
        else:
            suggestions.append(
                f"'{parameter_name}' is {abs(diff_pct)*100:.1f}% below target "
                f"({target:.2f}); consider increasing toward optimal value"
            )

        if sensitivity > 0.6:
            suggestions.append(
                f"High sensitivity ({sensitivity:.2f}): small adjustments to "
                f"'{parameter_name}' will significantly impact gameplay"
            )
        if breaking_point != current_value and abs(breaking_point - current_value) < abs(target - current_value) * 0.5:
            suggestions.append(
                f"Breaking point at {breaking_point:.2f} is close to current value; "
                f"monitor '{parameter_name}' carefully after tuning"
            )
        return suggestions

    # ---- Economy Prediction ----

    def predict_economy(
        self,
        economy_config: Dict[str, Any],
        simulation_steps: int = 100,
    ) -> ForecastResult:
        domain = ForecastDomain.ECONOMY.value

        starting_currency = economy_config.get(
            "starting_currency", self._simulation_config["economy_starting_currency"]
        )
        inflation_rate = economy_config.get(
            "inflation_rate", self._simulation_config["economy_inflation_rate"]
        )
        sink_rate = economy_config.get(
            "sink_rate", self._simulation_config["economy_sink_rate"]
        )
        faucet_multiplier = economy_config.get("faucet_multiplier", 1.0)
        player_count = max(1, economy_config.get("player_count", 1))

        predicted_states: List[GameStateSnapshot] = []
        currency_pool = float(starting_currency)
        total_earned = 0.0
        total_spent = 0.0

        for step in range(simulation_steps):
            faucet_amount = (
                starting_currency * 0.05 * faucet_multiplier
                * (1.0 + step * inflation_rate)
                * player_count
                * random.uniform(0.8, 1.2)
            )
            sink_amount = (
                currency_pool * sink_rate
                * (1.0 + step * inflation_rate * 0.5)
                * random.uniform(0.9, 1.1)
            )

            currency_pool += faucet_amount - sink_amount
            currency_pool = max(0.0, currency_pool)
            total_earned += faucet_amount
            total_spent += sink_amount

            inflation_factor = 1.0 + step * inflation_rate

            snapshot = GameStateSnapshot(
                variables={
                    "step": float(step),
                    "currency_pool": round(currency_pool, 2),
                    "inflation_factor": round(inflation_factor, 4),
                },
                entities_count=player_count,
                elapsed_time=float(step),
                player_stats={
                    "average_wallet": round(currency_pool / max(1, player_count), 2),
                    "cumulative_earned": round(total_earned / max(1, player_count), 2),
                    "cumulative_spent": round(total_spent / max(1, player_count), 2),
                },
                economy_indicators={
                    "money_supply": round(currency_pool, 2),
                    "velocity": round((faucet_amount + sink_amount) / max(currency_pool, 1.0), 4),
                    "inflation_factor": round(inflation_factor, 4),
                    "net_flow": round(faucet_amount - sink_amount, 2),
                },
            )
            predicted_states.append(snapshot)

        confidence = ForecastConfidence.LIKELY.value
        risks = self._assess_economy_risks(predicted_states)
        recommendations = self._generate_economy_recommendations(risks, predicted_states)

        result = ForecastResult(
            domain=domain,
            predicted_states=predicted_states,
            confidence=confidence,
            risks=risks,
            recommendations=recommendations,
            simulation_iterations=simulation_steps,
        )

        self._stats["economy_simulations_run"] += 1
        self._store_forecast(result)
        return result

    def _assess_economy_risks(
        self, states: List[GameStateSnapshot]
    ) -> List[str]:
        risks: List[str] = []
        if not states:
            return ["No economy simulation data available"]

        start_money = states[0].economy_indicators.get("money_supply", 0)
        end_money = states[-1].economy_indicators.get("money_supply", 0)

        if end_money < start_money * 0.3:
            risks.append(
                "Currency drain: money supply dropped by over 70% during simulation"
            )
        if end_money > start_money * 3.0:
            risks.append(
                "Runaway inflation: money supply tripled during simulation window"
            )

        end_inflation = states[-1].economy_indicators.get("inflation_factor", 1.0)
        if end_inflation > 2.5:
            risks.append(
                f"High cumulative inflation factor ({end_inflation:.2f}x); purchasing power degraded"
            )

        velocities = [
            s.economy_indicators.get("velocity", 0.0) for s in states[-20:]
        ]
        avg_velocity = sum(velocities) / max(1, len(velocities))
        if avg_velocity > 5.0:
            risks.append(
                f"Excessive currency velocity ({avg_velocity:.1f}); economy may be unstable"
            )

        return risks

    def _generate_economy_recommendations(
        self,
        risks: List[str],
        states: List[GameStateSnapshot],
    ) -> List[str]:
        recommendations: List[str] = []
        for risk in risks:
            if "Currency drain" in risk:
                recommendations.append(
                    "Increase faucet rates by 15-25% or reduce sink costs on essential items"
                )
            elif "Runaway inflation" in risk:
                recommendations.append(
                    "Introduce progressive gold sinks or cap earning sources at high levels"
                )
            elif "High cumulative inflation" in risk:
                recommendations.append(
                    "Add periodic economy resets or tier-based pricing to counter inflation"
                )
            elif "Excessive currency velocity" in risk:
                recommendations.append(
                    "Slow transaction frequency with cooldowns or limit daily trade volume"
                )
        if not recommendations:
            recommendations.append(
                "Economy appears stable across the simulation window; monitor after content updates"
            )
        return recommendations

    # ---- Difficulty Curve Estimation ----

    def estimate_difficulty_curve(
        self,
        level_configs: List[Dict[str, Any]],
        player_skill_profile: Dict[str, Any],
    ) -> List[float]:
        if not level_configs:
            return []

        skill_rating = player_skill_profile.get("skill_rating", 0.5)
        learning_rate = player_skill_profile.get("learning_rate", 0.1)
        curve_type = self._simulation_config.get(
            "difficulty_default_curve", "linear"
        )
        template = _DIFFICULTY_CURVE_TEMPLATES.get(
            curve_type, _DIFFICULTY_CURVE_TEMPLATES["linear"]
        )

        scores: List[float] = []
        adaptive_skill = skill_rating

        for i, config in enumerate(level_configs):
            base_multiplier = config.get("difficulty_multiplier", 1.0)
            enemy_count = config.get("enemy_count", 3)
            boss_multiplier = config.get("boss_multiplier", 1.0)
            puzzle_complexity = config.get("puzzle_complexity", 1.0)

            template_index = min(i, len(template) - 1)
            base_curve = template[template_index]

            raw_score = (
                base_curve
                * base_multiplier
                * (1.0 + enemy_count * 0.03)
                * boss_multiplier
                * (1.0 + puzzle_complexity * 0.05)
            )
            raw_score = max(self._MIN_DIFFICULTY_SCORE, min(self._MAX_DIFFICULTY_SCORE, raw_score))

            effective_score = raw_score * (1.0 - adaptive_skill * 0.5)
            effective_score = round(
                max(self._MIN_DIFFICULTY_SCORE, min(self._MAX_DIFFICULTY_SCORE, effective_score)),
                4,
            )
            scores.append(effective_score)

            adaptive_skill = min(1.0, adaptive_skill + learning_rate * (raw_score / max(effective_score, 0.01) - 1.0) * 0.3)

        self._stats["difficulty_curves_estimated"] += 1
        return scores

    # ---- Monte Carlo Simulation ----

    def run_monte_carlo(
        self,
        base_state: GameStateSnapshot,
        variables: Dict[str, Tuple[float, float]],
        iterations: int = 100,
    ) -> List[ForecastResult]:
        actual_iterations = max(
            self._MONTE_CARLO_MIN_ITERATIONS,
            min(iterations, self._MONTE_CARLO_MAX_ITERATIONS),
        )
        results: List[ForecastResult] = []
        seeded_random = random.Random(self._DEFAULT_SIMULATION_SEED_OFFSET)

        for i in range(actual_iterations):
            perturbed_state = GameStateSnapshot(
                variables=dict(base_state.variables),
                entities_count=base_state.entities_count,
                elapsed_time=base_state.elapsed_time,
                player_stats=dict(base_state.player_stats),
                economy_indicators=dict(base_state.economy_indicators),
            )

            for var_name, (var_min, var_max) in variables.items():
                if var_name in perturbed_state.variables:
                    base_val = perturbed_state.variables[var_name]
                    perturbed = base_val * seeded_random.uniform(
                        max(0.01, var_min / max(base_val, 0.001)),
                        var_max / max(base_val, 0.001),
                    )
                    perturbed_state.variables[var_name] = round(perturbed, 4)
                elif var_name in perturbed_state.player_stats:
                    base_val = perturbed_state.player_stats[var_name]
                    perturbed = base_val * seeded_random.uniform(
                        max(0.01, var_min / max(base_val, 0.001)),
                        var_max / max(base_val, 0.001),
                    )
                    perturbed_state.player_stats[var_name] = round(perturbed, 4)
                elif var_name in perturbed_state.economy_indicators:
                    base_val = perturbed_state.economy_indicators[var_name]
                    perturbed = base_val * seeded_random.uniform(
                        max(0.01, var_min / max(base_val, 0.001)),
                        var_max / max(base_val, 0.001),
                    )
                    perturbed_state.economy_indicators[var_name] = round(perturbed, 4)

            params: Dict[str, Any] = {
                "xp_base": self._simulation_config["progression_xp_base"],
                "xp_growth": self._simulation_config["progression_xp_growth"],
                "level_cap": self._DEFAULT_PLAYER_LEVEL_CAP,
            }
            result = self.simulate_progression(
                perturbed_state,
                params,
                depth=SimulationDepth.QUICK_SKETCH,
                horizon=TimeHorizon.SHORT_TERM,
            )
            result.confidence = self._compute_monte_carlo_confidence(
                actual_iterations, i, result
            )
            results.append(result)

        self._stats["total_monte_carlo_runs"] += actual_iterations
        return results

    def _compute_monte_carlo_confidence(
        self,
        total_iterations: int,
        current_iteration: int,
        result: ForecastResult,
    ) -> str:
        if total_iterations <= 50:
            return ForecastConfidence.SPECULATIVE.value
        if current_iteration < total_iterations * 0.5:
            return ForecastConfidence.LIKELY.value
        return ForecastConfidence.HIGH_CONFIDENCE.value

    # ---- Anomaly Detection ----

    def detect_anomalies(
        self, forecast_results: List[ForecastResult]
    ) -> List[str]:
        anomalies: List[str] = []
        if not forecast_results:
            return ["No forecast results to analyze"]

        for result in forecast_results:
            if not result.predicted_states:
                continue

            domain_anomalies = self._detect_domain_anomalies(result)
            anomalies.extend(domain_anomalies)

        unique = list(dict.fromkeys(anomalies))
        self._stats["total_anomalies_detected"] += len(unique)
        return unique

    def _detect_domain_anomalies(
        self, result: ForecastResult
    ) -> List[str]:
        anomalies: List[str] = []
        domain = result.domain
        states = result.predicted_states
        if len(states) < 2:
            return anomalies

        if domain == ForecastDomain.ECONOMY.value:
            anomalies.extend(self._detect_economy_anomalies(states))
        elif domain == ForecastDomain.PROGRESSION.value:
            anomalies.extend(self._detect_progression_anomalies(states))
        elif domain == ForecastDomain.DIFFICULTY.value:
            anomalies.extend(self._detect_difficulty_anomalies(result))
        elif domain == ForecastDomain.BALANCE.value:
            anomalies.extend(self._detect_balance_anomalies(states))

        return anomalies

    def _detect_economy_anomalies(
        self, states: List[GameStateSnapshot]
    ) -> List[str]:
        anomalies: List[str] = []
        start_money = states[0].economy_indicators.get("money_supply", 0)
        end_money = states[-1].economy_indicators.get("money_supply", 0)

        if start_money > 0:
            change_ratio = (end_money - start_money) / start_money
            if change_ratio > _ANOMALY_THRESHOLDS["economy_inflation"]:
                anomalies.append(
                    f"ECONOMY: Inflation anomaly — money supply grew "
                    f"{change_ratio*100:.1f}% exceeding {_ANOMALY_THRESHOLDS['economy_inflation']*100:.0f}% threshold"
                )
            if change_ratio < -_ANOMALY_THRESHOLDS["economy_inflation"]:
                anomalies.append(
                    f"ECONOMY: Deflation anomaly — money supply contracted "
                    f"{abs(change_ratio)*100:.1f}% exceeding threshold"
                )

        flows = [
            s.economy_indicators.get("net_flow", 0.0) for s in states[1:]
        ]
        flow_changes = [
            abs(flows[i] - flows[i - 1])
            for i in range(1, len(flows))
        ]
        if flow_changes:
            avg_change = sum(flow_changes) / len(flow_changes)
            max_flow = max(abs(f) for f in flows) or 1.0
            if avg_change > max_flow * 0.5:
                anomalies.append(
                    "ECONOMY: Volatility anomaly — high variance in net currency flow"
                )

        return anomalies

    def _detect_progression_anomalies(
        self, states: List[GameStateSnapshot]
    ) -> List[str]:
        anomalies: List[str] = []
        levels = [s.player_stats.get("level", 1) for s in states]

        segments = len(levels) // 10
        if segments < 2:
            return anomalies

        segment_gains: List[float] = []
        for seg in range(segments):
            start_idx = seg * 10
            end_idx = min((seg + 1) * 10, len(levels))
            gain = levels[end_idx - 1] - levels[start_idx]
            segment_gains.append(gain)

        avg_gain = sum(segment_gains) / len(segment_gains) if segment_gains else 0
        for idx, gain in enumerate(segment_gains):
            if avg_gain > 0 and gain < avg_gain * _ANOMALY_THRESHOLDS["progression_stall"]:
                anomalies.append(
                    f"PROGRESSION: Stall anomaly in segment {idx + 1} — "
                    f"level gain {gain:.1f} vs average {avg_gain:.1f}"
                )

        if len(levels) >= 20:
            recent = levels[-10:]
            if max(recent) - min(recent) < 1.0:
                anomalies.append(
                    "PROGRESSION: Plateau anomaly — level progression flatlined in recent window"
                )

        return anomalies

    def _detect_difficulty_anomalies(
        self, result: ForecastResult
    ) -> List[str]:
        anomalies: List[str] = []
        if not result.predicted_states:
            return anomalies

        difficulty_values: List[float] = []
        for state in result.predicted_states:
            diff = state.variables.get("difficulty_score", state.player_stats.get("level", 0.5))
            difficulty_values.append(float(diff))

        if len(difficulty_values) < 3:
            return anomalies

        for i in range(1, len(difficulty_values)):
            prev = max(difficulty_values[i - 1], 0.01)
            spike = (difficulty_values[i] - prev) / prev
            if spike > _ANOMALY_THRESHOLDS["difficulty_spike"]:
                anomalies.append(
                    f"DIFFICULTY: Spike anomaly at step {i} — "
                    f"difficulty jumped {spike*100:.1f}% exceeding "
                    f"{_ANOMALY_THRESHOLDS['difficulty_spike']*100:.0f}% threshold"
                )

        return anomalies

    def _detect_balance_anomalies(
        self, states: List[GameStateSnapshot]
    ) -> List[str]:
        anomalies: List[str] = []
        if not states:
            return anomalies

        all_variables: Dict[str, List[float]] = {}
        for state in states:
            for key, val in state.variables.items():
                if key not in all_variables:
                    all_variables[key] = []
                all_variables[key].append(val)

        for var_name, values in all_variables.items():
            if len(values) < 3:
                continue
            mean_val = sum(values) / len(values)
            if mean_val == 0:
                continue
            deviations = [abs(v - mean_val) / abs(mean_val) for v in values]
            max_dev = max(deviations)
            if max_dev > _ANOMALY_THRESHOLDS["balance_outlier"]:
                anomalies.append(
                    f"BALANCE: Outlier in '{var_name}' — "
                    f"max deviation {max_dev*100:.1f}% exceeds "
                    f"{_ANOMALY_THRESHOLDS['balance_outlier']*100:.0f}% threshold"
                )

        return anomalies

    # ---- Confidence Computation ----

    def _compute_confidence(
        self,
        depth: SimulationDepth,
        domain: str,
        pass_count: int,
    ) -> str:
        if depth == SimulationDepth.MONTE_CARLO:
            return ForecastConfidence.HIGH_CONFIDENCE.value
        if depth == SimulationDepth.DEEP_ANALYSIS:
            return ForecastConfidence.HIGH_CONFIDENCE.value
        if depth == SimulationDepth.STANDARD:
            return _DOMAIN_DEFAULT_CONFIDENCE.get(domain, ForecastConfidence.LIKELY.value)
        return ForecastConfidence.SPECULATIVE.value

    # ---- Forecast Storage ----

    def _store_forecast(self, result: ForecastResult) -> None:
        domain = result.domain
        self._forecast_history.append(result)
        self._stats["total_forecasts"] += 1
        if domain not in self._stats["forecasts_by_domain"]:
            self._stats["forecasts_by_domain"][domain] = 0
        self._stats["forecasts_by_domain"][domain] += 1

        limit = self._simulation_config.get("forecast_history_limit", 500)
        if len(self._forecast_history) > limit:
            self._forecast_history = self._forecast_history[-limit:]

    # ---- Model Registration ----

    def register_game_model(
        self, model_id: str, model_config: Dict[str, Any]
    ) -> None:
        self._game_models[model_id] = {
            "config": dict(model_config),
            "registered_at": _time_module.time(),
        }

    def get_game_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        return self._game_models.get(model_id)

    def list_game_models(self) -> List[str]:
        return list(self._game_models.keys())

    # ---- Configuration ----

    def update_simulation_config(
        self, updates: Dict[str, Any]
    ) -> None:
        for key, value in updates.items():
            if key in self._simulation_config:
                self._simulation_config[key] = value

    def get_simulation_config(self) -> Dict[str, Any]:
        return dict(self._simulation_config)

    # ---- Stats & Retrieval ----

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_forecasts": self._stats["total_forecasts"],
            "forecasts_by_domain": dict(self._stats["forecasts_by_domain"]),
            "total_monte_carlo_runs": self._stats["total_monte_carlo_runs"],
            "total_anomalies_detected": self._stats["total_anomalies_detected"],
            "balance_analyses_performed": self._stats["balance_analyses_performed"],
            "difficulty_curves_estimated": self._stats["difficulty_curves_estimated"],
            "economy_simulations_run": self._stats["economy_simulations_run"],
            "forecast_history_size": len(self._forecast_history),
            "registered_models": len(self._game_models),
            "simulation_config": dict(self._simulation_config),
            "available_domains": [d.value for d in ForecastDomain],
            "available_depths": [d.value for d in SimulationDepth],
            "available_horizons": [h.value for h in TimeHorizon],
            "available_confidences": [c.value for c in ForecastConfidence],
        }

    def get_forecast_history(
        self, domain: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        results = list(self._forecast_history)
        if domain:
            results = [r for r in results if r.domain == domain]
        return [r.to_dict() for r in results[-limit:]]

    def get_latest_forecast(
        self, domain: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        candidates = list(self._forecast_history)
        if domain:
            candidates = [r for r in candidates if r.domain == domain]
        if not candidates:
            return None
        return candidates[-1].to_dict()

    def reset(self) -> None:
        self._game_models.clear()
        self._forecast_history.clear()
        self._stats = {
            "total_forecasts": 0,
            "forecasts_by_domain": {},
            "total_monte_carlo_runs": 0,
            "total_anomalies_detected": 0,
            "balance_analyses_performed": 0,
            "difficulty_curves_estimated": 0,
            "economy_simulations_run": 0,
        }


def get_game_forecaster() -> GameForecaster:
    return GameForecaster.get_instance()