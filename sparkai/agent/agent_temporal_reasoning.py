"""
SparkLabs Agent - Temporal Reasoning Engine

Temporal cognition for AI agents: reasoning about time, schedules,
deadlines, durations, and temporal ordering of events.

Agents use this module to plan around timed quests, respect schedules
(shops opening/closing, day/night activities), reason about
"before/after/during" relationships, and understand deadlines.

Architecture:
  TemporalReasoningEngine (Singleton, double-checked locking)
    |-- TemporalRelation     -- Allen's interval algebra relations
    |-- TimeInterval         -- a bounded span of time
    |-- ScheduleEntry        -- a scheduled activity with timing
    |-- TemporalConstraint   -- a constraint between intervals
    |-- TemporalReasoningSnapshot -- complete engine snapshot

Subsystems:
  1. Interval Arithmetic -- add/subtract/intersect/union time intervals
  2. Allen's Algebra    -- 13 temporal relations between intervals
  3. Schedule Planning   -- resolve temporal constraints to find schedules
  4. Deadline Tracking   -- track upcoming deadlines and urgency
  5. Temporal Queries    -- answer "what happens before/after/during X?"
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TemporalRelation(Enum):
    """Allen's interval algebra: 13 relations between two time intervals."""
    BEFORE = "before"             # A ends before B starts
    AFTER = "after"               # A starts after B ends
    MEETS = "meets"               # A ends exactly when B starts
    MET_BY = "met_by"             # A starts exactly when B ends
    OVERLAPS = "overlaps"         # A starts before B, overlaps, ends before B
    OVERLAPPED_BY = "overlapped_by"  # B starts before A, overlaps, ends before A
    DURING = "during"             # A is fully contained within B
    CONTAINS = "contains"         # A fully contains B
    STARTS = "starts"             # A starts when B starts, ends before B
    STARTED_BY = "started_by"     # A starts when B starts, ends after B
    FINISHES = "finishes"         # A ends when B ends, starts after B
    FINISHED_BY = "finished_by"   # A ends when B ends, starts before B
    EQUALS = "equals"             # A and B are identical


class UrgencyLevel(Enum):
    """How urgent a deadline is relative to the current time."""
    PASSED = "passed"
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TimeInterval:
    """A bounded span of time with a start and end."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    start: float = 0.0
    end: float = 0.0
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    @property
    def is_instant(self) -> bool:
        return self.start == self.end

    def contains_point(self, t: float) -> bool:
        return self.start <= t <= self.end

    def overlaps_interval(self, other: "TimeInterval") -> bool:
        return self.start < other.end and other.start < self.end

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "label": self.label,
            "is_instant": self.is_instant,
            "metadata": dict(self.metadata),
        }


@dataclass
class ScheduleEntry:
    """A scheduled activity with timing constraints."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    interval: Optional[TimeInterval] = None
    deadline: Optional[float] = None
    priority: float = 0.5
    prerequisites: List[str] = field(default_factory=list)
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "interval": self.interval.to_dict() if self.interval else None,
            "deadline": self.deadline,
            "priority": self.priority,
            "prerequisites": list(self.prerequisites),
            "status": self.status,
            "metadata": dict(self.metadata),
        }


@dataclass
class TemporalConstraint:
    """A temporal constraint between two intervals."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    interval_a_id: str = ""
    interval_b_id: str = ""
    relation: TemporalRelation = TemporalRelation.BEFORE
    tolerance: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "interval_a_id": self.interval_a_id,
            "interval_b_id": self.interval_b_id,
            "relation": self.relation.value,
            "tolerance": self.tolerance,
            "metadata": dict(self.metadata),
        }


@dataclass
class TemporalReasoningSnapshot:
    """Complete snapshot of the Temporal Reasoning Engine."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    interval_count: int = 0
    schedule_count: int = 0
    constraint_count: int = 0
    active_deadlines: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "interval_count": self.interval_count,
            "schedule_count": self.schedule_count,
            "constraint_count": self.constraint_count,
            "active_deadlines": list(self.active_deadlines),
            "stats": dict(self.stats),
        }


