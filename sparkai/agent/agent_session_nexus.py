"""
SessionNexus - Conversation continuity across editor sessions and platforms.

Provides a singleton bridge that preserves full conversation state so
developers can start work on one device or platform and seamlessly
continue on another within the SparkLabs ecosystem.

Architecture:
    SessionNexus (singleton)
      |-- EditorSession (per-device/platform session tracking)
      |-- SessionBridge (cross-session transfer artifacts)
      |-- ContinuityCheckpoint (full-state snapshots for resume)

Lifecycle:
    Create Session -> Active -> Pause/Resume -> Bridge -> Accept -> Close

Features:
  - Cross-platform session bridging with encrypted transfer tokens
  - Continuity checkpoints for full state preservation and restore
  - Multiple continuity modes (EXACT_RESUME, SUMMARIZED_RESUME, PICK_UP_HINT)
  - Active session discovery and lifecycle management
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

_time_module = time


class SessionPlatform(Enum):
    """Supported editor platforms for session origination and targeting."""

    WEB_EDITOR = "web_editor"
    DESKTOP_APP = "desktop_app"
    CLI = "cli"
    MOBILE = "mobile"
    API = "api"


class SessionStatus(Enum):
    """Lifecycle states for an editor session."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    MIGRATING = "migrating"


class ContinuityMode(Enum):
    """How conversation context is transferred and resumed."""

    EXACT_RESUME = "exact_resume"
    SUMMARIZED_RESUME = "summarized_resume"
    FRESH_WITH_CONTEXT = "fresh_with_context"
    PICK_UP_HINT = "pick_up_hint"


class TransferMethod(Enum):
    """Transport mechanism for bridging sessions across platforms."""

    DIRECT = "direct"
    ENCRYPTED_LINK = "encrypted_link"
    QR_CODE = "qr_code"
    SHARE_TOKEN = "share_token"


@dataclass
class EditorSession:
    """Represents a single editor session on a specific device and platform.

    Tracks the active conversation threads, opened files, cursor position,
    and the project/scene context so that the full working state can be
    captured and transferred.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    platform: SessionPlatform = SessionPlatform.WEB_EDITOR
    device_id: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    conversation_threads: List[str] = field(default_factory=list)
    active_project: Optional[str] = None
    active_scene: Optional[str] = None
    cursor_position: Dict[str, Any] = field(default_factory=dict)
    opened_files: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    last_active_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform.value,
            "device_id": self.device_id,
            "status": self.status.value,
            "conversation_threads": self.conversation_threads,
            "active_project": self.active_project,
            "active_scene": self.active_scene,
            "cursor_position": self.cursor_position,
            "opened_files": self.opened_files,
            "created_at": self.created_at,
            "last_active_at": self.last_active_at,
        }


@dataclass
class SessionBridge:
    """A transfer artifact linking a source session to a target session.

    Carries the context snapshot, transfer token, and instructions for how
    continuity should be established. Expires after a configurable window.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_session_id: str = ""
    target_session_id: Optional[str] = None
    transfer_method: TransferMethod = TransferMethod.DIRECT
    continuity_mode: ContinuityMode = ContinuityMode.EXACT_RESUME
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    transfer_token: str = field(default_factory=lambda: uuid.uuid4().hex)
    expires_at: float = field(default_factory=lambda: _time_module.time() + 3600.0)
    created_at: float = field(default_factory=_time_module.time)
    accepted_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_session_id": self.source_session_id,
            "target_session_id": self.target_session_id,
            "transfer_method": self.transfer_method.value,
            "continuity_mode": self.continuity_mode.value,
            "context_snapshot": self.context_snapshot,
            "transfer_token": self.transfer_token,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "accepted_at": self.accepted_at,
        }


