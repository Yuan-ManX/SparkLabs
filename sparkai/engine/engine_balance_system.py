"""
SparkLabs Engine - Balance System

Provides engine-level game balance analysis, parameter tuning, and
automated adjustment recommendations. Tracks win/loss outcomes, item
usage statistics, and player-skill distributions to detect imbalances
and propose data-driven corrections.

Architecture:
  BalanceSystem (singleton)
    |-- BalanceParameter, BalanceMetric, WinLossRecord, ItemUsageRecord,
    |   BalanceRule, BalanceAdjustment, BalanceAnalysis, BalanceReport,
    |   BalanceSnapshot, BalanceEvent
    |-- ParameterCategory, AdjustmentStatus, RuleOperator, RuleAction,
        AnalysisVerdict, BalanceEventKind

Core Capabilities:
  - register_parameter / update_parameter / get_parameter / list_parameters:
    manage tunable game parameters organized by category.
  - record_match / record_item_usage: capture gameplay outcome and item
    telemetry that feeds the balance analysis pipeline.
  - get_win_rate / get_usage_stats: aggregate query helpers.
  - analyze_balance: run the full analysis pipeline, producing a
    BalanceAnalysis with verdicts (BALANCED / FAVORS_PLAYER / FAVORS_ENEMY /
    TOO_EASY / TOO_HARD) for each parameter and matchup.
  - propose_adjustment / apply_adjustment / revert_adjustment: manage the
    lifecycle of balance changes, including A/B experiment linking.
  - create_rule / update_rule / delete_rule / list_rules /
    evaluate_rules: declarative auto-tuning rules that fire when metrics
    cross thresholds.
  - auto_tune: evaluate all rules and apply matching adjustments.
  - generate_report: produce a comprehensive BalanceReport suitable for
    designers and the AI critic agent.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and lifecycle management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`BalanceSystem.get_instance` or the module-level
:func:`get_balance_system` factory. All public methods are guarded by
the re-entrant lock.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PARAMETERS: int = 500
_MAX_MATCHES: int = 5000
_MAX_USAGE_RECORDS: int = 5000
_MAX_RULES: int = 200
_MAX_ADJUSTMENTS: int = 500
_MAX_ANALYSES: int = 200
_MAX_REPORTS: int = 100
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


class ParameterCategory(Enum):
    """Category of a balance parameter."""
    COMBAT = "combat"
    ECONOMY = "economy"
    PROGRESSION = "progression"
    DIFFICULTY = "difficulty"
    LOOT = "loot"
    MOVEMENT = "movement"
    SURVIVAL = "survival"
    CUSTOM = "custom"


class AdjustmentStatus(Enum):
    """Lifecycle status of a balance adjustment."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    APPLIED = "applied"
    REVERTED = "reverted"
    REJECTED = "rejected"


class RuleOperator(Enum):
    """Comparison operator for balance rules."""
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    EQ = "=="
    NEQ = "!="


class RuleAction(Enum):
    """Action a balance rule takes when triggered."""
    INCREASE = "increase"
    DECREASE = "decrease"
    SET_VALUE = "set_value"
    FLAG = "flag"
    NOTIFY = "notify"


class AnalysisVerdict(Enum):
    """Verdict for a single balance check."""
    BALANCED = "balanced"
    FAVORS_PLAYER = "favors_player"
    FAVORS_ENEMY = "favors_enemy"
    TOO_EASY = "too_easy"
    TOO_HARD = "too_hard"
    INSUFFICIENT_DATA = "insufficient_data"


