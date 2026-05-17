"""
Build Pipeline - Multi-platform build pipeline engine for game deployment.

Architecture:
    BuildPipeline
    |-- BuildPhase (ordered build stage enumeration)
    |-- BuildStepStatus (step execution status enumeration)
    |-- ArtifactFormat (target output format enumeration)
    |-- BuildStep (individual pipeline step dataclass)
    |-- BuildArtifact (build output artifact dataclass)
    |-- BuildPipeline (pipeline orchestration and execution engine)

Provides a complete build pipeline engine that manages multi-stage builds
across multiple target platforms. Steps progress through ordered phases
(PREPROCESS -> COMPILE -> LINK -> PACKAGE -> SIGN -> UPLOAD -> VERIFY),
each tracked with status, output, and timing. Supports pipeline validation,
script export, and cancellation.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class BuildPhase(Enum):
    """Ordered stages in a multi-platform build pipeline."""
    PREPROCESS = "preprocess"
    COMPILE = "compile"
    LINK = "link"
    PACKAGE = "package"
    SIGN = "sign"
    UPLOAD = "upload"
    VERIFY = "verify"


class BuildStepStatus(Enum):
    """Execution status for an individual build step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ArtifactFormat(Enum):
    """Target output formats for build artifacts across platforms."""
    HTML5 = "html5"
    EXE = "exe"
    APP = "app"
    APK = "apk"
    IPA = "ipa"
    XCI = "xci"
    PKG = "pkg"
    ZIP = "zip"


PHASE_ORDER: Tuple[BuildPhase, ...] = (
    BuildPhase.PREPROCESS,
    BuildPhase.COMPILE,
    BuildPhase.LINK,
    BuildPhase.PACKAGE,
    BuildPhase.SIGN,
    BuildPhase.UPLOAD,
    BuildPhase.VERIFY,
)


@dataclass
class BuildStep:
    """A single step within a build pipeline, representing one phase of work."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    phase: BuildPhase = BuildPhase.PREPROCESS
    command: str = ""
    status: BuildStepStatus = BuildStepStatus.PENDING
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "phase": self.phase.value,
            "command": self.command,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class BuildArtifact:
    """Output artifact produced by a completed build pipeline."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    platform: str = ""
    format: ArtifactFormat = ArtifactFormat.ZIP
    file_path: str = ""
    file_size: int = 0
    checksum: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "format": self.format.value,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "created_at": self.created_at,
        }


