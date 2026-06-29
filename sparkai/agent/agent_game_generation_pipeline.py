"""
SparkLabs Agent - Game Generation Pipeline

End-to-end orchestrator that transforms a natural-language game
specification into a populated engine runtime. The pipeline
decomposes the spec into ordered phases (design, world, characters,
quests, dialogue, levels, playtest), invokes the appropriate agent
capabilities for each phase, records the produced artifacts, and
exposes live progress tracking.

The pipeline is the canonical entry point for "describe a game, get a
game" workflows. Each phase is independent and idempotent so that
failures can be retried in isolation without re-running the whole
pipeline.

Architecture:
  GameGenerationPipeline (Singleton)
    |-- GameSpec (natural-language game specification)
    |-- GenerationPhase (one stage of the pipeline)
    |-- PhaseResult (outcome of executing a phase)
    |-- GenerationRun (one full pipeline execution)
    |-- GenerationSnapshot (point-in-time state capture)

Phase handlers are callables registered via register_phase_handler.
When no handler is registered for a phase, the phase is recorded as
``SKIPPED`` so the pipeline remains robust in environments where not
every agent subsystem is live.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Enums
# =============================================================================


class GenerationPhaseType(Enum):
    """Standard phases of the game generation pipeline."""
    DESIGN = "design"
    WORLD = "world"
    CHARACTERS = "characters"
    QUESTS = "quests"
    DIALOGUE = "dialogue"
    LEVELS = "levels"
    ECONOMY = "economy"
    AUDIO = "audio"
    VISUAL = "visual"
    PLAYTEST = "playtest"
    POLISH = "polish"
    CUSTOM = "custom"


class PhaseStatus(Enum):
    """Status of an individual pipeline phase."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class RunStatus(Enum):
    """Status of a full pipeline run."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SpecFormat(Enum):
    """Format of the input game specification."""
    NATURAL_LANGUAGE = "natural_language"
    STRUCTURED = "structured"
    HYBRID = "hybrid"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class GameSpec:
    """A natural-language or structured game specification.

    Attributes:
        spec_id: Auto-generated unique identifier.
        title: Working title for the game.
        description: Natural-language description of the game.
        genre: Game genre label.
        target_platforms: Target platform identifiers.
        visual_style: Visual style label.
        core_mechanics: List of core mechanic descriptions.
        target_audience: Target audience description.
        tone: Narrative tone label.
        constraints: Free-form constraints (e.g. "no combat", "kid-friendly").
        parameters: Free-form structured parameters.
        format: Spec format hint.
        created_at: POSIX timestamp.
    """
    spec_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Untitled Game"
    description: str = ""
    genre: str = ""
    target_platforms: List[str] = field(default_factory=list)
    visual_style: str = ""
    core_mechanics: List[str] = field(default_factory=list)
    target_audience: str = ""
    tone: str = ""
    constraints: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    format: SpecFormat = SpecFormat.NATURAL_LANGUAGE
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "title": self.title,
            "description": self.description,
            "genre": self.genre,
            "target_platforms": list(self.target_platforms),
            "visual_style": self.visual_style,
            "core_mechanics": list(self.core_mechanics),
            "target_audience": self.target_audience,
            "tone": self.tone,
            "constraints": list(self.constraints),
            "parameters": dict(self.parameters),
            "format": self.format.value,
            "created_at": self.created_at,
        }


@dataclass
class GenerationPhase:
    """Describes one phase of the pipeline.

    Attributes:
        phase_id: Auto-generated unique identifier.
        phase_type: Standard phase type.
        name: Human-readable phase name.
        description: Long-form description of what the phase does.
        order: Execution order (lower runs first).
        depends_on: Phase IDs that must complete first.
        required: Whether the phase is mandatory for run success.
        parameters: Free-form phase parameters.
    """
    phase_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    phase_type: GenerationPhaseType = GenerationPhaseType.CUSTOM
    name: str = ""
    description: str = ""
    order: int = 0
    depends_on: List[str] = field(default_factory=list)
    required: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "phase_type": self.phase_type.value,
            "name": self.name,
            "description": self.description,
            "order": self.order,
            "depends_on": list(self.depends_on),
            "required": self.required,
            "parameters": dict(self.parameters),
        }


@dataclass
class PhaseResult:
    """Outcome of executing a single phase.

    Attributes:
        result_id: Auto-generated unique identifier.
        run_id: ID of the parent run.
        phase_id: ID of the phase.
        phase_type: Phase type label.
        status: Execution status.
        artifacts: Produced artifacts (free-form dict).
        metrics: Per-phase metrics (e.g. entities spawned, quests created).
        error: Error message on failure.
        started_at: Execution start timestamp.
        finished_at: Execution finish timestamp.
    """
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    run_id: str = ""
    phase_id: str = ""
    phase_type: str = ""
    status: PhaseStatus = PhaseStatus.PENDING
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "run_id": self.run_id,
            "phase_id": self.phase_id,
            "phase_type": self.phase_type,
            "status": self.status.value,
            "artifacts": dict(self.artifacts),
            "metrics": dict(self.metrics),
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass
class GenerationRun:
    """Records one full pipeline execution.

    Attributes:
        run_id: Auto-generated unique identifier.
        spec_id: ID of the source game spec.
        status: Aggregate run status.
        phase_results: Per-phase results.
        started_at: Run start timestamp.
        finished_at: Run finish timestamp.
        metadata: Free-form run metadata.
    """
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    spec_id: str = ""
    status: RunStatus = RunStatus.PENDING
    phase_results: List[PhaseResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "spec_id": self.spec_id,
            "status": self.status.value,
            "phase_results": [r.to_dict() for r in self.phase_results],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class GenerationSnapshot:
    """Point-in-time snapshot of the pipeline state.

    Attributes:
        snapshot_id: Auto-generated unique identifier.
        captured_at: POSIX timestamp of capture.
        spec_count: Total specs registered.
        run_count: Total runs executed.
        phase_count: Total phases defined.
        handler_count: Total phase handlers registered.
        recent_runs: Most recent runs.
        phases: Serialized phases.
        system_status: Aggregate status dictionary.
    """
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    captured_at: float = field(default_factory=time.time)
    spec_count: int = 0
    run_count: int = 0
    phase_count: int = 0
    handler_count: int = 0
    recent_runs: List[Dict[str, Any]] = field(default_factory=list)
    phases: List[Dict[str, Any]] = field(default_factory=list)
    system_status: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "spec_count": self.spec_count,
            "run_count": self.run_count,
            "phase_count": self.phase_count,
            "handler_count": self.handler_count,
            "recent_runs": list(self.recent_runs),
            "phases": list(self.phases),
            "system_status": dict(self.system_status),
        }


# =============================================================================
# Game Generation Pipeline (Singleton)
# =============================================================================


class GameGenerationPipeline:
    """Singleton orchestrator for end-to-end game generation.

    The pipeline is composed of phases, each of which is an
    independent unit of work that may declare dependencies on other
    phases. Phases are executed in topological order; failed required
    phases abort the run, while failed optional phases are recorded
    but do not block subsequent phases.

    Phase handlers are callables registered via
    :meth:`register_phase_handler`. When no handler is registered for
    a phase, the phase is recorded as ``SKIPPED`` to keep the pipeline
    robust in test and preview environments.
    """

    _instance: Optional["GameGenerationPipeline"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_HISTORY: int = 100

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._specs: Dict[str, GameSpec] = {}
        self._phases: Dict[str, GenerationPhase] = {}
        self._handlers: Dict[str, Callable[[GameSpec, GenerationPhase], Dict[str, Any]]] = {}
        self._runs: Dict[str, GenerationRun] = {}
        self._stats: Dict[str, int] = {
            "specs_registered": 0,
            "runs_started": 0,
            "runs_succeeded": 0,
            "runs_failed": 0,
            "runs_partial": 0,
            "phases_executed": 0,
            "phases_succeeded": 0,
            "phases_failed": 0,
            "phases_skipped": 0,
        }
        self._register_default_phases()

    @classmethod
    def get_instance(cls) -> "GameGenerationPipeline":
        """Return the singleton GameGenerationPipeline instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Default Phase Registration
    # ------------------------------------------------------------------

    def _register_default_phases(self) -> None:
        """Register the default pipeline phase set."""
        default_phases = [
            GenerationPhase(
                phase_type=GenerationPhaseType.DESIGN,
                name="Design Synthesis",
                description="Synthesize the high-level game design from the spec: pillars, mechanics, loops.",
                order=10,
                required=True,
            ),
            GenerationPhase(
                phase_type=GenerationPhaseType.WORLD,
                name="World Generation",
                description="Generate the world: terrain, biomes, landmarks, environment.",
                order=20,
                depends_on=[],
                required=True,
            ),
            GenerationPhase(
                phase_type=GenerationPhaseType.CHARACTERS,
                name="Character Generation",
                description="Generate player and NPC characters with personalities and behaviors.",
                order=30,
                required=True,
            ),
            GenerationPhase(
                phase_type=GenerationPhaseType.QUESTS,
                name="Quest Generation",
                description="Generate main and side quests anchored to the world and characters.",
                order=40,
                required=False,
            ),
            GenerationPhase(
                phase_type=GenerationPhaseType.DIALOGUE,
                name="Dialogue Generation",
                description="Generate dialogue trees for NPCs and quest conversations.",
                order=50,
                required=False,
            ),
            GenerationPhase(
                phase_type=GenerationPhaseType.LEVELS,
                name="Level Generation",
                description="Generate levels, dungeons, and encounter layouts.",
                order=60,
                required=False,
            ),
            GenerationPhase(
                phase_type=GenerationPhaseType.ECONOMY,
                name="Economy Balancing",
                description="Set up the economy: currencies, items, trade routes, balance.",
                order=70,
                required=False,
            ),
            GenerationPhase(
                phase_type=GenerationPhaseType.AUDIO,
                name="Audio Synthesis",
                description="Synthesize ambient and music layers for the world.",
                order=80,
                required=False,
            ),
            GenerationPhase(
                phase_type=GenerationPhaseType.VISUAL,
                name="Visual Polish",
                description="Apply visual polish: lighting, particles, post-processing.",
                order=90,
                required=False,
            ),
            GenerationPhase(
                phase_type=GenerationPhaseType.PLAYTEST,
                name="Playtest Simulation",
                description="Run simulated playtests and collect quality metrics.",
                order=100,
                required=False,
            ),
            GenerationPhase(
                phase_type=GenerationPhaseType.POLISH,
                name="Final Polish",
                description="Apply final polish based on playtest feedback.",
                order=110,
                required=False,
            ),
        ]
        for phase in default_phases:
            self._phases[phase.phase_id] = phase

    # ------------------------------------------------------------------
    # Phase Management
    # ------------------------------------------------------------------

    def register_phase(self, phase: GenerationPhase) -> GenerationPhase:
        """Register a custom pipeline phase."""
        with self._instance_lock:
            self._phases[phase.phase_id] = phase
            return phase

    def create_phase(
        self,
        phase_type: GenerationPhaseType,
        name: str,
        description: str = "",
        order: int = 0,
        depends_on: Optional[List[str]] = None,
        required: bool = True,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> GenerationPhase:
        """Create and register a phase."""
        phase = GenerationPhase(
            phase_type=phase_type,
            name=name,
            description=description,
            order=order,
            depends_on=list(depends_on) if depends_on else [],
            required=required,
            parameters=dict(parameters) if parameters else {},
        )
        return self.register_phase(phase)

    def remove_phase(self, phase_id: str) -> bool:
        """Remove a phase by id."""
        with self._instance_lock:
            removed = self._phases.pop(phase_id, None) is not None
            self._handlers.pop(phase_id, None)
            return removed

    def get_phase(self, phase_id: str) -> Optional[GenerationPhase]:
        """Retrieve a phase by id."""
        with self._instance_lock:
            return self._phases.get(phase_id)

    def list_phases(self) -> List[GenerationPhase]:
        """Return all phases sorted by execution order."""
        with self._instance_lock:
            return sorted(self._phases.values(), key=lambda p: p.order)

    # ------------------------------------------------------------------
    # Handler Management
    # ------------------------------------------------------------------

    def register_phase_handler(
        self, phase_id: str, handler: Callable[[GameSpec, GenerationPhase], Dict[str, Any]]
    ) -> None:
        """Register a handler for a phase."""
        with self._instance_lock:
            self._handlers[phase_id] = handler

    def unregister_phase_handler(self, phase_id: str) -> bool:
        """Remove a previously-registered phase handler."""
        with self._instance_lock:
            return self._handlers.pop(phase_id, None) is not None

    def list_handlers(self) -> List[Dict[str, str]]:
        """List all registered handler keys."""
        with self._instance_lock:
            return [
                {"phase_id": pid, "phase_name": self._phases[pid].name if pid in self._phases else ""}
                for pid in self._handlers.keys()
            ]

    # ------------------------------------------------------------------
    # Spec Management
    # ------------------------------------------------------------------

    def register_spec(self, spec: GameSpec) -> GameSpec:
        """Register a game spec."""
        with self._instance_lock:
            self._specs[spec.spec_id] = spec
            self._stats["specs_registered"] = len(self._specs)
            return spec

    def create_spec(
        self,
        title: str,
        description: str,
        genre: str = "",
        target_platforms: Optional[List[str]] = None,
        visual_style: str = "",
        core_mechanics: Optional[List[str]] = None,
        target_audience: str = "",
        tone: str = "",
        constraints: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        format: SpecFormat = SpecFormat.NATURAL_LANGUAGE,
    ) -> GameSpec:
        """Create and register a game spec."""
        spec = GameSpec(
            title=title,
            description=description,
            genre=genre,
            target_platforms=list(target_platforms) if target_platforms else [],
            visual_style=visual_style,
            core_mechanics=list(core_mechanics) if core_mechanics else [],
            target_audience=target_audience,
            tone=tone,
            constraints=list(constraints) if constraints else [],
            parameters=dict(parameters) if parameters else {},
            format=format,
        )
        return self.register_spec(spec)

    def get_spec(self, spec_id: str) -> Optional[GameSpec]:
        """Retrieve a spec by id."""
        with self._instance_lock:
            return self._specs.get(spec_id)

    def list_specs(self, limit: int = 50) -> List[GameSpec]:
        """Return the most recently registered specs."""
        with self._instance_lock:
            specs = sorted(
                self._specs.values(),
                key=lambda s: s.created_at,
                reverse=True,
            )
            return specs[:limit]

    # ------------------------------------------------------------------
    # Phase Ordering
    # ------------------------------------------------------------------

    def _resolve_phase_order(
        self, phases: List[GenerationPhase]
    ) -> Tuple[List[GenerationPhase], List[str]]:
        """Topologically sort phases respecting declared dependencies.

        Returns the ordered phase list and a list of cycles detected.
        """
        phase_by_id = {p.phase_id: p for p in phases}
        in_degree: Dict[str, int] = {p.phase_id: 0 for p in phases}
        graph: Dict[str, List[str]] = {p.phase_id: [] for p in phases}
        for phase in phases:
            for dep_id in phase.depends_on:
                if dep_id in phase_by_id:
                    graph[dep_id].append(phase.phase_id)
                    in_degree[phase.phase_id] += 1
        # Stable topological sort: when multiple phases have in-degree 0,
        # choose the one with the lowest declared order.
        ready = sorted(
            [pid for pid, d in in_degree.items() if d == 0],
            key=lambda pid: phase_by_id[pid].order,
        )
        ordered: List[GenerationPhase] = []
        cycles: List[str] = []
        while ready:
            pid = ready.pop(0)
            ordered.append(phase_by_id[pid])
            for child in graph[pid]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    # Insert maintaining order-key sort.
                    inserted = False
                    for i, existing in enumerate(ready):
                        if phase_by_id[child].order < phase_by_id[existing].order:
                            ready.insert(i, child)
                            inserted = True
                            break
                    if not inserted:
                        ready.append(child)
        if len(ordered) < len(phases):
            remaining = set(phase_by_id.keys()) - {p.phase_id for p in ordered}
            cycles = sorted(remaining)
        return ordered, cycles

    # ------------------------------------------------------------------
    # Run Execution
    # ------------------------------------------------------------------

    def _execute_phase(
        self,
        spec: GameSpec,
        phase: GenerationPhase,
        run_id: str,
        skipped_phase_ids: set,
        failed_phase_ids: set,
    ) -> PhaseResult:
        """Execute a single phase against its handler."""
        result = PhaseResult(
            run_id=run_id,
            phase_id=phase.phase_id,
            phase_type=phase.phase_type.value,
            started_at=time.time(),
        )
        if any(dep in failed_phase_ids or dep in skipped_phase_ids for dep in phase.depends_on):
            result.status = PhaseStatus.SKIPPED
            result.error = "dependency_unavailable"
            result.finished_at = time.time()
            return result
        handler = self._handlers.get(phase.phase_id)
        if handler is None:
            result.status = PhaseStatus.SKIPPED
            result.error = "no_handler_registered"
            result.finished_at = time.time()
            return result
        result.status = PhaseStatus.RUNNING
        try:
            handler_output = handler(spec, phase)
            if isinstance(handler_output, dict):
                result.artifacts = handler_output.get("artifacts", handler_output)
                result.metrics = handler_output.get("metrics", {})
            else:
                result.artifacts = {"value": str(handler_output)}
            result.status = PhaseStatus.SUCCESS
        except Exception as exc:  # noqa: BLE001 - pipeline must stay alive
            result.status = PhaseStatus.FAILED
            result.error = str(exc)
        result.finished_at = time.time()
        return result

    def run_pipeline(
        self,
        spec: GameSpec,
        phase_ids: Optional[List[str]] = None,
    ) -> GenerationRun:
        """Execute the pipeline for a spec.

        Args:
            spec: The game specification.
            phase_ids: Optional list of phase IDs to execute. If omitted,
                all registered phases are executed.

        Returns:
            The completed GenerationRun.
        """
        with self._instance_lock:
            self._specs[spec.spec_id] = spec
            self._stats["specs_registered"] = len(self._specs)
            if phase_ids is None:
                phases = self.list_phases()
            else:
                phases = [self._phases[pid] for pid in phase_ids if pid in self._phases]
        ordered, cycles = self._resolve_phase_order(phases)
        run = GenerationRun(
            spec_id=spec.spec_id,
            status=RunStatus.RUNNING,
            started_at=time.time(),
            metadata={"cycles_detected": cycles},
        )
        skipped_phase_ids: set = set()
        failed_phase_ids: set = set()
        for phase in ordered:
            result = self._execute_phase(
                spec, phase, run.run_id, skipped_phase_ids, failed_phase_ids
            )
            run.phase_results.append(result)
            if result.status == PhaseStatus.SUCCESS:
                pass
            elif result.status == PhaseStatus.FAILED:
                failed_phase_ids.add(phase.phase_id)
            elif result.status == PhaseStatus.SKIPPED:
                skipped_phase_ids.add(phase.phase_id)
            with self._instance_lock:
                self._stats["phases_executed"] += 1
                if result.status == PhaseStatus.SUCCESS:
                    self._stats["phases_succeeded"] += 1
                elif result.status == PhaseStatus.FAILED:
                    self._stats["phases_failed"] += 1
                elif result.status == PhaseStatus.SKIPPED:
                    self._stats["phases_skipped"] += 1
        # Compute aggregate run status.
        required_failed = any(
            r.status == PhaseStatus.FAILED
            and self._phases.get(r.phase_id) is not None
            and self._phases[r.phase_id].required
            for r in run.phase_results
        )
        any_success = any(r.status == PhaseStatus.SUCCESS for r in run.phase_results)
        if required_failed and not any_success:
            run.status = RunStatus.FAILED
        elif required_failed:
            run.status = RunStatus.PARTIAL
        elif any_success:
            run.status = RunStatus.SUCCESS
        else:
            run.status = RunStatus.FAILED
        run.finished_at = time.time()
        with self._instance_lock:
            self._runs[run.run_id] = run
            self._stats["runs_started"] += 1
            if run.status == RunStatus.SUCCESS:
                self._stats["runs_succeeded"] += 1
            elif run.status == RunStatus.FAILED:
                self._stats["runs_failed"] += 1
            elif run.status == RunStatus.PARTIAL:
                self._stats["runs_partial"] += 1
            self._trim_history()
        return run

    def run_pipeline_text(
        self,
        title: str,
        description: str,
        genre: str = "",
        visual_style: str = "",
        target_platforms: Optional[List[str]] = None,
        core_mechanics: Optional[List[str]] = None,
        tone: str = "",
        constraints: Optional[List[str]] = None,
        phase_ids: Optional[List[str]] = None,
    ) -> Tuple[GameSpec, GenerationRun]:
        """Convenience helper: build a spec from text and run the pipeline."""
        spec = self.create_spec(
            title=title,
            description=description,
            genre=genre,
            visual_style=visual_style,
            target_platforms=target_platforms,
            core_mechanics=core_mechanics,
            tone=tone,
            constraints=constraints,
        )
        run = self.run_pipeline(spec, phase_ids=phase_ids)
        return spec, run

    # ------------------------------------------------------------------
    # Run Query & Introspection
    # ------------------------------------------------------------------

    def get_run(self, run_id: str) -> Optional[GenerationRun]:
        """Retrieve a run by id."""
        with self._instance_lock:
            return self._runs.get(run_id)

    def list_runs(self, limit: int = 50) -> List[GenerationRun]:
        """Return the most recent runs."""
        with self._instance_lock:
            runs = sorted(
                self._runs.values(),
                key=lambda r: r.started_at,
                reverse=True,
            )
            return runs[:limit]

    def get_phase_result(self, run_id: str, phase_id: str) -> Optional[PhaseResult]:
        """Retrieve the result of a specific phase within a run."""
        with self._instance_lock:
            run = self._runs.get(run_id)
        if run is None:
            return None
        for result in run.phase_results:
            if result.phase_id == phase_id:
                return result
        return None

    def get_status(self) -> Dict[str, Any]:
        """Return aggregate status."""
        with self._instance_lock:
            return {
                "spec_count": len(self._specs),
                "phase_count": len(self._phases),
                "handler_count": len(self._handlers),
                "run_count": len(self._runs),
                "stats": dict(self._stats),
            }

    def get_snapshot(self) -> GenerationSnapshot:
        """Capture a point-in-time snapshot of the pipeline state."""
        with self._instance_lock:
            return GenerationSnapshot(
                spec_count=len(self._specs),
                run_count=len(self._runs),
                phase_count=len(self._phases),
                handler_count=len(self._handlers),
                recent_runs=[r.to_dict() for r in self.list_runs(20)],
                phases=[p.to_dict() for p in self.list_phases()],
                system_status=self.get_status(),
            )

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def _trim_history(self) -> None:
        """Trim run history to bounded size."""
        if len(self._runs) > self._MAX_HISTORY:
            sorted_runs = sorted(
                self._runs.items(), key=lambda kv: kv[1].started_at
            )
            excess = len(self._runs) - self._MAX_HISTORY
            for run_id, _ in sorted_runs[:excess]:
                self._runs.pop(run_id, None)

    def reset(self) -> None:
        """Reset the pipeline to its initial state."""
        with self._instance_lock:
            self._specs.clear()
            self._phases.clear()
            self._handlers.clear()
            self._runs.clear()
            for key in self._stats:
                self._stats[key] = 0
            self._register_default_phases()


def get_game_generation_pipeline() -> GameGenerationPipeline:
    """Return the singleton GameGenerationPipeline instance."""
    return GameGenerationPipeline.get_instance()
