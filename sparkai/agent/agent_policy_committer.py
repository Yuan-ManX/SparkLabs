"""
SparkLabs Agent - Policy Committer

Closes the AI-native decision loop. After the Agent reasons about a set
of candidate actions in the sandbox (counterfactual simulation), the
Policy Committer applies the strongest candidate to the LIVE world and
records the observable outcome. This fuses AI planning with the engine's
predictive dynamics and the editor's scene-editing operations into one
closed loop:

    observe -> simulate -> commit -> verify -> learn

Because every commit is also measured with the same metric used during
sandbox simulation, the committer can compare the sandbox prediction
against the actual result, giving the Agent a fidelity signal that tells
it how trustworthy its own reasoning is.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PolicyCommitRecord:
    """The observable result of committing an action to the live world."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal: str = ""
    description: str = ""
    action_type: str = "simulate"
    params: Dict[str, Any] = field(default_factory=dict)
    source: str = "direct"
    decision_id: str = ""
    recommended: bool = False

    added_entities: int = 0
    removed_entities: int = 0
    modified_entities: int = 0
    score_delta: float = 0.0
    actual_score: float = 0.0
    predicted_score: Optional[float] = None
    prediction_delta: float = 0.0

    applied_to: List[str] = field(default_factory=list)
    summary: str = ""
    applied_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "description": self.description,
            "action_type": self.action_type,
            "params": self.params,
            "source": self.source,
            "decision_id": self.decision_id,
            "recommended": self.recommended,
            "added_entities": self.added_entities,
            "removed_entities": self.removed_entities,
            "modified_entities": self.modified_entities,
            "score_delta": round(self.score_delta, 4),
            "actual_score": round(self.actual_score, 4),
            "predicted_score": (
                round(self.predicted_score, 4)
                if self.predicted_score is not None else None
            ),
            "prediction_delta": round(self.prediction_delta, 4),
            "applied_to": self.applied_to,
            "summary": self.summary,
            "applied_at": self.applied_at,
        }


