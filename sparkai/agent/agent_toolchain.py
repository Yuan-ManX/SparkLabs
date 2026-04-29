"""
SparkAI Agent - Tool Chain Engine

A dynamic tool composition and execution system that allows agents
to create custom tool chains, manage tool dependencies, and execute
complex multi-step operations with parallel execution support.

Architecture:
  ToolChainEngine
    |-- ToolChain (ordered sequence of tool invocations)
    |-- ChainStep (individual tool invocation with I/O mapping)
    |-- DependencyResolver (resolve execution order from dependencies)
    |-- ParallelExecutor (execute independent steps concurrently)
    |-- ChainTemplate (reusable tool chain templates)
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ChainStatus(Enum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(Enum):
    PENDING = "pending"
    BLOCKED = "blocked"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepType(Enum):
    TOOL = "tool"
    CONDITION = "condition"
    TRANSFORM = "transform"
    AGGREGATE = "aggregate"
    BRANCH = "branch"
    LOOP = "loop"


class TemplateCategory(Enum):
    GAME_GEN = "game_gen"
    WORLD_BUILD = "world_build"
    ASSET_GEN = "asset_gen"
    CODE_GEN = "code_gen"
    TEST = "test"
    DEPLOY = "deploy"
    ANALYSIS = "analysis"
    CUSTOM = "custom"


@dataclass
class ChainStep:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    step_type: StepType = StepType.TOOL
    tool_name: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_key: str = ""
    depends_on: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_ms: float = 30000.0
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "step_type": self.step_type.value,
            "tool_name": self.tool_name,
            "params": self.params,
            "input_mapping": self.input_mapping,
            "output_key": self.output_key,
            "depends_on": self.depends_on,
            "condition": self.condition,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_ms": self.timeout_ms,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class ToolChain:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    steps: List[ChainStep] = field(default_factory=list)
    status: ChainStatus = ChainStatus.DRAFT
    context: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "step_count": len(self.steps),
            "status": self.status.value,
            "context_keys": list(self.context.keys()),
            "result_keys": list(self.results.keys()),
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class ChainTemplate:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: TemplateCategory = TemplateCategory.CUSTOM
    description: str = ""
    step_definitions: List[Dict[str, Any]] = field(default_factory=list)
    default_params: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "step_definitions": self.step_definitions,
            "default_params": self.default_params,
            "tags": self.tags,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at,
        }


class DependencyResolver:
    """
    Resolves execution order from step dependencies using
    topological sort with parallel group detection.
    """

    @staticmethod
    def resolve(steps: List[ChainStep]) -> List[List[ChainStep]]:
        step_map = {s.id: s for s in steps}
        in_degree: Dict[str, int] = {s.id: 0 for s in steps}
        dependents: Dict[str, List[str]] = {s.id: [] for s in steps}

        for step in steps:
            for dep_id in step.depends_on:
                if dep_id in step_map:
                    in_degree[step.id] += 1
                    dependents[dep_id].append(step.id)

        groups: List[List[ChainStep]] = []
        remaining = set(s.id for s in steps)

        while remaining:
            ready = [sid for sid in remaining if in_degree[sid] == 0]
            if not ready:
                break

            group = [step_map[sid] for sid in ready if sid in step_map]
            groups.append(group)

            for sid in ready:
                remaining.remove(sid)
                for dep_id in dependents[sid]:
                    in_degree[dep_id] -= 1

        return groups


class ParallelExecutor:
    """
    Executes independent steps concurrently with configurable
    concurrency limits and timeout handling.
    """

    def __init__(self, max_concurrency: int = 5) -> None:
        self._max_concurrency = max_concurrency
        self._execution_count: int = 0
        self._success_count: int = 0
        self._failure_count: int = 0

    async def execute_group(
        self,
        steps: List[ChainStep],
        context: Dict[str, Any],
        tool_executor: Optional[Any] = None,
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def run_step(step: ChainStep) -> Tuple[str, Dict[str, Any], Optional[str]]:
            async with semaphore:
                step.status = StepStatus.RUNNING
                step.started_at = time.time()
                self._execution_count += 1

                try:
                    resolved_params = self._resolve_params(step, context)

                    if tool_executor:
                        result = await asyncio.wait_for(
                            tool_executor(step.tool_name, resolved_params),
                            timeout=step.timeout_ms / 1000.0,
                        )
                    else:
                        result = {
                            "tool": step.tool_name,
                            "params": resolved_params,
                            "output": f"Simulated output for {step.tool_name}",
                        }

                    step.status = StepStatus.COMPLETED
                    step.result = result
                    step.completed_at = time.time()
                    self._success_count += 1
                    return step.id, result, None

                except asyncio.TimeoutError:
                    step.status = StepStatus.FAILED
                    step.error = f"Timeout after {step.timeout_ms}ms"
                    step.completed_at = time.time()
                    self._failure_count += 1
                    return step.id, {}, step.error

                except Exception as e:
                    step.status = StepStatus.FAILED
                    step.error = str(e)
                    step.completed_at = time.time()
                    self._failure_count += 1
                    return step.id, {}, step.error

        tasks = [run_step(step) for step in steps]
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for task_result in task_results:
            if isinstance(task_result, Exception):
                continue
            step_id, result, error = task_result
            if result:
                results[step_id] = result

        return results

    def _resolve_params(
        self,
        step: ChainStep,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        resolved = dict(step.params)

        for param_key, context_key in step.input_mapping.items():
            if context_key in context:
                resolved[param_key] = context[context_key]

        return resolved

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_executions": self._execution_count,
            "successful": self._success_count,
            "failed": self._failure_count,
            "max_concurrency": self._max_concurrency,
        }


class ToolChainEngine:
    """
    Central tool chain management system for the SparkLabs AI-native game engine.

    Provides dynamic tool composition, dependency resolution, parallel
    execution, and reusable chain templates for complex multi-step operations.
    """

    def __init__(self, max_concurrency: int = 5) -> None:
        self._chains: Dict[str, ToolChain] = {}
        self._templates: Dict[str, ChainTemplate] = {}
        self._resolver = DependencyResolver()
        self._executor = ParallelExecutor(max_concurrency)
        self._chain_count: int = 0
        self._template_count: int = 0
        self._execution_count: int = 0
        self._seed_templates()

    def _seed_templates(self) -> None:
        templates = [
            ("full_game_gen", "Full Game Generation", TemplateCategory.GAME_GEN,
             "End-to-end game generation from concept to playable build",
             [
                 {"name": "Analyze Prompt", "step_type": "tool", "tool_name": "analyze_prompt", "output_key": "analysis"},
                 {"name": "Generate Blueprint", "step_type": "tool", "tool_name": "generate_blueprint", "depends_on": ["Analyze Prompt"], "output_key": "blueprint"},
                 {"name": "Generate Code", "step_type": "tool", "tool_name": "generate_code", "depends_on": ["Generate Blueprint"], "output_key": "code"},
                 {"name": "Generate Assets", "step_type": "tool", "tool_name": "generate_assets", "depends_on": ["Generate Blueprint"], "output_key": "assets"},
                 {"name": "Build World", "step_type": "tool", "tool_name": "build_world", "depends_on": ["Generate Code", "Generate Assets"], "output_key": "world"},
                 {"name": "Run Playtest", "step_type": "tool", "tool_name": "run_playtest", "depends_on": ["Build World"], "output_key": "playtest"},
                 {"name": "Quality Gate", "step_type": "tool", "tool_name": "quality_check", "depends_on": ["Run Playtest"], "output_key": "quality"},
             ],
             ["game", "generation", "pipeline"]),
            ("world_gen", "World Generation", TemplateCategory.WORLD_BUILD,
             "Procedural world generation with terrain, structures, and entities",
             [
                 {"name": "Parse World Spec", "step_type": "tool", "tool_name": "parse_world_spec", "output_key": "spec"},
                 {"name": "Generate Terrain", "step_type": "tool", "tool_name": "generate_terrain", "depends_on": ["Parse World Spec"], "output_key": "terrain"},
                 {"name": "Place Structures", "step_type": "tool", "tool_name": "place_structures", "depends_on": ["Generate Terrain"], "output_key": "structures"},
                 {"name": "Spawn Entities", "step_type": "tool", "tool_name": "spawn_entities", "depends_on": ["Place Structures"], "output_key": "entities"},
                 {"name": "Set Environment", "step_type": "tool", "tool_name": "set_environment", "depends_on": ["Generate Terrain"], "output_key": "environment"},
             ],
             ["world", "terrain", "procedural"]),
            ("code_review", "Code Review Chain", TemplateCategory.CODE_GEN,
             "Automated code review with quality checks and suggestions",
             [
                 {"name": "Parse Code", "step_type": "tool", "tool_name": "parse_code", "output_key": "parsed"},
                 {"name": "Static Analysis", "step_type": "tool", "tool_name": "static_analysis", "depends_on": ["Parse Code"], "output_key": "static"},
                 {"name": "Pattern Check", "step_type": "tool", "tool_name": "pattern_check", "depends_on": ["Parse Code"], "output_key": "patterns"},
                 {"name": "Performance Review", "step_type": "tool", "tool_name": "performance_review", "depends_on": ["Static Analysis"], "output_key": "perf"},
                 {"name": "Generate Report", "step_type": "tool", "tool_name": "generate_report", "depends_on": ["Pattern Check", "Performance Review"], "output_key": "report"},
             ],
             ["code", "review", "quality"]),
        ]

        for tid, name, cat, desc, steps, tags in templates:
            template = ChainTemplate(
                id=tid,
                name=name,
                category=cat,
                description=desc,
                step_definitions=steps,
                tags=tags,
            )
            self._templates[tid] = template
            self._template_count += 1

    def create_chain(
        self,
        name: str,
        description: str = "",
        steps: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolChain:
        chain = ToolChain(
            name=name,
            description=description,
            context=context or {},
        )

        if steps:
            for step_data in steps:
                step = ChainStep(
                    name=step_data.get("name", ""),
                    step_type=StepType(step_data.get("step_type", "tool")),
                    tool_name=step_data.get("tool_name", ""),
                    params=step_data.get("params", {}),
                    input_mapping=step_data.get("input_mapping", {}),
                    output_key=step_data.get("output_key", ""),
                    depends_on=step_data.get("depends_on", []),
                    condition=step_data.get("condition"),
                    max_retries=step_data.get("max_retries", 3),
                    timeout_ms=step_data.get("timeout_ms", 30000.0),
                )
                chain.steps.append(step)

            name_to_id: Dict[str, str] = {s.name: s.id for s in chain.steps if s.name}
            for step in chain.steps:
                resolved_deps: List[str] = []
                for dep in step.depends_on:
                    if dep in name_to_id:
                        resolved_deps.append(name_to_id[dep])
                    else:
                        resolved_deps.append(dep)
                step.depends_on = resolved_deps

        self._chains[chain.id] = chain
        self._chain_count += 1
        return chain

    def create_from_template(
        self,
        template_id: str,
        name: str = "",
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[ToolChain]:
        template = self._templates.get(template_id)
        if not template:
            return None

        template.usage_count += 1
        chain = self.create_chain(
            name=name or template.name,
            description=template.description,
            steps=template.step_definitions,
            context={**template.default_params, **(params or {})},
        )
        chain.status = ChainStatus.READY
        return chain

    def get_chain(self, chain_id: str) -> Optional[Dict[str, Any]]:
        chain = self._chains.get(chain_id)
        if chain:
            return chain.to_dict()
        return None

    def list_chains(self, status: Optional[ChainStatus] = None) -> List[Dict[str, Any]]:
        chains = list(self._chains.values())
        if status:
            chains = [c for c in chains if c.status == status]
        return [c.to_dict() for c in chains]

    def add_step(
        self,
        chain_id: str,
        name: str,
        step_type: str = "tool",
        tool_name: str = "",
        params: Optional[Dict[str, Any]] = None,
        input_mapping: Optional[Dict[str, str]] = None,
        output_key: str = "",
        depends_on: Optional[List[str]] = None,
        condition: Optional[str] = None,
        max_retries: int = 3,
        timeout_ms: float = 30000.0,
    ) -> Optional[Dict[str, Any]]:
        chain = self._chains.get(chain_id)
        if not chain:
            return None

        step = ChainStep(
            name=name,
            step_type=StepType(step_type),
            tool_name=tool_name,
            params=params or {},
            input_mapping=input_mapping or {},
            output_key=output_key,
            depends_on=depends_on or [],
            condition=condition,
            max_retries=max_retries,
            timeout_ms=timeout_ms,
        )
        chain.steps.append(step)
        return step.to_dict()

    def remove_step(self, chain_id: str, step_id: str) -> bool:
        chain = self._chains.get(chain_id)
        if not chain:
            return False

        before = len(chain.steps)
        chain.steps = [s for s in chain.steps if s.id != step_id]
        for step in chain.steps:
            step.depends_on = [d for d in step.depends_on if d != step_id]
        return len(chain.steps) < before

    def resolve_chain(self, chain_id: str) -> Optional[Dict[str, Any]]:
        chain = self._chains.get(chain_id)
        if not chain:
            return None

        groups = self._resolver.resolve(chain.steps)
        return {
            "chain_id": chain_id,
            "execution_groups": [
                {
                    "group_index": i,
                    "parallel_steps": [s.to_dict() for s in group],
                    "step_count": len(group),
                }
                for i, group in enumerate(groups)
            ],
            "total_groups": len(groups),
            "total_steps": len(chain.steps),
            "max_parallelism": max(len(g) for g in groups) if groups else 0,
        }

    async def execute_chain(self, chain_id: str) -> Optional[Dict[str, Any]]:
        chain = self._chains.get(chain_id)
        if not chain:
            return None

        chain.status = ChainStatus.RUNNING
        chain.started_at = time.time()
        self._execution_count += 1

        groups = self._resolver.resolve(chain.steps)

        for group_index, group in enumerate(groups):
            for step in group:
                step.status = StepStatus.READY

            group_results = await self._executor.execute_group(
                group, chain.context
            )

            for step_id, result in group_results.items():
                chain.results[step_id] = result
                step = next((s for s in chain.steps if s.id == step_id), None)
                if step and step.output_key:
                    chain.context[step.output_key] = result

            failed_in_group = [s for s in group if s.status == StepStatus.FAILED]
            if failed_in_group:
                chain.status = ChainStatus.FAILED
                chain.error = f"Step(s) failed: {', '.join(s.name for s in failed_in_group)}"
                chain.completed_at = time.time()
                return chain.to_dict()

        chain.status = ChainStatus.COMPLETED
        chain.completed_at = time.time()
        return chain.to_dict()

    def cancel_chain(self, chain_id: str) -> bool:
        chain = self._chains.get(chain_id)
        if not chain or chain.status != ChainStatus.RUNNING:
            return False
        chain.status = ChainStatus.CANCELLED
        chain.completed_at = time.time()
        return True

    def delete_chain(self, chain_id: str) -> bool:
        if chain_id in self._chains:
            del self._chains[chain_id]
            self._chain_count -= 1
            return True
        return False

    def add_template(
        self,
        name: str,
        category: str = "custom",
        description: str = "",
        step_definitions: Optional[List[Dict[str, Any]]] = None,
        default_params: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> ChainTemplate:
        template = ChainTemplate(
            name=name,
            category=TemplateCategory(category),
            description=description,
            step_definitions=step_definitions or [],
            default_params=default_params or {},
            tags=tags or [],
        )
        self._templates[template.id] = template
        self._template_count += 1
        return template

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        template = self._templates.get(template_id)
        if template:
            return template.to_dict()
        return None

    def list_templates(self, category: Optional[TemplateCategory] = None) -> List[Dict[str, Any]]:
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return [t.to_dict() for t in templates]

    def get_stats(self) -> Dict[str, Any]:
        status_counts: Dict[str, int] = {}
        for chain in self._chains.values():
            key = chain.status.value
            status_counts[key] = status_counts.get(key, 0) + 1

        return {
            "total_chains": self._chain_count,
            "total_templates": self._template_count,
            "total_executions": self._execution_count,
            "by_status": status_counts,
            "executor_stats": self._executor.get_stats(),
        }


_global_toolchain_engine: Optional[ToolChainEngine] = None


def get_toolchain_engine() -> ToolChainEngine:
    global _global_toolchain_engine
    if _global_toolchain_engine is None:
        _global_toolchain_engine = ToolChainEngine()
    return _global_toolchain_engine
