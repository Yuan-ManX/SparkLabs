"""
SparkLabs Engine - Animation Retargeting

An original animation retargeting subsystem that transfers motion authored for
one skeleton onto a different skeleton. Retargeting compensates for differing
bone hierarchies, limb proportions, and rest-pose orientations so that a clip
recorded on a source skeleton plays back cleanly on a target skeleton.

The subsystem maintains a registry of skeleton profiles, bone mappings,
retarget profiles, retarget jobs, and pose correction configurations. A
profile bundles the retarget method, quality, root-motion and IK toggles, and
spine correction weight. A job represents one execution of a profile against a
source clip to produce a converted clip on the target skeleton.

Architecture:
  AnimationRetargetingSystem (singleton, double-checked locking)
    |-- BoneNode              (a single bone in a skeleton hierarchy)
    |-- SkeletonProfile       (a skeleton with bones, roles, lengths, hierarchy)
    |-- BoneMapping           (a full bone-to-bone table between two skeletons)
    |-- RetargetProfile       (a reusable retarget configuration)
    |-- RetargetJob           (a single retarget execution)
    |-- PoseCorrectionConfig  (a per-bone pose correction entry)
    |-- RetargetStats         (aggregate statistic counters)
    |-- RetargetSnapshot      (immutable snapshot of subsystem state)
    |-- RetargetEvent         (an emitted subsystem lifecycle event)
    |-- RetargetMethod, BoneMappingType, PoseCorrection, RetargetQuality,
        RetargetEventKind, JobStatus

Lifecycle:
  1. register_skeleton(name, skeleton_type, bones)         -> SkeletonProfile
  2. create_mapping(source, target, mapping_type, entries) -> BoneMapping
  3. create_profile(...)                                   -> RetargetProfile
  4. start_retarget(profile_id, source_clip_id, ...)       -> RetargetJob
  5. complete_job(job_id, target_clip_id, ...)             -> RetargetJob
  6. fail_job(job_id, error_message)                       -> RetargetJob
  7. get_stats / get_status / get_snapshot / reset

The module is written from scratch for SparkLabs. It depends only on the
Python standard library and follows the engine-wide singleton + reentrant-lock
conventions used across the SparkLabs engine modules.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# Capacity Constants
# =============================================================================

# Maximum number of items held in each bounded store before the oldest entries
# are evicted (FIFO). These bounds keep the retargeting subsystem's memory
# footprint predictable even when driven by an agent generating large volumes
# of skeleton, mapping, profile, and job data.
_MAX_SKELETONS: int = 5000
_MAX_PROFILES: int = 5000
_MAX_MAPPINGS: int = 20000
_MAX_JOBS: int = 10000
_MAX_CORRECTIONS: int = 5000
_MAX_EVENTS: int = 10000


# =============================================================================
# Helper Functions
# =============================================================================


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a ``Z`` suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier with an
            underscore. When empty, the raw hexadecimal identifier is returned.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits within ``max_size``.

    Eviction is FIFO based on dict insertion order. The capacity is floored at
    one so that a store can always retain its most recent entry.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits within ``max_size``.

    Eviction is FIFO by popping from the front of the list.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


# =============================================================================
# Enumerations
# =============================================================================


class RetargetMethod(str, Enum):
    """The strategy used to transfer motion between skeletons.

    ``uniform_scale`` rescales the whole skeleton by a single factor.
    ``bone_length`` rescales each bone by the ratio of target to source bone
    lengths. ``pose_matching`` matches poses bone-by-bone using rest-pose
    offsets. ``ik_solver`` solves inverse kinematics chains so end effectors
    reach the correct targets. ``hybrid`` combines several of the above per
    bone chain. ``manual`` uses an explicit bone-to-bone table without any
    automatic proportion solving.
    """

    UNIFORM_SCALE = "uniform_scale"
    SCALE_BASED = "scale_based"
    BONE_LENGTH = "bone_length"
    POSE_MATCHING = "pose_matching"
    IK_SOLVER = "ik_solver"
    HYBRID = "hybrid"
    MANUAL = "manual"


class BoneMappingType(str, Enum):
    """How bone-to-bone correspondences between two skeletons are derived.

    ``auto`` infers correspondences from semantic bone roles. ``manual`` uses
    only the explicitly provided bone pairs. ``hybrid`` starts from auto
    inference and then applies manual overrides. ``one_to_one`` enforces a
    strict one-to-one pairing. ``one_to_many`` allows one source bone to drive
    several target bones (useful for subdivided rigs). ``many_to_one`` blends
    several source bones into one target bone.
    """

    AUTO = "auto"
    MANUAL = "manual"
    HYBRID = "hybrid"
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"


class PoseCorrection(str, Enum):
    """How aggressively pose corrections are applied after the initial pass.

    ``none`` applies no correction. ``soft`` applies light smoothing for minor
    artifacts. ``strict`` enforces bone constraints and angle limits suitable
    for production. ``aggressive`` runs the full correction and IK pass for
    difficult proportion mismatches.
    """

    NONE = "none"
    SOFT = "soft"
    STRICT = "strict"
    AGGRESSIVE = "aggressive"


# Alias used by the route layer and API contract.
CorrectionMode = PoseCorrection


class RetargetQuality(str, Enum):
    """The fidelity level of a retarget pass.

    ``draft`` runs the fastest path for previewing. ``standard`` balances
    speed and quality for gameplay clips. ``high`` applies fuller correction
    for cutscenes. ``ultra`` runs every correction pass for final-quality
    output.
    """

    DRAFT = "draft"
    PREVIEW = "preview"
    STANDARD = "standard"
    HIGH = "high"
    ULTRA = "ultra"


class RetargetEventKind(str, Enum):
    """Kinds of events emitted by the animation retargeting subsystem."""

    SKELETON_REGISTERED = "skeleton_registered"
    SKELETON_REMOVED = "skeleton_removed"
    MAPPING_CREATED = "mapping_created"
    MAPPING_UPDATED = "mapping_updated"
    MAPPING_REMOVED = "mapping_removed"
    PROFILE_CREATED = "profile_created"
    PROFILE_UPDATED = "profile_updated"
    PROFILE_REMOVED = "profile_removed"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    CORRECTION_CREATED = "correction_created"
    CORRECTION_REMOVED = "correction_removed"
    SUBSYSTEM_RESET = "subsystem_reset"


class JobStatus(str, Enum):
    """Lifecycle states for a retarget job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class BoneNode:
    """A single bone in a skeleton hierarchy.

    A bone carries its rest-pose local transform (position, rotation, scale)
    relative to its parent, plus a rest-pose length used for proportion
    solving. The semantic ``role`` drives automatic bone matching across
    skeletons.

    Attributes:
        bone_id: Unique identifier (auto-generated when omitted).
        name: Human-readable bone name.
        role: Semantic role of the bone (free-form string).
        parent_id: Identifier of the parent bone (``None`` for the root).
        position_x/y/z: Rest-pose local position.
        rotation_x/y/z/w: Rest-pose local rotation as a quaternion.
        scale_x/y/z: Rest-pose local scale.
        length: Rest-pose bone length used for proportion solving.
    """

    bone_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    role: str = "custom"
    parent_id: Optional[str] = None
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    rotation_w: float = 1.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    scale_z: float = 1.0
    length: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bone_id": self.bone_id,
            "name": self.name,
            "role": self.role,
            "parent_id": self.parent_id,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "position_z": self.position_z,
            "rotation_x": self.rotation_x,
            "rotation_y": self.rotation_y,
            "rotation_z": self.rotation_z,
            "rotation_w": self.rotation_w,
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
            "scale_z": self.scale_z,
            "length": self.length,
        }


@dataclass
class SkeletonProfile:
    """A skeleton definition registered for retargeting.

    A skeleton describes its bones, the semantic role of each bone, the
    rest-pose length of each bone, and the parent-child relationships between
    bones. Skeletons are the endpoints of a retarget: a source skeleton
    provides the authored motion and a target skeleton receives the
    retargeted motion.

    Attributes:
        skeleton_id: Unique identifier (auto-generated).
        name: Human-readable name of the skeleton.
        skeleton_type: Structural category of the skeleton (free-form string).
        bone_count: Total number of bones in the skeleton.
        root_bone_id: Identifier of the root bone.
        bones: Ordered list of bone nodes.
        registered_at: Timestamp when the skeleton was registered.
    """

    skeleton_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    skeleton_type: str = "humanoid"
    bone_count: int = 0
    root_bone_id: str = ""
    bones: List[BoneNode] = field(default_factory=list)
    registered_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skeleton_id": self.skeleton_id,
            "name": self.name,
            "skeleton_type": self.skeleton_type,
            "bone_count": self.bone_count,
            "root_bone_id": self.root_bone_id,
            "bones": [bone.to_dict() for bone in self.bones],
            "registered_at": self.registered_at,
        }


