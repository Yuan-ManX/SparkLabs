"""
SparkLabs Agent - Feedback Loop

Agent outcome feedback collection and learning system for the
SparkLabs AI-native game engine. Collects structured feedback on
agent actions, builds a quality signal from playtest results,
compilation errors, and user ratings. Aggregates feedback into
actionable insights that guide future agent behavior, forming
a closed-loop improvement cycle.

Architecture:
  FeedbackLoop
    |-- FeedbackEntry (single piece of structured feedback)
    |-- FeedbackSource (origin: playtest, compiler, user, self-eval)
    |-- FeedbackAggregator (rolling statistics per action type)
    |-- ImprovementSuggestion (generated guidance from patterns)
    |-- QualitySignal (composite score from multiple sources)
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class FeedbackSource(Enum):
    PLAYTEST = "playtest"
    COMPILER = "compiler"
    USER = "user"
    SELF_EVAL = "self_eval"
    VALIDATOR = "validator"
    BENCHMARK = "benchmark"


class FeedbackSentiment(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class FeedbackSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class FeedbackEntry:
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: FeedbackSource = FeedbackSource.USER
    action_type: str = ""
    action_context: str = ""
    sentiment: FeedbackSentiment = FeedbackSentiment.NEUTRAL
    severity: FeedbackSeverity = FeedbackSeverity.INFO
    score: float = 0.5
    message: str = ""
    suggestion: str = ""
    session_id: str = ""
    project_name: str = ""
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "source": self.source.value,
            "action_type": self.action_type,
            "sentiment": self.sentiment.value,
            "score": self.score,
            "message": self.message[:200],
            "resolved": self.resolved,
        }


@dataclass
class ActionStats:
    action_type: str = ""
    total_entries: int = 0
    positive_count: int = 0
    neutral_count: int = 0
    negative_count: int = 0
    avg_score: float = 0.0
    last_feedback_at: float = 0.0
    common_suggestions: List[Tuple[str, int]] = field(default_factory=list)

    @property
    def satisfaction_rate(self) -> float:
        if self.total_entries == 0:
            return 100.0
        return round(self.positive_count / self.total_entries * 100, 1)

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "total": self.total_entries,
            "satisfaction_rate": self.satisfaction_rate,
            "avg_score": self.avg_score,
        }


@dataclass
class ImprovementSuggestion:
    suggestion_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action_type: str = ""
    suggestion: str = ""
    based_on_entries: int = 0
    confidence: float = 0.5
    applied: bool = False
    outcome_after_apply: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "suggestion_id": self.suggestion_id,
            "action_type": self.action_type,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "applied": self.applied,
        }


class FeedbackLoop:
    """
    Closed-loop feedback system for AI agent quality improvement.

    Collects feedback from playtests, compilation results, user ratings,
    and self-evaluation to build a quality signal. Aggregates per-action-type
    statistics and generates improvement suggestions when patterns of
    failure or dissatisfaction emerge. Provides a feedback-driven
    improvement cycle that makes the agent progressively better at
    game development tasks.
    """

    _instance: Optional["FeedbackLoop"] = None

    def __init__(self):
        self._entries: List[FeedbackEntry] = []
        self._action_stats: Dict[str, ActionStats] = {}
        self._suggestions: List[ImprovementSuggestion] = []
        self._max_entries: int = 1000
        self._aggregation_window: int = 100
        self._suggestion_threshold: int = 5

    @classmethod
    def get_instance(cls) -> "FeedbackLoop":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record(
        self,
        action_type: str,
        source: FeedbackSource,
        sentiment: FeedbackSentiment = FeedbackSentiment.NEUTRAL,
        score: float = 0.5,
        message: str = "",
        suggestion: str = "",
        severity: FeedbackSeverity = FeedbackSeverity.INFO,
        **kwargs,
    ) -> FeedbackEntry:
        entry = FeedbackEntry(
            source=source,
            action_type=action_type,
            sentiment=sentiment,
            severity=severity,
            score=max(0.0, min(1.0, score)),
            message=message,
            suggestion=suggestion,
            **kwargs,
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        self._update_stats(entry)
        self._check_suggestions(entry.action_type)

        return entry

    def record_playtest_result(self, action_type: str, passed: bool, message: str = "", session_id: str = "") -> FeedbackEntry:
        return self.record(
            action_type=action_type,
            source=FeedbackSource.PLAYTEST,
            sentiment=FeedbackSentiment.POSITIVE if passed else FeedbackSentiment.NEGATIVE,
            score=1.0 if passed else 0.0,
            message=message,
            session_id=session_id,
            severity=FeedbackSeverity.ERROR if not passed else FeedbackSeverity.INFO,
        )

    def record_compiler_result(self, action_type: str, errors: int, warnings: int, message: str = "") -> FeedbackEntry:
        if errors > 0:
            sentiment = FeedbackSentiment.NEGATIVE
            score = max(0.0, 1.0 - errors * 0.2)
            severity = FeedbackSeverity.ERROR
        elif warnings > 0:
            sentiment = FeedbackSentiment.NEUTRAL
            score = 0.7
            severity = FeedbackSeverity.WARNING
        else:
            sentiment = FeedbackSentiment.POSITIVE
            score = 1.0
            severity = FeedbackSeverity.INFO
        return self.record(
            action_type=action_type,
            source=FeedbackSource.COMPILER,
            sentiment=sentiment,
            score=score,
            message=message,
            severity=severity,
        )

    def record_user_rating(self, action_type: str, rating: int, comment: str = "", session_id: str = "") -> FeedbackEntry:
        score = rating / 5.0
        sentiment = FeedbackSentiment.POSITIVE if rating >= 4 else FeedbackSentiment.NEUTRAL if rating >= 2 else FeedbackSentiment.NEGATIVE
        return self.record(
            action_type=action_type,
            source=FeedbackSource.USER,
            sentiment=sentiment,
            score=score,
            message=comment,
            session_id=session_id,
        )

    def _update_stats(self, entry: FeedbackEntry) -> None:
        if entry.action_type not in self._action_stats:
            self._action_stats[entry.action_type] = ActionStats(action_type=entry.action_type)
        stats = self._action_stats[entry.action_type]
        stats.total_entries += 1
        if entry.sentiment == FeedbackSentiment.POSITIVE:
            stats.positive_count += 1
        elif entry.sentiment == FeedbackSentiment.NEUTRAL:
            stats.neutral_count += 1
        else:
            stats.negative_count += 1
        n = stats.total_entries
        stats.avg_score = stats.avg_score * (n - 1) / n + entry.score / n
        stats.last_feedback_at = entry.timestamp

    def _check_suggestions(self, action_type: str) -> None:
        stats = self._action_stats.get(action_type)
        if not stats:
            return
        recent = [e for e in self._entries[-self._aggregation_window:] if e.action_type == action_type]
        if len(recent) < self._suggestion_threshold:
            return

        negative_ratio = stats.negative_count / max(stats.total_entries, 1)
        if negative_ratio > 0.4:
            suggestion_texts = [e.suggestion for e in recent if e.suggestion]
            if suggestion_texts:
                most_common = max(set(suggestion_texts), key=suggestion_texts.count)
                suggestion = ImprovementSuggestion(
                    action_type=action_type,
                    suggestion=most_common,
                    based_on_entries=len(recent),
                    confidence=min(0.9, negative_ratio),
                )
                self._suggestions.append(suggestion)
                stats.common_suggestions.append((most_common, suggestion_texts.count(most_common)))

    def get_action_quality(self, action_type: str) -> Optional[ActionStats]:
        return self._action_stats.get(action_type)

    def get_all_action_stats(self) -> List[ActionStats]:
        return sorted(self._action_stats.values(), key=lambda s: s.total_entries, reverse=True)

    def get_pending_suggestions(self) -> List[ImprovementSuggestion]:
        return [s for s in self._suggestions if not s.applied]

    def apply_suggestion(self, suggestion_id: str) -> bool:
        for s in self._suggestions:
            if s.suggestion_id == suggestion_id:
                s.applied = True
                return True
        return False

    def get_quality_report(self) -> dict:
        all_stats = self.get_all_action_stats()
        top_performers = sorted(all_stats, key=lambda s: s.avg_score, reverse=True)[:3]
        needs_improvement = sorted(all_stats, key=lambda s: s.avg_score)[:3]
        return {
            "total_feedback": len(self._entries),
            "overall_satisfaction": round(
                sum(s.satisfaction_rate for s in all_stats) / max(len(all_stats), 1), 1
            ) if all_stats else 100.0,
            "top_performers": [s.to_dict() for s in top_performers],
            "needs_improvement": [s.to_dict() for s in needs_improvement],
            "pending_suggestions": len(self.get_pending_suggestions()),
        }

    def get_recent_feedback(self, limit: int = 20) -> List[FeedbackEntry]:
        return self._entries[-limit:]

    def get_feedback_by_source(self, source: FeedbackSource, limit: int = 50) -> List[FeedbackEntry]:
        return [e for e in self._entries if e.source == source][-limit:]

    def get_stats(self) -> dict:
        return {
            "total_entries": len(self._entries),
            "action_types": len(self._action_stats),
            "suggestions": len(self._suggestions),
            "pending_suggestions": len(self.get_pending_suggestions()),
            "avg_score": self._compute_global_avg(),
        }

    def _compute_global_avg(self) -> float:
        if not self._entries:
            return 0.0
        recent = self._entries[-self._aggregation_window:]
        return round(sum(e.score for e in recent) / len(recent), 3)

    def reset(self) -> None:
        self._entries.clear()
        self._action_stats.clear()
        self._suggestions.clear()


def get_feedback_loop() -> FeedbackLoop:
    return FeedbackLoop.get_instance()
