"""
SparkLabs Agent - Skill Composition Engine

Composes and chains game development skills into automated workflows.
Each skill chain is an ordered or parallel sequence of SkillSteps that
represent individual capability invocations across agent subsystems.
Chains can be saved as reusable SkillTemplates and instantiated on demand.

Architecture:
  SkillComposer
    |-- SkillStep (single capability invocation with I/O spec)
    |-- SkillChain (ordered or parallel step sequence)
    |-- SkillTemplate (reusable chain blueprint)
    |-- Chain execution (sequential or parallel with result chaining)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SkillDomain(Enum):
    GAME_GENERATION = "game_generation"
    ASSET_CREATION = "asset_creation"
    LEVEL_BUILDING = "level_building"
    CODE_COMPLETION = "code_completion"
    TESTING = "testing"
    BALANCING = "balancing"
    PUBLISHING = "publishing"
    DOCUMENTATION = "documentation"


class ChainStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SkillStep:
    """
    A single step in a skill chain representing one capability invocation
    by a specific agent subsystem. Steps carry typed input/output
    specifications and configurable retry/timeout behavior.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    step_name: str = ""
    skill_type: str = ""
    agent_name: str = ""
    input_spec: Dict[str, Any] = field(default_factory=dict)
    output_spec: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 60
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "step_name": self.step_name,
            "skill_type": self.skill_type,
            "agent_name": self.agent_name,
            "input_spec": self.input_spec,
            "output_spec": self.output_spec,
            "parameters": self.parameters,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
        }


@dataclass
class SkillChain:
    """
    An ordered or parallel sequence of SkillSteps that together form an
    automated game development workflow. Chains track execution status
    and accumulate per-step results keyed by step_name.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    steps: List[SkillStep] = field(default_factory=list)
    domain: SkillDomain = SkillDomain.GAME_GENERATION
    is_parallel: bool = False
    status: ChainStatus = ChainStatus.PENDING
    results: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "step_count": len(self.steps),
            "domain": self.domain.value,
            "is_parallel": self.is_parallel,
            "status": self.status.value,
            "results": self.results,
            "created_at": self.created_at,
        }


@dataclass
class SkillTemplate:
    """
    A reusable skill chain blueprint. Templates store a pre-built chain
    along with usage tracking and success rate so the engine can surface
    the most reliable workflows.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    domain: SkillDomain = SkillDomain.GAME_GENERATION
    chain: Optional[SkillChain] = None
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain.value,
            "chain_id": self.chain.id if self.chain else None,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at,
        }


