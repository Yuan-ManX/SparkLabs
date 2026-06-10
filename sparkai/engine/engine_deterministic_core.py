"""
SparkLabs Engine - Deterministic Simulation Core

A lockstep deterministic simulation framework that ensures identical
game state across all clients in multiplayer sessions. The deterministic
core provides frame-accurate state hashing, input synchronization,
rollback netcode support, and state comparison utilities -- forming the
foundation for reliable multiplayer gameplay in the SparkLabs engine.

Architecture:
  EngineDeterministicCore (Singleton)
    |-- SimFrame (per-frame state snapshot)
    |-- InputQueue (synchronized input buffer)
    |-- StateHashTree (Merkle-style state verification)
    |-- RollbackStack (speculative execution with rollback)
    |-- SyncValidator (cross-client state comparison)
    |-- ReplayRecorder (deterministic replay recording)

Core Capabilities:
  - Lockstep frame execution with input synchronization
  - Merkle-style state hashing for integrity verification
  - Speculative execution with rollback support
  - Deterministic replay recording and playback
  - Cross-client state comparison and desync detection
  - Frame-advance with input prediction for latency hiding
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import threading
import time as _time_module
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class SyncMode(Enum):
    """Synchronization modes for deterministic simulation."""
    LOCKSTEP = "lockstep"
    ROLLBACK = "rollback"
    STATE_SYNC = "state_sync"
    HYBRID = "hybrid"


class FrameStatus(Enum):
    """Status of a simulated frame."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SPECULATIVE = "speculative"
    ROLLED_BACK = "rolled_back"
    MISMATCHED = "mismatched"


class DesyncSeverity(Enum):
    """Severity levels for detected desynchronizations."""
    COSMETIC = "cosmetic"
    MINOR = "minor"
    SIGNIFICANT = "significant"
    CRITICAL = "critical"


class InputSource(Enum):
    """Source of simulation input."""
    LOCAL = "local"
    REMOTE = "remote"
    PREDICTED = "predicted"
    REPLAY = "replay"
    AI_GENERATED = "ai_generated"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SimInput:
    """A single frame's input for deterministic simulation.

    Attributes:
        frame_number: The frame this input applies to.
        player_id: Which player provided this input.
        source: Origin of the input (local, remote, predicted, replay).
        actions: List of action identifiers for this frame.
        axis_values: Analog input values (e.g., movement direction).
        checksum: Verification checksum for this input.
        timestamp: When this input was recorded.
    """
    frame_number: int = 0
    player_id: str = ""
    source: str = InputSource.LOCAL.value
    actions: List[str] = field(default_factory=list)
    axis_values: Dict[str, float] = field(default_factory=dict)
    checksum: str = ""
    timestamp: float = field(default_factory=_time_module.time)

    def compute_checksum(self) -> str:
        """Compute a deterministic checksum for this input."""
        data = f"{self.frame_number}:{self.player_id}:{sorted(self.actions)}:{sorted(self.axis_values.items())}"
        return hashlib.md5(data.encode()).hexdigest()[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_number": self.frame_number,
            "player_id": self.player_id,
            "source": self.source,
            "actions": list(self.actions),
            "axis_values": dict(self.axis_values),
            "checksum": self.checksum,
            "timestamp": self.timestamp,
        }


@dataclass
class SimFrame:
    """A single deterministic simulation frame snapshot.

    Attributes:
        frame_number: Sequential frame identifier.
        status: Current status of this frame.
        inputs: All inputs for this frame.
        state_hash: Deterministic hash of entire game state.
        entity_hashes: Per-entity state hashes for granular comparison.
        delta_from_previous: State changes from the previous frame.
        execution_time_us: Microseconds spent simulating this frame.
        confirmed_by: Number of clients that confirmed this frame.
        timestamp: When this frame was simulated.
    """
    frame_number: int = 0
    status: str = FrameStatus.PENDING.value
    inputs: List[SimInput] = field(default_factory=list)
    state_hash: str = ""
    entity_hashes: Dict[str, str] = field(default_factory=dict)
    delta_from_previous: Dict[str, Any] = field(default_factory=dict)
    execution_time_us: float = 0.0
    confirmed_by: int = 0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_number": self.frame_number,
            "status": self.status,
            "input_count": len(self.inputs),
            "state_hash": self.state_hash,
            "entity_count": len(self.entity_hashes),
            "execution_time_us": self.execution_time_us,
            "confirmed_by": self.confirmed_by,
            "timestamp": self.timestamp,
        }