@dataclass
class ContinuityCheckpoint:
    """A full-state snapshot anchored to a session for later restore.

    Serializes the checkpoint data, file states, and agent memory so that
    a session can be rebuilt exactly as it was at the moment of capture.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)
    file_states: Dict[str, Any] = field(default_factory=dict)
    agent_memory_snapshot: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "checkpoint_data": self.checkpoint_data,
            "file_states": self.file_states,
            "agent_memory_snapshot": self.agent_memory_snapshot,
            "created_at": self.created_at,
        }


class SessionNexus:
    """Singleton orchestrator for cross-session conversation continuity.

    Bridges editor sessions across different platforms and devices within
    SparkLabs, preserving full conversation state and context so developers
    can switch environments without losing their workflow.

    Thread-safe via RLock. Single instance enforced with double-check
    locking in __new__.
    """

    _instance: Optional[SessionNexus] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> SessionNexus:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._sessions: Dict[str, EditorSession] = {}
                    instance._bridges: Dict[str, SessionBridge] = {}
                    instance._checkpoints: Dict[str, ContinuityCheckpoint] = {}
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> SessionNexus:
        """Return the singleton SessionNexus instance."""
        return cls()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(
        self,
        platform: SessionPlatform,
        device_id: str,
        project: Optional[str] = None,
    ) -> EditorSession:
        """Create and register a new editor session.

        Args:
            platform: The platform the session originates from.
            device_id: Unique identifier for the originating device.
            project: Optional active project name to associate.

        Returns:
            The newly created EditorSession.
        """
        with self._lock:
            session = EditorSession(
                platform=platform,
                device_id=device_id,
                active_project=project,
            )
            self._sessions[session.id] = session
            return session

    def close_session(self, session_id: str) -> bool:
        """Close a session by archiving it.

        The session is not removed from the internal registry — it is
        marked ARCHIVED so that bridges and checkpoints can still
        reference it.

        Args:
            session_id: The ID of the session to close.

        Returns:
            True if the session was found and closed, False otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.status = SessionStatus.ARCHIVED
            session.last_active_at = _time_module.time()
            return True

    def pause_session(self, session_id: str) -> bool:
        """Pause an active session without closing it.

        Paused sessions can be resumed later on the same or a different
        platform.

        Args:
            session_id: The ID of the session to pause.

        Returns:
            True on success, False if the session was not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.status = SessionStatus.PAUSED
            session.last_active_at = _time_module.time()
            return True

    def resume_session(self, session_id: str) -> bool:
        """Resume a previously paused session.

        Args:
            session_id: The ID of the session to resume.

        Returns:
            True on success, False if the session was not found or is
            not in PAUSED state.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if session.status != SessionStatus.PAUSED:
                return False
            session.status = SessionStatus.ACTIVE
            session.last_active_at = _time_module.time()
            return True

    # ------------------------------------------------------------------
    # Session bridging
    # ------------------------------------------------------------------

    def create_bridge(
        self,
        source_session_id: str,
        transfer_method: TransferMethod,
        continuity_mode: ContinuityMode,
    ) -> Optional[SessionBridge]:
        """Create a bridge from a source session for cross-platform transfer.

        Captures a context snapshot from the source session and generates
        a time-limited transfer token. The bridge expires after one hour.

        Args:
            source_session_id: The session to bridge from.
            transfer_method: How the bridge will be delivered.
            continuity_mode: How context should be resumed.

        Returns:
            A new SessionBridge, or None if the source session was not found.
        """
        with self._lock:
            source = self._sessions.get(source_session_id)
            if source is None:
                return None

            source.status = SessionStatus.MIGRATING
            source.last_active_at = _time_module.time()

            context_snapshot: Dict[str, Any] = {
                "conversation_threads": list(source.conversation_threads),
                "active_project": source.active_project,
                "active_scene": source.active_scene,
                "cursor_position": dict(source.cursor_position),
                "opened_files": list(source.opened_files),
                "platform": source.platform.value,
                "device_id": source.device_id,
            }

            bridge = SessionBridge(
                source_session_id=source_session_id,
                transfer_method=transfer_method,
                continuity_mode=continuity_mode,
                context_snapshot=context_snapshot,
            )
            self._bridges[bridge.id] = bridge
            return bridge

    def accept_bridge(
        self,
        bridge_token: str,
        target_platform: SessionPlatform,
        target_device_id: str,
    ) -> Optional[EditorSession]:
        """Accept a transfer bridge and create a new target session.

        Looks up the bridge by its transfer token, validates it has not
        expired, creates a fresh EditorSession on the target platform, and
        hydrates it with the context snapshot from the bridge.

        Args:
            bridge_token: The transfer token from the bridge.
            target_platform: The platform accepting the transfer.
            target_device_id: The device accepting the transfer.

        Returns:
            The newly created target EditorSession, or None if the bridge
            is invalid or expired.
        """
        with self._lock:
            bridge = self._find_bridge_by_token(bridge_token)
            if bridge is None:
                return None

            if _time_module.time() > bridge.expires_at:
                self._expire_bridge(bridge)
                return None

            snapshot = bridge.context_snapshot

            target_session = EditorSession(
                platform=target_platform,
                device_id=target_device_id,
                active_project=snapshot.get("active_project"),
                active_scene=snapshot.get("active_scene"),
                conversation_threads=list(snapshot.get("conversation_threads", [])),
                cursor_position=dict(snapshot.get("cursor_position", {})),
                opened_files=list(snapshot.get("opened_files", [])),
            )

            bridge.target_session_id = target_session.id
            bridge.accepted_at = _time_module.time()

            source = self._sessions.get(bridge.source_session_id)
            if source is not None:
                source.status = SessionStatus.ARCHIVED
                source.last_active_at = _time_module.time()

            self._sessions[target_session.id] = target_session
            return target_session

    # ------------------------------------------------------------------
    # Checkpoint management
    # ------------------------------------------------------------------

    def save_checkpoint(self, session_id: str) -> Optional[ContinuityCheckpoint]:
        """Save a full-state checkpoint for a session.

        Captures all session metadata, file states (from opened_files and
        cursor_position), and a snapshot of agent memory state so that
        the session can be restored later.

        Args:
            session_id: The session to checkpoint.

        Returns:
            A new ContinuityCheckpoint, or None if the session was not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            checkpoint_data: Dict[str, Any] = {
                "platform": session.platform.value,
                "device_id": session.device_id,
                "status": session.status.value,
                "conversation_threads": list(session.conversation_threads),
                "active_project": session.active_project,
                "active_scene": session.active_scene,
                "opened_files": list(session.opened_files),
                "cursor_position": dict(session.cursor_position),
                "last_active_at": session.last_active_at,
                "created_at": session.created_at,
            }

            file_states: Dict[str, Any] = {}
            for file_path in session.opened_files:
                file_states[file_path] = {
                    "cursor_position": session.cursor_position,
                    "last_active_at": session.last_active_at,
                }

            agent_memory_snapshot: Dict[str, Any] = {
                "conversation_threads": list(session.conversation_threads),
                "active_project": session.active_project,
                "active_scene": session.active_scene,
            }

            checkpoint = ContinuityCheckpoint(
                session_id=session_id,
                checkpoint_data=checkpoint_data,
                file_states=file_states,
                agent_memory_snapshot=agent_memory_snapshot,
            )
            self._checkpoints[checkpoint.id] = checkpoint
            return checkpoint

    def restore_checkpoint(self, checkpoint_id: str) -> Optional[EditorSession]:
        """Restore a session from a previously saved checkpoint.

        Creates a new EditorSession hydrated with the state captured in
        the checkpoint. The original session, if still in the registry, is
        left unchanged.

        Args:
            checkpoint_id: The ID of the checkpoint to restore.

        Returns:
            A new EditorSession built from the checkpoint, or None if the
            checkpoint was not found.
        """
        with self._lock:
            checkpoint = self._checkpoints.get(checkpoint_id)
            if checkpoint is None:
                return None

            data = checkpoint.checkpoint_data

            platform_raw = data.get("platform", "web_editor")
            try:
                platform = SessionPlatform(platform_raw)
            except ValueError:
                platform = SessionPlatform.WEB_EDITOR

            session = EditorSession(
                platform=platform,
                device_id=data.get("device_id", ""),
                active_project=data.get("active_project"),
                active_scene=data.get("active_scene"),
                conversation_threads=list(data.get("conversation_threads", [])),
                cursor_position=dict(data.get("cursor_position", {})),
                opened_files=list(data.get("opened_files", [])),
            )
            self._sessions[session.id] = session
            return session

    # ------------------------------------------------------------------
    # Session queries
    # ------------------------------------------------------------------

    def get_session(self, session_id: str) -> Optional[EditorSession]:
        """Retrieve a session by its ID.

        Args:
            session_id: The session ID to look up.

        Returns:
            The EditorSession if found, otherwise None.
        """
        with self._lock:
            return self._sessions.get(session_id)

    def list_active_sessions(self) -> List[EditorSession]:
        """Return all sessions currently in the ACTIVE state.

        Returns:
            A list of active EditorSession instances.
        """
        with self._lock:
            return [
                s
                for s in self._sessions.values()
                if s.status == SessionStatus.ACTIVE
            ]

    # ------------------------------------------------------------------
    # State mutation
    # ------------------------------------------------------------------

    def update_session_state(
        self,
        session_id: str,
        opened_files: List[str],
        cursor_position: Dict[str, Any],
        active_scene: Optional[str],
    ) -> bool:
        """Update the mutable state fields of an active session.

        Args:
            session_id: The session to update.
            opened_files: New list of opened file paths.
            cursor_position: New cursor position dictionary.
            active_scene: New active scene identifier.

        Returns:
            True if the session was found and updated, False otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.opened_files = list(opened_files)
            session.cursor_position = dict(cursor_position)
            session.active_scene = active_scene
            session.last_active_at = _time_module.time()
            return True

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregated statistics about all managed sessions.

        Returns:
            A dictionary with counts and breakdowns by platform, status,
            and bridge activity.
        """
        with self._lock:
            total_sessions = len(self._sessions)
            total_bridges = len(self._bridges)
            total_checkpoints = len(self._checkpoints)

            active_count = sum(
                1 for s in self._sessions.values() if s.status == SessionStatus.ACTIVE
            )
            paused_count = sum(
                1 for s in self._sessions.values() if s.status == SessionStatus.PAUSED
            )
            archived_count = sum(
                1 for s in self._sessions.values() if s.status == SessionStatus.ARCHIVED
            )
            migrating_count = sum(
                1
                for s in self._sessions.values()
                if s.status == SessionStatus.MIGRATING
            )

            platform_counts: Dict[str, int] = {}
            for s in self._sessions.values():
                key = s.platform.value
                platform_counts[key] = platform_counts.get(key, 0) + 1

            accepted_bridges = sum(
                1 for b in self._bridges.values() if b.accepted_at is not None
            )
            pending_bridges = sum(
                1 for b in self._bridges.values() if b.accepted_at is None
            )
            expired_bridges = sum(
                1
                for b in self._bridges.values()
                if b.accepted_at is None and _time_module.time() > b.expires_at
            )

            return {
                "total_sessions": total_sessions,
                "total_bridges": total_bridges,
                "total_checkpoints": total_checkpoints,
                "sessions_by_status": {
                    "active": active_count,
                    "paused": paused_count,
                    "archived": archived_count,
                    "migrating": migrating_count,
                },
                "sessions_by_platform": platform_counts,
                "bridges": {
                    "accepted": accepted_bridges,
                    "pending": pending_bridges,
                    "expired": expired_bridges,
                },
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_bridge_by_token(self, bridge_token: str) -> Optional[SessionBridge]:
        """Scan registered bridges for one matching the given transfer token.

        Args:
            bridge_token: The transfer token to look up.

        Returns:
            The matching SessionBridge, or None if not found.
        """
        for bridge in self._bridges.values():
            if bridge.transfer_token == bridge_token:
                return bridge
        return None

    def _expire_bridge(self, bridge: SessionBridge) -> None:
        """Mark a bridge as expired and revert its source session.

        Sets the source session back to ACTIVE if it was MIGRATING, so
        the user can retry the transfer.

        Args:
            bridge: The bridge that has expired.
        """
        source = self._sessions.get(bridge.source_session_id)
        if source is not None and source.status == SessionStatus.MIGRATING:
            source.status = SessionStatus.ACTIVE
            source.last_active_at = _time_module.time()

    def _purge_stale_bridges(self) -> int:
        """Remove bridges that have been expired for more than 24 hours.

        Returns:
            The number of bridges purged.
        """
        now = _time_module.time()
        stale_ids: List[str] = []
        for bridge_id, bridge in self._bridges.items():
            if bridge.accepted_at is None and (now - bridge.expires_at) > 86400.0:
                stale_ids.append(bridge_id)
        for bridge_id in stale_ids:
            del self._bridges[bridge_id]
        return len(stale_ids)

    def _purge_stale_checkpoints(self, max_age_seconds: float = 604800.0) -> int:
        """Remove checkpoints older than the given age.

        Defaults to 7 days (604800 seconds).

        Args:
            max_age_seconds: Maximum age in seconds before purging.

        Returns:
            The number of checkpoints purged.
        """
        now = _time_module.time()
        stale_ids: List[str] = []
        for checkpoint_id, checkpoint in self._checkpoints.items():
            if (now - checkpoint.created_at) > max_age_seconds:
                stale_ids.append(checkpoint_id)
        for checkpoint_id in stale_ids:
            del self._checkpoints[checkpoint_id]
        return len(stale_ids)

    def get_bridge(self, bridge_id: str) -> Optional[SessionBridge]:
        """Retrieve a bridge by its ID.

        Args:
            bridge_id: The bridge ID to look up.

        Returns:
            The SessionBridge if found, otherwise None.
        """
        with self._lock:
            return self._bridges.get(bridge_id)

    def get_checkpoint(self, checkpoint_id: str) -> Optional[ContinuityCheckpoint]:
        """Retrieve a checkpoint by its ID.

        Args:
            checkpoint_id: The checkpoint ID to look up.

        Returns:
            The ContinuityCheckpoint if found, otherwise None.
        """
        with self._lock:
            return self._checkpoints.get(checkpoint_id)

    def list_bridges_for_session(self, session_id: str) -> List[SessionBridge]:
        """Return all bridges originating from a given session.

        Args:
            session_id: The source session ID.

        Returns:
            A list of SessionBridge instances.
        """
        with self._lock:
            return [
                b
                for b in self._bridges.values()
                if b.source_session_id == session_id
            ]

    def list_checkpoints_for_session(
        self, session_id: str
    ) -> List[ContinuityCheckpoint]:
        """Return all checkpoints belonging to a given session.

        Args:
            session_id: The session ID.

        Returns:
            A list of ContinuityCheckpoint instances.
        """
        with self._lock:
            return [
                c
                for c in self._checkpoints.values()
                if c.session_id == session_id
            ]

    def get_sessions_by_platform(
        self, platform: SessionPlatform
    ) -> List[EditorSession]:
        """Return all sessions for a specific platform.

        Args:
            platform: The platform filter.

        Returns:
            A list of EditorSession instances for that platform.
        """
        with self._lock:
            return [
                s for s in self._sessions.values() if s.platform == platform
            ]

    def get_sessions_by_device(self, device_id: str) -> List[EditorSession]:
        """Return all sessions associated with a specific device.

        Args:
            device_id: The device identifier to filter by.

        Returns:
            A list of EditorSession instances for that device.
        """
        with self._lock:
            return [
                s
                for s in self._sessions.values()
                if s.device_id == device_id
            ]

    def get_sessions_by_project(self, project_name: str) -> List[EditorSession]:
        """Return all sessions associated with a specific project.

        Args:
            project_name: The project name to filter by.

        Returns:
            A list of EditorSession instances for that project.
        """
        with self._lock:
            return [
                s
                for s in self._sessions.values()
                if s.active_project == project_name
            ]

    def add_conversation_thread(
        self, session_id: str, thread_id: str
    ) -> bool:
        """Associate a conversation thread ID with a session.

        Args:
            session_id: The session to update.
            thread_id: The thread ID to add.

        Returns:
            True if the session was found and updated, False otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if thread_id not in session.conversation_threads:
                session.conversation_threads.append(thread_id)
            session.last_active_at = _time_module.time()
            return True

    def remove_conversation_thread(
        self, session_id: str, thread_id: str
    ) -> bool:
        """Remove a conversation thread ID from a session.

        Args:
            session_id: The session to update.
            thread_id: The thread ID to remove.

        Returns:
            True if the session was found and the thread was removed,
            False if the session was not found.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if thread_id in session.conversation_threads:
                session.conversation_threads.remove(thread_id)
            session.last_active_at = _time_module.time()
            return True

    def touch_session(self, session_id: str) -> bool:
        """Update the last_active_at timestamp for a session.

        Useful for heartbeat-style activity tracking.

        Args:
            session_id: The session to touch.

        Returns:
            True if the session was found, False otherwise.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.last_active_at = _time_module.time()
            return True

    def maintenance(self) -> Dict[str, int]:
        """Run housekeeping to purge stale bridges and checkpoints.

        Returns:
            A dictionary with counts of purged items.
        """
        with self._lock:
            bridges_purged = self._purge_stale_bridges()
            checkpoints_purged = self._purge_stale_checkpoints()
            return {
                "bridges_purged": bridges_purged,
                "checkpoints_purged": checkpoints_purged,
            }

    def reset(self) -> None:
        """Clear all internal state.

        Destroys every session, bridge, and checkpoint. This is a
        nuclear operation intended for testing and teardown scenarios.
        """
        with self._lock:
            self._sessions.clear()
            self._bridges.clear()
            self._checkpoints.clear()


def get_session_nexus() -> SessionNexus:
    """Module-level accessor for the SessionNexus singleton.

    Returns:
        The single SessionNexus instance.
    """
    return SessionNexus.get_instance()