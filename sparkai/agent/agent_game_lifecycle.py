"""
SparkLabs Agent - Game Lifecycle Management

Comprehensive lifecycle management for AI-native games. Tracks the full journey
of a game from conception through retirement: state transitions across discrete
lifecycle stages, versioning across deployment channels, milestone recording,
post-launch evolution, and graceful sunset.

The lifecycle is modeled as a finite state machine over `GameLifecycleState`
values, with explicit transition rules enforced by `GameLifecycleManager`.
Versioning follows a promotion ladder (INTERNAL -> CANARY -> STAGING ->
PRODUCTION) with first-class rollback support.

Architecture:
  GameLifecycleManager (singleton, RLock-guarded)
    |-- GameLifecycleState (lifecycle stage of a game)
    |-- TransitionTrigger  (why a transition occurred)
    |-- VersionChannel    (deployment channel for a release)
    |-- LifecyclePhase    (coarse-grained lifecycle phase for analytics)
    |-- LifecycleConfig   (per-game lifecycle configuration)
    |-- GameLifecycleRecord (canonical record for a tracked game)
    |-- StateTransition   (audit entry for a state change)
    |-- VersionRelease    (audit entry for a version release)
    |-- LifecycleMetrics  (aggregate metrics across the system)
    |-- LifecycleSnapshot (point-in-time system snapshot)

Lifecycle Flow:
  CONCEPTION -> PROTOTYPING -> DEVELOPMENT -> ALPHA -> BETA
            -> CERTIFICATION -> RELEASED -> LIVE_OPS -> SUNSET -> ARCHIVED
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GameLifecycleState(Enum):
    """Discrete stages in a game's lifecycle."""
    CONCEPTION = "conception"
    PROTOTYPING = "prototyping"
    DEVELOPMENT = "development"
    ALPHA = "alpha"
    BETA = "beta"
    CERTIFICATION = "certification"
    RELEASED = "released"
    LIVE_OPS = "live_ops"
    SUNSET = "sunset"
    ARCHIVED = "archived"


class TransitionTrigger(Enum):
    """Reasons that a lifecycle state transition may be initiated."""
    MANUAL = "manual"
    AUTO_MILESTONE = "auto_milestone"
    QUALITY_GATE = "quality_gate"
    USER_REQUEST = "user_request"
    SCHEDULE = "schedule"
    CRITICAL_ISSUE = "critical_issue"


class VersionChannel(Enum):
    """Deployment channels that a version release may target."""
    INTERNAL = "internal"
    CANARY = "canary"
    STAGING = "staging"
    PRODUCTION = "production"
    ROLLBACK = "rollback"


class LifecyclePhase(Enum):
    """Coarse-grained lifecycle phases used for analytics and grouping."""
    PLANNING = "planning"
    CREATION = "creation"
    ITERATION = "iteration"
    VALIDATION = "validation"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    EVOLUTION = "evolution"
    RETIREMENT = "retirement"


# ---------------------------------------------------------------------------
# Transition / promotion rules
# ---------------------------------------------------------------------------


# Valid forward and lateral transitions between lifecycle states.
VALID_STATE_TRANSITIONS: Dict[GameLifecycleState, Set[GameLifecycleState]] = {
    GameLifecycleState.CONCEPTION: {
        GameLifecycleState.PROTOTYPING,
        GameLifecycleState.DEVELOPMENT,
        GameLifecycleState.ARCHIVED,
    },
    GameLifecycleState.PROTOTYPING: {
        GameLifecycleState.DEVELOPMENT,
        GameLifecycleState.CONCEPTION,
        GameLifecycleState.ARCHIVED,
    },
    GameLifecycleState.DEVELOPMENT: {
        GameLifecycleState.ALPHA,
        GameLifecycleState.PROTOTYPING,
        GameLifecycleState.ARCHIVED,
    },
    GameLifecycleState.ALPHA: {
        GameLifecycleState.BETA,
        GameLifecycleState.DEVELOPMENT,
        GameLifecycleState.ARCHIVED,
    },
    GameLifecycleState.BETA: {
        GameLifecycleState.CERTIFICATION,
        GameLifecycleState.ALPHA,
        GameLifecycleState.ARCHIVED,
    },
    GameLifecycleState.CERTIFICATION: {
        GameLifecycleState.RELEASED,
        GameLifecycleState.BETA,
        GameLifecycleState.ARCHIVED,
    },
    GameLifecycleState.RELEASED: {
        GameLifecycleState.LIVE_OPS,
        GameLifecycleState.SUNSET,
        GameLifecycleState.ARCHIVED,
    },
    GameLifecycleState.LIVE_OPS: {
        GameLifecycleState.SUNSET,
        GameLifecycleState.RELEASED,
        GameLifecycleState.ARCHIVED,
    },
    GameLifecycleState.SUNSET: {
        GameLifecycleState.ARCHIVED,
        GameLifecycleState.LIVE_OPS,
    },
    GameLifecycleState.ARCHIVED: set(),  # terminal state
}

