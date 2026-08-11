"""
SparkLabs Agent - Counterfactual Decision Reasoner

Bridges the Agent's planning with the engine's predictive simulation so
that candidate actions are evaluated "what-if" style before they are
committed to the live world. Each candidate is applied to a sandbox
copy of the world, stepped forward for a number of frames, measured for
outcome, and then rolled back. The resulting ranked evaluation lets the
Agent reason about consequences and choose the strongest course of
action, fusing AI planning with real engine dynamics.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Supported engine-level candidate action types and their intent sign.
# A positive intent means the action is meant to grow/strengthen the
# world (add entities, raise score); a negative intent means it is meant
# to remove/weaken (destroy, debuff). The scoring uses intent so that
# removals on a destroy action are not penalized.
_ACTION_INTENT: Dict[str, int] = {
    "create_entity": 1,
    "spawn": 1,
    "add_component": 1,
    "set_property": 0,
    "trigger_signal": 0,
    "destroy_entity": -1,
    "destroy": -1,
    "simulate": 0,
    "none": 0,
}


@dataclass
class CounterfactualCandidate:
    """A single candidate action to be simulated and scored."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    action_type: str = "simulate"
    params: Dict[str, Any] = field(default_factory=dict)
    success_key: str = "score"
    intent: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "action_type": self.action_type,
            "params": self.params,
            "success_key": self.success_key,
            "intent": self.intent,
            "metadata": self.metadata,
        }


@dataclass
class CounterfactualResult:
    """Outcome of evaluating a single candidate in the sandbox."""
    candidate_id: str = ""
    description: str = ""
    action_type: str = ""
    score: float = 0.5
    added_entities: int = 0
    removed_entities: int = 0
    score_delta: float = 0.0
    frames_run: int = 0
    summary: str = ""
    committed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "description": self.description,
            "action_type": self.action_type,
            "score": round(self.score, 4),
            "added_entities": self.added_entities,
            "removed_entities": self.removed_entities,
            "score_delta": round(self.score_delta, 4),
            "frames_run": self.frames_run,
            "summary": self.summary,
            "committed": self.committed,
            "metadata": self.metadata,
        }


