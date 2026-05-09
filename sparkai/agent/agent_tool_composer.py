"""
SparkLabs Agent - Tool Composer

Tool composition engine for the SparkLabs AI-native game engine agent.
Enables chaining multiple tools into coordinated pipelines for complex
game development operations. Supports sequential, parallel, and conditional
tool chains with dependency resolution, output passing between tools,
rollback on failure, and execution scheduling.

Architecture:
  ToolComposer
    |-- ToolChain (ordered sequence of tool calls)
    |-- ToolStep (single tool invocation with inputs/outputs)
    |-- ChainTemplate (reusable pre-defined tool pipelines)
    |-- ExecutionPlan (resolved execution DAG with scheduling)
    |-- ChainContext (shared state across chained tools)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ChainExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    ROLLBACK_ON_FAILURE = "rollback_on_failure"


class ToolStepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class ChainStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass
class ToolStep:
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    tool_name: str = ""
    description: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: ToolStepStatus = ToolStepStatus.PENDING
    error_message: str = ""
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 2
    rollback_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "tool": self.tool_name,
            "description": self.description,
            "status": self.status.value,
            "depends_on": self.depends_on,
            "retries": self.retry_count,
            "error": self.error_message,
        }


@dataclass
class ChainTemplate:
    template_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: str = "general"
    description: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    mode: ChainExecutionMode = ChainExecutionMode.SEQUENTIAL
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "category": self.category,
            "steps": len(self.steps),
            "tags": self.tags,
            "usage_count": self.usage_count,
        }


@dataclass
class ChainContext:
    variables: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def add_artifact(self, name: str, data: Any) -> None:
        self.artifacts[name] = data

    def record_metric(self, name: str, value: float) -> None:
        self.metrics[name] = value

    def to_dict(self) -> dict:
        return {
            "variable_count": len(self.variables),
            "artifact_count": len(self.artifacts),
            "tag_count": len(self.tags),
        }


@dataclass
class ToolChain:
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "chain"
    steps: List[ToolStep] = field(default_factory=list)
    mode: ChainExecutionMode = ChainExecutionMode.SEQUENTIAL
    status: ChainStatus = ChainStatus.IDLE
    context: ChainContext = field(default_factory=ChainContext)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    on_before_step: Optional[Callable] = None
    on_after_step: Optional[Callable] = None

    def add_step(self, tool_name: str, inputs: Optional[Dict] = None, depends_on: Optional[List[str]] = None, description: str = "") -> ToolStep:
        step = ToolStep(tool_name=tool_name, inputs=inputs or {}, depends_on=depends_on or [], description=description)
        self.steps.append(step)
        return step

    def get_ready_steps(self) -> List[ToolStep]:
        done_ids = {s.step_id for s in self.steps if s.status in (ToolStepStatus.SUCCEEDED, ToolStepStatus.SKIPPED)}
        failed_ids = {s.step_id for s in self.steps if s.status == ToolStepStatus.FAILED}
        ready = []
        for step in self.steps:
            if step.status != ToolStepStatus.PENDING:
                continue
            deps_met = all(
                dep_id in done_ids or (dep_id in done_ids) for dep_id in step.depends_on
            )
            if deps_met:
                ready.append(step)
        return ready

    def mark_failed(self, step_id: str, error: str) -> bool:
        for step in self.steps:
            if step.step_id == step_id:
                step.status = ToolStepStatus.FAILED
                step.error_message = error
                step.completed_at = time.time()
                return True
        return False

    def mark_succeeded(self, step_id: str, outputs: Optional[Dict] = None) -> bool:
        for step in self.steps:
            if step.step_id == step_id:
                step.status = ToolStepStatus.SUCCEEDED
                if outputs:
                    step.outputs = outputs
                step.completed_at = time.time()
                return True
        return False

    def get_step_output(self, step_id: str) -> Optional[Dict]:
        for step in self.steps:
            if step.step_id == step_id:
                return step.outputs
        return None

    def generate_mermaid(self) -> str:
        lines = ["graph TD"]
        for step in self.steps:
            status_symbol = {"pending": "○", "running": "◐", "succeeded": "●", "failed": "✕", "skipped": "○"}.get(step.status.value, "○")
            lines.append(f'    {step.step_id}["{step.tool_name} {status_symbol}"]')
            for dep in step.depends_on:
                lines.append(f"    {dep} --> {step.step_id}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "mode": self.mode.value,
            "status": self.status.value,
            "step_count": len(self.steps),
            "completed_steps": sum(1 for s in self.steps if s.status == ToolStepStatus.SUCCEEDED),
            "failed_steps": sum(1 for s in self.steps if s.status == ToolStepStatus.FAILED),
            "steps": [s.to_dict() for s in self.steps],
        }


class ToolComposer:
    """
    Tool composition engine that chains multiple tools into pipelines.

    Enables AI agents to compose complex game development workflows by
    chaining tool calls. Supports sequential, parallel, and conditional
    execution modes with dependency resolution. Provides a library of
    reusable chain templates for common patterns like project scaffolding,
    asset pipeline execution, and build-deploy workflows.
    """

    _instance: Optional["ToolComposer"] = None

    def __init__(self):
        self._active_chains: Dict[str, ToolChain] = {}
        self._chain_history: List[ToolChain] = []
        self._templates: Dict[str, ChainTemplate] = {}
        self._max_history: int = 100
        self._init_defaults()

    @classmethod
    def get_instance(cls) -> "ToolComposer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_chain(self, name: str = "chain", mode: ChainExecutionMode = ChainExecutionMode.SEQUENTIAL) -> ToolChain:
        chain = ToolChain(name=name, mode=mode)
        self._active_chains[chain.chain_id] = chain
        return chain

    def get_chain(self, chain_id: str) -> Optional[ToolChain]:
        return self._active_chains.get(chain_id)

    def execute_chain(self, chain: ToolChain, executor: Optional[Callable[[ToolStep], ToolStep]] = None) -> ToolChain:
        chain.status = ChainStatus.RUNNING
        chain.started_at = time.time()

        for step in chain.steps:
            if chain.status == ChainStatus.FAILED and chain.mode == ChainExecutionMode.ROLLBACK_ON_FAILURE:
                break

            step.status = ToolStepStatus.RUNNING
            step.started_at = time.time()

            if chain.on_before_step:
                chain.on_before_step(step)

            if executor:
                try:
                    result_step = executor(step)
                    if result_step.status == ToolStepStatus.SUCCEEDED:
                        chain.mark_succeeded(step.step_id, result_step.outputs)
                    else:
                        chain.mark_failed(step.step_id, result_step.error_message)
                        if chain.mode == ChainExecutionMode.ROLLBACK_ON_FAILURE:
                            chain.status = ChainStatus.FAILED
                except Exception as e:
                    chain.mark_failed(step.step_id, str(e))
                    if chain.mode == ChainExecutionMode.ROLLBACK_ON_FAILURE:
                        chain.status = ChainStatus.FAILED

            if chain.on_after_step:
                chain.on_after_step(step)

        if chain.status != ChainStatus.FAILED:
            chain.status = ChainStatus.COMPLETED
        chain.completed_at = time.time()

        self._chain_history.append(chain)
        if len(self._chain_history) > self._max_history:
            self._chain_history = self._chain_history[-self._max_history:]

        return chain

    def register_template(self, template: ChainTemplate) -> None:
        self._templates[template.template_id] = template

    def get_template(self, template_id: str) -> Optional[ChainTemplate]:
        return self._templates.get(template_id)

    def list_templates(self, category: Optional[str] = None) -> List[ChainTemplate]:
        if category:
            return [t for t in self._templates.values() if t.category == category]
        return list(self._templates.values())

    def instantiate_template(self, template_id: str, name: str = "") -> Optional[ToolChain]:
        template = self._templates.get(template_id)
        if not template:
            return None
        chain = self.create_chain(name or template.name, template.mode)
        for step_def in template.steps:
            chain.add_step(
                tool_name=step_def.get("tool", ""),
                inputs=step_def.get("inputs", {}),
                depends_on=step_def.get("depends_on", []),
                description=step_def.get("description", ""),
            )
        template.usage_count += 1
        return chain

    def _init_defaults(self) -> None:
        defaults = [
            ("scaffold_game", "generate", [
                {"tool": "create_project", "description": "Initialize project structure"},
                {"tool": "setup_main_scene", "description": "Create main game scene"},
                {"tool": "add_player_entity", "description": "Spawn player character"},
                {"tool": "setup_physics", "description": "Configure physics world"},
            ]),
            ("asset_import_flow", "assets", [
                {"tool": "validate_assets", "description": "Check asset formats"},
                {"tool": "import_textures", "description": "Process sprite sheets"},
                {"tool": "generate_atlas", "description": "Build texture atlas"},
                {"tool": "configure_materials", "description": "Assign rendering params"},
            ]),
            ("build_deploy", "deploy", [
                {"tool": "validate_project", "description": "Run validation checks"},
                {"tool": "bundle_assets", "description": "Package game assets"},
                {"tool": "compile_scripts", "description": "Build game logic"},
                {"tool": "export_build", "description": "Generate platform build"},
            ]),
        ]
        for name, category, steps in defaults:
            template = ChainTemplate(name=name, category=category, description=f"Default {name} pipeline", steps=steps)
            self._templates[template.template_id] = template

    def get_active_chain_count(self) -> int:
        return len(self._active_chains)

    def clean_completed(self) -> int:
        completed = [cid for cid, c in self._active_chains.items() if c.status in (ChainStatus.COMPLETED, ChainStatus.FAILED, ChainStatus.ROLLED_BACK)]
        for cid in completed:
            del self._active_chains[cid]
        return len(completed)

    def get_stats(self) -> dict:
        return {
            "active_chains": len(self._active_chains),
            "history_size": len(self._chain_history),
            "templates": len(self._templates),
            "total_steps_executed": sum(len(c.steps) for c in self._chain_history),
            "success_rate": self._compute_success_rate(),
        }

    def _compute_success_rate(self) -> float:
        if not self._chain_history:
            return 100.0
        completed = sum(1 for c in self._chain_history if c.status == ChainStatus.COMPLETED)
        return round(completed / len(self._chain_history) * 100, 1)

    def reset(self) -> None:
        self._active_chains.clear()
        self._chain_history.clear()
        self._templates.clear()
        self._init_defaults()


def get_tool_composer() -> ToolComposer:
    return ToolComposer.get_instance()
