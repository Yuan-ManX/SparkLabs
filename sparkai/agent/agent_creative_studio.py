"""
SparkLabs Agent - AI Creative Studio

This module implements the AI Creative Studio for AI agents operating inside
the SparkLabs AI-native game engine. The studio coordinates multi-role
collaborative production of game content (concept art, characters, levels,
narrative, music, animation, mechanics) by simulating a small in-house
creative team.

The studio models a project through its lifecycle (IDEATION, DRAFTING,
REVIEW, REFINEMENT, FINALIZATION, PUBLISHING), tracks asset requests and
deliverables, gathers peer review verdicts, schedules milestones, and
records an observable event stream that downstream subsystems (game
intelligence hub, world synthesizer, content synthesis) can subscribe to.

Architecture:
  CreativeStudioEngine (Singleton, double-checked locking, threading.RLock)
    |-- CreativeProject       -- a multi-asset production project
    |-- AssetRequest          -- a single ask from one role for one asset
    |-- CreativeDeliverable   -- a delivered asset with versioning + score
    |-- ReviewRecord          -- a reviewer's verdict on a deliverable
    |-- Milestone             -- a dated checkpoint inside a project
    |-- StudioState           -- per-project state summary
    |-- StudioStats           -- aggregate studio statistics
    |-- StudioSnapshot        -- full engine snapshot
    |-- StudioEvent           -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the
engine is safe to call from multiple agent threads. Bounded in-memory
stores use FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_PROJECTS: int = 200
_MAX_ASSET_REQUESTS: int = 1000
_MAX_DELIVERABLES: int = 1000
_MAX_REVIEWS: int = 1000
_MAX_MILESTONES: int = 500
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return a UTC ISO-8601 timestamp string terminated with 'Z'."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id() -> str:
    """Generate a short unique identifier for a record."""
    return uuid.uuid4().hex[:16]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return float(value)


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds.

    Python dicts preserve insertion order (3.7+), so the first key returned
    by iteration is the oldest. This implements FIFO eviction.
    """
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a list until within bounds."""
    while len(store) > max_size:
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value to a JSON-friendly form.

    Enums become their string value, dataclasses become dicts (via this
    same function), lists and dicts are walked recursively, and anything
    else is returned as-is.
    """
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__") and not isinstance(value, type):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Convert a dataclass instance to a JSON-friendly dictionary.

    Enums are unwrapped to their string values, nested dataclasses and
    collections are walked recursively.
    """
    from dataclasses import fields, is_dataclass
    result: Dict[str, Any] = {}
    for fld in fields(instance):
        value = getattr(instance, fld.name)
        if is_dataclass(value) and not isinstance(value, type):
            result[fld.name] = _dataclass_to_dict(value)
        else:
            result[fld.name] = _to_jsonable(value)
    return result


def _resolve_role(value: Union[CreativeRole, str, None]) -> Optional[CreativeRole]:
    """Coerce a value into a :class:`CreativeRole` enum instance."""
    if value is None:
        return None
    if isinstance(value, CreativeRole):
        return value
    if isinstance(value, str):
        try:
            return CreativeRole(value)
        except ValueError:
            return None
    return None


def _resolve_phase(value: Union[CreativePhase, str, None]) -> Optional[CreativePhase]:
    """Coerce a value into a :class:`CreativePhase` enum instance."""
    if value is None:
        return None
    if isinstance(value, CreativePhase):
        return value
    if isinstance(value, str):
        try:
            return CreativePhase(value)
        except ValueError:
            return None
    return None


def _resolve_status(value: Union[CreativeStatus, str, None]) -> Optional[CreativeStatus]:
    """Coerce a value into a :class:`CreativeStatus` enum instance."""
    if value is None:
        return None
    if isinstance(value, CreativeStatus):
        return value
    if isinstance(value, str):
        try:
            return CreativeStatus(value)
        except ValueError:
            return None
    return None


def _resolve_asset_type(value: Union[AssetType, str, None]) -> Optional[AssetType]:
    """Coerce a value into an :class:`AssetType` enum instance."""
    if value is None:
        return None
    if isinstance(value, AssetType):
        return value
    if isinstance(value, str):
        try:
            return AssetType(value)
        except ValueError:
            return None
    return None


def _resolve_collaboration_mode(
    value: Union[CollaborationMode, str, None],
) -> Optional[CollaborationMode]:
    """Coerce a value into a :class:`CollaborationMode` enum instance."""
    if value is None:
        return None
    if isinstance(value, CollaborationMode):
        return value
    if isinstance(value, str):
        try:
            return CollaborationMode(value)
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CreativeRole(Enum):
    """A creative role inside the studio team."""
    DIRECTOR = "director"
    DESIGNER = "designer"
    ARTIST = "artist"
    WRITER = "writer"
    MUSICIAN = "musician"
    ANIMATOR = "animator"
    PROGRAMMER = "programmer"


class CreativePhase(Enum):
    """The lifecycle phase of a creative project."""
    IDEATION = "ideation"
    DRAFTING = "drafting"
    REVIEW = "review"
    REFINEMENT = "refinement"
    FINALIZATION = "finalization"
    PUBLISHING = "publishing"


class AssetType(Enum):
    """The kind of asset a project can produce."""
    CONCEPT_ART = "concept_art"
    CHARACTER_MODEL = "character_model"
    ENVIRONMENT = "environment"
    MUSIC = "music"
    VOICE = "voice"
    ANIMATION = "animation"
    DIALOGUE = "dialogue"
    LEVEL = "level"
    MECHANIC = "mechanic"
    NARRATIVE = "narrative"


class CreativeStatus(Enum):
    """The status of a project or asset request."""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    REVIEW_NEEDED = "review_needed"
    APPROVED = "approved"
    REJECTED = "rejected"
    RELEASED = "released"


class CollaborationMode(Enum):
    """How the studio team collaborates on a project."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PIPELINE = "pipeline"
    SWARM = "swarm"
    ITERATIVE = "iterative"


