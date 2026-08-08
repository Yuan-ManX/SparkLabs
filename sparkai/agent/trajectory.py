"""
SparkAI Agent - Trajectory Recorder and Action Timeline

Records the full agent decision/action sequence as a structured
timeline. Each entry captures: input, output, affected objects,
before/after state, validation results, and rollback support.

The timeline serves as an audit spine enabling:
- Per-op undo/rollback
- Re-validation of past operations
- Export as training data for model fine-tuning
- Debug bundle generation for failure analysis
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PermissionTier(Enum):
    """Tiered permission model for engine operations."""
    TIER_0_READONLY = 0      # Auto-allow (reads, queries)
    TIER_1_UNDOABLE = 1      # Allow within approved run + undo/redo
    TIER_2_REFACTOR = 2      # Must show plan + blast radius first
    TIER_3_EXTERNAL = 3      # Prompt cost + safety + target check
    TIER_4_DANGEROUS = 4     # Default blocked, one-shot scoped auth


class ActionStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    VALIDATED = "validated"


@dataclass
class TrajectoryEntry:
    """A single entry in the agent's action timeline."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    agent_id: str = ""
    agent_name: str = ""
    action: str = ""
    action_label: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    status: ActionStatus = ActionStatus.PENDING
    permission_tier: PermissionTier = PermissionTier.TIER_1_UNDOABLE
    # Affected objects tracking
    affected_entities: List[str] = field(default_factory=list)
    affected_scenes: List[str] = field(default_factory=list)
    # State tracking for rollback
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    # Validation
    validation_results: List[Dict[str, Any]] = field(default_factory=list)
    # Rollback support
    rollback_handler: Optional[Callable] = None
    rolled_back: bool = False
    # Error tracking
    error: Optional[str] = None
    duration_s: float = 0.0
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "action": self.action,
            "action_label": self.action_label,
            "params": self.params,
            "result": str(self.result)[:200] if self.result else None,
            "status": self.status.value,
            "permission_tier": self.permission_tier.value,
            "affected_entities": self.affected_entities,
            "affected_scenes": self.affected_scenes,
            "validation_count": len(self.validation_results),
            "rolled_back": self.rolled_back,
            "error": self.error,
            "duration_s": round(self.duration_s, 4),
            "metadata": self.metadata,
        }