# Ordered promotion ladder for version channels.
CHANNEL_PROMOTION_ORDER: List[VersionChannel] = [
    VersionChannel.INTERNAL,
    VersionChannel.CANARY,
    VersionChannel.STAGING,
    VersionChannel.PRODUCTION,
]

# Maps a lifecycle state to the coarse-grained phase used in analytics.
STATE_PHASE_MAPPING: Dict[GameLifecycleState, LifecyclePhase] = {
    GameLifecycleState.CONCEPTION: LifecyclePhase.PLANNING,
    GameLifecycleState.PROTOTYPING: LifecyclePhase.CREATION,
    GameLifecycleState.DEVELOPMENT: LifecyclePhase.CREATION,
    GameLifecycleState.ALPHA: LifecyclePhase.ITERATION,
    GameLifecycleState.BETA: LifecyclePhase.VALIDATION,
    GameLifecycleState.CERTIFICATION: LifecyclePhase.VALIDATION,
    GameLifecycleState.RELEASED: LifecyclePhase.DEPLOYMENT,
    GameLifecycleState.LIVE_OPS: LifecyclePhase.MONITORING,
    GameLifecycleState.SUNSET: LifecyclePhase.RETIREMENT,
    GameLifecycleState.ARCHIVED: LifecyclePhase.RETIREMENT,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class LifecycleConfig:
    """Configuration that governs lifecycle behavior for a single game."""
    auto_milestones: bool = True
    quality_gate_required: bool = True
    min_quality_score: float = 0.7
    max_version_history: int = 50
    enable_canary: bool = True
    certification_required: bool = True
    sunset_grace_period_days: int = 30

    def to_dict(self) -> Dict[str, Any]:
        return {
            "auto_milestones": self.auto_milestones,
            "quality_gate_required": self.quality_gate_required,
            "min_quality_score": self.min_quality_score,
            "max_version_history": self.max_version_history,
            "enable_canary": self.enable_canary,
            "certification_required": self.certification_required,
            "sunset_grace_period_days": self.sunset_grace_period_days,
        }


@dataclass
class StateTransition:
    """Audit record for a single lifecycle state transition."""
    transition_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    game_id: str = ""
    from_state: GameLifecycleState = GameLifecycleState.CONCEPTION
    to_state: GameLifecycleState = GameLifecycleState.CONCEPTION
    trigger: TransitionTrigger = TransitionTrigger.MANUAL
    notes: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "game_id": self.game_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "trigger": self.trigger.value,
            "notes": self.notes,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class VersionRelease:
    """Audit record for a version release on a deployment channel."""
    version_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    game_id: str = ""
    version_label: str = ""
    channel: VersionChannel = VersionChannel.INTERNAL
    changelog: str = ""
    created_at: float = field(default_factory=time.time)
    promoted_at: float = 0.0
    active: bool = True
    rollback_of: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "game_id": self.game_id,
            "version_label": self.version_label,
            "channel": self.channel.value,
            "changelog": self.changelog,
            "created_at": self.created_at,
            "promoted_at": self.promoted_at,
            "active": self.active,
            "rollback_of": self.rollback_of,
        }


@dataclass
class GameLifecycleRecord:
    """Complete lifecycle record for a tracked game."""
    game_id: str = ""
    title: str = ""
    state: GameLifecycleState = GameLifecycleState.CONCEPTION
    phase: LifecyclePhase = LifecyclePhase.PLANNING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    current_version: Optional[str] = None
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    config: LifecycleConfig = field(default_factory=LifecycleConfig)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "title": self.title,
            "state": self.state.value,
            "phase": self.phase.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_version": self.current_version,
            "milestones": list(self.milestones),
            "config": self.config.to_dict(),
        }