class SkillComposer:
    """
    Central skill composition engine for the SparkLabs AI-native game engine.

    Composes and chains game development skills into automated workflows.
    Supports sequential and parallel execution, reusable templates,
    import/export, and execution logging.
    """

    _instance: Optional["SkillComposer"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._chains: Dict[str, SkillChain] = {}
        self._templates: Dict[str, SkillTemplate] = {}
        self._chain_count: int = 0
        self._execution_log: List[Dict[str, Any]] = []
        self._seed_templates()

    @classmethod
    def get_instance(cls) -> "SkillComposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed_templates(self) -> None:
        seeds = [
            (
                "full_game_generation",
                "Full Game Generation Pipeline",
                SkillDomain.GAME_GENERATION,
                "End-to-end game generation from concept to exported project",
                False,
                [
                    ("generate_game_concept", "generate", "game_designer",
                     {"description": "High-level game concept description"},
                     {"type": "structured_game_concept"},
                     {"detail_level": "full", "include_mechanics": True}),
                    ("build_world_layout", "generate", "world_builder",
                     {"description": "Game concept from previous step"},
                     {"type": "world_layout_data"},
                     {"world_size": "medium", "terrain_type": "procedural"}),
                    ("create_characters", "generate", "asset_creator",
                     {"description": "World layout and game concept"},
                     {"type": "character_definitions"},
                     {"character_count": 4, "include_npcs": True}),
                    ("balance_mechanics", "optimize", "game_balancer",
                     {"description": "Game mechanics specification"},
                     {"type": "balanced_mechanics"},
                     {"difficulty_curve": "linear", "target_session_minutes": 30}),
                    ("generate_code", "generate", "game_coder",
                     {"description": "Complete game specification"},
                     {"type": "generated_source_code"},
                     {"language": "python", "framework": "pygame"}),
                    ("validate_output", "validate", "quality_gate",
                     {"description": "Generated code and assets"},
                     {"type": "validation_report"},
                     {"strict_mode": True, "fail_on_warnings": False}),
                    ("export_project", "export", "build_orchestrator",
                     {"description": "Validated project files"},
                     {"type": "exported_project_path"},
                     {"target_platform": "web", "compress": True}),
                ],
            ),
            (
                "asset_creation",
                "Asset Creation Pipeline",
                SkillDomain.ASSET_CREATION,
                "Generate, validate, and optimize game assets from concept to final form",
                False,
                [
                    ("design_asset_concept", "generate", "asset_designer",
                     {"description": "Visual style and asset requirements"},
                     {"type": "asset_concept_document"},
                     {"style": "2d_pixel_art", "resolution": "64x64"}),
                    ("generate_asset_parameters", "generate", "asset_generator",
                     {"description": "Asset concept from previous step"},
                     {"type": "asset_generation_params"},
                     {"format": "png", "color_palette": "vibrant"}),
                    ("create_preset", "transform", "preset_manager",
                     {"description": "Generated asset parameters"},
                     {"type": "asset_preset_record"},
                     {"preset_type": "reusable", "include_variations": 3}),
                    ("validate_assets", "validate", "asset_validator",
                     {"description": "Generated asset files"},
                     {"type": "asset_validation_report"},
                     {"check_dimensions": True, "check_format": True}),
                    ("optimize_assets", "optimize", "asset_optimizer",
                     {"description": "Validated assets with report"},
                     {"type": "optimized_asset_bundle"},
                     {"target_size_kb": 512, "strip_metadata": True}),
                ],
            ),
            (
                "level_design",
                "Level Design Pipeline",
                SkillDomain.LEVEL_BUILDING,
                "Design and validate complete game levels with tiles, entities, and lighting",
                False,
                [
                    ("plan_level_layout", "generate", "level_designer",
                     {"description": "Level theme and gameplay requirements"},
                     {"type": "level_layout_plan"},
                     {"grid_size": "32x32", "theme": "dungeon"}),
                    ("generate_tileset", "generate", "tile_generator",
                     {"description": "Level layout plan"},
                     {"type": "tileset_definition"},
                     {"tile_size": 32, "auto_tile": True}),
                    ("place_entities", "generate", "entity_placer",
                     {"description": "Tileset and layout plan"},
                     {"type": "entity_placement_data"},
                     {"enemy_density": 0.2, "item_density": 0.1}),
                    ("set_collisions", "transform", "collision_builder",
                     {"description": "Entity and tile placement data"},
                     {"type": "collision_map"},
                     {"collision_type": "grid", "precision": "tile"}),
                    ("add_lighting", "transform", "lighting_engine",
                     {"description": "Complete level data with collisions"},
                     {"type": "lighting_map"},
                     {"ambient_color": "#1a1a2e", "light_count": 15}),
                    ("validate_level", "validate", "level_validator",
                     {"description": "Complete level with lighting"},
                     {"type": "level_validation_report"},
                     {"check_playability": True, "check_performance": True}),
                ],
            ),
        ]

        for name, display_name, domain, description, is_parallel, step_defs in seeds:
            chain = SkillChain(
                name=display_name,
                description=description,
                domain=domain,
                is_parallel=is_parallel,
            )
            for step_name, skill_type, agent_name, input_spec, output_spec, parameters in step_defs:
                step = SkillStep(
                    step_name=step_name,
                    skill_type=skill_type,
                    agent_name=agent_name,
                    input_spec=input_spec,
                    output_spec=output_spec,
                    parameters=parameters,
                )
                chain.steps.append(step)

            self._chains[chain.id] = chain
            self._chain_count += 1

            template = SkillTemplate(
                name=display_name,
                description=description,
                domain=domain,
                chain=chain,
            )
            self._templates[template.id] = template

    def create_chain(
        self,
        name: str,
        description: str = "",
        domain: SkillDomain = SkillDomain.GAME_GENERATION,
        is_parallel: bool = False,
    ) -> SkillChain:
        chain = SkillChain(
            name=name,
            description=description,
            domain=domain,
            is_parallel=is_parallel,
        )
        self._chains[chain.id] = chain
        self._chain_count += 1
        return chain

    def add_step(
        self,
        chain_id: str,
        step_name: str,
        skill_type: str,
        agent_name: str,
        input_spec: Optional[Dict[str, Any]] = None,
        output_spec: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 60,
        retry_count: int = 0,
    ) -> Optional[SkillStep]:
        chain = self._chains.get(chain_id)
        if chain is None:
            return None

        step = SkillStep(
            step_name=step_name,
            skill_type=skill_type,
            agent_name=agent_name,
            input_spec=input_spec or {},
            output_spec=output_spec or {},
            parameters=parameters or {},
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
        )
        chain.steps.append(step)
        return step

    def remove_step(self, chain_id: str, step_index: int) -> bool:
        chain = self._chains.get(chain_id)
        if chain is None:
            return False
        if 0 <= step_index < len(chain.steps):
            chain.steps.pop(step_index)
            return True
        return False

    def insert_step(
        self,
        chain_id: str,
        index: int,
        step: SkillStep,
    ) -> bool:
        chain = self._chains.get(chain_id)
        if chain is None:
            return False
        if 0 <= index <= len(chain.steps):
            chain.steps.insert(index, step)
            return True
        return False

    def execute_chain(
        self,
        chain_id: str,
        initial_input: Dict[str, Any],
    ) -> Optional[SkillChain]:
        chain = self._chains.get(chain_id)
        if chain is None:
            return None

        chain.status = ChainStatus.RUNNING
        chain.results = {}

        if chain.is_parallel:
            for step in chain.steps:
                result = self._execute_step(step, initial_input)
                chain.results[step.step_name] = result
                self._execution_log.append({
                    "chain_id": chain_id,
                    "step_name": step.step_name,
                    "status": "completed",
                    "timestamp": time.time(),
                })
        else:
            current_input = dict(initial_input)
            for step in chain.steps:
                result = self._execute_step(step, current_input)
                chain.results[step.step_name] = result

                current_input = result if isinstance(result, dict) else {"output": result}

                self._execution_log.append({
                    "chain_id": chain_id,
                    "step_name": step.step_name,
                    "status": "completed",
                    "timestamp": time.time(),
                })

        chain.status = ChainStatus.COMPLETED
        return chain

    def _execute_step(
        self,
        step: SkillStep,
        step_input: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "step_name": step.step_name,
            "skill_type": step.skill_type,
            "agent_name": step.agent_name,
            "input_snapshot": step_input,
            "output_spec": step.output_spec,
            "parameters": step.parameters,
            "executed_at": time.time(),
            "status": "simulated_success",
        }

    def get_execution_log(self, chain_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if chain_id is None:
            return list(self._execution_log)
        return [entry for entry in self._execution_log if entry.get("chain_id") == chain_id]

    def create_template(
        self,
        chain_id: str,
        name: str,
        description: str = "",
        domain: Optional[SkillDomain] = None,
    ) -> Optional[SkillTemplate]:
        chain = self._chains.get(chain_id)
        if chain is None:
            return None

        template = SkillTemplate(
            name=name or chain.name,
            description=description or chain.description,
            domain=domain if domain is not None else chain.domain,
            chain=chain,
        )
        self._templates[template.id] = template
        return template

    def get_templates_by_domain(self, domain: SkillDomain) -> List[SkillTemplate]:
        return [t for t in self._templates.values() if t.domain == domain]

    def instantiate_template(self, template_id: str) -> Optional[str]:
        template = self._templates.get(template_id)
        if template is None or template.chain is None:
            return None

        new_chain = SkillChain(
            name=template.chain.name,
            description=template.chain.description,
            steps=[
                SkillStep(
                    step_name=s.step_name,
                    skill_type=s.skill_type,
                    agent_name=s.agent_name,
                    input_spec=dict(s.input_spec),
                    output_spec=dict(s.output_spec),
                    parameters=dict(s.parameters),
                    timeout_seconds=s.timeout_seconds,
                    retry_count=s.retry_count,
                )
                for s in template.chain.steps
            ],
            domain=template.domain,
            is_parallel=template.chain.is_parallel,
        )
        self._chains[new_chain.id] = new_chain
        self._chain_count += 1

        template.usage_count += 1
        return new_chain.id

    def get_chain_progress(self, chain_id: str) -> Optional[Tuple[int, int, float]]:
        chain = self._chains.get(chain_id)
        if chain is None:
            return None

        total_steps = len(chain.steps)
        if total_steps == 0:
            return (0, 0, 0.0)

        if chain.status == ChainStatus.COMPLETED:
            completed_steps = total_steps
        elif chain.status == ChainStatus.RUNNING:
            completed_steps = len(chain.results)
        elif chain.status in (ChainStatus.FAILED, ChainStatus.CANCELLED):
            completed_steps = len(chain.results)
        else:
            completed_steps = 0

        percentage = (completed_steps / total_steps) * 100.0
        return (completed_steps, total_steps, percentage)

    def cancel_chain(self, chain_id: str) -> bool:
        chain = self._chains.get(chain_id)
        if chain is None:
            return False
        if chain.status not in (ChainStatus.PENDING, ChainStatus.RUNNING):
            return False
        chain.status = ChainStatus.CANCELLED
        self._execution_log.append({
            "chain_id": chain_id,
            "step_name": "__cancel__",
            "status": "cancelled",
            "timestamp": time.time(),
        })
        return True

    def export_chain(self, chain_id: str) -> Optional[Dict[str, Any]]:
        chain = self._chains.get(chain_id)
        if chain is None:
            return None
        return chain.to_dict()

    def import_chain(self, data: Dict[str, Any]) -> Optional[str]:
        try:
            steps = []
            for step_data in data.get("steps", []):
                step = SkillStep(
                    id=step_data.get("id", uuid.uuid4().hex),
                    step_name=step_data.get("step_name", ""),
                    skill_type=step_data.get("skill_type", ""),
                    agent_name=step_data.get("agent_name", ""),
                    input_spec=step_data.get("input_spec", {}),
                    output_spec=step_data.get("output_spec", {}),
                    parameters=step_data.get("parameters", {}),
                    timeout_seconds=step_data.get("timeout_seconds", 60),
                    retry_count=step_data.get("retry_count", 0),
                )
                steps.append(step)

            domain_raw = data.get("domain", "game_generation")
            domain = SkillDomain(domain_raw) if domain_raw in [d.value for d in SkillDomain] else SkillDomain.GAME_GENERATION

            raw_status = data.get("status", "pending")
            status = ChainStatus(raw_status) if raw_status in [s.value for s in ChainStatus] else ChainStatus.PENDING

            chain = SkillChain(
                id=data.get("id", uuid.uuid4().hex),
                name=data.get("name", ""),
                description=data.get("description", ""),
                steps=steps,
                domain=domain,
                is_parallel=data.get("is_parallel", False),
                status=status,
                results=data.get("results", {}),
                created_at=data.get("created_at", time.time()),
            )
            self._chains[chain.id] = chain
            self._chain_count += 1
            return chain.id
        except Exception:
            return None

    def get_stats(self) -> Dict[str, Any]:
        domain_breakdown: Dict[str, int] = {}
        for chain in self._chains.values():
            key = chain.domain.value
            domain_breakdown[key] = domain_breakdown.get(key, 0) + 1

        status_breakdown: Dict[str, int] = {}
        for chain in self._chains.values():
            key = chain.status.value
            status_breakdown[key] = status_breakdown.get(key, 0) + 1

        return {
            "chain_count": self._chain_count,
            "template_count": len(self._templates),
            "domain_breakdown": domain_breakdown,
            "status_breakdown": status_breakdown,
            "total_log_entries": len(self._execution_log),
        }

    def get_chain(self, chain_id: str) -> Optional[SkillChain]:
        return self._chains.get(chain_id)

    def get_template(self, template_id: str) -> Optional[SkillTemplate]:
        return self._templates.get(template_id)

    def list_chains(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._chains.values()]

    def list_templates(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._templates.values()]

    def delete_chain(self, chain_id: str) -> bool:
        if chain_id in self._chains:
            del self._chains[chain_id]
            self._chain_count -= 1
            return True
        return False


def get_skill_composer() -> SkillComposer:
    return SkillComposer.get_instance()