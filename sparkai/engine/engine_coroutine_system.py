"""
SparkLabs Engine - Coroutine System

A game-loop coroutine system that lets game logic spread work across
frames, mirroring the classic StartCoroutine / yield pattern found in
native game engines. Coroutines are plain Python generators that yield
YieldInstruction objects to suspend execution until a condition is met,
then resume on a subsequent frame. This keeps long-running gameplay
logic (cutscenes, timed sequences, AI step logic, tween chains)
non-blocking with respect to the main game loop.

Architecture:
  CoroutineSystem (Singleton)
    |-- Coroutine (generator wrapper with lifecycle state)
    |-- YieldInstruction (declarative suspension contract)
    |-- YieldType (wait seconds / frames / condition / coroutine)
    |-- CoroutineState (pending / running / paused / completed / ...)
    |-- Scheduler (frame-driven update advancing running coroutines)
    |-- Snapshot / Status (introspection of live coroutine population)

The system is driven externally via update(delta_time), which advances
every running coroutine whose current yield instruction is satisfied,
captures the next yielded instruction, and reports the ids of
coroutines that completed during the tick. All public methods are
thread-safe.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Generator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CoroutineState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class YieldType(Enum):
    WAIT_SECONDS = "wait_seconds"
    WAIT_FRAMES = "wait_frames"
    WAIT_UNTIL = "wait_until"
    WAIT_WHILE = "wait_while"
    WAIT_FOR_COROUTINE = "wait_for_coroutine"
    IMMEDIATE = "immediate"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class YieldInstruction:
    """A declarative suspension contract yielded by a coroutine.

    Describes the condition that must be satisfied before the owning
    coroutine is advanced again. The scheduler records internal timing
    metadata (prefixed with ``_``) on the ``metadata`` dict when a
    coroutine first yields the instruction.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    yield_type: YieldType = YieldType.IMMEDIATE
    duration: float = 0.0
    frame_count: int = 0
    condition: Optional[Callable] = None
    target_coroutine_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "yield_type": self.yield_type.value,
            "duration": self.duration,
            "frame_count": self.frame_count,
            "target_coroutine_id": self.target_coroutine_id,
            "metadata": {k: v for k, v in self.metadata.items() if not k.startswith("_")},
        }


@dataclass
class Coroutine:
    """A generator-based coroutine tracked by the scheduler.

    The ``generator`` field holds the live generator object and is
    intentionally excluded from :meth:`to_dict` since generators are
    not serializable.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    generator: Generator = None
    state: CoroutineState = CoroutineState.PENDING
    current_yield: Optional[YieldInstruction] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    error: Optional[str] = None
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # Note: generator is intentionally omitted (not serializable).
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            "current_yield": self.current_yield.to_dict() if self.current_yield else None,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "parent_id": self.parent_id,
            "metadata": dict(self.metadata),
        }


@dataclass
class CoroutineSystemSnapshot:
    """Immutable snapshot of the coroutine system state."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    active_count: int = 0
    completed_count: int = 0
    cancelled_count: int = 0
    error_count: int = 0
    total_started: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "active_count": self.active_count,
            "completed_count": self.completed_count,
            "cancelled_count": self.cancelled_count,
            "error_count": self.error_count,
            "total_started": self.total_started,
            "stats": dict(self.stats),
        }


# ---------------------------------------------------------------------------
# Coroutine System (Singleton)
# ---------------------------------------------------------------------------

