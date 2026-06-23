"""
SparkLabs Agent - Counterfactual Simulator

Counterfactual reasoning engine that lets agents evaluate what-if scenarios
for game design decisions before committing to them. The simulator applies
proposed changes to a snapshot of game state, runs heuristic simulation
steps, scores outcomes across multiple metrics, detects side effects, and
produces actionable recommendations.

Architecture:
  CounterfactualSimulatorEngine (Singleton)
    |-- Scenario Builder (define what-if scenarios over state snapshots)
    |-- Change Applier (apply parameter, entity, rule, and event changes)
    |-- Heuristic Simulator (propagate effects across N simulation steps)
    |-- Metric Scorer (score engagement, balance, coherence, economy, performance)
    |-- Side Effect Detector (flag unexpected interactions between changes)
    |-- Comparison Reporter (rank multiple scenarios by metric outcomes)

Core Capabilities:
  - create_scenario: Define a counterfactual scenario over a base state snapshot
  - add_change: Attach a proposed change to an existing scenario
  - run_scenario: Execute heuristic simulation and produce a scored result
  - compare_scenarios: Rank multiple scenarios across selected metrics
  - evaluate_impact: Score a single metric for a scenario
  - recommend_action: Decide whether to apply, revise, or reject changes
  - rollback_scenario: Discard results and restore draft status
  - get_scenario: Retrieve a scenario by id
  - list_scenarios: List scenarios with optional status filter
  - get_stats: Engine-wide operational statistics

Usage:
    engine = get_counterfactual_simulator()
    scenario = engine.create_scenario(
        name="Reduce boss health",
        description="Test lowering boss HP by 30 percent",
        base_state_snapshot={"parameters": {"boss_hp": 1000, "player_dps": 50}},
    )
    engine.add_change(
        scenario_id=scenario.scenario_id,
        change_type=ChangeType.PARAMETER_MODIFICATION,
        target_entity="boss",
        property_path="parameters.boss_hp",
        original_value=1000,
        counterfactual_value=700,
        description="Lower boss HP by 30 percent",
    )
    result = engine.run_scenario(scenario.scenario_id, simulation_steps=20)
    report = engine.compare_scenarios(
        [scenario.scenario_id],
        metrics=[ComparisonMetric.DIFFICULTY_BALANCE],
    )
"""

from __future__ import annotations

import copy
import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ScenarioStatus(Enum):
    """Lifecycle status of a counterfactual scenario."""
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChangeType(Enum):
    """Categories of counterfactual changes applied to a state snapshot."""
    PARAMETER_MODIFICATION = "parameter_modification"
    ENTITY_REMOVAL = "entity_removal"
    ENTITY_ADDITION = "entity_addition"
    RULE_CHANGE = "rule_change"
    EVENT_INJECTION = "event_injection"