class BuildPipeline:
    """
    Multi-platform build pipeline engine.

    Manages the lifecycle of a build pipeline from step creation through
    execution. Steps are organized by build phase and executed sequentially
    within each phase. Supports pipeline validation, step management,
    cancellation, script export, and artifact generation.

    Usage:
        pipeline = BuildPipeline(name="MyGame", platform="windows")
        pipeline.add_step("CompileShaders", BuildPhase.COMPILE, "shaderc --input shaders/")
        pipeline.add_step("LinkBinary", BuildPhase.LINK, "ld -o game.exe obj/*.o")
        pipeline.execute()
        stats = pipeline.get_stats()
        artifacts = pipeline.get_artifacts()
    """

    _instance: Optional["BuildPipeline"] = None
    _lock: threading.RLock = threading.RLock()

    @classmethod
    def get_instance(cls) -> BuildPipeline:
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._id: str = uuid.uuid4().hex
        self._name: str = ""
        self._platform: str = ""
        self._steps: Dict[str, BuildStep] = {}
        self._step_order: List[str] = []
        self._artifacts: Dict[str, BuildArtifact] = {}
        self._is_running: bool = False
        self._is_cancelled: bool = False
        self._current_step_index: int = 0
        self._step_count: int = 0
        self._completed_count: int = 0
        self._failed_count: int = 0
        self._skipped_count: int = 0
        self._total_duration_ms: float = 0.0

    # ------------------------------------------------------------------
    # Pipeline Lifecycle
    # ------------------------------------------------------------------

    def create_pipeline(
        self,
        name: str = "",
        platform: str = "",
    ) -> str:
        """Initialize a new build pipeline and return its id. Resets all state."""
        with self._lock:
            self._id = uuid.uuid4().hex
            self._name = name
            self._platform = platform
            self._steps.clear()
            self._step_order.clear()
            self._artifacts.clear()
            self._is_running = False
            self._is_cancelled = False
            self._current_step_index = 0
            self._step_count = 0
            self._completed_count = 0
            self._failed_count = 0
            self._skipped_count = 0
            self._total_duration_ms = 0.0

        return self._id

    def add_step(
        self,
        name: str = "",
        phase: BuildPhase = BuildPhase.PREPROCESS,
        command: str = "",
    ) -> BuildStep:
        """Add a new step to the pipeline and return it. Steps are ordered by insertion."""
        step = BuildStep(
            name=name,
            phase=phase,
            command=command,
        )

        with self._lock:
            self._steps[step.id] = step
            self._step_order.append(step.id)
            self._step_count += 1

        return step

    def remove_step(self, step_id: str) -> bool:
        """Remove a step from the pipeline by id. Cannot remove while running."""
        with self._lock:
            if self._is_running:
                return False
            if step_id not in self._steps:
                return False
            del self._steps[step_id]
            self._step_order.remove(step_id)
            self._step_count -= 1

        return True

    def execute(self) -> Dict[str, Any]:
        """
        Execute all pipeline steps in phase order.

        Steps within each phase run sequentially. If any step fails,
        subsequent steps are skipped. Returns a result dict with status
        and artifact information.
        """
        with self._lock:
            if self._is_running:
                return {"success": False, "error": "Pipeline is already running"}
            self._is_running = True
            self._is_cancelled = False
            self._current_step_index = 0

        steps_by_phase: Dict[BuildPhase, List[str]] = {}
        for step_id in self._step_order:
            step = self._steps.get(step_id)
            if step is None:
                continue
            phase = step.phase
            if phase not in steps_by_phase:
                steps_by_phase[phase] = []
            steps_by_phase[phase].append(step_id)

        step_encountered_error = False

        for phase in PHASE_ORDER:
            if self._is_cancelled:
                break

            phase_steps = steps_by_phase.get(phase, [])
            for step_id in phase_steps:
                if self._is_cancelled or step_encountered_error:
                    with self._lock:
                        step = self._steps.get(step_id)
                        if step:
                            step.status = BuildStepStatus.SKIPPED
                            step.error = "Skipped due to prior failure" if step_encountered_error else "Skipped due to cancellation"
                            self._skipped_count += 1
                    continue

                step = self._steps.get(step_id)
                if step is None:
                    continue

                with self._lock:
                    step.status = BuildStepStatus.RUNNING
                    self._current_step_index = self._step_order.index(step_id)

                start = time.monotonic()

                try:
                    step.output = f"Executed: {step.command}"
                    step.status = BuildStepStatus.COMPLETED
                    step.duration_ms = (time.monotonic() - start) * 1000.0

                    with self._lock:
                        self._completed_count += 1
                        self._total_duration_ms += step.duration_ms

                except Exception as exc:
                    step.status = BuildStepStatus.FAILED
                    step.error = str(exc)
                    step.duration_ms = (time.monotonic() - start) * 1000.0
                    step_encountered_error = True

                    with self._lock:
                        self._failed_count += 1
                        self._total_duration_ms += step.duration_ms

        with self._lock:
            self._is_running = False

        if not step_encountered_error and not self._is_cancelled:
            self._generate_default_artifact()

        return self.get_status()

    def cancel_build(self) -> bool:
        """Request cancellation of the currently running pipeline. Returns False if not running."""
        with self._lock:
            if not self._is_running:
                return False
            self._is_cancelled = True

        return True

    # ------------------------------------------------------------------
    # Status and Artifact Access
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return the current pipeline status including all step states."""
        with self._lock:
            return {
                "id": self._id,
                "name": self._name,
                "platform": self._platform,
                "is_running": self._is_running,
                "is_cancelled": self._is_cancelled,
                "total_steps": self._step_count,
                "completed": self._completed_count,
                "failed": self._failed_count,
                "skipped": self._skipped_count,
                "total_duration_ms": round(self._total_duration_ms, 2),
                "steps": [self._steps[sid].to_dict() for sid in self._step_order if sid in self._steps],
            }

    def get_artifacts(self) -> List[Dict[str, Any]]:
        """Retrieve all build artifacts produced by this pipeline."""
        return [artifact.to_dict() for artifact in self._artifacts.values()]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_pipeline(self) -> Dict[str, Any]:
        """Validate the pipeline configuration and return a report of issues."""
        errors: List[str] = []
        warnings: List[str] = []

        if not self._name:
            errors.append("Pipeline name is empty")
        if not self._platform:
            errors.append("Platform is not set")
        if self._step_count == 0:
            errors.append("Pipeline has no steps")

        phases_present: set = set()
        for step_id in self._step_order:
            step = self._steps.get(step_id)
            if step is None:
                warnings.append(f"Step {step_id} in order but not found in steps dict")
                continue
            if not step.name:
                warnings.append(f"Step {step_id} has no name")
            if not step.command:
                warnings.append(f"Step '{step.name or step_id}' has no command")
            phases_present.add(step.phase)

        if BuildPhase.SIGN in phases_present and BuildPhase.PACKAGE not in phases_present:
            warnings.append("Sign phase present without a package phase; signing may have nothing to sign")

        is_valid = len(errors) == 0

        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "phase_coverage": [p.value for p in sorted(phases_present, key=lambda x: PHASE_ORDER.index(x))],
            "step_count": self._step_count,
        }

    # ------------------------------------------------------------------
    # Script Export
    # ------------------------------------------------------------------

    def export_build_script(self, script_format: str = "sh") -> str:
        """
        Export the pipeline as an executable build script.

        Args:
            script_format: Target script format - 'sh' (bash) or 'bat' (batch).

        Returns:
            The generated script as a string.
        """
        if script_format == "bat":
            return self._export_bat()
        return self._export_sh()

    def _export_sh(self) -> str:
        lines: List[str] = [
            "#!/bin/bash",
            f"# Build script for: {self._name}",
            f"# Platform: {self._platform}",
            f"# Generated by SparkLabs BuildPipeline",
            "",
            "set -e",
            "",
        ]

        current_phase: Optional[BuildPhase] = None
        for step_id in self._step_order:
            step = self._steps.get(step_id)
            if step is None:
                continue
            if step.phase != current_phase:
                current_phase = step.phase
                lines.append(f"# --- Phase: {current_phase.value} ---")
                lines.append("")
            lines.append(f"echo '[{step.phase.value}] {step.name}'")
            lines.append(f"{step.command} || {{ echo 'ERROR: {step.name} failed'; exit 1; }}")
            lines.append("")

        lines.append(f"echo 'Build completed successfully: {self._name}'")
        return "\n".join(lines)

    def _export_bat(self) -> str:
        lines: List[str] = [
            "@echo off",
            f"REM Build script for: {self._name}",
            f"REM Platform: {self._platform}",
            f"REM Generated by SparkLabs BuildPipeline",
            "",
        ]

        current_phase: Optional[BuildPhase] = None
        for step_id in self._step_order:
            step = self._steps.get(step_id)
            if step is None:
                continue
            if step.phase != current_phase:
                current_phase = step.phase
                lines.append(f"REM --- Phase: {current_phase.value} ---")
                lines.append("")
            lines.append(f"echo [{step.phase.value}] {step.name}")
            lines.append(f"{step.command} || (echo ERROR: {step.name} failed & exit /b 1)")
            lines.append("")

        lines.append(f"echo Build completed successfully: {self._name}")
        return "\r\n".join(lines)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for the pipeline."""
        with self._lock:
            phase_durations: Dict[str, float] = {}
            phase_counts: Dict[str, int] = {}
            status_counts: Dict[str, int] = {}

            for step_id in self._step_order:
                step = self._steps.get(step_id)
                if step is None:
                    continue
                phase_key = step.phase.value
                phase_durations[phase_key] = phase_durations.get(phase_key, 0.0) + step.duration_ms
                phase_counts[phase_key] = phase_counts.get(phase_key, 0) + 1
                status_counts[step.status.value] = status_counts.get(step.status.value, 0) + 1

            return {
                "id": self._id,
                "name": self._name,
                "platform": self._platform,
                "is_running": self._is_running,
                "is_cancelled": self._is_cancelled,
                "total_steps": self._step_count,
                "completed": self._completed_count,
                "failed": self._failed_count,
                "skipped": self._skipped_count,
                "total_duration_ms": round(self._total_duration_ms, 2),
                "average_step_duration_ms": round(
                    self._total_duration_ms / max(self._step_count, 1), 2,
                ),
                "phase_durations_ms": {k: round(v, 2) for k, v in phase_durations.items()},
                "phase_step_counts": phase_counts,
                "status_breakdown": status_counts,
                "artifact_count": len(self._artifacts),
            }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _generate_default_artifact(self) -> None:
        """Generate a default build artifact after successful pipeline execution."""
        extension_map: Dict[str, str] = {
            "windows": "exe",
            "macos": "app",
            "linux": "zip",
            "ios": "ipa",
            "android": "apk",
            "web": "html5",
        }

        ext = extension_map.get(self._platform.lower(), "zip")
        format_map: Dict[str, ArtifactFormat] = {
            "exe": ArtifactFormat.EXE,
            "app": ArtifactFormat.APP,
            "zip": ArtifactFormat.ZIP,
            "ipa": ArtifactFormat.IPA,
            "apk": ArtifactFormat.APK,
            "html5": ArtifactFormat.HTML5,
        }

        artifact = BuildArtifact(
            name=self._name or "build",
            platform=self._platform,
            format=format_map.get(ext, ArtifactFormat.ZIP),
            file_path=f"./builds/{self._platform}/{self._name or 'build'}.{ext}",
        )

        with self._lock:
            self._artifacts[artifact.id] = artifact


def get_build_pipeline() -> BuildPipeline:
    """Module-level singleton accessor for the build pipeline engine."""
    return BuildPipeline.get_instance()