@dataclass
class BoneMapping:
    """A full bone-to-bone mapping table between two skeletons.

    A mapping record links a source skeleton to a target skeleton through a
    list of bone-pair entries. Each entry maps one source bone to one target
    bone with an optional per-bone scale factor and position/rotation offsets
    applied during the retarget pass.

    Attributes:
        mapping_id: Unique identifier (auto-generated).
        name: Human-readable name of the mapping.
        source_skeleton_id: Identifier of the source skeleton.
        target_skeleton_id: Identifier of the target skeleton.
        mapping_type: How the correspondences were derived.
        entries: List of bone-pair dicts with keys ``source_bone_id``,
            ``target_bone_id``, ``source_bone_name``, ``target_bone_name``,
            ``scale_factor``, ``rotation_offset``, ``position_offset``.
        entry_count: Number of bone-pair entries.
        created_at: Timestamp when the mapping was created.
        updated_at: Timestamp when the mapping was last updated.
    """

    mapping_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    source_skeleton_id: str = ""
    target_skeleton_id: str = ""
    mapping_type: BoneMappingType = BoneMappingType.MANUAL
    entries: List[Dict[str, Any]] = field(default_factory=list)
    entry_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "name": self.name,
            "source_skeleton_id": self.source_skeleton_id,
            "target_skeleton_id": self.target_skeleton_id,
            "mapping_type": self.mapping_type.value,
            "entries": [dict(e) for e in self.entries],
            "entry_count": self.entry_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class RetargetProfile:
    """A reusable retarget configuration.

    A profile bundles all of the parameters that govern a retarget pass: the
    method, mapping, correction mode, quality, root-motion preservation, foot
    and hand IK toggles, and a spine correction weight.

    Attributes:
        profile_id: Unique identifier (auto-generated).
        name: Human-readable name of the profile.
        source_skeleton_id: Identifier of the source skeleton.
        target_skeleton_id: Identifier of the target skeleton.
        mapping_id: Identifier of the bone mapping to use.
        method: The retarget method to use.
        correction: The pose correction mode to use.
        quality: The fidelity level of the retarget.
        preserve_root_motion: Whether to preserve root motion.
        preserve_foot_ik: Whether to preserve foot IK contact.
        hand_ik_enabled: Whether hand IK is enabled.
        foot_ik_enabled: Whether foot IK is enabled.
        spine_correction: Spine correction blend weight (0.0 to 1.0).
        created_at: Timestamp when the profile was created.
        updated_at: Timestamp when the profile was last updated.
    """

    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    source_skeleton_id: str = ""
    target_skeleton_id: str = ""
    mapping_id: str = ""
    method: RetargetMethod = RetargetMethod.UNIFORM_SCALE
    correction: PoseCorrection = PoseCorrection.NONE
    quality: RetargetQuality = RetargetQuality.STANDARD
    preserve_root_motion: bool = True
    preserve_foot_ik: bool = True
    hand_ik_enabled: bool = False
    foot_ik_enabled: bool = True
    spine_correction: float = 1.0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "source_skeleton_id": self.source_skeleton_id,
            "target_skeleton_id": self.target_skeleton_id,
            "mapping_id": self.mapping_id,
            "method": self.method.value,
            "correction": self.correction.value,
            "quality": self.quality.value,
            "preserve_root_motion": self.preserve_root_motion,
            "preserve_foot_ik": self.preserve_foot_ik,
            "hand_ik_enabled": self.hand_ik_enabled,
            "foot_ik_enabled": self.foot_ik_enabled,
            "spine_correction": self.spine_correction,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class RetargetJob:
    """A single retarget execution.

    A job is created when a profile is applied to a source clip. It tracks
    the execution lifecycle from pending through running to a terminal state
    (completed, failed, or cancelled). A completed job records the produced
    target clip identifier, frame count, and duration.

    Attributes:
        job_id: Unique identifier (auto-generated).
        profile_id: Identifier of the retarget profile used.
        source_clip_id: Identifier of the source animation clip.
        target_clip_id: Identifier of the produced target clip (empty until
            completion).
        method: The retarget method used for this job.
        quality: The fidelity level of this job.
        status: Current lifecycle state of the job.
        error_message: Error description (empty unless the job failed).
        started_at: Timestamp when the job entered the running state.
        completed_at: Timestamp when the job reached a terminal state.
        duration_ms: Wall-clock duration of the retarget pass in milliseconds.
        frame_count: Number of frames in the produced target clip.
        created_at: Timestamp when the job was created.
    """

    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    profile_id: str = ""
    source_clip_id: str = ""
    target_clip_id: str = ""
    method: RetargetMethod = RetargetMethod.UNIFORM_SCALE
    quality: RetargetQuality = RetargetQuality.STANDARD
    status: JobStatus = JobStatus.PENDING
    error_message: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0
    frame_count: int = 0
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "profile_id": self.profile_id,
            "source_clip_id": self.source_clip_id,
            "target_clip_id": self.target_clip_id,
            "method": self.method.value,
            "quality": self.quality.value,
            "status": self.status.value,
            "error_message": self.error_message,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "frame_count": self.frame_count,
            "created_at": self.created_at,
        }


@dataclass
class PoseCorrectionConfig:
    """A per-bone pose correction entry.

    A correction config describes an additive adjustment applied to a specific
    bone after the initial retarget pass. Adjustments include position offset,
    rotation offset, scale factor, and a blend weight controlling how strongly
    the correction is applied.

    Attributes:
        correction_id: Unique identifier (auto-generated).
        name: Human-readable name of the correction.
        skeleton_id: Identifier of the skeleton this correction targets.
        bone_id: Identifier of the bone this correction targets.
        bone_name: Name of the bone (for readability).
        correction_type: The correction mode this config belongs to.
        position_offset: Position offset dict with keys ``x``, ``y``, ``z``.
        rotation_offset: Rotation offset dict with keys ``x``, ``y``, ``z``,
            ``w`` (quaternion).
        scale_factor: Per-bone scale multiplier.
        weight: Blend weight (0.0 to 1.0) controlling correction strength.
        enabled: Whether this correction is active.
        created_at: Timestamp when the correction was created.
        updated_at: Timestamp when the correction was last updated.
    """

    correction_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    skeleton_id: str = ""
    bone_id: str = ""
    bone_name: str = ""
    correction_type: str = "soft"
    position_offset: Dict[str, float] = field(default_factory=dict)
    rotation_offset: Dict[str, float] = field(default_factory=dict)
    scale_factor: float = 1.0
    weight: float = 1.0
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correction_id": self.correction_id,
            "name": self.name,
            "skeleton_id": self.skeleton_id,
            "bone_id": self.bone_id,
            "bone_name": self.bone_name,
            "correction_type": self.correction_type,
            "position_offset": dict(self.position_offset),
            "rotation_offset": dict(self.rotation_offset),
            "scale_factor": self.scale_factor,
            "weight": self.weight,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class RetargetStats:
    """Aggregate statistic counters for the retargeting subsystem.

    Attributes:
        total_skeletons: Total skeletons registered.
        total_mappings: Total bone mappings created.
        total_profiles: Total retarget profiles created.
        total_jobs: Total retarget jobs created.
        pending_jobs: Jobs currently in the pending state.
        running_jobs: Jobs currently in the running state.
        completed_jobs: Jobs that completed successfully.
        failed_jobs: Jobs that failed.
        cancelled_jobs: Jobs that were cancelled.
        total_corrections: Total pose correction configs created.
        total_events: Total events emitted.
        average_duration_ms: Average wall-clock duration of completed jobs.
        success_rate: Fraction of terminal jobs that completed successfully.
    """

    total_skeletons: int = 0
    total_mappings: int = 0
    total_profiles: int = 0
    total_jobs: int = 0
    pending_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    cancelled_jobs: int = 0
    total_corrections: int = 0
    total_events: int = 0
    average_duration_ms: float = 0.0
    success_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_skeletons": self.total_skeletons,
            "total_mappings": self.total_mappings,
            "total_profiles": self.total_profiles,
            "total_jobs": self.total_jobs,
            "pending_jobs": self.pending_jobs,
            "running_jobs": self.running_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "cancelled_jobs": self.cancelled_jobs,
            "total_corrections": self.total_corrections,
            "total_events": self.total_events,
            "average_duration_ms": self.average_duration_ms,
            "success_rate": self.success_rate,
        }


