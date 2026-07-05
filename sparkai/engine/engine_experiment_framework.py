"""
SparkLabs Engine - Experiment Framework

Designs, assigns and analyzes A/B/n experiments for game features.
An ``Experiment`` defines one or more ``Variant`` configurations (a
control plus treatment arms), a targeting rule set, a sample ratio, and
a lifecycle that moves from ``DRAFT`` to ``RUNNING`` to ``COMPLETED``.

Players are assigned to variants through a deterministic hash-based
``VariantAssignment`` that stays stable across sessions. As players
interact with the game, the engine collects ``MetricSample`` entries
per variant, and ``ExperimentResult`` snapshots summarize conversion
rates, means and statistical significance so the AI can decide whether
to ship a treatment arm to the entire population.

Architecture:
  ExperimentFramework (singleton)
    |-- Experiment, Variant, TargetingRule, MetricDefinition
    |-- VariantAssignment, MetricSample, ExperimentResult,
        VariantStatistic, SignificanceTest
    |-- ExperimentStats, ExperimentSnapshot, ExperimentEvent
    |-- ExperimentStatus, VariantType, MetricType, AllocationStrategy,
        SignificanceLevel

Core Capabilities:
  - create_experiment / update_experiment / delete_experiment:
    lifecycle management for experiments.
  - add_variant / remove_variant: variant composition.
  - add_metric / remove_metric: metric definition.
  - start_experiment / pause_experiment / complete_experiment:
    lifecycle transitions.
  - assign_variant / get_assignment / bulk_assign: deterministic
    hash-based player-to-variant assignment.
  - record_metric / record_conversion: metric sample collection.
  - get_results / compute_significance: statistical analysis.
  - list_experiments / list_assignments / list_events:
    observability helpers.
  - get_stats / get_status / get_snapshot / reset: standard
    engine observability.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`ExperimentFramework.get_instance` or the module-level
:func:`get_experiment_framework` factory.
"""

from __future__ import annotations

import hashlib
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

_MAX_EXPERIMENTS: int = 200
_MAX_VARIANTS_PER_EXPERIMENT: int = 10
_MAX_METRICS_PER_EXPERIMENT: int = 30
_MAX_ASSIGNMENTS_PER_EXPERIMENT: int = 10000
_MAX_SAMPLES_PER_VARIANT: int = 5000
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
    """Evict the oldest entries from a dict to keep it bounded."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list to keep it bounded."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Convert a value into a JSON-safe representation."""
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


def _hash_player(player_id: str, experiment_id: str) -> int:
    """Deterministically hash a player+experiment pair to an int in [0, 10000)."""
    raw = f"{experiment_id}:{player_id}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 10000


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ExperimentStatus(Enum):
    """Lifecycle status of an experiment.

    - ``DRAFT``: experiment is being configured, not yet assigning.
    - ``RUNNING``: experiment is live, assigning and collecting metrics.
    - ``PAUSED``: experiment is temporarily paused.
    - ``COMPLETED``: experiment has finished, results are final.
    - ``ARCHIVED``: experiment is archived and read-only.
    """

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class VariantType(Enum):
    """The role of a variant within an experiment.

    - ``CONTROL``: the baseline / status-quo variant.
    - ``TREATMENT``: a variant with a changed configuration.
    - ``HOLDOUT``: a variant excluded from the experiment for comparison.
    """

    CONTROL = "control"
    TREATMENT = "treatment"
    HOLDOUT = "holdout"


class MetricType(Enum):
    """The kind of metric being tracked.

    - ``CONVERSION``: binary yes/no outcome (e.g. did the player reach level 5).
    - ``CONTINUOUS``: a numeric value (e.g. session length in minutes).
    - ``COUNT``: a non-negative integer count (e.g. number of purchases).
    - ``RATING``: a bounded score (e.g. 1-5 star rating).
    """

    CONVERSION = "conversion"
    CONTINUOUS = "continuous"
    COUNT = "count"
    RATING = "rating"


class AllocationStrategy(Enum):
    """How traffic is split across variants.

    - ``EQUAL``: all variants get an equal share.
    - ``WEIGHTED``: variants get shares proportional to their ``weight``.
    - ``RAMPED``: treatment variants start small and ramp up over time.
    """

    EQUAL = "equal"
    WEIGHTED = "weighted"
    RAMPED = "ramped"


