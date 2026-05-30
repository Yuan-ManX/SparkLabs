"""
SparkLabs Agent - Reflection Loop

A singleton self-improvement system for the SparkLabs AI game engine.
Implements a reflection loop that analyzes past agent decisions, identifies
improvement opportunities, generates actionable insights, and adapts agent
strategies for increasingly better outcomes over time.

Architecture:
  ReflectionLoop (singleton)
    |-- ReflectionEntry (record of a single decision-outcome pair)
    |-- ImprovementInsight (actionable finding derived from reflections)
    |-- StrategyAdaptation (modified strategy based on an insight)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


_time_module = time


class ReflectionType(Enum):
    OUTCOME_ANALYSIS = "outcome_analysis"
    STRATEGY_REVIEW = "strategy_review"
    ERROR_POSTMORTEM = "error_postmortem"
    DECISION_AUDIT = "decision_audit"
    PERFORMANCE_BENCHMARK = "performance_benchmark"


class InsightCategory(Enum):
    EFFICIENCY = "efficiency"
    ACCURACY = "accuracy"
    CREATIVITY = "creativity"
    CONSISTENCY = "consistency"
    SAFETY = "safety"
    USER_SATISFACTION = "user_satisfaction"


class ImprovementStatus(Enum):
    IDENTIFIED = "identified"
    IN_PROGRESS = "in_progress"
    APPLIED = "applied"
    VERIFIED = "verified"
    REVERTED = "reverted"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class ReflectionEntry:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    reflection_type: ReflectionType = ReflectionType.OUTCOME_ANALYSIS
    context: Dict[str, Any] = field(default_factory=dict)
    decision_summary: str = ""
    outcome: str = ""
    expected_outcome: str = ""
    deviation_score: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "reflection_type": self.reflection_type.value,
            "context": dict(self.context),
            "decision_summary": self.decision_summary,
            "outcome": self.outcome,
            "expected_outcome": self.expected_outcome,
            "deviation_score": self.deviation_score,
            "timestamp": self.timestamp,
        }


@dataclass
class ImprovementInsight:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    category: InsightCategory = InsightCategory.EFFICIENCY
    description: str = ""
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    source_reflection_ids: List[str] = field(default_factory=list)
    status: ImprovementStatus = ImprovementStatus.IDENTIFIED
    applied_at: float = 0.0
    verified_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "description": self.description,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "action_items": list(self.action_items),
            "source_reflection_ids": list(self.source_reflection_ids),
            "status": self.status.value,
            "applied_at": self.applied_at,
            "verified_at": self.verified_at,
        }


@dataclass
class StrategyAdaptation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    insight_id: str = ""
    original_strategy: Dict[str, Any] = field(default_factory=dict)
    adapted_strategy: Dict[str, Any] = field(default_factory=dict)
    adaptation_rationale: str = ""
    impact_score: float = 0.5
    is_active: bool = True
    version: int = 1
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "insight_id": self.insight_id,
            "original_strategy": dict(self.original_strategy),
            "adapted_strategy": dict(self.adapted_strategy),
            "adaptation_rationale": self.adaptation_rationale,
            "impact_score": self.impact_score,
            "is_active": self.is_active,
            "version": self.version,
            "created_at": self.created_at,
        }


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

MAX_REFLECTION_HISTORY: int = 200
INSIGHT_CONFIDENCE_THRESHOLD: float = 0.6
MIN_SAMPLES_FOR_ADAPTATION: int = 5
ADAPTATION_COOLDOWN_SECONDS: float = 300.0


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------


class ReflectionLoop:
    """Singleton self-improvement system for adaptive agent strategies.

    Maintains a rolling history of agent decision outcomes, periodically
    analyzes patterns to derive improvement insights, and applies
    strategy adaptations to enhance future performance.
    """

    _instance: Optional[ReflectionLoop] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> ReflectionLoop:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> ReflectionLoop:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._reflections: List[ReflectionEntry] = []
        self._insights: List[ImprovementInsight] = []
        self._adaptations: List[StrategyAdaptation] = []
        self._session_reflections: Dict[str, List[str]] = {}
        self._last_adaptation_time: float = 0.0

    def _get_or_create_singleton(self) -> ReflectionLoop:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_reflections": len(self._reflections),
            "total_insights": len(self._insights),
            "insights_verified": sum(
                1 for i in self._insights if i.status == ImprovementStatus.VERIFIED
            ),
            "insights_applied": sum(
                1 for i in self._insights if i.status == ImprovementStatus.APPLIED
            ),
            "active_adaptations": sum(1 for a in self._adaptations if a.is_active),
            "total_adaptations": len(self._adaptations),
            "sessions_tracked": len(self._session_reflections),
        }

    def record_outcome(
        self,
        reflection_type: str = "outcome_analysis",
        context: Optional[Dict[str, Any]] = None,
        decision_summary: str = "",
        outcome: str = "",
        expected_outcome: str = "",
        deviation_score: float = 0.0,
    ) -> ReflectionEntry:
        rtype = ReflectionType(reflection_type)

        computed_deviation = deviation_score
        if computed_deviation == 0.0 and expected_outcome and outcome:
            computed_deviation = self._compute_deviation(outcome, expected_outcome)

        entry = ReflectionEntry(
            reflection_type=rtype,
            context=dict(context) if context else {},
            decision_summary=decision_summary,
            outcome=outcome,
            expected_outcome=expected_outcome,
            deviation_score=computed_deviation,
        )

        self._reflections.append(entry)

        if len(self._reflections) > MAX_REFLECTION_HISTORY:
            self._reflections = self._reflections[-MAX_REFLECTION_HISTORY:]

        session_id = entry.context.get("session_id", "")
        if session_id:
            if session_id not in self._session_reflections:
                self._session_reflections[session_id] = []
            self._session_reflections[session_id].append(entry.id)

        return entry

    def analyze_session(self, session_id: str) -> List[ImprovementInsight]:
        entry_ids = self._session_reflections.get(session_id, [])
        session_entries = [
            r for r in self._reflections if r.id in entry_ids
        ]

        if len(session_entries) < MIN_SAMPLES_FOR_ADAPTATION:
            return []

        insights: List[ImprovementInsight] = []

        high_deviation = [
            e for e in session_entries if e.deviation_score > INSIGHT_CONFIDENCE_THRESHOLD
        ]
        if len(high_deviation) >= MIN_SAMPLES_FOR_ADAPTATION:
            avg_deviation = sum(e.deviation_score for e in high_deviation) / len(high_deviation)
            evidence_texts = [
                f"Deviation {e.deviation_score:.2f}: {e.decision_summary}"
                for e in high_deviation[:10]
            ]
            insight = ImprovementInsight(
                category=InsightCategory.ACCURACY,
                description=(
                    f"Session {session_id} shows {len(high_deviation)} outcomes with "
                    f"significant deviation (avg {avg_deviation:.2f}). "
                    "Reviewing decision calibration may improve accuracy."
                ),
                confidence=min(avg_deviation, 1.0),
                evidence=evidence_texts,
                action_items=[
                    "Recalibrate prediction confidence for high-deviation scenarios",
                    "Add guard conditions for decisions with uncertain outcomes",
                ],
                source_reflection_ids=[e.id for e in high_deviation],
            )
            insights.append(insight)

        error_entries = [
            e for e in session_entries
            if e.reflection_type == ReflectionType.ERROR_POSTMORTEM
        ]
        if error_entries:
            insight = ImprovementInsight(
                category=InsightCategory.SAFETY,
                description=(
                    f"Session {session_id} recorded {len(error_entries)} error "
                    "postmortems. Implementing preventive checks is recommended."
                ),
                confidence=min(0.5 + len(error_entries) * 0.1, 1.0),
                evidence=[
                    f"Error: {e.outcome}" for e in error_entries
                ],
                action_items=[
                    "Add error-prevention assertions before critical decision paths",
                    "Log error patterns for upstream model improvement",
                ],
                source_reflection_ids=[e.id for e in error_entries],
            )
            insights.append(insight)

        for insight in insights:
            self._insights.append(insight)

        return insights

    def generate_insights(
        self,
        min_confidence: float = INSIGHT_CONFIDENCE_THRESHOLD,
    ) -> List[ImprovementInsight]:
        if len(self._reflections) < MIN_SAMPLES_FOR_ADAPTATION:
            return []

        new_insights: List[ImprovementInsight] = []

        reflection_ids_used: set = set()
        for insight in self._insights:
            reflection_ids_used.update(insight.source_reflection_ids)

        recent = [
            r for r in self._reflections
            if r.id not in reflection_ids_used
        ]
        if len(recent) < MIN_SAMPLES_FOR_ADAPTATION:
            return []

        avg_deviation = sum(r.deviation_score for r in recent) / len(recent)
        if avg_deviation >= min_confidence:
            insight = ImprovementInsight(
                category=InsightCategory.CONSISTENCY,
                description=(
                    f"Average deviation of {avg_deviation:.2f} across "
                    f"{len(recent)} recent reflections exceeds threshold. "
                    "Strategy consistency should be reviewed."
                ),
                confidence=avg_deviation,
                evidence=[
                    f"Deviation {r.deviation_score:.2f}: {r.decision_summary}"
                    for r in recent[:10]
                ],
                action_items=[
                    "Audit high-deviation decisions for common failure modes",
                    "Reduce strategy variance in similar decision contexts",
                ],
                source_reflection_ids=[r.id for r in recent],
            )
            new_insights.append(insight)

        performance_entries = [
            r for r in recent
            if r.reflection_type == ReflectionType.PERFORMANCE_BENCHMARK
        ]
        if len(performance_entries) >= MIN_SAMPLES_FOR_ADAPTATION:
            insight = ImprovementInsight(
                category=InsightCategory.EFFICIENCY,
                description=(
                    f"Performance benchmarks across {len(performance_entries)} "
                    "decisions indicate opportunities for optimization."
                ),
                confidence=0.7,
                evidence=[
                    f"Benchmark: {e.outcome}" for e in performance_entries[:10]
                ],
                action_items=[
                    "Profile decision pipelines for latency bottlenecks",
                    "Cache frequently accessed strategy parameters",
                ],
                source_reflection_ids=[e.id for e in performance_entries],
            )
            new_insights.append(insight)

        new_insights = self._merge_related_insights(new_insights)

        for insight in new_insights:
            self._insights.append(insight)

        return new_insights

    def adapt_strategy(
        self,
        insight_id: str,
        original_strategy: Optional[Dict[str, Any]] = None,
        adapted_strategy: Optional[Dict[str, Any]] = None,
        rationale: str = "",
        impact_score: float = 0.5,
    ) -> StrategyAdaptation:
        now = _time_module.time()
        if now - self._last_adaptation_time < ADAPTATION_COOLDOWN_SECONDS:
            raise RuntimeError(
                f"Adaptation cooldown active: "
                f"{ADAPTATION_COOLDOWN_SECONDS - (now - self._last_adaptation_time):.0f}s remaining"
            )

        target_insight = None
        for i in self._insights:
            if i.id == insight_id:
                target_insight = i
                break
        if target_insight is None:
            raise ValueError(f"Insight {insight_id} not found")

        adaptation = StrategyAdaptation(
            insight_id=insight_id,
            original_strategy=dict(original_strategy) if original_strategy else {},
            adapted_strategy=dict(adapted_strategy) if adapted_strategy else {},
            adaptation_rationale=rationale,
            impact_score=impact_score,
        )

        self._adaptations.append(adaptation)
        self._last_adaptation_time = now

        return adaptation

    def apply_insight(self, insight_id: str) -> Optional[ImprovementInsight]:
        target_insight = None
        for i in self._insights:
            if i.id == insight_id:
                target_insight = i
                break
        if target_insight is None:
            return None

        if target_insight.status not in (
            ImprovementStatus.IDENTIFIED,
            ImprovementStatus.IN_PROGRESS,
        ):
            return target_insight

        target_insight.status = ImprovementStatus.APPLIED
        target_insight.applied_at = _time_module.time()
        return target_insight

    def verify_insight(
        self,
        insight_id: str,
        verified: bool = True,
    ) -> Optional[ImprovementInsight]:
        target_insight = None
        for i in self._insights:
            if i.id == insight_id:
                target_insight = i
                break
        if target_insight is None:
            return None

        if target_insight.status != ImprovementStatus.APPLIED:
            return target_insight

        if verified:
            target_insight.status = ImprovementStatus.VERIFIED
            target_insight.verified_at = _time_module.time()
        else:
            target_insight.status = ImprovementStatus.REVERTED

        return target_insight

    def list_active_adaptations(self) -> List[StrategyAdaptation]:
        return [a for a in self._adaptations if a.is_active]

    def _compute_deviation(self, actual: str, expected: str) -> float:
        if not actual or not expected:
            return 0.0

        actual_lower = actual.lower()
        expected_lower = expected.lower()

        if actual_lower == expected_lower:
            return 0.0

        actual_words = set(actual_lower.split())
        expected_words = set(expected_lower.split())

        if not expected_words:
            return 0.0

        intersection = actual_words & expected_words
        union = actual_words | expected_words

        jaccard = len(intersection) / len(union) if union else 0.0
        return 1.0 - jaccard

    def _merge_related_insights(
        self,
        insights: List[ImprovementInsight],
    ) -> List[ImprovementInsight]:
        if len(insights) <= 1:
            return insights

        merged: List[ImprovementInsight] = []
        used: set = set()

        for i, insight_a in enumerate(insights):
            if i in used:
                continue
            group = [insight_a]
            used.add(i)

            for j, insight_b in enumerate(insights):
                if j in used:
                    continue
                if insight_a.category == insight_b.category:
                    group.append(insight_b)
                    used.add(j)

            if len(group) == 1:
                merged.append(group[0])
            else:
                all_evidence: List[str] = []
                all_actions: List[str] = []
                all_sources: List[str] = []
                total_confidence = 0.0

                for g in group:
                    all_evidence.extend(g.evidence)
                    all_actions.extend(g.action_items)
                    all_sources.extend(g.source_reflection_ids)
                    total_confidence += g.confidence

                merged_insight = ImprovementInsight(
                    category=insight_a.category,
                    description=(
                        f"Merged insight from {len(group)} related findings: "
                        f"{insight_a.description}"
                    ),
                    confidence=min(total_confidence / len(group), 1.0),
                    evidence=all_evidence[:20],
                    action_items=list(dict.fromkeys(all_actions)),
                    source_reflection_ids=all_sources,
                )
                merged.append(merged_insight)

        return merged


def get_reflection_loop() -> ReflectionLoop:
    return ReflectionLoop.get_instance()