class BalanceEventKind(Enum):
    """Audit event kinds emitted by the balance system."""
    PARAMETER_REGISTERED = "parameter_registered"
    PARAMETER_UPDATED = "parameter_updated"
    MATCH_RECORDED = "match_recorded"
    ITEM_USAGE_RECORDED = "item_usage_recorded"
    ANALYSIS_COMPLETED = "analysis_completed"
    ADJUSTMENT_PROPOSED = "adjustment_proposed"
    ADJUSTMENT_APPLIED = "adjustment_applied"
    ADJUSTMENT_REVERTED = "adjustment_reverted"
    ADJUSTMENT_REJECTED = "adjustment_rejected"
    RULE_CREATED = "rule_created"
    RULE_UPDATED = "rule_updated"
    RULE_DELETED = "rule_deleted"
    RULE_TRIGGERED = "rule_triggered"
    AUTO_TUNE_COMPLETED = "auto_tune_completed"
    REPORT_GENERATED = "report_generated"
    SYSTEM_RESET = "system_reset"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class BalanceParameter:
    """A tunable game parameter tracked by the balance system."""
    parameter_id: str
    name: str
    category: ParameterCategory
    current_value: float
    default_value: float
    min_value: float
    max_value: float
    description: str = ""
    unit: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WinLossRecord:
    """A single match outcome record."""
    record_id: str
    matchup: str
    player_id: str
    result: str  # "win" or "loss"
    duration_seconds: float = 0.0
    player_skill: float = 0.0
    enemy_skill: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    recorded_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ItemUsageRecord:
    """A single item usage telemetry record."""
    record_id: str
    item_id: str
    player_id: str
    usage_count: int = 1
    effectiveness: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    recorded_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BalanceRule:
    """A declarative auto-tuning rule."""
    rule_id: str
    name: str
    parameter_id: str
    metric: str
    operator: RuleOperator
    threshold: float
    action: RuleAction
    magnitude: float = 0.1
    target_value: Optional[float] = None
    enabled: bool = True
    description: str = ""
    last_triggered: Optional[str] = None
    trigger_count: int = 0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BalanceAdjustment:
    """A proposed or applied balance change."""
    adjustment_id: str
    parameter_id: str
    old_value: float
    new_value: float
    reason: str
    status: AdjustmentStatus = AdjustmentStatus.PROPOSED
    rule_id: Optional[str] = None
    experiment_id: Optional[str] = None
    analysis_id: Optional[str] = None
    proposed_at: str = field(default_factory=_now)
    applied_at: Optional[str] = None
    reverted_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParameterVerdict:
    """Balance verdict for a single parameter."""
    parameter_id: str
    parameter_name: str
    verdict: AnalysisVerdict
    win_rate: float
    sample_count: int
    deviation: float
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MatchupVerdict:
    """Balance verdict for a single matchup."""
    matchup: str
    verdict: AnalysisVerdict
    win_rate: float
    sample_count: int
    skill_gap: float
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BalanceAnalysis:
    """Result of a full balance analysis run."""
    analysis_id: str
    parameter_verdicts: List[ParameterVerdict] = field(default_factory=list)
    matchup_verdicts: List[MatchupVerdict] = field(default_factory=list)
    overall_health: float = 0.0
    total_matches: int = 0
    total_parameters: int = 0
    imbalanced_count: int = 0
    summary: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BalanceReport:
    """A comprehensive balance report for designers."""
    report_id: str
    analysis_id: str
    title: str
    executive_summary: str
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    risk_assessment: str = ""
    confidence_score: float = 0.0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BalanceStats:
    """Aggregate statistics for the balance system."""
    total_parameters: int = 0
    total_matches: int = 0
    total_usage_records: int = 0
    total_rules: int = 0
    active_rules: int = 0
    total_adjustments: int = 0
    applied_adjustments: int = 0
    reverted_adjustments: int = 0
    total_analyses: int = 0
    total_reports: int = 0
    total_events: int = 0
    parameter_counter: int = 0
    match_counter: int = 0
    usage_counter: int = 0
    rule_counter: int = 0
    adjustment_counter: int = 0
    analysis_counter: int = 0
    report_counter: int = 0
    event_counter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BalanceSnapshot:
    """A point-in-time snapshot of the entire balance system state."""
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    rules: List[Dict[str, Any]] = field(default_factory=list)
    adjustments: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BalanceEvent:
    """An audit event emitted by the balance system."""
    event_id: str
    kind: BalanceEventKind
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Balance System Singleton
# ---------------------------------------------------------------------------