@dataclass
class LifecycleMetrics:
    """Aggregate metrics across all tracked games."""
    total_transitions: int = 0
    total_versions: int = 0
    rollback_count: int = 0
    by_state: Dict[str, int] = field(default_factory=dict)
    by_channel: Dict[str, int] = field(default_factory=dict)
    by_phase: Dict[str, int] = field(default_factory=dict)
    avg_versions_per_game: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_transitions": self.total_transitions,
            "total_versions": self.total_versions,
            "rollback_count": self.rollback_count,
            "by_state": dict(self.by_state),
            "by_channel": dict(self.by_channel),
            "by_phase": dict(self.by_phase),
            "avg_versions_per_game": self.avg_versions_per_game,
        }


@dataclass
class LifecycleSnapshot:
    """Point-in-time snapshot of the entire lifecycle system."""
    timestamp: float = field(default_factory=time.time)
    total_games: int = 0
    total_transitions: int = 0
    total_versions: int = 0
    metrics: LifecycleMetrics = field(default_factory=LifecycleMetrics)
    games_by_state: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_games": self.total_games,
            "total_transitions": self.total_transitions,
            "total_versions": self.total_versions,
            "metrics": self.metrics.to_dict(),
            "games_by_state": dict(self.games_by_state),
        }


# ---------------------------------------------------------------------------
# GameLifecycleManager Singleton
# ---------------------------------------------------------------------------


