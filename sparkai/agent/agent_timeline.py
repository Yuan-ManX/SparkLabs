"""
SparkLabs Agent - Timeline Branching System

Timeline branching system for game narrative and world simulation.
Allows agents to create, manage, and switch between multiple parallel
timeline branches. Each branch is an isolated state that can be replayed,
compared, and merged to support what-if analysis and narrative exploration.

Architecture:
  TimelineManager (Singleton)
    |-- Timeline Creation (spawn new root timelines)
    |-- Event Recording (per-timeline event log)
    |-- Branching (fork a timeline at current state)
    |-- State Snapshots (save and restore timeline state)
    |-- Timeline Merging (reconcile two timelines)
    |-- Lifecycle Control (active/paused/frozen/archived management)

Operations:
  - create_timeline: spawn a new root timeline
  - record_event: append an event to a timeline
  - create_branch: fork a timeline at the current point
  - switch_timeline: change the active timeline
  - merge_timelines: reconcile two timelines
  - create_snapshot: capture current timeline state
  - restore_snapshot: restore a timeline to a previous snapshot
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TimelineState(Enum):
    """Lifecycle states for a timeline branch."""

    ACTIVE = "active"
    PAUSED = "paused"
    FROZEN = "frozen"
    MERGED = "merged"
    ARCHIVED = "archived"


# States that allow new events and mutations.
_MUTABLE_STATES: set = {TimelineState.ACTIVE, TimelineState.PAUSED}

# States that block any further mutation.
_TERMINAL_STATES: set = {
    TimelineState.FROZEN,
    TimelineState.MERGED,
    TimelineState.ARCHIVED,
}


@dataclass
class TimelineEvent:
    """A single event recorded on a timeline branch."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timeline_id: str = ""
    event_type: str = ""
    description: str = ""
    timestamp: float = field(default_factory=lambda: _time_module.time())
    agent_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timeline_id": self.timeline_id,
            "event_type": self.event_type,
            "description": self.description,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "data": dict(self.data),
            "tags": list(self.tags),
        }


