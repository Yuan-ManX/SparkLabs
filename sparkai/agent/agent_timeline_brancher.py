"""
SparkLabs Agent - Timeline Brancher

Timeline branching system for the SparkLabs AI-native game engine.
Creates, manages, and compares multiple parallel simulation timelines.
Each timeline branch is an isolated state that can be replayed,
compared, and merged to support what-if analysis and narrative
exploration.

Architecture:
  TimelineBrancherEngine (Singleton)
    |-- Timeline Creation & Branching (parallel simulation paths)
    |-- Event Recording (per-tick event log)
    |-- State Snapshots (world and entity state capture)
    |-- Timeline Comparison (multi-axis diffing)
    |-- Timeline Merging (strategy-based reconciliation)
    |-- Timeline Replay (range-based event playback)

Operations:
  - create_timeline: spawn a new root timeline
  - branch_timeline: fork a timeline at a given tick
  - record_event / save_state: append per-tick observations
  - compare_timelines: diff two timelines along an axis
  - merge_timelines: reconcile two timelines under a strategy
  - replay_timeline: re-execute events across a tick range
  - pause / resume / abandon: lifecycle control
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class TimelineStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    MERGED = "merged"


class BranchPointType(Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    EVENT_TRIGGERED = "event_triggered"
    PLAYER_CHOICE = "player_choice"


class ComparisonAxis(Enum):
    STATE_DIFF = "state_diff"
    EVENT_SEQUENCE = "event_sequence"
    OUTCOME_DIVERGENCE = "outcome_divergence"
    CHARACTER_TRAJECTORY = "character_trajectory"


class MergeStrategy(Enum):
    PREFER_SOURCE = "prefer_source"
    PREFER_TARGET = "prefer_target"
    UNION = "union"
    INTERSECTION = "intersection"
    CUSTOM = "custom"


# Statuses that allow new events and state saves.
_ACTIVE_STATUSES: Set[TimelineStatus] = {TimelineStatus.ACTIVE}

# Statuses that block any further mutation.
_TERMINAL_STATUSES: Set[TimelineStatus] = {
    TimelineStatus.ABANDONED,
    TimelineStatus.MERGED,
    TimelineStatus.COMPLETED,
}


@dataclass
class TimelineEvent:
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timeline_id: str = ""
    tick: int = 0
    event_type: str = ""
    description: str = ""
    entity_ids: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timeline_id": self.timeline_id,
            "tick": self.tick,
            "event_type": self.event_type,
            "description": self.description,
            "entity_ids": list(self.entity_ids),
            "data": dict(self.data),
            "timestamp": self.timestamp,
        }


@dataclass
class TimelineState:
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timeline_id: str = ""
    tick: int = 0
    world_state: Dict[str, Any] = field(default_factory=dict)
    entity_states: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "timeline_id": self.timeline_id,
            "tick": self.tick,
            "world_state": dict(self.world_state),
            "entity_states": dict(self.entity_states),
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class TimelineBranch:
    timeline_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: str = ""
    branch_point_tick: int = 0
    branch_type: BranchPointType = BranchPointType.MANUAL
    name: str = ""
    description: str = ""
    status: TimelineStatus = TimelineStatus.ACTIVE
    events: List[str] = field(default_factory=list)
    states: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: _time_module.time())
    last_active: float = field(default_factory=lambda: _time_module.time())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeline_id": self.timeline_id,
            "parent_id": self.parent_id,
            "branch_point_tick": self.branch_point_tick,
            "branch_type": self.branch_type.value,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "events": list(self.events),
            "states": list(self.states),
            "event_count": len(self.events),
            "state_count": len(self.states),
            "created_at": self.created_at,
            "last_active": self.last_active,
            "metadata": dict(self.metadata),
        }


@dataclass
class BranchComparison:
    comparison_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_timeline_id: str = ""
    target_timeline_id: str = ""
    axis: ComparisonAxis = ComparisonAxis.STATE_DIFF
    differences: List[Dict[str, Any]] = field(default_factory=list)
    similarity_score: float = 0.0
    divergence_tick: Optional[int] = None
    analysis: str = ""
    timestamp: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "source_timeline_id": self.source_timeline_id,
            "target_timeline_id": self.target_timeline_id,
            "axis": self.axis.value,
            "differences": list(self.differences),
            "similarity_score": round(self.similarity_score, 4),
            "divergence_tick": self.divergence_tick,
            "analysis": self.analysis,
            "timestamp": self.timestamp,
        }


@dataclass
class MergeResult:
    merge_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_timeline_id: str = ""
    target_timeline_id: str = ""
    strategy: MergeStrategy = MergeStrategy.UNION
    merged_state: Dict[str, Any] = field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    resolutions: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merge_id": self.merge_id,
            "source_timeline_id": self.source_timeline_id,
            "target_timeline_id": self.target_timeline_id,
            "strategy": self.strategy.value,
            "merged_state": dict(self.merged_state),
            "conflicts": list(self.conflicts),
            "resolutions": list(self.resolutions),
            "timestamp": self.timestamp,
        }


class TimelineBrancherEngine:
    """Singleton engine that manages parallel timeline branches.

    Holds timelines, their events, and their state snapshots in memory.
    All public methods are thread-safe through a single instance lock.
    The lock is a plain threading.Lock, so public methods must not
    invoke each other while holding it; helper methods that operate on
    unlocked data are prefixed with an underscore.
    """

    _instance: Optional["TimelineBrancherEngine"] = None
    _singleton_lock: threading.Lock = threading.Lock()

    MAX_EVENTS_PER_TIMELINE: int = 1000
    MAX_STATES_PER_TIMELINE: int = 500
    MAX_TIMELINES: int = 256
    MAX_BRANCH_DEPTH: int = 16

    def __new__(cls) -> "TimelineBrancherEngine":
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._timelines: Dict[str, TimelineBranch] = {}
        self._events: Dict[str, TimelineEvent] = {}
        self._states: Dict[str, TimelineState] = {}
        # Ordered event ids per timeline.
        self._timeline_events: Dict[str, List[str]] = {}
        # Ordered state ids per timeline.
        self._timeline_states: Dict[str, List[str]] = {}
        # Parent -> direct children mapping for lineage walks.
        self._children: Dict[str, List[str]] = {}
        # Lifetime counters (never reset).
        self._total_timelines_created: int = 0
        self._total_events_recorded: int = 0
        self._total_states_saved: int = 0
        self._total_branches_created: int = 0
        self._total_merges_performed: int = 0
        self._total_comparisons_performed: int = 0
        self._data_lock: threading.Lock = threading.Lock()
        self._initialized = True

    # ------------------------------------------------------------------
    # Internal helpers (operate without acquiring the lock).
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> float:
        return _time_module.time()

    def _touch(self, timeline: TimelineBranch) -> None:
        timeline.last_active = self._now()

    def _require_timeline(self, timeline_id: str) -> TimelineBranch:
        timeline = self._timelines.get(timeline_id)
        if timeline is None:
            raise ValueError(f"Timeline {timeline_id} not found")
        return timeline

    def _require_mutable(self, timeline_id: str) -> TimelineBranch:
        timeline = self._require_timeline(timeline_id)
        if timeline.status not in _ACTIVE_STATUSES:
            raise ValueError(
                f"Timeline {timeline_id} is {timeline.status.value}; "
                f"only active timelines accept mutations"
            )
        return timeline

    def _events_for(self, timeline_id: str) -> List[TimelineEvent]:
        ids = self._timeline_events.get(timeline_id, [])
        return [self._events[eid] for eid in ids if eid in self._events]

    def _states_for(self, timeline_id: str) -> List[TimelineState]:
        ids = self._timeline_states.get(timeline_id, [])
        return [self._states[sid] for sid in ids if sid in self._states]

    def _latest_state(self, timeline_id: str) -> Optional[TimelineState]:
        states = self._states_for(timeline_id)
        if not states:
            return None
        return max(states, key=lambda s: s.tick)

    def _branch_depth(self, timeline_id: str) -> int:
        depth = 0
        current = timeline_id
        seen: Set[str] = set()
        while current in self._timelines:
            parent = self._timelines[current].parent_id
            if not parent or parent == current or parent in seen:
                break
            seen.add(current)
            current = parent
            depth += 1
            if depth > self.MAX_BRANCH_DEPTH:
                break
        return depth

    # ------------------------------------------------------------------
    # Timeline lifecycle.
    # ------------------------------------------------------------------

    def create_timeline(
        self,
        name: str,
        description: str = "",
        parent_id: str = "",
        branch_point_tick: int = 0,
        branch_type: BranchPointType = BranchPointType.MANUAL,
    ) -> TimelineBranch:
        _time_module.sleep(0.001)
        with self._data_lock:
            if len(self._timelines) >= self.MAX_TIMELINES:
                raise ValueError(
                    f"Maximum timeline count reached ({self.MAX_TIMELINES})"
                )

            timeline = TimelineBranch(
                timeline_id=uuid.uuid4().hex,
                parent_id=parent_id,
                branch_point_tick=branch_point_tick,
                branch_type=branch_type,
                name=name or "Primary Timeline",
                description=description,
                status=TimelineStatus.ACTIVE,
                events=[],
                states=[],
                created_at=self._now(),
                last_active=self._now(),
                metadata={},
            )

            self._timelines[timeline.timeline_id] = timeline
            self._timeline_events[timeline.timeline_id] = []
            self._timeline_states[timeline.timeline_id] = []
            self._children[timeline.timeline_id] = []

            if parent_id:
                parent = self._timelines.get(parent_id)
                if parent is not None:
                    self._children.setdefault(parent_id, []).append(
                        timeline.timeline_id
                    )

            self._total_timelines_created += 1
            return timeline

    def branch_timeline(
        self,
        source_timeline_id: str,
        branch_point_tick: int,
        name: str = "",
        description: str = "",
        branch_type: BranchPointType = BranchPointType.MANUAL,
    ) -> TimelineBranch:
        _time_module.sleep(0.001)
        with self._data_lock:
            source = self._require_timeline(source_timeline_id)
            if source.status in _TERMINAL_STATUSES:
                raise ValueError(
                    f"Cannot branch from {source.status.value} timeline "
                    f"{source_timeline_id}"
                )

            depth = self._branch_depth(source_timeline_id) + 1
            if depth > self.MAX_BRANCH_DEPTH:
                raise ValueError(
                    f"Branch depth {depth} exceeds limit "
                    f"{self.MAX_BRANCH_DEPTH}"
                )

            branch_name = name or f"{source.name} - Branch {depth}"
            branch = TimelineBranch(
                timeline_id=uuid.uuid4().hex,
                parent_id=source_timeline_id,
                branch_point_tick=branch_point_tick,
                branch_type=branch_type,
                name=branch_name,
                description=description
                or f"Branch from '{source.name}' at tick {branch_point_tick}",
                status=TimelineStatus.ACTIVE,
                events=[],
                states=[],
                created_at=self._now(),
                last_active=self._now(),
                metadata={"source_name": source.name},
            )

            # Copy events at or before the branch point so the branch
            # starts with the same history as its parent.
            copied_event_ids: List[str] = []
            for eid in self._timeline_events.get(source_timeline_id, []):
                event = self._events.get(eid)
                if event is None or event.tick > branch_point_tick:
                    continue
                clone = TimelineEvent(
                    event_id=uuid.uuid4().hex,
                    timeline_id=branch.timeline_id,
                    tick=event.tick,
                    event_type=event.event_type,
                    description=event.description,
                    entity_ids=list(event.entity_ids),
                    data=dict(event.data),
                    timestamp=self._now(),
                )
                self._events[clone.event_id] = clone
                copied_event_ids.append(clone.event_id)

            # Copy states at or before the branch point.
            copied_state_ids: List[str] = []
            for sid in self._timeline_states.get(source_timeline_id, []):
                state = self._states.get(sid)
                if state is None or state.tick > branch_point_tick:
                    continue
                clone = TimelineState(
                    state_id=uuid.uuid4().hex,
                    timeline_id=branch.timeline_id,
                    tick=state.tick,
                    world_state=dict(state.world_state),
                    entity_states=dict(state.entity_states),
                    metadata=dict(state.metadata),
                    timestamp=self._now(),
                )
                self._states[clone.state_id] = clone
                copied_state_ids.append(clone.state_id)

            branch.events = copied_event_ids
            branch.states = copied_state_ids

            self._timelines[branch.timeline_id] = branch
            self._timeline_events[branch.timeline_id] = copied_event_ids
            self._timeline_states[branch.timeline_id] = copied_state_ids
            self._children[branch.timeline_id] = []
            self._children.setdefault(source_timeline_id, []).append(
                branch.timeline_id
            )

            self._total_timelines_created += 1
            self._total_branches_created += 1
            self._total_events_recorded += len(copied_event_ids)
            self._total_states_saved += len(copied_state_ids)
            return branch

    def pause_timeline(self, timeline_id: str) -> bool:
        _time_module.sleep(0.001)
        with self._data_lock:
            timeline = self._require_timeline(timeline_id)
            if timeline.status != TimelineStatus.ACTIVE:
                return False
            timeline.status = TimelineStatus.PAUSED
            self._touch(timeline)
            return True

    def resume_timeline(self, timeline_id: str) -> bool:
        _time_module.sleep(0.001)
        with self._data_lock:
            timeline = self._require_timeline(timeline_id)
            if timeline.status != TimelineStatus.PAUSED:
                return False
            timeline.status = TimelineStatus.ACTIVE
            self._touch(timeline)
            return True

    def abandon_timeline(self, timeline_id: str, reason: str = "") -> bool:
        _time_module.sleep(0.001)
        with self._data_lock:
            timeline = self._require_timeline(timeline_id)
            if timeline.status in _TERMINAL_STATUSES:
                return False
            timeline.status = TimelineStatus.ABANDONED
            timeline.metadata["abandon_reason"] = reason or "abandoned by caller"
            self._touch(timeline)
            return True

    # ------------------------------------------------------------------
    # Event and state recording.
    # ------------------------------------------------------------------

    def record_event(
        self,
        timeline_id: str,
        tick: int,
        event_type: str,
        description: str = "",
        entity_ids: Optional[List[str]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> TimelineEvent:
        _time_module.sleep(0.001)
        with self._data_lock:
            timeline = self._require_mutable(timeline_id)
            if len(timeline.events) >= self.MAX_EVENTS_PER_TIMELINE:
                raise ValueError(
                    f"Timeline {timeline_id} reached event cap "
                    f"({self.MAX_EVENTS_PER_TIMELINE})"
                )

            event = TimelineEvent(
                event_id=uuid.uuid4().hex,
                timeline_id=timeline_id,
                tick=tick,
                event_type=event_type,
                description=description,
                entity_ids=list(entity_ids or []),
                data=dict(data or {}),
                timestamp=self._now(),
            )

            self._events[event.event_id] = event
            timeline.events.append(event.event_id)
            self._timeline_events.setdefault(timeline_id, []).append(
                event.event_id
            )
            self._touch(timeline)
            self._total_events_recorded += 1
            return event

    def save_state(
        self,
        timeline_id: str,
        tick: int,
        world_state: Optional[Dict[str, Any]] = None,
        entity_states: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TimelineState:
        _time_module.sleep(0.001)
        with self._data_lock:
            timeline = self._require_mutable(timeline_id)
            if len(timeline.states) >= self.MAX_STATES_PER_TIMELINE:
                raise ValueError(
                    f"Timeline {timeline_id} reached state cap "
                    f"({self.MAX_STATES_PER_TIMELINE})"
                )

            state = TimelineState(
                state_id=uuid.uuid4().hex,
                timeline_id=timeline_id,
                tick=tick,
                world_state=dict(world_state or {}),
                entity_states=dict(entity_states or {}),
                metadata=dict(metadata or {}),
                timestamp=self._now(),
            )

            self._states[state.state_id] = state
            timeline.states.append(state.state_id)
            self._timeline_states.setdefault(timeline_id, []).append(
                state.state_id
            )
            self._touch(timeline)
            self._total_states_saved += 1
            return state

    # ------------------------------------------------------------------
    # Read paths.
    # ------------------------------------------------------------------

    def get_timeline(self, timeline_id: str) -> Optional[TimelineBranch]:
        _time_module.sleep(0.001)
        with self._data_lock:
            return self._timelines.get(timeline_id)

    def list_timelines(
        self, status_filter: Optional[TimelineStatus] = None
    ) -> List[Dict[str, Any]]:
        _time_module.sleep(0.001)
        with self._data_lock:
            result: List[Dict[str, Any]] = []
            for timeline in self._timelines.values():
                if status_filter is not None and timeline.status != status_filter:
                    continue
                result.append(timeline.to_dict())
            return result

    def get_timeline_events(
        self,
        timeline_id: str,
        from_tick: Optional[int] = None,
        to_tick: Optional[int] = None,
    ) -> List[TimelineEvent]:
        _time_module.sleep(0.001)
        with self._data_lock:
            self._require_timeline(timeline_id)
            events = self._events_for(timeline_id)
            filtered: List[TimelineEvent] = []
            for event in events:
                if from_tick is not None and event.tick < from_tick:
                    continue
                if to_tick is not None and event.tick > to_tick:
                    continue
                filtered.append(event)
            filtered.sort(key=lambda e: (e.tick, e.timestamp))
            return filtered

    def replay_timeline(
        self,
        timeline_id: str,
        from_tick: Optional[int] = None,
        to_tick: Optional[int] = None,
    ) -> List[TimelineEvent]:
        _time_module.sleep(0.001)
        # Replays are read-only, so we delegate to the locked reader.
        return self.get_timeline_events(timeline_id, from_tick, to_tick)

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        with self._data_lock:
            total_timelines = len(self._timelines)
            status_counts: Dict[str, int] = {}
            branch_counts: Dict[str, int] = {}
            max_event_count = 0
            max_event_timeline_id = ""
            depth_sum = 0
            for tid, timeline in self._timelines.items():
                status_counts[timeline.status.value] = (
                    status_counts.get(timeline.status.value, 0) + 1
                )
                event_count = len(timeline.events)
                if event_count > max_event_count:
                    max_event_count = event_count
                    max_event_timeline_id = tid
                depth = self._branch_depth(tid)
                depth_sum += depth
                branch_counts[str(depth)] = (
                    branch_counts.get(str(depth), 0) + 1
                )

            avg_depth = round(depth_sum / total_timelines, 2) if total_timelines else 0.0
            avg_events = (
                round(self._total_events_recorded / total_timelines, 2)
                if total_timelines
                else 0.0
            )

            return {
                "total_timelines": total_timelines,
                "total_events": len(self._events),
                "total_states": len(self._states),
                "timelines_created_lifetime": self._total_timelines_created,
                "events_recorded_lifetime": self._total_events_recorded,
                "states_saved_lifetime": self._total_states_saved,
                "branches_created_lifetime": self._total_branches_created,
                "merges_performed_lifetime": self._total_merges_performed,
                "comparisons_performed_lifetime": self._total_comparisons_performed,
                "status_distribution": status_counts,
                "branch_depth_distribution": branch_counts,
                "average_events_per_timeline": avg_events,
                "average_branch_depth": avg_depth,
                "max_event_timeline_id": max_event_timeline_id,
                "max_event_count": max_event_count,
                "max_timelines_limit": self.MAX_TIMELINES,
                "max_events_per_timeline_limit": self.MAX_EVENTS_PER_TIMELINE,
                "max_states_per_timeline_limit": self.MAX_STATES_PER_TIMELINE,
                "max_branch_depth_limit": self.MAX_BRANCH_DEPTH,
            }

    # ------------------------------------------------------------------
    # Comparison.
    # ------------------------------------------------------------------

    def compare_timelines(
        self,
        source_timeline_id: str,
        target_timeline_id: str,
        axis: ComparisonAxis = ComparisonAxis.STATE_DIFF,
    ) -> BranchComparison:
        _time_module.sleep(0.001)
        with self._data_lock:
            source = self._require_timeline(source_timeline_id)
            target = self._require_timeline(target_timeline_id)

            source_events = self._events_for(source_timeline_id)
            target_events = self._events_for(target_timeline_id)
            source_states = self._states_for(source_timeline_id)
            target_states = self._states_for(target_timeline_id)

            if axis == ComparisonAxis.STATE_DIFF:
                differences, similarity, divergence_tick, analysis = (
                    self._compare_state_diff(
                        source_states, target_states
                    )
                )
            elif axis == ComparisonAxis.EVENT_SEQUENCE:
                differences, similarity, divergence_tick, analysis = (
                    self._compare_event_sequence(
                        source_events, target_events
                    )
                )
            elif axis == ComparisonAxis.OUTCOME_DIVERGENCE:
                differences, similarity, divergence_tick, analysis = (
                    self._compare_outcome_divergence(
                        source, target, source_states, target_states
                    )
                )
            elif axis == ComparisonAxis.CHARACTER_TRAJECTORY:
                differences, similarity, divergence_tick, analysis = (
                    self._compare_character_trajectory(
                        source_states, target_states
                    )
                )
            else:
                raise ValueError(f"Unsupported comparison axis: {axis}")

            comparison = BranchComparison(
                comparison_id=uuid.uuid4().hex,
                source_timeline_id=source_timeline_id,
                target_timeline_id=target_timeline_id,
                axis=axis,
                differences=differences,
                similarity_score=similarity,
                divergence_tick=divergence_tick,
                analysis=analysis,
                timestamp=self._now(),
            )

            self._total_comparisons_performed += 1
            return comparison

    def _compare_state_diff(
        self,
        source_states: List[TimelineState],
        target_states: List[TimelineState],
    ) -> Tuple[List[Dict[str, Any]], float, Optional[int], str]:
        differences: List[Dict[str, Any]] = []
        similarity = 0.0
        divergence_tick: Optional[int] = None

        source_latest = (
            max(source_states, key=lambda s: s.tick) if source_states else None
        )
        target_latest = (
            max(target_states, key=lambda s: s.tick) if target_states else None
        )

        if source_latest is None and target_latest is None:
            return differences, 1.0, None, "Both timelines have no states."

        if source_latest is None or target_latest is None:
            missing = "source" if source_latest is None else "target"
            differences.append(
                {
                    "type": "missing_state",
                    "missing_side": missing,
                    "tick": (target_latest or source_latest).tick,
                }
            )
            return differences, 0.0, None, f"{missing} timeline has no states."

        # Compare world_state keys.
        world_keys = set(source_latest.world_state.keys()) | set(
            target_latest.world_state.keys()
        )
        matching = 0
        for key in sorted(world_keys):
            sv = source_latest.world_state.get(key)
            tv = target_latest.world_state.get(key)
            if sv == tv:
                matching += 1
            else:
                differences.append(
                    {
                        "type": "world_state",
                        "key": key,
                        "source_value": sv,
                        "target_value": tv,
                        "tick": source_latest.tick,
                    }
                )

        # Compare entity_states keys.
        entity_keys = set(source_latest.entity_states.keys()) | set(
            target_latest.entity_states.keys()
        )
        for key in sorted(entity_keys):
            sv = source_latest.entity_states.get(key)
            tv = target_latest.entity_states.get(key)
            if sv == tv:
                matching += 1
            else:
                differences.append(
                    {
                        "type": "entity_state",
                        "key": key,
                        "source_value": sv,
                        "target_value": tv,
                        "tick": source_latest.tick,
                    }
                )

        total_keys = len(world_keys) + len(entity_keys)
        similarity = matching / total_keys if total_keys else 1.0

        # Walk paired states by tick to find the first divergence.
        source_by_tick = {s.tick: s for s in source_states}
        target_by_tick = {s.tick: s for s in target_states}
        shared_ticks = sorted(set(source_by_tick) & set(target_by_tick))
        for tick in shared_ticks:
            s_state = source_by_tick[tick]
            t_state = target_by_tick[tick]
            if (
                s_state.world_state != t_state.world_state
                or s_state.entity_states != t_state.entity_states
            ):
                divergence_tick = tick
                break

        analysis = (
            f"State diff found {len(differences)} differing keys across "
            f"{total_keys} total keys. Similarity {similarity:.3f}. "
            f"Divergence first observed at tick {divergence_tick}."
        )
        return differences, similarity, divergence_tick, analysis

    def _compare_event_sequence(
        self,
        source_events: List[TimelineEvent],
        target_events: List[TimelineEvent],
    ) -> Tuple[List[Dict[str, Any]], float, Optional[int], str]:
        differences: List[Dict[str, Any]] = []
        divergence_tick: Optional[int] = None

        source_by_tick: Dict[int, List[TimelineEvent]] = {}
        for event in source_events:
            source_by_tick.setdefault(event.tick, []).append(event)
        target_by_tick: Dict[int, List[TimelineEvent]] = {}
        for event in target_events:
            target_by_tick.setdefault(event.tick, []).append(event)

        all_ticks = sorted(set(source_by_tick) | set(target_by_tick))
        matching_ticks = 0
        for tick in all_ticks:
            s_events = source_by_tick.get(tick, [])
            t_events = target_by_tick.get(tick, [])
            s_types = sorted(e.event_type for e in s_events)
            t_types = sorted(e.event_type for e in t_events)
            if s_types == t_types:
                matching_ticks += 1
            else:
                differences.append(
                    {
                        "type": "event_sequence",
                        "tick": tick,
                        "source_event_types": s_types,
                        "target_event_types": t_types,
                        "source_count": len(s_events),
                        "target_count": len(t_events),
                    }
                )
                if divergence_tick is None:
                    divergence_tick = tick

        similarity = (
            matching_ticks / len(all_ticks) if all_ticks else 1.0
        )
        analysis = (
            f"Event sequence diff found {len(differences)} divergent ticks "
            f"out of {len(all_ticks)} shared ticks. Similarity "
            f"{similarity:.3f}. First divergence at tick {divergence_tick}."
        )
        return differences, similarity, divergence_tick, analysis

    def _compare_outcome_divergence(
        self,
        source: TimelineBranch,
        target: TimelineBranch,
        source_states: List[TimelineState],
        target_states: List[TimelineState],
    ) -> Tuple[List[Dict[str, Any]], float, Optional[int], str]:
        differences: List[Dict[str, Any]] = []
        divergence_tick: Optional[int] = None

        source_latest = (
            max(source_states, key=lambda s: s.tick) if source_states else None
        )
        target_latest = (
            max(target_states, key=lambda s: s.tick) if target_states else None
        )

        source_outcome = (
            source_latest.metadata.get("outcome", {})
            if source_latest
            else {}
        )
        target_outcome = (
            target_latest.metadata.get("outcome", {})
            if target_latest
            else {}
        )

        outcome_keys = set(source_outcome.keys()) | set(target_outcome.keys())
        matching = 0
        for key in sorted(outcome_keys):
            sv = source_outcome.get(key)
            tv = target_outcome.get(key)
            if sv == tv:
                matching += 1
            else:
                differences.append(
                    {
                        "type": "outcome",
                        "key": key,
                        "source_value": sv,
                        "target_value": tv,
                    }
                )

        # Compare terminal status as part of outcome.
        if source.status != target.status:
            differences.append(
                {
                    "type": "status",
                    "source_status": source.status.value,
                    "target_status": target.status.value,
                }
            )
        else:
            matching += 1

        total = len(outcome_keys) + 1
        similarity = matching / total if total else 1.0

        # Divergence tick is the first tick where outcome metadata differs.
        source_by_tick = {s.tick: s for s in source_states}
        target_by_tick = {s.tick: s for s in target_states}
        for tick in sorted(set(source_by_tick) & set(target_by_tick)):
            s_out = source_by_tick[tick].metadata.get("outcome", {})
            t_out = target_by_tick[tick].metadata.get("outcome", {})
            if s_out != t_out:
                divergence_tick = tick
                break

        analysis = (
            f"Outcome divergence found {len(differences)} differences. "
            f"Similarity {similarity:.3f}. Outcome divergence first "
            f"observed at tick {divergence_tick}."
        )
        return differences, similarity, divergence_tick, analysis

    def _compare_character_trajectory(
        self,
        source_states: List[TimelineState],
        target_states: List[TimelineState],
    ) -> Tuple[List[Dict[str, Any]], float, Optional[int], str]:
        differences: List[Dict[str, Any]] = []
        divergence_tick: Optional[int] = None

        # Build per-entity trajectories keyed by tick.
        source_traj: Dict[str, Dict[int, Any]] = {}
        for state in source_states:
            for entity_id, value in state.entity_states.items():
                source_traj.setdefault(entity_id, {})[state.tick] = value
        target_traj: Dict[str, Dict[int, Any]] = {}
        for state in target_states:
            for entity_id, value in state.entity_states.items():
                target_traj.setdefault(entity_id, {})[state.tick] = value

        all_entities = set(source_traj) | set(target_traj)
        matching = 0
        total = 0
        for entity_id in sorted(all_entities):
            s_path = source_traj.get(entity_id, {})
            t_path = target_traj.get(entity_id, {})
            shared_ticks = set(s_path) & set(t_path)
            total += len(shared_ticks)
            for tick in sorted(shared_ticks):
                if s_path[tick] == t_path[tick]:
                    matching += 1
                else:
                    differences.append(
                        {
                            "type": "character_trajectory",
                            "entity_id": entity_id,
                            "tick": tick,
                            "source_value": s_path[tick],
                            "target_value": t_path[tick],
                        }
                    )
                    if divergence_tick is None or tick < divergence_tick:
                        divergence_tick = tick

        similarity = matching / total if total else 1.0
        analysis = (
            f"Character trajectory diff found {len(differences)} divergent "
            f"entity-ticks across {len(all_entities)} entities. Similarity "
            f"{similarity:.3f}. First divergence at tick {divergence_tick}."
        )
        return differences, similarity, divergence_tick, analysis

    # ------------------------------------------------------------------
    # Merging.
    # ------------------------------------------------------------------

    def merge_timelines(
        self,
        source_timeline_id: str,
        target_timeline_id: str,
        strategy: MergeStrategy = MergeStrategy.UNION,
    ) -> MergeResult:
        _time_module.sleep(0.001)
        with self._data_lock:
            source = self._require_timeline(source_timeline_id)
            target = self._require_timeline(target_timeline_id)

            if source_timeline_id == target_timeline_id:
                raise ValueError("Cannot merge a timeline with itself")

            if source.status in _TERMINAL_STATUSES or target.status in _TERMINAL_STATUSES:
                raise ValueError(
                    "Cannot merge timelines in terminal states "
                    f"({source.status.value}, {target.status.value})"
                )

            source_state = self._latest_state(source_timeline_id)
            target_state = self._latest_state(target_timeline_id)

            source_world = source_state.world_state if source_state else {}
            source_entities = source_state.entity_states if source_state else {}
            target_world = target_state.world_state if target_state else {}
            target_entities = target_state.entity_states if target_state else {}

            merged_world, world_conflicts, world_resolutions = (
                self._merge_dicts(source_world, target_world, strategy, "world_state")
            )
            merged_entities, entity_conflicts, entity_resolutions = (
                self._merge_dicts(
                    source_entities, target_entities, strategy, "entity_states"
                )
            )

            conflicts = world_conflicts + entity_conflicts
            resolutions = world_resolutions + entity_resolutions

            merged_state = {
                "world_state": merged_world,
                "entity_states": merged_entities,
                "source_timeline_id": source_timeline_id,
                "target_timeline_id": target_timeline_id,
                "source_tick": source_state.tick if source_state else 0,
                "target_tick": target_state.tick if target_state else 0,
            }

            result = MergeResult(
                merge_id=uuid.uuid4().hex,
                source_timeline_id=source_timeline_id,
                target_timeline_id=target_timeline_id,
                strategy=strategy,
                merged_state=merged_state,
                conflicts=conflicts,
                resolutions=resolutions,
                timestamp=self._now(),
            )

            # Mark the source as merged into the target; target remains
            # active so it can absorb further events.
            source.status = TimelineStatus.MERGED
            source.metadata["merged_into"] = target_timeline_id
            source.metadata["merge_id"] = result.merge_id
            self._touch(source)
            self._touch(target)

            self._total_merges_performed += 1
            return result

    def _merge_dicts(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        strategy: MergeStrategy,
        namespace: str,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Merge two dictionaries under the given strategy.

        Returns the merged dict, the list of detected conflicts, and the
        list of applied resolutions.
        """
        merged: Dict[str, Any] = {}
        conflicts: List[Dict[str, Any]] = []
        resolutions: List[Dict[str, Any]] = []

        all_keys = set(source.keys()) | set(target.keys())
        for key in sorted(all_keys):
            in_source = key in source
            in_target = key in target
            sv = source.get(key)
            tv = target.get(key)

            if in_source and in_target:
                if sv == tv:
                    merged[key] = sv
                    continue
                # Conflict: same key, different values.
                conflicts.append(
                    {
                        "namespace": namespace,
                        "key": key,
                        "source_value": sv,
                        "target_value": tv,
                    }
                )
                resolved_value, resolution_label = self._resolve_conflict(
                    sv, tv, strategy
                )
                if resolved_value is not None or resolution_label != "dropped":
                    merged[key] = resolved_value
                resolutions.append(
                    {
                        "namespace": namespace,
                        "key": key,
                        "resolution": resolution_label,
                        "value": resolved_value,
                    }
                )
            elif in_source:
                if strategy in (
                    MergeStrategy.PREFER_SOURCE,
                    MergeStrategy.UNION,
                    MergeStrategy.CUSTOM,
                ):
                    merged[key] = sv
                # INTERSECTION drops source-only keys.
            else:  # only in target
                if strategy in (
                    MergeStrategy.PREFER_TARGET,
                    MergeStrategy.UNION,
                    MergeStrategy.CUSTOM,
                ):
                    merged[key] = tv
                # INTERSECTION drops target-only keys.

        return merged, conflicts, resolutions

    @staticmethod
    def _resolve_conflict(
        source_value: Any,
        target_value: Any,
        strategy: MergeStrategy,
    ) -> Tuple[Any, str]:
        if strategy == MergeStrategy.PREFER_SOURCE:
            return source_value, "prefer_source"
        if strategy == MergeStrategy.PREFER_TARGET:
            return target_value, "prefer_target"
        if strategy == MergeStrategy.UNION:
            # Keep both values in a list so no data is lost.
            return [source_value, target_value], "union"
        if strategy == MergeStrategy.INTERSECTION:
            # Conflicting keys are dropped because no agreement exists.
            return None, "dropped"
        # CUSTOM falls back to target preference with a distinct label.
        return target_value, "custom_target"


def get_timeline_brancher() -> TimelineBrancherEngine:
    """Return the singleton TimelineBrancherEngine instance."""
    return TimelineBrancherEngine()
