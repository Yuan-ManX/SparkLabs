"""
SparkLabs Agent - Autonomous Goal Discoverer

Closes the proactive side of the AI-native loop. Instead of waiting for a
user-supplied goal, the agent observes the live world state and proposes
candidate goals that match emergent conditions: empty scenes, score
imbalance, entity drought, stale state, or missing variety.

Each candidate goal is scored by:
  - novelty      : how different the goal is from recently pursued goals;
  - impact       : magnitude of the world change the goal would trigger;
  - feasibility  : inverse of expected difficulty, tempered by the agent's
                   measured prediction reliability (calibrated confidence).

The discoverer fuses the agent's reasoning with the engine's world state,
turning observation into self-generated intent. It is the entry point of
the proactive autonomous initiative:

    observe -> discover goals -> forecast -> plan -> gate -> commit -> learn
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredGoal:
    """A candidate goal derived from live world observation."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    description: str = ""
    trigger: str = ""
    target_state: str = ""
    novelty: float = 0.5
    impact: float = 0.5
    feasibility: float = 0.5
    raw_confidence: float = 0.5
    calibrated_confidence: float = 0.5
    score: float = 0.0
    world_signature: str = ""
    discovered_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "trigger": self.trigger,
            "target_state": self.target_state,
            "novelty": round(self.novelty, 4),
            "impact": round(self.impact, 4),
            "feasibility": round(self.feasibility, 4),
            "raw_confidence": round(self.raw_confidence, 4),
            "calibrated_confidence": round(self.calibrated_confidence, 4),
            "score": round(self.score, 4),
            "world_signature": self.world_signature,
            "discovered_at": self.discovered_at,
        }


