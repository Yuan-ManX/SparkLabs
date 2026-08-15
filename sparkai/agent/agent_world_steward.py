"""
SparkLabs Agent - World Stewardship Cycle

The capstone orchestration that ties every proactive capability into one
self-directed loop. The steward:

  1. forecasts the world        (anticipate drift / problems)
  2. discovers candidate goals  (what needs doing?)
  3. synthesizes remediation     (turn each goal into concrete candidate
                                  actions the engine can execute)
  4. reasons counterfactually    (sandbox-evaluate each candidate)
  5. gates by autonomy           (calibrated confidence decides act/review/halt)
  6. commits the policy          (apply the strongest approved action to the
                                  live world)
  7. records calibration         (predicted vs actual -> reliability profile)
  8. emits a cycle report        (a compact audit trail of the whole pass)

This is the AI-native essence: the agent does not wait for instructions.
It continuously tends the world through the full reasoning pipeline,
fusing observation, simulation, decision, execution, and learning into
one coherent cycle.

    forecast -> discover -> synthesize -> reason -> gate -> commit -> calibrate
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StewardCycleStep:
    """A single phase outcome within a stewardship cycle."""

    phase: str = ""
    status: str = "skipped"  # ok | skipped | error | halted | review
    detail: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "status": self.status,
            "detail": self.detail,
            "data": self.data,
        }


@dataclass
class StewardCycleReport:
    """The compact audit trail of one stewardship cycle."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    goal_title: str = ""
    goal_trigger: str = ""
    forecast_stable: Optional[bool] = None
    forecast_problems: List[str] = field(default_factory=list)
    candidates_evaluated: int = 0
    recommended_score: float = 0.0
    autonomy_level: str = "halt"
    committed: bool = False
    commit_summary: str = ""
    actual_score: Optional[float] = None
    predicted_score: Optional[float] = None
    calibration_delta: Optional[float] = None
    steps: List[StewardCycleStep] = field(default_factory=list)
    outcome: str = "noop"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": round((self.finished_at - self.started_at) * 1000, 1),
            "goal_title": self.goal_title,
            "goal_trigger": self.goal_trigger,
            "forecast_stable": self.forecast_stable,
            "forecast_problems": self.forecast_problems,
            "candidates_evaluated": self.candidates_evaluated,
            "recommended_score": round(self.recommended_score, 4),
            "autonomy_level": self.autonomy_level,
            "committed": self.committed,
            "commit_summary": self.commit_summary,
            "actual_score": (
                round(self.actual_score, 4)
                if self.actual_score is not None else None
            ),
            "predicted_score": (
                round(self.predicted_score, 4)
                if self.predicted_score is not None else None
            ),
            "calibration_delta": (
                round(self.calibration_delta, 4)
                if self.calibration_delta is not None else None
            ),
            "steps": [s.to_dict() for s in self.steps],
            "outcome": self.outcome,
        }