class GameLifecycleManager:
    """
    Central lifecycle manager for SparkLabs games.

    Tracks each registered game through its lifecycle state machine, records
    every transition for audit purposes, manages version releases across
    deployment channels with promotion and rollback support, and aggregates
    lifecycle metrics for observability.

    All state mutations are serialized through a single reentrant lock so the
    in-memory registries stay consistent under concurrent access.
    """

    _instance: Optional["GameLifecycleManager"] = None
    _lock = threading.RLock()

    # Cap on retained transition history per game to bound memory usage.
    MAX_TRANSITION_HISTORY_PER_GAME = 200

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "GameLifecycleManager":
        """Get the singleton instance with double-checked locking.

        Returns:
            The single shared GameLifecycleManager instance.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._games: Dict[str, GameLifecycleRecord] = {}
        self._transitions: Dict[str, List[StateTransition]] = {}
        self._versions: Dict[str, List[VersionRelease]] = {}
        self._active_versions: Dict[str, str] = {}  # game_id -> version_id
        self._initialized: bool = False
        self._started_at: float = time.time()
        self._instance_lock = threading.RLock()

    def initialize(self) -> None:
        """Initialize the lifecycle manager and mark it ready for use."""
        with self._instance_lock:
            if self._initialized:
                return
            self._initialized = True
            self._started_at = time.time()

    # ------------------------------------------------------------------
    # Internal helpers (callers must already hold the lock)
    # ------------------------------------------------------------------

    def _require_game(self, game_id: str) -> GameLifecycleRecord:
        record = self._games.get(game_id)
        if record is None:
            raise ValueError(f"Game '{game_id}' is not registered for lifecycle tracking")
        return record

    def _record_transition(
        self,
        game_id: str,
        from_state: GameLifecycleState,
        to_state: GameLifecycleState,
        trigger: TransitionTrigger,
        notes: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StateTransition:
        transition = StateTransition(
            game_id=game_id,
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            notes=notes,
            metadata=dict(metadata or {}),
        )
        history = self._transitions.setdefault(game_id, [])
        history.append(transition)
        # Bound the per-game transition history to prevent unbounded growth.
        if len(history) > self.MAX_TRANSITION_HISTORY_PER_GAME:
            del history[: len(history) - self.MAX_TRANSITION_HISTORY_PER_GAME]
        return transition

    def _trim_version_history(self, game_id: str, limit: int) -> None:
        versions = self._versions.get(game_id, [])
        if len(versions) > limit:
            # Preserve the most recent `limit` entries; never drop the active
            # version even if it falls outside the window.
            active_id = self._active_versions.get(game_id)
            kept = versions[-limit:]
            if active_id and not any(v.version_id == active_id for v in kept):
                active_version = next(
                    (v for v in versions if v.version_id == active_id), None
                )
                if active_version is not None:
                    kept.insert(0, active_version)
            self._versions[game_id] = kept

    @staticmethod
    def _channel_rank(channel: VersionChannel) -> int:
        try:
            return CHANNEL_PROMOTION_ORDER.index(channel)
        except ValueError:
            # ROLLBACK is not part of the promotion ladder; treat it as the
            # highest rank so promotion validation still works as expected.
            return len(CHANNEL_PROMOTION_ORDER)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_game(
        self,
        game_id: str,
        config: Optional[LifecycleConfig] = None,
    ) -> GameLifecycleRecord:
        """Register a new game for lifecycle tracking.

        Args:
            game_id: Unique identifier for the game.
            config: Optional lifecycle configuration. Defaults are used when omitted.

        Returns:
            The newly created GameLifecycleRecord.

        Raises:
            ValueError: If the game_id is already registered.
        """
        with self._instance_lock:
            if not game_id:
                raise ValueError("game_id must be a non-empty string")
            if game_id in self._games:
                raise ValueError(f"Game '{game_id}' is already registered")
            record = GameLifecycleRecord(
                game_id=game_id,
                title=game_id,
                state=GameLifecycleState.CONCEPTION,
                phase=STATE_PHASE_MAPPING[GameLifecycleState.CONCEPTION],
                config=config or LifecycleConfig(),
            )
            self._games[game_id] = record
            self._transitions[game_id] = []
            self._versions[game_id] = []
            # Seed the transition history with the initial conception state.
            self._record_transition(
                game_id,
                GameLifecycleState.CONCEPTION,
                GameLifecycleState.CONCEPTION,
                TransitionTrigger.MANUAL,
                "Game registered for lifecycle tracking",
                metadata={"initial": True},
            )
            return record

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def transition_state(
        self,
        game_id: str,
        target_state: GameLifecycleState,
        trigger: TransitionTrigger = TransitionTrigger.MANUAL,
        notes: str = "",
    ) -> StateTransition:
        """Transition a game to a new lifecycle state.

        Args:
            game_id: Identifier of the game to transition.
            target_state: Desired lifecycle state.
            trigger: What initiated the transition.
            notes: Optional human-readable notes for the audit record.

        Returns:
            The recorded StateTransition.

        Raises:
            ValueError: If the game is unknown or the transition is invalid.
        """
        with self._instance_lock:
            record = self._require_game(game_id)
            current_state = record.state
            if current_state == target_state:
                # No-op transition still produces an audit record so observers
                # can see that the request was made.
                return self._record_transition(
                    game_id,
                    current_state,
                    target_state,
                    trigger,
                    notes or f"Already in {target_state.value}",
                    metadata={"no_op": True},
                )
            allowed = VALID_STATE_TRANSITIONS.get(current_state, set())
            if target_state not in allowed:
                raise ValueError(
                    f"Invalid state transition: {current_state.value} -> {target_state.value}"
                )
            # Enforce certification gating when configured by the game.
            if (
                target_state == GameLifecycleState.RELEASED
                and record.config.certification_required
                and current_state != GameLifecycleState.CERTIFICATION
            ):
                raise ValueError(
                    "RELEASED state requires prior CERTIFICATION when certification_required is set"
                )
            record.state = target_state
            record.phase = STATE_PHASE_MAPPING.get(target_state, record.phase)
            record.updated_at = time.time()
            return self._record_transition(
                game_id,
                current_state,
                target_state,
                trigger,
                notes,
                metadata={"phase": record.phase.value},
            )

    # ------------------------------------------------------------------
    # Version management
    # ------------------------------------------------------------------

    def create_version(
        self,
        game_id: str,
        channel: VersionChannel = VersionChannel.INTERNAL,
        changelog: str = "",
    ) -> VersionRelease:
        """Create a new version release for a game.

        Args:
            game_id: Identifier of the game.
            channel: Deployment channel for the release. ROLLBACK is not permitted here.
            changelog: Human-readable summary of changes in this release.

        Returns:
            The newly created VersionRelease.

        Raises:
            ValueError: If the game is unknown or the channel is invalid.
        """
        if channel == VersionChannel.ROLLBACK:
            raise ValueError("ROLLBACK channel is reserved for rollback_version()")
        with self._instance_lock:
            record = self._require_game(game_id)
            if channel == VersionChannel.CANARY and not record.config.enable_canary:
                raise ValueError("Canary channel is disabled for this game")
            version_index = len(self._versions.get(game_id, [])) + 1
            version_label = f"v{version_index}"
            release = VersionRelease(
                game_id=game_id,
                version_label=version_label,
                channel=channel,
                changelog=changelog,
            )
            self._versions.setdefault(game_id, []).append(release)
            # First release on a channel automatically becomes the active one.
            if self._active_versions.get(game_id) is None:
                self._active_versions[game_id] = release.version_id
                record.current_version = release.version_label
                record.updated_at = time.time()
            self._trim_version_history(game_id, record.config.max_version_history)
            return release

    def promote_version(
        self,
        game_id: str,
        version_id: str,
        target_channel: VersionChannel,
    ) -> VersionRelease:
        """Promote an existing version release to a higher-rank channel.

        Args:
            game_id: Identifier of the game.
            version_id: Identifier of the version release to promote.
            target_channel: Channel to promote the release to.

        Returns:
            The updated VersionRelease.

        Raises:
            ValueError: If the game/version is unknown, the target channel is
                invalid, or the promotion is not a forward step.
        """
        if target_channel == VersionChannel.ROLLBACK:
            raise ValueError("Cannot promote to the ROLLBACK channel")
        with self._instance_lock:
            record = self._require_game(game_id)
            versions = self._versions.get(game_id, [])
            release = next((v for v in versions if v.version_id == version_id), None)
            if release is None:
                raise ValueError(f"Version '{version_id}' not found for game '{game_id}'")
            if release.channel == target_channel:
                # Idempotent promotion is treated as a no-op refresh.
                release.promoted_at = time.time()
                return release
            current_rank = self._channel_rank(release.channel)
            target_rank = self._channel_rank(target_channel)
            if target_rank < current_rank:
                raise ValueError(
                    f"Cannot demote version from {release.channel.value} to {target_channel.value}; "
                    "use rollback_version() instead"
                )
            release.channel = target_channel
            release.promoted_at = time.time()
            # Promoting to production flips the active pointer.
            if target_channel == VersionChannel.PRODUCTION:
                self._active_versions[game_id] = release.version_id
                record.current_version = release.version_label
                record.updated_at = time.time()
            return release

    def rollback_version(
        self,
        game_id: str,
        target_version_id: str,
    ) -> VersionRelease:
        """Rollback a game to a previous version release.

        Marks the currently active release as inactive and activates the
        target release. A new VersionRelease with channel=ROLLBACK is
        recorded for audit purposes and points back to the target release.

        Args:
            game_id: Identifier of the game.
            target_version_id: Identifier of the version release to roll back to.

        Returns:
            The newly created rollback VersionRelease.

        Raises:
            ValueError: If the game or target version is unknown, or the
                target version is not currently inactive.
        """
        with self._instance_lock:
            record = self._require_game(game_id)
            versions = self._versions.get(game_id, [])
            target = next(
                (v for v in versions if v.version_id == target_version_id), None
            )
            if target is None:
                raise ValueError(
                    f"Version '{target_version_id}' not found for game '{game_id}'"
                )
            active_id = self._active_versions.get(game_id)
            if active_id == target_version_id:
                raise ValueError("Cannot roll back to the currently active version")
            # Deactivate the previously active release.
            if active_id:
                previous = next(
                    (v for v in versions if v.version_id == active_id), None
                )
                if previous is not None:
                    previous.active = False
            target.active = True
            self._active_versions[game_id] = target.version_id
            record.current_version = target.version_label
            record.updated_at = time.time()
            # Record an audit entry for the rollback operation.
            rollback_release = VersionRelease(
                game_id=game_id,
                version_label=f"{target.version_label}-rollback",
                channel=VersionChannel.ROLLBACK,
                changelog=f"Rolled back to {target.version_label}",
                rollback_of=target.version_id,
            )
            rollback_release.active = False  # the rollback record itself is not active
            self._versions.setdefault(game_id, []).append(rollback_release)
            self._trim_version_history(game_id, record.config.max_version_history)
            return rollback_release

    # ------------------------------------------------------------------
    # Milestones
    # ------------------------------------------------------------------

    def record_milestone(
        self,
        game_id: str,
        milestone: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a lifecycle milestone for a game.

        Args:
            game_id: Identifier of the game.
            milestone: Name of the milestone (e.g. "first_playable", "store_submission").
            data: Optional metadata associated with the milestone.

        Returns:
            The recorded milestone dictionary.

        Raises:
            ValueError: If the game is unknown.
        """
        with self._instance_lock:
            record = self._require_game(game_id)
            entry: Dict[str, Any] = {
                "milestone_id": uuid.uuid4().hex[:12],
                "name": milestone,
                "data": dict(data or {}),
                "state": record.state.value,
                "phase": record.phase.value,
                "timestamp": time.time(),
            }
            record.milestones.append(entry)
            record.updated_at = entry["timestamp"]
            return entry

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_lifecycle_record(self, game_id: str) -> Optional[GameLifecycleRecord]:
        """Get the complete lifecycle record for a game."""
        with self._instance_lock:
            return self._games.get(game_id)

    def get_transition_history(self, game_id: str) -> List[StateTransition]:
        """Get all recorded state transitions for a game, oldest first."""
        with self._instance_lock:
            return list(self._transitions.get(game_id, []))

    def get_version_history(self, game_id: str) -> List[VersionRelease]:
        """Get all version releases for a game, oldest first."""
        with self._instance_lock:
            return list(self._versions.get(game_id, []))

    def get_active_version(self, game_id: str) -> Optional[VersionRelease]:
        """Get the currently active version release for a game, if any."""
        with self._instance_lock:
            active_id = self._active_versions.get(game_id)
            if not active_id:
                return None
            versions = self._versions.get(game_id, [])
            return next((v for v in versions if v.version_id == active_id), None)

    # ------------------------------------------------------------------
    # Aggregate status / metrics
    # ------------------------------------------------------------------

    def _compute_metrics(self) -> LifecycleMetrics:
        """Compute aggregate metrics across all tracked games."""
        by_state: Dict[str, int] = {}
        by_channel: Dict[str, int] = {}
        by_phase: Dict[str, int] = {}
        rollback_count = 0
        total_versions = 0
        for record in self._games.values():
            by_state[record.state.value] = by_state.get(record.state.value, 0) + 1
            by_phase[record.phase.value] = by_phase.get(record.phase.value, 0) + 1
        for game_id, versions in self._versions.items():
            total_versions += len(versions)
            for v in versions:
                by_channel[v.channel.value] = by_channel.get(v.channel.value, 0) + 1
                if v.channel == VersionChannel.ROLLBACK:
                    rollback_count += 1
        total_transitions = sum(len(t) for t in self._transitions.values())
        avg_versions = (total_versions / len(self._games)) if self._games else 0.0
        return LifecycleMetrics(
            total_transitions=total_transitions,
            total_versions=total_versions,
            rollback_count=rollback_count,
            by_state=by_state,
            by_channel=by_channel,
            by_phase=by_phase,
            avg_versions_per_game=round(avg_versions, 3),
        )

    def get_status(self) -> Dict[str, Any]:
        """Get lifecycle manager status including aggregate metrics."""
        with self._instance_lock:
            metrics = self._compute_metrics()
            games_by_state: Dict[str, int] = dict(metrics.by_state)
            snapshot = LifecycleSnapshot(
                timestamp=time.time(),
                total_games=len(self._games),
                total_transitions=metrics.total_transitions,
                total_versions=metrics.total_versions,
                metrics=metrics,
                games_by_state=games_by_state,
            )
            status = snapshot.to_dict()
            status["initialized"] = self._initialized
            status["uptime_seconds"] = round(time.time() - self._started_at, 3)
            return status

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Gracefully shut down the lifecycle manager.

        Marks the manager as uninitialized while preserving in-memory state
        so callers can still inspect records after shutdown. A subsequent
        call to `initialize()` will make the manager ready for use again.
        """
        with self._instance_lock:
            self._initialized = False


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_game_lifecycle_manager() -> GameLifecycleManager:
    """Get the GameLifecycleManager singleton instance."""
    return GameLifecycleManager.get_instance()