class StudioEventKind(Enum):
    """Observable lifecycle events emitted by the studio engine."""
    PROJECT_STARTED = "project_started"
    ASSET_REQUESTED = "asset_requested"
    ASSET_DELIVERED = "asset_delivered"
    REVIEW_COMPLETED = "review_completed"
    MILESTONE_REACHED = "milestone_reached"
    PROJECT_COMPLETED = "project_completed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CreativeProject:
    """A multi-asset creative production project."""
    id: str
    project_id: str
    name: str
    genre: str
    target_audience: str
    current_phase: CreativePhase
    status: CreativeStatus
    lead_role: CreativeRole
    collaborator_roles: List[CreativeRole]
    milestones: List[str]
    asset_requests: List[str]
    deliverables: List[str]
    started_at: str
    updated_at: str
    completed_at: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this project to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class AssetRequest:
    """A single request from a role for an asset of a given type."""
    id: str
    project_id: str
    requester_role: CreativeRole
    asset_type: AssetType
    specification: str
    priority: int
    deadline: str
    status: CreativeStatus
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this asset request to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class CreativeDeliverable:
    """A delivered asset with versioning, quality score, and feedback."""
    id: str
    project_id: str
    asset_type: AssetType
    contributor: str
    content: str
    version: int
    quality_score: float
    feedback: str
    delivered_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this deliverable to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class ReviewRecord:
    """A reviewer's verdict on a delivered asset."""
    id: str
    project_id: str
    deliverable_id: str
    reviewer: str
    verdict: str
    score: float
    notes: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this review record to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class Milestone:
    """A named checkpoint within a project."""
    id: str
    project_id: str
    name: str
    description: str
    target_date: str
    achieved_at: Optional[str]
    status: CreativeStatus

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this milestone to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class StudioState:
    """A per-project summary snapshot."""
    project_id: str
    total_projects: int
    total_assets: int
    total_reviews: int
    milestones_achieved: int
    active_projects: int
    last_activity: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this state to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class StudioStats:
    """Aggregate statistics about the creative studio engine."""
    total_projects: int
    total_assets: int
    total_reviews: int
    total_milestones: int
    projects_by_status: Dict[str, int]
    assets_by_type: Dict[str, int]
    average_quality: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


