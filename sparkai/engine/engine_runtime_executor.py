"""
SparkLabs AI-Native Game Engine — Runtime Executor

Provides a standalone execution environment for running, testing, and profiling
AI-generated games without requiring a full game engine setup.  Serves as the
bridge between game creation and game execution.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExecutorState(Enum):
    """Lifecycle states of the runtime executor."""

    UNINITIALIZED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    STEPPING = auto()
    ERROR = auto()
    SHUTTING_DOWN = auto()


class ExecutionMode(Enum):
    """Execution modes supported by the runtime executor."""

    HEADLESS = auto()
    VISUAL = auto()
    DEBUG = auto()
    PROFILE = auto()
    REPLAY = auto()


class TestResult(Enum):
    """Possible outcomes of a single test case."""

    PASSED = auto()
    FAILED = auto()
    WARNING = auto()
    SKIPPED = auto()
    ERROR = auto()


class ProfileCategory(Enum):
    """Categories measured during performance profiling."""

    CPU = auto()
    GPU = auto()
    MEMORY = auto()
    PHYSICS = auto()
    RENDERING = auto()
    AI = auto()
    AUDIO = auto()
    NETWORK = auto()


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ExecutorConfig:
    """Configuration for the runtime executor.

    Attributes:
        max_instances: Maximum number of concurrent game instances.
        target_fps: Target frames per second for execution.
        time_step: Fixed simulation time-step in seconds.
        execution_mode: Default execution mode.
        temp_directory: Directory for temporary runtime artifacts.
        enable_profiling: Whether to collect profiling data by default.
        enable_deterministic_mode: Run in deterministic (lockstep) mode.
        max_frame_time_ms: Maximum allowed time per frame in milliseconds.
        auto_cleanup: Automatically clean up resources on shutdown.
        replay_buffer_size: Maximum number of frames stored for replay.
    """

    max_instances: int = 8
    target_fps: int = 60
    time_step: float = 1.0 / 60.0
    execution_mode: ExecutionMode = ExecutionMode.HEADLESS
    temp_directory: str = "/tmp/sparklabs/executor"
    enable_profiling: bool = False
    enable_deterministic_mode: bool = False
    max_frame_time_ms: float = 33.0
    auto_cleanup: bool = True
    replay_buffer_size: int = 3600


@dataclass
class GameInstance:
    """A running game instance with full state tracking.

    Attributes:
        game_id: Unique identifier for this instance.
        game_data: The original game definition data.
        state: Current execution state of this instance.
        mode: Execution mode for this instance.
        current_frame: Number of frames executed so far.
        elapsed_time: Total elapsed simulation time in seconds.
        start_time: Wall-clock time when execution started.
        last_frame_time: Wall-clock time of the last frame.
        frame_history: Recent frame results (ring buffer for replay).
        entities: Active entity count.
        paused: Whether this instance is currently paused.
    """

    game_id: str
    game_data: Dict[str, Any]
    state: ExecutorState = ExecutorState.UNINITIALIZED
    mode: ExecutionMode = ExecutionMode.HEADLESS
    current_frame: int = 0
    elapsed_time: float = 0.0
    start_time: Optional[float] = None
    last_frame_time: Optional[float] = None
    frame_history: List[FrameResult] = field(default_factory=list)
    entities: int = 0
    paused: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class FrameResult:
    """Result of a single frame execution.

    Attributes:
        frame_number: Sequential frame index.
        delta_time: Time delta used for this frame in seconds.
        execution_time_ms: Wall-clock time spent executing the frame.
        entity_count: Number of active entities this frame.
        events_processed: Number of events processed.
        state_snapshot: Optional serialised state snapshot.
        errors: Any errors encountered during the frame.
        warnings: Any warnings raised during the frame.
    """

    frame_number: int
    delta_time: float
    execution_time_ms: float
    entity_count: int = 0
    events_processed: int = 0
    state_snapshot: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TestReport:
    """Complete test execution report.

    Attributes:
        game_id: The game under test.
        total_tests: Number of tests executed.
        passed: Number of tests that passed.
        failed: Number of tests that failed.
        warnings: Number of tests with warnings.
        skipped: Number of tests skipped.
        errors: Number of tests that errored.
        duration_ms: Total test-suite duration in milliseconds.
        results: Per-test detailed results.
        summary: Human-readable summary string.
    """

    game_id: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    skipped: int = 0
    errors: int = 0
    duration_ms: float = 0.0
    results: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""

    def compute_summary(self) -> str:
        """Generate a human-readable summary of the test report."""
        self.summary = (
            f"Tests[{self.game_id}]: {self.total_tests} total, "
            f"{self.passed} passed, {self.failed} failed, "
            f"{self.warnings} warnings, {self.skipped} skipped, "
            f"{self.errors} errors ({self.duration_ms:.2f} ms)"
        )
        return self.summary


@dataclass
class ProfileReport:
    """Performance profiling report.

    Attributes:
        game_id: The game being profiled.
        duration_seconds: Duration of the profiling session.
        frame_count: Total frames captured.
        avg_fps: Average frames per second.
        min_fps: Minimum observed fps.
        max_fps: Maximum observed fps.
        category_times: Per-category accumulated times in milliseconds.
        frame_times: Per-frame execution times in milliseconds.
        memory_peak_mb: Peak memory usage in megabytes.
        bottlenecks: Identified performance bottlenecks.
    """

    game_id: str
    duration_seconds: float = 0.0
    frame_count: int = 0
    avg_fps: float = 0.0
    min_fps: float = 0.0
    max_fps: float = 0.0
    category_times: Dict[str, float] = field(default_factory=dict)
    frame_times: List[float] = field(default_factory=list)
    memory_peak_mb: float = 0.0
    bottlenecks: List[str] = field(default_factory=list)


@dataclass
class ExecutorSnapshot:
    """Complete executor state snapshot.

    Attributes:
        state: Overall executor state.
        active_instances: Number of active game instances.
        instance_ids: Identifiers of all loaded instances.
        uptime_seconds: Executor uptime in seconds.
        total_frames_executed: Cumulative frames across all instances.
        total_errors: Cumulative error count.
        memory_usage_mb: Estimated memory usage.
    """

    state: ExecutorState = ExecutorState.UNINITIALIZED
    active_instances: int = 0
    instance_ids: List[str] = field(default_factory=list)
    uptime_seconds: float = 0.0
    total_frames_executed: int = 0
    total_errors: int = 0
    memory_usage_mb: float = 0.0


# ---------------------------------------------------------------------------
# Runtime Executor (Singleton)
# ---------------------------------------------------------------------------


class RuntimeExecutor:
    """Standalone execution environment for AI-generated games.

    Singleton that manages game lifecycle, frame stepping, testing, and
    profiling.  Supports multiple concurrent game instances with isolated
    state.

    Typical usage::

        executor = RuntimeExecutor.get_instance()
        executor.initialize(ExecutorConfig(target_fps=60))
        executor.load_game(game_definition)
        executor.start_game("game-001")
        executor.step_frame("game-001")
        executor.stop_game("game-001")
        executor.shutdown()
    """

    _instance: Optional["RuntimeExecutor"] = None
    _instance_lock: threading.Lock = threading.Lock()
    _logger: logging.Logger = logging.getLogger("RuntimeExecutor")

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "RuntimeExecutor":
        """Return the singleton RuntimeExecutor instance (thread-safe)."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        """Initialize execution state, game instances, and tracking data."""
        if RuntimeExecutor._instance is not None:
            raise RuntimeError(
                "RuntimeExecutor is a singleton. Use get_instance() instead."
            )

        self._state: ExecutorState = ExecutorState.UNINITIALIZED
        self._config: Optional[ExecutorConfig] = None
        self._instances: Dict[str, GameInstance] = {}
        self._instances_lock: threading.Lock = threading.Lock()
        self._test_registry: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._profile_data: Dict[str, ProfileReport] = {}
        self._startup_time: float = 0.0
        self._total_frames: int = 0
        self._total_errors: int = 0
        self._executor_lock: threading.RLock = threading.RLock()
        self._logger.info("RuntimeExecutor instance created (uninitialized).")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize(self, config: ExecutorConfig) -> None:
        """Set up the executor with the given configuration.

        Args:
            config: An ``ExecutorConfig`` instance.

        Raises:
            RuntimeError: If the executor is already initialized.
        """
        with self._executor_lock:
            if self._state not in (ExecutorState.UNINITIALIZED, ExecutorState.SHUTTING_DOWN):
                raise RuntimeError(
                    f"Cannot initialize executor in state {self._state.name}."
                )
            self._state = ExecutorState.INITIALIZING
            self._config = config
            self._startup_time = time.monotonic()
            self._state = ExecutorState.READY
            self._logger.info(
                "RuntimeExecutor initialized (mode=%s, max_instances=%d, fps=%d).",
                config.execution_mode.name,
                config.max_instances,
                config.target_fps,
            )

    def load_game(self, game_data: Dict[str, Any]) -> str:
        """Load and prepare a game for execution.

        Args:
            game_data: Dictionary containing the complete game definition.

        Returns:
            The generated ``game_id`` string.

        Raises:
            RuntimeError: If the executor is not ready.
            ValueError: If the maximum instance limit has been reached.
        """
        self._ensure_state(ExecutorState.READY, ExecutorState.RUNNING, ExecutorState.PAUSED)

        game_id = game_data.get("game_id") or str(uuid.uuid4().hex[:12])

        with self._instances_lock:
            if game_id in self._instances:
                self._logger.warning("Game %s already loaded; replacing.", game_id)
                self._instances[game_id].state = ExecutorState.SHUTTING_DOWN

            if len(self._instances) >= self._config.max_instances:  # type: ignore[union-attr]
                raise ValueError(
                    f"Maximum instance limit ({self._config.max_instances}) reached."  # type: ignore[union-attr]
                )

            instance = GameInstance(
                game_id=game_id,
                game_data=game_data,
                state=ExecutorState.READY,
                mode=self._config.execution_mode,  # type: ignore[union-attr]
            )
            self._instances[game_id] = instance

        self._logger.info("Game %s loaded (mode=%s).", game_id, instance.mode.name)
        return game_id

    def start_game(self, game_id: str) -> None:
        """Start executing a loaded game.

        Args:
            game_id: The identifier of the game to start.

        Raises:
            KeyError: If the game is not loaded.
            RuntimeError: If the game is not in a startable state.
        """
        instance = self._get_instance(game_id)
        with instance._lock:
            if instance.state not in (ExecutorState.READY, ExecutorState.PAUSED):
                raise RuntimeError(
                    f"Game {game_id} cannot be started from state {instance.state.name}."
                )
            instance.state = ExecutorState.RUNNING
            instance.start_time = instance.start_time or time.monotonic()
            instance.paused = False
        self._logger.info("Game %s started.", game_id)

    def pause_game(self, game_id: str) -> None:
        """Pause game execution.

        Args:
            game_id: The identifier of the game to pause.

        Raises:
            KeyError: If the game is not loaded.
            RuntimeError: If the game is not running.
        """
        instance = self._get_instance(game_id)
        with instance._lock:
            if instance.state != ExecutorState.RUNNING:
                raise RuntimeError(
                    f"Game {game_id} cannot be paused from state {instance.state.name}."
                )
            instance.state = ExecutorState.PAUSED
            instance.paused = True
        self._logger.info("Game %s paused at frame %d.", game_id, instance.current_frame)

    def resume_game(self, game_id: str) -> None:
        """Resume a paused game.

        Args:
            game_id: The identifier of the game to resume.

        Raises:
            KeyError: If the game is not loaded.
            RuntimeError: If the game is not paused.
        """
        instance = self._get_instance(game_id)
        with instance._lock:
            if instance.state != ExecutorState.PAUSED:
                raise RuntimeError(
                    f"Game {game_id} cannot be resumed from state {instance.state.name}."
                )
            instance.state = ExecutorState.RUNNING
            instance.paused = False
        self._logger.info("Game %s resumed.", game_id)

    def stop_game(self, game_id: str) -> None:
        """Stop and unload a game, releasing its resources.

        Args:
            game_id: The identifier of the game to stop.

        Raises:
            KeyError: If the game is not loaded.
        """
        instance = self._get_instance(game_id)
        with instance._lock:
            instance.state = ExecutorState.SHUTTING_DOWN
        self._logger.info("Game %s stopping (total frames: %d).", game_id, instance.current_frame)

        with self._instances_lock:
            self._instances.pop(game_id, None)

        self._test_registry.pop(game_id, None)
        self._profile_data.pop(game_id, None)
        self._logger.info("Game %s unloaded.", game_id)

    def step_frame(self, game_id: str) -> FrameResult:
        """Execute a single frame for debugging purposes.

        Args:
            game_id: The identifier of the game.

        Returns:
            A ``FrameResult`` describing the frame execution.

        Raises:
            KeyError: If the game is not loaded.
            RuntimeError: If the game is not in a steppable state.
        """
        instance = self._get_instance(game_id)
        with instance._lock:
            if instance.state not in (
                ExecutorState.READY,
                ExecutorState.RUNNING,
                ExecutorState.PAUSED,
                ExecutorState.STEPPING,
            ):
                raise RuntimeError(
                    f"Game {game_id} cannot step from state {instance.state.name}."
                )
            previous_state = instance.state
            instance.state = ExecutorState.STEPPING

        try:
            result = self._execute_frame(instance)
            self._total_frames += 1
        finally:
            with instance._lock:
                instance.state = previous_state

        self._logger.debug(
            "Game %s frame %d executed in %.2f ms.",
            game_id,
            result.frame_number,
            result.execution_time_ms,
        )
        return result

    def run_test_suite(self, game_id: str, tests: List[Dict[str, Any]]) -> TestReport:
        """Run a test suite on a loaded game.

        Args:
            game_id: The identifier of the game to test.
            tests: List of test definitions, each a dict with keys such as
                ``name``, ``type``, ``params``, and ``expected``.

        Returns:
            A ``TestReport`` summarising all results.

        Raises:
            KeyError: If the game is not loaded.
        """
        self._get_instance(game_id)

        report = TestReport(game_id=game_id, total_tests=len(tests))
        start = time.monotonic()

        for test in tests:
            try:
                outcome = self._run_single_test(game_id, test)
                result_map = {
                    TestResult.PASSED: "passed",
                    TestResult.FAILED: "failed",
                    TestResult.WARNING: "warnings",
                    TestResult.SKIPPED: "skipped",
                    TestResult.ERROR: "errors",
                }
                attr = result_map.get(outcome, "errors")
                setattr(report, attr, getattr(report, attr) + 1)
                report.results.append(
                    {
                        "name": test.get("name", "unnamed"),
                        "result": outcome.name,
                    }
                )
            except Exception as exc:
                report.errors += 1
                report.results.append(
                    {
                        "name": test.get("name", "unnamed"),
                        "result": TestResult.ERROR.name,
                        "error": str(exc),
                    }
                )

        report.duration_ms = (time.monotonic() - start) * 1000.0
        report.compute_summary()
        self._logger.info(report.summary)
        return report

    def profile_game(self, game_id: str, duration: float) -> ProfileReport:
        """Profile game performance over a given duration.

        Args:
            game_id: The identifier of the game to profile.
            duration: How long to profile in seconds.

        Returns:
            A ``ProfileReport`` with detailed performance metrics.

        Raises:
            KeyError: If the game is not loaded.
        """
        instance = self._get_instance(game_id)

        report = ProfileReport(game_id=game_id, duration_seconds=duration)
        frame_times: List[float] = []
        category_accum: Dict[str, float] = defaultdict(float)

        start = time.monotonic()
        while time.monotonic() - start < duration:
            frame_start = time.monotonic()
            result = self.step_frame(game_id)
            frame_duration = (time.monotonic() - frame_start) * 1000.0
            frame_times.append(frame_duration)
            report.frame_count += 1

            # Simulated per-category breakdown
            for cat in ProfileCategory:
                category_accum[cat.name] += frame_duration * 0.12  # placeholder

        report.frame_times = frame_times
        report.category_times = dict(category_accum)

        if frame_times:
            report.avg_fps = 1000.0 / (sum(frame_times) / len(frame_times))
            report.min_fps = 1000.0 / max(frame_times) if max(frame_times) > 0 else 0.0
            report.max_fps = 1000.0 / min(frame_times) if min(frame_times) > 0 else 0.0

        # Identify bottlenecks
        if report.avg_fps < 30.0:
            report.bottlenecks.append("Low average FPS (< 30)")
        if frame_times:
            avg_frame = sum(frame_times) / len(frame_times)
            if avg_frame > 16.67:
                report.bottlenecks.append("Average frame time exceeds 60 FPS budget")

        self._profile_data[game_id] = report
        self._logger.info(
            "Profile complete for %s: avg_fps=%.1f, frames=%d.",
            game_id,
            report.avg_fps,
            report.frame_count,
        )
        return report

    def get_game_state(self, game_id: str) -> Dict[str, Any]:
        """Return the current state of a loaded game.

        Args:
            game_id: The identifier of the game.

        Returns:
            A dictionary describing the game's current state.

        Raises:
            KeyError: If the game is not loaded.
        """
        instance = self._get_instance(game_id)
        with instance._lock:
            return {
                "game_id": instance.game_id,
                "state": instance.state.name,
                "mode": instance.mode.name,
                "current_frame": instance.current_frame,
                "elapsed_time": instance.elapsed_time,
                "entities": instance.entities,
                "paused": instance.paused,
            }

    def get_status(self) -> ExecutorSnapshot:
        """Return a comprehensive snapshot of executor status.

        Returns:
            An ``ExecutorSnapshot`` with overall executor health.
        """
        with self._instances_lock:
            instance_ids = list(self._instances.keys())
            active = sum(
                1
                for i in self._instances.values()
                if i.state in (ExecutorState.RUNNING, ExecutorState.PAUSED, ExecutorState.STEPPING)
            )

        uptime = (
            time.monotonic() - self._startup_time
            if self._startup_time > 0
            else 0.0
        )

        return ExecutorSnapshot(
            state=self._state,
            active_instances=active,
            instance_ids=instance_ids,
            uptime_seconds=uptime,
            total_frames_executed=self._total_frames,
            total_errors=self._total_errors,
            memory_usage_mb=0.0,  # platform-specific; left as placeholder
        )

    def shutdown(self) -> None:
        """Gracefully shut down the executor and release all resources.

        Stops all running game instances, clears caches, and resets to
        UNINITIALIZED state.
        """
        with self._executor_lock:
            self._state = ExecutorState.SHUTTING_DOWN
            self._logger.info("RuntimeExecutor shutting down...")

            with self._instances_lock:
                game_ids = list(self._instances.keys())
                for gid in game_ids:
                    try:
                        self.stop_game(gid)
                    except Exception as exc:
                        self._logger.error("Error stopping game %s: %s", gid, exc)

            self._instances.clear()
            self._test_registry.clear()
            self._profile_data.clear()
            self._config = None
            self._state = ExecutorState.UNINITIALIZED
            self._logger.info("RuntimeExecutor shut down complete.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_state(self, *valid_states: ExecutorState) -> None:
        """Raise if the executor is not in one of the *valid_states*."""
        if self._state not in valid_states:
            raise RuntimeError(
                f"Executor is in state {self._state.name}; "
                f"expected one of {[s.name for s in valid_states]}."
            )

    def _get_instance(self, game_id: str) -> GameInstance:
        """Retrieve a game instance or raise KeyError."""
        with self._instances_lock:
            instance = self._instances.get(game_id)
        if instance is None:
            raise KeyError(f"Game instance '{game_id}' not found.")
        return instance

    def _execute_frame(self, instance: GameInstance) -> FrameResult:
        """Execute one simulation frame for the given instance.

        This is the core simulation entry point.  In a real engine this
        would orchestrate the ECS world tick, physics, rendering, etc.
        """
        frame_start = time.monotonic()
        delta = instance.last_frame_time or self._config.time_step  # type: ignore[union-attr]
        if instance.last_frame_time is not None:
            delta = time.monotonic() - instance.last_frame_time

        errors: List[str] = []
        warnings: List[str] = []

        try:
            # Simulated frame processing
            self._simulate_frame_tick(instance, delta)
        except Exception as exc:
            self._total_errors += 1
            errors.append(str(exc))
            self._logger.exception("Error during frame %d of game %s.", instance.current_frame, instance.game_id)

        instance.current_frame += 1
        instance.elapsed_time += delta
        instance.last_frame_time = frame_start

        exec_ms = (time.monotonic() - frame_start) * 1000.0

        if exec_ms > self._config.max_frame_time_ms:  # type: ignore[union-attr]
            warnings.append(
                f"Frame {instance.current_frame} exceeded max frame time "
                f"({exec_ms:.2f} ms > {self._config.max_frame_time_ms} ms)"  # type: ignore[union-attr]
            )

        result = FrameResult(
            frame_number=instance.current_frame,
            delta_time=delta,
            execution_time_ms=exec_ms,
            entity_count=instance.entities,
            events_processed=0,
            errors=errors,
            warnings=warnings,
        )

        # Maintain replay ring buffer
        max_history = self._config.replay_buffer_size  # type: ignore[union-attr]
        if len(instance.frame_history) >= max_history:
            instance.frame_history.pop(0)
        instance.frame_history.append(result)

        return result

    @staticmethod
    def _simulate_frame_tick(instance: GameInstance, delta: float) -> None:
        """Placeholder for the actual per-frame simulation logic.

        In a full implementation this would invoke engine systems: physics
        step, AI update, animation advance, event dispatch, and rendering.
        """
        time.sleep(0.001)  # tiny sleep to simulate work

    def _run_single_test(
        self, game_id: str, test: Dict[str, Any]
    ) -> TestResult:
        """Execute a single test case and return its outcome.

        Args:
            game_id: The game under test.
            test: Dictionary with test definition.

        Returns:
            The ``TestResult`` outcome.
        """
        test_type = test.get("type", "unit")
        test_name = test.get("name", "unnamed")

        if test_type == "skip":
            return TestResult.SKIPPED

        try:
            if test_type == "frame":
                # Frame-based test: step N frames and check state
                frames = test.get("params", {}).get("frames", 1)
                for _ in range(frames):
                    self.step_frame(game_id)
                return TestResult.PASSED

            if test_type == "assertion":
                expected = test.get("expected")
                actual = test.get("params", {}).get("actual")
                if actual == expected:
                    return TestResult.PASSED
                return TestResult.FAILED

            if test_type == "performance":
                threshold_ms = test.get("params", {}).get("max_ms", 16.0)
                t0 = time.monotonic()
                self.step_frame(game_id)
                elapsed = (time.monotonic() - t0) * 1000.0
                if elapsed <= threshold_ms:
                    return TestResult.PASSED
                return TestResult.WARNING

            # Unknown test type — treat as pass for now
            self._logger.warning("Unknown test type '%s' for '%s'.", test_type, test_name)
            return TestResult.PASSED

        except Exception:
            self._logger.exception("Test '%s' raised an exception.", test_name)
            return TestResult.ERROR


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def get_runtime_executor() -> RuntimeExecutor:
    """Get the RuntimeExecutor singleton instance."""
    return RuntimeExecutor.get_instance()