class OutcomeValence(Enum):
    """Overall valence of a scenario outcome."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class ComparisonMetric(Enum):
    """Metrics used to compare and rank scenarios."""
    PLAYER_ENGAGEMENT = "player_engagement"
    DIFFICULTY_BALANCE = "difficulty_balance"
    NARRATIVE_COHERENCE = "narrative_coherence"
    ECONOMY_STABILITY = "economy_stability"
    PERFORMANCE_IMPACT = "performance_impact"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CounterfactualChange:
    """A single proposed change within a counterfactual scenario."""
    change_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    change_type: ChangeType = ChangeType.PARAMETER_MODIFICATION
    target_entity: str = ""
    property_path: str = ""
    original_value: Any = None
    counterfactual_value: Any = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type.value,
            "target_entity": self.target_entity,
            "property_path": self.property_path,
            "original_value": self.original_value,
            "counterfactual_value": self.counterfactual_value,
            "description": self.description,
        }


@dataclass
class ScenarioResult:
    """Outcome of running a counterfactual scenario."""
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scenario_id: str = ""
    metric_scores: Dict[str, float] = field(default_factory=dict)
    outcome_valence: OutcomeValence = OutcomeValence.NEUTRAL
    summary: str = ""
    side_effects: List[str] = field(default_factory=list)
    recommendation: str = ""
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "scenario_id": self.scenario_id,
            "metric_scores": {k: round(v, 4) for k, v in self.metric_scores.items()},
            "outcome_valence": self.outcome_valence.value,
            "summary": self.summary,
            "side_effects": list(self.side_effects),
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
        }


@dataclass
class CounterfactualScenario:
    """A complete counterfactual scenario with changes and results."""
    scenario_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    base_state_snapshot: Dict[str, Any] = field(default_factory=dict)
    changes: List[CounterfactualChange] = field(default_factory=list)
    status: ScenarioStatus = ScenarioStatus.DRAFT
    results: Dict[str, ScenarioResult] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "base_state_keys": list(self.base_state_snapshot.keys()),
            "change_count": len(self.changes),
            "changes": [c.to_dict() for c in self.changes],
            "status": self.status.value,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class ComparisonReport:
    """Report comparing multiple scenarios across selected metrics."""
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scenario_ids: List[str] = field(default_factory=list)
    metric_comparisons: Dict[str, Dict[str, float]] = field(default_factory=dict)
    winner_scenario_id: str = ""
    analysis: str = ""
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "scenario_ids": list(self.scenario_ids),
            "metric_comparisons": {
                m: {sid: round(v, 4) for sid, v in scores.items()}
                for m, scores in self.metric_comparisons.items()
            },
            "winner_scenario_id": self.winner_scenario_id,
            "analysis": self.analysis,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# CounterfactualSimulatorEngine - Singleton
# ---------------------------------------------------------------------------

class CounterfactualSimulatorEngine:
    """Counterfactual reasoning engine for evaluating what-if game design scenarios.

    Applies proposed changes to a deep copy of a base state snapshot, runs
    heuristic simulation steps that propagate effects through parameters,
    entities, rules, and events, then scores each comparison metric and
    detects side effects caused by unexpected interactions between changes.
    """

    _instance: Optional["CounterfactualSimulatorEngine"] = None
    _lock = threading.RLock()

    _MAX_SCENARIOS = 1000
    _MAX_CHANGES_PER_SCENARIO = 100
    _MAX_SIMULATION_STEPS = 200
    _DEFAULT_SIMULATION_STEPS = 25

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._scenarios: Dict[str, CounterfactualScenario] = {}
            self._comparison_reports: Dict[str, ComparisonReport] = {}
            self._total_scenarios_created: int = 0
            self._total_changes_added: int = 0
            self._total_runs: int = 0
            self._total_comparisons: int = 0
            self._total_rollbacks: int = 0

    # ------------------------------------------------------------------
    # Scenario Management
    # ------------------------------------------------------------------

    def create_scenario(
        self,
        name: str,
        description: str,
        base_state_snapshot: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CounterfactualScenario:
        """Create a new counterfactual scenario over a base state snapshot."""
        with self._lock:
            self._enforce_scenario_limit()
            scenario = CounterfactualScenario(
                name=name,
                description=description,
                base_state_snapshot=copy.deepcopy(base_state_snapshot),
                metadata=dict(metadata) if metadata else {},
            )
            self._scenarios[scenario.scenario_id] = scenario
            self._total_scenarios_created += 1
            return scenario

    def add_change(
        self,
        scenario_id: str,
        change_type: ChangeType,
        target_entity: str,
        property_path: str,
        original_value: Any,
        counterfactual_value: Any,
        description: str = "",
    ) -> Optional[CounterfactualChange]:
        """Attach a proposed change to an existing scenario."""
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                return None
            if scenario.status == ScenarioStatus.RUNNING:
                return None
            if len(scenario.changes) >= self._MAX_CHANGES_PER_SCENARIO:
                return None

            change = CounterfactualChange(
                change_type=change_type,
                target_entity=target_entity,
                property_path=property_path,
                original_value=original_value,
                counterfactual_value=counterfactual_value,
                description=description,
            )
            scenario.changes.append(change)
            self._total_changes_added += 1
            # Reset to draft so a re-run is required after editing changes
            if scenario.status == ScenarioStatus.COMPLETED:
                scenario.status = ScenarioStatus.DRAFT
                scenario.completed_at = None
            return change

    def get_scenario(self, scenario_id: str) -> Optional[CounterfactualScenario]:
        """Retrieve a scenario by id."""
        with self._lock:
            return self._scenarios.get(scenario_id)

    def list_scenarios(
        self, status_filter: Optional[ScenarioStatus] = None
    ) -> List[Dict[str, Any]]:
        """List scenarios with an optional status filter."""
        with self._lock:
            scenarios = list(self._scenarios.values())
            if status_filter is not None:
                scenarios = [s for s in scenarios if s.status == status_filter]
            scenarios.sort(key=lambda s: s.created_at, reverse=True)
            return [
                {
                    "scenario_id": s.scenario_id,
                    "name": s.name,
                    "description": s.description,
                    "status": s.status.value,
                    "change_count": len(s.changes),
                    "result_count": len(s.results),
                    "created_at": s.created_at,
                    "completed_at": s.completed_at,
                }
                for s in scenarios
            ]

    def rollback_scenario(self, scenario_id: str) -> bool:
        """Discard results and restore a scenario to draft status."""
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                return False
            if scenario.status not in (
                ScenarioStatus.COMPLETED,
                ScenarioStatus.FAILED,
                ScenarioStatus.RUNNING,
            ):
                return False
            scenario.results.clear()
            scenario.status = ScenarioStatus.DRAFT
            scenario.completed_at = None
            self._total_rollbacks += 1
            return True

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def run_scenario(
        self, scenario_id: str, simulation_steps: int = 25
    ) -> Optional[ScenarioResult]:
        """Run heuristic simulation for a scenario and return a scored result."""
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                return None

            steps = max(1, min(simulation_steps, self._MAX_SIMULATION_STEPS))
            scenario.status = ScenarioStatus.RUNNING
            scenario.completed_at = None

            try:
                # Apply changes to a deep copy of the base state
                working_state = copy.deepcopy(scenario.base_state_snapshot)
                application_log = self._apply_changes(working_state, scenario.changes)

                # Run heuristic simulation steps
                trajectory: List[Dict[str, Any]] = []
                for step in range(steps):
                    step_state = self._simulate_step(
                        working_state, scenario.changes, step, steps
                    )
                    trajectory.append(step_state)

                # Score each metric based on the final state and trajectory
                metric_scores: Dict[str, float] = {}
                for metric in ComparisonMetric:
                    metric_scores[metric.value] = self._score_metric(
                        metric, working_state, trajectory, scenario.changes
                    )

                # Detect side effects from unexpected interactions
                side_effects = self._detect_side_effects(
                    working_state,
                    scenario.base_state_snapshot,
                    scenario.changes,
                    trajectory,
                )

                # Determine overall valence
                outcome_valence = self._classify_valence(metric_scores, side_effects)

                # Generate recommendation
                recommendation = self._build_recommendation(
                    metric_scores, side_effects, scenario.changes
                )

                summary = self._build_summary(
                    scenario, metric_scores, side_effects, application_log, steps
                )

                result = ScenarioResult(
                    scenario_id=scenario_id,
                    metric_scores=metric_scores,
                    outcome_valence=outcome_valence,
                    summary=summary,
                    side_effects=side_effects,
                    recommendation=recommendation,
                )
                scenario.results[result.result_id] = result
                scenario.status = ScenarioStatus.COMPLETED
                scenario.completed_at = _time_module.time
                self._total_runs += 1
                return result
            except Exception as exc:
                scenario.status = ScenarioStatus.FAILED
                scenario.completed_at = _time_module.time
                failed_result = ScenarioResult(
                    scenario_id=scenario_id,
                    outcome_valence=OutcomeValence.NEGATIVE,
                    summary=f"Simulation failed: {exc}",
                    side_effects=[],
                    recommendation="Reject: simulation encountered an error.",
                )
                scenario.results[failed_result.result_id] = failed_result
                return failed_result

    def evaluate_impact(
        self, scenario_id: str, metric: ComparisonMetric
    ) -> float:
        """Evaluate a single metric for a scenario, running a lightweight check."""
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                return 0.0

            # If a completed result exists, return the stored score
            latest = self._latest_result(scenario)
            if latest is not None and metric.value in latest.metric_scores:
                return latest.metric_scores[metric.value]

            # Otherwise compute a quick estimate without a full run
            working_state = copy.deepcopy(scenario.base_state_snapshot)
            self._apply_changes(working_state, scenario.changes)
            trajectory = [
                self._simulate_step(working_state, scenario.changes, 0, 5)
                for _ in range(5)
            ]
            return self._score_metric(
                metric, working_state, trajectory, scenario.changes
            )

    def compare_scenarios(
        self,
        scenario_ids: List[str],
        metrics: Optional[List[ComparisonMetric]] = None,
    ) -> Optional[ComparisonReport]:
        """Compare multiple scenarios across selected metrics and pick a winner."""
        with self._lock:
            if not scenario_ids:
                return None

            selected_metrics = metrics if metrics else list(ComparisonMetric)
            scenarios: List[CounterfactualScenario] = []
            for sid in scenario_ids:
                scenario = self._scenarios.get(sid)
                if scenario is None:
                    return None
                scenarios.append(scenario)

            # Ensure each scenario has a result; run if missing
            for scenario in scenarios:
                if not scenario.results:
                    self.run_scenario(scenario.scenario_id)

            metric_comparisons: Dict[str, Dict[str, float]] = {}
            for metric in selected_metrics:
                metric_comparisons[metric.value] = {}
                for scenario in scenarios:
                    latest = self._latest_result(scenario)
                    if latest and metric.value in latest.metric_scores:
                        score = latest.metric_scores[metric.value]
                    else:
                        score = self.evaluate_impact(scenario.scenario_id, metric)
                    metric_comparisons[metric.value][scenario.scenario_id] = score

            # Pick winner by average score across metrics
            winner_id = self._select_winner(
                scenarios, metric_comparisons, selected_metrics
            )
            analysis = self._build_comparison_analysis(
                scenarios, metric_comparisons, selected_metrics, winner_id
            )

            report = ComparisonReport(
                scenario_ids=list(scenario_ids),
                metric_comparisons=metric_comparisons,
                winner_scenario_id=winner_id,
                analysis=analysis,
            )
            self._comparison_reports[report.report_id] = report
            self._total_comparisons += 1
            return report

    def recommend_action(self, scenario_id: str) -> Dict[str, Any]:
        """Recommend whether to apply, revise, or reject a scenario's changes."""
        with self._lock:
            scenario = self._scenarios.get(scenario_id)
            if scenario is None:
                return {
                    "scenario_id": scenario_id,
                    "decision": "reject",
                    "reason": "Scenario not found.",
                    "confidence": 0.0,
                }

            latest = self._latest_result(scenario)
            if latest is None:
                return {
                    "scenario_id": scenario_id,
                    "decision": "revise",
                    "reason": "Scenario has not been simulated yet. Run it before deciding.",
                    "confidence": 0.0,
                }

            scores = list(latest.metric_scores.values())
            avg_score = sum(scores) / max(1, len(scores))
            min_score = min(scores) if scores else 0.0
            side_effect_count = len(latest.side_effects)

            decision = "revise"
            reason = ""
            confidence = 0.5

            if avg_score >= 0.75 and min_score >= 0.5 and side_effect_count <= 1:
                decision = "apply"
                reason = (
                    "Strong overall metrics with minimal side effects. "
                    "Safe to apply the counterfactual changes."
                )
                confidence = min(1.0, avg_score)
            elif avg_score < 0.35 or min_score < 0.2 or side_effect_count >= 4:
                decision = "reject"
                reason = (
                    "Weak metrics or too many side effects. "
                    "Reject the proposed changes."
                )
                confidence = min(1.0, 1.0 - avg_score)
            else:
                decision = "revise"
                reason = (
                    "Mixed outcomes. Adjust the changes to address weak metrics "
                    "and side effects before applying."
                )
                confidence = 0.5 + abs(avg_score - 0.5)

            return {
                "scenario_id": scenario_id,
                "decision": decision,
                "reason": reason,
                "confidence": round(confidence, 4),
                "avg_metric_score": round(avg_score, 4),
                "min_metric_score": round(min_score, 4),
                "side_effect_count": side_effect_count,
                "outcome_valence": latest.outcome_valence.value,
            }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return engine-wide operational statistics."""
        with self._lock:
            status_counts: Dict[str, int] = {}
            change_type_counts: Dict[str, int] = {}
            valence_counts: Dict[str, int] = {}
            for scenario in self._scenarios.values():
                status_counts[scenario.status.value] = (
                    status_counts.get(scenario.status.value, 0) + 1
                )
                for change in scenario.changes:
                    change_type_counts[change.change_type.value] = (
                        change_type_counts.get(change.change_type.value, 0) + 1
                    )
                for result in scenario.results.values():
                    valence_counts[result.outcome_valence.value] = (
                        valence_counts.get(result.outcome_valence.value, 0) + 1
                    )

            return {
                "total_scenarios": len(self._scenarios),
                "total_scenarios_created": self._total_scenarios_created,
                "total_changes_added": self._total_changes_added,
                "total_runs": self._total_runs,
                "total_comparisons": self._total_comparisons,
                "total_rollbacks": self._total_rollbacks,
                "comparison_reports": len(self._comparison_reports),
                "status_distribution": status_counts,
                "change_type_distribution": change_type_counts,
                "valence_distribution": valence_counts,
                "available_statuses": [s.value for s in ScenarioStatus],
                "available_change_types": [c.value for c in ChangeType],
                "available_metrics": [m.value for m in ComparisonMetric],
                "available_valences": [v.value for v in OutcomeValence],
            }

    # ------------------------------------------------------------------
    # Internal: Change Application
    # ------------------------------------------------------------------

    def _apply_changes(
        self,
        state: Dict[str, Any],
        changes: List[CounterfactualChange],
    ) -> List[str]:
        """Apply each change to the working state and return a log of actions."""
        log: List[str] = []
        for change in changes:
            try:
                if change.change_type == ChangeType.PARAMETER_MODIFICATION:
                    self._set_path(state, change.property_path, change.counterfactual_value)
                    log.append(
                        f"Set {change.property_path} to {change.counterfactual_value}"
                    )
                elif change.change_type == ChangeType.ENTITY_REMOVAL:
                    removed = self._remove_path(state, change.property_path)
                    if removed:
                        log.append(f"Removed entity at {change.property_path}")
                    else:
                        log.append(f"No entity found at {change.property_path}")
                elif change.change_type == ChangeType.ENTITY_ADDITION:
                    self._set_path(state, change.property_path, change.counterfactual_value)
                    log.append(f"Added entity at {change.property_path}")
                elif change.change_type == ChangeType.RULE_CHANGE:
                    rules = state.setdefault("rules", {})
                    rules[change.property_path] = change.counterfactual_value
                    log.append(f"Updated rule {change.property_path}")
                elif change.change_type == ChangeType.EVENT_INJECTION:
                    events = state.setdefault("events", [])
                    events.append(
                        {
                            "target": change.target_entity,
                            "property": change.property_path,
                            "value": change.counterfactual_value,
                            "step": 0,
                        }
                    )
                    log.append(f"Injected event for {change.target_entity}")
            except Exception as exc:
                log.append(f"Failed to apply change {change.change_id}: {exc}")
        return log

    def _set_path(self, state: Dict[str, Any], path: str, value: Any) -> None:
        """Set a value at a dot-separated path, creating intermediate dicts."""
        if not path:
            return
        keys = path.split(".")
        current = state
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def _get_path(self, state: Dict[str, Any], path: str) -> Any:
        """Retrieve a value at a dot-separated path."""
        if not path:
            return None
        keys = path.split(".")
        current = state
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    def _remove_path(self, state: Dict[str, Any], path: str) -> bool:
        """Remove a value at a dot-separated path."""
        if not path:
            return False
        keys = path.split(".")
        current = state
        for key in keys[:-1]:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        if isinstance(current, dict) and keys[-1] in current:
            del current[keys[-1]]
            return True
        return False

    # ------------------------------------------------------------------
    # Internal: Heuristic Simulation
    # ------------------------------------------------------------------

    def _simulate_step(
        self,
        state: Dict[str, Any],
        changes: List[CounterfactualChange],
        step: int,
        total_steps: int,
    ) -> Dict[str, Any]:
        """Run a single heuristic simulation step and return a state snapshot."""
        progress = (step + 1) / max(1, total_steps)

        parameters = state.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}
            state["parameters"] = parameters

        entities = state.get("entities", {})
        if not isinstance(entities, dict):
            entities = {}
            state["entities"] = entities

        events = state.get("events", [])
        if not isinstance(events, list):
            events = []
            state["events"] = events

        # Propagate parameter perturbations: each numeric parameter drifts
        # slightly toward an equilibrium derived from the simulation progress.
        for key, value in list(parameters.items()):
            if isinstance(value, (int, float)):
                drift = 0.02 * math.sin(step * 0.5 + (hash(key) % 7))
                equilibrium = value * (1.0 - 0.05 * progress)
                parameters[key] = value + (equilibrium - value) * 0.1 + drift

        # Process queued events and decay their influence over a few steps
        remaining_events: List[Dict[str, Any]] = []
        for event in events:
            event_age = step - event.get("step", 0)
            if event_age < 3:
                prop = event.get("property", "")
                if prop:
                    current_val = self._get_path(state, prop)
                    if isinstance(current_val, (int, float)):
                        decay = 1.0 / (1.0 + event_age)
                        adjustment = event.get("value", 0) * decay * 0.1
                        self._set_path(state, prop, current_val + adjustment)
                remaining_events.append(event)
        state["events"] = remaining_events

        # Track entity count and aggregate load for performance scoring
        entity_count = len(entities)
        load = sum(1 for v in entities.values() if isinstance(v, dict))

        return {
            "step": step,
            "progress": round(progress, 4),
            "parameter_count": len(parameters),
            "entity_count": entity_count,
            "active_events": len(remaining_events),
            "load": load,
        }

    # ------------------------------------------------------------------
    # Internal: Metric Scoring
    # ------------------------------------------------------------------

    def _score_metric(
        self,
        metric: ComparisonMetric,
        state: Dict[str, Any],
        trajectory: List[Dict[str, Any]],
        changes: List[CounterfactualChange],
    ) -> float:
        """Score a single metric in [0, 1] based on state and trajectory."""
        if metric == ComparisonMetric.PLAYER_ENGAGEMENT:
            return self._score_engagement(state, trajectory, changes)
        if metric == ComparisonMetric.DIFFICULTY_BALANCE:
            return self._score_difficulty(state, trajectory, changes)
        if metric == ComparisonMetric.NARRATIVE_COHERENCE:
            return self._score_narrative(state, trajectory, changes)
        if metric == ComparisonMetric.ECONOMY_STABILITY:
            return self._score_economy(state, trajectory, changes)
        if metric == ComparisonMetric.PERFORMANCE_IMPACT:
            return self._score_performance(state, trajectory, changes)
        return 0.5

    def _score_engagement(
        self,
        state: Dict[str, Any],
        trajectory: List[Dict[str, Any]],
        changes: List[CounterfactualChange],
    ) -> float:
        """Score player engagement from variety, event activity, and change diversity."""
        parameters = state.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}

        # Variety: more distinct numeric parameters raises engagement
        numeric_values = [
            v for v in parameters.values() if isinstance(v, (int, float))
        ]
        variety = min(1.0, len(numeric_values) / 10.0)

        # Event activity: active events during simulation suggest dynamic gameplay
        avg_events = (
            sum(t.get("active_events", 0) for t in trajectory)
            / max(1, len(trajectory))
        )
        event_activity = min(1.0, avg_events / 5.0)

        # Change diversity: multiple change types suggest richer content shifts
        change_types = len({c.change_type for c in changes})
        diversity = min(1.0, change_types / 5.0)

        # Penalize excessive entity removal which can reduce engagement
        removals = sum(
            1 for c in changes if c.change_type == ChangeType.ENTITY_REMOVAL
        )
        removal_penalty = min(0.4, removals * 0.1)

        score = 0.4 * variety + 0.3 * event_activity + 0.3 * diversity - removal_penalty
        return max(0.0, min(1.0, score))

    def _score_difficulty(
        self,
        state: Dict[str, Any],
        trajectory: List[Dict[str, Any]],
        changes: List[CounterfactualChange],
    ) -> float:
        """Score difficulty balance by proximity of key parameters to a mid-range band."""
        parameters = state.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}

        # Gather numeric parameters and assess how close they are to a mid band
        numeric_values = [
            v for v in parameters.values()
            if isinstance(v, (int, float)) and v != 0
        ]
        if not numeric_values:
            return 0.5

        # Normalize each value against the max magnitude and score closeness to 0.5
        max_abs = max(abs(v) for v in numeric_values)
        if max_abs == 0:
            return 0.5

        normalized = [abs(v) / max_abs for v in numeric_values]
        deviations = [abs(n - 0.5) for n in normalized]
        avg_deviation = sum(deviations) / len(deviations)
        balance = max(0.0, 1.0 - avg_deviation * 2.0)

        # Reward parameter modifications that move values closer to the band
        mod_bonus = 0.0
        for change in changes:
            if change.change_type == ChangeType.PARAMETER_MODIFICATION:
                orig = change.original_value
                new = change.counterfactual_value
                if (
                    isinstance(orig, (int, float))
                    and isinstance(new, (int, float))
                    and max_abs > 0
                ):
                    orig_norm = abs(orig) / max_abs
                    new_norm = abs(new) / max_abs
                    if abs(new_norm - 0.5) < abs(orig_norm - 0.5):
                        mod_bonus += 0.05
        mod_bonus = min(0.2, mod_bonus)

        # Penalize rule changes that can destabilize difficulty
        rule_changes = sum(
            1 for c in changes if c.change_type == ChangeType.RULE_CHANGE
        )
        rule_penalty = min(0.3, rule_changes * 0.1)

        score = balance + mod_bonus - rule_penalty
        return max(0.0, min(1.0, score))

    def _score_narrative(
        self,
        state: Dict[str, Any],
        trajectory: List[Dict[str, Any]],
        changes: List[CounterfactualChange],
    ) -> float:
        """Score narrative coherence from consistency of entities and events."""
        entities = state.get("entities", {})
        if not isinstance(entities, dict):
            entities = {}

        # Coherence drops when entities are removed (plot threads cut)
        entity_count = len(entities)
        entity_factor = min(1.0, entity_count / 10.0)

        # Event injections can support or disrupt narrative depending on count
        injections = sum(
            1 for c in changes if c.change_type == ChangeType.EVENT_INJECTION
        )
        if injections <= 2:
            event_factor = 0.6 + 0.2 * injections
        else:
            event_factor = max(0.2, 1.0 - 0.15 * (injections - 2))

        # Additions strengthen narrative when they introduce new threads
        additions = sum(
            1 for c in changes if c.change_type == ChangeType.ENTITY_ADDITION
        )
        addition_bonus = min(0.2, additions * 0.05)

        # Removals weaken narrative continuity
        removals = sum(
            1 for c in changes if c.change_type == ChangeType.ENTITY_REMOVAL
        )
        removal_penalty = min(0.4, removals * 0.1)

        score = 0.5 * entity_factor + 0.5 * event_factor + addition_bonus - removal_penalty
        return max(0.0, min(1.0, score))

    def _score_economy(
        self,
        state: Dict[str, Any],
        trajectory: List[Dict[str, Any]],
        changes: List[CounterfactualChange],
    ) -> float:
        """Score economy stability from variance of numeric parameters over time."""
        parameters = state.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}

        numeric_values = [
            v for v in parameters.values() if isinstance(v, (int, float))
        ]
        if not numeric_values:
            return 0.5

        # Stability is inverse to the spread of numeric values
        mean_val = sum(numeric_values) / len(numeric_values)
        if mean_val == 0:
            variance = sum(v * v for v in numeric_values) / len(numeric_values)
        else:
            variance = sum((v - mean_val) ** 2 for v in numeric_values) / len(numeric_values)
        std = math.sqrt(variance)
        cv = std / max(abs(mean_val), 0.001)  # coefficient of variation
        stability = max(0.0, 1.0 - cv)

        # Track trajectory load variance as a secondary stability indicator
        loads = [t.get("load", 0) for t in trajectory]
        if loads:
            load_mean = sum(loads) / len(loads)
            load_var = sum((l - load_mean) ** 2 for l in loads) / len(loads)
            load_stability = max(
                0.0, 1.0 - math.sqrt(load_var) / max(load_mean, 1.0)
            )
        else:
            load_stability = 0.5

        # Penalize event injections that inject volatility
        injections = sum(
            1 for c in changes if c.change_type == ChangeType.EVENT_INJECTION
        )
        injection_penalty = min(0.3, injections * 0.08)

        score = 0.6 * stability + 0.4 * load_stability - injection_penalty
        return max(0.0, min(1.0, score))

    def _score_performance(
        self,
        state: Dict[str, Any],
        trajectory: List[Dict[str, Any]],
        changes: List[CounterfactualChange],
    ) -> float:
        """Score performance impact from entity count and trajectory load."""
        entities = state.get("entities", {})
        if not isinstance(entities, dict):
            entities = {}

        entity_count = len(entities)
        # Performance is high when entity count is low
        entity_score = max(0.0, 1.0 - entity_count / 50.0)

        # Average load across the trajectory
        avg_load = (
            sum(t.get("load", 0) for t in trajectory) / max(1, len(trajectory))
        )
        load_score = max(0.0, 1.0 - avg_load / 30.0)

        # Additions hurt performance; removals help
        additions = sum(
            1 for c in changes if c.change_type == ChangeType.ENTITY_ADDITION
        )
        removals = sum(
            1 for c in changes if c.change_type == ChangeType.ENTITY_REMOVAL
        )
        net_entity_impact = (removals - additions) * 0.05

        score = 0.5 * entity_score + 0.5 * load_score + net_entity_impact
        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Internal: Side Effect Detection
    # ------------------------------------------------------------------

    def _detect_side_effects(
        self,
        final_state: Dict[str, Any],
        base_state: Dict[str, Any],
        changes: List[CounterfactualChange],
        trajectory: List[Dict[str, Any]],
    ) -> List[str]:
        """Detect unexpected interactions caused by the applied changes."""
        side_effects: List[str] = []

        base_params = base_state.get("parameters", {})
        if not isinstance(base_params, dict):
            base_params = {}
        final_params = final_state.get("parameters", {})
        if not isinstance(final_params, dict):
            final_params = {}

        # Detect parameters that shifted significantly without direct modification
        directly_modified_paths = {
            c.property_path
            for c in changes
            if c.change_type == ChangeType.PARAMETER_MODIFICATION
        }
        for key, base_val in base_params.items():
            if not isinstance(base_val, (int, float)):
                continue
            final_val = final_params.get(key)
            if not isinstance(final_val, (int, float)):
                continue
            path = f"parameters.{key}"
            if path in directly_modified_paths:
                continue
            if base_val == 0:
                relative_change = abs(final_val)
            else:
                relative_change = abs(final_val - base_val) / abs(base_val)
            if relative_change > 0.2:
                side_effects.append(
                    f"Parameter '{key}' shifted by {relative_change:.0%} "
                    f"without direct modification."
                )

        # Detect entity loss not caused by explicit removal
        base_entities = base_state.get("entities", {})
        if not isinstance(base_entities, dict):
            base_entities = {}
        final_entities = final_state.get("entities", {})
        if not isinstance(final_entities, dict):
            final_entities = {}
        removed_paths = {
            c.property_path
            for c in changes
            if c.change_type == ChangeType.ENTITY_REMOVAL
        }
        for key in base_entities:
            if key not in final_entities and f"entities.{key}" not in removed_paths:
                side_effects.append(
                    f"Entity '{key}' disappeared without an explicit removal change."
                )

        # Detect load spikes during simulation
        loads = [t.get("load", 0) for t in trajectory]
        if loads:
            avg_load = sum(loads) / len(loads)
            max_load = max(loads)
            if max_load > avg_load * 2 and max_load > 5:
                side_effects.append(
                    f"Load spike to {max_load} (avg {avg_load:.1f}) during simulation."
                )

        # Detect cascading event accumulation
        event_counts = [t.get("active_events", 0) for t in trajectory]
        if event_counts and max(event_counts) > 5:
            side_effects.append(
                f"Event accumulation reached {max(event_counts)} active events."
            )

        # Detect conflicting rule changes
        rule_changes = [
            c for c in changes if c.change_type == ChangeType.RULE_CHANGE
        ]
        if len(rule_changes) > 2:
            side_effects.append(
                f"{len(rule_changes)} rule changes may conflict with each other."
            )

        return side_effects

    # ------------------------------------------------------------------
    # Internal: Valence, Recommendation, Summary
    # ------------------------------------------------------------------

    def _classify_valence(
        self,
        metric_scores: Dict[str, float],
        side_effects: List[str],
    ) -> OutcomeValence:
        """Classify the overall valence of a scenario outcome."""
        if not metric_scores:
            return OutcomeValence.NEUTRAL

        scores = list(metric_scores.values())
        avg = sum(scores) / len(scores)
        positive_count = sum(1 for s in scores if s >= 0.6)
        negative_count = sum(1 for s in scores if s < 0.4)

        if side_effects and len(side_effects) >= 3:
            if avg >= 0.6:
                return OutcomeValence.MIXED
            return OutcomeValence.NEGATIVE

        if positive_count == len(scores) and avg >= 0.7:
            return OutcomeValence.POSITIVE
        if negative_count >= len(scores) * 0.6:
            return OutcomeValence.NEGATIVE
        if positive_count > 0 and negative_count > 0:
            return OutcomeValence.MIXED
        return OutcomeValence.NEUTRAL

    def _build_recommendation(
        self,
        metric_scores: Dict[str, float],
        side_effects: List[str],
        changes: List[CounterfactualChange],
    ) -> str:
        """Build a textual recommendation for the scenario."""
        scores = list(metric_scores.values())
        avg = sum(scores) / max(1, len(scores))
        min_metric = (
            min(metric_scores.items(), key=lambda x: x[1])
            if metric_scores
            else ("", 0.0)
        )

        if avg >= 0.75 and len(side_effects) <= 1:
            return (
                "Apply: metrics are strong and side effects are limited. "
                "Proceed with the counterfactual changes."
            )
        if avg < 0.35 or len(side_effects) >= 4:
            return (
                "Reject: metrics are weak or side effects are too numerous. "
                "Do not apply the counterfactual changes."
            )
        parts = ["Revise: outcomes are mixed."]
        if min_metric[1] < 0.4:
            parts.append(
                f"Improve the weakest metric '{min_metric[0]}' (score {min_metric[1]:.2f})."
            )
        if side_effects:
            parts.append(f"Address {len(side_effects)} detected side effect(s).")
        return " ".join(parts)

    def _build_summary(
        self,
        scenario: CounterfactualScenario,
        metric_scores: Dict[str, float],
        side_effects: List[str],
        application_log: List[str],
        steps: int,
    ) -> str:
        """Build a human-readable summary of the simulation run."""
        avg = sum(metric_scores.values()) / max(1, len(metric_scores))
        top_metric = (
            max(metric_scores.items(), key=lambda x: x[1])
            if metric_scores
            else ("", 0.0)
        )
        weak_metric = (
            min(metric_scores.items(), key=lambda x: x[1])
            if metric_scores
            else ("", 0.0)
        )
        return (
            f"Scenario '{scenario.name}' simulated over {steps} step(s) with "
            f"{len(scenario.changes)} change(s). "
            f"Average metric score: {avg:.2f}. "
            f"Strongest metric: {top_metric[0]} ({top_metric[1]:.2f}). "
            f"Weakest metric: {weak_metric[0]} ({weak_metric[1]:.2f}). "
            f"Side effects detected: {len(side_effects)}. "
            f"Changes applied: {len(application_log)}."
        )

    # ------------------------------------------------------------------
    # Internal: Comparison Helpers
    # ------------------------------------------------------------------

    def _select_winner(
        self,
        scenarios: List[CounterfactualScenario],
        metric_comparisons: Dict[str, Dict[str, float]],
        metrics: List[ComparisonMetric],
    ) -> str:
        """Select the scenario with the highest average score across metrics."""
        if not scenarios:
            return ""
        best_id = ""
        best_avg = -1.0
        for scenario in scenarios:
            total = 0.0
            count = 0
            for metric in metrics:
                score = metric_comparisons.get(metric.value, {}).get(
                    scenario.scenario_id, 0.0
                )
                total += score
                count += 1
            avg = total / max(1, count)
            if avg > best_avg:
                best_avg = avg
                best_id = scenario.scenario_id
        return best_id

    def _build_comparison_analysis(
        self,
        scenarios: List[CounterfactualScenario],
        metric_comparisons: Dict[str, Dict[str, float]],
        metrics: List[ComparisonMetric],
        winner_id: str,
    ) -> str:
        """Build a textual analysis of the comparison across scenarios."""
        if not scenarios:
            return "No scenarios to compare."
        winner = next(
            (s for s in scenarios if s.scenario_id == winner_id), None
        )
        winner_name = winner.name if winner else "Unknown"
        lines = [
            f"Compared {len(scenarios)} scenario(s) across {len(metrics)} metric(s).",
            f"Winner: '{winner_name}' (scenario_id={winner_id}).",
        ]
        for metric in metrics:
            scores = metric_comparisons.get(metric.value, {})
            if not scores:
                continue
            best_sid = max(scores, key=lambda sid: scores[sid])
            worst_sid = min(scores, key=lambda sid: scores[sid])
            best_name = next(
                (s.name for s in scenarios if s.scenario_id == best_sid), best_sid
            )
            worst_name = next(
                (s.name for s in scenarios if s.scenario_id == worst_sid), worst_sid
            )
            lines.append(
                f"Metric '{metric.value}': best '{best_name}' "
                f"({scores[best_sid]:.2f}), worst '{worst_name}' "
                f"({scores[worst_sid]:.2f})."
            )
        return " ".join(lines)

    # ------------------------------------------------------------------
    # Internal: Utilities
    # ------------------------------------------------------------------

    def _latest_result(
        self, scenario: CounterfactualScenario
    ) -> Optional[ScenarioResult]:
        """Return the most recent result for a scenario."""
        if not scenario.results:
            return None
        return max(
            scenario.results.values(),
            key=lambda r: r.timestamp,
        )

    def _enforce_scenario_limit(self) -> None:
        """Evict the oldest scenarios when the capacity is reached."""
        if len(self._scenarios) < self._MAX_SCENARIOS:
            return
        oldest = sorted(
            self._scenarios.values(),
            key=lambda s: s.created_at,
        )
        excess = len(self._scenarios) - self._MAX_SCENARIOS + 1
        for scenario in oldest[:excess]:
            self._scenarios.pop(scenario.scenario_id, None)


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_counterfactual_simulator() -> CounterfactualSimulatorEngine:
    """Get or create the global CounterfactualSimulatorEngine singleton."""
    return CounterfactualSimulatorEngine()