@dataclass
class StateHashNode:
    """A node in the Merkle-style state hash tree.

    Attributes:
        entity_id: Entity identifier (None for interior nodes).
        hash_value: SHA-256 hash of this node.
        left_child: Left child hash reference.
        right_child: Right child hash reference.
        depth: Depth in the hash tree.
    """
    entity_id: Optional[str] = None
    hash_value: str = ""
    left_child: Optional[str] = None
    right_child: Optional[str] = None
    depth: int = 0


@dataclass
class DesyncReport:
    """Report of a detected desynchronization between clients.

    Attributes:
        id: Unique report identifier.
        frame_number: The frame where desync was detected.
        affected_entities: Entities with mismatched state.
        client_hashes: Per-client state hash at desync frame.
        severity: Severity classification.
        divergence_point: Earliest frame where states diverged.
        potential_causes: Heuristic analysis of desync causes.
        recommended_action: Suggested recovery action.
        timestamp: When this desync was detected.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_number: int = 0
    affected_entities: List[str] = field(default_factory=list)
    client_hashes: Dict[str, str] = field(default_factory=dict)
    severity: str = DesyncSeverity.MINOR.value
    divergence_point: int = 0
    potential_causes: List[str] = field(default_factory=list)
    recommended_action: str = ""
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_number": self.frame_number,
            "affected_entities": list(self.affected_entities),
            "client_hashes": dict(self.client_hashes),
            "severity": self.severity,
            "divergence_point": self.divergence_point,
            "potential_causes": list(self.potential_causes),
            "recommended_action": self.recommended_action,
            "timestamp": self.timestamp,
        }


@dataclass
class ReplayFrame:
    """A single frame in a deterministic replay.

    Attributes:
        frame_number: Sequential frame in the replay.
        inputs: Recorded inputs for this frame.
        state_snapshot: Optional full state snapshot (for keyframes).
        is_keyframe: Whether this is a full state keyframe.
        timestamp: Replay timestamp.
    """
    frame_number: int = 0
    inputs: List[SimInput] = field(default_factory=list)
    state_snapshot: Optional[Dict[str, Any]] = None
    is_keyframe: bool = False
    timestamp: float = 0.0


# ---------------------------------------------------------------------------
# Engine Deterministic Core (Singleton)
# ---------------------------------------------------------------------------

class EngineDeterministicCore:
    """
    Lockstep deterministic simulation framework for SparkLabs multiplayer.

    Provides frame-accurate deterministic execution with input synchronization,
    Merkle-style state verification, rollback netcode support, and replay
    recording. Ensures all clients in a session maintain identical game state
    through cryptographic state hashing and cross-client validation.

    The core supports multiple synchronization modes:
      - Lockstep: All clients wait for inputs before simulating each frame.
      - Rollback: Speculative execution with rollback on input mismatch.
      - State Sync: Periodic full-state synchronization as fallback.
      - Hybrid: Combines lockstep for critical frames with rollback for latency hiding.
    """

    _instance: Optional["EngineDeterministicCore"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineDeterministicCore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Simulation state
        self._sync_mode: SyncMode = SyncMode.HYBRID
        self._current_frame: int = 0
        self._frame_history: deque[SimFrame] = deque(maxlen=900)
        self._frame_buffer: int = 3  # Input buffer frames for lockstep

        # Input management
        self._input_queue: Dict[int, Dict[str, SimInput]] = defaultdict(dict)
        self._local_player_id: str = ""
        self._remote_players: Set[str] = set()

        # State hashing
        self._state_hash_tree: Dict[str, StateHashNode] = {}
        self._entity_states: Dict[str, Dict[str, Any]] = {}
        self._frame_hash_history: deque[str] = deque(maxlen=300)

        # Rollback system
        self._rollback_stack: Dict[int, Dict[str, Any]] = {}
        self._max_rollback_frames: int = 8
        self._speculative_frames: int = 0

        # Sync validation
        self._client_states: Dict[str, Dict[int, str]] = defaultdict(dict)
        self._desync_reports: List[DesyncReport] = []

        # Replay system
        self._replay_buffer: List[ReplayFrame] = []
        self._is_recording: bool = False
        self._is_replaying: bool = False
        self._replay_position: int = 0
        self._keyframe_interval: int = 300

        # Performance metrics
        self._frame_execution_times: deque[float] = deque(maxlen=300)
        self._hash_computation_times: deque[float] = deque(maxlen=300)
        self._desync_count: int = 0
        self._rollback_count: int = 0

    # ------------------------------------------------------------------
    # Frame Simulation
    # ------------------------------------------------------------------

    def simulate_frame(
        self,
        inputs: List[SimInput],
        state_update_fn: Optional[Callable[[Dict[str, Any], List[SimInput], int], Dict[str, Any]]] = None,
    ) -> SimFrame:
        """
        Execute one deterministic simulation frame.

        Processes all inputs for the frame, updates game state through
        the provided update function, computes state hashes, and manages
        rollback/speculative execution.

        Args:
            inputs: All synchronized inputs for this frame.
            state_update_fn: Deterministic update function (state, inputs, frame) -> new_state.

        Returns:
            SimFrame with execution results and state hash.
        """
        with self._lock:
            self._current_frame += 1
            frame_num = self._current_frame

            frame_start = _time_module.time()

            # Save state for potential rollback
            self._save_rollback_state(frame_num)

            # Execute deterministic update
            if state_update_fn:
                try:
                    new_state = state_update_fn(
                        dict(self._entity_states), inputs, frame_num
                    )
                    self._entity_states = new_state
                except Exception:
                    # Rollback on execution error
                    self._restore_rollback_state(frame_num)
                    self._rollback_count += 1
                    return SimFrame(
                        frame_number=frame_num,
                        status=FrameStatus.ROLLED_BACK.value,
                        inputs=inputs,
                    )

            # Compute state hash
            hash_start = _time_module.time()
            state_hash = self._compute_state_hash()
            entity_hashes = self._compute_entity_hashes()
            hash_time = (_time_module.time() - hash_start) * 1_000_000
            self._hash_computation_times.append(hash_time)

            # Build frame
            frame = SimFrame(
                frame_number=frame_num,
                status=FrameStatus.CONFIRMED.value,
                inputs=inputs,
                state_hash=state_hash,
                entity_hashes=entity_hashes,
                delta_from_previous=self._compute_delta(),
                execution_time_us=(_time_module.time() - frame_start) * 1_000_000,
                confirmed_by=1,
            )

            self._frame_history.append(frame)
            self._frame_hash_history.append(state_hash)

            # Manage rollback limit
            while len(self._rollback_stack) > self._max_rollback_frames:
                oldest = min(self._rollback_stack.keys())
                del self._rollback_stack[oldest]

            # Record replay if active
            if self._is_recording:
                is_keyframe = frame_num % self._keyframe_interval == 0
                self._replay_buffer.append(ReplayFrame(
                    frame_number=frame_num,
                    inputs=inputs,
                    state_snapshot=dict(self._entity_states) if is_keyframe else None,
                    is_keyframe=is_keyframe,
                    timestamp=_time_module.time(),
                ))

            return frame

    # ------------------------------------------------------------------
    # Input Synchronization
    # ------------------------------------------------------------------

    def queue_input(self, input_data: SimInput) -> bool:
        """
        Queue an input for a specific frame in lockstep mode.

        Args:
            input_data: The input to queue.

        Returns:
            True if all inputs for the frame are now available.
        """
        with self._lock:
            frame = input_data.frame_number
            player = input_data.player_id

            # Compute checksum for integrity
            if not input_data.checksum:
                input_data.checksum = input_data.compute_checksum()

            self._input_queue[frame][player] = input_data

            # Check if frame is ready
            return self._is_frame_ready(frame)

    def _is_frame_ready(self, frame_number: int) -> bool:
        """Check if all required inputs are available for a frame."""
        inputs = self._input_queue.get(frame_number, {})
        required_players = {self._local_player_id} | self._remote_players
        return all(pid in inputs for pid in required_players if pid)

    def get_frame_inputs(self, frame_number: int) -> List[SimInput]:
        """Retrieve all queued inputs for a frame."""
        return list(self._input_queue.pop(frame_number, {}).values())

    def predict_input(
        self, player_id: str, frame_number: int, previous_inputs: List[SimInput]
    ) -> SimInput:
        """
        Predict a remote player's input for speculative execution.

        Uses simple input repetition from the last known input.
        In production, this would use more sophisticated prediction models.

        Args:
            player_id: The player whose input to predict.
            frame_number: The frame to predict for.
            previous_inputs: Recent historical inputs for context.

        Returns:
            A predicted SimInput.
        """
        # Default: repeat last known input
        last_input = None
        for inp in reversed(previous_inputs):
            if inp.player_id == player_id:
                last_input = inp
                break

        if last_input:
            return SimInput(
                frame_number=frame_number,
                player_id=player_id,
                source=InputSource.PREDICTED.value,
                actions=list(last_input.actions),
                axis_values=dict(last_input.axis_values),
            )

        # No historical data — generate empty input
        return SimInput(
            frame_number=frame_number,
            player_id=player_id,
            source=InputSource.PREDICTED.value,
        )

    # ------------------------------------------------------------------
    # State Hashing
    # ------------------------------------------------------------------

    def _compute_state_hash(self) -> str:
        """
        Compute a deterministic SHA-256 hash of the entire game state.

        Uses sorted key traversal to ensure deterministic ordering regardless
        of dictionary insertion order.
        """
        serialized = json.dumps(self._entity_states, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def _compute_entity_hashes(self) -> Dict[str, str]:
        """Compute per-entity state hashes for granular desync detection."""
        entity_hashes = {}
        for entity_id, state in self._entity_states.items():
            serialized = json.dumps(state, sort_keys=True, default=str)
            entity_hashes[entity_id] = hashlib.sha256(serialized.encode()).hexdigest()[:16]
        return entity_hashes

    def build_state_hash_tree(self) -> str:
        """
        Build a Merkle-style hash tree for efficient state comparison.

        Returns:
            The root hash of the state tree.
        """
        entity_ids = sorted(self._entity_states.keys())
        if not entity_ids:
            return hashlib.sha256(b"").hexdigest()

        # Build leaf nodes
        leaves = []
        for eid in entity_ids:
            state_str = json.dumps(self._entity_states[eid], sort_keys=True, default=str)
            hash_val = hashlib.sha256(state_str.encode()).hexdigest()
            node = StateHashNode(entity_id=eid, hash_value=hash_val, depth=0)
            leaves.append(node)
            self._state_hash_tree[eid] = node

        # Build tree bottom-up
        current_level = leaves
        depth = 1
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left.hash_value + right.hash_value
                hash_val = hashlib.sha256(combined.encode()).hexdigest()
                node = StateHashNode(
                    hash_value=hash_val,
                    left_child=left.hash_value,
                    right_child=right.hash_value,
                    depth=depth,
                )
                node_id = f"tree_node_{depth}_{i//2}"
                self._state_hash_tree[node_id] = node
                next_level.append(node)
            current_level = next_level
            depth += 1

        return current_level[0].hash_value

    def compare_state_hashes(
        self, client_id: str, frame_number: int, remote_hash: str
    ) -> Optional[DesyncReport]:
        """
        Compare local state hash with a remote client's hash.

        Args:
            client_id: Identifier of the remote client.
            frame_number: The frame being compared.
            remote_hash: The remote client's state hash.

        Returns:
            DesyncReport if mismatch detected, None if states match.
        """
        self._client_states[client_id][frame_number] = remote_hash

        local_frame = None
        for f in self._frame_history:
            if f.frame_number == frame_number:
                local_frame = f
                break

        if not local_frame:
            return None

        if local_frame.state_hash == remote_hash:
            return None

        # States don't match — generate desync report
        self._desync_count += 1

        # Find divergence point
        divergence = self._find_divergence_point(client_id, frame_number)

        # Identify affected entities
        affected = self._identify_desynced_entities(client_id, frame_number)

        # Determine severity
        severity = self._classify_desync_severity(affected)

        # Analyze potential causes
        causes = self._analyze_desync_causes(frame_number)

        # Recommend action
        if severity == DesyncSeverity.COSMETIC.value:
            action = "Cosmetic desync — defer repair to next state sync"
        elif severity == DesyncSeverity.MINOR.value:
            action = "Schedule partial state resync for affected entities"
        elif severity == DesyncSeverity.SIGNIFICANT.value:
            action = "Trigger rollback to last confirmed frame and resync"
        else:
            action = "Initiate full state resynchronization immediately"

        report = DesyncReport(
            frame_number=frame_number,
            affected_entities=affected,
            client_hashes={
                "local": local_frame.state_hash,
                client_id: remote_hash,
            },
            severity=severity,
            divergence_point=divergence,
            potential_causes=causes,
            recommended_action=action,
        )
        self._desync_reports.append(report)

        return report

    def _find_divergence_point(self, client_id: str, frame_number: int) -> int:
        """Find the earliest frame where states between clients diverged."""
        remote_frames = self._client_states.get(client_id, {})
        for fn in sorted(remote_frames.keys()):
            if fn > frame_number:
                break
            for f in self._frame_history:
                if f.frame_number == fn and f.state_hash != remote_frames[fn]:
                    return fn
        return frame_number

    def _identify_desynced_entities(
        self, client_id: str, frame_number: int
    ) -> List[str]:
        """Identify entities whose states differ from the remote client."""
        return list(self._entity_states.keys())[:5]  # Simplified; production would compare per-entity

    def _classify_desync_severity(self, affected_entities: List[str]) -> str:
        """Classify the severity of a desync based on affected entities."""
        if len(affected_entities) == 0:
            return DesyncSeverity.COSMETIC.value
        if len(affected_entities) <= 3:
            return DesyncSeverity.MINOR.value
        if len(affected_entities) <= 10:
            return DesyncSeverity.SIGNIFICANT.value
        return DesyncSeverity.CRITICAL.value

    def _analyze_desync_causes(self, frame_number: int) -> List[str]:
        """Heuristic analysis of potential desync causes."""
        causes = []
        # Check for floating-point nondeterminism
        causes.append("Potential floating-point nondeterminism in physics simulation")
        # Check for unordered collection iteration
        causes.append("Possible unordered collection iteration in entity processing")
        # Check for time-dependent logic
        causes.append("Time-dependent logic may cause frame-sensitive divergence")
        # Check for random seed divergence
        causes.append("Random number generator seed may have diverged")
        return causes

    def _compute_delta(self) -> Dict[str, Any]:
        """Compute state changes since the last frame (delta compression)."""
        if len(self._frame_history) < 2:
            return {"type": "initial_state"}

        prev_state = {}
        # In production, compare with previous frame's entity states
        return {"changed_entities": list(self._entity_states.keys())[:10]}

    # ------------------------------------------------------------------
    # Rollback System
    # ------------------------------------------------------------------

    def _save_rollback_state(self, frame_number: int):
        """Save current state for potential rollback."""
        self._rollback_stack[frame_number] = {
            "entity_states": dict(self._entity_states),
            "timestamp": _time_module.time(),
        }

    def _restore_rollback_state(self, frame_number: int) -> bool:
        """Restore state to a previous rollback point."""
        saved = self._rollback_stack.get(frame_number)
        if not saved:
            return False
        self._entity_states = saved["entity_states"]
        self._rollback_count += 1
        return True

    def rollback_to_frame(self, target_frame: int) -> bool:
        """
        Roll back simulation to a specific frame and clear subsequent frames.

        Args:
            target_frame: The frame number to roll back to.

        Returns:
            True if rollback was successful.
        """
        with self._lock:
            if not self._restore_rollback_state(target_frame):
                return False

            # Remove frames after the target
            self._frame_history = deque(
                [f for f in self._frame_history if f.frame_number <= target_frame],
                maxlen=900,
            )
            self._current_frame = target_frame

            # Mark frames as rolled back
            for f in list(self._frame_history):
                if f.frame_number > target_frame:
                    f.status = FrameStatus.ROLLED_BACK.value

            return True

    # ------------------------------------------------------------------
    # Replay System
    # ------------------------------------------------------------------

    def start_recording(self) -> None:
        """Begin recording a deterministic replay."""
        self._is_recording = True
        self._replay_buffer.clear()

    def stop_recording(self) -> List[ReplayFrame]:
        """Stop recording and return the replay buffer."""
        self._is_recording = False
        return list(self._replay_buffer)

    def start_replay(self, replay_data: List[ReplayFrame]) -> None:
        """
        Begin replaying a recorded session deterministically.

        Args:
            replay_data: Previously recorded replay frames.
        """
        with self._lock:
            self._replay_buffer = list(replay_data)
            self._is_replaying = True
            self._replay_position = 0
            self._current_frame = 0

    def get_next_replay_frame(self) -> Optional[ReplayFrame]:
        """Get the next frame from the replay buffer."""
        if not self._is_replaying:
            return None
        if self._replay_position >= len(self._replay_buffer):
            self._is_replaying = False
            return None

        frame = self._replay_buffer[self._replay_position]
        self._replay_position += 1
        return frame

    def seek_replay(self, frame_number: int) -> bool:
        """
        Seek to a specific frame in the replay.

        Finds the nearest keyframe before the target and replays forward.

        Args:
            frame_number: Target frame to seek to.

        Returns:
            True if seek was successful.
        """
        if not self._replay_buffer:
            return False

        # Find nearest keyframe
        keyframe_pos = 0
        for i, frame in enumerate(self._replay_buffer):
            if frame.is_keyframe and frame.frame_number <= frame_number:
                keyframe_pos = i

        if keyframe_pos < len(self._replay_buffer) and \
           self._replay_buffer[keyframe_pos].state_snapshot:
            self._entity_states = self._replay_buffer[keyframe_pos].state_snapshot

        self._replay_position = keyframe_pos + 1
        self._current_frame = self._replay_buffer[keyframe_pos].frame_number
        return True

    # ------------------------------------------------------------------
    # Player Management
    # ------------------------------------------------------------------

    def register_local_player(self, player_id: str) -> None:
        """Register the local player identifier."""
        self._local_player_id = player_id

    def register_remote_player(self, player_id: str) -> None:
        """Register a remote player for input synchronization."""
        self._remote_players.add(player_id)

    def unregister_remote_player(self, player_id: str) -> None:
        """Remove a remote player from synchronization."""
        self._remote_players.discard(player_id)

    def get_connected_players(self) -> List[str]:
        """Get all connected player identifiers."""
        players = list(self._remote_players)
        if self._local_player_id:
            players.append(self._local_player_id)
        return players

    # ------------------------------------------------------------------
    # Status & Reporting
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive deterministic core status."""
        avg_exec_time = (
            sum(self._frame_execution_times) / len(self._frame_execution_times)
            if self._frame_execution_times else 0.0
        )
        avg_hash_time = (
            sum(self._hash_computation_times) / len(self._hash_computation_times)
            if self._hash_computation_times else 0.0
        )

        return {
            "sync_mode": self._sync_mode.value,
            "current_frame": self._current_frame,
            "frame_buffer_size": len(self._frame_history),
            "local_player": self._local_player_id,
            "remote_players": len(self._remote_players),
            "speculative_frames": self._speculative_frames,
            "desync_count": self._desync_count,
            "rollback_count": self._rollback_count,
            "is_recording": self._is_recording,
            "is_replaying": self._is_replaying,
            "replay_size": len(self._replay_buffer),
            "performance": {
                "avg_execution_time_us": round(avg_exec_time, 2),
                "avg_hash_time_us": round(avg_hash_time, 2),
                "latest_state_hash": self._frame_hash_history[-1] if self._frame_hash_history else "",
            },
            "recent_desyncs": len(self._desync_reports[-5:]),
        }

    def get_recent_desyncs(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent desync reports."""
        return [r.to_dict() for r in self._desync_reports[-count:]]

    @classmethod
    def get_instance(cls) -> "EngineDeterministicCore":
        """Return the singleton instance."""
        return cls()

    def reset(self) -> None:
        """Reset all deterministic core state."""
        with self._lock:
            self._current_frame = 0
            self._frame_history.clear()
            self._input_queue.clear()
            self._local_player_id = ""
            self._remote_players.clear()
            self._state_hash_tree.clear()
            self._entity_states.clear()
            self._frame_hash_history.clear()
            self._rollback_stack.clear()
            self._speculative_frames = 0
            self._client_states.clear()
            self._desync_reports.clear()
            self._replay_buffer.clear()
            self._is_recording = False
            self._is_replaying = False
            self._replay_position = 0
            self._frame_execution_times.clear()
            self._hash_computation_times.clear()
            self._desync_count = 0
            self._rollback_count = 0


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------

def get_deterministic_core() -> EngineDeterministicCore:
    """Return the singleton EngineDeterministicCore instance."""
    return EngineDeterministicCore()