class CoroutineSystem:
    """Singleton game-loop coroutine scheduler.

    Manages generator-based coroutines and advances them frame by frame
    according to their yielded :class:`YieldInstruction`. The scheduler
    is driven externally via :meth:`update`, which advances every
    running coroutine whose current yield is satisfied and reports the
    ids of coroutines that completed during the tick. All public
    methods are thread-safe.
    """

    _instance: Optional["CoroutineSystem"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "CoroutineSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.__init_singleton()
        return cls._instance

    def __init_singleton(self) -> None:
        # Guard against re-initialization of the singleton. The flag is
        # set to True (never False) so subsequent constructions never
        # reset live scheduler state.
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._coroutines: Dict[str, Coroutine] = {}
        self._frame_count: int = 0
        self._current_time: float = 0.0
        self._stats: Dict[str, Any] = {
            "total_started": 0,
            "completed": 0,
            "cancelled": 0,
            "errors": 0,
        }
        self._handlers: Dict[str, Callable] = {}

    @classmethod
    def get_instance(cls) -> "CoroutineSystem":
        """Return the singleton CoroutineSystem instance (thread-safe)."""
        return cls()

    # ------------------------------------------------------------------
    # Coroutine lifecycle
    # ------------------------------------------------------------------

    def start_coroutine(self, generator: Generator, name: str = "") -> Coroutine:
        """Register and start a generator-based coroutine.

        Args:
            generator: The generator object to schedule.
            name: Optional human-readable name. Defaults to the
                generator's ``__name__`` when available.

        Returns:
            The newly created :class:`Coroutine` wrapper.
        """
        with self._instance_lock:
            resolved_name = name or getattr(generator, "__name__", "") or "coroutine"
            coroutine = Coroutine(
                id=uuid.uuid4().hex[:12],
                name=resolved_name,
                generator=generator,
                state=CoroutineState.RUNNING,
                started_at=time.time(),
            )
            self._coroutines[coroutine.id] = coroutine
            self._stats["total_started"] = self._stats.get("total_started", 0) + 1
            return coroutine

    def start_coroutine_fn(self, fn: Callable, *args, **kwargs) -> Coroutine:
        """Convenience helper to start a coroutine from a callable.

        The callable is invoked with the provided arguments and is
        expected to return a generator, which is then scheduled.

        Args:
            fn: Callable returning a generator.
            *args: Positional arguments forwarded to ``fn``.
            **kwargs: Keyword arguments forwarded to ``fn``.

        Returns:
            The newly created :class:`Coroutine` wrapper.
        """
        generator = fn(*args, **kwargs)
        name = getattr(fn, "__name__", "")
        return self.start_coroutine(generator, name=name)

    def stop_coroutine(self, coroutine_id: str) -> bool:
        """Cancel a running or paused coroutine.

        Args:
            coroutine_id: Identifier of the coroutine to stop.

        Returns:
            True if the coroutine was cancelled, False if not found or
            already in a terminal state.
        """
        with self._instance_lock:
            coroutine = self._coroutines.get(coroutine_id)
            if coroutine is None:
                return False
            if coroutine.state in (CoroutineState.COMPLETED, CoroutineState.CANCELLED, CoroutineState.ERROR):
                return False
            coroutine.state = CoroutineState.CANCELLED
            coroutine.completed_at = time.time()
            coroutine.current_yield = None
            self._stats["cancelled"] = self._stats.get("cancelled", 0) + 1
            return True

    def pause_coroutine(self, coroutine_id: str) -> bool:
        """Pause a running coroutine.

        Args:
            coroutine_id: Identifier of the coroutine to pause.

        Returns:
            True if paused, False if not found or not running.
        """
        with self._instance_lock:
            coroutine = self._coroutines.get(coroutine_id)
            if coroutine is None or coroutine.state != CoroutineState.RUNNING:
                return False
            coroutine.state = CoroutineState.PAUSED
            return True

    def resume_coroutine(self, coroutine_id: str) -> bool:
        """Resume a paused coroutine.

        Args:
            coroutine_id: Identifier of the coroutine to resume.

        Returns:
            True if resumed, False if not found or not paused.
        """
        with self._instance_lock:
            coroutine = self._coroutines.get(coroutine_id)
            if coroutine is None or coroutine.state != CoroutineState.PAUSED:
                return False
            coroutine.state = CoroutineState.RUNNING
            return True

    # ------------------------------------------------------------------
    # Update / scheduling
    # ------------------------------------------------------------------

    def update(self, delta_time: float, current_time: Optional[float] = None) -> List[str]:
        """Advance all running coroutines by ``delta_time`` seconds.

        For each running coroutine, the current yield instruction is
        evaluated. When satisfied, the generator is advanced one step
        and the next yielded instruction is captured. Coroutines that
        raise :class:`StopIteration` are marked completed, and those
        that raise are marked errored.

        Args:
            delta_time: Time to advance, in seconds.
            current_time: Optional explicit clock value. When omitted,
                the internal clock advances by ``delta_time``.

        Returns:
            The ids of coroutines that completed during this update.
        """
        completed_ids: List[str] = []
        with self._instance_lock:
            self._frame_count += 1
            if current_time is not None:
                self._current_time = current_time
            else:
                self._current_time += delta_time

            # Snapshot running coroutines to tolerate mutation mid-tick.
            running = [c for c in self._coroutines.values() if c.state == CoroutineState.RUNNING]
            for coroutine in running:
                instruction = coroutine.current_yield
                if instruction is None:
                    # Prime the generator on its first update tick.
                    self._advance_coroutine(coroutine)
                    self._record_terminal(coroutine, completed_ids)
                    continue
                if self._is_yield_satisfied(instruction):
                    self._advance_coroutine(coroutine)
                    self._record_terminal(coroutine, completed_ids)

            return completed_ids

    def _advance_coroutine(self, coroutine: Coroutine) -> None:
        """Advance the generator one step and capture the next yield."""
        try:
            yielded = next(coroutine.generator)
        except StopIteration:
            coroutine.state = CoroutineState.COMPLETED
            coroutine.completed_at = self._current_time
            coroutine.current_yield = None
            return
        except Exception as exc:  # noqa: BLE001 - coroutines are user code
            coroutine.state = CoroutineState.ERROR
            coroutine.error = str(exc)
            coroutine.completed_at = self._current_time
            coroutine.current_yield = None
            self._stats["errors"] = self._stats.get("errors", 0) + 1
            return

        if isinstance(yielded, YieldInstruction):
            instruction = yielded
        else:
            # Treat any non-instruction yield as an immediate resume.
            instruction = YieldInstruction(yield_type=YieldType.IMMEDIATE)

        coroutine.current_yield = instruction
        # Record when this yield began so timed/frame waits resolve correctly.
        instruction.metadata["_yield_started_at"] = self._current_time
        instruction.metadata["_yield_started_frame"] = self._frame_count

    def _record_terminal(self, coroutine: Coroutine, completed_ids: List[str]) -> None:
        """Bookkeep a coroutine that just reached a terminal state."""
        if coroutine.state == CoroutineState.COMPLETED:
            completed_ids.append(coroutine.id)
            self._stats["completed"] = self._stats.get("completed", 0) + 1

    def _is_yield_satisfied(self, instruction: YieldInstruction) -> bool:
        """Evaluate whether a yield instruction is ready to resume."""
        yield_type = instruction.yield_type
        if yield_type == YieldType.IMMEDIATE:
            return True
        if yield_type == YieldType.WAIT_SECONDS:
            start = instruction.metadata.get("_yield_started_at", self._current_time)
            return (self._current_time - start) >= instruction.duration
        if yield_type == YieldType.WAIT_FRAMES:
            start_frame = instruction.metadata.get("_yield_started_frame", self._frame_count)
            return (self._frame_count - start_frame) >= instruction.frame_count
        if yield_type == YieldType.WAIT_UNTIL:
            condition = instruction.condition
            if condition is None:
                return True
            try:
                return bool(condition())
            except Exception:  # noqa: BLE001 - condition is user code
                return False
        if yield_type == YieldType.WAIT_WHILE:
            condition = instruction.condition
            if condition is None:
                return True
            try:
                return not bool(condition())
            except Exception:  # noqa: BLE001 - condition is user code
                return True
        if yield_type == YieldType.WAIT_FOR_COROUTINE:
            target = self._coroutines.get(instruction.target_coroutine_id)
            if target is None:
                return True
            return target.state == CoroutineState.COMPLETED
        return True

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_coroutine(self, coroutine_id: str) -> Optional[Coroutine]:
        with self._instance_lock:
            return self._coroutines.get(coroutine_id)

    def get_active_coroutines(self) -> List[Coroutine]:
        with self._instance_lock:
            return [c for c in self._coroutines.values() if c.state == CoroutineState.RUNNING]

    def get_all_coroutines(self) -> List[Coroutine]:
        with self._instance_lock:
            return list(self._coroutines.values())

    # ------------------------------------------------------------------
    # Yield instruction factories
    # ------------------------------------------------------------------

    def wait_for_seconds(self, seconds: float) -> YieldInstruction:
        """Create a wait instruction that suspends for ``seconds``."""
        return YieldInstruction(
            yield_type=YieldType.WAIT_SECONDS,
            duration=max(0.0, float(seconds)),
        )

    def wait_for_frames(self, frames: int) -> YieldInstruction:
        """Create a wait instruction that suspends for ``frames`` ticks."""
        return YieldInstruction(
            yield_type=YieldType.WAIT_FRAMES,
            frame_count=max(0, int(frames)),
        )

    def wait_until(self, condition: Callable[[], bool]) -> YieldInstruction:
        """Create a wait that resumes once ``condition`` returns True."""
        return YieldInstruction(
            yield_type=YieldType.WAIT_UNTIL,
            condition=condition,
        )

    def wait_while(self, condition: Callable[[], bool]) -> YieldInstruction:
        """Create a wait that resumes once ``condition`` returns False."""
        return YieldInstruction(
            yield_type=YieldType.WAIT_WHILE,
            condition=condition,
        )

    def wait_for_coroutine(self, coroutine_id: str) -> YieldInstruction:
        """Create a wait that resumes once the target coroutine completes."""
        return YieldInstruction(
            yield_type=YieldType.WAIT_FOR_COROUTINE,
            target_coroutine_id=coroutine_id,
        )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def register_handler(self, event: str, handler: Callable) -> None:
        """Register a handler callable for a named event."""
        with self._instance_lock:
            self._handlers[event] = handler

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state as a dict."""
        with self._instance_lock:
            active = sum(1 for c in self._coroutines.values() if c.state == CoroutineState.RUNNING)
            completed = sum(1 for c in self._coroutines.values() if c.state == CoroutineState.COMPLETED)
            cancelled = sum(1 for c in self._coroutines.values() if c.state == CoroutineState.CANCELLED)
            errors = sum(1 for c in self._coroutines.values() if c.state == CoroutineState.ERROR)
            return {
                "frame_count": self._frame_count,
                "current_time": self._current_time,
                "total_coroutines": len(self._coroutines),
                "active": active,
                "completed": completed,
                "cancelled": cancelled,
                "errors": errors,
                "total_started": self._stats.get("total_started", 0),
            }

    def get_snapshot(self) -> CoroutineSystemSnapshot:
        """Capture an immutable snapshot of the system state."""
        with self._instance_lock:
            active = sum(1 for c in self._coroutines.values() if c.state == CoroutineState.RUNNING)
            completed = sum(1 for c in self._coroutines.values() if c.state == CoroutineState.COMPLETED)
            cancelled = sum(1 for c in self._coroutines.values() if c.state == CoroutineState.CANCELLED)
            errors = sum(1 for c in self._coroutines.values() if c.state == CoroutineState.ERROR)
            return CoroutineSystemSnapshot(
                id=uuid.uuid4().hex[:12],
                timestamp=time.time(),
                active_count=active,
                completed_count=completed,
                cancelled_count=cancelled,
                error_count=errors,
                total_started=self._stats.get("total_started", 0),
                stats=dict(self._stats),
            )

    def reset(self) -> None:
        """Clear all coroutines, handlers, and counters."""
        with self._instance_lock:
            self._coroutines.clear()
            self._handlers.clear()
            self._frame_count = 0
            self._current_time = 0.0
            self._stats = {
                "total_started": 0,
                "completed": 0,
                "cancelled": 0,
                "errors": 0,
            }


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_coroutine_system() -> CoroutineSystem:
    return CoroutineSystem.get_instance()
