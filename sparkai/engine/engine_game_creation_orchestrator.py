"""
SparkLabs - Game Creation Orchestrator

Provides a single unified entry point that coordinates the full AI-native
game creation pipeline. The orchestrator wires together the cognitive
architect, the AI-native conductor, the runtime bridge, and the integration
layer so a natural-language prompt becomes a playable game with full AI
reasoning, parameter tuning, and outcome learning attached.

Pipeline phases:
  1. REASON   - CognitiveArchitect reasons about the prompt (genre, mechanics,
                world, narrative) and produces a design conclusion.
  2. CONDUCT  - AINativeConductor tunes physics/render/scene parameters for
                the reasoned genre and player skill profile.
  3. BUILD    - AIRuntimeBridge assembles the playable HTML game, applying
                architect conclusions and conductor adjustments as overrides.
  4. CAPTURE  - AINativeIntegration runs a tick to capture the build outcome
                and feed lessons back into the architect's knowledge base.

The orchestrator is a thread-safe singleton so both the REST API and the
WebSocket layer can drive it concurrently.

Original SparkLabs design - unified AI-native game creation entry point.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Orchestrator Enums
# =============================================================================


class OrchestratorPhase(Enum):
    """Phases of the unified creation pipeline."""
    REASON = "reason"       # Architect reasons about the prompt
    CONDUCT = "conduct"     # Conductor tunes engine parameters
    BUILD = "build"         # Bridge assembles the playable game
    CAPTURE = "capture"     # Integration captures outcomes and learns
    DONE = "done"           # Pipeline complete


class CreationStatus(Enum):
    """Status of a creation run."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class CreationPhaseResult:
    """Outcome of a single orchestrator phase."""
    phase: OrchestratorPhase
    success: bool
    duration_s: float = 0.0
    summary: str = ""
    artifacts: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class CreationResult:
    """The full outcome of a creation run."""
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    prompt: str = ""
    status: CreationStatus = CreationStatus.PENDING
    phases: List[CreationPhaseResult] = field(default_factory=list)
    # Final playable artifact
    html: str = ""
    html_length: int = 0
    config: Optional[Any] = None
    # AI metadata
    architect_conclusion: str = ""
    architect_confidence: float = 0.0
    conductor_adjustments: int = 0
    bridge_overrides: int = 0
    integration_tick: int = 0
    # Timing
    started_at: float = 0.0
    duration_s: float = 0.0
    # Errors
    error: Optional[str] = None

    def to_dict(self, include_html: bool = False) -> Dict[str, Any]:
        """Serialize to a dictionary. HTML is omitted unless requested."""
        data = {
            "run_id": self.run_id,
            "prompt": self.prompt,
            "status": self.status.value,
            "phases": [
                {
                    "phase": p.phase.value,
                    "success": p.success,
                    "duration_s": p.duration_s,
                    "summary": p.summary,
                    "error": p.error,
                }
                for p in self.phases
            ],
            "html_length": self.html_length,
            "architect_conclusion": self.architect_conclusion,
            "architect_confidence": round(self.architect_confidence, 3),
            "conductor_adjustments": self.conductor_adjustments,
            "bridge_overrides": self.bridge_overrides,
            "integration_tick": self.integration_tick,
            "duration_s": round(self.duration_s, 3),
            "error": self.error,
        }
        if include_html:
            data["html"] = self.html
        return data


# =============================================================================
# Game Creation Orchestrator (Singleton)
# =============================================================================