@dataclass
class CounterfactualDecision:
    """The ranked outcome of a counterfactual reasoning pass."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal: str = ""
    candidates: List[CounterfactualResult] = field(default_factory=list)
    # The original candidate actions (with full params) so the Policy
    # Committer can re-apply the recommended one to the live world.
    candidates_raw: List[CounterfactualCandidate] = field(default_factory=list)
    recommended_id: str = ""
    recommended_score: float = 0.0
    reasoning: str = ""
    created_at: float = field(default_factory=time.time)

    def best(self) -> Optional[CounterfactualResult]:
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda r: r.score)

    def find_candidate(self, candidate_id: str) -> Optional[CounterfactualCandidate]:
        """Locate the original candidate action by its id."""
        for cand in self.candidates_raw:
            if cand.id == candidate_id:
                return cand
        return None

    def to_dict(self) -> Dict[str, Any]:
        best = self.best()
        return {
            "id": self.id,
            "goal": self.goal,
            "candidates": [r.to_dict() for r in self.candidates],
            "recommended_id": best.candidate_id if best else None,
            "recommended_score": best.score if best else 0.0,
            "reasoning": self.reasoning,
            "created_at": self.created_at,
        }


class CounterfactualReasoner:
    """
    Evaluates candidate actions by sandbox simulation.

    For every candidate the current world is checkpointed, the candidate
    is applied, the world is stepped forward for `frames` frames, the
    outcome is measured, and the world is restored to its pre-candidate
    state. Candidates are scored and ranked so the Agent can commit only
    to the most promising path.
    """

    def __init__(self) -> None:
        self._decisions: Dict[str, CounterfactualDecision] = {}
        self._total_evaluated: int = 0
        self._total_simulations: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reason(
        self,
        engine: Any,
        candidates: List[Dict[str, Any]],
        goal: str = "",
        frames: int = 60,
        delta_time: float = 1.0 / 60.0,
    ) -> CounterfactualDecision:
        """
        Run a full counterfactual reasoning pass over the candidates.

        Each candidate is simulated in the sandbox and scored. The result
        is a ranked decision with a recommended candidate. The live world
        is never permanently changed: every candidate is rolled back.
        """
        normalized: List[CounterfactualCandidate] = []
        for c in candidates:
            if isinstance(c, CounterfactualCandidate):
                normalized.append(c)
            elif isinstance(c, dict):
                normalized.append(self._from_dict(c))
            else:
                continue

        results: List[CounterfactualResult] = []
        for cand in normalized:
            try:
                result = self.evaluate_candidate(
                    engine, cand, frames=frames, delta_time=delta_time,
                )
                results.append(result)
            except Exception as exc:
                logger.warning("Counterfactual evaluation failed: %s", exc)
                results.append(CounterfactualResult(
                    candidate_id=cand.id,
                    description=cand.description,
                    action_type=cand.action_type,
                    score=0.0,
                    summary=f"Evaluation error: {exc}",
                ))

        results.sort(key=lambda r: r.score, reverse=True)

        decision = CounterfactualDecision(
            goal=goal,
            candidates=results,
            candidates_raw=normalized,
            recommended_id=results[0].candidate_id if results else None,
            recommended_score=results[0].score if results else 0.0,
            reasoning=self._compose_reasoning(goal, results),
        )
        self._decisions[decision.id] = decision
        self._total_evaluated += 1
        return decision

    def evaluate_candidate(
        self,
        engine: Any,
        candidate: CounterfactualCandidate,
        frames: int = 60,
        delta_time: float = 1.0 / 60.0,
    ) -> CounterfactualResult:
        """
        Simulate a single candidate in the sandbox and return its score.

        Workflow: checkpoint -> apply -> step -> measure -> restore.
        The checkpoint service guarantees rollback even when running.
        """
        from sparkai.engine.world_checkpoint import get_world_checkpoint_service
        svc = get_world_checkpoint_service()

        if candidate.intent == 0:
            candidate.intent = _ACTION_INTENT.get(
                candidate.action_type, 0
            )

        # Capture baseline for measurement.
        checkpoint = svc.capture_checkpoint(engine, reason="counterfactual-before")

        before_state = self._flatten(engine)
        before_count = len(before_state)

        # Apply the candidate action to the (sandbox) world.
        self._apply_candidate(engine, candidate)

        # Step the world forward in sandbox mode (rolled back internally),
        # then re-apply is not needed because we hold our own checkpoint.
        sim = engine.simulate_frames(
            frames=frames, delta_time=delta_time, commit=False,
        )

        after_state = self._flatten(engine)
        after_count = len(after_state)

        # Measure outcome while we still have the post-action state, then
        # roll back to the pre-candidate checkpoint to leave no residue.
        result = self._measure(
            engine, candidate, before_state, after_state,
            frames_run=sim.get("frames_run", max(1, int(frames))),
            summary=sim.get("summary", ""),
        )

        # Rollback to pre-candidate state (also clears the sim sandbox).
        engine.restore_checkpoint(checkpoint.id)
        try:
            svc.discard_checkpoint(checkpoint.id)
        except Exception:
            pass

        self._total_simulations += 1
        return result

    def get_decision(self, decision_id: str) -> Optional[CounterfactualDecision]:
        return self._decisions.get(decision_id)

    def list_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [d.to_dict() for d in list(self._decisions.values())[-limit:]]

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_decisions": len(self._decisions),
            "total_candidates_evaluated": self._total_evaluated,
            "total_simulations": self._total_simulations,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _from_dict(self, data: Dict[str, Any]) -> CounterfactualCandidate:
        params = dict(data.get("params", {}) or {})
        action_type = data.get("action_type", "simulate")
        intent = data.get("intent", _ACTION_INTENT.get(action_type, 0))
        return CounterfactualCandidate(
            id=data.get("id", uuid.uuid4().hex),
            description=data.get("description", action_type),
            action_type=action_type,
            params=params,
            success_key=data.get("success_key", "score"),
            intent=intent,
            metadata=data.get("metadata", {}),
        )

    def _flatten(self, engine: Any) -> Dict[str, Dict[str, Any]]:
        """Flatten scene entities to {id: properties} for measurement."""
        state: Dict[str, Dict[str, Any]] = {}
        for scene in engine._scenes.values():
            for entity in scene.entities.values():
                state[entity.id] = {
                    "name": entity.name,
                    "properties": dict(entity.properties),
                    "position": list(entity.position),
                }
        return state

    def _apply_candidate(self, engine: Any, candidate: CounterfactualCandidate) -> None:
        """Apply a candidate action to the current (sandbox) world."""
        action_type = candidate.action_type
        params = candidate.params

        if action_type in ("create_entity", "spawn"):
            scene = self._active_scene(engine)
            if scene is None:
                return
            props = dict(params.get("properties", {}) or {})
            entity = scene.create_entity(
                name=params.get("name", "Sandbox Entity"),
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
                key = params.get("key", "score")
                value = params.get("value", 0)
                entity.properties[key] = value

        elif action_type in ("add_component",):
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
            # Simulation-only or no-op; the sandbox stepping handles it.
            pass

    def _active_scene(self, engine: Any) -> Any:
        scene = getattr(engine, "get_active_scene", lambda: None)()
        if scene is None:
            scenes = list(engine._scenes.values())
            scene = scenes[0] if scenes else None
        return scene

    def _measure(
        self,
        engine: Any,
        candidate: CounterfactualCandidate,
        before: Dict[str, Dict[str, Any]],
        after: Dict[str, Dict[str, Any]],
        frames_run: int,
        summary: str,
    ) -> CounterfactualResult:
        before_ids = set(before)
        after_ids = set(after)
        added = after_ids - before_ids
        removed = before_ids - after_ids

        # Compute net score movement across surviving entities.
        score_delta = 0.0
        for eid in after_ids & before_ids:
            b = before[eid]["properties"].get("score", 0.0)
            a = after[eid]["properties"].get("score", 0.0)
            try:
                score_delta += float(a) - float(b)
            except (TypeError, ValueError):
                pass

        intent = candidate.intent

        # Base neutral score; adjust by intent-aligned outcomes.
        score = 0.5

        # Growth actions reward new entities / score gain.
        if intent > 0:
            score += min(0.5, len(added) * 0.15)
            score += min(0.4, max(0.0, score_delta) * 0.2)
            score -= min(0.4, len(removed) * 0.2)
        # Removal actions reward removals (goal-consistent destruction).
        elif intent < 0:
            score += min(0.5, len(removed) * 0.2)
            score -= min(0.4, len(added) * 0.2)
        else:
            # Neutral actions: reward score gain, mildly penalize churn.
            score += min(0.4, max(0.0, score_delta) * 0.2)
            score -= min(0.3, (len(added) + len(removed)) * 0.1)

        # Prefer candidates that produced some measurable change.
        if (added or removed or abs(score_delta) > 0.001):
            score += 0.05
        else:
            score -= 0.05

        score = max(0.0, min(1.0, score))

        return CounterfactualResult(
            candidate_id=candidate.id,
            description=candidate.description,
            action_type=candidate.action_type,
            score=score,
            added_entities=len(added),
            removed_entities=len(removed),
            score_delta=score_delta,
            frames_run=frames_run,
            summary=summary or "No observable change.",
            metadata=candidate.metadata,
        )

    def _compose_reasoning(
        self, goal: str, results: List[CounterfactualResult]
    ) -> str:
        if not results:
            return "No candidates were evaluable."
        best = results[0]
        lines = [f"Goal: {goal or 'unspecified'}"]
        lines.append(
            f"Recommended: '{best.description}' (score={best.score:.2f}, "
            f"added={best.added_entities}, removed={best.removed_entities}, "
            f"score_delta={best.score_delta:+.2f})."
        )
        for r in results[1:]:
            lines.append(
                f"  Alternative '{r.description}': score={r.score:.2f} "
                f"(added={r.added_entities}, removed={r.removed_entities})."
            )
        return "\n".join(lines)


_instance: Optional[CounterfactualReasoner] = None


def get_counterfactual_reasoner() -> CounterfactualReasoner:
    """Return the process-wide CounterfactualReasoner singleton."""
    global _instance
    if _instance is None:
        _instance = CounterfactualReasoner()
    return _instance