class WorldSteward:
    """
    Orchestrates the full proactive pipeline into a single cycle.

    The steward is deliberately stateless across cycles: every cycle reads
    the live world fresh and writes its report to history. This keeps the
    loop safe to trigger at any time (manually, on a schedule, or from the
    editor) without hidden state drift.
    """

    # Maps a goal trigger to concrete candidate actions the engine can
    # execute. Each candidate is a sandbox-evaluable operation that the
    # counterfactual reasoner will score before anything is committed.
    _REMEDIATION: Dict[str, List[Dict[str, Any]]] = {
        "empty_scene": [
            {
                "description": "Spawn a starter entity to populate the empty scene",
                "action_type": "create_entity",
                "params": {"name": "Starter", "properties": {"score": 10}},
            },
            {
                "description": "Spawn a second entity to enable interaction",
                "action_type": "create_entity",
                "params": {"name": "Companion", "properties": {"score": 8}},
            },
        ],
        "sparse_scene": [
            {
                "description": "Add a complementary entity to the sparse scene",
                "action_type": "create_entity",
                "params": {"name": "Ally", "properties": {"score": 12}},
            },
        ],
        "score_spread": [
            {
                "description": "Lift the lowest score toward the mean",
                "action_type": "set_property",
                "params": {"key": "score", "value": 10},
            },
        ],
        "negative_average": [
            {
                "description": "Introduce a positive-score entity to lift the average",
                "action_type": "create_entity",
                "params": {"name": "Booster", "properties": {"score": 25}},
            },
        ],
        "low_variety": [
            {
                "description": "Introduce a distinct entity type for variety",
                "action_type": "create_entity",
                "params": {"name": "Scout", "properties": {"score": 7}, "tags": ["scout"]},
            },
        ],
        "inert_world": [
            {
                "description": "Assign a meaningful score to make dynamics observable",
                "action_type": "set_property",
                "params": {"key": "score", "value": 15},
            },
        ],
    }

    def __init__(self, max_history: int = 30) -> None:
        self._history: List[StewardCycleReport] = []
        self._max_history = max_history

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_cycle(self, agent: Any, engine: Any = None) -> StewardCycleReport:
        """
        Execute one full stewardship cycle and return the audit report.

        The cycle is the proactive heartbeat: forecast, discover, synthesize,
        reason, gate, commit, calibrate. Every phase is wrapped so a single
        phase failure never aborts the whole cycle.
        """
        report = StewardCycleReport()
        report.steps.append(StewardCycleStep(
            phase="init", status="ok", detail="stewardship cycle started",
        ))

        # Resolve the engine once; reuse across all phases.
        if engine is None:
            engine = agent._resolve_engine() if hasattr(agent, "_resolve_engine") else None
        if engine is None:
            report.outcome = "no_engine"
            report.steps.append(StewardCycleStep(
                phase="engine", status="error", detail="no live engine available",
            ))
            report.finished_at = time.time()
            self._record(report)
            return report

        # Phase 1: Forecast
        self._phase_forecast(agent, engine, report)

        # Phase 2: Discover goals
        self._phase_discover(agent, engine, report)

        # If no goals were discovered, the world is healthy this cycle.
        if not report.goal_trigger:
            report.outcome = "healthy"
            report.finished_at = time.time()
            self._record(report)
            return report

        # Phase 3: Synthesize remediation candidates
        candidates = self._phase_synthesize(report, engine)

        # Phase 4: Counterfactual reasoning
        if not self._phase_reason(agent, engine, candidates, report):
            report.finished_at = time.time()
            self._record(report)
            return report

        # Phase 5: Autonomy gate
        if not self._phase_gate(agent, report):
            report.finished_at = time.time()
            self._record(report)
            return report

        # Phase 6: Commit
        self._phase_commit(agent, engine, report)

        # Phase 7: Calibration is recorded inside commit_policy_action;
        # surface the delta here for the report.
        self._phase_calibrate(agent, report)

        report.finished_at = time.time()
        self._record(report)
        return report

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in list(reversed(self._history[-limit:]))]

    def get_statistics(self) -> Dict[str, Any]:
        if not self._history:
            return {"total_cycles": 0}
        recent = self._history[-20:]
        committed = sum(1 for r in recent if r.committed)
        return {
            "total_cycles": len(self._history),
            "recent_committed": committed,
            "recent_commit_rate": round(committed / len(recent), 3),
            "recent_avg_actual_score": (
                round(
                    sum(r.actual_score for r in recent if r.actual_score is not None)
                    / max(1, sum(1 for r in recent if r.actual_score is not None)),
                    4,
                )
            ),
            "recent_outcomes": {
                o: sum(1 for r in recent if r.outcome == o)
                for o in ("healthy", "committed", "halted", "review", "error", "noop")
                if any(r.outcome == o for r in recent)
            },
        }

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def _phase_forecast(self, agent: Any, engine: Any, report: StewardCycleReport) -> None:
        try:
            forecast = agent.forecast_world(engine=engine, horizon_frames=60)
            report.forecast_stable = forecast.get("stable")
            report.forecast_problems = forecast.get("predicted_problems", [])
            report.steps.append(StewardCycleStep(
                phase="forecast",
                status="ok",
                detail=forecast.get("drift_summary", ""),
                data={
                    "stable": report.forecast_stable,
                    "problems": report.forecast_problems,
                    "opportunities": forecast.get("predicted_opportunities", []),
                },
            ))
        except Exception as exc:
            report.steps.append(StewardCycleStep(
                phase="forecast", status="error", detail=str(exc),
            ))

    def _phase_discover(self, agent: Any, engine: Any, report: StewardCycleReport) -> None:
        try:
            goals = agent.discover_goals(engine=engine, max_goals=6)
            if goals:
                top = goals[0]
                report.goal_title = top.get("title", "")
                report.goal_trigger = top.get("trigger", "")
            report.steps.append(StewardCycleStep(
                phase="discover",
                status="ok" if goals else "skipped",
                detail=f"{len(goals)} goal(s) discovered; top='{report.goal_title}'",
                data={"goals": goals[:3]},
            ))
        except Exception as exc:
            report.steps.append(StewardCycleStep(
                phase="discover", status="error", detail=str(exc),
            ))

    def _phase_synthesize(
        self, report: StewardCycleReport, engine: Any,
    ) -> List[Dict[str, Any]]:
        """
        Generate remediation candidates dynamically from the live world state.

        Instead of a static lookup table, the steward reads the actual entities,
        scores, and scene composition to synthesize multiple varied candidates
        tailored to the specific condition. This gives the counterfactual
        reasoner meaningful alternatives to evaluate in the sandbox, making
        the steward's decision creative rather than mechanical.
        """
        candidates = self._synthesize_dynamic(report.goal_trigger, engine)
        if not candidates:
            # Fall back to the static baseline if dynamic synthesis yields nothing.
            candidates = list(self._REMEDIATION.get(report.goal_trigger, []))
        report.steps.append(StewardCycleStep(
            phase="synthesize",
            status="ok" if candidates else "skipped",
            detail=(
                f"{len(candidates)} candidate(s) synthesized for trigger "
                f"'{report.goal_trigger}' (dynamic)"
            ),
            data={"candidates": candidates},
        ))
        return candidates

    # ------------------------------------------------------------------
    # Dynamic candidate synthesis
    # ------------------------------------------------------------------

    def _read_world(self, engine: Any) -> List[Dict[str, Any]]:
        """Flatten every entity across every scene into a compact list."""
        entities: List[Dict[str, Any]] = []
        for scene in getattr(engine, "_scenes", {}).values():
            for entity in scene.entities.values():
                try:
                    score = float(entity.properties.get("score", 0.0))
                except (TypeError, ValueError):
                    score = 0.0
                entities.append({
                    "id": entity.id,
                    "name": entity.name,
                    "score": score,
                    "scene_id": scene.id,
                })
        return entities

    def _synthesize_dynamic(
        self, trigger: str, engine: Any,
    ) -> List[Dict[str, Any]]:
        """
        Produce context-aware candidates by reading the live world state.

        Each trigger type yields multiple varied approaches so the
        counterfactual reasoner has genuine alternatives to score:
          - a targeted approach (fix the specific problem),
          - an additive approach (introduce something new),
          - a blanket approach (apply broadly).

        All candidates use the same action semantics the counterfactual
        reasoner and policy committer already understand, so no new
        action types are introduced.
        """
        entities = self._read_world(engine)
        if trigger == "inert_world":
            return self._synth_inert_world(entities)
        if trigger == "empty_scene":
            return self._synth_empty_scene(entities)
        if trigger == "sparse_scene":
            return self._synth_sparse_scene(entities)
        if trigger == "score_spread":
            return self._synth_score_spread(entities)
        if trigger == "negative_average":
            return self._synth_negative_average(entities)
        if trigger == "low_variety":
            return self._synth_low_variety(entities)
        # Rule-violation triggers: generate remediation based on the
        # underlying rule type (e.g. rule_max_entities, rule_min_score).
        if trigger.startswith("rule_"):
            return self._synth_rule_violation(trigger, entities, engine)
        return []

    def _synth_rule_violation(
        self, trigger: str, entities: List[Dict[str, Any]], engine: Any,
    ) -> List[Dict[str, Any]]:
        """
        Generate remediation candidates for a world-rule violation.

        Maps the rule type to a concrete fix: max_entities -> remove
        excess, min_score -> raise the floor, score_spread -> pull
        outliers, max_duplicates -> remove duplicates.
        """
        rule_type = trigger.replace("rule_", "", 1)
        cands: List[Dict[str, Any]] = []
        if rule_type == "max_entities":
            # Remove the most recently added entity to get under the limit.
            if entities:
                cands.append({
                    "description": f"Remove excess entity '{entities[-1]['name']}' to satisfy the max-entities rule",
                    "action_type": "destroy_entity",
                    "params": {"target": entities[-1]["id"]},
                })
        elif rule_type == "min_score":
            # Raise the lowest-scoring entity above the floor.
            if entities:
                lowest = min(entities, key=lambda e: e["score"])
                cands.append({
                    "description": f"Raise low-score entity '{lowest['name']}' from {lowest['score']:.1f} to 0",
                    "action_type": "set_property",
                    "params": {"key": "score", "value": 0, "target": lowest["id"]},
                })
        elif rule_type == "score_spread":
            # Pull the outlier toward the mean.
            if entities:
                scores = [e["score"] for e in entities]
                mean_score = sum(scores) / len(scores)
                outlier = max(entities, key=lambda e: abs(e["score"] - mean_score))
                cands.append({
                    "description": f"Pull outlier '{outlier['name']}' toward the mean ({mean_score:.1f})",
                    "action_type": "set_property",
                    "params": {"key": "score", "value": round(mean_score, 1), "target": outlier["id"]},
                })
        elif rule_type == "max_duplicates":
            # Remove one of the duplicate-named entities.
            names: Dict[str, List[Dict[str, Any]]] = {}
            for e in entities:
                names.setdefault(e["name"], []).append(e)
            for name, group in names.items():
                if len(group) > 1:
                    cands.append({
                        "description": f"Remove a duplicate '{name}' to satisfy the variety rule",
                        "action_type": "destroy_entity",
                        "params": {"target": group[-1]["id"]},
                    })
                    break
        elif rule_type == "score_range":
            # Clamp the out-of-range entity to the nearest bound.
            if entities:
                cands.append({
                    "description": "Clamp out-of-range scores to the allowed bounds",
                    "action_type": "set_property",
                    "params": {"key": "score", "value": 0},
                })
        return cands

    def _synth_inert_world(
        self, entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate candidates to activate an all-zero-score world."""
        cands: List[Dict[str, Any]] = []
        # Targeted: assign a score to the first entity.
        if entities:
            cands.append({
                "description": f"Assign score 15 to '{entities[0]['name']}' to spark dynamics",
                "action_type": "set_property",
                "params": {"key": "score", "value": 15, "target": entities[0]["id"]},
            })
        # Additive: introduce a catalyst entity with a high score.
        cands.append({
            "description": "Introduce a Catalyst entity with score 20 to activate the world",
            "action_type": "create_entity",
            "params": {"name": "Catalyst", "properties": {"score": 20}},
        })
        # Blanket: assign a moderate score to make all entities participate.
        cands.append({
            "description": "Set score 10 across the board to make every entity active",
            "action_type": "set_property",
            "params": {"key": "score", "value": 10},
        })
        return cands

    def _synth_empty_scene(
        self, entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate candidates to populate an empty scene."""
        return [
            {
                "description": "Spawn a Hero entity to anchor the empty scene",
                "action_type": "create_entity",
                "params": {"name": "Hero", "properties": {"score": 12}},
            },
            {
                "description": "Spawn a Companion entity to enable interaction",
                "action_type": "create_entity",
                "params": {"name": "Companion", "properties": {"score": 8}},
            },
            {
                "description": "Spawn an Environment entity to provide context",
                "action_type": "create_entity",
                "params": {"name": "Landmark", "properties": {"score": 5}},
            },
        ]

    def _synth_sparse_scene(
        self, entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate candidates to diversify a single-entity scene."""
        existing_name = entities[0]["name"] if entities else "Entity"
        return [
            {
                "description": f"Add an Ally to complement the lone '{existing_name}'",
                "action_type": "create_entity",
                "params": {"name": "Ally", "properties": {"score": 10}},
            },
            {
                "description": f"Add a Rival to create tension with '{existing_name}'",
                "action_type": "create_entity",
                "params": {"name": "Rival", "properties": {"score": -5}},
            },
        ]

    def _synth_score_spread(
        self, entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate candidates to rebalance a wide score spread."""
        if not entities:
            return []
        scores = [e["score"] for e in entities]
        mean_score = sum(scores) / len(scores)
        # Find the outlier furthest from the mean.
        outlier = max(entities, key=lambda e: abs(e["score"] - mean_score))
        cands: List[Dict[str, Any]] = []
        # Targeted: pull the outlier toward the mean.
        cands.append({
            "description": (
                f"Pull outlier '{outlier['name']}' (score {outlier['score']:.0f}) "
                f"toward the mean ({mean_score:.1f})"
            ),
            "action_type": "set_property",
            "params": {
                "key": "score",
                "value": round(mean_score, 1),
                "target": outlier["id"],
            },
        })
        # Additive: introduce a balancer entity at the mean.
        cands.append({
            "description": f"Introduce a Balancer entity at the mean score ({mean_score:.1f})",
            "action_type": "create_entity",
            "params": {
                "name": "Balancer",
                "properties": {"score": round(mean_score, 1)},
            },
        })
        return cands

    def _synth_negative_average(
        self, entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate candidates to lift a negative-average world."""
        cands: List[Dict[str, Any]] = []
        # Additive: introduce a high-score entity to lift the average.
        cands.append({
            "description": "Introduce a Booster entity with score 30 to lift the average",
            "action_type": "create_entity",
            "params": {"name": "Booster", "properties": {"score": 30}},
        })
        # Targeted: boost the lowest-scoring entity.
        if entities:
            lowest = min(entities, key=lambda e: e["score"])
            cands.append({
                "description": f"Boost lowest entity '{lowest['name']}' from {lowest['score']:.0f} to 10",
                "action_type": "set_property",
                "params": {"key": "score", "value": 10, "target": lowest["id"]},
            })
        return cands

    def _synth_low_variety(
        self, entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate candidates to introduce entity variety."""
        # Identify the most common name to avoid duplicating it.
        names: Dict[str, int] = {}
        for e in entities:
            names[e["name"]] = names.get(e["name"], 0) + 1
        common = max(names, key=names.get) if names else ""
        cands: List[Dict[str, Any]] = []
        cands.append({
            "description": f"Introduce a Scout entity (distinct from common '{common}')",
            "action_type": "create_entity",
            "params": {"name": "Scout", "properties": {"score": 7}, "tags": ["scout"]},
        })
        cands.append({
            "description": "Introduce a Guardian entity for structural variety",
            "action_type": "create_entity",
            "params": {"name": "Guardian", "properties": {"score": 14}, "tags": ["guardian"]},
        })
        return cands

    def _phase_reason(
        self,
        agent: Any,
        engine: Any,
        candidates: List[Dict[str, Any]],
        report: StewardCycleReport,
    ) -> bool:
        if not candidates:
            report.outcome = "noop"
            return False
        try:
            decision = agent.reason_counterfactually(
                candidates=candidates,
                goal=report.goal_title,
                frames=45,
            )
            report.candidates_evaluated = len(decision.get("candidates", []))
            report.predicted_score = decision.get("recommended_score")
            report.steps.append(StewardCycleStep(
                phase="reason",
                status="ok",
                detail=f"recommended_score={report.predicted_score}",
                data={"decision_id": decision.get("id")},
            ))
            return True
        except Exception as exc:
            report.steps.append(StewardCycleStep(
                phase="reason", status="error", detail=str(exc),
            ))
            report.outcome = "error"
            return False

    def _phase_gate(self, agent: Any, report: StewardCycleReport) -> bool:
        try:
            raw = report.predicted_score if report.predicted_score is not None else 0.5
            assessment = agent.assess_autonomy(
                raw_confidence=float(raw),
                description=f"stewardship cycle for '{report.goal_title}'",
            )
            report.autonomy_level = assessment.get("autonomy_level", "halt")
            report.steps.append(StewardCycleStep(
                phase="gate",
                status=report.autonomy_level,
                detail=(
                    f"raw={assessment.get('raw_confidence')} "
                    f"calibrated={assessment.get('calibrated_confidence')} "
                    f"level={report.autonomy_level}"
                ),
                data=assessment,
            ))
            if report.autonomy_level == "halt":
                report.outcome = "halted"
                return False
            return True
        except Exception as exc:
            report.steps.append(StewardCycleStep(
                phase="gate", status="error", detail=str(exc),
            ))
            report.autonomy_level = "halt"
            report.outcome = "error"
            return False

    def _phase_commit(self, agent: Any, engine: Any, report: StewardCycleReport) -> None:
        try:
            # Commit the recommended candidate of the decision we just made.
            record = agent.commit_latest_decision(goal=report.goal_title)
            if record is None:
                report.steps.append(StewardCycleStep(
                    phase="commit", status="skipped",
                    detail="no recommended candidate to commit",
                ))
                report.outcome = "noop"
                return
            commit_data = record
            report.committed = True
            report.commit_summary = commit_data.get("summary", "")
            report.actual_score = commit_data.get("actual_score")
            # predicted_score already set from the reasoning phase.
            if report.predicted_score is not None and report.actual_score is not None:
                report.calibration_delta = report.actual_score - report.predicted_score
            report.outcome = "committed"
            report.steps.append(StewardCycleStep(
                phase="commit",
                status="ok",
                detail=report.commit_summary,
                data=commit_data,
            ))
        except Exception as exc:
            report.steps.append(StewardCycleStep(
                phase="commit", status="error", detail=str(exc),
            ))
            report.outcome = "error"

    def _phase_calibrate(self, agent: Any, report: StewardCycleReport) -> None:
        try:
            # The commit already recorded calibration internally; surface
            # the current profile so the report carries the agent's
            # post-cycle reliability snapshot.
            profile = agent.get_calibration()
            report.steps.append(StewardCycleStep(
                phase="calibrate",
                status="ok",
                detail=(
                    f"samples={profile.get('profile', {}).get('sample_count', 0)} "
                    f"multiplier={profile.get('profile', {}).get('confidence_multiplier', 1.0)}"
                ),
                data=profile,
            ))
        except Exception as exc:
            report.steps.append(StewardCycleStep(
                phase="calibrate", status="error", detail=str(exc),
            ))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _record(self, report: StewardCycleReport) -> None:
        self._history.append(report)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        logger.info(
            "Stewardship cycle %s: outcome=%s goal='%s' committed=%s",
            report.id[:8], report.outcome, report.goal_title, report.committed,
        )


_instance: Optional[WorldSteward] = None


def get_world_steward() -> WorldSteward:
    """Return the process-wide WorldSteward singleton."""
    global _instance
    if _instance is None:
        _instance = WorldSteward()
    return _instance
