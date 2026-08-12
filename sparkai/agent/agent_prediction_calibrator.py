"""
SparkAI Agent - Prediction Calibration

The agent records sandbox predictions and live outcomes through the policy
committer. This module turns that prediction-vs-actual history into a
reliability profile: how trustworthy the agent's own simulations have been,
across all actions and per action type.

A calibrated confidence is produced by scaling a raw (uncalibrated)
confidence by the agent's measured track record. This lets the agent
self-correct its decision-making over time: when predictions have been
faithful, its confidence is trusted; when they have drifted, confidence is
tempered. The calibration is a live, data-driven self-model, refreshed from
every committed action.
"""

from __future__ import annotations

import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CalibrationSample:
    """A single prediction-vs-outcome observation used for calibration."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action_type: str = "simulate"
    predicted_score: Optional[float] = None
    actual_score: float = 0.0
    error: float = 0.0
    bias: float = 0.0
    recorded_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "predicted_score": (
                round(self.predicted_score, 4)
                if self.predicted_score is not None else None
            ),
            "actual_score": round(self.actual_score, 4),
            "error": round(self.error, 4),
            "bias": round(self.bias, 4),
            "recorded_at": self.recorded_at,
        }


@dataclass
class CalibrationProfile:
    """Aggregate reliability metrics derived from calibration samples."""

    sample_count: int = 0
    mean_absolute_error: float = 0.0
    mean_bias: float = 0.0
    best_score: float = 0.0
    worst_score: float = 0.0
    action_type_reliability: Dict[str, float] = field(default_factory=dict)
    confidence_multiplier: float = 1.0
    reliability_rating: str = "uncalibrated"
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "mean_absolute_error": round(self.mean_absolute_error, 4),
            "mean_bias": round(self.mean_bias, 4),
            "best_score": round(self.best_score, 4),
            "worst_score": round(self.worst_score, 4),
            "action_type_reliability": {
                k: round(v, 4) for k, v in self.action_type_reliability.items()
            },
            "confidence_multiplier": round(self.confidence_multiplier, 4),
            "reliability_rating": self.reliability_rating,
            "last_updated": self.last_updated,
        }


class PredictionCalibrator:
    """
    Tracks the fidelity of the agent's sandbox predictions and exposes a
    calibrated confidence for future decisions.

    Each committed action that carries both a predicted and an actual score
    yields a sample. The calibrator accumulates samples, computes error and
    bias statistics (overall and per action type), and derives a confidence
    multiplier that scales raw confidence toward the measured reality.
    """

    def __init__(self, max_samples: int = 200) -> None:
        self._samples: List[CalibrationSample] = []
        self._max_samples = max_samples
        self._seen_commit_ids: set = set()
        self._profile: CalibrationProfile = CalibrationProfile()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_commit(self, commit: Dict[str, Any]) -> Optional[CalibrationSample]:
        """
        Ingest a single policy-commit record and add a calibration sample.

        A sample is only produced when the commit carries both a predicted
        and an actual score; otherwise there is nothing to calibrate against.
        Returns the created sample, or None if the commit is not usable.
        """
        predicted = commit.get("predicted_score")
        actual = commit.get("actual_score")
        if predicted is None or actual is None:
            return None

        # Guard against re-ingesting the same commit (e.g. on resync), so a
        # single action never produces duplicate calibration samples.
        commit_id = commit.get("id")
        if commit_id and commit_id in self._seen_commit_ids:
            return None
        if commit_id:
            self._seen_commit_ids.add(commit_id)

        error = abs(float(actual) - float(predicted))
        bias = float(actual) - float(predicted)
        sample = CalibrationSample(
            action_type=commit.get("action_type", "simulate"),
            predicted_score=float(predicted),
            actual_score=float(actual),
            error=error,
            bias=bias,
        )
        self._samples.append(sample)
        while len(self._samples) > self._max_samples:
            self._samples.pop(0)
        self._refresh_profile()
        return sample

    def record_many(self, commits: List[Dict[str, Any]]) -> int:
        """Ingest a batch of commit records, returning how many samples were added."""
        count = 0
        for commit in commits:
            if self.record_commit(commit) is not None:
                count += 1
        return count

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def calibrate(self, raw_confidence: float) -> float:
        """
        Scale a raw confidence value by the agent's measured reliability.

        Returns a value clamped to [0.0, 1.0]. With no samples the raw
        confidence is returned unchanged (the agent is not yet self-aware).
        """
        if self._profile.sample_count == 0:
            return max(0.0, min(1.0, float(raw_confidence)))
        scaled = float(raw_confidence) * self._profile.confidence_multiplier
        return max(0.0, min(1.0, scaled))

    def get_profile(self) -> CalibrationProfile:
        """Return the current calibration profile."""
        return self._profile

    def get_samples(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent calibration samples, newest first."""
        return [s.to_dict() for s in list(reversed(self._samples[-limit:]))]

    def get_statistics(self) -> Dict[str, Any]:
        """Return a compact status payload for dashboards."""
        return {
            "sample_count": self._profile.sample_count,
            "confidence_multiplier": round(self._profile.confidence_multiplier, 4),
            "reliability_rating": self._profile.reliability_rating,
            "mean_absolute_error": round(self._profile.mean_absolute_error, 4),
            "mean_bias": round(self._profile.mean_bias, 4),
            "reliable_action_types": [
                at for at, r in self._profile.action_type_reliability.items() if r >= 0.7
            ],
        }

    # ------------------------------------------------------------------
    # Profile derivation
    # ------------------------------------------------------------------

    def _refresh_profile(self) -> None:
        if not self._samples:
            self._profile = CalibrationProfile()
            return

        errors = [s.error for s in self._samples]
        biases = [s.bias for s in self._samples]
        mae = sum(errors) / len(errors)
        mbias = sum(biases) / len(biases)

        # Per-action-type reliability: 1 - normalized mean error for that type.
        by_type: Dict[str, List[float]] = {}
        for s in self._samples:
            by_type.setdefault(s.action_type, []).append(s.error)
        reliability = {}
        for atype, errs in by_type.items():
            type_mae = sum(errs) / len(errs)
            reliability[atype] = max(0.0, min(1.0, 1.0 - type_mae))

        # Overall confidence multiplier: temper confidence as error grows.
        multiplier = max(0.0, min(1.0, 1.0 - mae))
        rating = self._rate(mae)

        self._profile = CalibrationProfile(
            sample_count=len(self._samples),
            mean_absolute_error=mae,
            mean_bias=mbias,
            best_score=min(errors),
            worst_score=max(errors),
            action_type_reliability=reliability,
            confidence_multiplier=multiplier,
            reliability_rating=rating,
            last_updated=time.time(),
        )

    @staticmethod
    def _rate(mae: float) -> str:
        """Map mean absolute error to a human-readable reliability rating."""
        if mae <= 0.05:
            return "high"
        if mae <= 0.15:
            return "moderate"
        if mae <= 0.35:
            return "developing"
        return "low"


# Module-level singleton for shared use across the agent and API layer.
_instance: Optional[PredictionCalibrator] = None


def get_prediction_calibrator() -> PredictionCalibrator:
    """Return the shared PredictionCalibrator singleton."""
    global _instance
    if _instance is None:
        _instance = PredictionCalibrator()
    return _instance