class SignificanceLevel(Enum):
    """Confidence threshold for declaring a result significant.

    - ``P90``: 90% confidence (alpha = 0.10).
    - ``P95``: 95% confidence (alpha = 0.05).
    - ``P99``: 99% confidence (alpha = 0.01).
    """

    P90 = "p90"
    P95 = "p95"
    P99 = "p99"


class ExperimentEventKind(Enum):
    """Audit event types emitted by the engine."""

    EXPERIMENT_CREATED = "experiment_created"
    EXPERIMENT_UPDATED = "experiment_updated"
    EXPERIMENT_DELETED = "experiment_deleted"
    VARIANT_ADDED = "variant_added"
    VARIANT_REMOVED = "variant_removed"
    METRIC_ADDED = "metric_added"
    METRIC_REMOVED = "metric_removed"
    EXPERIMENT_STARTED = "experiment_started"
    EXPERIMENT_PAUSED = "experiment_paused"
    EXPERIMENT_COMPLETED = "experiment_completed"
    EXPERIMENT_ARCHIVED = "experiment_archived"
    VARIANT_ASSIGNED = "variant_assigned"
    METRIC_RECORDED = "metric_recorded"
    CONVERSION_RECORDED = "conversion_recorded"
    RESULT_COMPUTED = "result_computed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Variant:
    """A single arm of an A/B/n experiment.

    The ``weight`` field controls traffic allocation under the
    ``WEIGHTED`` strategy. The ``configuration`` dict holds the
    game-side parameters that change for this variant.
    """

    variant_id: str
    name: str
    variant_type: VariantType = VariantType.TREATMENT
    weight: float = 1.0
    description: str = ""
    configuration: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MetricDefinition:
    """A metric tracked across variants in an experiment.

    For ``CONVERSION`` metrics, the ``value`` recorded per sample
    should be 0 or 1. For ``CONTINUOUS`` metrics, any numeric value.
    """

    metric_id: str
    name: str
    metric_type: MetricType = MetricType.CONTINUOUS
    description: str = ""
    unit: str = ""
    higher_is_better: bool = True
    target_value: Optional[float] = None
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TargetingRule:
    """An eligibility rule for experiment participation.

    A player must match all rules to be eligible. Each rule is a
    ``key OP value`` expression evaluated against the player's
    attributes dict.
    """

    rule_id: str
    attribute: str
    operator: str
    value: str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Experiment:
    """A top-level A/B/n experiment definition.

    An experiment contains variants, metric definitions, targeting
    rules, and a lifecycle status. Only ``RUNNING`` experiments
    assign players and collect metrics.
    """

    experiment_id: str
    name: str
    description: str = ""
    status: ExperimentStatus = ExperimentStatus.DRAFT
    allocation: AllocationStrategy = AllocationStrategy.EQUAL
    significance_level: SignificanceLevel = SignificanceLevel.P95
    variants: List[Variant] = field(default_factory=list)
    metrics: List[MetricDefinition] = field(default_factory=list)
    targeting_rules: List[TargetingRule] = field(default_factory=list)
    traffic_percentage: float = 100.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VariantAssignment:
    """A player's assignment to a variant within an experiment."""

    assignment_id: str
    experiment_id: str
    player_id: str
    variant_id: str
    assigned_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MetricSample:
    """A single metric data point for a player in a variant."""

    sample_id: str
    experiment_id: str
    variant_id: str
    player_id: str
    metric_id: str
    value: float
    recorded_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class VariantStatistic:
    """Aggregate statistics for one variant on one metric."""

    variant_id: str
    metric_id: str
    sample_count: int = 0
    sum_value: float = 0.0
    sum_sq_value: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    conversion_count: int = 0
    mean: float = 0.0
    variance: float = 0.0
    std_error: float = 0.0
    conversion_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SignificanceTest:
    """Result of a statistical significance test between two variants."""

    control_variant_id: str
    treatment_variant_id: str
    metric_id: str
    control_mean: float = 0.0
    treatment_mean: float = 0.0
    difference: float = 0.0
    relative_lift: float = 0.0
    z_score: float = 0.0
    p_value: float = 1.0
    is_significant: bool = False
    confidence_level: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ExperimentResult:
    """Full results snapshot for a completed or running experiment."""

    experiment_id: str
    status: ExperimentStatus = ExperimentStatus.RUNNING
    total_assignments: int = 0
    total_samples: int = 0
    variant_statistics: List[VariantStatistic] = field(default_factory=list)
    significance_tests: List[SignificanceTest] = field(default_factory=list)
    winning_variant_id: Optional[str] = None
    computed_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ExperimentStats:
    """Aggregate statistics for the experiment framework."""

    total_experiments: int = 0
    draft_experiments: int = 0
    running_experiments: int = 0
    paused_experiments: int = 0
    completed_experiments: int = 0
    archived_experiments: int = 0
    total_variants: int = 0
    total_metrics: int = 0
    total_assignments: int = 0
    total_samples: int = 0
    event_counter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ExperimentSnapshot:
    """Full state snapshot for persistence or debugging."""

    experiments: List[Dict[str, Any]] = field(default_factory=list)
    assignments: List[Dict[str, Any]] = field(default_factory=list)
    samples: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ExperimentEvent:
    """Audit event emitted on every state transition."""

    event_id: str
    kind: ExperimentEventKind
    timestamp: str
    experiment_id: str = ""
    variant_id: str = ""
    player_id: str = ""
    metric_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class ExperimentFramework:
    """Singleton engine for designing, running and analyzing A/B/n experiments.

    The engine stores experiment definitions, variant assignments, metric
    samples and an audit event log. All public methods are guarded by a
    re-entrant lock for thread safety.
    """

    _instance: Optional["ExperimentFramework"] = None
    _lock: threading.RLock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "ExperimentFramework":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __new__(cls) -> "ExperimentFramework":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._initialized = False
                    cls._instance = inst
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        with self._lock:
            if getattr(self, "_initialized", False):
                return
            self._initialized: bool = False
            self._experiments: Dict[str, Experiment] = {}
            self._assignments: Dict[str, Dict[str, VariantAssignment]] = {}
            self._samples: Dict[str, List[MetricSample]] = {}
            self._events: List[ExperimentEvent] = []
            self._experiment_counter: int = 0
            self._variant_counter: int = 0
            self._metric_counter: int = 0
            self._assignment_counter: int = 0
            self._sample_counter: int = 0
            self._event_counter: int = 0
            self._seed_data()
            self._initialized = True

    # ------------------------------------------------------------------
    # Experiment Management
    # ------------------------------------------------------------------

    def create_experiment(
        self,
        name: str,
        description: str = "",
        allocation: AllocationStrategy = AllocationStrategy.EQUAL,
        significance_level: SignificanceLevel = SignificanceLevel.P95,
        traffic_percentage: float = 100.0,
    ) -> Experiment:
        """Create a new experiment in DRAFT status."""
        with self._lock:
            exp_id = _new_id("exp")
            exp = Experiment(
                experiment_id=exp_id,
                name=name,
                description=description,
                allocation=allocation,
                significance_level=significance_level,
                traffic_percentage=max(0.0, min(100.0, float(traffic_percentage))),
            )
            self._experiments[exp_id] = exp
            self._assignments[exp_id] = {}
            self._samples[exp_id] = []
            self._experiment_counter += 1
            self._record_event(
                ExperimentEventKind.EXPERIMENT_CREATED,
                experiment_id=exp_id,
                payload={"name": name, "allocation": allocation.value},
            )
            _evict_fifo_dict(self._experiments, _MAX_EXPERIMENTS)
            return exp

    def update_experiment(
        self,
        experiment_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Experiment]:
        """Update mutable fields of an experiment (only in DRAFT status)."""
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp is None:
                return None
            if "name" in updates:
                exp.name = str(updates["name"])
            if "description" in updates:
                exp.description = str(updates["description"])
            if "allocation" in updates:
                exp.allocation = AllocationStrategy(updates["allocation"])
            if "significance_level" in updates:
                exp.significance_level = SignificanceLevel(updates["significance_level"])
            if "traffic_percentage" in updates:
                exp.traffic_percentage = max(0.0, min(100.0, float(updates["traffic_percentage"])))
            exp.updated_at = _now()
            self._record_event(
                ExperimentEventKind.EXPERIMENT_UPDATED,
                experiment_id=experiment_id,
                payload=updates,
            )
            return exp

    def delete_experiment(self, experiment_id: str) -> bool:
        """Delete an experiment and all its data."""
        with self._lock:
            existed = self._experiments.pop(experiment_id, None) is not None
            if existed:
                self._assignments.pop(experiment_id, None)
                self._samples.pop(experiment_id, None)
                self._record_event(
                    ExperimentEventKind.EXPERIMENT_DELETED,
                    experiment_id=experiment_id,
                )
            return existed

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        with self._lock:
            return self._experiments.get(experiment_id)

    def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
    ) -> List[Experiment]:
        with self._lock:
            out: List[Experiment] = []
            for e in self._experiments.values():
                if status is not None and e.status != status:
                    continue
                out.append(e)
            out.sort(key=lambda x: x.created_at)
            return out

    # ------------------------------------------------------------------
    # Variant Management
    # ------------------------------------------------------------------

    def add_variant(
        self,
        experiment_id: str,
        name: str,
        variant_type: VariantType = VariantType.TREATMENT,
        weight: float = 1.0,
        description: str = "",
        configuration: Optional[Dict[str, Any]] = None,
    ) -> Optional[Variant]:
        """Add a variant to an experiment."""
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp is None:
                return None
            if exp.status not in (ExperimentStatus.DRAFT, ExperimentStatus.PAUSED):
                return None
            variant_id = _new_id("var")
            variant = Variant(
                variant_id=variant_id,
                name=name,
                variant_type=variant_type,
                weight=max(0.0, float(weight)),
                description=description,
                configuration=configuration or {},
            )
            exp.variants.append(variant)
            self._variant_counter += 1
            exp.updated_at = _now()
            self._record_event(
                ExperimentEventKind.VARIANT_ADDED,
                experiment_id=experiment_id,
                variant_id=variant_id,
                payload={"name": name, "variant_type": variant_type.value},
            )
            _evict_fifo_list(exp.variants, _MAX_VARIANTS_PER_EXPERIMENT)
            return variant

    def remove_variant(self, experiment_id: str, variant_id: str) -> bool:
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp is None:
                return False
            if exp.status not in (ExperimentStatus.DRAFT, ExperimentStatus.PAUSED):
                return False
            before = len(exp.variants)
            exp.variants = [v for v in exp.variants if v.variant_id != variant_id]
            removed = len(exp.variants) < before
            if removed:
                exp.updated_at = _now()
                self._record_event(
                    ExperimentEventKind.VARIANT_REMOVED,
                    experiment_id=experiment_id,
                    variant_id=variant_id,
                )
            return removed

    # ------------------------------------------------------------------
    # Metric Management
    # ------------------------------------------------------------------

    def add_metric(
        self,
        experiment_id: str,
        name: str,
        metric_type: MetricType = MetricType.CONTINUOUS,
        description: str = "",
        unit: str = "",
        higher_is_better: bool = True,
        target_value: Optional[float] = None,
    ) -> Optional[MetricDefinition]:
        """Add a metric definition to an experiment."""
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp is None:
                return None
            metric_id = _new_id("met")
            metric = MetricDefinition(
                metric_id=metric_id,
                name=name,
                metric_type=metric_type,
                description=description,
                unit=unit,
                higher_is_better=higher_is_better,
                target_value=target_value,
            )
            exp.metrics.append(metric)
            self._metric_counter += 1
            exp.updated_at = _now()
            self._record_event(
                ExperimentEventKind.METRIC_ADDED,
                experiment_id=experiment_id,
                metric_id=metric_id,
                payload={"name": name, "metric_type": metric_type.value},
            )
            _evict_fifo_list(exp.metrics, _MAX_METRICS_PER_EXPERIMENT)
            return metric

    def remove_metric(self, experiment_id: str, metric_id: str) -> bool:
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp is None:
                return False
            before = len(exp.metrics)
            exp.metrics = [m for m in exp.metrics if m.metric_id != metric_id]
            removed = len(exp.metrics) < before
            if removed:
                exp.updated_at = _now()
                self._record_event(
                    ExperimentEventKind.METRIC_REMOVED,
                    experiment_id=experiment_id,
                    metric_id=metric_id,
                )
            return removed

    # ------------------------------------------------------------------
    # Lifecycle Transitions
    # ------------------------------------------------------------------

    def start_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Move an experiment from DRAFT/PAUSED to RUNNING."""
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp is None:
                return None
            if exp.status not in (ExperimentStatus.DRAFT, ExperimentStatus.PAUSED):
                return None
            if len(exp.variants) < 2:
                return None
            exp.status = ExperimentStatus.RUNNING
            if exp.started_at is None:
                exp.started_at = _now()
            exp.updated_at = _now()
            self._record_event(
                ExperimentEventKind.EXPERIMENT_STARTED,
                experiment_id=experiment_id,
            )
            return exp

    def pause_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Pause a running experiment."""
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp is None:
                return None
            if exp.status != ExperimentStatus.RUNNING:
                return None
            exp.status = ExperimentStatus.PAUSED
            exp.updated_at = _now()
            self._record_event(
                ExperimentEventKind.EXPERIMENT_PAUSED,
                experiment_id=experiment_id,
            )
            return exp

    def complete_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Complete an experiment and compute final results."""
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp is None:
                return None
            if exp.status not in (ExperimentStatus.RUNNING, ExperimentStatus.PAUSED):
                return None
            exp.status = ExperimentStatus.COMPLETED
            exp.completed_at = _now()
            exp.updated_at = _now()
            self._record_event(
                ExperimentEventKind.EXPERIMENT_COMPLETED,
                experiment_id=experiment_id,
            )
            self.get_results(experiment_id)
            return exp

    def archive_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Archive a completed experiment."""
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp is None:
                return None
            if exp.status != ExperimentStatus.COMPLETED:
                return None
            exp.status = ExperimentStatus.ARCHIVED
            exp.updated_at = _now()
            self._record_event(
                ExperimentEventKind.EXPERIMENT_ARCHIVED,
                experiment_id=experiment_id,
            )
            return exp

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------

    def assign_variant(
        self,
        experiment_id: str,
        player_id: str,
    ) -> Optional[VariantAssignment]:
        """Assign a player to a variant using deterministic hashing.

        If the player already has an assignment, the existing one is
        returned. Otherwise a new assignment is created based on a
        hash of (experiment_id, player_id) mapped onto the variant
        weight distribution.
        """
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp is None or exp.status != ExperimentStatus.RUNNING:
                return None
            assignments = self._assignments.setdefault(experiment_id, {})
            existing = assignments.get(player_id)
            if existing is not None:
                return existing
            traffic_pct = exp.traffic_percentage
            if traffic_pct < 100.0:
                bucket = _hash_player(player_id, experiment_id)
                if bucket >= int(traffic_pct * 100):
                    return None
            variant = self._select_variant(exp, player_id)
            if variant is None:
                return None
            assignment = VariantAssignment(
                assignment_id=_new_id("asgn"),
                experiment_id=experiment_id,
                player_id=player_id,
                variant_id=variant.variant_id,
            )
            assignments[player_id] = assignment
            self._assignment_counter += 1
            self._record_event(
                ExperimentEventKind.VARIANT_ASSIGNED,
                experiment_id=experiment_id,
                variant_id=variant.variant_id,
                player_id=player_id,
            )
            _evict_fifo_dict(assignments, _MAX_ASSIGNMENTS_PER_EXPERIMENT)
            return assignment

    def _select_variant(self, exp: Experiment, player_id: str) -> Optional[Variant]:
        """Select a variant for a player based on the allocation strategy."""
        if not exp.variants:
            return None
        if exp.allocation == AllocationStrategy.EQUAL:
            bucket = _hash_player(player_id, exp.experiment_id)
            idx = bucket % len(exp.variants)
            return exp.variants[idx]
        total_weight = sum(v.weight for v in exp.variants)
        if total_weight <= 0:
            return exp.variants[0]
        bucket = _hash_player(player_id, exp.experiment_id) / 10000.0
        cumulative = 0.0
        for v in exp.variants:
            cumulative += v.weight / total_weight
            if bucket <= cumulative:
                return v
        return exp.variants[-1]

    def get_assignment(
        self,
        experiment_id: str,
        player_id: str,
    ) -> Optional[VariantAssignment]:
        """Get a player's existing assignment without creating one."""
        with self._lock:
            assignments = self._assignments.get(experiment_id, {})
            return assignments.get(player_id)

    def bulk_assign(
        self,
        experiment_id: str,
        player_ids: List[str],
    ) -> List[VariantAssignment]:
        """Assign multiple players at once."""
        with self._lock:
            out: List[VariantAssignment] = []
            for pid in player_ids:
                a = self.assign_variant(experiment_id, pid)
                if a is not None:
                    out.append(a)
            return out

    def list_assignments(
        self,
        experiment_id: str,
        variant_id: Optional[str] = None,
    ) -> List[VariantAssignment]:
        with self._lock:
            assignments = self._assignments.get(experiment_id, {})
            out = list(assignments.values())
            if variant_id is not None:
                out = [a for a in out if a.variant_id == variant_id]
            return out

    # ------------------------------------------------------------------
    # Metric Recording
    # ------------------------------------------------------------------

    def record_metric(
        self,
        experiment_id: str,
        player_id: str,
        metric_id: str,
        value: float,
    ) -> Optional[MetricSample]:
        """Record a metric sample for a player.

        The player must already have a variant assignment. The metric
        must be defined on the experiment.
        """
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp is None or exp.status != ExperimentStatus.RUNNING:
                return None
            assignment = self._assignments.get(experiment_id, {}).get(player_id)
            if assignment is None:
                return None
            metric_exists = any(m.metric_id == metric_id for m in exp.metrics)
            if not metric_exists:
                return None
            sample = MetricSample(
                sample_id=_new_id("smp"),
                experiment_id=experiment_id,
                variant_id=assignment.variant_id,
                player_id=player_id,
                metric_id=metric_id,
                value=float(value),
            )
            samples = self._samples.setdefault(experiment_id, [])
            samples.append(sample)
            self._sample_counter += 1
            self._record_event(
                ExperimentEventKind.METRIC_RECORDED,
                experiment_id=experiment_id,
                variant_id=assignment.variant_id,
                player_id=player_id,
                metric_id=metric_id,
                payload={"value": float(value)},
            )
            _evict_fifo_list(samples, _MAX_SAMPLES_PER_VARIANT * len(exp.variants))
            return sample

    def record_conversion(
        self,
        experiment_id: str,
        player_id: str,
        metric_id: str,
        converted: bool = True,
    ) -> Optional[MetricSample]:
        """Record a binary conversion metric (value 0 or 1)."""
        return self.record_metric(experiment_id, player_id, metric_id, 1.0 if converted else 0.0)

    # ------------------------------------------------------------------
    # Results & Significance
    # ------------------------------------------------------------------

    def get_results(self, experiment_id: str) -> Optional[ExperimentResult]:
        """Compute and return results for an experiment."""
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if exp is None:
                return None
            assignments = self._assignments.get(experiment_id, {})
            samples = self._samples.get(experiment_id, [])
            variant_stats: Dict[Tuple[str, str], VariantStatistic] = {}
            for s in samples:
                key = (s.variant_id, s.metric_id)
                stat = variant_stats.get(key)
                if stat is None:
                    stat = VariantStatistic(
                        variant_id=s.variant_id,
                        metric_id=s.metric_id,
                        min_value=s.value,
                        max_value=s.value,
                    )
                    variant_stats[key] = stat
                stat.sample_count += 1
                stat.sum_value += s.value
                stat.sum_sq_value += s.value * s.value
                if s.value < stat.min_value:
                    stat.min_value = s.value
                if s.value > stat.max_value:
                    stat.max_value = s.value
                if s.value > 0.5:
                    stat.conversion_count += 1
            for stat in variant_stats.values():
                n = stat.sample_count
                if n > 0:
                    stat.mean = stat.sum_value / n
                    stat.variance = max(0.0, (stat.sum_sq_value / n) - (stat.mean ** 2))
                    stat.std_error = math.sqrt(stat.variance / n) if n > 1 else 0.0
                    stat.conversion_rate = stat.conversion_count / n
            sig_tests: List[SignificanceTest] = []
            control = None
            for v in exp.variants:
                if v.variant_type == VariantType.CONTROL:
                    control = v
                    break
            if control is None and exp.variants:
                control = exp.variants[0]
            if control is not None:
                alpha_map = {
                    SignificanceLevel.P90: 1.645,
                    SignificanceLevel.P95: 1.96,
                    SignificanceLevel.P99: 2.576,
                }
                z_threshold = alpha_map.get(exp.significance_level, 1.96)
                for metric in exp.metrics:
                    control_stat = variant_stats.get((control.variant_id, metric.metric_id))
                    if control_stat is None or control_stat.sample_count == 0:
                        continue
                    for v in exp.variants:
                        if v.variant_id == control.variant_id:
                            continue
                        treat_stat = variant_stats.get((v.variant_id, metric.metric_id))
                        if treat_stat is None or treat_stat.sample_count == 0:
                            continue
                        diff = treat_stat.mean - control_stat.mean
                        se = math.sqrt(
                            control_stat.variance / max(1, control_stat.sample_count)
                            + treat_stat.variance / max(1, treat_stat.sample_count)
                        )
                        z = diff / se if se > 0 else 0.0
                        p_val = 2.0 * (1.0 - _normal_cdf(abs(z))) if z != 0 else 1.0
                        rel_lift = (diff / abs(control_stat.mean) * 100.0) if control_stat.mean != 0 else 0.0
                        sig = SignificanceTest(
                            control_variant_id=control.variant_id,
                            treatment_variant_id=v.variant_id,
                            metric_id=metric.metric_id,
                            control_mean=control_stat.mean,
                            treatment_mean=treat_stat.mean,
                            difference=diff,
                            relative_lift=rel_lift,
                            z_score=z,
                            p_value=p_val,
                            is_significant=abs(z) >= z_threshold,
                            confidence_level=(1.0 - p_val) * 100.0,
                        )
                        sig_tests.append(sig)
            winning = None
            if sig_tests:
                best = None
                for st in sig_tests:
                    if not st.is_significant:
                        continue
                    if best is None:
                        best = st
                        continue
                    if st.treatment_mean > best.treatment_mean:
                        best = st
                if best is not None:
                    winning = best.treatment_variant_id
            result = ExperimentResult(
                experiment_id=experiment_id,
                status=exp.status,
                total_assignments=len(assignments),
                total_samples=len(samples),
                variant_statistics=list(variant_stats.values()),
                significance_tests=sig_tests,
                winning_variant_id=winning,
            )
            self._record_event(
                ExperimentEventKind.RESULT_COMPUTED,
                experiment_id=experiment_id,
                payload={"total_samples": len(samples), "winner": winning},
            )
            return result

    def compute_significance(
        self,
        experiment_id: str,
    ) -> List[SignificanceTest]:
        """Compute significance tests for an experiment."""
        result = self.get_results(experiment_id)
        if result is None:
            return []
        return result.significance_tests

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(
        self,
        kind: Optional[ExperimentEventKind] = None,
        experiment_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ExperimentEvent]:
        with self._lock:
            out: List[ExperimentEvent] = []
            for e in reversed(self._events):
                if kind is not None and e.kind != kind:
                    continue
                if experiment_id is not None and e.experiment_id != experiment_id:
                    continue
                out.append(e)
                if len(out) >= int(limit):
                    break
            return out

    def get_stats(self) -> ExperimentStats:
        with self._lock:
            draft = sum(1 for e in self._experiments.values() if e.status == ExperimentStatus.DRAFT)
            running = sum(1 for e in self._experiments.values() if e.status == ExperimentStatus.RUNNING)
            paused = sum(1 for e in self._experiments.values() if e.status == ExperimentStatus.PAUSED)
            completed = sum(1 for e in self._experiments.values() if e.status == ExperimentStatus.COMPLETED)
            archived = sum(1 for e in self._experiments.values() if e.status == ExperimentStatus.ARCHIVED)
            total_variants = sum(len(e.variants) for e in self._experiments.values())
            total_metrics = sum(len(e.metrics) for e in self._experiments.values())
            total_assignments = sum(len(a) for a in self._assignments.values())
            total_samples = sum(len(s) for s in self._samples.values())
            return ExperimentStats(
                total_experiments=len(self._experiments),
                draft_experiments=draft,
                running_experiments=running,
                paused_experiments=paused,
                completed_experiments=completed,
                archived_experiments=archived,
                total_variants=total_variants,
                total_metrics=total_metrics,
                total_assignments=total_assignments,
                total_samples=total_samples,
                event_counter=self._event_counter,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_experiments": len(self._experiments),
                "total_assignment_sets": len(self._assignments),
                "total_sample_sets": len(self._samples),
                "total_events": len(self._events),
                "experiment_counter": self._experiment_counter,
                "variant_counter": self._variant_counter,
                "metric_counter": self._metric_counter,
                "assignment_counter": self._assignment_counter,
                "sample_counter": self._sample_counter,
                "event_counter": self._event_counter,
                "capacities": {
                    "max_experiments": _MAX_EXPERIMENTS,
                    "max_variants_per_experiment": _MAX_VARIANTS_PER_EXPERIMENT,
                    "max_metrics_per_experiment": _MAX_METRICS_PER_EXPERIMENT,
                    "max_assignments_per_experiment": _MAX_ASSIGNMENTS_PER_EXPERIMENT,
                    "max_samples_per_variant": _MAX_SAMPLES_PER_VARIANT,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> ExperimentSnapshot:
        with self._lock:
            return ExperimentSnapshot(
                experiments=[e.to_dict() for e in self._experiments.values()],
                assignments=[
                    a.to_dict()
                    for exp_assigns in self._assignments.values()
                    for a in exp_assigns.values()
                ],
                samples=[
                    s.to_dict()
                    for exp_samples in self._samples.values()
                    for s in exp_samples
                ],
                events=[e.to_dict() for e in self._events[-200:]],
                stats=self.get_stats().to_dict(),
            )

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: ExperimentEventKind,
        experiment_id: str = "",
        variant_id: str = "",
        player_id: str = "",
        metric_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an audit event. Caller must hold the lock."""
        event = ExperimentEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            experiment_id=experiment_id,
            variant_id=variant_id,
            player_id=player_id,
            metric_id=metric_id,
            payload=payload or {},
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the engine to its seeded state."""
        with self._lock:
            self._experiments.clear()
            self._assignments.clear()
            self._samples.clear()
            self._events.clear()
            self._experiment_counter = 0
            self._variant_counter = 0
            self._metric_counter = 0
            self._assignment_counter = 0
            self._sample_counter = 0
            self._event_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with a sample experiment."""
        exp = self.create_experiment(
            name="Difficulty Tuning A/B Test",
            description="Tests whether reducing enemy health by 10% improves retention.",
            allocation=AllocationStrategy.EQUAL,
            significance_level=SignificanceLevel.P95,
            traffic_percentage=100.0,
        )
        self.add_variant(
            experiment_id=exp.experiment_id,
            name="Control (Full HP)",
            variant_type=VariantType.CONTROL,
            description="Enemies at full health.",
            configuration={"enemy_health_multiplier": 1.0},
        )
        self.add_variant(
            experiment_id=exp.experiment_id,
            name="Treatment (-10% HP)",
            variant_type=VariantType.TREATMENT,
            description="Enemies with 10% less health.",
            configuration={"enemy_health_multiplier": 0.9},
        )
        self.add_metric(
            experiment_id=exp.experiment_id,
            name="Day 1 Retention",
            metric_type=MetricType.CONVERSION,
            description="Did the player return on day 1?",
            higher_is_better=True,
        )
        self.add_metric(
            experiment_id=exp.experiment_id,
            name="Session Length",
            metric_type=MetricType.CONTINUOUS,
            description="Average session length in minutes.",
            unit="minutes",
            higher_is_better=True,
        )
        self.start_experiment(exp.experiment_id)


# ---------------------------------------------------------------------------
# Statistical Helpers
# ---------------------------------------------------------------------------


def _normal_cdf(x: float) -> float:
    """Approximate the standard normal CDF using the error function.

    Uses Abramowitz and Stegun's approximation (formula 7.1.26).
    """
    if x < -8.0:
        return 0.0
    if x > 8.0:
        return 1.0
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911
    sign = 1.0 if x >= 0 else -1.0
    abs_x = abs(x) / math.sqrt(2.0)
    t = 1.0 / (1.0 + p * abs_x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-abs_x * abs_x)
    return 0.5 * (1.0 + sign * y)


# ---------------------------------------------------------------------------
# Module-level Factory
# ---------------------------------------------------------------------------


def get_experiment_framework() -> ExperimentFramework:
    """Return the singleton ExperimentFramework instance."""
    return ExperimentFramework.get_instance()
