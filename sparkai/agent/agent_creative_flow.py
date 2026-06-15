"""
SparkLabs Agent - Creative Flow Orchestrator

End-to-end creative pipeline manager for the AI-native game engine.
Connects game vision, design decisions, content generation, and game
assembly into a seamless creative pipeline with structured stage tracking
and artifact management.

Architecture:
  CreativeFlowOrchestrator (singleton)
    |-- CreativeFlow (pipeline definition with stage progression)
    |-- FlowArtifact (versioned content artifacts per stage)
    |-- FlowStage enum (IDEATION → DESIGN → PROTOTYPE → PRODUCTION → POLISH → DEPLOY)
    |-- FlowState enum (PENDING, ACTIVE, COMPLETED, BLOCKED, FAILED)

Flow Stages:
  IDEATION - generate and refine the core game concept
  DESIGN - create detailed game design specifications
  PROTOTYPE - build a playable proof-of-concept
  PRODUCTION - implement the full game content
  POLISH - refine, balance, and optimize
  DEPLOY - package and prepare for distribution
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FlowStage(Enum):
    """Stages in the creative flow pipeline."""
    IDEATION = "ideation"
    DESIGN = "design"
    PROTOTYPE = "prototype"
    PRODUCTION = "production"
    POLISH = "polish"
    DEPLOY = "deploy"


class FlowState(Enum):
    """Execution states for flow stages and flows."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Stage Order and Descriptions
# ---------------------------------------------------------------------------

_STAGE_ORDER: List[FlowStage] = [
    FlowStage.IDEATION,
    FlowStage.DESIGN,
    FlowStage.PROTOTYPE,
    FlowStage.PRODUCTION,
    FlowStage.POLISH,
    FlowStage.DEPLOY,
]

_STAGE_DESCRIPTIONS: Dict[FlowStage, str] = {
    FlowStage.IDEATION: "Generate and refine the core game concept",
    FlowStage.DESIGN: "Create detailed game design specifications",
    FlowStage.PROTOTYPE: "Build a playable proof-of-concept",
    FlowStage.PRODUCTION: "Implement the full game content",
    FlowStage.POLISH: "Refine, balance, and optimize",
    FlowStage.DEPLOY: "Package and prepare for distribution",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CreativeFlow:
    """A creative flow pipeline instance with stage progression tracking.

    Represents one complete creative pipeline from initial ideation
    through to deployment. Each flow maintains its current stage,
    state tracking per stage, and accumulated context metadata.
    """
    flow_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    stages: List[FlowStage] = field(default_factory=lambda: list(_STAGE_ORDER))
    current_stage: FlowStage = FlowStage.IDEATION
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Internal tracking
    _stage_states: Dict[str, FlowState] = field(default_factory=dict)
    _completed_at: Optional[float] = None
    _blocked_reason: str = ""
    _artifact_count: int = 0

    def __post_init__(self) -> None:
        if not self._stage_states:
            for s in self.stages:
                self._stage_states[s.value] = FlowState.PENDING
            first = self.stages[0] if self.stages else self.current_stage
            self._stage_states[first.value] = FlowState.ACTIVE
            self.current_stage = first

    def get_stage_state(self, stage: FlowStage) -> FlowState:
        """Get the state of a specific stage within this flow."""
        return self._stage_states.get(stage.value, FlowState.PENDING)

    def get_progress(self) -> float:
        """Return the fraction of completed stages (0.0 to 1.0)."""
        if not self.stages:
            return 0.0
        completed = sum(
            1 for s in self.stages
            if self._stage_states.get(s.value) == FlowState.COMPLETED
        )
        return completed / len(self.stages)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "name": self.name,
            "stages": [s.value for s in self.stages],
            "current_stage": self.current_stage.value,
            "stage_states": {k: v.value for k, v in self._stage_states.items()},
            "progress": self.get_progress(),
            "created_at": self.created_at,
            "completed_at": self._completed_at,
            "blocked_reason": self._blocked_reason,
            "artifact_count": self._artifact_count,
            "metadata": dict(self.metadata),
        }


@dataclass
class FlowArtifact:
    """A versioned content artifact produced at a specific flow stage.

    Each artifact is associated with a flow and stage, carrying typed
    content data and a version number for iteration tracking.
    """
    artifact_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    flow_id: str = ""
    stage: FlowStage = FlowStage.IDEATION
    content_type: str = "generic"
    data: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "flow_id": self.flow_id,
            "stage": self.stage.value,
            "content_type": self.content_type,
            "version": self.version,
            "created_at": self.created_at,
            "data_keys": list(self.data.keys()),
        }