# ---------------------------------------------------------------------------
# Singleton Engine
# ---------------------------------------------------------------------------

class TemporalReasoningEngine:
    """Singleton temporal reasoning engine for AI agents."""

    _instance: Optional["TemporalReasoningEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "TemporalReasoningEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.__init_singleton()
        return cls._instance

    def __init_singleton(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._intervals: Dict[str, TimeInterval] = {}
        self._schedules: Dict[str, ScheduleEntry] = {}
        self._constraints: List[TemporalConstraint] = []
        self._current_time: float = time.time()
        self._handlers: Dict[str, Callable] = {}
        self._stats: Dict[str, Any] = {
            "queries_total": 0,
            "relations_computed": 0,
            "schedules_resolved": 0,
            "deadlines_checked": 0,
        }

    @classmethod
    def get_instance(cls) -> "TemporalReasoningEngine":
        return cls()

    # -- Interval management ------------------------------------------------

    def add_interval(self, interval: TimeInterval) -> TimeInterval:
        with self._instance_lock:
            self._intervals[interval.id] = interval
            return interval

    def create_interval(self, start: float, end: float, label: str = "") -> TimeInterval:
        interval = TimeInterval(start=start, end=end, label=label)
        return self.add_interval(interval)

    def get_interval(self, interval_id: str) -> Optional[TimeInterval]:
        with self._instance_lock:
            return self._intervals.get(interval_id)

    def get_all_intervals(self) -> List[TimeInterval]:
        with self._instance_lock:
            return list(self._intervals.values())

    def remove_interval(self, interval_id: str) -> bool:
        with self._instance_lock:
            if interval_id in self._intervals:
                del self._intervals[interval_id]
                self._constraints = [
                    c for c in self._constraints
                    if c.interval_a_id != interval_id and c.interval_b_id != interval_id
                ]
                return True
            return False

    # -- Allen's interval algebra -------------------------------------------

    def compute_relation(self, a: TimeInterval, b: TimeInterval) -> TemporalRelation:
        """Compute the Allen interval relation between two intervals."""
        self._stats["relations_computed"] += 1
        tol = 1e-9
        if abs(a.start - b.start) < tol and abs(a.end - b.end) < tol:
            return TemporalRelation.EQUALS
        if a.end <= b.start + tol:
            if abs(a.end - b.start) < tol:
                return TemporalRelation.MEETS
            return TemporalRelation.BEFORE
        if b.end <= a.start + tol:
            if abs(b.end - a.start) < tol:
                return TemporalRelation.MET_BY
            return TemporalRelation.AFTER
        if a.start >= b.start - tol and a.end <= b.end + tol:
            if abs(a.start - b.start) < tol:
                return TemporalRelation.STARTS
            if abs(a.end - b.end) < tol:
                return TemporalRelation.FINISHES
            return TemporalRelation.DURING
        if b.start >= a.start - tol and b.end <= a.end + tol:
            if abs(b.start - a.start) < tol:
                return TemporalRelation.STARTED_BY
            if abs(b.end - b.end) < tol:
                return TemporalRelation.FINISHED_BY
            return TemporalRelation.CONTAINS
        if a.start < b.start and a.end < b.end:
            return TemporalRelation.OVERLAPS
        return TemporalRelation.OVERLAPPED_BY

    def check_relation(self, interval_a_id: str, interval_b_id: str, expected: TemporalRelation) -> bool:
        """Check if two intervals satisfy a specific temporal relation."""
        a = self.get_interval(interval_a_id)
        b = self.get_interval(interval_b_id)
        if a is None or b is None:
            return False
        actual = self.compute_relation(a, b)
        return actual == expected

    # -- Constraint management ----------------------------------------------

    def add_constraint(self, constraint: TemporalConstraint) -> TemporalConstraint:
        with self._instance_lock:
            self._constraints.append(constraint)
            return constraint

    def get_constraints(self) -> List[TemporalConstraint]:
        with self._instance_lock:
            return list(self._constraints)

    def validate_constraints(self) -> Dict[str, Any]:
        """Validate all temporal constraints and report violations."""
        violations: List[Dict[str, Any]] = []
        checked = 0
        for c in self._constraints:
            a = self.get_interval(c.interval_a_id)
            b = self.get_interval(c.interval_b_id)
            if a is None or b is None:
                continue
            checked += 1
            actual = self.compute_relation(a, b)
            if actual != c.relation:
                violations.append({
                    "constraint_id": c.id,
                    "expected": c.relation.value,
                    "actual": actual.value,
                    "interval_a": c.interval_a_id,
                    "interval_b": c.interval_b_id,
                })
        return {
            "checked": checked,
            "violations": violations,
            "all_satisfied": len(violations) == 0,
        }

    # -- Schedule management ------------------------------------------------

    def add_schedule(self, entry: ScheduleEntry) -> ScheduleEntry:
        with self._instance_lock:
            self._schedules[entry.id] = entry
            return entry

    def create_schedule(self, name: str, start: float, end: float, deadline: Optional[float] = None) -> ScheduleEntry:
        interval = TimeInterval(start=start, end=end, label=name)
        self.add_interval(interval)
        entry = ScheduleEntry(name=name, interval=interval, deadline=deadline)
        return self.add_schedule(entry)

    def get_schedule(self, schedule_id: str) -> Optional[ScheduleEntry]:
        with self._instance_lock:
            return self._schedules.get(schedule_id)

    def get_all_schedules(self) -> List[ScheduleEntry]:
        with self._instance_lock:
            return list(self._schedules.values())

    def resolve_schedule_order(self) -> List[str]:
        """Topologically sort schedules by prerequisites."""
        self._stats["schedules_resolved"] += 1
        with self._instance_lock:
            visited: set = set()
            order: List[str] = []

            def visit(sid: str) -> None:
                if sid in visited:
                    return
                visited.add(sid)
                entry = self._schedules.get(sid)
                if entry:
                    for prereq in entry.prerequisites:
                        visit(prereq)
                    order.append(sid)

            for sid in self._schedules:
                visit(sid)
            return order

    # -- Deadline tracking --------------------------------------------------

    def check_deadlines(self, current_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """Check all deadlines and return their urgency levels."""
        self._stats["deadlines_checked"] += 1
        if current_time is None:
            current_time = time.time()
        self._current_time = current_time
        results: List[Dict[str, Any]] = []
        with self._instance_lock:
            for entry in self._schedules.values():
                if entry.deadline is None:
                    continue
                remaining = entry.deadline - current_time
                if remaining < 0:
                    urgency = UrgencyLevel.PASSED
                elif remaining < 60:
                    urgency = UrgencyLevel.CRITICAL
                elif remaining < 3600:
                    urgency = UrgencyLevel.HIGH
                elif remaining < 21600:
                    urgency = UrgencyLevel.MEDIUM
                else:
                    urgency = UrgencyLevel.LOW
                results.append({
                    "schedule_id": entry.id,
                    "name": entry.name,
                    "deadline": entry.deadline,
                    "remaining": remaining,
                    "urgency": urgency.value,
                })
        return results

    # -- Temporal queries ---------------------------------------------------

    def query_before(self, target_id: str) -> List[str]:
        """Find all intervals that end before the target starts."""
        self._stats["queries_total"] += 1
        target = self.get_interval(target_id)
        if target is None:
            return []
        result: List[str] = []
        with self._instance_lock:
            for iv in self._intervals.values():
                if iv.id == target_id:
                    continue
                rel = self.compute_relation(iv, target)
                if rel in (TemporalRelation.BEFORE, TemporalRelation.MEETS):
                    result.append(iv.id)
        return result

    def query_after(self, target_id: str) -> List[str]:
        """Find all intervals that start after the target ends."""
        self._stats["queries_total"] += 1
        target = self.get_interval(target_id)
        if target is None:
            return []
        result: List[str] = []
        with self._instance_lock:
            for iv in self._intervals.values():
                if iv.id == target_id:
                    continue
                rel = self.compute_relation(iv, target)
                if rel in (TemporalRelation.AFTER, TemporalRelation.MET_BY):
                    result.append(iv.id)
        return result

    def query_during(self, target_id: str) -> List[str]:
        """Find all intervals contained within the target."""
        self._stats["queries_total"] += 1
        target = self.get_interval(target_id)
        if target is None:
            return []
        result: List[str] = []
        with self._instance_lock:
            for iv in self._intervals.values():
                if iv.id == target_id:
                    continue
                rel = self.compute_relation(iv, target)
                if rel in (TemporalRelation.DURING, TemporalRelation.STARTS, TemporalRelation.FINISHES):
                    result.append(iv.id)
        return result

    def query_overlapping(self, target_id: str) -> List[str]:
        """Find all intervals that overlap with the target."""
        self._stats["queries_total"] += 1
        target = self.get_interval(target_id)
        if target is None:
            return []
        result: List[str] = []
        with self._instance_lock:
            for iv in self._intervals.values():
                if iv.id == target_id:
                    continue
                if iv.overlaps_interval(target):
                    result.append(iv.id)
        return result

    # -- Interval arithmetic ------------------------------------------------

    def intersect(self, a_id: str, b_id: str) -> Optional[TimeInterval]:
        """Compute the intersection of two intervals."""
        a = self.get_interval(a_id)
        b = self.get_interval(b_id)
        if a is None or b is None:
            return None
        start = max(a.start, b.start)
        end = min(a.end, b.end)
        if start > end:
            return None
        return TimeInterval(start=start, end=end, label=f"intersect_{a_id}_{b_id}")

    def union(self, a_id: str, b_id: str) -> TimeInterval:
        """Compute the union of two intervals."""
        a = self.get_interval(a_id)
        b = self.get_interval(b_id)
        if a is None or b is None:
            return TimeInterval()
        start = min(a.start, b.start)
        end = max(a.end, b.end)
        return TimeInterval(start=start, end=end, label=f"union_{a_id}_{b_id}")

    def gap(self, a_id: str, b_id: str) -> Optional[float]:
        """Compute the gap between two intervals (0 if they meet/overlap)."""
        a = self.get_interval(a_id)
        b = self.get_interval(b_id)
        if a is None or b is None:
            return None
        if a.end <= b.start:
            return b.start - a.end
        if b.end <= a.start:
            return a.start - b.end
        return 0.0

    # -- Status and snapshot ------------------------------------------------

    def register_handler(self, event: str, handler: Callable) -> None:
        with self._instance_lock:
            self._handlers[event] = handler

    def get_status(self) -> Dict[str, Any]:
        with self._instance_lock:
            return {
                "engine_id": id(self),
                "current_time": self._current_time,
                "interval_count": len(self._intervals),
                "schedule_count": len(self._schedules),
                "constraint_count": len(self._constraints),
                "stats": dict(self._stats),
            }

    def get_snapshot(self) -> TemporalReasoningSnapshot:
        with self._instance_lock:
            deadlines = self.check_deadlines()
            return TemporalReasoningSnapshot(
                interval_count=len(self._intervals),
                schedule_count=len(self._schedules),
                constraint_count=len(self._constraints),
                active_deadlines=deadlines,
                stats=dict(self._stats),
            )

    def reset(self) -> None:
        with self._instance_lock:
            self._intervals.clear()
            self._schedules.clear()
            self._constraints.clear()
            self._stats = {
                "queries_total": 0,
                "relations_computed": 0,
                "schedules_resolved": 0,
                "deadlines_checked": 0,
            }


# Module-level factory
def get_temporal_reasoning_engine() -> TemporalReasoningEngine:
    return TemporalReasoningEngine.get_instance()