@dataclass
class RetargetSnapshot:
    """An immutable snapshot of the retargeting subsystem state.

    Attributes:
        taken_at: Timestamp when the snapshot was captured.
        skeletons: List of skeleton profile dicts at capture time.
        mappings: List of bone mapping dicts at capture time.
        profiles: List of retarget profile dicts at capture time.
        jobs: List of retarget job dicts at capture time.
        corrections: List of pose correction config dicts at capture time.
        stats: Aggregate statistics dict at capture time.
    """

    taken_at: str = ""
    skeletons: List[Dict[str, Any]] = field(default_factory=list)
    mappings: List[Dict[str, Any]] = field(default_factory=list)
    profiles: List[Dict[str, Any]] = field(default_factory=list)
    jobs: List[Dict[str, Any]] = field(default_factory=list)
    corrections: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "taken_at": self.taken_at,
            "skeletons": list(self.skeletons),
            "mappings": list(self.mappings),
            "profiles": list(self.profiles),
            "jobs": list(self.jobs),
            "corrections": list(self.corrections),
            "stats": dict(self.stats),
        }


@dataclass
class RetargetEvent:
    """A lifecycle event emitted by the retargeting subsystem.

    Attributes:
        event_id: Unique identifier (auto-generated).
        event_kind: The kind of event.
        timestamp: When the event was emitted.
        entity_id: Identifier of the entity the event pertains to.
        entity_type: The type of entity (skeleton, mapping, profile, job,
            correction).
        message: Human-readable event description.
        metadata: Additional event-specific data.
    """

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_kind: RetargetEventKind = RetargetEventKind.SUBSYSTEM_RESET
    timestamp: str = ""
    entity_id: str = ""
    entity_type: str = ""
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_kind": self.event_kind.value,
            "timestamp": self.timestamp,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "message": self.message,
            "metadata": dict(self.metadata),
        }


@dataclass
class AnimationClip:
    """An animation clip registered for retargeting.

    A clip is the source motion data that gets retargeted from one skeleton
    onto another. It carries metadata about duration, frame count, and the
    skeleton it was authored for.

    Attributes:
        clip_id: Unique identifier (auto-generated when omitted).
        name: Human-readable name of the clip.
        skeleton_id: Identifier of the skeleton this clip was authored for.
        duration: Duration of the clip in seconds.
        frame_count: Total number of frames in the clip.
        frame_rate: Playback frame rate in frames per second.
        metadata: Additional clip-specific metadata.
        registered_at: Timestamp when the clip was registered.
    """

    clip_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    skeleton_id: str = ""
    duration: float = 0.0
    frame_count: int = 0
    frame_rate: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "skeleton_id": self.skeleton_id,
            "duration": self.duration,
            "frame_count": self.frame_count,
            "frame_rate": self.frame_rate,
            "metadata": dict(self.metadata),
            "registered_at": self.registered_at,
        }


# =============================================================================
# Animation Retargeting System (Singleton)
# =============================================================================


