"""
SparkAI Agent - Skill Evolution Engine

A skill evolution system for the AI-native game engine that learns from
experience, maintains evolving skill templates, and builds a living
protocol of verified fixes. Skills grow over time through usage,
feedback, and adaptation.

Architecture:
  SkillEvolutionEngine
    |-- SkillTemplate (reusable capability pattern)
    |-- DebugProtocol (verified fix protocol)
    |-- SkillExecution (execution record with feedback)
    |-- EvolutionCycle (skill adaptation cycle)
    |-- SkillLineage (skill ancestry tracking)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class SkillDomain(Enum):
    CODE_GEN = "code_gen"
    WORLD_BUILD = "world_build"
    ASSET_GEN = "asset_gen"
    AUDIO_GEN = "audio_gen"
    NARRATIVE = "narrative"
    QA_TEST = "qa_test"
    DESIGN = "design"
    OPTIMIZATION = "optimization"
    DEBUG = "debug"
    DEPLOY = "deploy"


class SkillMaturity(Enum):
    SEED = "seed"
    SPROUT = "sprout"
    GROWING = "growing"
    MATURE = "mature"
    EXPERT = "expert"
    MASTER = "master"


class ExecutionOutcome(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


class FixStatus(Enum):
    PROPOSED = "proposed"
    TESTED = "tested"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"


class EvolutionType(Enum):
    PARAMETER_TUNING = "parameter_tuning"
    PATTERN_REFINEMENT = "pattern_refinement"
    SCOPE_EXPANSION = "scope_expansion"
    ERROR_ADAPTATION = "error_adaptation"
    MERGE = "merge"
    SPLIT = "split"


@dataclass
class SkillTemplate:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    domain: SkillDomain = SkillDomain.CODE_GEN
    maturity: SkillMaturity = SkillMaturity.SEED
    description: str = ""
    pattern: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    avg_execution_ms: float = 0.0
    parent_id: Optional[str] = None
    version: int = 1
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain.value,
            "maturity": self.maturity.value,
            "description": self.description,
            "pattern": self.pattern,
            "parameters": self.parameters,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "success_rate": self.success_count / max(self.usage_count, 1),
            "avg_execution_ms": self.avg_execution_ms,
            "parent_id": self.parent_id,
            "version": self.version,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class DebugProtocol:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    domain: SkillDomain = SkillDomain.DEBUG
    status: FixStatus = FixStatus.PROPOSED
    error_pattern: str = ""
    fix_pattern: str = ""
    fix_description: str = ""
    applicable_contexts: List[str] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_count: int = 0
    confidence: float = 0.0
    related_skill_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    verified_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain.value,
            "status": self.status.value,
            "error_pattern": self.error_pattern,
            "fix_pattern": self.fix_pattern,
            "fix_description": self.fix_description,
            "applicable_contexts": self.applicable_contexts,
            "verification_steps": self.verification_steps,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "confidence": self.confidence,
            "related_skill_ids": self.related_skill_ids,
            "created_at": self.created_at,
            "verified_at": self.verified_at,
        }


@dataclass
class SkillExecution:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    skill_id: str = ""
    outcome: ExecutionOutcome = ExecutionOutcome.SUCCESS
    execution_time_ms: float = 0.0
    input_snapshot: Dict[str, Any] = field(default_factory=dict)
    output_snapshot: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    feedback: str = ""
    rating: float = 0.0
    triggered_protocol_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "outcome": self.outcome.value,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
            "feedback": self.feedback,
            "rating": self.rating,
            "triggered_protocol_id": self.triggered_protocol_id,
            "created_at": self.created_at,
        }


@dataclass
class EvolutionCycle:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    skill_id: str = ""
    evolution_type: EvolutionType = EvolutionType.PARAMETER_TUNING
    before_state: Dict[str, Any] = field(default_factory=dict)
    after_state: Dict[str, Any] = field(default_factory=dict)
    trigger: str = ""
    improvement_score: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "evolution_type": self.evolution_type.value,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "trigger": self.trigger,
            "improvement_score": self.improvement_score,
            "created_at": self.created_at,
        }


class SkillEvolutionEngine:
    """
    Central skill evolution system for the SparkLabs AI-native game engine.

    Skills grow through usage, feedback, and adaptation. The system
    maintains a library of evolving skill templates and a living
    protocol of verified debug fixes.
    """

    def __init__(self) -> None:
        self._skills: Dict[str, SkillTemplate] = {}
        self._protocols: Dict[str, DebugProtocol] = {}
        self._executions: List[SkillExecution] = []
        self._evolutions: List[EvolutionCycle] = []
        self._skill_count: int = 0
        self._protocol_count: int = 0
        self._seed_skills()

    def _seed_skills(self) -> None:
        seed = [
            ("game_scaffold", "Game Scaffold", SkillDomain.CODE_GEN, SkillMaturity.MATURE,
             "Generate a complete game project structure with entry point, game loop, and scene management",
             {"language": "javascript", "engine": "html5_canvas", "entry": "index.html"},
             ["prompt provided"], ["project created"]),
            ("sprite_gen", "Sprite Generation", SkillDomain.ASSET_GEN, SkillMaturity.GROWING,
             "Generate 2D sprite assets from description with proper dimensions and format",
             {"format": "png", "size": "64x64", "style": "pixel_art"},
             ["style specified"], ["sprites generated"]),
            ("level_design", "Level Design", SkillDomain.WORLD_BUILD, SkillMaturity.GROWING,
             "Design game levels with proper difficulty curve and entity placement",
             {"difficulty_curve": "linear", "entity_density": 0.3},
             ["genre specified"], ["level data generated"]),
            ("audio_sfx", "Sound Effect Synthesis", SkillDomain.AUDIO_GEN, SkillMaturity.SPROUT,
             "Synthesize sound effects from description using procedural audio generation",
             {"format": "wav", "duration_ms": 500},
             ["effect type specified"], ["audio file generated"]),
            ("narrative_arc", "Narrative Arc Construction", SkillDomain.NARRATIVE, SkillMaturity.SPROUT,
             "Construct narrative arcs with setup, rising action, climax, and resolution",
             {"arc_length": "short", "genre": "fantasy"},
             ["genre specified"], ["arc structure defined"]),
            ("perf_optimize", "Performance Optimization", SkillDomain.OPTIMIZATION, SkillMaturity.MATURE,
             "Analyze and optimize game performance bottlenecks",
             {"target_fps": 60, "budget_ms": 16.67},
             ["performance data available"], ["bottlenecks identified and fixed"]),
            ("bug_fix", "Bug Fix Protocol", SkillDomain.DEBUG, SkillMaturity.EXPERT,
             "Systematic bug diagnosis and fix using verified debug protocols",
             {"max_iterations": 3, "verification": "automated"},
             ["error description provided"], ["bug fixed and verified"]),
            ("qa_smoke", "Smoke Test", SkillDomain.QA_TEST, SkillMaturity.MATURE,
             "Run smoke tests to verify basic game functionality",
             {"test_suite": "core", "timeout_ms": 30000},
             ["game build available"], ["smoke test report generated"]),
        ]

        maturity_usage_map = {
            SkillMaturity.SEED: 0, SkillMaturity.SPROUT: 5,
            SkillMaturity.GROWING: 15, SkillMaturity.MATURE: 30,
            SkillMaturity.EXPERT: 60, SkillMaturity.MASTER: 100,
        }

        for sid, name, domain, maturity, desc, params, pre, post in seed:
            base_usage = maturity_usage_map.get(maturity, 0)
            skill = SkillTemplate(
                id=sid,
                name=name,
                domain=domain,
                maturity=maturity,
                description=desc,
                parameters=params,
                preconditions=pre,
                postconditions=post,
                usage_count=base_usage,
                success_count=int(base_usage * 0.8),
            )
            self._skills[sid] = skill
            self._skill_count += 1

        debug_protocols = [
            ("fix_null_ref", "Null Reference Fix", "TypeError: Cannot read properties of null",
             "Add null guard before property access", FixStatus.VERIFIED,
             ["javascript", "runtime"], 0.95),
            ("fix_infinite_loop", "Infinite Loop Fix", "Maximum call stack size exceeded",
             "Add loop termination condition or recursion base case", FixStatus.VERIFIED,
             ["javascript", "logic"], 0.9),
            ("fix_canvas_size", "Canvas Size Fix", "Canvas rendering at incorrect dimensions",
             "Set canvas width/height attributes to match CSS dimensions", FixStatus.VERIFIED,
             ["html5", "rendering"], 0.85),
            ("fix_event_leak", "Event Listener Leak Fix", "Event listeners not removed on cleanup",
             "Store listener references and remove in cleanup function", FixStatus.TESTED,
             ["javascript", "memory"], 0.8),
        ]

        for pid, name, error_pat, fix_pat, status, contexts, confidence in debug_protocols:
            protocol = DebugProtocol(
                id=pid,
                name=name,
                error_pattern=error_pat,
                fix_pattern=fix_pat,
                status=status,
                applicable_contexts=contexts,
                confidence=confidence,
                usage_count=int(confidence * 20),
                success_count=int(confidence * 18),
            )
            self._protocols[pid] = protocol
            self._protocol_count += 1

    def create_skill(
        self,
        name: str,
        domain: str = "code_gen",
        description: str = "",
        pattern: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        preconditions: Optional[List[str]] = None,
        postconditions: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> SkillTemplate:
        skill = SkillTemplate(
            name=name,
            domain=SkillDomain(domain),
            description=description,
            pattern=pattern,
            parameters=parameters or {},
            preconditions=preconditions or [],
            postconditions=postconditions or [],
            tags=tags or [],
        )
        self._skills[skill.id] = skill
        self._skill_count += 1
        return skill

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        skill = self._skills.get(skill_id)
        if skill:
            return skill.to_dict()
        return None

    def list_skills(
        self,
        domain: Optional[SkillDomain] = None,
        maturity: Optional[SkillMaturity] = None,
        min_success_rate: float = 0.0,
    ) -> List[Dict[str, Any]]:
        skills = list(self._skills.values())
        if domain:
            skills = [s for s in skills if s.domain == domain]
        if maturity:
            skills = [s for s in skills if s.maturity == maturity]
        if min_success_rate > 0:
            skills = [s for s in skills if s.success_count / max(s.usage_count, 1) >= min_success_rate]
        return [s.to_dict() for s in skills]

    def record_execution(
        self,
        skill_id: str,
        outcome: str = "success",
        execution_time_ms: float = 0.0,
        error_message: str = "",
        feedback: str = "",
        rating: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        skill = self._skills.get(skill_id)
        if not skill:
            return None

        execution = SkillExecution(
            skill_id=skill_id,
            outcome=ExecutionOutcome(outcome),
            execution_time_ms=execution_time_ms,
            error_message=error_message,
            feedback=feedback,
            rating=rating,
        )
        self._executions.append(execution)

        skill.usage_count += 1
        if execution.outcome in (ExecutionOutcome.SUCCESS, ExecutionOutcome.PARTIAL):
            skill.success_count += 1
        else:
            skill.fail_count += 1

        if execution_time_ms > 0:
            skill.avg_execution_ms = (
                (skill.avg_execution_ms * (skill.usage_count - 1) + execution_time_ms)
                / skill.usage_count
            )

        skill.updated_at = time.time()
        self._check_evolution(skill)

        return execution.to_dict()

    def _check_evolution(self, skill: SkillTemplate) -> None:
        maturity_thresholds = {
            SkillMaturity.SEED: 5,
            SkillMaturity.SPROUT: 15,
            SkillMaturity.GROWING: 30,
            SkillMaturity.MATURE: 60,
            SkillMaturity.EXPERT: 100,
        }

        current_threshold = maturity_thresholds.get(skill.maturity, 999)
        if skill.usage_count >= current_threshold:
            old_maturity = skill.maturity
            if skill.maturity == SkillMaturity.SEED:
                skill.maturity = SkillMaturity.SPROUT
            elif skill.maturity == SkillMaturity.SPROUT:
                skill.maturity = SkillMaturity.GROWING
            elif skill.maturity == SkillMaturity.GROWING:
                skill.maturity = SkillMaturity.MATURE
            elif skill.maturity == SkillMaturity.MATURE:
                skill.maturity = SkillMaturity.EXPERT
            elif skill.maturity == SkillMaturity.EXPERT:
                skill.maturity = SkillMaturity.MASTER

            if skill.maturity != old_maturity:
                evolution = EvolutionCycle(
                    skill_id=skill.id,
                    evolution_type=EvolutionType.PATTERN_REFINEMENT,
                    before_state={"maturity": old_maturity.value, "usage_count": skill.usage_count},
                    after_state={"maturity": skill.maturity.value, "usage_count": skill.usage_count},
                    trigger=f"Usage threshold reached: {skill.usage_count} >= {current_threshold}",
                    improvement_score=skill.maturity.value - old_maturity.value,
                )
                self._evolutions.append(evolution)

    def create_protocol(
        self,
        name: str,
        error_pattern: str,
        fix_pattern: str,
        fix_description: str = "",
        applicable_contexts: Optional[List[str]] = None,
    ) -> DebugProtocol:
        protocol = DebugProtocol(
            name=name,
            error_pattern=error_pattern,
            fix_pattern=fix_pattern,
            fix_description=fix_description,
            applicable_contexts=applicable_contexts or [],
        )
        self._protocols[protocol.id] = protocol
        self._protocol_count += 1
        return protocol

    def get_protocol(self, protocol_id: str) -> Optional[Dict[str, Any]]:
        protocol = self._protocols.get(protocol_id)
        if protocol:
            return protocol.to_dict()
        return None

    def list_protocols(self, status: Optional[FixStatus] = None) -> List[Dict[str, Any]]:
        protocols = list(self._protocols.values())
        if status:
            protocols = [p for p in protocols if p.status == status]
        return [p.to_dict() for p in protocols]

    def apply_protocol(self, protocol_id: str, success: bool = True) -> Optional[Dict[str, Any]]:
        protocol = self._protocols.get(protocol_id)
        if not protocol:
            return None

        protocol.usage_count += 1
        if success:
            protocol.success_count += 1
            protocol.confidence = min(1.0, protocol.confidence + 0.05)
            if protocol.status == FixStatus.PROPOSED and protocol.usage_count >= 3:
                protocol.status = FixStatus.TESTED
            elif protocol.status == FixStatus.TESTED and protocol.confidence >= 0.8:
                protocol.status = FixStatus.VERIFIED
                protocol.verified_at = time.time()
        else:
            protocol.confidence = max(0.0, protocol.confidence - 0.1)

        return protocol.to_dict()

    def find_protocol_for_error(self, error_message: str) -> List[Dict[str, Any]]:
        error_lower = error_message.lower()
        scored: List[Tuple[DebugProtocol, float]] = []

        for protocol in self._protocols.values():
            if protocol.status == FixStatus.DEPRECATED:
                continue
            pattern_lower = protocol.error_pattern.lower()
            if pattern_lower in error_lower or error_lower in pattern_lower:
                scored.append((protocol, protocol.confidence))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [p.to_dict() for p, _ in scored[:5]]

    def get_skill_lineage(self, skill_id: str) -> List[Dict[str, Any]]:
        lineage: List[Dict[str, Any]] = []
        current = self._skills.get(skill_id)
        while current:
            lineage.append(current.to_dict())
            if current.parent_id and current.parent_id in self._skills:
                current = self._skills[current.parent_id]
            else:
                break
        return lineage

    def get_evolution_history(self, skill_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        evolutions = self._evolutions
        if skill_id:
            evolutions = [e for e in evolutions if e.skill_id == skill_id]
        return [e.to_dict() for e in evolutions[-limit:]]

    def get_execution_history(self, skill_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        executions = self._executions
        if skill_id:
            executions = [e for e in executions if e.skill_id == skill_id]
        return [e.to_dict() for e in executions[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        domain_counts: Dict[str, int] = {}
        maturity_counts: Dict[str, int] = {}
        for skill in self._skills.values():
            domain_counts[skill.domain.value] = domain_counts.get(skill.domain.value, 0) + 1
            maturity_counts[skill.maturity.value] = maturity_counts.get(skill.maturity.value, 0) + 1

        protocol_status_counts: Dict[str, int] = {}
        for protocol in self._protocols.values():
            protocol_status_counts[protocol.status.value] = protocol_status_counts.get(protocol.status.value, 0) + 1

        outcome_counts: Dict[str, int] = {}
        for execution in self._executions:
            outcome_counts[execution.outcome.value] = outcome_counts.get(execution.outcome.value, 0) + 1

        return {
            "total_skills": self._skill_count,
            "total_protocols": self._protocol_count,
            "total_executions": len(self._executions),
            "total_evolutions": len(self._evolutions),
            "by_domain": domain_counts,
            "by_maturity": maturity_counts,
            "by_protocol_status": protocol_status_counts,
            "by_execution_outcome": outcome_counts,
        }


_global_skill_engine: Optional[SkillEvolutionEngine] = None


def get_skill_evolution_engine() -> SkillEvolutionEngine:
    global _global_skill_engine
    if _global_skill_engine is None:
        _global_skill_engine = SkillEvolutionEngine()
    return _global_skill_engine