class GameCreationOrchestrator:
    """
    Singleton orchestrator that coordinates the full AI-native game creation
    pipeline. Wires together architect, conductor, bridge, and integration.

    Usage:
        orchestrator = GameCreationOrchestrator.get_instance()
        result = orchestrator.create_game("a neon platformer with wall jumps")
    """

    _instance: Optional["GameCreationOrchestrator"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._runs: List[CreationResult] = []
        self._max_history: int = 32

        # AI-native module wiring (lazy)
        self._architect: Any = None
        self._conductor: Any = None
        self._bridge: Any = None
        self._integration: Any = None

    @classmethod
    def get_instance(cls) -> "GameCreationOrchestrator":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -----------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------

    def initialize(self) -> None:
        """Wire up all AI-native modules. Safe to call multiple times."""
        with self._lock:
            if self._initialized:
                return

            # Architect - multi-modal reasoning
            try:
                from sparkai.agent.agent_cognitive_architect import (
                    get_architect,
                )
                self._architect = get_architect()
            except Exception as exc:
                logger.warning("Architect wiring failed: %s", exc)

            # Conductor - physics/render/scene tuning
            try:
                from sparkai.engine.engine_ai_native_conductor import (
                    AINativeConductor,
                )
                self._conductor = AINativeConductor.get_instance()
            except Exception as exc:
                logger.warning("Conductor wiring failed: %s", exc)

            # Bridge - game assembly with AI overrides
            try:
                from sparkai.engine.engine_ai_runtime_bridge import (
                    get_ai_bridge,
                )
                self._bridge = get_ai_bridge()
                if not self._bridge._initialized:
                    self._bridge.initialize()
            except Exception as exc:
                logger.warning("Bridge wiring failed: %s", exc)

            # Integration - outcome capture and learning
            try:
                from sparkai.engine.engine_ai_native_integration import (
                    get_integration,
                )
                self._integration = get_integration()
                if not self._integration._initialized:
                    self._integration.initialize()
            except Exception as exc:
                logger.warning("Integration wiring failed: %s", exc)

            self._initialized = True
            logger.info(
                "GameCreationOrchestrator initialized (architect=%s, conductor=%s, bridge=%s, integration=%s)",
                self._architect is not None,
                self._conductor is not None,
                self._bridge is not None,
                self._integration is not None,
            )

    # -----------------------------------------------------------------
    # Main Entry Point
    # -----------------------------------------------------------------

    def create_game(
        self,
        prompt: str,
        genre_hint: Optional[str] = None,
    ) -> CreationResult:
        """
        Create a complete, playable game from a natural-language prompt.

        Runs the full pipeline: REASON -> CONDUCT -> BUILD -> CAPTURE.
        Returns a CreationResult with the playable HTML and AI metadata.
        """
        if not self._initialized:
            self.initialize()

        result = CreationResult(
            prompt=prompt,
            status=CreationStatus.RUNNING,
            started_at=time.time(),
        )

        try:
            # Phase 1: REASON - Architect reasons about the game design
            reason_phase = self._run_reason_phase(prompt, genre_hint)
            result.phases.append(reason_phase)
            if reason_phase.success and reason_phase.artifacts:
                result.architect_conclusion = reason_phase.artifacts.get(
                    "conclusion", ""
                )
                result.architect_confidence = reason_phase.artifacts.get(
                    "confidence", 0.0
                )

            # Phase 2: CONDUCT - Conductor tunes engine parameters
            conduct_phase = self._run_conduct_phase(
                prompt, genre_hint, result.architect_conclusion
            )
            result.phases.append(conduct_phase)
            if conduct_phase.success:
                result.conductor_adjustments = conduct_phase.artifacts.get(
                    "adjustment_count", 0
                )

            # Phase 3: BUILD - Bridge assembles the playable game
            build_phase = self._run_build_phase(prompt, genre_hint)
            result.phases.append(build_phase)
            if build_phase.success:
                result.html = build_phase.artifacts.get("html", "")
                result.html_length = build_phase.artifacts.get("html_length", 0)
                result.config = build_phase.artifacts.get("config")
                result.bridge_overrides = build_phase.artifacts.get(
                    "overrides_count", 0
                )
            else:
                result.status = CreationStatus.FAILED
                result.error = build_phase.error or "Build phase failed"

            # Phase 4: CAPTURE - Integration captures outcomes and learns
            if result.html:
                capture_phase = self._run_capture_phase(result)
                result.phases.append(capture_phase)
                if capture_phase.success:
                    result.integration_tick = capture_phase.artifacts.get(
                        "tick", 0
                    )

            # Mark done
            if result.status == CreationStatus.RUNNING:
                result.status = CreationStatus.SUCCESS

        except Exception as exc:
            logger.exception("Creation pipeline failed: %s", exc)
            result.status = CreationStatus.FAILED
            result.error = str(exc)

        result.duration_s = time.time() - result.started_at

        # Record in history
        with self._lock:
            self._runs.append(result)
            if len(self._runs) > self._max_history:
                self._runs = self._runs[-self._max_history:]

        return result

    # -----------------------------------------------------------------
    # Phase Implementations
    # -----------------------------------------------------------------

    def _run_reason_phase(
        self,
        prompt: str,
        genre_hint: Optional[str],
    ) -> CreationPhaseResult:
        """Phase 1: Architect reasons about the game design."""
        phase = CreationPhaseResult(phase=OrchestratorPhase.REASON, success=False)
        start = time.time()

        if self._architect is None:
            phase.error = "Architect not available"
            phase.duration_s = time.time() - start
            phase.summary = "Architect not wired - skipped reasoning"
            phase.success = True  # Non-fatal: continue pipeline
            return phase

        try:
            from sparkai.agent.agent_cognitive_architect import (
                ReasoningRequest,
            )

            task = (
                f"Design a game based on this prompt: '{prompt}'. "
                f"Genre hint: {genre_hint or 'auto-detect'}. "
                f"Identify core mechanics, world structure, and narrative hooks."
            )
            request = ReasoningRequest(
                task=task,
                context={
                    "prompt": prompt,
                    "genre_hint": genre_hint,
                    "pipeline": "game_creation_orchestrator",
                },
            )
            reasoning = self._architect.run_reasoning(request)

            phase.success = reasoning.success
            phase.duration_s = time.time() - start
            phase.summary = reasoning.conclusion[:200] if reasoning.conclusion else ""
            phase.artifacts = {
                "conclusion": reasoning.conclusion,
                "confidence": reasoning.confidence,
                "modes_used": reasoning.modes_used,
                "steps": reasoning.steps,
                "duration_s": reasoning.duration_s,
            }
        except Exception as exc:
            logger.warning("Reason phase failed: %s", exc)
            phase.error = str(exc)
            phase.duration_s = time.time() - start
            phase.success = True  # Non-fatal: continue pipeline

        return phase

    def _run_conduct_phase(
        self,
        prompt: str,
        genre_hint: Optional[str],
        architect_conclusion: str,
    ) -> CreationPhaseResult:
        """Phase 2: Conductor tunes engine parameters."""
        phase = CreationPhaseResult(phase=OrchestratorPhase.CONDUCT, success=False)
        start = time.time()

        if self._conductor is None:
            phase.error = "Conductor not available"
            phase.duration_s = time.time() - start
            phase.summary = "Conductor not wired - skipped tuning"
            phase.success = True  # Non-fatal
            return phase

        try:
            # Push context to the conductor then run a cycle
            if hasattr(self._conductor, "observe_state"):
                self._conductor.observe_state({
                    "prompt": prompt,
                    "genre_hint": genre_hint,
                    "architect_conclusion": architect_conclusion,
                    "source": "orchestrator",
                })

            decision = self._conductor.cycle()

            # Count adjustments across all subsystems
            adj_count = 0
            if hasattr(decision, "physics_adjustments"):
                adj_count += len(decision.physics_adjustments)
            if hasattr(decision, "render_adjustments"):
                adj_count += len(decision.render_adjustments)
            if hasattr(decision, "scene_adjustments"):
                adj_count += len(decision.scene_adjustments)

            phase.success = True
            phase.duration_s = time.time() - start
            phase.summary = f"Applied {adj_count} engine adjustments"
            phase.artifacts = {
                "adjustment_count": adj_count,
                "cycle_id": getattr(decision, "cycle_id", ""),
                "phase": getattr(decision, "phase", ""),
            }
        except Exception as exc:
            logger.warning("Conduct phase failed: %s", exc)
            phase.error = str(exc)
            phase.duration_s = time.time() - start
            phase.success = True  # Non-fatal

        return phase

    def _run_build_phase(
        self,
        prompt: str,
        genre_hint: Optional[str],
    ) -> CreationPhaseResult:
        """Phase 3: Bridge assembles the playable game."""
        phase = CreationPhaseResult(phase=OrchestratorPhase.BUILD, success=False)
        start = time.time()

        if self._bridge is None:
            phase.error = "Bridge not available"
            phase.duration_s = time.time() - start
            return phase

        try:
            build_result = self._bridge.build_from_prompt(
                prompt, genre_hint=genre_hint
            )

            # AIRuntimeResult has .success, .html, .config, .ai_overrides
            phase.success = build_result.success
            phase.duration_s = time.time() - start

            if build_result.success:
                html = build_result.html or ""
                phase.summary = (
                    f"Built {len(html)} chars of playable HTML"
                )
                phase.artifacts = {
                    "html": html,
                    "html_length": len(html),
                    "config": build_result.config,
                    "overrides_count": len(build_result.ai_overrides)
                    if hasattr(build_result, "ai_overrides")
                    else 0,
                    "ai_session_id": getattr(build_result, "ai_session_id", ""),
                    "reasoning_conclusion": getattr(
                        build_result, "ai_reasoning_conclusion", ""
                    ),
                }
            else:
                phase.error = build_result.error or "Build failed"
                phase.summary = "Build failed"
        except Exception as exc:
            logger.exception("Build phase failed: %s", exc)
            phase.error = str(exc)
            phase.duration_s = time.time() - start

        return phase

    def _run_capture_phase(self, result: CreationResult) -> CreationPhaseResult:
        """Phase 4: Integration captures outcomes and learns."""
        phase = CreationPhaseResult(phase=OrchestratorPhase.CAPTURE, success=False)
        start = time.time()

        if self._integration is None:
            phase.error = "Integration not available"
            phase.duration_s = time.time() - start
            phase.success = True  # Non-fatal
            return phase

        try:
            # Run an integration tick to capture the build outcome
            tick_result = self._integration.tick()

            phase.success = bool(tick_result.architect_cycle)
            phase.duration_s = time.time() - start
            phase.summary = (
                f"Tick {tick_result.tick}: "
                f"{tick_result.directives_issued} directives issued, "
                f"{tick_result.directives_applied} applied"
            )
            phase.artifacts = {
                "tick": tick_result.tick,
                "observations": tick_result.observations_collected,
                "directives_issued": tick_result.directives_issued,
                "directives_applied": tick_result.directives_applied,
                "architect_cycle": tick_result.architect_cycle,
                "conductor_cycle": tick_result.conductor_cycle,
                "brain_cycle": tick_result.brain_cycle,
                "duration_s": tick_result.duration_s,
            }
        except Exception as exc:
            logger.warning("Capture phase failed: %s", exc)
            phase.error = str(exc)
            phase.duration_s = time.time() - start
            phase.success = True  # Non-fatal

        return phase

    # -----------------------------------------------------------------
    # Status and History
    # -----------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Return orchestrator status."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "architect_wired": self._architect is not None,
                "conductor_wired": self._conductor is not None,
                "bridge_wired": self._bridge is not None,
                "integration_wired": self._integration is not None,
                "runs_total": len(self._runs),
                "runs_success": sum(
                    1 for r in self._runs if r.status == CreationStatus.SUCCESS
                ),
                "runs_failed": sum(
                    1 for r in self._runs if r.status == CreationStatus.FAILED
                ),
                "last_run": (
                    self._runs[-1].to_dict()
                    if self._runs
                    else None
                ),
            }

    def history(self, limit: int = 16) -> List[Dict[str, Any]]:
        """Return recent creation runs."""
        with self._lock:
            return [r.to_dict() for r in self._runs[-limit:]]

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific run by ID (includes HTML)."""
        with self._lock:
            for r in self._runs:
                if r.run_id == run_id:
                    return r.to_dict(include_html=True)
        return None

    def reset(self) -> None:
        """Clear run history."""
        with self._lock:
            self._runs.clear()


# =============================================================================
# Module-level Convenience Functions
# =============================================================================


def get_orchestrator() -> GameCreationOrchestrator:
    """Return the singleton GameCreationOrchestrator instance."""
    return GameCreationOrchestrator.get_instance()


def create_game(
    prompt: str,
    genre_hint: Optional[str] = None,
) -> CreationResult:
    """Convenience function: create a game from a prompt."""
    return get_orchestrator().create_game(prompt, genre_hint=genre_hint)


def quick_status() -> Dict[str, Any]:
    """Convenience function: get orchestrator status."""
    return get_orchestrator().status()
