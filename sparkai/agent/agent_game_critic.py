"""
SparkLabs Agent - Game Critic

An AI agent that reviews games like a professional critic, analyzing
fun factor, pacing, difficulty curve, narrative cohesion, visual
coherence, audio design, accessibility, and replayability. Produces
qualitative scores, written critique, and actionable recommendations.

Architecture:
  GameCriticAgent (singleton)
    |-- ReviewSession, CriterionScore, CritiqueFinding, Recommendation,
    |   CriticReport, CriticSnapshot, CriticEvent
    |-- ReviewDimension, ReviewStatus, SeverityLevel, FindingCategory,
        CriticEventKind

Core Capabilities:
  - create_session / update_session / get_session / list_sessions:
    manage review sessions for games or builds.
  - score_criterion: assign a numeric score (0-10) to a review
    dimension (FUN, PACING, DIFFICULTY, NARRATIVE, VISUALS, AUDIO,
    ACCESSIBILITY, REPLAYABILITY, INNOVATION, POLISH).
  - add_finding: record a qualitative finding with severity and
    category (POSITIVE, NEGATIVE, SUGGESTION, BUG, OBSERVATION).
  - add_recommendation: add an actionable recommendation linked to
    findings.
  - generate_report: compile all scores, findings, and recommendations
    into a comprehensive CriticReport with an overall score, verdict,
    and written summary.
  - compare_sessions: compare two review sessions side by side,
    highlighting improvements and regressions.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and lifecycle management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`GameCriticAgent.get_instance` or the module-level
:func:`get_game_critic` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SESSIONS: int = 200
_MAX_SCORES_PER_SESSION: int = 20
_MAX_FINDINGS_PER_SESSION: int = 200
_MAX_RECOMMENDATIONS_PER_SESSION: int = 100
_MAX_REPORTS: int = 200
_MAX_EVENTS: int = 3000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict to keep ``len(store) <= max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list to keep ``len(store) <= max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Convert ``value`` into something safe to drop into a JSON payload."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Convert a dataclass instance to a plain dictionary."""
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ReviewDimension(Enum):
    """Dimensions of a game review."""
    FUN = "fun"
    PACING = "pacing"
    DIFFICULTY = "difficulty"
    NARRATIVE = "narrative"
    VISUALS = "visuals"
    AUDIO = "audio"
    ACCESSIBILITY = "accessibility"
    REPLAYABILITY = "replayability"
    INNOVATION = "innovation"
    POLISH = "polish"


class ReviewStatus(Enum):
    """Lifecycle status of a review session."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class SeverityLevel(Enum):
    """Severity of a finding."""
    INFO = "info"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class FindingCategory(Enum):
    """Category of a critique finding."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    SUGGESTION = "suggestion"
    BUG = "bug"
    OBSERVATION = "observation"


