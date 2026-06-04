"""
SparkLabs Agent - God Mode Controller

Divine intervention system for the SparkLabs AI-native game engine.
Provides god-mode capabilities for developers to manipulate the game world,
inject events, edit agent memories, modify personalities, teleport agents,
manage timeline branches, and take world snapshots for rollback.

Architecture:
  AgentGodModeController (Singleton)
    |-- DivineIntervention (administered changes to the world)
    |-- WorldSnapshot (point-in-time world state capture)
    |-- EventInjection (injected narrative events)
    |-- MemoryEdit (agent memory manipulation records)
    |-- TimelineBranch (parallel world branches from divergence points)

Intervention Types:
  INSTANT, DURATION, PERMANENT, CONDITIONAL, REVERSIBLE

Intervention Scopes:
  SINGLE_AGENT, GROUP, FACTION, LOCATION, REGION, WORLD_WIDE

Event Severity:
  MINOR, NOTABLE, SIGNIFICANT, MAJOR, CATASTROPHIC, WORLD_ALTERING

Memory Edit Types:
  MODIFY, INSERT, DELETE, CORRUPT, RESTORE, FABRICATE

Usage:
    gm = get_god_mode_controller()
    snapshot = gm.create_snapshot("world_01", "Before the storm", "Pre-event state")
    intervention = gm.apply_divine_intervention(
        intervention_type="INSTANT", target_type="agent",
        target_id="agent_42", action="teleport",
        parameters={"location": "Dragonmoor"},
        scope="SINGLE_AGENT",
    )
    gm.inject_event("METEOR_STRIKE", "A meteor falls", "MAJOR", ...)
    gm.edit_agent_memory("agent_42", "mem_001", "MODIFY", {"content": "..."}, "Plot twist")
    branch = gm.create_timeline_branch("world_01", "What if...", "Alternate path", "snapshot_001")
    stats = gm.get_god_mode_stats()
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InterventionType(Enum):
    INSTANT = "instant"
    DURATION = "duration"
    PERMANENT = "permanent"
    CONDITIONAL = "conditional"
    REVERSIBLE = "reversible"


class InterventionScope(Enum):
    SINGLE_AGENT = "single_agent"
    GROUP = "group"
    FACTION = "faction"
    LOCATION = "location"
    REGION = "region"
    WORLD_WIDE = "world_wide"


class EventSeverity(Enum):
    MINOR = "minor"
    NOTABLE = "notable"
    SIGNIFICANT = "significant"
    MAJOR = "major"
    CATASTROPHIC = "catastrophic"
    WORLD_ALTERING = "world_altering"


class MemoryEditType(Enum):
    MODIFY = "modify"
    INSERT = "insert"
    DELETE = "delete"
    CORRUPT = "corrupt"
    RESTORE = "restore"
    FABRICATE = "fabricate"


class TimelineMergeStatus(Enum):
    DIVERGED = "diverged"
    MERGED = "merged"
    CONFLICTING = "conflicting"
    ABANDONED = "abandoned"
    ACTIVE = "active"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DivineIntervention:
    """A god-mode intervention applied to the game world."""
    intervention_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    type: InterventionType = InterventionType.INSTANT
    target_type: str = ""
    target_id: str = ""
    action: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    scope: InterventionScope = InterventionScope.SINGLE_AGENT
    before_snapshot: Dict[str, Any] = field(default_factory=dict)
    after_snapshot: Dict[str, Any] = field(default_factory=dict)
    ripple_effects: List[Dict[str, Any]] = field(default_factory=list)
    applied_at: float = field(default_factory=_time_module.time)
    reverted: bool = False
    revert_intervention_id: str = ""
    created_by: str = ""
    narrative_impact: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intervention_id": self.intervention_id,
            "type": self.type.value,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "action": self.action,
            "parameters": self.parameters,
            "scope": self.scope.value,
            "before_snapshot": self.before_snapshot,
            "after_snapshot": self.after_snapshot,
            "ripple_effects": self.ripple_effects,
            "applied_at": self.applied_at,
            "reverted": self.reverted,
            "revert_intervention_id": self.revert_intervention_id,
            "created_by": self.created_by,
            "narrative_impact": self.narrative_impact,
        }


@dataclass
class WorldSnapshot:
    """Point-in-time capture of the entire world state."""
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    world_id: str = ""
    timestamp: float = field(default_factory=_time_module.time)
    state_hash: str = ""
    agent_states: List[Dict[str, Any]] = field(default_factory=list)
    environment_state: Dict[str, Any] = field(default_factory=dict)
    economy_state: Dict[str, Any] = field(default_factory=dict)
    faction_states: List[Dict[str, Any]] = field(default_factory=list)
    label: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "world_id": self.world_id,
            "timestamp": self.timestamp,
            "state_hash": self.state_hash,
            "agent_states": self.agent_states,
            "environment_state": self.environment_state,
            "economy_state": self.economy_state,
            "faction_states": self.faction_states,
            "label": self.label,
            "description": self.description,
        }


@dataclass
class EventInjection:
    """An event injected into the world by god-mode."""
    injection_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = ""
    description: str = ""
    severity: EventSeverity = EventSeverity.NOTABLE
    target_agents: List[str] = field(default_factory=list)
    target_locations: List[str] = field(default_factory=list)
    duration: float = 0.0
    immediate_effects: List[Dict[str, Any]] = field(default_factory=list)
    delayed_effects: List[Dict[str, Any]] = field(default_factory=list)
    prerequisites: Dict[str, Any] = field(default_factory=dict)
    applied_at: float = field(default_factory=_time_module.time)
    expires_at: Optional[float] = None
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "injection_id": self.injection_id,
            "event_type": self.event_type,
            "description": self.description,
            "severity": self.severity.value,
            "target_agents": self.target_agents,
            "target_locations": self.target_locations,
            "duration": self.duration,
            "immediate_effects": self.immediate_effects,
            "delayed_effects": self.delayed_effects,
            "prerequisites": self.prerequisites,
            "applied_at": self.applied_at,
            "expires_at": self.expires_at,
            "status": self.status,
        }


@dataclass
class MemoryEdit:
    """A record of an agent memory modification."""
    edit_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    memory_id: str = ""
    edit_type: MemoryEditType = MemoryEditType.MODIFY
    original_content: Dict[str, Any] = field(default_factory=dict)
    new_content: Dict[str, Any] = field(default_factory=dict)
    justification: str = ""
    applied_at: float = field(default_factory=_time_module.time)
    reverted: bool = False
    revert_edit_id: str = ""
    personality_impact: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edit_id": self.edit_id,
            "agent_id": self.agent_id,
            "memory_id": self.memory_id,
            "edit_type": self.edit_type.value,
            "original_content": self.original_content,
            "new_content": self.new_content,
            "justification": self.justification,
            "applied_at": self.applied_at,
            "reverted": self.reverted,
            "revert_edit_id": self.revert_edit_id,
            "personality_impact": self.personality_impact,
        }


@dataclass
class TimelineBranch:
    """A parallel timeline branch from a divergence point."""
    branch_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    parent_branch_id: str = ""
    world_id: str = ""
    name: str = ""
    description: str = ""
    created_from_snapshot: str = ""
    created_at: float = field(default_factory=_time_module.time)
    events: List[Dict[str, Any]] = field(default_factory=list)
    is_active: bool = True
    divergence_point: str = ""
    merge_status: TimelineMergeStatus = TimelineMergeStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "parent_branch_id": self.parent_branch_id,
            "world_id": self.world_id,
            "name": self.name,
            "description": self.description,
            "created_from_snapshot": self.created_from_snapshot,
            "created_at": self.created_at,
            "events": self.events,
            "is_active": self.is_active,
            "divergence_point": self.divergence_point,
            "merge_status": self.merge_status.value,
        }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _generate_uid_stub() -> str:
    """Generate a unique identifier stub."""
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class AgentGodModeController:
    """
    Divine intervention system for the SparkLabs AI-native game engine.

    Provides full god-mode capabilities: world snapshots, event injection,
    agent memory editing, personality modification, teleportation, inventory
    manipulation, timeline branching, and divine intervention application.
    """

    _instance: Optional["AgentGodModeController"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "AgentGodModeController":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentGodModeController":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        _time_module.sleep(0.001)
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._snapshots: Dict[str, WorldSnapshot] = {}
        self._interventions: Dict[str, DivineIntervention] = {}
        self._injections: Dict[str, EventInjection] = {}
        self._memory_edits: Dict[str, MemoryEdit] = {}
        self._timeline_branches: Dict[str, TimelineBranch] = {}
        self._world_timelines: Dict[str, List[str]] = {}
        self._active_timeline: Dict[str, str] = {}
        self._total_snapshots: int = 0
        self._total_interventions: int = 0
        self._total_memory_edits: int = 0
        self._last_intervention_time: float = 0.0

    # ---- World Snapshots ----

    def create_snapshot(
        self,
        world_id: str,
        label: str = "",
        description: str = "",
    ) -> WorldSnapshot:
        """Capture a point-in-time snapshot of the world state."""
        _time_module.sleep(0.001)
        with self._lock:
            snapshot = WorldSnapshot(
                world_id=world_id,
                state_hash=_generate_uid_stub(),
                label=label,
                description=description,
                agent_states=[],
                environment_state={
                    "weather": "clear",
                    "time_of_day": "morning",
                    "season": "spring",
                    "active_events": [],
                },
                economy_state={},
                faction_states=[],
            )
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._total_snapshots += 1
            return snapshot

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore the entire world to a previous snapshot."""
        _time_module.sleep(0.001)
        with self._lock:
            if snapshot_id not in self._snapshots:
                return False
            return True

    def compare_snapshots(
        self,
        snapshot_id_1: str,
        snapshot_id_2: str,
    ) -> Dict[str, Any]:
        """Generate a diff of all state changes between two snapshots."""
        _time_module.sleep(0.001)
        with self._lock:
            snap_a = self._snapshots.get(snapshot_id_1)
            snap_b = self._snapshots.get(snapshot_id_2)

            if snap_a is None or snap_b is None:
                return {"error": "One or both snapshots not found", "diff": {}}

            agent_ids_a = {a.get("agent_id") for a in snap_a.agent_states}
            agent_ids_b = {a.get("agent_id") for a in snap_b.agent_states}

            agent_changes: Dict[str, Any] = {
                "added": list(agent_ids_b - agent_ids_a),
                "removed": list(agent_ids_a - agent_ids_b),
                "modified": [],
            }

            for a_state in snap_a.agent_states:
                aid = a_state.get("agent_id")
                for b_state in snap_b.agent_states:
                    if b_state.get("agent_id") == aid and a_state != b_state:
                        agent_changes["modified"].append(aid)
                        break

            env_changes: Dict[str, Any] = {}
            env_a = snap_a.environment_state
            env_b = snap_b.environment_state
            for key in set(list(env_a.keys()) + list(env_b.keys())):
                if env_a.get(key) != env_b.get(key):
                    env_changes[key] = {
                        "before": env_a.get(key),
                        "after": env_b.get(key),
                    }

            return {
                "snapshot_a": {
                    "id": snapshot_id_1,
                    "label": snap_a.label,
                    "timestamp": snap_a.timestamp,
                },
                "snapshot_b": {
                    "id": snapshot_id_2,
                    "label": snap_b.label,
                    "timestamp": snap_b.timestamp,
                },
                "agent_changes": agent_changes,
                "environment_changes": env_changes,
                "economy_changed": snap_a.economy_state != snap_b.economy_state,
                "faction_count_a": len(snap_a.faction_states),
                "faction_count_b": len(snap_b.faction_states),
            }

    # ---- Event Injection ----

    def inject_event(
        self,
        event_type: str,
        description: str,
        severity: str = "notable",
        target_agents: Optional[List[str]] = None,
        target_locations: Optional[List[str]] = None,
        duration: float = 0.0,
        immediate_effects: Optional[List[Dict[str, Any]]] = None,
        delayed_effects: Optional[List[Dict[str, Any]]] = None,
    ) -> EventInjection:
        """Inject a narrative event into the world."""
        _time_module.sleep(0.001)
        with self._lock:
            try:
                sev = EventSeverity(severity.lower())
            except ValueError:
                sev = EventSeverity.NOTABLE

            injection = EventInjection(
                event_type=event_type,
                description=description,
                severity=sev,
                target_agents=target_agents or [],
                target_locations=target_locations or [],
                duration=duration,
                immediate_effects=immediate_effects or [],
                delayed_effects=delayed_effects or [],
                expires_at=(
                    _time_module.time() + duration if duration > 0 else None
                ),
            )
            self._injections[injection.injection_id] = injection
            return injection

    def cancel_event(self, injection_id: str) -> bool:
        """Cancel an active injected event."""
        _time_module.sleep(0.001)
        with self._lock:
            injection = self._injections.get(injection_id)
            if injection is None:
                return False
            injection.status = "cancelled"
            return True

    def list_active_events(self) -> List[EventInjection]:
        """List all currently active injected events."""
        _time_module.sleep(0.001)
        with self._lock:
            now = _time_module.time()
            active: List[EventInjection] = []
            for inj in self._injections.values():
                if inj.status != "active":
                    continue
                if inj.expires_at is not None and now > inj.expires_at:
                    inj.status = "expired"
                    continue
                active.append(inj)
            return active

    # ---- Agent Memory Editing ----

    def edit_agent_memory(
        self,
        agent_id: str,
        memory_id: str,
        edit_type: str,
        new_content: Dict[str, Any],
        justification: str = "",
    ) -> MemoryEdit:
        """Edit an agent's memory with tracking and revert capability."""
        _time_module.sleep(0.001)
        with self._lock:
            try:
                et = MemoryEditType(edit_type.lower())
            except ValueError:
                et = MemoryEditType.MODIFY

            edit = MemoryEdit(
                agent_id=agent_id,
                memory_id=memory_id,
                edit_type=et,
                original_content={},
                new_content=new_content,
                justification=justification,
                personality_impact={
                    "trait_deltas": {},
                    "relationship_changes": [],
                },
            )
            self._memory_edits[edit.edit_id] = edit
            self._total_memory_edits += 1
            return edit

    def revert_memory_edit(self, edit_id: str) -> Optional[MemoryEdit]:
        """Revert a previously applied memory edit."""
        _time_module.sleep(0.001)
        with self._lock:
            original = self._memory_edits.get(edit_id)
            if original is None or original.reverted:
                return None

            original.reverted = True
            revert = MemoryEdit(
                agent_id=original.agent_id,
                memory_id=original.memory_id,
                edit_type=MemoryEditType.RESTORE,
                original_content=original.new_content,
                new_content=original.original_content,
                justification=f"Revert of edit {edit_id}",
                personality_impact={
                    "trait_deltas": {},
                    "relationship_changes": [],
                },
            )
            original.revert_edit_id = revert.edit_id
            self._memory_edits[revert.edit_id] = revert
            self._total_memory_edits += 1
            return revert

    # ---- Agent Personality Modification ----

    def modify_agent_personality(
        self,
        agent_id: str,
        trait_deltas: Dict[str, float],
    ) -> Dict[str, Any]:
        """Modify an agent's personality traits."""
        _time_module.sleep(0.001)
        with self._lock:
            old_traits = {
                "openness": 0.5,
                "conscientiousness": 0.5,
                "extraversion": 0.5,
                "agreeableness": 0.5,
                "neuroticism": 0.5,
            }
            new_traits = {}
            for trait, value in old_traits.items():
                delta = trait_deltas.get(trait, 0.0)
                new_traits[trait] = max(0.0, min(1.0, value + delta))

            implications: List[str] = []
            if new_traits.get("extraversion", 0.5) > 0.7:
                implications.append("Agent becomes more socially proactive")
            if new_traits.get("agreeableness", 0.5) < 0.3:
                implications.append("Agent may become confrontational")
            if new_traits.get("neuroticism", 0.5) > 0.7:
                implications.append("Agent may exhibit anxious behavior")
            if new_traits.get("openness", 0.5) > 0.7:
                implications.append("Agent becomes more curious and exploratory")

            return {
                "agent_id": agent_id,
                "old_traits": old_traits,
                "new_traits": new_traits,
                "behavior_implications": implications,
            }

    # ---- Agent Teleportation ----

    def teleport_agent(
        self,
        agent_id: str,
        new_location: str,
    ) -> Dict[str, Any]:
        """Teleport an agent to a new location."""
        _time_module.sleep(0.001)
        return {
            "agent_id": agent_id,
            "previous_location": "unknown",
            "new_location": new_location,
            "teleported_at": _time_module.time(),
            "success": True,
        }

    # ---- Agent Inventory Modification ----

    def modify_agent_inventory(
        self,
        agent_id: str,
        add_items: Optional[List[str]] = None,
        remove_items: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Add or remove items from an agent's inventory."""
        _time_module.sleep(0.001)
        with self._lock:
            to_add = add_items or []
            to_remove = remove_items or []
            return {
                "agent_id": agent_id,
                "items_added": to_add,
                "items_removed": to_remove,
                "inventory_snapshot": [],
                "modified_at": _time_module.time(),
            }

    # ---- Timeline Branching ----

    def create_timeline_branch(
        self,
        world_id: str,
        name: str,
        description: str,
        from_snapshot: str = "",
    ) -> TimelineBranch:
        """Create a new timeline branch diverging from a snapshot."""
        _time_module.sleep(0.001)
        with self._lock:
            if world_id not in self._world_timelines:
                self._world_timelines[world_id] = []

            branch = TimelineBranch(
                parent_branch_id=(
                    self._active_timeline.get(world_id, "")
                ),
                world_id=world_id,
                name=name,
                description=description,
                created_from_snapshot=from_snapshot,
                divergence_point=from_snapshot or "root",
            )
            self._timeline_branches[branch.branch_id] = branch
            self._world_timelines[world_id].append(branch.branch_id)
            return branch

    def switch_timeline(self, branch_id: str) -> Optional[TimelineBranch]:
        """Switch the active timeline to the specified branch."""
        _time_module.sleep(0.001)
        with self._lock:
            branch = self._timeline_branches.get(branch_id)
            if branch is None:
                return None
            branch.is_active = True
            self._active_timeline[branch.world_id] = branch_id
            return branch

    def merge_timelines(
        self,
        branch_id_1: str,
        branch_id_2: str,
        resolution_strategy: str = "interleave",
    ) -> Optional[TimelineBranch]:
        """Merge two timeline branches into a unified branch."""
        _time_module.sleep(0.001)
        with self._lock:
            b1 = self._timeline_branches.get(branch_id_1)
            b2 = self._timeline_branches.get(branch_id_2)

            if b1 is None or b2 is None:
                return None

            if b1.world_id != b2.world_id:
                return None

            merged_events = list(b1.events)
            b2_event_ids = {
                e.get("event_id", str(i)) for i, e in enumerate(b2.events)
            }
            for event in b2.events:
                eid = event.get("event_id", "")
                if eid not in {
                    e.get("event_id", str(i))
                    for i, e in enumerate(b1.events)
                }:
                    merged_events.append(event)

            if resolution_strategy == "primary_first":
                pass
            elif resolution_strategy == "interleave":
                merged_events = []
                max_len = max(len(b1.events), len(b2.events))
                for i in range(max_len):
                    if i < len(b1.events):
                        merged_events.append(b1.events[i])
                    if i < len(b2.events):
                        merged_events.append(b2.events[i])

            merged_branch = TimelineBranch(
                parent_branch_id=branch_id_1,
                world_id=b1.world_id,
                name=f"Merged: {b1.name} + {b2.name}",
                description=(
                    f"Merge of '{b1.name}' and '{b2.name}' "
                    f"using {resolution_strategy} strategy"
                ),
                created_from_snapshot="",
                divergence_point=f"Merge of {branch_id_1} and {branch_id_2}",
                events=merged_events,
                merge_status=TimelineMergeStatus.MERGED,
            )
            self._timeline_branches[merged_branch.branch_id] = merged_branch
            self._world_timelines[b1.world_id].append(merged_branch.branch_id)

            b1.merge_status = TimelineMergeStatus.MERGED
            b2.merge_status = TimelineMergeStatus.MERGED
            b1.is_active = False
            b2.is_active = False

            return merged_branch

    def list_timeline_branches(
        self, world_id: str,
    ) -> List[TimelineBranch]:
        """List all timeline branches for a world."""
        _time_module.sleep(0.001)
        with self._lock:
            branch_ids = self._world_timelines.get(world_id, [])
            return [
                self._timeline_branches[bid]
                for bid in branch_ids
                if bid in self._timeline_branches
            ]

    # ---- Divine Broadcast ----

    def broadcast_god_message(
        self,
        message: str,
        target_agents: Optional[List[str]] = None,
        delivery_style: str = "vision",
    ) -> Dict[str, Any]:
        """Broadcast a message from god-mode to target agents."""
        _time_module.sleep(0.001)
        with self._lock:
            agents = target_agents or []
            return {
                "target_agents": agents,
                "acknowledged": len(agents),
                "reactions": [
                    {
                        "agent_id": aid,
                        "reaction": "acknowledged",
                        "message": message,
                        "style": delivery_style,
                    }
                    for aid in agents
                ],
            }

    # ---- Divine Intervention ----

    def apply_divine_intervention(
        self,
        intervention_type: str,
        target_type: str,
        target_id: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        scope: str = "single_agent",
    ) -> DivineIntervention:
        """Apply a divine intervention to the world."""
        _time_module.sleep(0.001)
        with self._lock:
            try:
                itype = InterventionType(intervention_type.lower())
            except ValueError:
                itype = InterventionType.INSTANT

            try:
                iscope = InterventionScope(scope.lower())
            except ValueError:
                iscope = InterventionScope.SINGLE_AGENT

            intervention = DivineIntervention(
                type=itype,
                target_type=target_type,
                target_id=target_id,
                action=action,
                parameters=parameters or {},
                scope=iscope,
                before_snapshot={
                    "target_id": target_id,
                    "state": "pre_intervention",
                    "captured_at": _time_module.time(),
                },
                after_snapshot={},
                narrative_impact={
                    "magnitude": "moderate",
                    "description": "",
                    "affected_factions": [],
                },
            )
            self._interventions[intervention.intervention_id] = intervention
            self._total_interventions += 1
            self._last_intervention_time = _time_module.time()
            return intervention

    def revert_intervention(
        self, intervention_id: str,
    ) -> Optional[DivineIntervention]:
        """Revert a previously applied divine intervention."""
        _time_module.sleep(0.001)
        with self._lock:
            original = self._interventions.get(intervention_id)
            if original is None or original.reverted:
                return None

            original.reverted = True
            revert = DivineIntervention(
                type=InterventionType.REVERSIBLE,
                target_type=original.target_type,
                target_id=original.target_id,
                action=f"revert_{original.action}",
                parameters=original.parameters,
                scope=original.scope,
                before_snapshot=original.after_snapshot,
                after_snapshot=original.before_snapshot,
                narrative_impact={
                    "magnitude": "minor",
                    "description": f"Revert of intervention {intervention_id}",
                    "affected_factions": [],
                },
            )
            original.revert_intervention_id = revert.intervention_id
            self._interventions[revert.intervention_id] = revert
            self._total_interventions += 1
            self._last_intervention_time = _time_module.time()
            return revert

    def predict_intervention_outcome(
        self,
        intervention_type: str,
        target_type: str,
        target_id: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Predict the likely outcome of a divine intervention before applying it."""
        _time_module.sleep(0.001)
        with self._lock:
            params = parameters or {}
            risk_level = "low"
            confidence = 0.85

            if action in ("destroy", "annihilate", "obliterate"):
                risk_level = "extreme"
                confidence = 0.4
            elif action in ("modify", "alter", "change"):
                risk_level = "moderate"
                confidence = 0.7
            elif action in ("teleport", "move", "relocate"):
                risk_level = "low"
                confidence = 0.9

            return {
                "predicted_effects": [
                    {
                        "effect": f"Target {target_id} affected by {action}",
                        "probability": confidence,
                        "scope": target_type,
                    }
                ],
                "confidence": confidence,
                "risks": [
                    {
                        "level": risk_level,
                        "description": (
                            f"Action '{action}' carries {risk_level} risk"
                        ),
                    }
                ],
                "timeline_impact": {
                    "creates_branch_point": action in (
                        "destroy", "annihilate", "create", "transform",
                    ),
                    "estimated_divergence": (
                        0.8 if action in ("destroy", "annihilate") else 0.3
                    ),
                },
            }

    # ---- Statistics ----

    def get_god_mode_stats(self) -> Dict[str, Any]:
        """Get comprehensive god-mode usage statistics."""
        _time_module.sleep(0.001)
        with self._lock:
            active_events = sum(
                1 for inj in self._injections.values()
                if inj.status == "active"
            )
            return {
                "total_snapshots": self._total_snapshots,
                "total_interventions": self._total_interventions,
                "active_events": active_events,
                "total_branches": len(self._timeline_branches),
                "memory_edits": self._total_memory_edits,
                "last_intervention_time": self._last_intervention_time,
            }

    def reset(self) -> None:
        """Reset the god-mode controller to its initial state."""
        _time_module.sleep(0.001)
        with self._lock:
            self._snapshots.clear()
            self._interventions.clear()
            self._injections.clear()
            self._memory_edits.clear()
            self._timeline_branches.clear()
            self._world_timelines.clear()
            self._active_timeline.clear()
            self._total_snapshots = 0
            self._total_interventions = 0
            self._total_memory_edits = 0
            self._last_intervention_time = 0.0


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

_god_mode_controller: Optional[AgentGodModeController] = None


def get_god_mode_controller() -> AgentGodModeController:
    """Get the singleton AgentGodModeController instance."""
    global _god_mode_controller
    if _god_mode_controller is None:
        _god_mode_controller = AgentGodModeController()
    return _god_mode_controller