@dataclass
class StudioSnapshot:
    """A complete snapshot of the creative studio engine state."""
    initialized: bool
    projects: List[CreativeProject]
    events: List["StudioEvent"]
    stats: StudioStats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "initialized": self.initialized,
            "projects": [p.to_dict() for p in self.projects],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


@dataclass
class StudioEvent:
    """An observable lifecycle event emitted by the creative studio engine."""
    id: str
    kind: StudioEventKind
    project_id: str
    payload: Dict[str, Any]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Creative Studio Engine (Singleton with double-checked locking)
# ---------------------------------------------------------------------------


class CreativeStudioEngine:
    """Creative studio engine for AI game agents.

    The engine simulates a small creative studio inside the SparkLabs
    AI-native game engine. Each project moves through a sequence of
    phases (IDEATION -> ... -> PUBLISHING) and accumulates asset
    requests, deliverables, reviews, and milestones. Studio events are
    emitted at every meaningful step so other subsystems (the game
    intelligence hub, the world synthesizer, the content synthesis
    engine) can observe and react.

    It is a thread-safe singleton accessed via :meth:`get_instance` or
    the module-level :func:`get_creative_studio` helper.
    """

    _instance: Optional["CreativeStudioEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # -- Construction (double-checked locking) ---------------------------

    def __new__(cls) -> "CreativeStudioEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        # Fast path: already initialized singleton.
        if self._initialized:
            return
        with self._lock:
            # Second check inside the lock to guard against concurrent
            # construction.
            if self._initialized:
                return

            # Per-project stores keyed by project_id.
            self._projects: Dict[str, CreativeProject] = {}

            # Asset requests keyed by request id.
            self._asset_requests: Dict[str, AssetRequest] = {}

            # Deliverables keyed by deliverable id.
            self._deliverables: Dict[str, CreativeDeliverable] = {}

            # Review records keyed by review id.
            self._reviews: Dict[str, ReviewRecord] = {}

            # Milestones keyed by milestone id.
            self._milestones: Dict[str, Milestone] = {}

            # Observable lifecycle events.
            self._events: List[StudioEvent] = []

            # Monotonic counters for diagnostics.
            self._project_counter: int = 0
            self._asset_request_counter: int = 0
            self._deliverable_counter: int = 0
            self._review_counter: int = 0
            self._milestone_counter: int = 0

            self._initialized: bool = True

            # Seed baseline studio data.
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "CreativeStudioEngine":
        """Return the singleton CreativeStudioEngine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Project lifecycle
    # ------------------------------------------------------------------

    def start_project(
        self,
        name: str,
        genre: str,
        target_audience: str,
        lead_role: Union[CreativeRole, str],
    ) -> CreativeProject:
        """Start a new creative project.

        ``name`` is the project title, ``genre`` is the target game genre
        (e.g. ``"rpg"``, ``"platformer"``), ``target_audience`` is a
        short description of the intended players, and ``lead_role`` is
        the :class:`CreativeRole` that owns the project. Returns the
        newly created :class:`CreativeProject`.
        """
        with self._lock:
            resolved_lead = _resolve_role(lead_role) or CreativeRole.DIRECTOR
            now = _now()
            project_id = _new_id()
            project = CreativeProject(
                id=project_id,
                project_id=project_id,
                name=name or "Untitled Project",
                genre=genre or "generic",
                target_audience=target_audience or "general",
                current_phase=CreativePhase.IDEATION,
                status=CreativeStatus.PLANNED,
                lead_role=resolved_lead,
                collaborator_roles=[],
                milestones=[],
                asset_requests=[],
                deliverables=[],
                started_at=now,
                updated_at=now,
                completed_at=None,
                metadata={},
            )
            self._projects[project_id] = project
            self._project_counter += 1
            _evict_fifo_dict(self._projects, _MAX_PROJECTS)
            self._record_event(
                StudioEventKind.PROJECT_STARTED,
                project_id,
                {
                    "name": project.name,
                    "genre": project.genre,
                    "target_audience": project.target_audience,
                    "lead_role": resolved_lead.value,
                },
            )
            return project

    def add_collaborator(
        self,
        project_id: str,
        role: Union[CreativeRole, str],
    ) -> bool:
        """Add a collaborator role to a project.

        Returns ``True`` if the role was newly added, ``False`` if the
        project is missing, the role could not be resolved, or the role
        was already present (or equals the lead role).
        """
        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return False
            resolved = _resolve_role(role)
            if resolved is None:
                return False
            if resolved == project.lead_role:
                return False
            if resolved in project.collaborator_roles:
                return False
            project.collaborator_roles.append(resolved)
            project.updated_at = _now()
            return True

    def advance_phase(
        self,
        project_id: str,
        new_phase: Union[CreativePhase, str],
    ) -> bool:
        """Move a project to a new lifecycle phase.

        Returns ``True`` if the phase changed, ``False`` if the project
        is missing or the phase could not be resolved.
        """
        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return False
            resolved = _resolve_phase(new_phase)
            if resolved is None:
                return False
            if resolved == project.current_phase:
                return False
            project.current_phase = resolved
            project.updated_at = _now()
            if resolved == CreativePhase.PUBLISHING:
                project.status = CreativeStatus.RELEASED
                project.completed_at = project.updated_at
                self._record_event(
                    StudioEventKind.PROJECT_COMPLETED,
                    project_id,
                    {
                        "name": project.name,
                        "phase": resolved.value,
                    },
                )
            return True

    # ------------------------------------------------------------------
    # Asset request / deliver / review
    # ------------------------------------------------------------------

    def request_asset(
        self,
        project_id: str,
        requester_role: Union[CreativeRole, str],
        asset_type: Union[AssetType, str],
        specification: str,
        priority: int,
    ) -> Optional[AssetRequest]:
        """Create a new :class:`AssetRequest` for a project.

        ``requester_role`` is the role asking for the asset, ``asset_type``
        is the kind of asset, ``specification`` is a free-form brief, and
        ``priority`` is an integer in ``[1, 10]`` (clamped). Returns the
        new :class:`AssetRequest` or ``None`` if the project is missing
        or the arguments cannot be resolved.
        """
        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return None
            role = _resolve_role(requester_role)
            if role is None:
                role = project.lead_role
            resolved_type = _resolve_asset_type(asset_type)
            if resolved_type is None:
                return None
            now = _now()
            request = AssetRequest(
                id=_new_id(),
                project_id=project_id,
                requester_role=role,
                asset_type=resolved_type,
                specification=specification or "",
                priority=_clamp(float(priority), 1.0, 10.0),
                deadline=now,
                status=CreativeStatus.PLANNED,
                created_at=now,
            )
            self._asset_requests[request.id] = request
            self._asset_request_counter += 1
            _evict_fifo_dict(self._asset_requests, _MAX_ASSET_REQUESTS)
            project.asset_requests.append(request.id)
            project.status = CreativeStatus.IN_PROGRESS
            project.updated_at = now
            self._record_event(
                StudioEventKind.ASSET_REQUESTED,
                project_id,
                {
                    "request_id": request.id,
                    "requester_role": role.value,
                    "asset_type": resolved_type.value,
                    "priority": request.priority,
                },
            )
            return request

    def deliver_asset(
        self,
        request_id: str,
        contributor: str,
        content: str,
    ) -> Optional[CreativeDeliverable]:
        """Deliver an asset that fulfils a previous :class:`AssetRequest`.

        ``contributor`` is a free-form identifier for who produced the
        asset, and ``content`` is a short summary or stub payload for
        the asset body. The deliverable starts at version 1 with a
        neutral quality score; subsequent revisions increment the
        version. Returns the new :class:`CreativeDeliverable` or
        ``None`` if the request is missing.
        """
        with self._lock:
            request = self._asset_requests.get(request_id)
            if request is None:
                return None
            now = _now()
            project = self._projects.get(request.project_id)
            existing_versions = [
                d for d in self._deliverables.values()
                if d.project_id == request.project_id
                and d.asset_type == request.asset_type
                and d.contributor == (contributor or "")
            ]
            version = len(existing_versions) + 1
            deliverable = CreativeDeliverable(
                id=_new_id(),
                project_id=request.project_id,
                asset_type=request.asset_type,
                contributor=contributor or "anonymous",
                content=content or "",
                version=version,
                quality_score=0.5,
                feedback="",
                delivered_at=now,
            )
            self._deliverables[deliverable.id] = deliverable
            self._deliverable_counter += 1
            _evict_fifo_dict(self._deliverables, _MAX_DELIVERABLES)
            request.status = CreativeStatus.REVIEW_NEEDED
            if project is not None:
                project.deliverables.append(deliverable.id)
                project.current_phase = CreativePhase.REVIEW
                project.updated_at = now
            self._record_event(
                StudioEventKind.ASSET_DELIVERED,
                request.project_id,
                {
                    "request_id": request_id,
                    "deliverable_id": deliverable.id,
                    "contributor": deliverable.contributor,
                    "asset_type": request.asset_type.value,
                    "version": deliverable.version,
                },
            )
            return deliverable

    def review_deliverable(
        self,
        deliverable_id: str,
        reviewer: str,
        verdict: str,
        score: float,
        notes: str = "",
    ) -> Optional[ReviewRecord]:
        """Record a reviewer's verdict on a delivered asset.

        ``verdict`` is a free-form label (e.g. ``"approve"``,
        ``"reject"``, ``"revise"``), ``score`` is clamped to
        ``[0.0, 1.0]``. The deliverable's ``quality_score`` is updated
        to a weighted blend of its prior score and the review score.
        Returns the new :class:`ReviewRecord` or ``None`` if the
        deliverable is missing.
        """
        with self._lock:
            deliverable = self._deliverables.get(deliverable_id)
            if deliverable is None:
                return None
            now = _now()
            clamped_score = _clamp(float(score), 0.0, 1.0)
            review = ReviewRecord(
                id=_new_id(),
                project_id=deliverable.project_id,
                deliverable_id=deliverable_id,
                reviewer=reviewer or "anonymous",
                verdict=(verdict or "approve").strip().lower(),
                score=clamped_score,
                notes=notes or "",
                created_at=now,
            )
            self._reviews[review.id] = review
            self._review_counter += 1
            _evict_fifo_dict(self._reviews, _MAX_REVIEWS)
            previous = deliverable.quality_score
            deliverable.quality_score = round(
                (previous * 0.5) + (clamped_score * 0.5), 4
            )
            deliverable.feedback = notes or deliverable.feedback
            project = self._projects.get(deliverable.project_id)
            if project is not None:
                project.updated_at = now
            self._record_event(
                StudioEventKind.REVIEW_COMPLETED,
                deliverable.project_id,
                {
                    "deliverable_id": deliverable_id,
                    "reviewer": review.reviewer,
                    "verdict": review.verdict,
                    "score": review.score,
                    "quality_score": deliverable.quality_score,
                },
            )
            return review

    # ------------------------------------------------------------------
    # Milestones
    # ------------------------------------------------------------------

    def add_milestone(
        self,
        project_id: str,
        name: str,
        description: str,
        target_date: str,
    ) -> Optional[Milestone]:
        """Schedule a new milestone for a project.

        ``target_date`` is a free-form date string (e.g. ``"2026-09-01"``).
        Returns the new :class:`Milestone` or ``None`` if the project is
        missing.
        """
        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                return None
            milestone = Milestone(
                id=_new_id(),
                project_id=project_id,
                name=name or "Milestone",
                description=description or "",
                target_date=target_date or "",
                achieved_at=None,
                status=CreativeStatus.PLANNED,
            )
            self._milestones[milestone.id] = milestone
            self._milestone_counter += 1
            _evict_fifo_dict(self._milestones, _MAX_MILESTONES)
            project.milestones.append(milestone.id)
            project.updated_at = _now()
            return milestone

    def achieve_milestone(
        self,
        milestone_id: str,
    ) -> Optional[Milestone]:
        """Mark a milestone as achieved.

        Returns the updated :class:`Milestone` or ``None`` if the
        milestone is missing or was already achieved.
        """
        with self._lock:
            milestone = self._milestones.get(milestone_id)
            if milestone is None:
                return None
            if milestone.achieved_at is not None:
                return milestone
            now = _now()
            milestone.achieved_at = now
            milestone.status = CreativeStatus.APPROVED
            project = self._projects.get(milestone.project_id)
            if project is not None:
                project.updated_at = now
            self._record_event(
                StudioEventKind.MILESTONE_REACHED,
                milestone.project_id,
                {
                    "milestone_id": milestone.id,
                    "name": milestone.name,
                    "target_date": milestone.target_date,
                },
            )
            return milestone

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_projects(self) -> List[CreativeProject]:
        """Return all creative projects currently tracked."""
        with self._lock:
            return list(self._projects.values())

    def get_project(self, project_id: str) -> Optional[CreativeProject]:
        """Return a single project by id, or ``None`` if missing."""
        with self._lock:
            return self._projects.get(project_id)

    def get_asset_requests(
        self, project_id: str
    ) -> List[AssetRequest]:
        """Return all asset requests for a project, oldest first."""
        with self._lock:
            if project_id not in self._projects:
                return []
            return [
                self._asset_requests[rid]
                for rid in self._projects[project_id].asset_requests
                if rid in self._asset_requests
            ]

    def get_deliverables(
        self, project_id: str
    ) -> List[CreativeDeliverable]:
        """Return all deliverables for a project, oldest first."""
        with self._lock:
            if project_id not in self._projects:
                return []
            return [
                self._deliverables[did]
                for did in self._projects[project_id].deliverables
                if did in self._deliverables
            ]

    def get_reviews(
        self, project_id: str
    ) -> List[ReviewRecord]:
        """Return all review records for a project, oldest first."""
        with self._lock:
            if project_id not in self._projects:
                return []
            return [
                r for r in self._reviews.values()
                if r.project_id == project_id
            ]

    def get_milestones(
        self, project_id: str
    ) -> List[Milestone]:
        """Return all milestones for a project, oldest first."""
        with self._lock:
            if project_id not in self._projects:
                return []
            return [
                self._milestones[mid]
                for mid in self._projects[project_id].milestones
                if mid in self._milestones
            ]

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: StudioEventKind,
        project_id: str,
        payload: Dict[str, Any],
    ) -> None:
        """Record an observable studio event.

        Assumes the caller already holds ``self._lock``. The event log
        is bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = StudioEvent(
            id=_new_id(),
            kind=kind,
            project_id=project_id,
            payload=dict(payload) if payload else {},
            timestamp=_now(),
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, limit: int = 100) -> List[StudioEvent]:
        """Return the most recent studio events, newest first."""
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(self._events))[:n]

    def get_stats(self) -> StudioStats:
        """Return aggregate statistics about the creative studio engine."""
        with self._lock:
            total_assets = len(self._deliverables)
            total_reviews = len(self._reviews)
            total_milestones = len(self._milestones)
            projects_by_status: Dict[str, int] = {}
            assets_by_type: Dict[str, int] = {}
            quality_sum = 0.0
            for project in self._projects.values():
                projects_by_status[project.status.value] = (
                    projects_by_status.get(project.status.value, 0) + 1
                )
            for deliverable in self._deliverables.values():
                key = deliverable.asset_type.value
                assets_by_type[key] = assets_by_type.get(key, 0) + 1
                quality_sum += deliverable.quality_score
            average_quality = (
                round(quality_sum / total_assets, 4) if total_assets else 0.0
            )
            return StudioStats(
                total_projects=len(self._projects),
                total_assets=total_assets,
                total_reviews=total_reviews,
                total_milestones=total_milestones,
                projects_by_status=projects_by_status,
                assets_by_type=assets_by_type,
                average_quality=average_quality,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics.

        The first key is always ``"initialized"`` so callers can verify
        the singleton is alive.
        """
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "total_projects": stats.total_projects,
                "total_assets": stats.total_assets,
                "total_reviews": stats.total_reviews,
                "total_milestones": stats.total_milestones,
                "projects_by_status": stats.projects_by_status,
                "assets_by_type": stats.assets_by_type,
                "average_quality": stats.average_quality,
                "total_events": len(self._events),
                "project_counter": self._project_counter,
                "asset_request_counter": self._asset_request_counter,
                "deliverable_counter": self._deliverable_counter,
                "review_counter": self._review_counter,
                "milestone_counter": self._milestone_counter,
                "capacities": {
                    "max_projects": _MAX_PROJECTS,
                    "max_asset_requests": _MAX_ASSET_REQUESTS,
                    "max_deliverables": _MAX_DELIVERABLES,
                    "max_reviews": _MAX_REVIEWS,
                    "max_milestones": _MAX_MILESTONES,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> StudioSnapshot:
        """Return a complete snapshot of the creative studio engine state."""
        with self._lock:
            return StudioSnapshot(
                initialized=self._initialized,
                projects=list(self._projects.values()),
                events=list(self._events),
                stats=self.get_stats(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all tracked state and re-seed baseline data.

        Unlike a one-shot clear, ``reset`` re-seeds the baseline studio
        data so the engine returns to a freshly initialized state.
        """
        with self._lock:
            self._projects.clear()
            self._asset_requests.clear()
            self._deliverables.clear()
            self._reviews.clear()
            self._milestones.clear()
            self._events.clear()
            self._project_counter = 0
            self._asset_request_counter = 0
            self._deliverable_counter = 0
            self._review_counter = 0
            self._milestone_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline SparkLabs creative studio data.

        Seeds two projects (``Echoes of Aetheria`` -- an RPG led by a
        director, and ``Pixel Pulse Racers`` -- a platformer led by a
        designer), with asset requests, deliverables, reviews, and
        milestones to provide a useful out-of-the-box demo.
        """
        # --- Project 1: Echoes of Aetheria (RPG, director-led) --------
        rpg = self.start_project(
            name="Echoes of Aetheria",
            genre="rpg",
            target_audience="adults who enjoy story-rich fantasy",
            lead_role=CreativeRole.DIRECTOR,
        )
        self.add_collaborator(rpg.project_id, CreativeRole.WRITER)
        self.add_collaborator(rpg.project_id, CreativeRole.ARTIST)
        self.add_collaborator(rpg.project_id, CreativeRole.MUSICIAN)
        self.add_collaborator(rpg.project_id, CreativeRole.PROGRAMMER)

        rpg_req_story = self.request_asset(
            rpg.project_id,
            requester_role=CreativeRole.DIRECTOR,
            asset_type=AssetType.NARRATIVE,
            specification="Main storyline outline for the first act",
            priority=9,
        )
        rpg_req_art = self.request_asset(
            rpg.project_id,
            requester_role=CreativeRole.ARTIST,
            asset_type=AssetType.CONCEPT_ART,
            specification="Hero portrait and key environment paintings",
            priority=8,
        )
        rpg_req_music = self.request_asset(
            rpg.project_id,
            requester_role=CreativeRole.MUSICIAN,
            asset_type=AssetType.MUSIC,
            specification="Main theme and three regional leitmotifs",
            priority=7,
        )
        rpg_req_level = self.request_asset(
            rpg.project_id,
            requester_role=CreativeRole.DESIGNER,
            asset_type=AssetType.LEVEL,
            specification="Layout for the Aetheria Citadel hub",
            priority=6,
        )

        # Deliver and review the story outline.
        if rpg_req_story is not None:
            story = self.deliver_asset(
                rpg_req_story.id,
                contributor="writer_aelin",
                content=(
                    "Draft outline of Act I: arrival at the citadel, "
                    "first echo vision, council of mages meeting."
                ),
            )
            if story is not None:
                self.review_deliverable(
                    story.id,
                    reviewer="director_kade",
                    verdict="approve",
                    score=0.82,
                    notes="Strong opening; tighten the council scene.",
                )

        # Deliver the concept art and reject for revision.
        if rpg_req_art is not None:
            art = self.deliver_asset(
                rpg_req_art.id,
                contributor="artist_mira",
                content="Hero portrait v1 and two citadel paintings.",
            )
            if art is not None:
                self.review_deliverable(
                    art.id,
                    reviewer="director_kade",
                    verdict="revise",
                    score=0.55,
                    notes="Hero portrait needs a more weathered look.",
                )

        # Schedule and achieve the first milestone.
        alpha_ms = self.add_milestone(
            rpg.project_id,
            name="Vertical slice",
            description="First playable slice covering Act I intro",
            target_date="2026-09-15",
        )
        if alpha_ms is not None:
            self.achieve_milestone(alpha_ms.id)

        # Advance the project to refinement.
        self.advance_phase(rpg.project_id, CreativePhase.DRAFTING)
        self.advance_phase(rpg.project_id, CreativePhase.REVIEW)

        # --- Project 2: Pixel Pulse Racers (platformer, designer-led)
        platformer = self.start_project(
            name="Pixel Pulse Racers",
            genre="platformer",
            target_audience="teens and casual players",
            lead_role=CreativeRole.DESIGNER,
        )
        self.add_collaborator(platformer.project_id, CreativeRole.ANIMATOR)
        self.add_collaborator(platformer.project_id, CreativeRole.ARTIST)
        self.add_collaborator(platformer.project_id, CreativeRole.MUSICIAN)

        plat_req_char = self.request_asset(
            platformer.project_id,
            requester_role=CreativeRole.DESIGNER,
            asset_type=AssetType.CHARACTER_MODEL,
            specification="Three racer characters with distinct silhouettes",
            priority=8,
        )
        plat_req_track = self.request_asset(
            platformer.project_id,
            requester_role=CreativeRole.DESIGNER,
            asset_type=AssetType.LEVEL,
            specification="Neon Speedway track with three shortcuts",
            priority=7,
        )

        if plat_req_char is not None:
            char = self.deliver_asset(
                plat_req_char.id,
                contributor="artist_neo",
                content="Racer models for Velo, Glitch, and Drift-Kit.",
            )
            if char is not None:
                self.review_deliverable(
                    char.id,
                    reviewer="designer_kai",
                    verdict="approve",
                    score=0.74,
                    notes="Silhouettes read well; tweak Velo's helmet.",
                )

        beat_ms = self.add_milestone(
            platformer.project_id,
            name="Prototype demo",
            description="Internal demo with two playable tracks",
            target_date="2026-08-30",
        )
        if beat_ms is not None:
            self.achieve_milestone(beat_ms.id)

        self.advance_phase(platformer.project_id, CreativePhase.DRAFTING)


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_creative_studio() -> CreativeStudioEngine:
    """Return the singleton CreativeStudioEngine instance."""
    return CreativeStudioEngine.get_instance()