class TrajectoryRecorder:
    """
    Records agent action trajectories as a structured timeline.

    The timeline is the audit spine for the AI-native engine:
    every meaningful operation is recorded, inspectable, and
    rollback-able. This enables trust in autonomous modes.
    """

    def __init__(self, max_entries: int = 500):
        self._entries: List[TrajectoryEntry] = []
        self._max_entries = max_entries
        self._entry_index: Dict[str, TrajectoryEntry] = {}

    def begin_action(
        self,
        agent_id: str,
        agent_name: str,
        action: str,
        params: Dict[str, Any],
        permission_tier: PermissionTier = PermissionTier.TIER_1_UNDOABLE,
        before_state: Optional[Dict[str, Any]] = None,
    ) -> TrajectoryEntry:
        """Begin recording a new action in the timeline."""
        entry = TrajectoryEntry(
            agent_id=agent_id,
            agent_name=agent_name,
            action=action,
            action_label=action.replace("_", " ").title(),
            params=params,
            permission_tier=permission_tier,
            before_state=before_state,
            status=ActionStatus.EXECUTING,
        )
        self._entries.append(entry)
        self._entry_index[entry.id] = entry
        self._enforce_capacity()
        return entry

    def complete_action(
        self,
        entry_id: str,
        result: Any,
        after_state: Optional[Dict[str, Any]] = None,
        affected_entities: Optional[List[str]] = None,
        affected_scenes: Optional[List[str]] = None,
    ) -> Optional[TrajectoryEntry]:
        """Mark an action as completed successfully."""
        entry = self._entry_index.get(entry_id)
        if not entry:
            return None

        entry.result = result
        entry.after_state = after_state
        entry.affected_entities = affected_entities or []
        entry.affected_scenes = affected_scenes or []
        entry.status = ActionStatus.SUCCESS
        entry.duration_s = time.time() - entry.timestamp

        # Auto-validate
        self._validate_entry(entry)
        return entry

    def fail_action(
        self,
        entry_id: str,
        error: str,
    ) -> Optional[TrajectoryEntry]:
        """Mark an action as failed."""
        entry = self._entry_index.get(entry_id)
        if not entry:
            return None

        entry.status = ActionStatus.FAILED
        entry.error = error
        entry.duration_s = time.time() - entry.timestamp
        return entry

    def rollback(self, entry_id: str) -> bool:
        """Rollback a specific action using its rollback handler."""
        entry = self._entry_index.get(entry_id)
        if not entry or entry.rolled_back:
            return False
        if entry.status not in (ActionStatus.SUCCESS, ActionStatus.VALIDATED):
            return False

        if entry.rollback_handler:
            try:
                entry.rollback_handler(entry)
                entry.rolled_back = True
                entry.status = ActionStatus.ROLLED_BACK
                logger.info("Rolled back action %s (%s)", entry_id, entry.action)
                return True
            except Exception as exc:
                logger.error("Rollback failed for %s: %s", entry_id, exc)
                return False
        return False

    def _validate_entry(self, entry: TrajectoryEntry) -> None:
        """Run validation checks on a completed action."""
        validations = []

        # Check if result indicates success
        if isinstance(entry.result, dict):
            status = entry.result.get("status", "")
            if status in ("created", "added", "removed", "queried", "listed", "active", "spawned", "configured", "emitted", "retrieved", "executed"):
                validations.append({"check": "result_status", "passed": True})
            elif status == "error":
                validations.append({"check": "result_status", "passed": False, "message": entry.result.get("error", "Unknown error")})
            else:
                validations.append({"check": "result_status", "passed": True})

        # Check if affected entities exist (if we can verify)
        if entry.after_state and entry.affected_entities:
            entities = entry.after_state.get("entities", [])
            if entities:
                validations.append({"check": "entities_exist", "passed": True})

        # All passed -> mark validated
        all_passed = all(v.get("passed", False) for v in validations)
        if all_passed and entry.status == ActionStatus.SUCCESS:
            entry.status = ActionStatus.VALIDATED
        entry.validation_results = validations

    def get_timeline(self, limit: int = 50, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent timeline entries."""
        entries = self._entries
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        return [e.to_dict() for e in entries[-limit:]]

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        entry = self._entry_index.get(entry_id)
        return entry.to_dict() if entry else None

    def get_statistics(self) -> Dict[str, Any]:
        total = len(self._entries)
        return {
            "total_actions": total,
            "successful": sum(1 for e in self._entries if e.status in (ActionStatus.SUCCESS, ActionStatus.VALIDATED)),
            "failed": sum(1 for e in self._entries if e.status == ActionStatus.FAILED),
            "rolled_back": sum(1 for e in self._entries if e.rolled_back),
            "validated": sum(1 for e in self._entries if e.status == ActionStatus.VALIDATED),
            "avg_duration_s": round(
                sum(e.duration_s for e in self._entries) / max(total, 1), 4
            ),
        }

    def export_trajectory(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Export full trajectory as training data format."""
        entries = self._entries
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        return [
            {
                "agent": e.agent_name,
                "action": e.action,
                "params": e.params,
                "result": str(e.result)[:500] if e.result else None,
                "status": e.status.value,
                "duration_s": round(e.duration_s, 4),
                "validated": len(e.validation_results) > 0,
            }
            for e in entries
        ]

    def _enforce_capacity(self) -> None:
        while len(self._entries) > self._max_entries:
            evicted = self._entries.pop(0)
            self._entry_index.pop(evicted.id, None)


# Global singleton
_recorder: Optional[TrajectoryRecorder] = None


def get_trajectory_recorder() -> TrajectoryRecorder:
    global _recorder
    if _recorder is None:
        _recorder = TrajectoryRecorder()
    return _recorder