class GoalDiscoverer:
    """
    Observes the engine's live world state and proposes candidate goals.

    The discovery rules are deterministic heuristics that read the same
    world snapshot the editor renders, so agent intent always tracks the
    scene the user sees. A lightweight novelty signal avoids proposing the
    same goal repeatedly across consecutive runs.
    """

    def __init__(self, max_history: int = 40) -> None:
        self._history: List[DiscoveredGoal] = []
        self._max_history = max_history
        # Sliding window of recently pursued goal titles for novelty scoring.
        self._recent_titles: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def discover(
        self,
        engine: Any,
        calibrator: Any = None,
        max_goals: int = 6,
    ) -> List[DiscoveredGoal]:
        """
        Inspect the live world and return ranked candidate goals.

        The calibrator (PredictionCalibrator) is used to temper raw
        confidence by the agent's measured simulation reliability, so the
        agent does not over-commit to goals its forecasts have historically
        gotten wrong.
        """
        snapshot = self._snapshot(engine)
        signature = self._signature(snapshot)

        candidates: List[DiscoveredGoal] = []
        candidates.extend(self._rules_empty_scene(snapshot, signature))
        candidates.extend(self._rules_score_balance(snapshot, signature))
        candidates.extend(self._rules_variety(snapshot, signature))
        candidates.extend(self._rules_stale_state(snapshot, signature))
        # Rule violations: each broken game-design rule yields a goal the
        # stewardship cycle can remediate. This fuses the engine's rule
        # enforcement with the agent's goal-directed reasoning.
        candidates.extend(self._rules_violation_goals(engine, signature))

        # Score and rank.
        for goal in candidates:
            goal.novelty = self._novelty(goal)
            goal.raw_confidence = self._raw_confidence(goal)
            if calibrator is not None:
                goal.calibrated_confidence = calibrator.calibrate(goal.raw_confidence)
            else:
                goal.calibrated_confidence = goal.raw_confidence
            goal.score = self._rank_score(goal)

        candidates.sort(key=lambda g: g.score, reverse=True)
        ranked = candidates[:max_goals]
        # Persist discovered goals so they can be looked up by id later
        # (e.g. when the agent or user chooses one to pursue).
        for goal in ranked:
            self._history.append(goal)
        while len(self._history) > self._max_history:
            self._history.pop(0)
        return ranked

    def remember_pursued(self, goal_title: str) -> None:
        """Record that a goal is being pursued, to dampen future novelty."""
        self._recent_titles.append(goal_title)
        # Keep the novelty window short so old pursuits resurface eventually.
        if len(self._recent_titles) > 12:
            self._recent_titles = self._recent_titles[-12:]

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [g.to_dict() for g in list(reversed(self._history[-limit:]))]

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_discovered": len(self._history),
            "recent_titles": list(self._recent_titles),
        }

    def clear(self) -> int:
        n = len(self._history)
        self._history.clear()
        return n

    # ------------------------------------------------------------------
    # World observation
    # ------------------------------------------------------------------

    def _snapshot(self, engine: Any) -> Dict[str, Any]:
        """Flatten every entity across every scene into a single view."""
        scenes: List[Dict[str, Any]] = []
        all_scores: List[float] = []
        entity_count = 0

        for scene in getattr(engine, "_scenes", {}).values():
            entities = []
            for entity in scene.entities.values():
                props = dict(entity.properties)
                try:
                    score = float(props.get("score", 0.0))
                except (TypeError, ValueError):
                    score = 0.0
                all_scores.append(score)
                entities.append({
                    "id": entity.id,
                    "name": entity.name,
                    "score": score,
                    "tags": list(getattr(entity, "tags", []) or []),
                    "position": list(entity.position),
                    "properties": props,
                })
            scenes.append({
                "id": scene.id,
                "name": getattr(scene, "name", "Scene"),
                "entity_count": len(entities),
                "entities": entities,
            })
            entity_count += len(entities)

        return {
            "scenes": scenes,
            "entity_count": entity_count,
            "scores": all_scores,
            "scene_count": len(scenes),
        }

    def _signature(self, snapshot: Dict[str, Any]) -> str:
        """A compact signature of the world state for change detection."""
        return (
            f"s{snapshot['scene_count']}:e{snapshot['entity_count']}:"
            f"max{max(snapshot['scores']) if snapshot['scores'] else 0:.1f}:"
            f"min{min(snapshot['scores']) if snapshot['scores'] else 0:.1f}"
        )

    # ------------------------------------------------------------------
    # Discovery rules
    # ------------------------------------------------------------------

    def _rules_empty_scene(
        self, snapshot: Dict[str, Any], signature: str,
    ) -> List[DiscoveredGoal]:
        goals: List[DiscoveredGoal] = []
        for scene in snapshot["scenes"]:
            if scene["entity_count"] == 0:
                goals.append(DiscoveredGoal(
                    title=f"Populate empty scene '{scene['name']}'",
                    description=(
                        f"Scene '{scene['name']}' has no entities. Introduce a "
                        f"balanced starting set so the world is interactive."
                    ),
                    trigger="empty_scene",
                    target_state="scene has at least 3 balanced entities",
                    impact=0.7,
                    feasibility=0.8,
                    world_signature=signature,
                ))
            elif scene["entity_count"] == 1:
                goals.append(DiscoveredGoal(
                    title=f"Diversify sparse scene '{scene['name']}'",
                    description=(
                        f"Scene '{scene['name']}' has only one entity. Add "
                        f"complementary entities to enable interaction."
                    ),
                    trigger="sparse_scene",
                    target_state="scene has 3+ distinct entities",
                    impact=0.5,
                    feasibility=0.75,
                    world_signature=signature,
                ))
        return goals

    def _rules_score_balance(
        self, snapshot: Dict[str, Any], signature: str,
    ) -> List[DiscoveredGoal]:
        scores = snapshot["scores"]
        if len(scores) < 2:
            return []
        goals: List[DiscoveredGoal] = []
        avg = sum(scores) / len(scores)
        spread = max(scores) - min(scores)
        if spread > 15.0:
            goals.append(DiscoveredGoal(
                title="Rebalance entity score distribution",
                description=(
                    f"Score spread is {spread:.1f} (avg {avg:.1f}). "
                    f"Pull outliers toward the mean for a fairer world."
                ),
                trigger="score_spread",
                target_state="score spread under 10",
                impact=0.6,
                feasibility=0.7,
                world_signature=signature,
            ))
        if avg < 0.0:
            goals.append(DiscoveredGoal(
                title="Lift negative-scoring world",
                description=(
                    f"Average score is {avg:.1f}. Introduce positive-score "
                    f"entities to shift the world toward a healthier state."
                ),
                trigger="negative_average",
                target_state="average score above 0",
                impact=0.7,
                feasibility=0.7,
                world_signature=signature,
            ))
        return goals

    def _rules_variety(
        self, snapshot: Dict[str, Any], signature: str,
    ) -> List[DiscoveredGoal]:
        if snapshot["entity_count"] < 3:
            return []
        names: Dict[str, int] = {}
        for scene in snapshot["scenes"]:
            for ent in scene["entities"]:
                key = (ent["name"] or "").lower()
                names[key] = names.get(key, 0) + 1
        duplicates = sum(c - 1 for c in names.values() if c > 1)
        if duplicates >= 2:
            return [DiscoveredGoal(
                title="Introduce entity variety",
                description=(
                    f"{duplicates} duplicate-name entities detected. "
                    f"Add distinct entity types to enrich the world."
                ),
                trigger="low_variety",
                target_state="no more than one duplicate name",
                impact=0.4,
                feasibility=0.8,
                world_signature=signature,
            )]
        return []

    def _rules_stale_state(
        self, snapshot: Dict[str, Any], signature: str,
    ) -> List[DiscoveredGoal]:
        # A world with entities but all-zero scores is functionally inert.
        if snapshot["entity_count"] < 2:
            return []
        scores = snapshot["scores"]
        if all(abs(s) < 0.001 for s in scores):
            return [DiscoveredGoal(
                title="Activate inert world",
                description=(
                    "All entities have zero score. Assign meaningful scores "
                    "to make the world's dynamics observable."
                ),
                trigger="inert_world",
                target_state="at least one non-zero score",
                impact=0.6,
                feasibility=0.9,
                world_signature=signature,
            )]
        return []

    def _rules_violation_goals(
        self, engine: Any, signature: str,
    ) -> List[DiscoveredGoal]:
        """
        Turn world-rule violations into candidate goals.

        Each broken game-design rule yields a goal whose trigger is the
        rule type (e.g. ``max_entities``, ``min_score``). The steward's
        dynamic synthesizer can then generate remediation candidates
        tailored to the specific violation. This closes the loop from
        engine rule enforcement to agent-driven remediation.
        """
        goals: List[DiscoveredGoal] = []
        try:
            if not hasattr(engine, "validate_world_rules"):
                return goals
            violations = engine.validate_world_rules()
            if not violations:
                return goals
            # Group violations by rule type to avoid duplicate goals.
            seen_types: set = set()
            for v in violations:
                trigger = f"rule_{v.rule_type}"
                if trigger in seen_types:
                    continue
                seen_types.add(trigger)
                severity = getattr(v, "severity", "warning")
                goals.append(DiscoveredGoal(
                    title=f"Fix rule violation: {v.rule_name}",
                    description=v.message,
                    trigger=trigger,
                    target_state=f"rule '{v.rule_name}' satisfied",
                    impact=0.8 if severity == "critical" else 0.6 if severity == "error" else 0.4,
                    feasibility=0.7,
                    world_signature=signature,
                ))
        except Exception:
            pass
        return goals

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _novelty(self, goal: DiscoveredGoal) -> float:
        """Higher novelty for goals not recently pursued."""
        if not self._recent_titles:
            return 0.8
        repeats = sum(
            1 for t in self._recent_titles
            if t.lower() == goal.title.lower()
        )
        # Each recent repeat dampens novelty.
        return max(0.1, 0.8 - 0.2 * repeats)

    def _raw_confidence(self, goal: DiscoveredGoal) -> float:
        """Blend impact and feasibility into a pre-calibration confidence."""
        return 0.4 * goal.impact + 0.6 * goal.feasibility

    def _rank_score(self, goal: DiscoveredGoal) -> float:
        """Final ranking weight: novelty + calibrated confidence + impact."""
        return (
            0.3 * goal.novelty
            + 0.5 * goal.calibrated_confidence
            + 0.2 * goal.impact
        )


_instance: Optional[GoalDiscoverer] = None


def get_goal_discoverer() -> GoalDiscoverer:
    """Return the process-wide GoalDiscoverer singleton."""
    global _instance
    if _instance is None:
        _instance = GoalDiscoverer()
    return _instance