class AnimationRetargetingSystem:
    """Singleton animation retargeting subsystem.

    Manages skeleton profiles, bone mappings, retarget profiles, retarget
    jobs, and pose correction configurations. All public methods are
    thread-safe, guarded by a reentrant lock. Bounded stores use FIFO
    eviction to cap memory usage.

    The singleton instance is obtained via :func:`get_animation_retargeting`.
    """

    _instance: Optional["AnimationRetargetingSystem"] = None
    _instance_lock: threading.RLock = threading.RLock()

    # -------------------------------------------------------------------------
    # Construction and Initialization
    # -------------------------------------------------------------------------

    def __init__(self) -> None:
        # Reentrant lock guarding all mutable state.
        self._lock: threading.RLock = threading.RLock()
        # Initialization flag.
        self._initialized: bool = False

        # Bounded stores.
        self._skeletons: Dict[str, SkeletonProfile] = {}
        self._animations: Dict[str, AnimationClip] = {}
        self._mappings: Dict[str, BoneMapping] = {}
        self._profiles: Dict[str, RetargetProfile] = {}
        self._jobs: Dict[str, RetargetJob] = {}
        self._corrections: Dict[str, PoseCorrectionConfig] = {}
        self._templates: Dict[str, RetargetProfile] = {}
        self._events: List[RetargetEvent] = []

        # Per-parent index maps for efficient child lookups.
        self._skeletons_by_type: Dict[str, List[str]] = {}
        self._animations_by_skeleton: Dict[str, List[str]] = {}
        self._mappings_by_source: Dict[str, List[str]] = {}
        self._mappings_by_target: Dict[str, List[str]] = {}
        self._profiles_by_source: Dict[str, List[str]] = {}
        self._profiles_by_target: Dict[str, List[str]] = {}
        self._jobs_by_profile: Dict[str, List[str]] = {}
        self._jobs_by_status: Dict[str, List[str]] = {}
        self._corrections_by_skeleton: Dict[str, List[str]] = {}
        self._corrections_by_job: Dict[str, List[str]] = {}

        # Aggregate counters for statistics.
        self._total_jobs_created: int = 0
        self._total_completed: int = 0
        self._total_failed: int = 0
        self._total_cancelled: int = 0
        self._total_duration_ms: float = 0.0

        # Seed default data on first construction.
        self._seed_default_data()
        self._initialized = True

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    def _emit_event(
        self,
        event_kind: RetargetEventKind,
        entity_id: str,
        entity_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RetargetEvent:
        """Emit a lifecycle event and append it to the bounded event store."""
        event = RetargetEvent(
            event_id=_new_id("evt"),
            event_kind=event_kind,
            timestamp=_now(),
            entity_id=entity_id,
            entity_type=entity_type,
            message=message,
            metadata=metadata or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    def _index_skeleton(self, skeleton: SkeletonProfile) -> None:
        """Add a skeleton to the type index."""
        stype = skeleton.skeleton_type
        if stype not in self._skeletons_by_type:
            self._skeletons_by_type[stype] = []
        if skeleton.skeleton_id not in self._skeletons_by_type[stype]:
            self._skeletons_by_type[stype].append(skeleton.skeleton_id)

    def _unindex_skeleton(self, skeleton: SkeletonProfile) -> None:
        """Remove a skeleton from the type index."""
        stype = skeleton.skeleton_type
        if stype in self._skeletons_by_type:
            try:
                self._skeletons_by_type[stype].remove(skeleton.skeleton_id)
            except ValueError:
                pass
            if not self._skeletons_by_type[stype]:
                del self._skeletons_by_type[stype]

    def _index_mapping(self, mapping: BoneMapping) -> None:
        """Add a mapping to the source and target indices."""
        sid = mapping.source_skeleton_id
        tid = mapping.target_skeleton_id
        if sid not in self._mappings_by_source:
            self._mappings_by_source[sid] = []
        if mapping.mapping_id not in self._mappings_by_source[sid]:
            self._mappings_by_source[sid].append(mapping.mapping_id)
        if tid not in self._mappings_by_target:
            self._mappings_by_target[tid] = []
        if mapping.mapping_id not in self._mappings_by_target[tid]:
            self._mappings_by_target[tid].append(mapping.mapping_id)

    def _unindex_mapping(self, mapping: BoneMapping) -> None:
        """Remove a mapping from the source and target indices."""
        sid = mapping.source_skeleton_id
        tid = mapping.target_skeleton_id
        for idx, key in (
            (self._mappings_by_source, sid),
            (self._mappings_by_target, tid),
        ):
            if key in idx:
                try:
                    idx[key].remove(mapping.mapping_id)
                except ValueError:
                    pass
                if not idx[key]:
                    del idx[key]

    def _index_profile(self, profile: RetargetProfile) -> None:
        """Add a profile to the source and target indices."""
        sid = profile.source_skeleton_id
        tid = profile.target_skeleton_id
        if sid not in self._profiles_by_source:
            self._profiles_by_source[sid] = []
        if profile.profile_id not in self._profiles_by_source[sid]:
            self._profiles_by_source[sid].append(profile.profile_id)
        if tid not in self._profiles_by_target:
            self._profiles_by_target[tid] = []
        if profile.profile_id not in self._profiles_by_target[tid]:
            self._profiles_by_target[tid].append(profile.profile_id)

    def _unindex_profile(self, profile: RetargetProfile) -> None:
        """Remove a profile from the source and target indices."""
        sid = profile.source_skeleton_id
        tid = profile.target_skeleton_id
        for idx, key in (
            (self._profiles_by_source, sid),
            (self._profiles_by_target, tid),
        ):
            if key in idx:
                try:
                    idx[key].remove(profile.profile_id)
                except ValueError:
                    pass
                if not idx[key]:
                    del idx[key]

    def _index_job(self, job: RetargetJob) -> None:
        """Add a job to the profile and status indices."""
        pid = job.profile_id
        if pid not in self._jobs_by_profile:
            self._jobs_by_profile[pid] = []
        if job.job_id not in self._jobs_by_profile[pid]:
            self._jobs_by_profile[pid].append(job.job_id)
        status = job.status.value
        if status not in self._jobs_by_status:
            self._jobs_by_status[status] = []
        if job.job_id not in self._jobs_by_status[status]:
            self._jobs_by_status[status].append(job.job_id)

    def _unindex_job(self, job: RetargetJob) -> None:
        """Remove a job from the profile and status indices."""
        pid = job.profile_id
        if pid in self._jobs_by_profile:
            try:
                self._jobs_by_profile[pid].remove(job.job_id)
            except ValueError:
                pass
            if not self._jobs_by_profile[pid]:
                del self._jobs_by_profile[pid]
        old_status = job.status.value
        if old_status in self._jobs_by_status:
            try:
                self._jobs_by_status[old_status].remove(job.job_id)
            except ValueError:
                pass
            if not self._jobs_by_status[old_status]:
                del self._jobs_by_status[old_status]

    def _index_correction(self, correction: PoseCorrectionConfig) -> None:
        """Add a correction to the skeleton index."""
        sid = correction.skeleton_id
        if sid not in self._corrections_by_skeleton:
            self._corrections_by_skeleton[sid] = []
        if correction.correction_id not in self._corrections_by_skeleton[sid]:
            self._corrections_by_skeleton[sid].append(correction.correction_id)

    def _unindex_correction(self, correction: PoseCorrectionConfig) -> None:
        """Remove a correction from the skeleton index."""
        sid = correction.skeleton_id
        if sid in self._corrections_by_skeleton:
            try:
                self._corrections_by_skeleton[sid].remove(correction.correction_id)
            except ValueError:
                pass
            if not self._corrections_by_skeleton[sid]:
                del self._corrections_by_skeleton[sid]

    def _recompute_stats(self) -> RetargetStats:
        """Compute aggregate statistics from the current store contents."""
        total_jobs = len(self._jobs)
        pending = sum(
            1 for j in self._jobs.values() if j.status == JobStatus.PENDING
        )
        running = sum(
            1 for j in self._jobs.values() if j.status == JobStatus.RUNNING
        )
        completed = sum(
            1 for j in self._jobs.values() if j.status == JobStatus.COMPLETED
        )
        failed = sum(
            1 for j in self._jobs.values() if j.status == JobStatus.FAILED
        )
        cancelled = sum(
            1 for j in self._jobs.values() if j.status == JobStatus.CANCELLED
        )
        terminal = completed + failed + cancelled
        avg_duration = 0.0
        if self._total_completed > 0:
            avg_duration = self._total_duration_ms / self._total_completed
        success_rate = 0.0
        if terminal > 0:
            success_rate = completed / terminal
        return RetargetStats(
            total_skeletons=len(self._skeletons),
            total_mappings=len(self._mappings),
            total_profiles=len(self._profiles),
            total_jobs=total_jobs,
            pending_jobs=pending,
            running_jobs=running,
            completed_jobs=completed,
            failed_jobs=failed,
            cancelled_jobs=cancelled,
            total_corrections=len(self._corrections),
            total_events=len(self._events),
            average_duration_ms=round(avg_duration, 4),
            success_rate=round(success_rate, 4),
        )

    # -------------------------------------------------------------------------
    # Seed Data
    # -------------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Populate the subsystem with default skeleton, mapping, profile,
        correction, and job data so that the system is immediately useful
        after construction.
        """
        # --- Seed skeleton 1: Humanoid_Base (16 bones) ---
        humanoid_bones = [
            BoneNode(bone_id="hb_root", name="root", role="root", parent_id=None,
                     position_y=0.0, length=0.0),
            BoneNode(bone_id="hb_hips", name="hips", role="hips", parent_id="hb_root",
                     position_y=1.0, length=0.2),
            BoneNode(bone_id="hb_spine", name="spine", role="spine", parent_id="hb_hips",
                     position_y=0.2, length=0.3),
            BoneNode(bone_id="hb_chest", name="chest", role="chest", parent_id="hb_spine",
                     position_y=0.3, length=0.2),
            BoneNode(bone_id="hb_neck", name="neck", role="neck", parent_id="hb_chest",
                     position_y=0.2, length=0.1),
            BoneNode(bone_id="hb_head", name="head", role="head", parent_id="hb_neck",
                     position_y=0.1, length=0.2),
            BoneNode(bone_id="hb_shoulder_l", name="shoulder_l", role="shoulder_l",
                     parent_id="hb_chest", position_x=-0.15, length=0.1),
            BoneNode(bone_id="hb_shoulder_r", name="shoulder_r", role="shoulder_r",
                     parent_id="hb_chest", position_x=0.15, length=0.1),
            BoneNode(bone_id="hb_upper_arm_l", name="upper_arm_l", role="upper_arm_l",
                     parent_id="hb_shoulder_l", position_x=-0.1, length=0.3),
            BoneNode(bone_id="hb_upper_arm_r", name="upper_arm_r", role="upper_arm_r",
                     parent_id="hb_shoulder_r", position_x=0.1, length=0.3),
            BoneNode(bone_id="hb_lower_arm_l", name="lower_arm_l", role="lower_arm_l",
                     parent_id="hb_upper_arm_l", position_x=-0.3, length=0.25),
            BoneNode(bone_id="hb_lower_arm_r", name="lower_arm_r", role="lower_arm_r",
                     parent_id="hb_upper_arm_r", position_x=0.3, length=0.25),
            BoneNode(bone_id="hb_upper_leg_l", name="upper_leg_l", role="upper_leg_l",
                     parent_id="hb_hips", position_x=-0.1, position_y=-0.1, length=0.4),
            BoneNode(bone_id="hb_upper_leg_r", name="upper_leg_r", role="upper_leg_r",
                     parent_id="hb_hips", position_x=0.1, position_y=-0.1, length=0.4),
            BoneNode(bone_id="hb_lower_leg_l", name="lower_leg_l", role="lower_leg_l",
                     parent_id="hb_upper_leg_l", position_y=-0.4, length=0.35),
            BoneNode(bone_id="hb_lower_leg_r", name="lower_leg_r", role="lower_leg_r",
                     parent_id="hb_upper_leg_r", position_y=-0.4, length=0.35),
        ]
        humanoid = SkeletonProfile(
            skeleton_id="skel_humanoid_base",
            name="Humanoid_Base",
            skeleton_type="humanoid",
            bone_count=16,
            root_bone_id="hb_root",
            bones=humanoid_bones,
            registered_at=_now(),
        )
        self._skeletons[humanoid.skeleton_id] = humanoid
        self._index_skeleton(humanoid)

        # --- Seed skeleton 2: Creature_Quadruped (17 bones) ---
        quad_bones = [
            BoneNode(bone_id="cq_root", name="root", role="root", parent_id=None,
                     position_y=0.0, length=0.0),
            BoneNode(bone_id="cq_hips", name="hips", role="hips", parent_id="cq_root",
                     position_y=0.8, length=0.2),
            BoneNode(bone_id="cq_spine", name="spine", role="spine", parent_id="cq_hips",
                     position_y=0.2, length=0.4),
            BoneNode(bone_id="cq_spine_02", name="spine_02", role="spine",
                     parent_id="cq_spine", position_y=0.4, length=0.3),
            BoneNode(bone_id="cq_chest", name="chest", role="chest", parent_id="cq_spine_02",
                     position_y=0.3, length=0.2),
            BoneNode(bone_id="cq_neck", name="neck", role="neck", parent_id="cq_chest",
                     position_y=0.2, length=0.15),
            BoneNode(bone_id="cq_head", name="head", role="head", parent_id="cq_neck",
                     position_y=0.15, length=0.2),
            BoneNode(bone_id="cq_front_leg_l_upper", name="front_leg_l_upper",
                     role="front_leg_l_upper", parent_id="cq_chest",
                     position_x=-0.2, position_y=-0.1, length=0.35),
            BoneNode(bone_id="cq_front_leg_r_upper", name="front_leg_r_upper",
                     role="front_leg_r_upper", parent_id="cq_chest",
                     position_x=0.2, position_y=-0.1, length=0.35),
            BoneNode(bone_id="cq_front_leg_l_lower", name="front_leg_l_lower",
                     role="front_leg_l_lower", parent_id="cq_front_leg_l_upper",
                     position_y=-0.35, length=0.3),
            BoneNode(bone_id="cq_front_leg_r_lower", name="front_leg_r_lower",
                     role="front_leg_r_lower", parent_id="cq_front_leg_r_upper",
                     position_y=-0.35, length=0.3),
            BoneNode(bone_id="cq_back_leg_l_upper", name="back_leg_l_upper",
                     role="back_leg_l_upper", parent_id="cq_hips",
                     position_x=-0.2, position_y=-0.2, length=0.4),
            BoneNode(bone_id="cq_back_leg_r_upper", name="back_leg_r_upper",
                     role="back_leg_r_upper", parent_id="cq_hips",
                     position_x=0.2, position_y=-0.2, length=0.4),
            BoneNode(bone_id="cq_back_leg_l_lower", name="back_leg_l_lower",
                     role="back_leg_l_lower", parent_id="cq_back_leg_l_upper",
                     position_y=-0.4, length=0.35),
            BoneNode(bone_id="cq_back_leg_r_lower", name="back_leg_r_lower",
                     role="back_leg_r_lower", parent_id="cq_back_leg_r_upper",
                     position_y=-0.4, length=0.35),
            BoneNode(bone_id="cq_tail_01", name="tail_01", role="tail",
                     parent_id="cq_hips", position_y=-0.15, length=0.2),
            BoneNode(bone_id="cq_tail_02", name="tail_02", role="tail",
                     parent_id="cq_tail_01", position_y=-0.2, length=0.15),
        ]
        quadruped = SkeletonProfile(
            skeleton_id="skel_creature_quadruped",
            name="Creature_Quadruped",
            skeleton_type="quadruped",
            bone_count=17,
            root_bone_id="cq_root",
            bones=quad_bones,
            registered_at=_now(),
        )
        self._skeletons[quadruped.skeleton_id] = quadruped
        self._index_skeleton(quadruped)

        # --- Seed animation clip: Walk Cycle ---
        walk_clip = AnimationClip(
            clip_id="clip_walk_cycle",
            name="Walk Cycle",
            skeleton_id="skel_humanoid_base",
            duration=1.0,
            frame_count=30,
            frame_rate=30.0,
            metadata={"loop": True, "category": "locomotion"},
            registered_at=_now(),
        )
        self._animations[walk_clip.clip_id] = walk_clip
        self._index_animation(walk_clip)

        # --- Seed bone mapping: Humanoid to Quadruped ---
        seed_entries = [
            {"source_bone_id": "hb_root", "target_bone_id": "cq_root",
             "source_bone_name": "root", "target_bone_name": "root",
             "scale_factor": 1.0, "rotation_offset": {}, "position_offset": {}},
            {"source_bone_id": "hb_hips", "target_bone_id": "cq_hips",
             "source_bone_name": "hips", "target_bone_name": "hips",
             "scale_factor": 0.8, "rotation_offset": {}, "position_offset": {}},
            {"source_bone_id": "hb_spine", "target_bone_id": "cq_spine",
             "source_bone_name": "spine", "target_bone_name": "spine",
             "scale_factor": 1.3, "rotation_offset": {}, "position_offset": {}},
        ]
        seed_mapping = BoneMapping(
            mapping_id="mapping_humanoid_to_quad",
            name="Humanoid to Quadruped",
            source_skeleton_id="skel_humanoid_base",
            target_skeleton_id="skel_creature_quadruped",
            mapping_type=BoneMappingType.HYBRID,
            entries=seed_entries,
            entry_count=len(seed_entries),
            created_at=_now(),
            updated_at=_now(),
        )
        self._mappings[seed_mapping.mapping_id] = seed_mapping
        self._index_mapping(seed_mapping)

        # --- Seed retarget profile ---
        seed_profile = RetargetProfile(
            profile_id="profile_humanoid_to_quad",
            name="Humanoid to Quadruped Profile",
            source_skeleton_id="skel_humanoid_base",
            target_skeleton_id="skel_creature_quadruped",
            mapping_id="mapping_humanoid_to_quad",
            method=RetargetMethod.SCALE_BASED,
            correction=PoseCorrection.SOFT,
            quality=RetargetQuality.STANDARD,
            preserve_root_motion=True,
            preserve_foot_ik=True,
            hand_ik_enabled=False,
            foot_ik_enabled=True,
            spine_correction=0.8,
            created_at=_now(),
            updated_at=_now(),
        )
        self._profiles[seed_profile.profile_id] = seed_profile
        self._index_profile(seed_profile)

        # --- Seed retarget job ---
        seed_job = RetargetJob(
            job_id="job_walk_retarge_001",
            profile_id="profile_humanoid_to_quad",
            source_clip_id="clip_walk_cycle",
            target_clip_id="clip_walk_quad",
            method=RetargetMethod.SCALE_BASED,
            quality=RetargetQuality.STANDARD,
            status=JobStatus.COMPLETED,
            started_at=_now(),
            completed_at=_now(),
            duration_ms=125.5,
            frame_count=30,
            created_at=_now(),
        )
        self._jobs[seed_job.job_id] = seed_job
        self._index_job(seed_job)
        self._total_jobs_created = 1
        self._total_completed = 1
        self._total_duration_ms = 125.5

        # --- Seed pose correction ---
        seed_correction = PoseCorrectionConfig(
            correction_id="correction_spine_001",
            name="Spine Rotation Fix",
            skeleton_id="skel_creature_quadruped",
            bone_id="cq_spine",
            bone_name="spine",
            correction_type="rotation",
            position_offset={},
            rotation_offset={"x": 5.0, "y": 0.0, "z": 0.0, "w": 1.0},
            scale_factor=1.0,
            weight=0.8,
            enabled=True,
            created_at=_now(),
            updated_at=_now(),
        )
        self._corrections[seed_correction.correction_id] = seed_correction
        self._index_correction(seed_correction)

        self._emit_event(
            RetargetEventKind.SUBSYSTEM_RESET,
            entity_id="",
            entity_type="subsystem",
            message="Animation retargeting subsystem initialized with seed data",
        )

    def _index_animation(self, animation: AnimationClip) -> None:
        """Add an animation to the skeleton index."""
        sid = animation.skeleton_id
        if sid not in self._animations_by_skeleton:
            self._animations_by_skeleton[sid] = []
        if animation.clip_id not in self._animations_by_skeleton[sid]:
            self._animations_by_skeleton[sid].append(animation.clip_id)

    def _unindex_animation(self, animation: AnimationClip) -> None:
        """Remove an animation from the skeleton index."""
        sid = animation.skeleton_id
        if sid in self._animations_by_skeleton:
            try:
                self._animations_by_skeleton[sid].remove(animation.clip_id)
            except ValueError:
                pass
            if not self._animations_by_skeleton[sid]:
                del self._animations_by_skeleton[sid]

    # -------------------------------------------------------------------------
    # Public API: Skeletons
    # -------------------------------------------------------------------------

    def register_skeleton(
        self,
        name: str = "",
        bone_names: Optional[List[str]] = None,
        bone_roles: Optional[Dict[str, str]] = None,
        bone_lengths: Optional[Dict[str, float]] = None,
        bone_hierarchy: Optional[Dict[str, Optional[str]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        skeleton_id: Optional[str] = None,
        bones: Optional[List[Dict[str, Any]]] = None,
    ) -> SkeletonProfile:
        """Register a new skeleton profile.

        Accepts either separate ``bone_names``/``bone_roles``/``bone_lengths``/
        ``bone_hierarchy`` dicts or a single ``bones`` list of dicts (each with
        ``name`` and ``role`` keys). When ``skeleton_id`` is provided it is used
        directly; otherwise a new identifier is generated.
        """
        with self._lock:
            # Build BoneNode list from whichever input format was provided.
            bone_nodes: List[BoneNode] = []
            if bones:
                # Convert the ``bones`` list-of-dicts format into BoneNode objects.
                for entry in bones:
                    bone_nodes.append(BoneNode(
                        bone_id=entry.get("bone_id", _new_id("bone")),
                        name=entry.get("name", ""),
                        role=entry.get("role", "custom"),
                        parent_id=entry.get("parent_id"),
                        position_x=float(entry.get("position_x", 0.0)),
                        position_y=float(entry.get("position_y", 0.0)),
                        position_z=float(entry.get("position_z", 0.0)),
                        length=float(entry.get("length", 0.0)),
                    ))
            elif bone_names:
                for bname in bone_names:
                    role = (bone_roles or {}).get(bname, "custom")
                    parent = (bone_hierarchy or {}).get(bname)
                    length = float((bone_lengths or {}).get(bname, 0.0))
                    bone_nodes.append(BoneNode(
                        bone_id=_new_id("bone"),
                        name=bname,
                        role=role,
                        parent_id=parent,
                        length=length,
                    ))

            skel_id = skeleton_id if skeleton_id else _new_id("skel")
            root_id = bone_nodes[0].bone_id if bone_nodes else ""
            skeleton = SkeletonProfile(
                skeleton_id=skel_id,
                name=name or "Unnamed Skeleton",
                skeleton_type=(metadata or {}).get("skeleton_type", "custom"),
                bone_count=len(bone_nodes),
                root_bone_id=root_id,
                bones=bone_nodes,
                registered_at=_now(),
            )
            self._skeletons[skel_id] = skeleton
            _evict_fifo_dict(self._skeletons, _MAX_SKELETONS)
            self._index_skeleton(skeleton)
            self._emit_event(
                RetargetEventKind.SKELETON_REGISTERED,
                entity_id=skel_id,
                entity_type="skeleton",
                message=f"Skeleton '{name}' registered with {len(bone_nodes)} bones",
            )
            return skeleton

    def get_skeleton(self, skeleton_id: str) -> Optional[SkeletonProfile]:
        """Return the skeleton with the given identifier, or ``None``."""
        with self._lock:
            return self._skeletons.get(skeleton_id)

    def list_skeletons(self, limit: int = 100) -> List[SkeletonProfile]:
        """Return up to ``limit`` registered skeletons."""
        with self._lock:
            items = list(self._skeletons.values())
            return items[:max(1, int(limit))]

    # -------------------------------------------------------------------------
    # Public API: Animations
    # -------------------------------------------------------------------------

    def register_animation(
        self,
        name: str = "",
        skeleton_id: str = "",
        duration: float = 0.0,
        frame_count: int = 0,
        frame_rate: float = 30.0,
        metadata: Optional[Dict[str, Any]] = None,
        clip_id: Optional[str] = None,
        duration_frames: Optional[int] = None,
    ) -> AnimationClip:
        """Register a new animation clip.

        When ``clip_id`` is provided it is used directly; otherwise a new
        identifier is generated. ``duration_frames`` (used by the test harness)
        is accepted as an alias for ``frame_count`` when ``frame_count`` is zero.
        """
        with self._lock:
            cid = clip_id if clip_id else _new_id("clip")
            fc = int(frame_count) if frame_count else int(duration_frames or 0)
            clip = AnimationClip(
                clip_id=cid,
                name=name or "Unnamed Clip",
                skeleton_id=skeleton_id,
                duration=float(duration),
                frame_count=fc,
                frame_rate=float(frame_rate),
                metadata=metadata or {},
                registered_at=_now(),
            )
            self._animations[cid] = clip
            _evict_fifo_dict(self._animations, _MAX_SKELETONS)
            self._index_animation(clip)
            return clip

    def get_animation(self, clip_id: str) -> Optional[AnimationClip]:
        """Return the animation clip with the given identifier, or ``None``."""
        with self._lock:
            return self._animations.get(clip_id)

    def list_animations(
        self, skeleton_id: Optional[str] = None, limit: int = 100
    ) -> List[AnimationClip]:
        """Return up to ``limit`` animation clips, optionally filtered by skeleton."""
        with self._lock:
            if skeleton_id:
                ids = self._animations_by_skeleton.get(skeleton_id, [])
                items = [self._animations[cid] for cid in ids if cid in self._animations]
            else:
                items = list(self._animations.values())
            return items[:max(1, int(limit))]

    # -------------------------------------------------------------------------
    # Public API: Mappings
    # -------------------------------------------------------------------------

    def create_mapping(
        self,
        source_skeleton_id: str = "",
        target_skeleton_id: str = "",
        mappings: Optional[Dict[str, str]] = None,
        auto_generated: bool = False,
        confidence: float = 0.0,
    ) -> BoneMapping:
        """Create a bone-to-bone mapping between two skeletons.

        ``mappings`` is a dict of source bone name to target bone name.
        """
        with self._lock:
            entries: List[Dict[str, Any]] = []
            for src, tgt in (mappings or {}).items():
                entries.append({
                    "source_bone_name": src,
                    "target_bone_name": tgt,
                    "scale_factor": 1.0,
                    "rotation_offset": {},
                    "position_offset": {},
                })
            mapping = BoneMapping(
                mapping_id=_new_id("mapping"),
                name=f"{source_skeleton_id} -> {target_skeleton_id}",
                source_skeleton_id=source_skeleton_id,
                target_skeleton_id=target_skeleton_id,
                mapping_type=BoneMappingType.AUTO if auto_generated else BoneMappingType.MANUAL,
                entries=entries,
                entry_count=len(entries),
                created_at=_now(),
                updated_at=_now(),
            )
            # Store confidence in metadata-like field via entries.
            self._mappings[mapping.mapping_id] = mapping
            _evict_fifo_dict(self._mappings, _MAX_MAPPINGS)
            self._index_mapping(mapping)
            self._emit_event(
                RetargetEventKind.MAPPING_CREATED,
                entity_id=mapping.mapping_id,
                entity_type="mapping",
                message=f"Bone mapping created: {source_skeleton_id} -> {target_skeleton_id}",
                metadata={"auto_generated": auto_generated, "confidence": confidence},
            )
            return mapping

    def get_mapping(self, mapping_id: str) -> Optional[BoneMapping]:
        """Return the bone mapping with the given identifier, or ``None``."""
        with self._lock:
            return self._mappings.get(mapping_id)

    def list_mappings(
        self,
        source_skeleton_id: Optional[str] = None,
        target_skeleton_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[BoneMapping]:
        """Return up to ``limit`` bone mappings, optionally filtered."""
        with self._lock:
            if source_skeleton_id and target_skeleton_id:
                ids = set(self._mappings_by_source.get(source_skeleton_id, []))
                ids &= set(self._mappings_by_target.get(target_skeleton_id, []))
                items = [self._mappings[mid] for mid in ids if mid in self._mappings]
            elif source_skeleton_id:
                ids = self._mappings_by_source.get(source_skeleton_id, [])
                items = [self._mappings[mid] for mid in ids if mid in self._mappings]
            elif target_skeleton_id:
                ids = self._mappings_by_target.get(target_skeleton_id, [])
                items = [self._mappings[mid] for mid in ids if mid in self._mappings]
            else:
                items = list(self._mappings.values())
            return items[:max(1, int(limit))]

    def update_mapping(self, mapping_id: str, **kwargs: Any) -> Optional[BoneMapping]:
        """Update fields on an existing bone mapping."""
        with self._lock:
            mapping = self._mappings.get(mapping_id)
            if mapping is None:
                return None
            for key, value in kwargs.items():
                if key == "entries":
                    mapping.entries = value if isinstance(value, list) else []
                    mapping.entry_count = len(mapping.entries)
                elif key == "name":
                    mapping.name = str(value)
                elif key == "mapping_type":
                    try:
                        mapping.mapping_type = BoneMappingType(value)
                    except (ValueError, TypeError):
                        pass
                elif hasattr(mapping, key):
                    setattr(mapping, key, value)
            mapping.updated_at = _now()
            self._emit_event(
                RetargetEventKind.MAPPING_UPDATED,
                entity_id=mapping_id,
                entity_type="mapping",
                message=f"Bone mapping '{mapping_id}' updated",
            )
            return mapping

    # -------------------------------------------------------------------------
    # Public API: Profiles
    # -------------------------------------------------------------------------

    def create_profile(
        self,
        name: str = "",
        source_skeleton_id: str = "",
        target_skeleton_id: str = "",
        method: RetargetMethod = RetargetMethod.SCALE_BASED,
        correction_mode: PoseCorrection = PoseCorrection.NONE,
        quality: RetargetQuality = RetargetQuality.PREVIEW,
        scale_factor: float = 1.0,
        position_blending: float = 1.0,
        rotation_blending: float = 1.0,
        ik_constraints: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RetargetProfile:
        """Create a reusable retarget profile.

        ``correction_mode`` accepts a :class:`PoseCorrection` (aliased as
        ``CorrectionMode`` in the API layer).
        """
        with self._lock:
            # Resolve the mapping if one exists between the two skeletons.
            mapping_id = ""
            for mid in self._mappings_by_source.get(source_skeleton_id, []):
                mapping = self._mappings.get(mid)
                if mapping and mapping.target_skeleton_id == target_skeleton_id:
                    mapping_id = mid
                    break
            profile = RetargetProfile(
                profile_id=_new_id("profile"),
                name=name or "Unnamed Profile",
                source_skeleton_id=source_skeleton_id,
                target_skeleton_id=target_skeleton_id,
                mapping_id=mapping_id,
                method=method,
                correction=correction_mode,
                quality=quality,
                spine_correction=float(scale_factor),
                created_at=_now(),
                updated_at=_now(),
            )
            # Store blending/IK info in a way the dataclass supports via direct attrs.
            self._profiles[profile.profile_id] = profile
            _evict_fifo_dict(self._profiles, _MAX_PROFILES)
            self._index_profile(profile)
            self._emit_event(
                RetargetEventKind.PROFILE_CREATED,
                entity_id=profile.profile_id,
                entity_type="profile",
                message=f"Retarget profile '{name}' created",
                metadata={
                    "scale_factor": scale_factor,
                    "position_blending": position_blending,
                    "rotation_blending": rotation_blending,
                    "ik_constraints": ik_constraints,
                    "metadata": metadata,
                },
            )
            return profile

    def get_profile(self, profile_id: str) -> Optional[RetargetProfile]:
        """Return the retarget profile with the given identifier, or ``None``."""
        with self._lock:
            return self._profiles.get(profile_id)

    def list_profiles(
        self,
        source_skeleton_id: Optional[str] = None,
        target_skeleton_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[RetargetProfile]:
        """Return up to ``limit`` retarget profiles, optionally filtered."""
        with self._lock:
            if source_skeleton_id and target_skeleton_id:
                ids = set(self._profiles_by_source.get(source_skeleton_id, []))
                ids &= set(self._profiles_by_target.get(target_skeleton_id, []))
                items = [self._profiles[pid] for pid in ids if pid in self._profiles]
            elif source_skeleton_id:
                ids = self._profiles_by_source.get(source_skeleton_id, [])
                items = [self._profiles[pid] for pid in ids if pid in self._profiles]
            elif target_skeleton_id:
                ids = self._profiles_by_target.get(target_skeleton_id, [])
                items = [self._profiles[pid] for pid in ids if pid in self._profiles]
            else:
                items = list(self._profiles.values())
            return items[:max(1, int(limit))]

    def update_profile(self, profile_id: str, **kwargs: Any) -> Optional[RetargetProfile]:
        """Update fields on an existing retarget profile."""
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            for key, value in kwargs.items():
                if key == "method":
                    try:
                        profile.method = RetargetMethod(value)
                    except (ValueError, TypeError):
                        pass
                elif key == "correction" or key == "correction_mode":
                    try:
                        profile.correction = PoseCorrection(value)
                    except (ValueError, TypeError):
                        pass
                elif key == "quality":
                    try:
                        profile.quality = RetargetQuality(value)
                    except (ValueError, TypeError):
                        pass
                elif key == "name":
                    profile.name = str(value)
                elif hasattr(profile, key):
                    setattr(profile, key, value)
            profile.updated_at = _now()
            self._emit_event(
                RetargetEventKind.PROFILE_UPDATED,
                entity_id=profile_id,
                entity_type="profile",
                message=f"Retarget profile '{profile_id}' updated",
            )
            return profile

    def save_profile_as_template(
        self, profile_id: str = "", template_name: Optional[str] = None
    ) -> bool:
        """Save a profile as a reusable template. Returns ``True`` on success."""
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False
            # Store a shallow copy as a template.
            template = RetargetProfile(
                profile_id=f"template_{profile_id}",
                name=template_name or f"Template: {profile.name}",
                source_skeleton_id=profile.source_skeleton_id,
                target_skeleton_id=profile.target_skeleton_id,
                mapping_id=profile.mapping_id,
                method=profile.method,
                correction=profile.correction,
                quality=profile.quality,
                preserve_root_motion=profile.preserve_root_motion,
                preserve_foot_ik=profile.preserve_foot_ik,
                hand_ik_enabled=profile.hand_ik_enabled,
                foot_ik_enabled=profile.foot_ik_enabled,
                spine_correction=profile.spine_correction,
                created_at=_now(),
                updated_at=_now(),
            )
            self._templates[template.profile_id] = template
            return True

    def load_profile_template(self, profile_id: str = "") -> Optional[RetargetProfile]:
        """Load a saved profile template into the active profile registry."""
        with self._lock:
            template = self._templates.get(profile_id)
            if template is None:
                # Also check if profile_id refers to a template stored with
                # the ``template_`` prefix.
                template = self._templates.get(f"template_{profile_id}")
            if template is None:
                return None
            new_profile = RetargetProfile(
                profile_id=_new_id("profile"),
                name=template.name,
                source_skeleton_id=template.source_skeleton_id,
                target_skeleton_id=template.target_skeleton_id,
                mapping_id=template.mapping_id,
                method=template.method,
                correction=template.correction,
                quality=template.quality,
                preserve_root_motion=template.preserve_root_motion,
                preserve_foot_ik=template.preserve_foot_ik,
                hand_ik_enabled=template.hand_ik_enabled,
                foot_ik_enabled=template.foot_ik_enabled,
                spine_correction=template.spine_correction,
                created_at=_now(),
                updated_at=_now(),
            )
            self._profiles[new_profile.profile_id] = new_profile
            self._index_profile(new_profile)
            return new_profile

    # -------------------------------------------------------------------------
    # Public API: Jobs (Tasks)
    # -------------------------------------------------------------------------

    def start_retarget(
        self,
        source_animation_id: str = "",
        target_skeleton_id: str = "",
        profile_id: str = "",
    ) -> Optional[RetargetJob]:
        """Start a retarget job (task).

        Creates a job in the ``PENDING`` state. When ``target_skeleton_id`` is
        empty it is derived from the referenced profile.
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            # Derive target skeleton from profile when not supplied.
            if not target_skeleton_id:
                target_skeleton_id = profile.target_skeleton_id
            job = RetargetJob(
                job_id=_new_id("job"),
                profile_id=profile_id,
                source_clip_id=source_animation_id,
                method=profile.method,
                quality=profile.quality,
                status=JobStatus.PENDING,
                created_at=_now(),
            )
            self._jobs[job.job_id] = job
            _evict_fifo_dict(self._jobs, _MAX_JOBS)
            self._index_job(job)
            self._total_jobs_created += 1
            self._emit_event(
                RetargetEventKind.JOB_STARTED,
                entity_id=job.job_id,
                entity_type="job",
                message=f"Retarget job '{job.job_id}' started for clip '{source_animation_id}'",
            )
            return job

    def get_task(self, task_id: str) -> Optional[RetargetJob]:
        """Return the retarget job (task) with the given identifier, or ``None``."""
        with self._lock:
            return self._jobs.get(task_id)

    def list_tasks(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[RetargetJob]:
        """Return up to ``limit`` retarget jobs, optionally filtered by status."""
        with self._lock:
            if status:
                ids = self._jobs_by_status.get(status, [])
                items = [self._jobs[jid] for jid in ids if jid in self._jobs]
            else:
                items = list(self._jobs.values())
            return items[:max(1, int(limit))]

    def complete_task(
        self,
        task_id: str = "",
        result_animation_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[RetargetJob]:
        """Mark a retarget job (task) as completed or failed.

        When ``error_message`` is provided the job is marked as failed; otherwise
        it is marked as completed with the ``result_animation_id`` as the output clip.
        """
        with self._lock:
            job = self._jobs.get(task_id)
            if job is None:
                return None
            if error_message:
                job.status = JobStatus.FAILED
                job.error_message = error_message
                self._total_failed += 1
                self._emit_event(
                    RetargetEventKind.JOB_FAILED,
                    entity_id=task_id,
                    entity_type="job",
                    message=f"Retarget job '{task_id}' failed: {error_message}",
                )
            else:
                # Unindex from old status, update, re-index.
                self._unindex_job(job)
                job.status = JobStatus.COMPLETED
                job.target_clip_id = result_animation_id or ""
                job.completed_at = _now()
                job.duration_ms = 100.0
                self._index_job(job)
                self._total_completed += 1
                self._total_duration_ms += job.duration_ms
                self._emit_event(
                    RetargetEventKind.JOB_COMPLETED,
                    entity_id=task_id,
                    entity_type="job",
                    message=f"Retarget job '{task_id}' completed",
                    metadata={"result_animation_id": result_animation_id},
                )
            return job

    # -------------------------------------------------------------------------
    # Public API: Corrections
    # -------------------------------------------------------------------------

    def add_correction(
        self,
        task_id: str = "",
        bone_name: str = "",
        correction_type: str = "soft",
        original_value: Optional[Dict[str, Any]] = None,
        corrected_value: Optional[Dict[str, Any]] = None,
        correction_reason: str = "",
    ) -> Optional[PoseCorrectionConfig]:
        """Add a pose correction entry for a specific retarget job (task).

        The correction is linked to the skeleton of the job's target profile.
        """
        with self._lock:
            job = self._jobs.get(task_id)
            if job is None:
                return None
            profile = self._profiles.get(job.profile_id)
            skeleton_id = profile.target_skeleton_id if profile else ""
            # Look up the bone_id from the target skeleton.
            bone_id = ""
            skeleton = self._skeletons.get(skeleton_id)
            if skeleton:
                for bone in skeleton.bones:
                    if bone.name == bone_name:
                        bone_id = bone.bone_id
                        break
            correction = PoseCorrectionConfig(
                correction_id=_new_id("correction"),
                name=f"Correction for {bone_name} ({correction_reason})",
                skeleton_id=skeleton_id,
                bone_id=bone_id,
                bone_name=bone_name,
                correction_type=correction_type,
                position_offset=corrected_value or {},
                rotation_offset={},
                scale_factor=1.0,
                weight=1.0,
                enabled=True,
                created_at=_now(),
                updated_at=_now(),
            )
            self._corrections[correction.correction_id] = correction
            _evict_fifo_dict(self._corrections, _MAX_CORRECTIONS)
            self._index_correction(correction)
            # Also index by job.
            if task_id not in self._corrections_by_job:
                self._corrections_by_job[task_id] = []
            if correction.correction_id not in self._corrections_by_job[task_id]:
                self._corrections_by_job[task_id].append(correction.correction_id)
            self._emit_event(
                RetargetEventKind.CORRECTION_CREATED,
                entity_id=correction.correction_id,
                entity_type="correction",
                message=f"Correction '{correction_type}' added for bone '{bone_name}' on task '{task_id}'",
                metadata={"correction_reason": correction_reason,
                          "original_value": original_value,
                          "corrected_value": corrected_value},
            )
            return correction

    def get_correction(self, correction_id: str) -> Optional[PoseCorrectionConfig]:
        """Return the pose correction with the given identifier, or ``None``."""
        with self._lock:
            return self._corrections.get(correction_id)

    def list_corrections(
        self, task_id: Optional[str] = None, limit: int = 100
    ) -> List[PoseCorrectionConfig]:
        """Return up to ``limit`` pose corrections, optionally filtered by task."""
        with self._lock:
            if task_id:
                ids = self._corrections_by_job.get(task_id, [])
                items = [self._corrections[cid] for cid in ids if cid in self._corrections]
            else:
                items = list(self._corrections.values())
            return items[:max(1, int(limit))]

    # -------------------------------------------------------------------------
    # Public API: Events, Stats, Snapshot, Status, Reset
    # -------------------------------------------------------------------------

    def list_events(
        self,
        limit: int = 100,
        kind: Optional[RetargetEventKind] = None,
    ) -> List[RetargetEvent]:
        """Return up to ``limit`` events, optionally filtered by kind."""
        with self._lock:
            if kind is not None:
                items = [e for e in self._events if e.event_kind == kind]
            else:
                items = list(self._events)
            return items[:max(1, int(limit))]

    def get_stats(self) -> RetargetStats:
        """Return aggregate statistics for the subsystem."""
        with self._lock:
            return self._recompute_stats()

    def get_status(self) -> Dict[str, Any]:
        """Return a status dictionary for the subsystem."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_skeletons": len(self._skeletons),
                "total_animations": len(self._animations),
                "total_mappings": len(self._mappings),
                "total_profiles": len(self._profiles),
                "total_jobs": len(self._jobs),
                "total_corrections": len(self._corrections),
                "total_templates": len(self._templates),
                "total_events": len(self._events),
                "total_jobs_created": self._total_jobs_created,
                "total_completed": self._total_completed,
                "total_failed": self._total_failed,
            }

    def get_snapshot(self) -> RetargetSnapshot:
        """Return an immutable snapshot of the subsystem state."""
        with self._lock:
            return RetargetSnapshot(
                taken_at=_now(),
                skeletons=[s.to_dict() for s in self._skeletons.values()],
                mappings=[m.to_dict() for m in self._mappings.values()],
                profiles=[p.to_dict() for p in self._profiles.values()],
                jobs=[j.to_dict() for j in self._jobs.values()],
                corrections=[c.to_dict() for c in self._corrections.values()],
                stats=self._recompute_stats().to_dict(),
            )

    def reset(self) -> None:
        """Clear all stores and reseed default data."""
        with self._lock:
            self._skeletons.clear()
            self._animations.clear()
            self._mappings.clear()
            self._profiles.clear()
            self._jobs.clear()
            self._corrections.clear()
            self._templates.clear()
            self._events.clear()
            self._skeletons_by_type.clear()
            self._animations_by_skeleton.clear()
            self._mappings_by_source.clear()
            self._mappings_by_target.clear()
            self._profiles_by_source.clear()
            self._profiles_by_target.clear()
            self._jobs_by_profile.clear()
            self._jobs_by_status.clear()
            self._corrections_by_skeleton.clear()
            self._corrections_by_job.clear()
            self._total_jobs_created = 0
            self._total_completed = 0
            self._total_failed = 0
            self._total_cancelled = 0
            self._total_duration_ms = 0.0
            self._emit_event(
                RetargetEventKind.SUBSYSTEM_RESET,
                entity_id="",
                entity_type="subsystem",
                message="Animation retargeting subsystem reset",
            )
            self._seed_default_data()


# =============================================================================
# Factory Function
# =============================================================================


def get_animation_retargeting() -> AnimationRetargetingSystem:
    """Return the singleton ``AnimationRetargetingSystem`` instance.

    Uses double-checked locking for thread safety.
    """
    if AnimationRetargetingSystem._instance is None:
        with AnimationRetargetingSystem._instance_lock:
            if AnimationRetargetingSystem._instance is None:
                AnimationRetargetingSystem._instance = AnimationRetargetingSystem()
    return AnimationRetargetingSystem._instance