class BalanceSystem:
    """Engine-level game balance system.

    Tracks parameters, match outcomes, and item usage to detect
    imbalances and propose data-driven adjustments. Supports
    declarative auto-tuning rules and comprehensive reporting.
    """

    _instance: Optional["BalanceSystem"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "BalanceSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._initialized = False
                    cls._instance = obj
        return cls._instance

    @classmethod
    def get_instance(cls) -> "BalanceSystem":
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
            self._parameters: Dict[str, BalanceParameter] = {}
            self._matches: List[WinLossRecord] = []
            self._usage_records: List[ItemUsageRecord] = []
            self._rules: Dict[str, BalanceRule] = {}
            self._adjustments: Dict[str, BalanceAdjustment] = {}
            self._analyses: Dict[str, BalanceAnalysis] = {}
            self._reports: Dict[str, BalanceReport] = {}
            self._events: List[BalanceEvent] = []

            self._parameter_counter: int = 0
            self._match_counter: int = 0
            self._usage_counter: int = 0
            self._rule_counter: int = 0
            self._adjustment_counter: int = 0
            self._analysis_counter: int = 0
            self._report_counter: int = 0
            self._event_counter: int = 0

            self._initialized: bool = True
            self._seed()

    # -- Event Recording ---------------------------------------------------

    def _record_event(
        self,
        kind: BalanceEventKind,
        **data: Any,
    ) -> None:
        """Record an audit event."""
        event = BalanceEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # -- Parameter Management ----------------------------------------------

    def register_parameter(
        self,
        name: str,
        category: ParameterCategory,
        current_value: float,
        default_value: float,
        min_value: float = 0.0,
        max_value: float = 1.0,
        description: str = "",
        unit: str = "",
        tags: Optional[List[str]] = None,
    ) -> BalanceParameter:
        """Register a new tunable balance parameter."""
        with self._inner_lock:
            param = BalanceParameter(
                parameter_id=_new_id("par"),
                name=name,
                category=category,
                current_value=current_value,
                default_value=default_value,
                min_value=min_value,
                max_value=max_value,
                description=description,
                unit=unit,
                tags=tags or [],
            )
            self._parameters[param.parameter_id] = param
            self._parameter_counter += 1
            _evict_fifo_dict(self._parameters, _MAX_PARAMETERS)
            self._record_event(
                BalanceEventKind.PARAMETER_REGISTERED,
                parameter_id=param.parameter_id,
                name=name,
                category=category.value,
            )
            return param

    def update_parameter(
        self,
        parameter_id: str,
        updates: Dict[str, Any],
    ) -> Optional[BalanceParameter]:
        """Update a balance parameter's mutable fields."""
        with self._inner_lock:
            param = self._parameters.get(parameter_id)
            if param is None:
                return None
            if "name" in updates:
                param.name = updates["name"]
            if "current_value" in updates:
                param.current_value = float(updates["current_value"])
            if "default_value" in updates:
                param.default_value = float(updates["default_value"])
            if "min_value" in updates:
                param.min_value = float(updates["min_value"])
            if "max_value" in updates:
                param.max_value = float(updates["max_value"])
            if "description" in updates:
                param.description = updates["description"]
            if "unit" in updates:
                param.unit = updates["unit"]
            if "tags" in updates:
                param.tags = updates["tags"]
            param.updated_at = _now()
            self._record_event(
                BalanceEventKind.PARAMETER_UPDATED,
                parameter_id=parameter_id,
            )
            return param

    def get_parameter(self, parameter_id: str) -> Optional[BalanceParameter]:
        """Get a single parameter by ID."""
        with self._inner_lock:
            return self._parameters.get(parameter_id)

    def list_parameters(
        self,
        category: Optional[ParameterCategory] = None,
    ) -> List[BalanceParameter]:
        """List parameters, optionally filtered by category."""
        with self._inner_lock:
            items = list(self._parameters.values())
            if category is not None:
                items = [p for p in items if p.category == category]
            return items

    def delete_parameter(self, parameter_id: str) -> bool:
        """Delete a balance parameter."""
        with self._inner_lock:
            if parameter_id not in self._parameters:
                return False
            self._parameters.pop(parameter_id, None)
            return True

    # -- Match Tracking ----------------------------------------------------

    def record_match(
        self,
        matchup: str,
        player_id: str,
        result: str,
        duration_seconds: float = 0.0,
        player_skill: float = 0.0,
        enemy_skill: float = 0.0,
        context: Optional[Dict[str, Any]] = None,
    ) -> WinLossRecord:
        """Record a match outcome for balance analysis."""
        with self._inner_lock:
            record = WinLossRecord(
                record_id=_new_id("mch"),
                matchup=matchup,
                player_id=player_id,
                result=result.lower(),
                duration_seconds=duration_seconds,
                player_skill=player_skill,
                enemy_skill=enemy_skill,
                context=context or {},
            )
            self._matches.append(record)
            self._match_counter += 1
            _evict_fifo_list(self._matches, _MAX_MATCHES)
            self._record_event(
                BalanceEventKind.MATCH_RECORDED,
                record_id=record.record_id,
                matchup=matchup,
                result=result,
            )
            return record

    def get_win_rate(
        self,
        matchup: Optional[str] = None,
    ) -> float:
        """Compute the win rate, optionally filtered by matchup."""
        with self._inner_lock:
            matches = self._matches
            if matchup is not None:
                matches = [m for m in matches if m.matchup == matchup]
            if not matches:
                return 0.5
            wins = sum(1 for m in matches if m.result == "win")
            return wins / len(matches)

    def list_matches(
        self,
        matchup: Optional[str] = None,
        limit: int = 100,
    ) -> List[WinLossRecord]:
        """List match records, optionally filtered by matchup."""
        with self._inner_lock:
            matches = self._matches
            if matchup is not None:
                matches = [m for m in matches if m.matchup == matchup]
            return matches[-limit:]

    # -- Item Usage Tracking -----------------------------------------------

    def record_item_usage(
        self,
        item_id: str,
        player_id: str,
        usage_count: int = 1,
        effectiveness: float = 0.0,
        context: Optional[Dict[str, Any]] = None,
    ) -> ItemUsageRecord:
        """Record an item usage telemetry entry."""
        with self._inner_lock:
            record = ItemUsageRecord(
                record_id=_new_id("usg"),
                item_id=item_id,
                player_id=player_id,
                usage_count=usage_count,
                effectiveness=effectiveness,
                context=context or {},
            )
            self._usage_records.append(record)
            self._usage_counter += 1
            _evict_fifo_list(self._usage_records, _MAX_USAGE_RECORDS)
            self._record_event(
                BalanceEventKind.ITEM_USAGE_RECORDED,
                record_id=record.record_id,
                item_id=item_id,
            )
            return record

    def get_usage_stats(
        self,
        item_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Aggregate item usage statistics."""
        with self._inner_lock:
            records = self._usage_records
            if item_id is not None:
                records = [r for r in records if r.item_id == item_id]
            # Group by item_id
            groups: Dict[str, List[ItemUsageRecord]] = {}
            for r in records:
                groups.setdefault(r.item_id, []).append(r)
            stats: List[Dict[str, Any]] = []
            for iid, group in groups.items():
                total_usage = sum(r.usage_count for r in group)
                avg_eff = sum(r.effectiveness for r in group) / max(1, len(group))
                stats.append({
                    "item_id": iid,
                    "total_uses": total_usage,
                    "session_count": len(group),
                    "average_effectiveness": round(avg_eff, 4),
                })
            stats.sort(key=lambda s: s["total_uses"], reverse=True)
            return stats

    def list_usage_records(
        self,
        item_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ItemUsageRecord]:
        """List raw usage records, optionally filtered by item."""
        with self._inner_lock:
            records = self._usage_records
            if item_id is not None:
                records = [r for r in records if r.item_id == item_id]
            return records[-limit:]

    # -- Balance Analysis --------------------------------------------------

    def analyze_balance(self) -> BalanceAnalysis:
        """Run the full balance analysis pipeline.

        Examines win rates per matchup, parameter deviations from
        defaults, and item usage distribution to produce verdicts
        and an overall health score.
        """
        with self._inner_lock:
            # Group matches by matchup
            matchup_groups: Dict[str, List[WinLossRecord]] = {}
            for m in self._matches:
                matchup_groups.setdefault(m.matchup, []).append(m)

            matchup_verdicts: List[MatchupVerdict] = []
            for matchup, matches in matchup_groups.items():
                wins = sum(1 for m in matches if m.result == "win")
                win_rate = wins / max(1, len(matches))
                avg_skill_gap = sum(
                    m.player_skill - m.enemy_skill for m in matches
                ) / max(1, len(matches))
                if len(matches) < 10:
                    verdict = AnalysisVerdict.INSUFFICIENT_DATA
                elif win_rate > 0.65:
                    verdict = AnalysisVerdict.TOO_EASY
                elif win_rate < 0.35:
                    verdict = AnalysisVerdict.TOO_HARD
                else:
                    verdict = AnalysisVerdict.BALANCED
                rec = ""
                if verdict == AnalysisVerdict.TOO_EASY:
                    rec = "Consider increasing enemy strength or reducing player advantages."
                elif verdict == AnalysisVerdict.TOO_HARD:
                    rec = "Consider reducing enemy strength or adding player buffs."
                matchup_verdicts.append(MatchupVerdict(
                    matchup=matchup,
                    verdict=verdict,
                    win_rate=round(win_rate, 4),
                    sample_count=len(matches),
                    skill_gap=round(avg_skill_gap, 4),
                    recommendation=rec,
                ))

            # Parameter verdicts based on deviation from default
            parameter_verdicts: List[ParameterVerdict] = []
            for param in self._parameters.values():
                deviation = abs(param.current_value - param.default_value)
                rel_dev = deviation / max(0.001, abs(param.default_value))
                # Use overall win rate as a proxy
                overall_wr = self.get_win_rate()
                if overall_wr > 0.65:
                    verdict = AnalysisVerdict.FAVORS_PLAYER
                elif overall_wr < 0.35:
                    verdict = AnalysisVerdict.FAVORS_ENEMY
                elif rel_dev > 0.5:
                    verdict = AnalysisVerdict.FAVORS_PLAYER if param.current_value > param.default_value else AnalysisVerdict.FAVORS_ENEMY
                else:
                    verdict = AnalysisVerdict.BALANCED
                rec = ""
                if verdict == AnalysisVerdict.FAVORS_PLAYER:
                    rec = f"Reduce {param.name} toward default {param.default_value}."
                elif verdict == AnalysisVerdict.FAVORS_ENEMY:
                    rec = f"Increase {param.name} toward default {param.default_value}."
                parameter_verdicts.append(ParameterVerdict(
                    parameter_id=param.parameter_id,
                    parameter_name=param.name,
                    verdict=verdict,
                    win_rate=round(overall_wr, 4),
                    sample_count=len(self._matches),
                    deviation=round(rel_dev, 4),
                    recommendation=rec,
                ))

            # Overall health: higher is better (0.0 - 1.0)
            balanced_count = sum(
                1 for v in matchup_verdicts if v.verdict == AnalysisVerdict.BALANCED
            ) + sum(
                1 for v in parameter_verdicts if v.verdict == AnalysisVerdict.BALANCED
            )
            total_checks = len(matchup_verdicts) + len(parameter_verdicts)
            overall_health = balanced_count / max(1, total_checks)
            imbalanced = total_checks - balanced_count

            analysis = BalanceAnalysis(
                analysis_id=_new_id("anl"),
                parameter_verdicts=parameter_verdicts,
                matchup_verdicts=matchup_verdicts,
                overall_health=round(overall_health, 4),
                total_matches=len(self._matches),
                total_parameters=len(self._parameters),
                imbalanced_count=imbalanced,
                summary=f"Analyzed {len(self._matches)} matches across {len(matchup_groups)} matchups. "
                        f"Health: {round(overall_health * 100, 1)}%. {imbalanced} imbalanced checks found.",
            )
            self._analyses[analysis.analysis_id] = analysis
            self._analysis_counter += 1
            _evict_fifo_dict(self._analyses, _MAX_ANALYSES)
            self._record_event(
                BalanceEventKind.ANALYSIS_COMPLETED,
                analysis_id=analysis.analysis_id,
                health=round(overall_health, 4),
            )
            return analysis

    def get_analysis(self, analysis_id: str) -> Optional[BalanceAnalysis]:
        """Get a stored analysis by ID."""
        with self._inner_lock:
            return self._analyses.get(analysis_id)

    def list_analyses(self, limit: int = 50) -> List[BalanceAnalysis]:
        """List recent analyses."""
        with self._inner_lock:
            return list(self._analyses.values())[-limit:]

    # -- Adjustments -------------------------------------------------------

    def propose_adjustment(
        self,
        parameter_id: str,
        new_value: float,
        reason: str,
        rule_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        analysis_id: Optional[str] = None,
    ) -> Optional[BalanceAdjustment]:
        """Propose a balance adjustment for review."""
        with self._inner_lock:
            param = self._parameters.get(parameter_id)
            if param is None:
                return None
            adj = BalanceAdjustment(
                adjustment_id=_new_id("adj"),
                parameter_id=parameter_id,
                old_value=param.current_value,
                new_value=new_value,
                reason=reason,
                status=AdjustmentStatus.PROPOSED,
                rule_id=rule_id,
                experiment_id=experiment_id,
                analysis_id=analysis_id,
            )
            self._adjustments[adj.adjustment_id] = adj
            self._adjustment_counter += 1
            _evict_fifo_dict(self._adjustments, _MAX_ADJUSTMENTS)
            self._record_event(
                BalanceEventKind.ADJUSTMENT_PROPOSED,
                adjustment_id=adj.adjustment_id,
                parameter_id=parameter_id,
            )
            return adj

    def apply_adjustment(self, adjustment_id: str) -> Optional[BalanceAdjustment]:
        """Apply a proposed adjustment, updating the parameter value."""
        with self._inner_lock:
            adj = self._adjustments.get(adjustment_id)
            if adj is None or adj.status not in (AdjustmentStatus.PROPOSED, AdjustmentStatus.APPROVED):
                return None
            param = self._parameters.get(adj.parameter_id)
            if param is None:
                return None
            param.current_value = adj.new_value
            param.updated_at = _now()
            adj.status = AdjustmentStatus.APPLIED
            adj.applied_at = _now()
            self._record_event(
                BalanceEventKind.ADJUSTMENT_APPLIED,
                adjustment_id=adjustment_id,
                parameter_id=adj.parameter_id,
            )
            return adj

    def revert_adjustment(self, adjustment_id: str) -> Optional[BalanceAdjustment]:
        """Revert an applied adjustment, restoring the old value."""
        with self._inner_lock:
            adj = self._adjustments.get(adjustment_id)
            if adj is None or adj.status != AdjustmentStatus.APPLIED:
                return None
            param = self._parameters.get(adj.parameter_id)
            if param is None:
                return None
            param.current_value = adj.old_value
            param.updated_at = _now()
            adj.status = AdjustmentStatus.REVERTED
            adj.reverted_at = _now()
            self._record_event(
                BalanceEventKind.ADJUSTMENT_REVERTED,
                adjustment_id=adjustment_id,
                parameter_id=adj.parameter_id,
            )
            return adj

    def reject_adjustment(self, adjustment_id: str) -> Optional[BalanceAdjustment]:
        """Reject a proposed adjustment."""
        with self._inner_lock:
            adj = self._adjustments.get(adjustment_id)
            if adj is None or adj.status != AdjustmentStatus.PROPOSED:
                return None
            adj.status = AdjustmentStatus.REJECTED
            self._record_event(
                BalanceEventKind.ADJUSTMENT_REJECTED,
                adjustment_id=adjustment_id,
            )
            return adj

    def list_adjustments(
        self,
        status: Optional[AdjustmentStatus] = None,
        parameter_id: Optional[str] = None,
    ) -> List[BalanceAdjustment]:
        """List adjustments, optionally filtered."""
        with self._inner_lock:
            items = list(self._adjustments.values())
            if status is not None:
                items = [a for a in items if a.status == status]
            if parameter_id is not None:
                items = [a for a in items if a.parameter_id == parameter_id]
            return items

    # -- Rules -------------------------------------------------------------

    def create_rule(
        self,
        name: str,
        parameter_id: str,
        metric: str,
        operator: RuleOperator,
        threshold: float,
        action: RuleAction,
        magnitude: float = 0.1,
        target_value: Optional[float] = None,
        description: str = "",
    ) -> Optional[BalanceRule]:
        """Create a declarative auto-tuning rule."""
        with self._inner_lock:
            if parameter_id not in self._parameters:
                return None
            rule = BalanceRule(
                rule_id=_new_id("rul"),
                name=name,
                parameter_id=parameter_id,
                metric=metric,
                operator=operator,
                threshold=threshold,
                action=action,
                magnitude=magnitude,
                target_value=target_value,
                description=description,
            )
            self._rules[rule.rule_id] = rule
            self._rule_counter += 1
            _evict_fifo_dict(self._rules, _MAX_RULES)
            self._record_event(
                BalanceEventKind.RULE_CREATED,
                rule_id=rule.rule_id,
                name=name,
            )
            return rule

    def update_rule(
        self,
        rule_id: str,
        updates: Dict[str, Any],
    ) -> Optional[BalanceRule]:
        """Update a balance rule's mutable fields."""
        with self._inner_lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return None
            if "name" in updates:
                rule.name = updates["name"]
            if "metric" in updates:
                rule.metric = updates["metric"]
            if "operator" in updates:
                rule.operator = RuleOperator(updates["operator"])
            if "threshold" in updates:
                rule.threshold = float(updates["threshold"])
            if "action" in updates:
                rule.action = RuleAction(updates["action"])
            if "magnitude" in updates:
                rule.magnitude = float(updates["magnitude"])
            if "target_value" in updates:
                rule.target_value = updates["target_value"]
            if "enabled" in updates:
                rule.enabled = bool(updates["enabled"])
            if "description" in updates:
                rule.description = updates["description"]
            rule.updated_at = _now()
            self._record_event(
                BalanceEventKind.RULE_UPDATED,
                rule_id=rule_id,
            )
            return rule

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a balance rule."""
        with self._inner_lock:
            if rule_id not in self._rules:
                return False
            self._rules.pop(rule_id, None)
            self._record_event(
                BalanceEventKind.RULE_DELETED,
                rule_id=rule_id,
            )
            return True

    def list_rules(self, enabled_only: bool = False) -> List[BalanceRule]:
        """List balance rules, optionally only enabled ones."""
        with self._inner_lock:
            items = list(self._rules.values())
            if enabled_only:
                items = [r for r in items if r.enabled]
            return items

    def get_rule(self, rule_id: str) -> Optional[BalanceRule]:
        """Get a single rule by ID."""
        with self._inner_lock:
            return self._rules.get(rule_id)

    def _evaluate_rule(self, rule: BalanceRule) -> Tuple[bool, float]:
        """Evaluate a rule against current metrics. Returns (triggered, metric_value)."""
        param = self._parameters.get(rule.parameter_id)
        if param is None:
            return False, 0.0
        # Resolve metric value
        if rule.metric == "win_rate":
            value = self.get_win_rate()
        elif rule.metric == "parameter_value":
            value = param.current_value
        elif rule.metric == "usage_count":
            stats = self.get_usage_stats()
            value = sum(s["total_uses"] for s in stats)
        else:
            # Try to resolve as a numeric context key from matches
            value = 0.0
        # Compare
        op = rule.operator
        if op == RuleOperator.GT:
            triggered = value > rule.threshold
        elif op == RuleOperator.LT:
            triggered = value < rule.threshold
        elif op == RuleOperator.GTE:
            triggered = value >= rule.threshold
        elif op == RuleOperator.LTE:
            triggered = value <= rule.threshold
        elif op == RuleOperator.EQ:
            triggered = abs(value - rule.threshold) < 1e-6
        elif op == RuleOperator.NEQ:
            triggered = abs(value - rule.threshold) >= 1e-6
        else:
            triggered = False
        return triggered, value

    def auto_tune(self) -> List[BalanceAdjustment]:
        """Evaluate all enabled rules and apply matching adjustments.

        Returns the list of adjustments that were created and applied.
        """
        with self._inner_lock:
            applied: List[BalanceAdjustment] = []
            rules = [r for r in self._rules.values() if r.enabled]
            for rule in rules:
                triggered, metric_value = self._evaluate_rule(rule)
                if not triggered:
                    continue
                param = self._parameters.get(rule.parameter_id)
                if param is None:
                    continue
                # Compute new value
                if rule.action == RuleAction.INCREASE:
                    new_val = param.current_value * (1.0 + rule.magnitude)
                elif rule.action == RuleAction.DECREASE:
                    new_val = param.current_value * (1.0 - rule.magnitude)
                elif rule.action == RuleAction.SET_VALUE:
                    new_val = rule.target_value if rule.target_value is not None else param.current_value
                else:
                    # FLAG or NOTIFY: no value change, just record
                    new_val = param.current_value
                new_val = max(param.min_value, min(param.max_value, new_val))
                adj = self.propose_adjustment(
                    parameter_id=rule.parameter_id,
                    new_value=new_val,
                    reason=f"Auto-tune rule '{rule.name}' triggered: {rule.metric} {rule.operator.value} {rule.threshold} (actual: {round(metric_value, 4)})",
                    rule_id=rule.rule_id,
                )
                if adj is not None:
                    applied_adj = self.apply_adjustment(adj.adjustment_id)
                    if applied_adj is not None:
                        applied.append(applied_adj)
                        rule.last_triggered = _now()
                        rule.trigger_count += 1
                        self._record_event(
                            BalanceEventKind.RULE_TRIGGERED,
                            rule_id=rule.rule_id,
                            adjustment_id=adj.adjustment_id,
                        )
            self._record_event(
                BalanceEventKind.AUTO_TUNE_COMPLETED,
                adjustments_applied=len(applied),
            )
            return applied

    # -- Reporting ---------------------------------------------------------

    def generate_report(
        self,
        analysis_id: Optional[str] = None,
        title: str = "Balance Report",
    ) -> BalanceReport:
        """Generate a comprehensive balance report.

        If ``analysis_id`` is None, a fresh analysis is run.
        """
        with self._inner_lock:
            if analysis_id is None:
                analysis = self.analyze_balance()
                analysis_id = analysis.analysis_id
            else:
                analysis = self._analyses.get(analysis_id)
                if analysis is None:
                    analysis = self.analyze_balance()
                    analysis_id = analysis.analysis_id

            findings: List[str] = []
            recommendations: List[str] = []
            for mv in analysis.matchup_verdicts:
                if mv.verdict != AnalysisVerdict.BALANCED:
                    findings.append(
                        f"Matchup '{mv.matchup}': {mv.verdict.value} "
                        f"(win rate {mv.win_rate:.1%}, {mv.sample_count} matches)"
                    )
                    if mv.recommendation:
                        recommendations.append(mv.recommendation)
            for pv in analysis.parameter_verdicts:
                if pv.verdict not in (AnalysisVerdict.BALANCED, AnalysisVerdict.INSUFFICIENT_DATA):
                    findings.append(
                        f"Parameter '{pv.parameter_name}': {pv.verdict.value} "
                        f"(deviation {pv.deviation:.1%})"
                    )
                    if pv.recommendation:
                        recommendations.append(pv.recommendation)

            if not findings:
                findings.append("All checks within balanced range.")
            if not recommendations:
                recommendations.append("No immediate adjustments needed. Continue monitoring.")

            health_pct = analysis.overall_health * 100
            if health_pct >= 80:
                risk = "Low risk. Game balance is healthy."
            elif health_pct >= 60:
                risk = "Moderate risk. Some imbalances detected, monitor closely."
            elif health_pct >= 40:
                risk = "High risk. Multiple imbalances require attention."
            else:
                risk = "Critical risk. Immediate balance intervention recommended."

            confidence = min(1.0, analysis.total_matches / 100.0)

            report = BalanceReport(
                report_id=_new_id("rpt"),
                analysis_id=analysis_id,
                title=title,
                executive_summary=f"Balance health: {health_pct:.1f}%. "
                                  f"{analysis.imbalanced_count} imbalanced checks out of "
                                  f"{len(analysis.matchup_verdicts) + len(analysis.parameter_verdicts)} total. "
                                  f"Based on {analysis.total_matches} matches.",
                findings=findings,
                recommendations=recommendations,
                risk_assessment=risk,
                confidence_score=round(confidence, 4),
            )
            self._reports[report.report_id] = report
            self._report_counter += 1
            _evict_fifo_dict(self._reports, _MAX_REPORTS)
            self._record_event(
                BalanceEventKind.REPORT_GENERATED,
                report_id=report.report_id,
            )
            return report

    def get_report(self, report_id: str) -> Optional[BalanceReport]:
        """Get a stored report by ID."""
        with self._inner_lock:
            return self._reports.get(report_id)

    def list_reports(self, limit: int = 50) -> List[BalanceReport]:
        """List recent reports."""
        with self._inner_lock:
            return list(self._reports.values())[-limit:]

    # -- Observability -----------------------------------------------------

    def list_events(self, limit: int = 100) -> List[BalanceEvent]:
        """List recent audit events."""
        with self._inner_lock:
            return self._events[-limit:]

    def get_stats(self) -> BalanceStats:
        """Return aggregate statistics."""
        with self._inner_lock:
            return BalanceStats(
                total_parameters=len(self._parameters),
                total_matches=len(self._matches),
                total_usage_records=len(self._usage_records),
                total_rules=len(self._rules),
                active_rules=sum(1 for r in self._rules.values() if r.enabled),
                total_adjustments=len(self._adjustments),
                applied_adjustments=sum(1 for a in self._adjustments.values() if a.status == AdjustmentStatus.APPLIED),
                reverted_adjustments=sum(1 for a in self._adjustments.values() if a.status == AdjustmentStatus.REVERTED),
                total_analyses=len(self._analyses),
                total_reports=len(self._reports),
                total_events=len(self._events),
                parameter_counter=self._parameter_counter,
                match_counter=self._match_counter,
                usage_counter=self._usage_counter,
                rule_counter=self._rule_counter,
                adjustment_counter=self._adjustment_counter,
                analysis_counter=self._analysis_counter,
                report_counter=self._report_counter,
                event_counter=self._event_counter,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a status dictionary for health checks."""
        with self._inner_lock:
            return {
                "initialized": self._initialized,
                "total_parameters": len(self._parameters),
                "total_matches": len(self._matches),
                "total_usage_records": len(self._usage_records),
                "total_rules": len(self._rules),
                "total_adjustments": len(self._adjustments),
                "total_analyses": len(self._analyses),
                "total_reports": len(self._reports),
                "total_events": len(self._events),
                "capacities": {
                    "max_parameters": _MAX_PARAMETERS,
                    "max_matches": _MAX_MATCHES,
                    "max_usage_records": _MAX_USAGE_RECORDS,
                    "max_rules": _MAX_RULES,
                    "max_adjustments": _MAX_ADJUSTMENTS,
                    "max_analyses": _MAX_ANALYSES,
                    "max_reports": _MAX_REPORTS,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> BalanceSnapshot:
        """Capture a point-in-time snapshot of the full state."""
        with self._inner_lock:
            return BalanceSnapshot(
                parameters=[p.to_dict() for p in self._parameters.values()],
                rules=[r.to_dict() for r in self._rules.values()],
                adjustments=[a.to_dict() for a in self._adjustments.values()],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        """Reset the balance system to its seed state."""
        with self._inner_lock:
            self._parameters.clear()
            self._matches.clear()
            self._usage_records.clear()
            self._rules.clear()
            self._adjustments.clear()
            self._analyses.clear()
            self._reports.clear()
            self._events.clear()
            self._parameter_counter = 0
            self._match_counter = 0
            self._usage_counter = 0
            self._rule_counter = 0
            self._adjustment_counter = 0
            self._analysis_counter = 0
            self._report_counter = 0
            self._event_counter = 0
            self._record_event(BalanceEventKind.SYSTEM_RESET)
            self._seed()

    # -- Seeding -----------------------------------------------------------

    def _seed(self) -> None:
        """Seed the balance system with initial demo data."""
        # Combat parameters
        enemy_hp = self.register_parameter(
            name="Enemy Health Multiplier",
            category=ParameterCategory.COMBAT,
            current_value=1.0,
            default_value=1.0,
            min_value=0.1,
            max_value=5.0,
            description="Multiplier applied to enemy health pools.",
            unit="x",
            tags=["combat", "enemy"],
        )
        self.register_parameter(
            name="Player Damage Multiplier",
            category=ParameterCategory.COMBAT,
            current_value=1.0,
            default_value=1.0,
            min_value=0.1,
            max_value=5.0,
            description="Multiplier applied to player outgoing damage.",
            unit="x",
            tags=["combat", "player"],
        )
        # Economy parameters
        self.register_parameter(
            name="Gold Drop Rate",
            category=ParameterCategory.ECONOMY,
            current_value=0.5,
            default_value=0.5,
            min_value=0.0,
            max_value=1.0,
            description="Probability of gold dropping from defeated enemies.",
            unit="%",
            tags=["economy", "loot"],
        )
        # Difficulty parameters
        self.register_parameter(
            name="Enemy Aggression",
            category=ParameterCategory.DIFFICULTY,
            current_value=0.7,
            default_value=0.7,
            min_value=0.0,
            max_value=1.0,
            description="How aggressively enemies pursue and attack the player.",
            unit="",
            tags=["difficulty", "ai"],
        )

        # Seed match data
        matchups = ["warrior_vs_goblin", "mage_vs_dragon", "rogue_vs_skeleton"]
        import random
        rng = random.Random(42)
        for i in range(60):
            matchup = matchups[i % len(matchups)]
            result = "win" if rng.random() > 0.4 else "loss"
            self.record_match(
                matchup=matchup,
                player_id=f"seed_player_{i}",
                result=result,
                duration_seconds=rng.uniform(30.0, 300.0),
                player_skill=rng.uniform(0.3, 0.9),
                enemy_skill=rng.uniform(0.3, 0.9),
            )

        # Seed item usage
        items = ["sword_basic", "bow_long", "staff_fire", "shield_iron", "potion_health"]
        for i in range(40):
            item = items[i % len(items)]
            self.record_item_usage(
                item_id=item,
                player_id=f"seed_player_{i % 20}",
                usage_count=rng.randint(1, 10),
                effectiveness=rng.uniform(0.2, 0.95),
            )

        # Seed a rule: if win rate drops below 35%, reduce enemy health
        self.create_rule(
            name="Ease Difficulty on Low Win Rate",
            parameter_id=enemy_hp.parameter_id,
            metric="win_rate",
            operator=RuleOperator.LT,
            threshold=0.35,
            action=RuleAction.DECREASE,
            magnitude=0.1,
            description="Automatically reduce enemy health when overall win rate falls below 35%.",
        )


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_balance_system() -> BalanceSystem:
    """Return the singleton BalanceSystem instance."""
    return BalanceSystem.get_instance()
