"""
SparkLabs Agent - World State Forecaster

Projects the live world forward using the engine's own predictive
simulation (checkpoint-based rollback), then distills the predicted
future into a compact forecast the agent can reason about.

Unlike the agent's internal world model (which is a learned predictive
representation), this forecaster runs the REAL engine forward in a
sandbox and measures what actually happens to entities, scores, and
scene composition. The result is a forward-looking signal that feeds:

  - goal discovery : does the world drift toward a problem state?
  - autonomy gating: is the predicted future stable enough to act on?
  - mission debrief: were the committed actions moving the world
                     toward the forecasted trajectory?

The forecaster never mutates the live world: every projection is rolled
back through the engine's checkpoint service, so observation is safe.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorldForecast:
    """A compact projection of the world's future state."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    horizon_frames: int = 60
    delta_time: float = 1.0 / 60.0
    created_at: float = field(default_factory=time.time)

    # Population dynamics.
    entity_count_before: int = 0
    entity_count_after: int = 0
    entity_delta: int = 0

    # Score dynamics.
    total_score_before: float = 0.0
    total_score_after: float = 0.0
    score_delta: float = 0.0
    score_velocity: float = 0.0

    # Stability signals.
    stable: bool = True
    drift_summary: str = ""
    predicted_problems: List[str] = field(default_factory=list)
    predicted_opportunities: List[str] = field(default_factory=list)

    # Raw engine projection (compact).
    projection: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "horizon_frames": self.horizon_frames,
            "delta_time": self.delta_time,
            "created_at": self.created_at,
            "entity_count_before": self.entity_count_before,
            "entity_count_after": self.entity_count_after,
            "entity_delta": self.entity_delta,
            "total_score_before": round(self.total_score_before, 4),
            "total_score_after": round(self.total_score_after, 4),
            "score_delta": round(self.score_delta, 4),
            "score_velocity": round(self.score_velocity, 4),
            "stable": self.stable,
            "drift_summary": self.drift_summary,
            "predicted_problems": self.predicted_problems,
            "predicted_opportunities": self.predicted_opportunities,
            "projection": self.projection,
        }