@dataclass
class BranchPoint:
    """Marker where a timeline was forked into a child branch."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timeline_id: str = ""
    event_id: str = ""
    branch_name: str = ""
    description: str = ""
    created_at: float = field(default_factory=lambda: _time_module.time())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timeline_id": self.timeline_id,
            "event_id": self.event_id,
            "branch_name": self.branch_name,
            "description": self.description,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class Timeline:
    """A single timeline branch with its events and branch points."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    state: TimelineState = TimelineState.ACTIVE
    branch_points: List[BranchPoint] = field(default_factory=list)
    events: List[TimelineEvent] = field(default_factory=list)
    parent_timeline_id: str = ""
    created_at: float = field(default_factory=lambda: _time_module.time())
    updated_at: float = field(default_factory=lambda: _time_module.time())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "parent_timeline_id": self.parent_timeline_id,
            "branch_point_count": len(self.branch_points),
            "event_count": len(self.events),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class TimelineSnapshot:
    """A frozen capture of a timeline at a specific event index."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timeline_id: str = ""
    event_index: int = 0
    state_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: _time_module.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timeline_id": self.timeline_id,
            "event_index": self.event_index,
            "timestamp": self.timestamp,
            "state_data_keys": list(self.state_data.keys()),
        }


@dataclass
class TimelineBranchResult:
    """Result of a branch creation operation."""

    success: bool = False
    branch_id: str = ""
    timeline_id: str = ""
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "branch_id": self.branch_id,
            "timeline_id": self.timeline_id,
            "message": self.message,
        }


@dataclass
class TimelineMergeResult:
    """Result of merging two timelines together."""

    success: bool = False
    source_timeline_id: str = ""
    target_timeline_id: str = ""
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    merged_events: int = 0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "source_timeline_id": self.source_timeline_id,
            "target_timeline_id": self.target_timeline_id,
            "conflict_count": len(self.conflicts),
            "merged_events": self.merged_events,
            "message": self.message,
        }


class TimelineManager:
    """Singleton manager for the timeline branching system.

    Holds all timelines, their events, branch points, and snapshots
    in memory. All public methods are thread-safe through a reentrant
    lock (RLock). The lock is reentrant so helper methods can be called
    from within locked public methods.
    """

    _instance: Optional["TimelineManager"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_TIMELINES: int = 256
    MAX_EVENTS_PER_TIMELINE: int = 1000
    MAX_SNAPSHOTS_PER_TIMELINE: int = 100
    MAX_BRANCH_DEPTH: int = 16

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._timelines: Dict[str, Timeline] = {}
        self._snapshots: Dict[str, List[TimelineSnapshot]] = {}
        self._branch_points: Dict[str, BranchPoint] = {}
        self._active_timeline_id: str = ""
        self._total_timelines_created: int = 0
        self._total_events_recorded: int = 0
        self._total_branches_created: int = 0
        self._total_merges_performed: int = 0
        self._total_snapshots_created: int = 0
        self._is_running: bool = False
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "TimelineManager":
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers (operate without acquiring the lock).
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> float:
        return _time_module.time()

    def _require_timeline(self, timeline_id: str) -> Timeline:
        timeline = self._timelines.get(timeline_id)
        if timeline is None:
            raise ValueError(f"Timeline {timeline_id} not found")
        return timeline

    def _require_mutable(self, timeline_id: str) -> Timeline:
        timeline = self._require_timeline(timeline_id)
        if timeline.state not in _MUTABLE_STATES:
            raise ValueError(
                f"Timeline {timeline_id} is {timeline.state.value}; "
                f"cannot mutate"
            )
        return timeline

    def _branch_depth(self, timeline_id: str) -> int:
        """Walk parent chain to compute the branch depth."""
        depth = 0
        current = timeline_id
        seen: set = set()
        while current and current in self._timelines:
            parent = self._timelines[current].parent_timeline_id
            if not parent or parent == current or parent in seen:
                break
            seen.add(current)
            current = parent
            depth += 1
            if depth > self.MAX_BRANCH_DEPTH:
                break
        return depth

    # ------------------------------------------------------------------
    # System lifecycle.
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        """Set up the timeline system. Returns True on first init."""
        with self._lock:
            if self._is_running:
                return False
            self._is_running = True
            return True

    def shutdown(self) -> bool:
        """Clean shutdown: clears the active timeline reference."""
        with self._lock:
            if not self._is_running:
                return False
            self._is_running = False
            self._active_timeline_id = ""
            return True

    # ------------------------------------------------------------------
    # Timeline creation and retrieval.
    # ------------------------------------------------------------------

    def create_timeline(
        self,
        name: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Timeline:
        """Create a new root timeline and return it."""
        with self._lock:
            if len(self._timelines) >= self.MAX_TIMELINES:
                raise ValueError(
                    f"Maximum timeline count reached ({self.MAX_TIMELINES})"
                )

            timeline = Timeline(
                id=uuid.uuid4().hex,
                name=name or "Primary Timeline",
                description=description,
                state=TimelineState.ACTIVE,
                parent_timeline_id="",
                created_at=self._now(),
                updated_at=self._now(),
                metadata=dict(metadata or {}),
            )

            self._timelines[timeline.id] = timeline
            self._snapshots[timeline.id] = []

            if not self._active_timeline_id:
                self._active_timeline_id = timeline.id

            self._total_timelines_created += 1
            return timeline

    def get_timeline(self, timeline_id: str) -> Optional[Timeline]:
        """Return the timeline with the given id, or None."""
        with self._lock:
            return self._timelines.get(timeline_id)

    def list_timelines(self) -> List[Dict[str, Any]]:
        """Return a summary list of all managed timelines."""
        with self._lock:
            result: List[Dict[str, Any]] = []
            for timeline in self._timelines.values():
                entry = timeline.to_dict()
                entry["is_active"] = timeline.id == self._active_timeline_id
                result.append(entry)
            return result

    # ------------------------------------------------------------------
    # Event recording.
    # ------------------------------------------------------------------

    def record_event(
        self,
        timeline_id: str,
        event_type: str,
        description: str = "",
        agent_id: str = "",
        data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> TimelineEvent:
        """Record a new event on the given timeline."""
        with self._lock:
            timeline = self._require_mutable(timeline_id)
            if len(timeline.events) >= self.MAX_EVENTS_PER_TIMELINE:
                raise ValueError(
                    f"Timeline {timeline_id} reached event cap "
                    f"({self.MAX_EVENTS_PER_TIMELINE})"
                )

            event = TimelineEvent(
                id=uuid.uuid4().hex,
                timeline_id=timeline_id,
                event_type=event_type,
                description=description,
                timestamp=self._now(),
                agent_id=agent_id,
                data=dict(data or {}),
                tags=list(tags or []),
            )

            timeline.events.append(event)
            timeline.updated_at = self._now()
            self._total_events_recorded += 1
            return event

    # ------------------------------------------------------------------
    # Branching.
    # ------------------------------------------------------------------

    def create_branch(
        self,
        timeline_id: str,
        branch_name: str = "",
        description: str = "",
    ) -> TimelineBranchResult:
        """Fork a new branch from the current state of a timeline.

        The new branch inherits all events from the source timeline up
        to the branch point, then diverges independently.
        """
        with self._lock:
            source = self._require_timeline(timeline_id)
            if source.state in _TERMINAL_STATES:
                return TimelineBranchResult(
                    success=False,
                    timeline_id=timeline_id,
                    message=f"Cannot branch from {source.state.value} timeline",
                )

            depth = self._branch_depth(timeline_id) + 1
            if depth > self.MAX_BRANCH_DEPTH:
                return TimelineBranchResult(
                    success=False,
                    timeline_id=timeline_id,
                    message=(
                        f"Branch depth {depth} exceeds limit "
                        f"{self.MAX_BRANCH_DEPTH}"
                    ),
                )

            if len(self._timelines) >= self.MAX_TIMELINES:
                return TimelineBranchResult(
                    success=False,
                    timeline_id=timeline_id,
                    message=(
                        f"Maximum timeline count reached "
                        f"({self.MAX_TIMELINES})"
                    ),
                )

            last_event_id = source.events[-1].id if source.events else ""

            branch_point = BranchPoint(
                id=uuid.uuid4().hex,
                timeline_id=timeline_id,
                event_id=last_event_id,
                branch_name=branch_name or f"{source.name} - Branch {depth}",
                description=description or f"Branch from '{source.name}'",
                created_at=self._now(),
                metadata={
                    "source_name": source.name,
                    "branch_depth": depth,
                },
            )

            source.branch_points.append(branch_point)
            source.updated_at = self._now()
            self._branch_points[branch_point.id] = branch_point

            final_name = branch_name or f"{source.name} - Branch {depth}"
            branch = Timeline(
                id=uuid.uuid4().hex,
                name=final_name,
                description=(
                    description
                    or f"Branch from '{source.name}' at event {last_event_id}"
                ),
                state=TimelineState.ACTIVE,
                parent_timeline_id=timeline_id,
                created_at=self._now(),
                updated_at=self._now(),
                metadata={
                    "source_timeline_id": timeline_id,
                    "branch_point_id": branch_point.id,
                },
            )

            # Copy events from source to preserve history up to the
            # branch point. Each event gets a new id so the branch
            # owns its own copies.
            for event in source.events:
                cloned = TimelineEvent(
                    id=uuid.uuid4().hex,
                    timeline_id=branch.id,
                    event_type=event.event_type,
                    description=event.description,
                    timestamp=event.timestamp,
                    agent_id=event.agent_id,
                    data=dict(event.data),
                    tags=list(event.tags),
                )
                branch.events.append(cloned)

            self._timelines[branch.id] = branch
            self._snapshots[branch.id] = []
            self._total_timelines_created += 1
            self._total_branches_created += 1

            return TimelineBranchResult(
                success=True,
                branch_id=branch_point.id,
                timeline_id=branch.id,
                message=f"Branch '{final_name}' created from '{source.name}'",
            )

    # ------------------------------------------------------------------
    # Active timeline switching.
    # ------------------------------------------------------------------

    def switch_timeline(self, timeline_id: str) -> bool:
        """Set the given timeline as the currently active one."""
        with self._lock:
            timeline = self._require_timeline(timeline_id)
            if timeline.state == TimelineState.ARCHIVED:
                return False
            self._active_timeline_id = timeline_id
            timeline.updated_at = self._now()
            return True

    # ------------------------------------------------------------------
    # Merging.
    # ------------------------------------------------------------------

    def merge_timelines(
        self,
        source_id: str,
        target_id: str,
    ) -> TimelineMergeResult:
        """Merge the source timeline into the target timeline.

        Events from the source that are not already present in the
        target are appended. Metadata keys that differ are recorded
        as conflicts. After merging, the source is marked as MERGED.
        """
        with self._lock:
            if source_id == target_id:
                return TimelineMergeResult(
                    success=False,
                    source_timeline_id=source_id,
                    target_timeline_id=target_id,
                    message="Cannot merge a timeline with itself",
                )

            source = self._timelines.get(source_id)
            target = self._timelines.get(target_id)

            if source is None:
                return TimelineMergeResult(
                    success=False,
                    source_timeline_id=source_id,
                    target_timeline_id=target_id,
                    message=f"Source timeline {source_id} not found",
                )
            if target is None:
                return TimelineMergeResult(
                    success=False,
                    source_timeline_id=source_id,
                    target_timeline_id=target_id,
                    message=f"Target timeline {target_id} not found",
                )

            if source.state in _TERMINAL_STATES:
                return TimelineMergeResult(
                    success=False,
                    source_timeline_id=source_id,
                    target_timeline_id=target_id,
                    message=f"Source timeline is {source.state.value}",
                )
            if target.state in _TERMINAL_STATES:
                return TimelineMergeResult(
                    success=False,
                    source_timeline_id=source_id,
                    target_timeline_id=target_id,
                    message=f"Target timeline is {target.state.value}",
                )

            conflicts: List[Dict[str, Any]] = []
            merged_events = 0

            # Deduplicate by event type + description to avoid
            # appending events that represent the same logical
            # occurrence.
            existing_keys = {
                (e.event_type, e.description) for e in target.events
            }
            for event in source.events:
                key = (event.event_type, event.description)
                if key in existing_keys:
                    conflicts.append(
                        {
                            "event_id": event.id,
                            "event_type": event.event_type,
                            "resolution": "skipped_duplicate",
                        }
                    )
                    continue
                cloned = TimelineEvent(
                    id=uuid.uuid4().hex,
                    timeline_id=target_id,
                    event_type=event.event_type,
                    description=event.description,
                    timestamp=event.timestamp,
                    agent_id=event.agent_id,
                    data=dict(event.data),
                    tags=list(event.tags),
                )
                target.events.append(cloned)
                existing_keys.add(key)
                merged_events += 1

            # Merge metadata: conflicting keys are recorded, new keys
            # are added.
            for key, value in source.metadata.items():
                if key in target.metadata and target.metadata[key] != value:
                    conflicts.append(
                        {
                            "key": key,
                            "source_value": value,
                            "target_value": target.metadata[key],
                            "resolution": "preserved_target",
                        }
                    )
                elif key not in target.metadata:
                    target.metadata[key] = value

            source.state = TimelineState.MERGED
            source.metadata["merged_into"] = target_id
            source.updated_at = self._now()
            target.updated_at = self._now()
            self._total_merges_performed += 1

            return TimelineMergeResult(
                success=True,
                source_timeline_id=source_id,
                target_timeline_id=target_id,
                conflicts=conflicts,
                merged_events=merged_events,
                message=(
                    f"Merged {merged_events} events from source into "
                    f"target ({len(conflicts)} conflicts)"
                ),
            )

    # ------------------------------------------------------------------
    # Snapshot management.
    # ------------------------------------------------------------------

    def create_snapshot(
        self,
        timeline_id: str,
        state_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[TimelineSnapshot]:
        """Capture the current state of a timeline as a snapshot.

        The snapshot records the current event index so that the
        timeline can later be restored to this exact point.
        """
        with self._lock:
            timeline = self._require_timeline(timeline_id)
            snapshots = self._snapshots.get(timeline_id, [])
            if len(snapshots) >= self.MAX_SNAPSHOTS_PER_TIMELINE:
                snapshots.pop(0)

            snapshot = TimelineSnapshot(
                id=uuid.uuid4().hex,
                timeline_id=timeline_id,
                event_index=len(timeline.events),
                state_data=dict(state_data or {}),
                timestamp=self._now(),
            )

            snapshots.append(snapshot)
            self._snapshots[timeline_id] = snapshots
            timeline.updated_at = self._now()
            self._total_snapshots_created += 1
            return snapshot

    def restore_snapshot(
        self,
        timeline_id: str,
        snapshot_id: str,
    ) -> bool:
        """Restore a timeline to a previously captured snapshot.

        Events recorded after the snapshot are discarded. Snapshots
        taken after the restored one are also removed.
        """
        with self._lock:
            timeline = self._require_mutable(timeline_id)
            snapshots = self._snapshots.get(timeline_id, [])
            target_snapshot: Optional[TimelineSnapshot] = None
            snapshot_index = -1

            for i, snap in enumerate(snapshots):
                if snap.id == snapshot_id:
                    target_snapshot = snap
                    snapshot_index = i
                    break

            if target_snapshot is None:
                return False

            # Truncate events to the snapshot's event index.
            if target_snapshot.event_index < len(timeline.events):
                timeline.events = timeline.events[
                    : target_snapshot.event_index
                ]

            # Discard snapshots that were taken after the restored one.
            self._snapshots[timeline_id] = snapshots[: snapshot_index + 1]

            timeline.updated_at = self._now()
            return True

    # ------------------------------------------------------------------
    # Read paths.
    # ------------------------------------------------------------------

    def get_timeline_events(
        self,
        timeline_id: str,
        limit: int = 100,
    ) -> List[TimelineEvent]:
        """Return the most recent events for a timeline, up to limit.

        A limit of 0 or negative returns all events.
        """
        with self._lock:
            timeline = self._require_timeline(timeline_id)
            events = timeline.events
            if limit > 0:
                events = events[-limit:]
            return list(events)

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current manager state."""
        with self._lock:
            active_timeline = self._timelines.get(self._active_timeline_id)
            state_counts: Dict[str, int] = {}
            for timeline in self._timelines.values():
                state_counts[timeline.state.value] = (
                    state_counts.get(timeline.state.value, 0) + 1
                )

            total_events = sum(
                len(t.events) for t in self._timelines.values()
            )
            total_snapshots = sum(
                len(s) for s in self._snapshots.values()
            )

            return {
                "is_running": self._is_running,
                "active_timeline_id": self._active_timeline_id,
                "active_timeline_name": (
                    active_timeline.name if active_timeline else ""
                ),
                "total_timelines": len(self._timelines),
                "total_events": total_events,
                "total_snapshots": total_snapshots,
                "timelines_created": self._total_timelines_created,
                "events_recorded": self._total_events_recorded,
                "branches_created": self._total_branches_created,
                "merges_performed": self._total_merges_performed,
                "snapshots_created": self._total_snapshots_created,
                "state_distribution": state_counts,
                "max_timelines": self.MAX_TIMELINES,
                "max_events_per_timeline": self.MAX_EVENTS_PER_TIMELINE,
                "max_snapshots_per_timeline": self.MAX_SNAPSHOTS_PER_TIMELINE,
                "max_branch_depth": self.MAX_BRANCH_DEPTH,
            }


def get_timeline_manager() -> TimelineManager:
    """Return the singleton TimelineManager instance."""
    return TimelineManager.get_instance()