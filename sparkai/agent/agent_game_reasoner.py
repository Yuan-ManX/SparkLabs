"""
SparkLabs Agent - Game Design Reasoner

Reasoning engine for game balance, difficulty curves, progression systems,
and mechanics. Analyzes game design decisions and suggests optimizations
using mathematical modeling, curve fitting, and simulation techniques.

Architecture:
  GameDesignReasoner
    |-- DesignAnalyzer (comprehensive design evaluation)
    |-- BalanceOptimizer (parameter tuning and fairness analysis)
    |-- CurveModeler (progression and difficulty curve fitting)
    |-- EconomySimulator (in-game economy flow simulation)
    |-- DesignComparator (A/B comparison of alternate designs)

Analysis Domains:
  - BALANCE: fairness, power distribution, counterplay viability
  - DIFFICULTY: challenge scaling, skill floor/ceiling, player frustration points
  - PROGRESSION: level-up pacing, unlock distribution, reward timing
  - ECONOMY: currency flow, sink/faucet ratios, inflation modeling
  - PACING: tension/reward rhythm, content density, session length
  - ACCESSIBILITY: difficulty options, input customization, barrier reduction
  - REPLAYABILITY: procedural variation, emergent mechanics, mastery depth
  - ENGAGEMENT: flow state modeling, attention curve, retention hooks
"""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DesignAspect(Enum):
    """Dimensions of game design analysis."""
    BALANCE = "balance"
    DIFFICULTY = "difficulty"
    PROGRESSION = "progression"
    ECONOMY = "economy"
    PACING = "pacing"
    ACCESSIBILITY = "accessibility"
    REPLAYABILITY = "replayability"
    ENGAGEMENT = "engagement"


class OptimizationGoal(Enum):
    """Target objectives for design optimization."""
    MAXIMIZE_FUN = "maximize_fun"
    BALANCE_FAIRNESS = "balance_fairness"
    SMOOTH_DIFFICULTY = "smooth_difficulty"
    BOOST_ENGAGEMENT = "boost_engagement"
    REDUCE_FRUSTRATION = "reduce_frustration"
    ENHANCE_ACCESSIBILITY = "enhance_accessibility"


class ConfidenceLevel(Enum):
    """Confidence rating for design recommendations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CONFIRMED = "confirmed"


@dataclass
class DesignAnalysis:
    """Result of analyzing a specific game design aspect."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    aspect: DesignAspect = DesignAspect.BALANCE
    current_state: Dict[str, Any] = field(default_factory=dict)
    analysis: str = ""
    suggestions: List[str] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "aspect": self.aspect.value,
            "current_state": self.current_state,
            "analysis": self.analysis,
            "suggestions": self.suggestions,
            "confidence": self.confidence.value,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class BalanceParameter:
    """A tunable game balance parameter with optimal range."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    current_value: float = 0.0
    range_min: float = 0.0
    range_max: float = 100.0
    optimal_range: Tuple[float, float] = (0.0, 100.0)
    impact_score: float = 0.0
    affected_systems: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        in_optimal = self.optimal_range[0] <= self.current_value <= self.optimal_range[1]
        deviation = 0.0
        optimal_center = (self.optimal_range[0] + self.optimal_range[1]) / 2.0
        if optimal_center > 0:
            deviation = abs(self.current_value - optimal_center) / optimal_center
        return {
            "id": self.id,
            "name": self.name,
            "current_value": self.current_value,
            "range_min": self.range_min,
            "range_max": self.range_max,
            "optimal_range": list(self.optimal_range),
            "is_in_optimal_range": in_optimal,
            "deviation_from_optimal": round(deviation, 4),
            "impact_score": self.impact_score,
            "affected_systems": self.affected_systems,
            "created_at": self.created_at,
        }


@dataclass
class ProgressionCurve:
    """Mathematical model of a progression curve."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    data_points: List[Tuple[float, float]] = field(default_factory=list)
    curve_type: str = "linear"
    formula: str = ""
    visualization_data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "data_points": self.data_points,
            "curve_type": self.curve_type,
            "formula": self.formula,
            "visualization_data": self.visualization_data,
            "created_at": self.created_at,
        }

    def evaluate(self, x: float) -> float:
        """Evaluate the curve at a given input point."""
        if self.curve_type == "exponential":
            base = self.visualization_data.get("base", 1.05)
            return self.data_points[0][1] * (base ** x) if self.data_points else x
        elif self.curve_type == "logarithmic":
            multiplier = self.visualization_data.get("multiplier", 1.0)
            offset = self.visualization_data.get("offset", 1.0)
            return multiplier * math.log(max(x + offset, 1))
        elif self.curve_type == "s_curve":
            steepness = self.visualization_data.get("steepness", 0.1)
            midpoint = self.visualization_data.get("midpoint", len(self.data_points) / 2 if self.data_points else 5)
            max_val = self.visualization_data.get("max_value", 100.0)
            return max_val / (1 + math.exp(-steepness * (x - midpoint)))
        else:
            if len(self.data_points) < 2:
                return x
            slope = (self.data_points[-1][1] - self.data_points[0][1]) / max(
                self.data_points[-1][0] - self.data_points[0][0], 1
            )
            intercept = self.data_points[0][1] - slope * self.data_points[0][0]
            return slope * x + intercept