class WorldForecaster:
    """
    Projects the engine's live world forward and interprets the result.

    Uses SparkEngine.simulate_frames (which is checkpoint-rollback safe)
    to obtain a before/after snapshot, then derives population and score
    dynamics plus qualitative problem/opportunity flags.
    """

    def __init__(self, max_history: int = 30) -> None:
        self._history: List[WorldForecast] = []
        self._max_history = max_history

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def forecast(
        self,
        engine: Any,
        horizon_frames: int = 60,
        delta_time: float = 1.0 / 60.0,
    ) -> WorldForecast:
        """
        Run the engine forward in a sandbox and summarize the predicted
        future. The live world is left untouched (rollback simulation).
        """
        before = self._flatten(engine)
        before_count = sum(len(s["entities"]) for s in before["scenes"])
        before_score = sum(
            e["score"]
            for s in before["scenes"]
            for e in s["entities"]
        )

        projection: Dict[str, Any] = {}
        try:
            projection = engine.simulate_frames(
                frames=horizon_frames,
                delta_time=delta_time,
                commit=False,
            ) or {}
        except Exception as exc:
            logger.warning("World forecast simulation failed: %s", exc)
            projection = {"error": str(exc)}

        # simulate_frames already rolls back, so re-reading the engine
        # gives the original (pre-simulation) state. The projection dict
        # carries the predicted after-state, which we parse instead.
        after = self._parse_projection(projection, before)
        after_count = after["entity_count"]
        after_score = after["total_score"]

        entity_delta = after_count - before_count
        score_delta = after_score - before_score
        # Velocity = score change per frame.
        score_velocity = (
            score_delta / horizon_frames if horizon_frames else 0.0
        )

        problems: List[str] = []
        opportunities: List[str] = []

        if after_count == 0 and before_count > 0:
            problems.append("predicted_empty_world")
        elif entity_delta < 0:
            problems.append(f"predicted_entity_loss:{abs(entity_delta)}")
        elif entity_delta > 0:
            opportunities.append(f"predicted_growth:{entity_delta}")

        if score_delta < -5.0:
            problems.append(f"predicted_score_decline:{score_delta:.2f}")
        elif score_delta > 5.0:
            opportunities.append(f"predicted_score_gain:{score_delta:.2f}")

        if abs(score_velocity) < 0.01 and before_count > 0:
            problems.append("predicted_inert_world")

        stable = not problems
        drift_summary = self._compose_summary(
            before_count, after_count, before_score, after_score, stable,
        )

        forecast = WorldForecast(
            horizon_frames=horizon_frames,
            delta_time=delta_time,
            entity_count_before=before_count,
            entity_count_after=after_count,
            entity_delta=entity_delta,
            total_score_before=before_score,
            total_score_after=after_score,
            score_delta=score_delta,
            score_velocity=score_velocity,
            stable=stable,
            drift_summary=drift_summary,
            predicted_problems=problems,
            predicted_opportunities=opportunities,
            projection={
                "summary": projection.get("summary", "") if isinstance(projection, dict) else "",
            },
        )

        self._history.append(forecast)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        return forecast

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in list(reversed(self._history[-limit:]))]

    def get_statistics(self) -> Dict[str, Any]:
        if not self._history:
            return {"total_forecasts": 0}
        recent = self._history[-10:]
        return {
            "total_forecasts": len(self._history),
            "recent_stable_ratio": (
                sum(1 for f in recent if f.stable) / len(recent)
            ),
            "recent_avg_score_velocity": (
                sum(f.score_velocity for f in recent) / len(recent)
            ),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _flatten(self, engine: Any) -> Dict[str, Any]:
        scenes: List[Dict[str, Any]] = []
        for scene in getattr(engine, "_scenes", {}).values():
            entities = []
            for entity in scene.entities.values():
                try:
                    score = float(entity.properties.get("score", 0.0))
                except (TypeError, ValueError):
                    score = 0.0
                entities.append({"id": entity.id, "name": entity.name, "score": score})
            scenes.append({"id": scene.id, "name": getattr(scene, "name", "Scene"), "entities": entities})
        return {"scenes": scenes}

    def _parse_projection(
        self, projection: Dict[str, Any], before: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract the predicted after-state from the engine projection.

        The checkpoint service returns a dict with before/after/diff/summary.
        We count entities and sum scores from the 'after' view when present,
        falling back to the 'before' view if the projection is partial.
        """
        if not isinstance(projection, dict):
            return {"entity_count": 0, "total_score": 0.0}

        after_raw = projection.get("after") or projection.get("after_state") or {}
        # after_raw may be a list of scenes or a dict of scenes.
        entities: List[Dict[str, Any]] = []
        if isinstance(after_raw, dict):
            scenes_view = after_raw.get("scenes") or after_raw.get("entities") or []
            if isinstance(scenes_view, list):
                for item in scenes_view:
                    if isinstance(item, dict):
                        ents = item.get("entities") or []
                        if isinstance(ents, list):
                            entities.extend(ents)
                        elif isinstance(item, dict) and "score" in item:
                            entities.append(item)
            elif isinstance(after_raw, list):
                entities = [e for e in after_raw if isinstance(e, dict)]
        elif isinstance(after_raw, list):
            entities = [e for e in after_raw if isinstance(e, dict)]

        # If the projection did not carry a parseable after-state, fall back
        # to the diff signal so we still produce a meaningful forecast.
        if not entities:
            diff = projection.get("diff") or {}
            added = 0
            removed = 0
            score_delta = 0.0
            if isinstance(diff, dict):
                added = len(diff.get("added_entities", []) or [])
                removed = len(diff.get("removed_entities", []) or [])
                try:
                    score_delta = float(diff.get("score_delta", 0.0) or 0.0)
                except (TypeError, ValueError):
                    score_delta = 0.0
            before_count = sum(len(s["entities"]) for s in before["scenes"])
            before_score = sum(
                e["score"]
                for s in before["scenes"]
                for e in s["entities"]
            )
            return {
                "entity_count": max(0, before_count + added - removed),
                "total_score": before_score + score_delta,
            }

        count = len(entities)
        total = 0.0
        for ent in entities:
            try:
                total += float(ent.get("score", 0.0) or 0.0)
            except (TypeError, ValueError):
                pass
        return {"entity_count": count, "total_score": total}

    def _compose_summary(
        self,
        before_count: int,
        after_count: int,
        before_score: float,
        after_score: float,
        stable: bool,
    ) -> str:
        drift = after_count - before_count
        score_drift = after_score - before_score
        parts = []
        if drift:
            parts.append(f"entities {before_count}->{after_count} ({drift:+d})")
        else:
            parts.append(f"entities stable at {before_count}")
        if abs(score_drift) > 0.001:
            parts.append(f"score {before_score:.2f}->{after_score:.2f} ({score_drift:+.2f})")
        else:
            parts.append(f"score stable at {before_score:.2f}")
        verdict = "stable" if stable else "drift detected"
        return f"{', '.join(parts)}; {verdict}"


_instance: Optional[WorldForecaster] = None


def get_world_forecaster() -> WorldForecaster:
    """Return the process-wide WorldForecaster singleton."""
    global _instance
    if _instance is None:
        _instance = WorldForecaster()
    return _instance