class CriticEventKind(Enum):
    """Audit event kinds emitted by the game critic agent."""
    SESSION_CREATED = "session_created"
    SESSION_UPDATED = "session_updated"
    SESSION_COMPLETED = "session_completed"
    CRITERION_SCORED = "criterion_scored"
    FINDING_ADDED = "finding_added"
    RECOMMENDATION_ADDED = "recommendation_added"
    REPORT_GENERATED = "report_generated"
    SESSIONS_COMPARED = "sessions_compared"
    SYSTEM_RESET = "system_reset"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CriterionScore:
    """A score for a single review dimension."""
    dimension: ReviewDimension
    score: float  # 0.0 - 10.0
    notes: str = ""
    scored_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CritiqueFinding:
    """A qualitative finding from the review."""
    finding_id: str
    category: FindingCategory
    severity: SeverityLevel
    dimension: ReviewDimension
    title: str
    description: str = ""
    location: str = ""  # e.g. "Level 3", "Main Menu"
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Recommendation:
    """An actionable recommendation from the review."""
    recommendation_id: str
    dimension: ReviewDimension
    priority: int  # 1 (highest) - 5 (lowest)
    title: str
    description: str = ""
    linked_finding_ids: List[str] = field(default_factory=list)
    estimated_effort: str = ""  # e.g. "low", "medium", "high"
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReviewSession:
    """A review session for a game or build."""
    session_id: str
    game_title: str
    build_version: str
    reviewer: str = "AI Critic"
    status: ReviewStatus = ReviewStatus.IN_PROGRESS
    playtime_minutes: float = 0.0
    genre: str = ""
    platform: str = ""
    tags: List[str] = field(default_factory=list)
    scores: List[CriterionScore] = field(default_factory=list)
    findings: List[CritiqueFinding] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    notes: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CriticReport:
    """A comprehensive review report."""
    report_id: str
    session_id: str
    game_title: str
    overall_score: float
    verdict: str
    summary: str
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    top_positives: List[str] = field(default_factory=list)
    top_negatives: List[str] = field(default_factory=list)
    priority_recommendations: List[str] = field(default_factory=list)
    total_findings: int = 0
    total_recommendations: int = 0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ComparisonResult:
    """Result of comparing two review sessions."""
    comparison_id: str
    session_a_id: str
    session_b_id: str
    score_deltas: Dict[str, float] = field(default_factory=dict)
    overall_delta: float = 0.0
    improvements: List[str] = field(default_factory=list)
    regressions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CriticStats:
    """Aggregate statistics."""
    total_sessions: int = 0
    completed_sessions: int = 0
    in_progress_sessions: int = 0
    total_scores: int = 0
    total_findings: int = 0
    total_recommendations: int = 0
    total_reports: int = 0
    total_comparisons: int = 0
    total_events: int = 0
    session_counter: int = 0
    finding_counter: int = 0
    recommendation_counter: int = 0
    report_counter: int = 0
    comparison_counter: int = 0
    event_counter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CriticSnapshot:
    """Point-in-time snapshot."""
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    reports: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CriticEvent:
    """An audit event."""
    event_id: str
    kind: CriticEventKind
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Game Critic Agent Singleton
# ---------------------------------------------------------------------------