# ---------------------------------------------------------------------------
# CreativeFlowOrchestrator (Singleton)
# ---------------------------------------------------------------------------


class CreativeFlowOrchestrator:
    """End-to-end creative pipeline orchestrator for game development.

    Manages the complete creative flow lifecycle from ideation through
    deployment. Tracks stage progression, collects versioned artifacts,
    and provides comprehensive pipeline statistics.

    Usage:
        orchestrator = get_creative_flow()
        flow = orchestrator.create_flow("My RPG", metadata={"genre": "fantasy"})
        orchestrator.advance_stage(flow.flow_id)
        orchestrator.add_artifact(flow.flow_id, FlowStage.DESIGN, "design_doc", {...})
        stats = orchestrator.get_stats()
    """

    _instance: Optional[CreativeFlowOrchestrator] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> CreativeFlowOrchestrator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> CreativeFlowOrchestrator:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # Primary storage
        self._flows: Dict[str, CreativeFlow] = {}
        self._artifacts: Dict[str, FlowArtifact] = {}

        # Statistics
        self._total_flows_created: int = 0
        self._total_artifacts_created: int = 0
        self._total_stage_advances: int = 0
        self._completed_flows: int = 0
        self._failed_flows: int = 0
        self._blocked_flows: int = 0

        # Recent activity for diagnostics
        self._recent_events: Deque[Dict[str, Any]] = deque(maxlen=100)

    def _record_event(self, event_type: str, flow_id: str, details: str = "") -> None:
        self._recent_events.append({
            "timestamp": time.time(),
            "event_type": event_type,
            "flow_id": flow_id,
            "details": details,
        })

    # --- Flow Management ---

    def create_flow(
        self,
        name: str,
        stages: Optional[List[FlowStage]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CreativeFlow:
        """Create a new creative flow with the given name and optional stage list.

        Args:
            name: Display name for this flow.
            stages: Custom stage ordering (defaults to standard 6-stage pipeline).
            metadata: Optional key-value metadata for context tracking.

        Returns:
            The newly created CreativeFlow instance.
        """
        with self._lock:
            flow = CreativeFlow(
                name=name,
                stages=list(stages) if stages else list(_STAGE_ORDER),
                metadata=dict(metadata) if metadata else {},
            )
            self._flows[flow.flow_id] = flow
            self._total_flows_created += 1
            self._record_event("flow_created", flow.flow_id, f"name={name}")
            return flow

    def advance_stage(self, flow_id: str) -> FlowStage:
        """Move a flow to the next stage in its pipeline.

        Marks the current stage as completed and activates the next stage.
        If the current stage is the last, marks the entire flow as completed.

        Args:
            flow_id: The flow to advance.

        Returns:
            The new current stage after advancing.

        Raises:
            ValueError: If the flow_id is not found.
        """
        with self._lock:
            flow = self._flows.get(flow_id)
            if flow is None:
                raise ValueError(f"Flow not found: {flow_id}")

            current = flow.current_stage
            flow._stage_states[current.value] = FlowState.COMPLETED

            current_idx = flow.stages.index(current)
            next_idx = current_idx + 1

            if next_idx >= len(flow.stages):
                flow._completed_at = time.time()
                self._completed_flows += 1
                self._record_event("flow_completed", flow_id)
                return current

            next_stage = flow.stages[next_idx]
            flow.current_stage = next_stage
            flow._stage_states[next_stage.value] = FlowState.ACTIVE
            self._total_stage_advances += 1
            self._record_event(
                "stage_advanced", flow_id,
                f"{current.value} -> {next_stage.value}"
            )
            return next_stage

    def set_stage_state(
        self,
        flow_id: str,
        stage: FlowStage,
        state: FlowState,
        reason: str = "",
    ) -> None:
        """Explicitly set the state of a stage within a flow.

        Useful for marking stages as BLOCKED or FAILED with a reason.

        Args:
            flow_id: The flow to update.
            stage: The stage to set state for.
            state: The new state.
            reason: Optional explanation for BLOCKED or FAILED states.

        Raises:
            ValueError: If the flow_id is not found.
        """
        with self._lock:
            flow = self._flows.get(flow_id)
            if flow is None:
                raise ValueError(f"Flow not found: {flow_id}")

            flow._stage_states[stage.value] = state
            if state == FlowState.BLOCKED:
                flow._blocked_reason = reason
                self._blocked_flows += 1
                self._record_event("stage_blocked", flow_id, reason)
            elif state == FlowState.FAILED:
                self._failed_flows += 1
                flow._blocked_reason = reason
                self._record_event("stage_failed", flow_id, reason)

    # --- Artifact Management ---

    def add_artifact(
        self,
        flow_id: str,
        stage: FlowStage,
        content_type: str,
        data: Dict[str, Any],
    ) -> FlowArtifact:
        """Create and attach a versioned artifact to a flow at a specific stage.

        If an artifact already exists for the same flow, stage, and content type,
        the version is auto-incremented.

        Args:
            flow_id: The flow to attach the artifact to.
            stage: The pipeline stage this artifact belongs to.
            content_type: Category label (e.g., "design_doc", "level_map", "asset_bundle").
            data: Arbitrary key-value content data.

        Returns:
            The created FlowArtifact.

        Raises:
            ValueError: If the flow_id is not found.
        """
        with self._lock:
            flow = self._flows.get(flow_id)
            if flow is None:
                raise ValueError(f"Flow not found: {flow_id}")

            # Auto-increment version if same type exists for this stage
            existing = [
                a for a in self._artifacts.values()
                if a.flow_id == flow_id
                and a.stage == stage
                and a.content_type == content_type
            ]
            version = max((a.version for a in existing), default=0) + 1

            artifact = FlowArtifact(
                flow_id=flow_id,
                stage=stage,
                content_type=content_type,
                data=dict(data),
                version=version,
            )
            self._artifacts[artifact.artifact_id] = artifact
            flow._artifact_count += 1
            self._total_artifacts_created += 1
            self._record_event(
                "artifact_added", flow_id,
                f"stage={stage.value}, type={content_type}, v{version}"
            )
            return artifact

    def get_artifacts(
        self,
        flow_id: str,
        stage: Optional[FlowStage] = None,
        content_type: Optional[str] = None,
    ) -> List[FlowArtifact]:
        """Retrieve artifacts for a flow, optionally filtered by stage or content type.

        Args:
            flow_id: The flow to query artifacts for.
            stage: Optional stage filter.
            content_type: Optional content type filter.

        Returns:
            List of matching FlowArtifacts, ordered by creation time.
        """
        results = [
            a for a in self._artifacts.values() if a.flow_id == flow_id
        ]
        if stage is not None:
            results = [a for a in results if a.stage == stage]
        if content_type is not None:
            results = [a for a in results if a.content_type == content_type]
        return sorted(results, key=lambda a: a.created_at)

    def get_latest_artifact(
        self,
        flow_id: str,
        stage: FlowStage,
        content_type: str,
    ) -> Optional[FlowArtifact]:
        """Get the highest-version artifact for a flow, stage, and content type.

        Args:
            flow_id: The flow to query.
            stage: The stage filter.
            content_type: The content type filter.

        Returns:
            The latest FlowArtifact or None if none found.
        """
        candidates = [
            a for a in self._artifacts.values()
            if a.flow_id == flow_id
            and a.stage == stage
            and a.content_type == content_type
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda a: a.version)

    # --- Query Operations ---

    def get_flow(self, flow_id: str) -> Optional[CreativeFlow]:
        """Retrieve a flow by its ID.

        Args:
            flow_id: The flow identifier.

        Returns:
            The CreativeFlow if found, otherwise None.
        """
        return self._flows.get(flow_id)

    def list_flows(
        self,
        stage: Optional[FlowStage] = None,
        state: Optional[FlowState] = None,
    ) -> List[CreativeFlow]:
        """List all flows, optionally filtered by current stage or a stage state.

        Args:
            stage: Filter to flows currently at this stage.
            state: Filter to flows where the current stage has this state.

        Returns:
            List of matching CreativeFlows ordered by creation time (newest first).
        """
        results = list(self._flows.values())
        if stage is not None:
            results = [f for f in results if f.current_stage == stage]
        if state is not None:
            results = [
                f for f in results
                if f._stage_states.get(f.current_stage.value) == state
            ]
        return sorted(results, key=lambda f: f.created_at, reverse=True)

    def list_artifacts(
        self,
        flow_id: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> List[FlowArtifact]:
        """List all artifacts, optionally filtered by flow or content type.

        Args:
            flow_id: Optional flow filter.
            content_type: Optional content type filter.

        Returns:
            List of FlowArtifacts ordered by creation time (newest first).
        """
        results = list(self._artifacts.values())
        if flow_id is not None:
            results = [a for a in results if a.flow_id == flow_id]
        if content_type is not None:
            results = [a for a in results if a.content_type == content_type]
        return sorted(results, key=lambda a: a.created_at, reverse=True)

    # --- Statistics ---

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive statistics for the orchestrator.

        Includes flow counts, artifact counts, stage distribution,
        completion rates, and recent activity summary.

        Returns:
            Dictionary with statistical summaries.
        """
        with self._lock:
            # Stage distribution
            stage_counts: Dict[str, int] = {}
            for f in self._flows.values():
                key = f.current_stage.value
                stage_counts[key] = stage_counts.get(key, 0) + 1

            # Artifact type distribution
            artifact_type_counts: Dict[str, int] = {}
            for a in self._artifacts.values():
                artifact_type_counts[a.content_type] = (
                    artifact_type_counts.get(a.content_type, 0) + 1
                )

            # Content type breakdown per stage
            content_by_stage: Dict[str, Dict[str, int]] = {}
            for a in self._artifacts.values():
                stage_key = a.stage.value
                if stage_key not in content_by_stage:
                    content_by_stage[stage_key] = {}
                ct = a.content_type
                content_by_stage[stage_key][ct] = (
                    content_by_stage[stage_key].get(ct, 0) + 1
                )

            total = max(len(self._flows), 1)
            return {
                "total_flows": len(self._flows),
                "total_flows_created": self._total_flows_created,
                "total_artifacts": len(self._artifacts),
                "total_artifacts_created": self._total_artifacts_created,
                "total_stage_advances": self._total_stage_advances,
                "completed_flows": self._completed_flows,
                "failed_flows": self._failed_flows,
                "blocked_flows": self._blocked_flows,
                "active_flows": sum(
                    1 for f in self._flows.values()
                    if f._stage_states.get(f.current_stage.value) == FlowState.ACTIVE
                ),
                "completion_rate": round(self._completed_flows / total, 4),
                "avg_artifacts_per_flow": round(len(self._artifacts) / total, 2),
                "avg_progress": round(
                    sum(f.get_progress() for f in self._flows.values()) / total, 4
                ),
                "stage_distribution": stage_counts,
                "artifact_type_distribution": artifact_type_counts,
                "content_by_stage": content_by_stage,
                "recent_events_count": len(self._recent_events),
            }

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent orchestrator events for diagnostics.

        Args:
            limit: Maximum number of events to return.

        Returns:
            List of event dictionaries, most recent first.
        """
        events = list(self._recent_events)
        return list(reversed(events))[:limit]

    # --- Export ---

    def export_flow(self, flow_id: str) -> Dict[str, Any]:
        """Export a complete flow with all its artifacts as a JSON-serializable dict.

        Args:
            flow_id: The flow to export.

        Returns:
            Dictionary with flow data and its artifacts.

        Raises:
            ValueError: If the flow_id is not found.
        """
        flow = self._flows.get(flow_id)
        if flow is None:
            raise ValueError(f"Flow not found: {flow_id}")

        artifacts = [
            a.to_dict()
            for a in self._artifacts.values()
            if a.flow_id == flow_id
        ]
        return {
            "flow": flow.to_dict(),
            "artifacts": artifacts,
            "stage_descriptions": {
                s.value: _STAGE_DESCRIPTIONS.get(s, "")
                for s in flow.stages
            },
        }

    def export_flow_json(self, flow_id: str, indent: int = 2) -> str:
        """Export a flow as a formatted JSON string.

        Args:
            flow_id: The flow to export.
            indent: JSON indentation level.

        Returns:
            JSON string of the flow export.

        Raises:
            ValueError: If the flow_id is not found.
        """
        return json.dumps(self.export_flow(flow_id), indent=indent, default=str)

    def delete_flow(self, flow_id: str) -> bool:
        """Remove a flow and all its artifacts.

        Args:
            flow_id: The flow to delete.

        Returns:
            True if the flow was found and deleted, False otherwise.
        """
        with self._lock:
            if flow_id not in self._flows:
                return False
            del self._flows[flow_id]
            artifact_ids = [
                aid for aid, a in self._artifacts.items()
                if a.flow_id == flow_id
            ]
            for aid in artifact_ids:
                del self._artifacts[aid]
            self._record_event("flow_deleted", flow_id)
            return True


# ---------------------------------------------------------------------------
# Singleton Accessor
# ---------------------------------------------------------------------------


def get_creative_flow() -> CreativeFlowOrchestrator:
    """Get the global CreativeFlowOrchestrator singleton instance."""
    return CreativeFlowOrchestrator.get_instance()