class PolicyCommitter:
    """
    Applies agent-chosen actions to the live engine and records outcomes.

    Reuses the counterfactual reasoner as the single source of truth for
    action semantics (create/destroy/set-property/add-component), so a
    sandbox-evaluated candidate and a live commit behave identically.
    Every commit is measured and retained for audit and self-correction.
    """

    def __init__(self, max_history: int = 50) -> None:
        self._history: List[PolicyCommitRecord] = []
        self._max_history = max_history

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def commit(
        self,
        engine: Any,
        action_type: str,
        params: Optional[Dict[str, Any]] = None,
        goal: str = "",
        description: str = "",
        source: str = "direct",
        decision_id: str = "",
        predicted_score: Optional[float] = None,
    ) -> PolicyCommitRecord:
        """
        Apply an action to the live world and record the observable result.

        The world is not rolled back here: this is the real commit. The
        entity delta and score movement are measured using the same metric
        as sandbox simulation so predictions can be compared to reality.
        """
        from sparkai.agent.agent_counterfactual_reasoner import (
            CounterfactualCandidate,
        )

        candidate = CounterfactualCandidate(
            description=description or action_type,
            action_type=action_type,
            params=dict(params or {}),
        )

        before = self._flatten(engine)
        before_ids = set(before)

        self._apply_candidate(engine, candidate)

        after = self._flatten(engine)
        after_ids = set(after)

        added = sorted(after_ids - before_ids)
        removed = sorted(before_ids - after_ids)
        modified = sorted(
            eid for eid in (before_ids & after_ids)
            if self._entity_changed(before[eid], after[eid])
        )

        score_delta = 0.0
        for eid in before_ids & after_ids:
            b = before[eid]["properties"].get("score", 0.0)
            a = after[eid]["properties"].get("score", 0.0)
            try:
                score_delta += float(a) - float(b)
            except (TypeError, ValueError):
                pass

        # Score the committed result with the same metric as the sandbox.
        actual = self._score_actual(
            candidate, len(added), len(removed), score_delta,
        )

        record = PolicyCommitRecord(
            goal=goal,
            description=description or action_type,
            action_type=action_type,
            params=dict(params or {}),
            source=source,
            decision_id=decision_id,
            recommended=bool(decision_id),
            added_entities=len(added),
            removed_entities=len(removed),
            modified_entities=len(modified),
            score_delta=score_delta,
            actual_score=actual,
            predicted_score=predicted_score,
            prediction_delta=(
                (actual - predicted_score) if predicted_score is not None else 0.0
            ),
            applied_to=added + removed + modified,
            summary=self._compose_summary(len(added), len(removed), score_delta),
        )

        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        logger.info(
            "Policy commit '%s' (%s): added=%d removed=%d score_delta=%+.2f",
            record.description, action_type, len(added), len(removed), score_delta,
        )
        return record

    def commit_recommended(
        self,
        engine: Any,
        decision_id: str,
        goal: str = "",
    ) -> Optional[PolicyCommitRecord]:
        """
        Commit the recommended candidate of a prior counterfactual decision
        to the live world, carrying the sandbox-predicted score forward so
        the actual outcome can be compared against the prediction.
        """
        from sparkai.agent.agent_counterfactual_reasoner import (
            get_counterfactual_reasoner,
        )

        reasoner = get_counterfactual_reasoner()
        decision = reasoner.get_decision(decision_id)
        if decision is None:
            logger.warning("Unknown decision '%s' for policy commit", decision_id)
            return None

        best = decision.best()
        if best is None:
            return None

        candidate = decision.find_candidate(best.candidate_id)
        if candidate is None:
            return None

        return self.commit(
            engine,
            candidate.action_type,
            candidate.params,
            goal=goal or decision.goal,
            description=candidate.description,
            source="counterfactual",
            decision_id=decision.id,
            predicted_score=best.score,
        )

    def commit_latest_decision(
        self,
        engine: Any,
        goal: str = "",
    ) -> Optional[PolicyCommitRecord]:
        """Commit the recommended candidate of the most recent decision."""
        from sparkai.agent.agent_counterfactual_reasoner import (
            get_counterfactual_reasoner,
        )

        reasoner = get_counterfactual_reasoner()
        decisions = reasoner.list_decisions(limit=1)
        if not decisions:
            return None
        return self.commit_recommended(engine, decisions[0]["id"], goal=goal)

    def get_commits(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the recent commit history (most recent first)."""
        return [r.to_dict() for r in list(reversed(self._history[-limit:]))]

    def get_statistics(self) -> Dict[str, Any]:
        if not self._history:
            return {"total_commits": 0, "avg_actual_score": 0.0}
        scores = [r.actual_score for r in self._history]
        return {
            "total_commits": len(self._history),
            "avg_actual_score": round(sum(scores) / len(scores), 4),
            "recommended_commits": sum(1 for r in self._history if r.recommended),
        }

    # ------------------------------------------------------------------
    # Action application (mirrors the counterfactual reasoner semantics)
    # ------------------------------------------------------------------

    def _apply_candidate(self, engine: Any, candidate) -> None:
        action_type = candidate.action_type
        params = candidate.params

        if action_type in ("create_entity", "spawn"):
            scene = self._active_scene(engine)
            if scene is None:
                return
            props = dict(params.get("properties", {}) or {})
            entity = scene.create_entity(
                name=params.get("name", "Committed Entity"),
                position=params.get("position", [0.0, 0.0, 0.0]),
            )
            entity.properties.update(props)
            for tag in params.get("tags", []) or []:
                entity.add_tag(tag)
            if "score" not in props:
                entity.properties.setdefault("score", 0.0)

        elif action_type in ("destroy_entity", "destroy"):
            scene = self._active_scene(engine)
            if scene is None:
                return
            target = params.get("target") or params.get("entity_id") or params.get("name")
            if target:
                if target in scene.entities:
                    scene.remove_entity(target)
                else:
                    hit = scene.find_entity_by_name(str(target))
                    if hit:
                        scene.remove_entity(hit.id)

        elif action_type == "set_property":
            scene = self._active_scene(engine)
            if scene is None:
                return
            target = params.get("target") or params.get("entity_id")
            entity = None
            if target:
                entity = scene.get_entity(target) or scene.find_entity_by_name(str(target))
            if entity is None and scene.entities:
                entity = next(iter(scene.entities.values()))
            if entity:
                entity.properties[params.get("key", "score")] = params.get("value", 0)

        elif action_type == "add_component":
            scene = self._active_scene(engine)
            if scene is None:
                return
            target = params.get("target") or params.get("entity_id")
            entity = None
            if target:
                entity = scene.get_entity(target) or scene.find_entity_by_name(str(target))
            if entity is None and scene.entities:
                entity = next(iter(scene.entities.values()))
            if entity:
                entity.add_component(
                    params.get("component_type", "generic"),
                    params.get("data", {}),
                )

        elif action_type in ("trigger_signal", "simulate", "none"):
            # No-op for live commit; the running engine handles behavior.
            pass

    def _active_scene(self, engine: Any) -> Any:
        scene = getattr(engine, "get_active_scene", lambda: None)()
        if scene is None:
            scenes = list(getattr(engine, "_scenes", {}).values())
            scene = scenes[0] if scenes else None
        return scene

    # ------------------------------------------------------------------
    # Measurement
    # ------------------------------------------------------------------

    def _flatten(self, engine: Any) -> Dict[str, Dict[str, Any]]:
        state: Dict[str, Dict[str, Any]] = {}
        for scene in getattr(engine, "_scenes", {}).values():
            for entity in scene.entities.values():
                state[entity.id] = {
                    "name": entity.name,
                    "properties": dict(entity.properties),
                    "position": list(entity.position),
                }
        return state

    def _entity_changed(self, before: Dict[str, Any], after: Dict[str, Any]) -> bool:
        return (
            before["properties"] != after["properties"]
            or list(before["position"]) != list(after["position"])
        )

    def _score_actual(
        self,
        candidate,
        added: int,
        removed: int,
        score_delta: float,
    ) -> float:
        """Score a live commit with the same intent-aligned metric as the
        sandbox so predicted (sandbox) and actual (committed) are comparable."""
        from sparkai.agent.agent_counterfactual_reasoner import _ACTION_INTENT

        intent = candidate.intent or _ACTION_INTENT.get(candidate.action_type, 0)
        score = 0.5
        if intent > 0:
            score += min(0.5, added * 0.15)
            score += min(0.4, max(0.0, score_delta) * 0.2)
            score -= min(0.4, removed * 0.2)
        elif intent < 0:
            score += min(0.5, removed * 0.2)
            score -= min(0.4, added * 0.2)
        else:
            score += min(0.4, max(0.0, score_delta) * 0.2)
            score -= min(0.3, (added + removed) * 0.1)
        if (added or removed or abs(score_delta) > 0.001):
            score += 0.05
        else:
            score -= 0.05
        return max(0.0, min(1.0, score))

    def _compose_summary(self, added: int, removed: int, score_delta: float) -> str:
        if added or removed:
            parts = []
            if added:
                parts.append(f"{added} entity/entities created")
            if removed:
                parts.append(f"{removed} entity/entities destroyed")
            return ", ".join(parts) + f" (score {score_delta:+.2f})"
        if abs(score_delta) > 0.001:
            return f"Score moved {score_delta:+.2f} with no entity count change."
        return "No observable world change from the committed action."


_instance: Optional[PolicyCommitter] = None


def get_policy_committer() -> PolicyCommitter:
    """Return the process-wide PolicyCommitter singleton."""
    global _instance
    if _instance is None:
        _instance = PolicyCommitter()
    return _instance