class GameCriticAgent:
    """AI game critic that reviews games like a professional critic.

    Analyzes fun factor, pacing, difficulty curve, narrative cohesion,
    and other dimensions, producing scores, findings, recommendations,
    and comprehensive reports.
    """

    _instance: Optional["GameCriticAgent"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "GameCriticAgent":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._initialized = False
                    cls._instance = obj
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GameCriticAgent":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls()
        return cls._instance  # type: ignore[return-value]

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._inner_lock: threading.RLock = threading.RLock()
            self._sessions: Dict[str, ReviewSession] = {}
            self._reports: Dict[str, CriticReport] = {}
            self._comparisons: Dict[str, ComparisonResult] = {}
            self._events: List[CriticEvent] = []

            self._session_counter: int = 0
            self._finding_counter: int = 0
            self._recommendation_counter: int = 0
            self._report_counter: int = 0
            self._comparison_counter: int = 0
            self._event_counter: int = 0

            self._initialized: bool = True
            self._seed()

    # -- Event Recording ---------------------------------------------------

    def _record_event(self, kind: CriticEventKind, **data: Any) -> None:
        """Record an audit event."""
        event = CriticEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # -- Session Management ------------------------------------------------

    def create_session(
        self,
        game_title: str,
        build_version: str = "",
        reviewer: str = "AI Critic",
        genre: str = "",
        platform: str = "",
        tags: Optional[List[str]] = None,
        notes: str = "",
    ) -> ReviewSession:
        """Create a new review session."""
        with self._inner_lock:
            session = ReviewSession(
                session_id=_new_id("rev"),
                game_title=game_title,
                build_version=build_version,
                reviewer=reviewer,
                genre=genre,
                platform=platform,
                tags=tags or [],
                notes=notes,
            )
            self._sessions[session.session_id] = session
            self._session_counter += 1
            _evict_fifo_dict(self._sessions, _MAX_SESSIONS)
            self._record_event(
                CriticEventKind.SESSION_CREATED,
                session_id=session.session_id,
                game_title=game_title,
            )
            return session

    def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any],
    ) -> Optional[ReviewSession]:
        """Update a review session's mutable fields."""
        with self._inner_lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if "game_title" in updates:
                session.game_title = updates["game_title"]
            if "build_version" in updates:
                session.build_version = updates["build_version"]
            if "reviewer" in updates:
                session.reviewer = updates["reviewer"]
            if "playtime_minutes" in updates:
                session.playtime_minutes = float(updates["playtime_minutes"])
            if "genre" in updates:
                session.genre = updates["genre"]
            if "platform" in updates:
                session.platform = updates["platform"]
            if "tags" in updates:
                session.tags = updates["tags"]
            if "notes" in updates:
                session.notes = updates["notes"]
            if "status" in updates:
                session.status = ReviewStatus(updates["status"])
            session.updated_at = _now()
            self._record_event(
                CriticEventKind.SESSION_UPDATED,
                session_id=session_id,
            )
            return session

    def get_session(self, session_id: str) -> Optional[ReviewSession]:
        """Get a single review session by ID."""
        with self._inner_lock:
            return self._sessions.get(session_id)

    def list_sessions(
        self,
        status: Optional[ReviewStatus] = None,
    ) -> List[ReviewSession]:
        """List review sessions, optionally filtered by status."""
        with self._inner_lock:
            items = list(self._sessions.values())
            if status is not None:
                items = [s for s in items if s.status == status]
            return items

    def complete_session(self, session_id: str) -> Optional[ReviewSession]:
        """Mark a review session as completed."""
        with self._inner_lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.status = ReviewStatus.COMPLETED
            session.completed_at = _now()
            session.updated_at = _now()
            self._record_event(
                CriticEventKind.SESSION_COMPLETED,
                session_id=session_id,
            )
            return session

    # -- Scoring -----------------------------------------------------------

    def score_criterion(
        self,
        session_id: str,
        dimension: ReviewDimension,
        score: float,
        notes: str = "",
    ) -> Optional[CriterionScore]:
        """Assign a score (0-10) to a review dimension."""
        with self._inner_lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            clamped = max(0.0, min(10.0, float(score)))
            # Replace existing score for same dimension or add new
            existing_idx = None
            for i, s in enumerate(session.scores):
                if s.dimension == dimension:
                    existing_idx = i
                    break
            crit_score = CriterionScore(
                dimension=dimension,
                score=clamped,
                notes=notes,
            )
            if existing_idx is not None:
                session.scores[existing_idx] = crit_score
            else:
                if len(session.scores) >= _MAX_SCORES_PER_SESSION:
                    return None
                session.scores.append(crit_score)
            session.updated_at = _now()
            self._record_event(
                CriticEventKind.CRITERION_SCORED,
                session_id=session_id,
                dimension=dimension.value,
                score=clamped,
            )
            return crit_score

    def get_scores(self, session_id: str) -> List[CriterionScore]:
        """Get all criterion scores for a session."""
        with self._inner_lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            return list(session.scores)

    def get_overall_score(self, session_id: str) -> float:
        """Compute the weighted overall score for a session."""
        with self._inner_lock:
            session = self._sessions.get(session_id)
            if session is None or not session.scores:
                return 0.0
            total = sum(s.score for s in session.scores)
            return round(total / len(session.scores), 2)

    # -- Findings ----------------------------------------------------------

    def add_finding(
        self,
        session_id: str,
        category: FindingCategory,
        severity: SeverityLevel,
        dimension: ReviewDimension,
        title: str,
        description: str = "",
        location: str = "",
    ) -> Optional[CritiqueFinding]:
        """Add a qualitative finding to a review session."""
        with self._inner_lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if len(session.findings) >= _MAX_FINDINGS_PER_SESSION:
                return None
            finding = CritiqueFinding(
                finding_id=_new_id("fnd"),
                category=category,
                severity=severity,
                dimension=dimension,
                title=title,
                description=description,
                location=location,
            )
            session.findings.append(finding)
            self._finding_counter += 1
            session.updated_at = _now()
            self._record_event(
                CriticEventKind.FINDING_ADDED,
                session_id=session_id,
                finding_id=finding.finding_id,
                category=category.value,
            )
            return finding

    def list_findings(
        self,
        session_id: str,
        category: Optional[FindingCategory] = None,
        dimension: Optional[ReviewDimension] = None,
    ) -> List[CritiqueFinding]:
        """List findings for a session, optionally filtered."""
        with self._inner_lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            items = list(session.findings)
            if category is not None:
                items = [f for f in items if f.category == category]
            if dimension is not None:
                items = [f for f in items if f.dimension == dimension]
            return items

    # -- Recommendations ---------------------------------------------------

    def add_recommendation(
        self,
        session_id: str,
        dimension: ReviewDimension,
        priority: int,
        title: str,
        description: str = "",
        linked_finding_ids: Optional[List[str]] = None,
        estimated_effort: str = "",
    ) -> Optional[Recommendation]:
        """Add an actionable recommendation to a review session."""
        with self._inner_lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if len(session.recommendations) >= _MAX_RECOMMENDATIONS_PER_SESSION:
                return None
            rec = Recommendation(
                recommendation_id=_new_id("rec"),
                dimension=dimension,
                priority=max(1, min(5, int(priority))),
                title=title,
                description=description,
                linked_finding_ids=linked_finding_ids or [],
                estimated_effort=estimated_effort,
            )
            session.recommendations.append(rec)
            self._recommendation_counter += 1
            session.updated_at = _now()
            self._record_event(
                CriticEventKind.RECOMMENDATION_ADDED,
                session_id=session_id,
                recommendation_id=rec.recommendation_id,
            )
            return rec

    def list_recommendations(
        self,
        session_id: str,
        dimension: Optional[ReviewDimension] = None,
    ) -> List[Recommendation]:
        """List recommendations for a session, optionally filtered."""
        with self._inner_lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            items = list(session.recommendations)
            if dimension is not None:
                items = [r for r in items if r.dimension == dimension]
            # Sort by priority
            items.sort(key=lambda r: r.priority)
            return items

    # -- Report Generation -------------------------------------------------

    def generate_report(self, session_id: str) -> Optional[CriticReport]:
        """Generate a comprehensive review report for a session."""
        with self._inner_lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            overall = self.get_overall_score(session_id)
            # Build dimension scores dict
            dim_scores: Dict[str, float] = {}
            for s in session.scores:
                dim_scores[s.dimension.value] = s.score
            # Top positives and negatives
            positives = [f.title for f in session.findings if f.category == FindingCategory.POSITIVE]
            negatives = [f.title for f in session.findings if f.category == FindingCategory.NEGATIVE]
            # Priority recommendations (top 5)
            sorted_recs = sorted(session.recommendations, key=lambda r: r.priority)
            priority_recs = [r.title for r in sorted_recs[:5]]
            # Verdict
            if overall >= 9.0:
                verdict = "Masterpiece"
            elif overall >= 8.0:
                verdict = "Excellent"
            elif overall >= 7.0:
                verdict = "Great"
            elif overall >= 6.0:
                verdict = "Good"
            elif overall >= 5.0:
                verdict = "Average"
            elif overall >= 3.0:
                verdict = "Below Average"
            elif overall >= 1.0:
                verdict = "Poor"
            else:
                verdict = "Unrated"
            # Summary
            summary = (
                f"'{session.game_title}' (v{session.build_version}) reviewed by {session.reviewer}. "
                f"Overall score: {overall}/10 ({verdict}). "
                f"Scored across {len(session.scores)} dimensions. "
                f"Found {len(session.findings)} findings ({len(positives)} positive, {len(negatives)} negative). "
                f"Made {len(session.recommendations)} recommendations."
            )
            report = CriticReport(
                report_id=_new_id("rpt"),
                session_id=session_id,
                game_title=session.game_title,
                overall_score=overall,
                verdict=verdict,
                summary=summary,
                dimension_scores=dim_scores,
                top_positives=positives[:5],
                top_negatives=negatives[:5],
                priority_recommendations=priority_recs,
                total_findings=len(session.findings),
                total_recommendations=len(session.recommendations),
            )
            self._reports[report.report_id] = report
            self._report_counter += 1
            _evict_fifo_dict(self._reports, _MAX_REPORTS)
            self._record_event(
                CriticEventKind.REPORT_GENERATED,
                report_id=report.report_id,
                session_id=session_id,
                overall_score=overall,
            )
            return report

    def get_report(self, report_id: str) -> Optional[CriticReport]:
        """Get a stored report by ID."""
        with self._inner_lock:
            return self._reports.get(report_id)

    def list_reports(self, limit: int = 50) -> List[CriticReport]:
        """List recent reports."""
        with self._inner_lock:
            return list(self._reports.values())[-limit:]

    # -- Comparison --------------------------------------------------------

    def compare_sessions(
        self,
        session_a_id: str,
        session_b_id: str,
    ) -> Optional[ComparisonResult]:
        """Compare two review sessions side by side."""
        with self._inner_lock:
            session_a = self._sessions.get(session_a_id)
            session_b = self._sessions.get(session_b_id)
            if session_a is None or session_b is None:
                return None
            # Build score maps
            scores_a: Dict[str, float] = {s.dimension.value: s.score for s in session_a.scores}
            scores_b: Dict[str, float] = {s.dimension.value: s.score for s in session_b.scores}
            all_dims = set(scores_a.keys()) | set(scores_b.keys())
            score_deltas: Dict[str, float] = {}
            improvements: List[str] = []
            regressions: List[str] = []
            for dim in all_dims:
                val_a = scores_a.get(dim, 0.0)
                val_b = scores_b.get(dim, 0.0)
                delta = round(val_b - val_a, 2)
                score_deltas[dim] = delta
                if delta > 0.5:
                    improvements.append(f"{dim}: +{delta} (improved from {val_a} to {val_b})")
                elif delta < -0.5:
                    regressions.append(f"{dim}: {delta} (regressed from {val_a} to {val_b})")
            overall_a = self.get_overall_score(session_a_id)
            overall_b = self.get_overall_score(session_b_id)
            overall_delta = round(overall_b - overall_a, 2)
            comparison = ComparisonResult(
                comparison_id=_new_id("cmp"),
                session_a_id=session_a_id,
                session_b_id=session_b_id,
                score_deltas=score_deltas,
                overall_delta=overall_delta,
                improvements=improvements,
                regressions=regressions,
            )
            self._comparisons[comparison.comparison_id] = comparison
            self._comparison_counter += 1
            self._record_event(
                CriticEventKind.SESSIONS_COMPARED,
                comparison_id=comparison.comparison_id,
                session_a_id=session_a_id,
                session_b_id=session_b_id,
            )
            return comparison

    def list_comparisons(self, limit: int = 50) -> List[ComparisonResult]:
        """List recent comparisons."""
        with self._inner_lock:
            return list(self._comparisons.values())[-limit:]

    # -- Observability -----------------------------------------------------

    def list_events(self, limit: int = 100) -> List[CriticEvent]:
        """List recent audit events."""
        with self._inner_lock:
            return self._events[-limit:]

    def get_stats(self) -> CriticStats:
        """Return aggregate statistics."""
        with self._inner_lock:
            total_scores = sum(len(s.scores) for s in self._sessions.values())
            total_findings = sum(len(s.findings) for s in self._sessions.values())
            total_recs = sum(len(s.recommendations) for s in self._sessions.values())
            completed = sum(1 for s in self._sessions.values() if s.status == ReviewStatus.COMPLETED)
            in_progress = sum(1 for s in self._sessions.values() if s.status == ReviewStatus.IN_PROGRESS)
            return CriticStats(
                total_sessions=len(self._sessions),
                completed_sessions=completed,
                in_progress_sessions=in_progress,
                total_scores=total_scores,
                total_findings=total_findings,
                total_recommendations=total_recs,
                total_reports=len(self._reports),
                total_comparisons=len(self._comparisons),
                total_events=len(self._events),
                session_counter=self._session_counter,
                finding_counter=self._finding_counter,
                recommendation_counter=self._recommendation_counter,
                report_counter=self._report_counter,
                comparison_counter=self._comparison_counter,
                event_counter=self._event_counter,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a status dictionary for health checks."""
        with self._inner_lock:
            return {
                "initialized": self._initialized,
                "total_sessions": len(self._sessions),
                "total_reports": len(self._reports),
                "total_comparisons": len(self._comparisons),
                "total_events": len(self._events),
                "capacities": {
                    "max_sessions": _MAX_SESSIONS,
                    "max_scores_per_session": _MAX_SCORES_PER_SESSION,
                    "max_findings_per_session": _MAX_FINDINGS_PER_SESSION,
                    "max_recommendations_per_session": _MAX_RECOMMENDATIONS_PER_SESSION,
                    "max_reports": _MAX_REPORTS,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> CriticSnapshot:
        """Capture a point-in-time snapshot."""
        with self._inner_lock:
            return CriticSnapshot(
                sessions=[s.to_dict() for s in self._sessions.values()],
                reports=[r.to_dict() for r in self._reports.values()],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        """Reset to seed state."""
        with self._inner_lock:
            self._sessions.clear()
            self._reports.clear()
            self._comparisons.clear()
            self._events.clear()
            self._session_counter = 0
            self._finding_counter = 0
            self._recommendation_counter = 0
            self._report_counter = 0
            self._comparison_counter = 0
            self._event_counter = 0
            self._record_event(CriticEventKind.SYSTEM_RESET)
            self._seed()

    # -- Seeding -----------------------------------------------------------

    def _seed(self) -> None:
        """Seed with initial demo data."""
        # Session 1: A completed review
        session1 = self.create_session(
            game_title="Crystal Caverns",
            build_version="1.0.0",
            reviewer="AI Critic",
            genre="action_adventure",
            platform="PC",
            tags=["indie", "pixel_art"],
            notes="Full playthrough of main campaign.",
        )
        # Score multiple dimensions
        self.score_criterion(session1.session_id, ReviewDimension.FUN, 8.5, "Engaging core loop with satisfying combat.")
        self.score_criterion(session1.session_id, ReviewDimension.PACING, 7.0, "Middle section drags, but recovers in act 3.")
        self.score_criterion(session1.session_id, ReviewDimension.DIFFICULTY, 7.5, "Well-tuned for the target audience.")
        self.score_criterion(session1.session_id, ReviewDimension.NARRATIVE, 6.0, "Predictable but charming story.")
        self.score_criterion(session1.session_id, ReviewDimension.VISUALS, 9.0, "Gorgeous pixel art with great lighting.")
        self.score_criterion(session1.session_id, ReviewDimension.AUDIO, 8.0, "Memorable soundtrack and crisp SFX.")
        self.score_criterion(session1.session_id, ReviewDimension.ACCESSIBILITY, 5.5, "Limited options for colorblind players.")
        self.score_criterion(session1.session_id, ReviewDimension.REPLAYABILITY, 6.5, "Some optional content but low incentive.")
        self.score_criterion(session1.session_id, ReviewDimension.INNOVATION, 7.0, "Unique crystal-fusion mechanic.")
        self.score_criterion(session1.session_id, ReviewDimension.POLISH, 8.0, "Few bugs, smooth performance.")
        # Findings
        self.add_finding(
            session1.session_id, FindingCategory.POSITIVE, SeverityLevel.INFO,
            ReviewDimension.VISUALS, "Stunning Visual Design",
            "The crystal cavern environments are breathtaking with dynamic lighting.",
            "Levels 1-5",
        )
        self.add_finding(
            session1.session_id, FindingCategory.POSITIVE, SeverityLevel.INFO,
            ReviewDimension.AUDIO, "Excellent Soundtrack",
            "The adaptive music system creates immersive atmosphere during exploration and combat.",
        )
        self.add_finding(
            session1.session_id, FindingCategory.NEGATIVE, SeverityLevel.MODERATE,
            ReviewDimension.PACING, "Mid-Game Pacing Issues",
            "Levels 6-8 feel repetitive with similar enemy encounters.",
            "Levels 6-8",
        )
        self.add_finding(
            session1.session_id, FindingCategory.NEGATIVE, SeverityLevel.MAJOR,
            ReviewDimension.ACCESSIBILITY, "Missing Colorblind Support",
            "Crystal color-coding is the primary mechanic but no colorblind alternatives exist.",
        )
        self.add_finding(
            session1.session_id, FindingCategory.SUGGESTION, SeverityLevel.MINOR,
            ReviewDimension.REPLAYABILITY, "Add New Game Plus",
            "A NG+ mode with harder enemies and new crystal combinations would add replay value.",
        )
        self.add_finding(
            session1.session_id, FindingCategory.BUG, SeverityLevel.MINOR,
            ReviewDimension.POLISH, "Audio Desync in Cutscenes",
            "Occasional audio desync during boss intro cutscenes.",
            "Boss encounters",
        )
        # Recommendations
        self.add_recommendation(
            session1.session_id, ReviewDimension.ACCESSIBILITY, 1,
            "Add Colorblind Modes",
            "Implement pattern-based or shape-based crystal differentiation for colorblind players.",
            estimated_effort="medium",
        )
        self.add_recommendation(
            session1.session_id, ReviewDimension.PACING, 2,
            "Diversify Mid-Game Encounters",
            "Introduce new enemy types and mechanics in levels 6-8 to break repetition.",
            estimated_effort="medium",
        )
        self.add_recommendation(
            session1.session_id, ReviewDimension.REPLAYABILITY, 3,
            "Implement New Game Plus",
            "Add a NG+ mode with scaled difficulty and unlockable crystal combinations.",
            estimated_effort="high",
        )
        self.add_recommendation(
            session1.session_id, ReviewDimension.POLISH, 4,
            "Fix Audio Desync",
            "Investigate and fix the audio desync in boss intro cutscenes.",
            estimated_effort="low",
        )
        self.complete_session(session1.session_id)

        # Session 2: An in-progress review
        session2 = self.create_session(
            game_title="Crystal Caverns",
            build_version="1.1.0",
            reviewer="AI Critic",
            genre="action_adventure",
            platform="PC",
            tags=["indie", "pixel_art", "patch"],
            notes="Re-review after patch 1.1.0 addressing accessibility and pacing.",
        )
        self.score_criterion(session2.session_id, ReviewDimension.FUN, 8.5, "Still engaging.")
        self.score_criterion(session2.session_id, ReviewDimension.PACING, 8.0, "Mid-game significantly improved in 1.1.0.")
        self.score_criterion(session2.session_id, ReviewDimension.ACCESSIBILITY, 7.5, "Colorblind modes added, much better.")
        self.score_criterion(session2.session_id, ReviewDimension.VISUALS, 9.0, "Still gorgeous.")
        self.add_finding(
            session2.session_id, FindingCategory.POSITIVE, SeverityLevel.INFO,
            ReviewDimension.ACCESSIBILITY, "Colorblind Support Added",
            "Pattern-based crystal differentiation is now available in accessibility settings.",
        )


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_game_critic() -> GameCriticAgent:
    """Return the singleton GameCriticAgent instance."""
    return GameCriticAgent.get_instance()