@dataclass
class DesignSuggestion:
    """A concrete design recommendation with rationale."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    analysis_id: str = ""
    suggestion: str = ""
    rationale: str = ""
    expected_impact: str = ""
    risk_level: str = "low"
    implementation_effort: str = "medium"
    priority: int = 3
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "suggestion": self.suggestion,
            "rationale": self.rationale,
            "expected_impact": self.expected_impact,
            "risk_level": self.risk_level,
            "implementation_effort": self.implementation_effort,
            "priority": self.priority,
            "created_at": self.created_at,
        }


class GameDesignReasoner:
    """AI reasoning engine for game design analysis and optimization."""

    _instance: Optional["GameDesignReasoner"] = None
    _lock = threading.RLock()

    _TEMPERATURE_DECAY_RATE = 0.95
    _MAX_CURVE_POINTS = 100
    _DEFAULT_ECONOMY_STEPS = 50

    _CURVE_FITTING_CONFIG: Dict[str, Dict[str, Any]] = {
        "linear": {"tolerance": 0.05, "max_deviation_pct": 10},
        "exponential": {"base_range": (1.02, 1.5), "max_deviation_pct": 15},
        "logarithmic": {"offset_range": (0.0, 5.0), "max_deviation_pct": 12},
        "s_curve": {"steepness_range": (0.01, 0.5), "max_deviation_pct": 8},
    }

    def __init__(self) -> None:
        self._analyses: Dict[str, DesignAnalysis] = {}
        self._parameters: Dict[str, BalanceParameter] = {}
        self._curves: Dict[str, ProgressionCurve] = {}
        self._suggestions: Dict[str, DesignSuggestion] = {}
        self._simulation_results: Dict[str, Dict[str, Any]] = {}
        self._optimization_history: List[Dict[str, Any]] = []
        self._total_analyses = 0
        self._total_suggestions = 0
        self._total_simulations = 0

    @classmethod
    def get_instance(cls) -> "GameDesignReasoner":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def analyze_game_design(self,
                           game_state: Dict[str, Any],
                           aspects: Optional[List[str]] = None) -> List[DesignAnalysis]:
        """Performs comprehensive design analysis across specified aspects."""
        target_aspects: List[DesignAspect]
        if aspects is None:
            target_aspects = list(DesignAspect)
        else:
            target_aspects = []
            for a in aspects:
                try:
                    target_aspects.append(DesignAspect(a.lower()))
                except ValueError:
                    pass
        if not target_aspects:
            target_aspects = [DesignAspect.BALANCE]

        results: List[DesignAnalysis] = []
        for aspect in target_aspects:
            analysis = self._analyze_aspect(aspect, game_state)
            self._analyses[analysis.id] = analysis
            self._total_analyses += 1
            results.append(analysis)

        return results

    def suggest_balancing(self,
                         parameter_name: str,
                         current_value: float,
                         target_experience: str) -> List[DesignSuggestion]:
        """Generates balance recommendations for a specific parameter."""
        parameter = self._parameters.get(parameter_name)
        suggestions: List[DesignSuggestion] = []

        if parameter is None:
            parameter = BalanceParameter(
                name=parameter_name,
                current_value=current_value,
            )
            self._parameters[parameter_name] = parameter

        optimal_center = (parameter.optimal_range[0] + parameter.optimal_range[1]) / 2.0
        deviation = current_value - optimal_center

        if abs(deviation) < (parameter.optimal_range[1] - parameter.optimal_range[0]) * 0.1:
            suggestion = DesignSuggestion(
                analysis_id="",
                suggestion=f"Parameter '{parameter_name}' is within optimal range — no changes needed",
                rationale=f"Current value {current_value} is within acceptable bounds",
                expected_impact="Maintains current player experience",
                risk_level="low",
                implementation_effort="none",
                priority=5,
            )
            suggestions.append(suggestion)
        else:
            target = optimal_center
            direction = "increase" if deviation < 0 else "decrease"
            suggestion = DesignSuggestion(
                analysis_id="",
                suggestion=f"{direction.capitalize()} '{parameter_name}' from {current_value} to {round(target, 2)}",
                rationale=f"Deviation of {abs(deviation):.2f} from optimal center {optimal_center:.2f} impacts {target_experience}",
                expected_impact=f"Better alignment with {target_experience} target experience",
                risk_level="low" if abs(deviation) < optimal_center * 0.3 else "medium",
                implementation_effort="low",
                priority=3,
            )
            suggestions.append(suggestion)

            alternative = DesignSuggestion(
                analysis_id="",
                suggestion=f"Gradually adjust '{parameter_name}' in steps of {abs(deviation)/3:.2f}",
                rationale="Incremental changes reduce risk of player backlash",
                expected_impact="Smoother transition to target balance state",
                risk_level="low",
                implementation_effort="medium",
                priority=4,
            )
            suggestions.append(alternative)

        for s in suggestions:
            self._suggestions[s.id] = s
            self._total_suggestions += 1

        return suggestions

    def model_progression_curve(self,
                               curve_name: str,
                               data_points: List[Tuple[float, float]],
                               target_shape: str = "linear") -> ProgressionCurve:
        """Fits a mathematical progression curve to the data points."""
        if not data_points or len(data_points) < 2:
            curve = ProgressionCurve(
                name=curve_name,
                data_points=data_points or [(0.0, 0.0), (1.0, 1.0)],
                curve_type=target_shape,
                formula="y = x",
            )
            self._curves[curve.id] = curve
            return curve

        fit_result = self._fit_curve(data_points, target_shape)
        curve = ProgressionCurve(
            name=curve_name,
            data_points=data_points,
            curve_type=fit_result["curve_type"],
            formula=fit_result["formula"],
            visualization_data=fit_result["params"],
        )
        self._curves[curve.id] = curve
        return curve

    def evaluate_difficulty(self,
                           game_state: Dict[str, Any],
                           player_skill: float = 0.5) -> DesignAnalysis:
        """Assesses game difficulty relative to player skill level."""
        current_difficulty = game_state.get("difficulty", {}).get("current", 0.5)
        target_difficulty = game_state.get("difficulty", {}).get("target", 0.6)
        frustration_indicators = game_state.get("frustration_indicators", [])

        difficulty_gap = current_difficulty - target_difficulty
        gap_score = abs(difficulty_gap)

        confidence = ConfidenceLevel.MEDIUM
        if gap_score < 0.05:
            analysis_text = "Difficulty is well-calibrated for the target player skill level"
            confidence = ConfidenceLevel.HIGH
        elif difficulty_gap > 0:
            analysis_text = "Game is harder than target — may cause player frustration"
            confidence = ConfidenceLevel.CONFIRMED if frustration_indicators else ConfidenceLevel.MEDIUM
        else:
            analysis_text = "Game is easier than target — may reduce player engagement"
            confidence = ConfidenceLevel.MEDIUM

        suggestions = []
        if abs(difficulty_gap) > 0.05:
            if difficulty_gap > 0:
                suggestions.append("Consider reducing enemy health or damage scaling")
                suggestions.append("Add more frequent checkpoint opportunities")
                suggestions.append("Provide enhanced tutorial hints at difficulty spike points")
            else:
                suggestions.append("Introduce optional challenge modifiers")
                suggestions.append("Add time-trial or perfect-clear bonus objectives")
                suggestions.append("Increase enemy variety at higher progression stages")

        analysis = DesignAnalysis(
            aspect=DesignAspect.DIFFICULTY,
            current_state={
                "current_difficulty": current_difficulty,
                "target_difficulty": target_difficulty,
                "player_skill": player_skill,
                "difficulty_gap": difficulty_gap,
            },
            analysis=analysis_text,
            suggestions=suggestions,
            confidence=confidence,
            metadata={"frustration_indicators": frustration_indicators},
        )

        self._analyses[analysis.id] = analysis
        self._total_analyses += 1
        return analysis

    def generate_tuning_parameters(self, system_name: str) -> List[BalanceParameter]:
        """Generates tunable balance parameters for a game system."""
        templates: Dict[str, List[Dict[str, Any]]] = {
            "combat": [
                {"name": "base_damage", "default": 10.0, "range": (1.0, 100.0), "optimal": (5.0, 25.0)},
                {"name": "attack_speed", "default": 1.0, "range": (0.1, 5.0), "optimal": (0.5, 2.0)},
                {"name": "critical_chance", "default": 0.1, "range": (0.0, 1.0), "optimal": (0.05, 0.25)},
                {"name": "health_pool", "default": 100.0, "range": (10.0, 5000.0), "optimal": (80.0, 500.0)},
                {"name": "armor_value", "default": 10.0, "range": (0.0, 500.0), "optimal": (5.0, 50.0)},
            ],
            "economy": [
                {"name": "currency_drop_rate", "default": 1.0, "range": (0.1, 10.0), "optimal": (0.5, 3.0)},
                {"name": "item_base_price", "default": 50.0, "range": (1.0, 10000.0), "optimal": (10.0, 1000.0)},
                {"name": "repair_cost_rate", "default": 0.1, "range": (0.01, 0.5), "optimal": (0.03, 0.15)},
                {"name": "sellback_ratio", "default": 0.5, "range": (0.1, 1.0), "optimal": (0.3, 0.7)},
                {"name": "resource_scarcity", "default": 0.5, "range": (0.1, 0.9), "optimal": (0.3, 0.6)},
            ],
            "progression": [
                {"name": "xp_per_kill", "default": 10.0, "range": (1.0, 100.0), "optimal": (5.0, 30.0)},
                {"name": "xp_curve_exponent", "default": 1.2, "range": (1.0, 2.0), "optimal": (1.05, 1.3)},
                {"name": "unlock_frequency", "default": 3.0, "range": (1.0, 10.0), "optimal": (2.0, 5.0)},
                {"name": "max_level", "default": 100, "range": (20.0, 999.0), "optimal": (50.0, 200.0)},
                {"name": "power_scaling_per_level", "default": 1.10, "range": (1.01, 1.50), "optimal": (1.05, 1.15)},
            ],
            "skills": [
                {"name": "cooldown_base", "default": 5.0, "range": (0.5, 60.0), "optimal": (2.0, 10.0)},
                {"name": "duration_base", "default": 3.0, "range": (0.5, 30.0), "optimal": (1.5, 6.0)},
                {"name": "mana_cost_base", "default": 20.0, "range": (0.0, 500.0), "optimal": (10.0, 80.0)},
                {"name": "skill_range", "default": 300.0, "range": (50.0, 2000.0), "optimal": (150.0, 600.0)},
                {"name": "aoe_radius", "default": 100.0, "range": (20.0, 500.0), "optimal": (60.0, 200.0)},
            ],
        }

        system_templates = templates.get(system_name.lower(), templates.get("combat", []))
        parameters: List[BalanceParameter] = []

        for tpl in system_templates:
            param = BalanceParameter(
                name=f"{system_name}.{tpl['name']}",
                current_value=tpl["default"],
                range_min=tpl["range"][0],
                range_max=tpl["range"][1],
                optimal_range=(tpl["optimal"][0], tpl["optimal"][1]),
                impact_score=self._calc_impact(tpl["name"], system_name),
                affected_systems=[system_name],
            )
            self._parameters[param.name] = param
            parameters.append(param)

        return parameters

    def compare_designs(self,
                       design_a: Dict[str, Any],
                       design_b: Dict[str, Any],
                       metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """Performs A/B comparison of two game design alternatives."""
        if metrics is None:
            metrics = ["balance_score", "difficulty_fairness", "engagement_potential",
                      "accessibility_score", "replayability_potential", "economy_health"]

        comparison: Dict[str, Any] = {
            "design_a_name": design_a.get("name", "Design A"),
            "design_b_name": design_b.get("name", "Design B"),
            "metrics": {},
            "winner_per_metric": {},
            "overall_winner": "",
            "detailed_notes": [],
        }

        a_wins = 0
        b_wins = 0

        for metric in metrics:
            a_val = float(design_a.get(metric, 0.5))
            b_val = float(design_b.get(metric, 0.5))
            diff = a_val - b_val

            comparison["metrics"][metric] = {
                "design_a_value": a_val,
                "design_b_value": b_val,
                "difference": round(diff, 4),
            }

            if diff > 0.02:
                comparison["winner_per_metric"][metric] = "design_a"
                a_wins += 1
                if abs(diff) > 0.1:
                    comparison["detailed_notes"].append(
                        f"Design A outperforms in '{metric}' by {diff:.2%}"
                    )
            elif diff < -0.02:
                comparison["winner_per_metric"][metric] = "design_b"
                b_wins += 1
                if abs(diff) > 0.1:
                    comparison["detailed_notes"].append(
                        f"Design B significantly outperforms in '{metric}' by {abs(diff):.2%}"
                    )
            else:
                comparison["winner_per_metric"][metric] = "tie"

        threshold = len(metrics) * 0.6
        if a_wins >= threshold:
            comparison["overall_winner"] = "design_a"
        elif b_wins >= threshold:
            comparison["overall_winner"] = "design_b"
        elif a_wins > b_wins:
            comparison["overall_winner"] = "design_a_slight"
        elif b_wins > a_wins:
            comparison["overall_winner"] = "design_b_slight"
        else:
            comparison["overall_winner"] = "tie"

        comparison["score_summary"] = {
            "design_a_total_wins": a_wins,
            "design_b_total_wins": b_wins,
            "ties": len(metrics) - a_wins - b_wins,
            "total_metrics": len(metrics),
        }

        return comparison

    def simulate_economy(self,
                        economy_config: Dict[str, Any],
                        simulation_steps: int = 50) -> Dict[str, Any]:
        """Simulates in-game economy flow over multiple time steps."""
        steps = min(simulation_steps, 200)

        faucet_rate = economy_config.get("faucet_rate", 100.0)
        sink_rate = economy_config.get("sink_rate", 0.7)
        initial_currency = economy_config.get("initial_currency", 500.0)
        player_spending_rate = economy_config.get("player_spending_rate", 0.5)
        inflation_factor = economy_config.get("inflation_factor", 1.02)

        currency_history: List[float] = [initial_currency]
        net_flow_history: List[float] = []
        total_generated = 0.0
        total_spent = 0.0

        current_currency = initial_currency

        for step in range(steps):
            generated = faucet_rate * (step * inflation_factor / max(steps, 1) + 1)
            spent = current_currency * sink_rate * player_spending_rate + 5
            net_flow = generated - spent
            current_currency += net_flow
            current_currency = max(0.0, current_currency)

            currency_history.append(current_currency)
            net_flow_history.append(net_flow)
            total_generated += generated
            total_spent += spent

        is_sustainable = current_currency > initial_currency * 0.3
        inflation_trend = self._calc_inflation_trend(currency_history)
        balance_score = self._calc_economy_balance(
            total_generated, total_spent, currency_history
        )

        result = {
            "simulation_id": uuid.uuid4().hex,
            "steps": steps,
            "currency_history": currency_history,
            "net_flow_history": net_flow_history,
            "final_currency": round(currency_history[-1], 2),
            "total_generated": round(total_generated, 2),
            "total_spent": round(total_spent, 2),
            "is_sustainable": is_sustainable,
            "inflation_trend": round(inflation_trend, 4),
            "balance_score": round(balance_score, 2),
            "currency_change_pct": round(
                (currency_history[-1] - initial_currency) / max(initial_currency, 1) * 100, 1
            ),
            "health_status": (
                "healthy" if is_sustainable and balance_score > 0.5
                else "warning" if is_sustainable
                else "critical"
            ),
        }

        self._simulation_results[result["simulation_id"]] = result
        self._total_simulations += 1
        return result

    def get_analysis(self, analysis_id: str) -> Optional[DesignAnalysis]:
        """Retrieves a design analysis by ID."""
        return self._analyses.get(analysis_id)

    def get_curve(self, curve_id: str) -> Optional[ProgressionCurve]:
        """Retrieves a progression curve by ID."""
        return self._curves.get(curve_id)

    def get_suggestion(self, suggestion_id: str) -> Optional[DesignSuggestion]:
        """Retrieves a design suggestion by ID."""
        return self._suggestions.get(suggestion_id)

    def get_parameter(self, name: str) -> Optional[BalanceParameter]:
        """Retrieves a balance parameter by name."""
        return self._parameters.get(name)

    def list_analyses(self, aspect: Optional[str] = None) -> List[DesignAnalysis]:
        """Lists design analyses, optionally filtered by aspect."""
        if aspect is None:
            return list(self._analyses.values())
        return [
            a for a in self._analyses.values()
            if a.aspect.value == aspect.lower()
        ]

    def list_suggestions(self, priority_min: int = 1) -> List[DesignSuggestion]:
        """Lists design suggestions filtered by minimum priority."""
        return [
            s for s in self._suggestions.values()
            if s.priority >= priority_min
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Returns current reasoner statistics."""
        aspect_counts: Dict[str, int] = {}
        for a in self._analyses.values():
            key = a.aspect.value
            aspect_counts[key] = aspect_counts.get(key, 0) + 1

        confidence_dist: Dict[str, int] = {}
        for a in self._analyses.values():
            key = a.confidence.value
            confidence_dist[key] = confidence_dist.get(key, 0) + 1

        risk_dist: Dict[str, int] = {}
        for s in self._suggestions.values():
            key = s.risk_level
            risk_dist[key] = risk_dist.get(key, 0) + 1

        return {
            "initialized": True,
            "subsystem": "game_design_reasoner",
            "total_analyses": self._total_analyses,
            "total_suggestions": self._total_suggestions,
            "total_simulations": self._total_simulations,
            "stored_analyses": len(self._analyses),
            "stored_parameters": len(self._parameters),
            "stored_curves": len(self._curves),
            "stored_suggestions": len(self._suggestions),
            "analysis_by_aspect": aspect_counts,
            "confidence_distribution": confidence_dist,
            "suggestion_risk_distribution": risk_dist,
            "optimization_history_entries": len(self._optimization_history),
        }

    # ---- Internal Analysis Methods ----

    def _analyze_aspect(self,
                       aspect: DesignAspect,
                       game_state: Dict[str, Any]) -> DesignAnalysis:
        """Analyzes a single design aspect."""
        analyzer = {
            DesignAspect.BALANCE: self._analyze_balance,
            DesignAspect.DIFFICULTY: self._analyze_difficulty_internal,
            DesignAspect.PROGRESSION: self._analyze_progression,
            DesignAspect.ECONOMY: self._analyze_economy,
            DesignAspect.PACING: self._analyze_pacing,
            DesignAspect.ACCESSIBILITY: self._analyze_accessibility,
            DesignAspect.REPLAYABILITY: self._analyze_replayability,
            DesignAspect.ENGAGEMENT: self._analyze_engagement,
        }

        analyzer_fn = analyzer.get(aspect, self._analyze_balance)
        return analyzer_fn(game_state)

    def _analyze_balance(self, game_state: Dict[str, Any]) -> DesignAnalysis:
        options = game_state.get("options_count", 3)
        viable = game_state.get("viable_options", max(1, options - 1))
        viability_ratio = viable / max(options, 1)
        current_state = {"options": options, "viable_options": viable, "ratio": viability_ratio}
        analysis = "Balance is acceptable" if viability_ratio > 0.6 else "Balance needs improvement"
        suggestions = []
        if viability_ratio <= 0.6:
            suggestions.append("Reduce dominance of top-tier options")
            suggestions.append("Increase viability of underperforming choices")
        confidence = ConfidenceLevel.HIGH if options > 0 else ConfidenceLevel.LOW
        return DesignAnalysis(
            aspect=DesignAspect.BALANCE,
            current_state=current_state,
            analysis=analysis,
            suggestions=suggestions,
            confidence=confidence,
        )

    def _analyze_difficulty_internal(self, game_state: Dict[str, Any]) -> DesignAnalysis:
        difficulty = game_state.get("difficulty", 0.5)
        ramp_smoothness = game_state.get("ramp_smoothness", 0.7)
        current_state = {"difficulty": difficulty, "ramp_smoothness": ramp_smoothness}
        analysis = "Difficulty curve is well-shaped"
        suggestions = []
        if ramp_smoothness < 0.5:
            analysis = "Difficulty spikes detected"
            suggestions.append("Smooth difficulty transitions between levels")
        confidence = ConfidenceLevel.MEDIUM if ramp_smoothness > 0.5 else ConfidenceLevel.HIGH
        return DesignAnalysis(
            aspect=DesignAspect.DIFFICULTY,
            current_state=current_state,
            analysis=analysis,
            suggestions=suggestions,
            confidence=confidence,
        )

    def _analyze_progression(self, game_state: Dict[str, Any]) -> DesignAnalysis:
        unlocks_per_hour = game_state.get("unlocks_per_hour", 4)
        total_levels = game_state.get("total_levels", 50)
        current_state = {"unlocks_per_hour": unlocks_per_hour, "total_levels": total_levels}
        analysis = "Progression pacing is suitable"
        suggestions = []
        if unlocks_per_hour < 2:
            analysis = "Progression feels too slow"
            suggestions.append("Increase reward frequency early in the game")
        elif unlocks_per_hour > 8:
            analysis = "Too many unlocks may overwhelm players"
            suggestions.append("Space unlocks more evenly across play sessions")
        confidence = ConfidenceLevel.HIGH
        return DesignAnalysis(
            aspect=DesignAspect.PROGRESSION,
            current_state=current_state,
            analysis=analysis,
            suggestions=suggestions,
            confidence=confidence,
        )

    def _analyze_economy(self, game_state: Dict[str, Any]) -> DesignAnalysis:
        sink_faucet_ratio = game_state.get("sink_faucet_ratio", 0.7)
        inflation = game_state.get("inflation", 0.05)
        current_state = {"sink_faucet_ratio": sink_faucet_ratio, "inflation": inflation}
        analysis = "Economy appears stable"
        suggestions = []
        if sink_faucet_ratio < 0.4:
            analysis = "Insufficient currency sinks detected"
            suggestions.append("Add more spending opportunities")
            suggestions.append("Introduce optional sinks")
        elif sink_faucet_ratio > 0.9:
            analysis = "Economy feels too restrictive"
            suggestions.append("Reduce sink costs or increase faucet rates")
        confidence = ConfidenceLevel.MEDIUM
        return DesignAnalysis(
            aspect=DesignAspect.ECONOMY,
            current_state=current_state,
            analysis=analysis,
            suggestions=suggestions,
            confidence=confidence,
        )

    def _analyze_pacing(self, game_state: Dict[str, Any]) -> DesignAnalysis:
        action_density = game_state.get("action_density", 0.6)
        rest_periods = game_state.get("rest_periods", 3)
        current_state = {"action_density": action_density, "rest_periods": rest_periods}
        analysis = "Pacing rhythm is well-balanced"
        suggestions = []
        if action_density > 0.8:
            analysis = "Pacing is too intense — risk of player fatigue"
            suggestions.append("Introduce more quiet moments between action sequences")
        elif action_density < 0.3:
            analysis = "Pacing is too slow — risk of boredom"
            suggestions.append("Increase encounter frequency or shorten downtime")
        confidence = ConfidenceLevel.MEDIUM
        return DesignAnalysis(
            aspect=DesignAspect.PACING,
            current_state=current_state,
            analysis=analysis,
            suggestions=suggestions,
            confidence=confidence,
        )

    def _analyze_accessibility(self, game_state: Dict[str, Any]) -> DesignAnalysis:
        difficulty_presets = game_state.get("difficulty_presets", 1)
        input_options = game_state.get("input_options", 2)
        current_state = {"difficulty_presets": difficulty_presets, "input_options": input_options}
        analysis = "Accessibility features are adequate"
        suggestions = []
        if difficulty_presets < 2:
            suggestions.append("Add easy/normal/hard difficulty options")
        if input_options < 3:
            suggestions.append("Support additional input methods")
        confidence = ConfidenceLevel.HIGH if difficulty_presets >= 2 else ConfidenceLevel.MEDIUM
        return DesignAnalysis(
            aspect=DesignAspect.ACCESSIBILITY,
            current_state=current_state,
            analysis=analysis,
            suggestions=suggestions,
            confidence=confidence,
        )

    def _analyze_replayability(self, game_state: Dict[str, Any]) -> DesignAnalysis:
        procedural_content = game_state.get("procedural_content", 0.3)
        branching_paths = game_state.get("branching_paths", 2)
        current_state = {"procedural_content": procedural_content, "branching_paths": branching_paths}
        analysis = "Moderate replayability detected"
        suggestions = []
        if procedural_content < 0.4:
            suggestions.append("Add procedural generation for varied replay experiences")
        if branching_paths < 3:
            suggestions.append("Introduce more narrative or gameplay branches")
        confidence = ConfidenceLevel.MEDIUM
        return DesignAnalysis(
            aspect=DesignAspect.REPLAYABILITY,
            current_state=current_state,
            analysis=analysis,
            suggestions=suggestions,
            confidence=confidence,
        )

    def _analyze_engagement(self, game_state: Dict[str, Any]) -> DesignAnalysis:
        flow_state_uptime = game_state.get("flow_state_uptime", 0.6)
        retention_rate = game_state.get("retention_rate", 0.5)
        current_state = {"flow_state_uptime": flow_state_uptime, "retention_rate": retention_rate}
        analysis = "Player engagement is at acceptable levels"
        suggestions = []
        if flow_state_uptime < 0.5:
            analysis = "Players spend too little time in flow state"
            suggestions.append("Adjust challenge-to-skill ratio for better flow")
            suggestions.append("Reduce interruptions during gameplay")
        if retention_rate < 0.4:
            suggestions.append("Add stronger session-to-session retention hooks")
        confidence = ConfidenceLevel.HIGH if retention_rate > 0.5 else ConfidenceLevel.MEDIUM
        return DesignAnalysis(
            aspect=DesignAspect.ENGAGEMENT,
            current_state=current_state,
            analysis=analysis,
            suggestions=suggestions,
            confidence=confidence,
        )

    def _fit_curve(self,
                  data_points: List[Tuple[float, float]],
                  target_shape: str) -> Dict[str, Any]:
        """Fits a mathematical model to the data points."""
        xs = [p[0] for p in data_points]
        ys = [p[1] for p in data_points]
        n = len(xs)
        n = max(n, 2)

        if target_shape == "linear":
            sum_x = sum(xs)
            sum_y = sum(ys)
            sum_xy = sum(x * y for x, y in zip(xs, ys))
            sum_x2 = sum(x * x for x in xs)
            denom = n * sum_x2 - sum_x * sum_x
            slope = 0.0
            if denom != 0:
                slope = (n * sum_xy - sum_x * sum_y) / denom
            intercept = (sum_y - slope * sum_x) / n
            return {
                "curve_type": "linear",
                "formula": f"y = {slope:.4f}x + {intercept:.4f}",
                "params": {"slope": slope, "intercept": intercept},
            }

        elif target_shape == "exponential":
            if min(ys) <= 0:
                y_offset = abs(min(ys)) + 1
                ys_adj = [y + y_offset for y in ys]
            else:
                ys_adj = list(ys)
                y_offset = 0
            log_ys = [math.log(max(y, 1e-10)) for y in ys_adj]
            sum_x = sum(xs)
            sum_ly = sum(log_ys)
            sum_xly = sum(x * ly for x, ly in zip(xs, log_ys))
            sum_x2 = sum(x * x for x in xs)
            denom = n * sum_x2 - sum_x * sum_x
            log_base = 0.05
            if denom != 0:
                log_base = (n * sum_xly - sum_x * sum_ly) / denom
            base = math.exp(log_base)
            log_a = (sum_ly - log_base * sum_x) / n
            a = math.exp(log_a) - y_offset
            return {
                "curve_type": "exponential",
                "formula": f"y = {a:.4f} * {base:.4f}^x",
                "params": {"base": base, "a": a},
            }

        elif target_shape == "logarithmic":
            if min(xs) <= -1:
                x_offset = abs(min(xs)) + 1
            else:
                x_offset = 1
            log_xs = [math.log(max(x + x_offset, 1e-10)) for x in xs]
            sum_lx = sum(log_xs)
            sum_y = sum(ys)
            sum_lxy = sum(lx * y for lx, y in zip(log_xs, ys))
            sum_lx2 = sum(lx * lx for lx in log_xs)
            denom = n * sum_lx2 - sum_lx * sum_lx
            multiplier = 1.0
            if denom != 0:
                multiplier = (n * sum_lxy - sum_lx * sum_y) / denom
            intercept_y = (sum_y - multiplier * sum_lx) / n
            return {
                "curve_type": "logarithmic",
                "formula": f"y = {multiplier:.4f} * ln(x + {x_offset:.1f}) + {intercept_y:.4f}",
                "params": {"multiplier": multiplier, "offset": x_offset},
            }

        elif target_shape == "s_curve":
            max_y = max(ys) if ys else 100.0
            midpoint = sum(xs) / n if n else 5.0
            steepness = 0.1
            if max(xs) - min(xs) > 0:
                steepness = 1.0 / (max(xs) - min(xs)) if max(xs) != min(xs) else 0.1
                steepness = max(0.01, min(steepness, 0.5))
            return {
                "curve_type": "s_curve",
                "formula": f"y = {max_y:.2f} / (1 + e^({-steepness:.4f}(x - {midpoint:.2f})))",
                "params": {"max_value": max_y, "midpoint": midpoint, "steepness": steepness},
            }
        else:
            return {
                "curve_type": target_shape,
                "formula": f"y = {ys[0]} (constant for {target_shape})",
                "params": {"base": ys[0] if ys else 1.0},
            }

    def _calc_impact(self, param_name: str, system_name: str) -> float:
        """Calculates the impact score of a parameter."""
        high_impact = {"base_damage", "health_pool", "xp_curve_exponent", "cooldown_base"}
        medium_impact = {"critical_chance", "attack_speed", "armor_value", "unlock_frequency",
                        "currency_drop_rate", "skill_range", "duration_base"}
        if param_name in high_impact:
            return 0.9
        elif param_name in medium_impact:
            return 0.6
        return 0.35

    def _calc_inflation_trend(self, currency_history: List[float]) -> float:
        """Calculates inflation/deflation trend from currency history."""
        if len(currency_history) < 3:
            return 0.0
        recent = currency_history[-3:]
        earlier = currency_history[:3]
        avg_recent = sum(recent) / max(len(recent), 1)
        avg_earlier = sum(earlier) / max(len(earlier), 1)
        if avg_earlier > 0:
            return (avg_recent - avg_earlier) / avg_earlier
        return 0.0

    def _calc_economy_balance(self,
                             total_generated: float,
                             total_spent: float,
                             history: List[float]) -> float:
        """Calculates economy balance score."""
        if total_generated <= 0:
            return 0.5
        ratio = total_spent / total_generated
        ideal_ratio = 0.7
        ratio_score = 1.0 - min(abs(ratio - ideal_ratio) / ideal_ratio, 1.0)

        if len(history) < 2:
            return ratio_score
        min_val = min(history)
        max_val = max(history)
        if max_val <= 0:
            return ratio_score
        stability = 1.0 - (max_val - min_val) / max_val
        return ratio_score * 0.6 + stability * 0.4


def get_game_reasoner() -> GameDesignReasoner:
    """Get the singleton instance of the game design reasoner."""
    return GameDesignReasoner.get_instance()