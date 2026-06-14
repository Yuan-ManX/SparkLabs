"""
SparkLabs Agent - Intelligence Orchestrator

The central AI orchestration module for the SparkLabs AI-native game engine.
Coordinates all AI agents, manages cognitive pipelines, and provides a unified
intelligence layer that bridges game design intent with runtime execution.

Architecture:
  IntelligenceOrchestrator (singleton)
    |-- PipelineStage (cognitive pipeline phase enumeration)
    |-- InsightType (knowledge node categorization)
    |-- PipelineStatus (lifecycle state of a pipeline)
    |-- CognitiveDomain (domain classification for insights)
    |-- CognitiveContext (shared context flowing through the pipeline)
    |-- InsightNode (AI-generated knowledge about game design)
    |-- StageResult (outcome of a single pipeline stage execution)
    |-- IntelligencePipeline (multi-stage cognitive processing chain)

Core Capabilities:
  - create_pipeline: Instantiate a new cognitive processing pipeline
  - execute_stage: Process one stage of the cognitive pipeline
  - inject_insight: Add an AI-generated insight to a pipeline
  - query_insights: Search the global insight graph with filters
  - get_pipeline_status: Real-time status snapshot of a pipeline
  - get_stats: Aggregate statistics across all pipelines
  - synthesize_knowledge: Cross-pipeline knowledge synthesis by domain

Pipeline Flow:
  ANALYZE -> DESIGN -> IMPLEMENT -> TEST -> DEPLOY -> ITERATE
  Each stage consumes the CognitiveContext, transforms it, and generates
  insights that accumulate into a growing knowledge graph.

Usage:
    orchestrator = get_intelligence_orchestrator()
    pid = orchestrator.create_pipeline('combat_design', [
        PipelineStage.ANALYZE, PipelineStage.DESIGN,
        PipelineStage.IMPLEMENT, PipelineStage.TEST,
    ])
    result = orchestrator.execute_stage(pid, PipelineStage.ANALYZE,
        {'game_type': 'rpg', 'target_audience': 'casual'})
    insight = orchestrator.inject_insight(pid, 'design_pattern',
        'Players respond well to risk-reward combat loops', 0.85)
    knowledge = orchestrator.synthesize_knowledge('combat')
    stats = orchestrator.get_stats()
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PipelineStage(Enum):
    """Stages of the cognitive pipeline that process game creation tasks."""

    ANALYZE = "analyze"
    DESIGN = "design"
    IMPLEMENT = "implement"
    TEST = "test"
    DEPLOY = "deploy"
    ITERATE = "iterate"


class InsightType(Enum):
    """Categories of AI-generated knowledge nodes."""

    DESIGN_PATTERN = "design_pattern"
    MECHANICS_RULE = "mechanics_rule"
    BALANCE_FINDING = "balance_finding"
    PLAYER_BEHAVIOR = "player_behavior"
    NARRATIVE_STRUCTURE = "narrative_structure"
    AESTHETIC_GUIDELINE = "aesthetic_guideline"
    TECHNICAL_CONSTRAINT = "technical_constraint"
    RISK_ASSESSMENT = "risk_assessment"
    OPPORTUNITY_SIGNAL = "opportunity_signal"
    SYSTEM_DYNAMICS = "system_dynamics"


class PipelineStatus(Enum):
    """Lifecycle states of an intelligence pipeline."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ITERATING = "iterating"


class CognitiveDomain(Enum):
    """Domains of game knowledge that insights can address."""

    GAME_DESIGN = "game_design"
    COMBAT = "combat"
    ECONOMY = "economy"
    PROGRESSION = "progression"
    NARRATIVE = "narrative"
    AESTHETICS = "aesthetics"
    TECHNOLOGY = "technology"
    PLAYER_PSYCHOLOGY = "player_psychology"
    LEVEL_ARCHITECTURE = "level_architecture"
    AUDIO = "audio"
    UI_UX = "ui_ux"
    SOCIAL = "social"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CognitiveContext:
    """Shared context that flows through the cognitive pipeline.

    Accumulates insights and knowledge at each stage, forming a growing
    representation of the game design problem being solved. As stages
    execute, the context is enriched with analysis results, design
    candidates, implementation specifications, and validation feedback.

    Attributes:
        context_id: Unique identifier for this context instance.
        pipeline_id: The pipeline this context belongs to.
        current_stage: Active pipeline stage.
        accumulated_knowledge: Stage-keyed dictionary of extracted knowledge.
        insight_chain: Ordered list of insight IDs accumulated so far.
        confidence_map: Per-concept confidence scores [0.0, 1.0].
        design_candidates: Alternative design approaches under consideration.
        constraints: Design and technical constraints discovered.
        metrics: Performance and quality metrics collected during stages.
        metadata: Arbitrary extensible metadata.
        created_at: Unix timestamp of context creation.
        updated_at: Unix timestamp of last modification.
    """

    context_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    pipeline_id: str = ""
    current_stage: str = PipelineStage.ANALYZE.value
    accumulated_knowledge: Dict[str, Any] = field(default_factory=dict)
    insight_chain: List[str] = field(default_factory=list)
    confidence_map: Dict[str, float] = field(default_factory=dict)
    design_candidates: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "pipeline_id": self.pipeline_id,
            "current_stage": self.current_stage,
            "accumulated_knowledge": dict(self.accumulated_knowledge),
            "insight_chain": list(self.insight_chain),
            "confidence_map": dict(self.confidence_map),
            "design_candidates": list(self.design_candidates),
            "constraints": list(self.constraints),
            "metrics": dict(self.metrics),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def merge_knowledge(self, key: str, value: Any) -> None:
        """Merge a piece of knowledge into the accumulated store."""
        self.accumulated_knowledge[key] = value
        self.updated_at = _time_module.time()

    def add_confidence(self, concept: str, score: float) -> None:
        """Record confidence score for a concept, bounded to [0, 1]."""
        self.confidence_map[concept] = max(0.0, min(1.0, score))
        self.updated_at = _time_module.time()

    def add_constraint(self, constraint_type: str, description: str,
                       severity: str = "medium") -> None:
        """Register a design or technical constraint."""
        self.constraints.append({
            "type": constraint_type,
            "description": description,
            "severity": severity,
            "stage": self.current_stage,
            "timestamp": _time_module.time(),
        })
        self.updated_at = _time_module.time()


@dataclass
class InsightNode:
    """A knowledge node representing an AI-generated insight about game design.

    Insights form a graph where each node connects to parent insights
    through parent_insight_ids, enabling traceability of the reasoning
    chain. Insights are cross-referenced by type, domain, and confidence
    for efficient querying.

    Attributes:
        insight_id: Unique identifier for this insight.
        insight_type: Category of the insight.
        domain: Game knowledge domain this insight addresses.
        content: Human-readable description of the insight.
        confidence: Confidence score [0.0, 1.0].
        source_stage: Pipeline stage that generated this insight.
        pipeline_id: The pipeline that produced this insight.
        parent_insight_ids: IDs of parent insights in the reasoning chain.
        metadata: Arbitrary extensible metadata.
        created_at: Unix timestamp of insight creation.
    """

    insight_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    insight_type: str = InsightType.DESIGN_PATTERN.value
    domain: str = CognitiveDomain.GAME_DESIGN.value
    content: str = ""
    confidence: float = 0.5
    source_stage: str = PipelineStage.ANALYZE.value
    pipeline_id: str = ""
    parent_insight_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "insight_type": self.insight_type,
            "domain": self.domain,
            "content": self.content,
            "confidence": self.confidence,
            "source_stage": self.source_stage,
            "pipeline_id": self.pipeline_id,
            "parent_insight_ids": list(self.parent_insight_ids),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    def quality_score(self) -> float:
        """Compute a composite quality score for this insight.

        Combines confidence with a relevance factor derived from insight
        type specificity and domain coverage to produce a holistic
        quality metric useful for ranking and filtering.
        """
        type_weights = {
            InsightType.DESIGN_PATTERN.value: 0.9,
            InsightType.MECHANICS_RULE.value: 1.0,
            InsightType.BALANCE_FINDING.value: 0.95,
            InsightType.PLAYER_BEHAVIOR.value: 0.85,
            InsightType.NARRATIVE_STRUCTURE.value: 0.8,
            InsightType.AESTHETIC_GUIDELINE.value: 0.75,
            InsightType.TECHNICAL_CONSTRAINT.value: 0.7,
            InsightType.RISK_ASSESSMENT.value: 0.9,
            InsightType.OPPORTUNITY_SIGNAL.value: 0.8,
            InsightType.SYSTEM_DYNAMICS.value: 0.95,
        }
        type_weight = type_weights.get(self.insight_type, 0.5)
        content_richness = min(1.0, len(self.content) / 500.0)
        parent_factor = min(1.0, len(self.parent_insight_ids) * 0.1 + 0.7)
        return self.confidence * type_weight * (0.5 + 0.5 * content_richness) * parent_factor


@dataclass
class StageResult:
    """The outcome of executing a single stage of a cognitive pipeline.

    Captures what the stage produced, which insights it generated, how
    long it took, and whether it succeeded or failed. Stage results form
    an audit trail for the entire pipeline execution.

    Attributes:
        result_id: Unique identifier for this result.
        pipeline_id: The pipeline this result belongs to.
        stage: The pipeline stage that was executed.
        success: Whether the stage completed successfully.
        output_data: Structured output from the stage execution.
        insights_generated: IDs of insights created during this stage.
        duration_ms: Wall-clock duration of stage execution in milliseconds.
        error_message: Error details if the stage failed.
        metadata: Arbitrary extensible metadata.
        timestamp: Unix timestamp of stage completion.
    """

    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    pipeline_id: str = ""
    stage: str = PipelineStage.ANALYZE.value
    success: bool = True
    output_data: Dict[str, Any] = field(default_factory=dict)
    insights_generated: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "pipeline_id": self.pipeline_id,
            "stage": self.stage,
            "success": self.success,
            "output_data": dict(self.output_data),
            "insights_generated": list(self.insights_generated),
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class IntelligencePipeline:
    """A multi-stage cognitive pipeline for processing game creation tasks.

    Represents a complete cognitive workflow that moves through stages
    from ANALYZE through ITERATE. Each stage transforms the shared
    CognitiveContext and generates InsightNodes that accumulate into a
    growing knowledge representation of the game being created.

    Attributes:
        pipeline_id: Unique identifier for this pipeline.
        name: Human-readable pipeline name.
        stages: Ordered list of stages this pipeline will execute.
        current_stage_index: Index into stages for the current position.
        status: Current lifecycle status of the pipeline.
        context: The shared cognitive context flowing through the pipeline.
        execution_history: Ordered list of stage execution results.
        insight_nodes: All insights generated during this pipeline.
        total_stages_completed: Count of successfully completed stages.
        created_at: Unix timestamp of pipeline creation.
        completed_at: Unix timestamp when pipeline reached COMPLETED/FAILED.
    """

    pipeline_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    stages: List[str] = field(default_factory=list)
    current_stage_index: int = 0
    status: str = PipelineStatus.IDLE.value
    context: Optional[CognitiveContext] = None
    execution_history: List[StageResult] = field(default_factory=list)
    insight_nodes: List[InsightNode] = field(default_factory=list)
    total_stages_completed: int = 0
    created_at: float = field(default_factory=_time_module.time)
    completed_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "stages": list(self.stages),
            "current_stage_index": self.current_stage_index,
            "status": self.status,
            "context": self.context.to_dict() if self.context else None,
            "execution_history_length": len(self.execution_history),
            "insight_node_count": len(self.insight_nodes),
            "total_stages_completed": self.total_stages_completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    def get_current_stage(self) -> Optional[str]:
        """Return the current stage, or None if the pipeline is finished."""
        if self.current_stage_index < len(self.stages):
            return self.stages[self.current_stage_index]
        return None

    def advance_stage(self) -> Optional[str]:
        """Move to the next stage and return it, or None if complete."""
        self.current_stage_index += 1
        if self.current_stage_index < len(self.stages):
            if self.context:
                self.context.current_stage = self.stages[self.current_stage_index]
                self.context.updated_at = _time_module.time()
            return self.stages[self.current_stage_index]
        self.status = PipelineStatus.COMPLETED.value
        self.completed_at = _time_module.time()
        return None


# ---------------------------------------------------------------------------
# IntelligenceOrchestrator Singleton
# ---------------------------------------------------------------------------


class IntelligenceOrchestrator:
    """Central AI orchestration system for the SparkLabs game engine.

    Coordinates all AI agents through cognitive pipelines, manages the
    shared insight graph, and provides a unified intelligence layer that
    bridges game design intent with runtime execution.

    The orchestrator maintains a registry of pipelines, each containing
    a CognitiveContext that flows through stages (ANALYZE -> DESIGN ->
    IMPLEMENT -> TEST -> DEPLOY -> ITERATE), accumulating InsightNodes
    at each stage. A cross-pipeline knowledge synthesis capability
    enables global reasoning across all active and completed pipelines.
    """

    _instance: Optional[IntelligenceOrchestrator] = None
    _lock = threading.RLock()

    def __new__(cls) -> IntelligenceOrchestrator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> IntelligenceOrchestrator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.__init__()
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if hasattr(self, "_initialized") and self._initialized:
                return
            self._pipelines: Dict[str, IntelligencePipeline] = {}
            self._global_insight_index: Dict[str, InsightNode] = {}
            self._domain_insight_index: Dict[str, List[str]] = defaultdict(list)
            self._stage_templates: Dict[str, Dict[str, Any]] = {}
            self._stats: Dict[str, Any] = {
                "total_pipelines_created": 0,
                "total_stages_executed": 0,
                "total_insights_generated": 0,
                "total_stages_failed": 0,
                "total_synthesis_operations": 0,
                "pipelines_by_status": defaultdict(int),
                "insights_by_type": defaultdict(int),
                "insights_by_domain": defaultdict(int),
                "stage_duration_history_ms": [],
            }
            self._initialize_stage_templates()
            self._initialized = True

    def _initialize_stage_templates(self) -> None:
        """Initialize the processing logic templates for each stage."""
        self._stage_templates = {
            PipelineStage.ANALYZE.value: {
                "description": "Decompose input, extract entities, identify patterns",
                "output_keys": ["entities", "relationships", "constraints", "complexity_score"],
                "produces_insights": [InsightType.SYSTEM_DYNAMICS, InsightType.TECHNICAL_CONSTRAINT],
                "avg_duration_ms": 150.0,
            },
            PipelineStage.DESIGN.value: {
                "description": "Generate design alternatives and evaluate trade-offs",
                "output_keys": ["design_alternatives", "rationale", "trade_off_matrix", "selected_design"],
                "produces_insights": [InsightType.DESIGN_PATTERN, InsightType.AESTHETIC_GUIDELINE],
                "avg_duration_ms": 200.0,
            },
            PipelineStage.IMPLEMENT.value: {
                "description": "Convert design into concrete specifications and code structures",
                "output_keys": ["specification", "component_tree", "data_model", "interface_definitions"],
                "produces_insights": [InsightType.MECHANICS_RULE, InsightType.TECHNICAL_CONSTRAINT],
                "avg_duration_ms": 250.0,
            },
            PipelineStage.TEST.value: {
                "description": "Validate implementation against requirements and constraints",
                "output_keys": ["test_results", "coverage_report", "issues_found", "quality_score"],
                "produces_insights": [InsightType.RISK_ASSESSMENT, InsightType.BALANCE_FINDING],
                "avg_duration_ms": 180.0,
            },
            PipelineStage.DEPLOY.value: {
                "description": "Package output for runtime integration",
                "output_keys": ["deployment_package", "runtime_config", "integration_points", "rollback_plan"],
                "produces_insights": [InsightType.OPPORTUNITY_SIGNAL],
                "avg_duration_ms": 120.0,
            },
            PipelineStage.ITERATE.value: {
                "description": "Review results from all stages and prepare next cycle",
                "output_keys": ["iteration_plan", "lessons_learned", "improvement_targets", "next_cycle_goals"],
                "produces_insights": [InsightType.PLAYER_BEHAVIOR, InsightType.OPPORTUNITY_SIGNAL],
                "avg_duration_ms": 160.0,
            },
        }

    # -----------------------------------------------------------------------
    # Pipeline Management
    # -----------------------------------------------------------------------

    def create_pipeline(
        self,
        name: str,
        stages: List[PipelineStage],
    ) -> Optional[str]:
        """Create a new cognitive pipeline for processing game creation tasks.

        Initializes a pipeline with the given stages, a fresh CognitiveContext,
        and registers it for orchestration. Returns the pipeline_id for use
        in subsequent operations.

        Args:
            name: Human-readable name for the pipeline.
            stages: Ordered list of PipelineStage values to execute.

        Returns:
            The pipeline_id string, or None if stages is empty.
        """
        with self._lock:
            if not stages:
                return None

            stage_values = [s.value for s in stages]
            pipeline = IntelligencePipeline(
                name=name,
                stages=stage_values,
            )

            context = CognitiveContext(
                pipeline_id=pipeline.pipeline_id,
                current_stage=stage_values[0],
            )
            pipeline.context = context

            self._pipelines[pipeline.pipeline_id] = pipeline
            self._stats["total_pipelines_created"] += 1
            self._stats["pipelines_by_status"][pipeline.status] += 1

            return pipeline.pipeline_id

    def get_pipeline(self, pipeline_id: str) -> Optional[IntelligencePipeline]:
        """Retrieve a pipeline by its ID."""
        return self._pipelines.get(pipeline_id)

    def list_pipelines(
        self,
        status: Optional[PipelineStatus] = None,
    ) -> List[IntelligencePipeline]:
        """List all pipelines, optionally filtered by status."""
        results = list(self._pipelines.values())
        if status is not None:
            results = [p for p in results if p.status == status.value]
        return results

    def delete_pipeline(self, pipeline_id: str) -> bool:
        """Delete a pipeline and its associated insights from global index."""
        with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if pipeline is None:
                return False

            for insight in pipeline.insight_nodes:
                self._global_insight_index.pop(insight.insight_id, None)
                domain_list = self._domain_insight_index.get(insight.domain, [])
                if insight.insight_id in domain_list:
                    domain_list.remove(insight.insight_id)

            old_status = pipeline.status
            self._stats["pipelines_by_status"][old_status] = max(
                0, self._stats["pipelines_by_status"].get(old_status, 1) - 1
            )

            del self._pipelines[pipeline_id]
            return True

    # -----------------------------------------------------------------------
    # Stage Execution
    # -----------------------------------------------------------------------

    def execute_stage(
        self,
        pipeline_id: str,
        stage: PipelineStage,
        context_data: Dict[str, Any],
    ) -> Optional[StageResult]:
        """Execute a single stage of the cognitive pipeline.

        Processes the given context_data through the specified stage's
        intelligence logic, updates the shared CognitiveContext, generates
        relevant insights, and records the stage result in the pipeline's
        execution history.

        Each stage performs domain-specific processing:
        - ANALYZE: Entity extraction, constraint identification, complexity assessment
        - DESIGN: Alternative generation, trade-off evaluation, pattern matching
        - IMPLEMENT: Specification generation, component decomposition
        - TEST: Constraint validation, quality scoring, issue detection
        - DEPLOY: Integration point mapping, runtime configuration
        - ITERATE: Result synthesis, improvement planning, cycle preparation

        Args:
            pipeline_id: The pipeline to execute within.
            stage: The stage to execute.
            context_data: Input data for this stage's processing.

        Returns:
            StageResult with output data and generated insights, or None on error.
        """
        with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if pipeline is None:
                return None

            if pipeline.status in (PipelineStatus.COMPLETED.value,
                                    PipelineStatus.FAILED.value):
                return None

            stage_value = stage.value
            template = self._stage_templates.get(stage_value, {})
            stage_start = _time_module.time()

            try:
                old_status = pipeline.status
                pipeline.status = PipelineStatus.RUNNING.value
                if old_status != PipelineStatus.RUNNING.value:
                    self._stats["pipelines_by_status"][old_status] = max(
                        0, self._stats["pipelines_by_status"].get(old_status, 1) - 1
                    )
                    self._stats["pipelines_by_status"][PipelineStatus.RUNNING.value] += 1

                # --- Stage-specific processing ---
                output_data: Dict[str, Any] = {}
                generated_insight_ids: List[str] = []

                if stage == PipelineStage.ANALYZE:
                    output_data = self._process_analyze_stage(
                        pipeline, context_data, generated_insight_ids
                    )
                elif stage == PipelineStage.DESIGN:
                    output_data = self._process_design_stage(
                        pipeline, context_data, generated_insight_ids
                    )
                elif stage == PipelineStage.IMPLEMENT:
                    output_data = self._process_implement_stage(
                        pipeline, context_data, generated_insight_ids
                    )
                elif stage == PipelineStage.TEST:
                    output_data = self._process_test_stage(
                        pipeline, context_data, generated_insight_ids
                    )
                elif stage == PipelineStage.DEPLOY:
                    output_data = self._process_deploy_stage(
                        pipeline, context_data, generated_insight_ids
                    )
                elif stage == PipelineStage.ITERATE:
                    output_data = self._process_iterate_stage(
                        pipeline, context_data, generated_insight_ids
                    )

                # Update context with stage output
                if pipeline.context:
                    pipeline.context.merge_knowledge(stage_value, output_data)
                    pipeline.context.current_stage = stage_value

                # Update pipeline position
                for i, s in enumerate(pipeline.stages):
                    if s == stage_value:
                        pipeline.current_stage_index = i
                        break

                pipeline.total_stages_completed += 1

                duration_ms = (_time_module.time() - stage_start) * 1000.0

                result = StageResult(
                    pipeline_id=pipeline_id,
                    stage=stage_value,
                    success=True,
                    output_data=output_data,
                    insights_generated=list(generated_insight_ids),
                    duration_ms=round(duration_ms, 2),
                )
                pipeline.execution_history.append(result)

                self._stats["total_stages_executed"] += 1
                self._stats["stage_duration_history_ms"].append(duration_ms)

                return result

            except Exception as exc:
                duration_ms = (_time_module.time() - stage_start) * 1000.0
                result = StageResult(
                    pipeline_id=pipeline_id,
                    stage=stage_value,
                    success=False,
                    output_data={},
                    insights_generated=[],
                    duration_ms=round(duration_ms, 2),
                    error_message=str(exc),
                )
                pipeline.execution_history.append(result)
                self._stats["total_stages_failed"] += 1
                return result

    # --- Stage Processing Implementations ---

    def _process_analyze_stage(
        self,
        pipeline: IntelligencePipeline,
        context_data: Dict[str, Any],
        generated_insight_ids: List[str],
    ) -> Dict[str, Any]:
        """ANALYZE stage: Decompose input, extract entities, identify patterns."""
        entities: Dict[str, Any] = {}
        relationships: List[Dict[str, str]] = []
        constraints_found: List[Dict[str, Any]] = []

        game_type = context_data.get("game_type", "unknown")
        target_audience = context_data.get("target_audience", "general")
        scope = context_data.get("scope", "full_game")

        entities["game"] = {"type": game_type, "scope": scope}
        entities["audience"] = {"profile": target_audience}
        entities["pipeline_name"] = pipeline.name

        if "mechanics" in context_data:
            entities["mechanics"] = context_data["mechanics"]
            for mech in context_data["mechanics"] if isinstance(context_data["mechanics"], list) else [context_data["mechanics"]]:
                relationships.append({"from": "game", "to": str(mech), "type": "requires"})

        if "constraints" in context_data:
            constraints_found = context_data["constraints"] if isinstance(context_data["constraints"], list) else [{"description": str(context_data["constraints"])}]

        complexity_score = self._estimate_complexity(entities)
        output = {
            "entities": entities,
            "relationships": relationships,
            "constraints": constraints_found,
            "complexity_score": complexity_score,
            "analysis_summary": f"Analyzed {game_type} game for {target_audience} audience.",
        }

        # Generate system dynamics insight
        insight = self.inject_insight(
            pipeline.pipeline_id,
            InsightType.SYSTEM_DYNAMICS.value,
            f"Game system of type '{game_type}' has estimated complexity {complexity_score:.2f}. "
            f"Target audience '{target_audience}' suggests accessibility requirements.",
            0.7 + 0.2 * (1.0 - complexity_score),
            stage=PipelineStage.ANALYZE,
            domain=CognitiveDomain.GAME_DESIGN.value,
        )
        if insight:
            generated_insight_ids.append(insight.insight_id)

        # Update context
        if pipeline.context:
            pipeline.context.merge_knowledge("entities", entities)
            pipeline.context.add_confidence("analysis_completeness", 0.75)
            for c in constraints_found:
                pipeline.context.add_constraint(
                    c.get("type", "general"),
                    c.get("description", str(c)),
                    c.get("severity", "medium"),
                )

        return output

    def _process_design_stage(
        self,
        pipeline: IntelligencePipeline,
        context_data: Dict[str, Any],
        generated_insight_ids: List[str],
    ) -> Dict[str, Any]:
        """DESIGN stage: Generate design alternatives and evaluate trade-offs."""
        design_alternatives: List[Dict[str, Any]] = []
        existing_knowledge = pipeline.context.accumulated_knowledge if pipeline.context else {}
        entities = existing_knowledge.get("entities", {})

        design_count = context_data.get("design_count", 3)
        design_style = context_data.get("design_style", "balanced")

        for i in range(design_count):
            approach = ["conservative", "balanced", "innovative"][i % 3]
            if design_style != "balanced":
                approach = design_style
            alt = {
                "index": i,
                "approach": approach,
                "description": f"Design alternative {i + 1} using {approach} approach",
                "innovation_score": {"conservative": 0.2, "balanced": 0.5, "innovative": 0.9}.get(approach, 0.5),
                "risk_level": {"conservative": "low", "balanced": "medium", "innovative": "high"}.get(approach, "medium"),
            }
            design_alternatives.append(alt)

        trade_offs = {
            "conservative": {"safety": 0.9, "novelty": 0.2, "engagement": 0.5},
            "balanced": {"safety": 0.6, "novelty": 0.5, "engagement": 0.7},
            "innovative": {"safety": 0.3, "novelty": 0.9, "engagement": 0.8},
        }

        selected_design = design_alternatives[0] if design_alternatives else {}

        output = {
            "design_alternatives": design_alternatives,
            "rationale": f"Generated {len(design_alternatives)} design alternatives with {design_style} preference.",
            "trade_off_matrix": trade_offs,
            "selected_design": selected_design,
        }

        # Generate design pattern insight
        insight = self.inject_insight(
            pipeline.pipeline_id,
            InsightType.DESIGN_PATTERN.value,
            f"Design exploration for '{pipeline.name}' generated {len(design_alternatives)} "
            f"alternatives. Recommended: {selected_design.get('approach', 'balanced')} approach.",
            0.65,
            stage=PipelineStage.DESIGN,
            domain=CognitiveDomain.GAME_DESIGN.value,
        )
        if insight:
            generated_insight_ids.append(insight.insight_id)

        if pipeline.context:
            pipeline.context.merge_knowledge("design_alternatives", design_alternatives)

        return output

    def _process_implement_stage(
        self,
        pipeline: IntelligencePipeline,
        context_data: Dict[str, Any],
        generated_insight_ids: List[str],
    ) -> Dict[str, Any]:
        """IMPLEMENT stage: Convert design into concrete specifications."""
        component_tree: Dict[str, Any] = {
            "root": pipeline.name,
            "components": context_data.get("components", ["core_logic", "ui", "data"]),
        }
        data_model = context_data.get("data_model", {"entities": [], "relationships": []})
        interfaces = context_data.get("interfaces", ["IInitializable", "IUpdatable"])

        # Generate mechanics rule insight
        insight = self.inject_insight(
            pipeline.pipeline_id,
            InsightType.MECHANICS_RULE.value,
            f"Implementation for '{pipeline.name}' decomposes into "
            f"{len(component_tree.get('components', []))} components with "
            f"{len(interfaces)} interfaces defined.",
            0.75,
            stage=PipelineStage.IMPLEMENT,
            domain=CognitiveDomain.TECHNOLOGY.value,
        )
        if insight:
            generated_insight_ids.append(insight.insight_id)

        output = {
            "specification": f"Implementation spec for {pipeline.name}",
            "component_tree": component_tree,
            "data_model": data_model,
            "interface_definitions": interfaces,
        }

        if pipeline.context:
            pipeline.context.merge_knowledge("specification", output)

        return output

    def _process_test_stage(
        self,
        pipeline: IntelligencePipeline,
        context_data: Dict[str, Any],
        generated_insight_ids: List[str],
    ) -> Dict[str, Any]:
        """TEST stage: Validate implementation against requirements."""
        test_count = context_data.get("test_count", 10)
        pass_rate = random.uniform(0.7, 0.98)
        passed = int(test_count * pass_rate)
        failed = test_count - passed

        quality_score = pass_rate * 0.8 + random.uniform(0.0, 0.2)
        quality_score = min(1.0, quality_score)

        issues: List[Dict[str, Any]] = []
        if failed > 0:
            for _ in range(failed):
                issues.append({
                    "severity": random.choice(["low", "medium", "high"]),
                    "description": "Simulated test failure for verification purposes.",
                })

        output = {
            "test_results": {"passed": passed, "failed": failed, "total": test_count},
            "coverage_report": {"line_coverage": round(pass_rate * 0.9, 2)},
            "issues_found": issues,
            "quality_score": round(quality_score, 3),
        }

        # Generate risk assessment insight if issues found
        if issues:
            insight = self.inject_insight(
                pipeline.pipeline_id,
                InsightType.RISK_ASSESSMENT.value,
                f"Testing revealed {len(issues)} issues in '{pipeline.name}'. "
                f"Quality score: {quality_score:.2f}.",
                max(0.3, 1.0 - pass_rate),
                stage=PipelineStage.TEST,
                domain=CognitiveDomain.TECHNOLOGY.value,
            )
            if insight:
                generated_insight_ids.append(insight.insight_id)

        if pipeline.context:
            pipeline.context.merge_knowledge("test_results", output)
            pipeline.context.metrics["quality_score"] = quality_score

        return output

    def _process_deploy_stage(
        self,
        pipeline: IntelligencePipeline,
        context_data: Dict[str, Any],
        generated_insight_ids: List[str],
    ) -> Dict[str, Any]:
        """DEPLOY stage: Package output for runtime integration."""
        runtime_config = context_data.get("runtime_config", {
            "environment": "development",
            "optimization_level": "standard",
        })

        integration_points = context_data.get("integration_points", [])

        output = {
            "deployment_package": f"{pipeline.name}_v1.0",
            "runtime_config": runtime_config,
            "integration_points": integration_points,
            "rollback_plan": "Standard rollback to previous stable configuration.",
        }

        # Generate opportunity insight
        insight = self.inject_insight(
            pipeline.pipeline_id,
            InsightType.OPPORTUNITY_SIGNAL.value,
            f"Deployment of '{pipeline.name}' with {len(integration_points)} "
            f"integration points. Environment: {runtime_config.get('environment', 'unknown')}.",
            0.8,
            stage=PipelineStage.DEPLOY,
            domain=CognitiveDomain.TECHNOLOGY.value,
        )
        if insight:
            generated_insight_ids.append(insight.insight_id)

        return output

    def _process_iterate_stage(
        self,
        pipeline: IntelligencePipeline,
        context_data: Dict[str, Any],
        generated_insight_ids: List[str],
    ) -> Dict[str, Any]:
        """ITERATE stage: Review results and prepare for next cycle."""
        history_count = len(pipeline.execution_history)
        lessons: List[str] = []

        for result in pipeline.execution_history:
            if not result.success:
                lessons.append(f"Stage {result.stage} failed: {result.error_message}")
            if result.insights_generated:
                lessons.append(f"Stage {result.stage} produced {len(result.insights_generated)} insights")

        quality = pipeline.context.metrics.get("quality_score", 0.5) if pipeline.context else 0.5
        improvement_targets = []

        if quality < 0.7:
            improvement_targets.append("quality_improvement")
        if history_count < 3:
            improvement_targets.append("deeper_exploration")
        if len(pipeline.insight_nodes) < 3:
            improvement_targets.append("more_insight_generation")

        output = {
            "iteration_plan": f"Next iteration focusing on: {', '.join(improvement_targets) or 'refinement'}",
            "lessons_learned": lessons,
            "improvement_targets": improvement_targets,
            "next_cycle_goals": ["increase_quality", "expand_coverage", "deepen_insights"],
        }

        # Generate player behavior insight
        insight = self.inject_insight(
            pipeline.pipeline_id,
            InsightType.PLAYER_BEHAVIOR.value,
            f"Iteration review for '{pipeline.name}': {len(lessons)} lessons, "
            f"quality {quality:.2f}. Targets: {improvement_targets}.",
            0.7,
            stage=PipelineStage.ITERATE,
            domain=CognitiveDomain.PLAYER_PSYCHOLOGY.value,
        )
        if insight:
            generated_insight_ids.append(insight.insight_id)

        pipeline.status = PipelineStatus.ITERATING.value
        return output

    def _estimate_complexity(self, entities: Dict[str, Any]) -> float:
        """Estimate the complexity of a game design from its entities."""
        base = 0.3
        entity_count = len(entities)
        base += min(0.5, entity_count * 0.1)

        game_type = entities.get("game", {}).get("type", "")
        type_complexity = {
            "rpg": 0.7,
            "strategy": 0.8,
            "simulation": 0.75,
            "action": 0.4,
            "puzzle": 0.3,
            "platformer": 0.35,
            "sandbox": 0.65,
        }
        base = type_complexity.get(str(game_type).lower(), base)

        return max(0.1, min(1.0, base + random.uniform(-0.05, 0.05)))

    # -----------------------------------------------------------------------
    # Insight Management
    # -----------------------------------------------------------------------

    def inject_insight(
        self,
        pipeline_id: str,
        insight_type: str,
        content: str,
        confidence: float,
        stage: Optional[PipelineStage] = None,
        domain: Optional[str] = None,
        parent_insight_ids: Optional[List[str]] = None,
    ) -> Optional[InsightNode]:
        """Inject an AI-generated insight into a pipeline's knowledge graph.

        Creates an InsightNode, attaches it to the pipeline, and indexes it
        globally by ID and domain for cross-pipeline querying.

        Args:
            pipeline_id: Target pipeline.
            insight_type: Category from InsightType enum values.
            content: Human-readable description of the insight.
            confidence: Confidence score [0.0, 1.0].
            stage: Pipeline stage that generated this insight.
            domain: CognitiveDomain value for domain classification.
            parent_insight_ids: IDs of parent insights for traceability.

        Returns:
            The created InsightNode, or None if pipeline not found.
        """
        with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if pipeline is None:
                return None

            source_stage = stage.value if stage else (
                pipeline.context.current_stage if pipeline.context else PipelineStage.ANALYZE.value
            )
            resolved_domain = domain or CognitiveDomain.GAME_DESIGN.value

            insight = InsightNode(
                insight_type=insight_type,
                domain=resolved_domain,
                content=content,
                confidence=max(0.0, min(1.0, confidence)),
                source_stage=source_stage,
                pipeline_id=pipeline_id,
                parent_insight_ids=parent_insight_ids or [],
            )

            pipeline.insight_nodes.append(insight)
            if pipeline.context:
                pipeline.context.insight_chain.append(insight.insight_id)

            self._global_insight_index[insight.insight_id] = insight
            self._domain_insight_index[resolved_domain].append(insight.insight_id)

            self._stats["total_insights_generated"] += 1
            self._stats["insights_by_type"][insight_type] += 1
            self._stats["insights_by_domain"][resolved_domain] += 1

            return insight

    def query_insights(
        self,
        insight_type: Optional[str] = None,
        domain: Optional[str] = None,
        min_confidence: Optional[float] = None,
        pipeline_id: Optional[str] = None,
        stage: Optional[PipelineStage] = None,
        sort_by: str = "confidence",
        limit: int = 100,
    ) -> List[InsightNode]:
        """Query the global insight graph with flexible filters.

        Searches across all pipelines' insights with filtering by type,
        domain, confidence threshold, source pipeline, and originating stage.
        Results are sorted and limited as specified.

        Args:
            insight_type: Filter by InsightType value.
            domain: Filter by CognitiveDomain value.
            min_confidence: Minimum confidence threshold [0.0, 1.0].
            pipeline_id: Filter by source pipeline.
            stage: Filter by originating PipelineStage.
            sort_by: Sort key: 'confidence', 'created_at', or 'quality'.
            limit: Maximum number of results to return.

        Returns:
            List of matching InsightNode instances.
        """
        with self._lock:
            # Determine candidate pool
            if pipeline_id is not None:
                pipeline = self._pipelines.get(pipeline_id)
                if pipeline is None:
                    return []
                candidates = list(pipeline.insight_nodes)
            elif domain is not None:
                domain_ids = self._domain_insight_index.get(domain, [])
                candidates = [
                    self._global_insight_index[iid]
                    for iid in domain_ids
                    if iid in self._global_insight_index
                ]
            else:
                candidates = list(self._global_insight_index.values())

            # Apply filters
            results: List[InsightNode] = []
            for insight in candidates:
                if insight_type is not None and insight.insight_type != insight_type:
                    continue
                if domain is not None and insight.domain != domain:
                    continue
                if min_confidence is not None and insight.confidence < min_confidence:
                    continue
                if stage is not None and insight.source_stage != stage.value:
                    continue
                results.append(insight)

            # Sort
            if sort_by == "confidence":
                results.sort(key=lambda i: i.confidence, reverse=True)
            elif sort_by == "quality":
                results.sort(key=lambda i: i.quality_score(), reverse=True)
            elif sort_by == "created_at":
                results.sort(key=lambda i: i.created_at, reverse=True)
            else:
                results.sort(key=lambda i: i.confidence, reverse=True)

            return results[:limit]

    def get_insight(self, insight_id: str) -> Optional[InsightNode]:
        """Retrieve a single insight by its ID from the global index."""
        return self._global_insight_index.get(insight_id)

    # -----------------------------------------------------------------------
    # Status and Statistics
    # -----------------------------------------------------------------------

    def get_pipeline_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get a detailed status snapshot for a pipeline.

        Returns current stage, progress percentage, insight counts,
        execution history summary, and quality metrics.

        Args:
            pipeline_id: The pipeline to inspect.

        Returns:
            Status dictionary, or None if pipeline not found.
        """
        with self._lock:
            pipeline = self._pipelines.get(pipeline_id)
            if pipeline is None:
                return None

            total_stages = len(pipeline.stages)
            completed = pipeline.total_stages_completed
            progress_pct = (completed / total_stages * 100.0) if total_stages > 0 else 0.0

            stage_breakdown: Dict[str, Dict[str, Any]] = {}
            for result in pipeline.execution_history:
                stage_breakdown[result.stage] = {
                    "success": result.success,
                    "duration_ms": result.duration_ms,
                    "insights_count": len(result.insights_generated),
                    "error": result.error_message if not result.success else None,
                }

            avg_confidence = 0.0
            if pipeline.insight_nodes:
                avg_confidence = sum(
                    i.confidence for i in pipeline.insight_nodes
                ) / len(pipeline.insight_nodes)

            quality_metrics = pipeline.context.metrics if pipeline.context else {}

            return {
                "pipeline_id": pipeline.pipeline_id,
                "name": pipeline.name,
                "status": pipeline.status,
                "current_stage": pipeline.get_current_stage(),
                "current_stage_index": pipeline.current_stage_index,
                "total_stages": total_stages,
                "stages_completed": completed,
                "progress_pct": round(progress_pct, 1),
                "stage_breakdown": stage_breakdown,
                "total_insights": len(pipeline.insight_nodes),
                "avg_insight_confidence": round(avg_confidence, 3),
                "execution_history_length": len(pipeline.execution_history),
                "quality_metrics": quality_metrics,
                "constraints_count": len(pipeline.context.constraints) if pipeline.context else 0,
                "created_at": pipeline.created_at,
                "completed_at": pipeline.completed_at,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics across all pipelines and insights.

        Includes pipeline counts by status, insight distribution by type
        and domain, stage execution metrics, and overall system health.
        """
        with self._lock:
            active_pipelines = sum(
                1 for p in self._pipelines.values()
                if p.status == PipelineStatus.RUNNING.value
            )
            completed_pipelines = sum(
                1 for p in self._pipelines.values()
                if p.status == PipelineStatus.COMPLETED.value
            )
            failed_pipelines = sum(
                1 for p in self._pipelines.values()
                if p.status == PipelineStatus.FAILED.value
            )

            avg_stage_duration = 0.0
            durations = self._stats["stage_duration_history_ms"]
            if durations:
                avg_stage_duration = sum(durations) / len(durations)

            total_stage_duration_ms = sum(durations)

            avg_global_confidence = 0.0
            if self._global_insight_index:
                avg_global_confidence = sum(
                    i.confidence for i in self._global_insight_index.values()
                ) / len(self._global_insight_index)

            return {
                "total_pipelines": len(self._pipelines),
                "active_pipelines": active_pipelines,
                "completed_pipelines": completed_pipelines,
                "failed_pipelines": failed_pipelines,
                "total_pipelines_created": self._stats["total_pipelines_created"],
                "total_stages_executed": self._stats["total_stages_executed"],
                "total_stages_failed": self._stats["total_stages_failed"],
                "total_insights_generated": self._stats["total_insights_generated"],
                "total_insights_indexed": len(self._global_insight_index),
                "total_synthesis_operations": self._stats["total_synthesis_operations"],
                "pipelines_by_status": dict(self._stats["pipelines_by_status"]),
                "insights_by_type": dict(self._stats["insights_by_type"]),
                "insights_by_domain": dict(self._stats["insights_by_domain"]),
                "avg_stage_duration_ms": round(avg_stage_duration, 2),
                "total_stage_duration_ms": round(total_stage_duration_ms, 2),
                "avg_insight_confidence": round(avg_global_confidence, 3),
                "unique_domains_indexed": len(self._domain_insight_index),
                "stage_failure_rate": round(
                    self._stats["total_stages_failed"] / max(1, self._stats["total_stages_executed"]), 3
                ),
            }

    # -----------------------------------------------------------------------
    # Knowledge Synthesis
    # -----------------------------------------------------------------------

    def synthesize_knowledge(self, domain: str) -> Dict[str, Any]:
        """Synthesize knowledge across all pipelines for a given domain.

        Aggregates insights from all pipelines within the specified domain,
        computes confidence-weighted summaries, identifies knowledge gaps,
        detects consensus patterns, and ranks insights by quality.

        This is the cross-pipeline reasoning capability that enables the
        orchestrator to derive holistic conclusions from distributed
        cognitive processing.

        Args:
            domain: CognitiveDomain value to synthesize knowledge for.

        Returns:
            Dictionary with synthesized knowledge, ranked insights, gaps,
            patterns, and domain coverage assessment.
        """
        with self._lock:
            self._stats["total_synthesis_operations"] += 1

            domain_insights = self.query_insights(domain=domain, sort_by="quality")

            if not domain_insights:
                return {
                    "domain": domain,
                    "insight_count": 0,
                    "summary": f"No insights available for domain '{domain}'.",
                    "ranked_insights": [],
                    "knowledge_gaps": ["no_data"],
                    "consensus_patterns": [],
                    "coverage_assessment": "none",
                    "avg_confidence": 0.0,
                    "recommendations": [f"Create pipelines that generate insights for the '{domain}' domain."],
                }

            # Rank insights by quality score
            ranked = sorted(domain_insights, key=lambda i: i.quality_score(), reverse=True)
            top_insights = ranked[:10]

            # Compute confidence-weighted summary
            total_weight = sum(i.confidence for i in domain_insights)
            if total_weight > 0:
                avg_confidence = sum(i.confidence * i.confidence for i in domain_insights) / total_weight
            else:
                avg_confidence = 0.0

            # Build summary strings from top insights
            summary_parts: List[str] = []
            for insight in top_insights[:5]:
                truncated = insight.content[:120]
                if len(insight.content) > 120:
                    truncated += "..."
                summary_parts.append(f"[{insight.insight_type}] {truncated}")

            # Detect consensus patterns: insights of same type with high confidence
            type_groups: Dict[str, List[InsightNode]] = defaultdict(list)
            for insight in domain_insights:
                type_groups[insight.insight_type].append(insight)

            consensus_patterns: List[Dict[str, Any]] = []
            for itype, group in type_groups.items():
                if len(group) >= 2:
                    avg_conf = sum(i.confidence for i in group) / len(group)
                    if avg_conf >= 0.5:
                        consensus_patterns.append({
                            "insight_type": itype,
                            "occurrence_count": len(group),
                            "avg_confidence": round(avg_conf, 3),
                            "representative_insight": group[0].insight_id,
                        })

            # Identify knowledge gaps: InsightTypes not represented
            all_types = {t.value for t in InsightType}
            represented_types = {i.insight_type for i in domain_insights}
            knowledge_gaps = list(all_types - represented_types)

            # Coverage assessment
            coverage_ratio = len(represented_types) / len(all_types) if all_types else 0.0
            if coverage_ratio >= 0.7:
                coverage = "comprehensive"
            elif coverage_ratio >= 0.4:
                coverage = "moderate"
            elif coverage_ratio >= 0.1:
                coverage = "sparse"
            else:
                coverage = "minimal"

            # Generate recommendations
            recommendations: List[str] = []
            if knowledge_gaps:
                recommendations.append(
                    f"Consider generating insights for missing types: {', '.join(knowledge_gaps[:5])}"
                )
            if avg_confidence < 0.5:
                recommendations.append("Overall confidence is low. Consider re-running stages with more input data.")
            if len(consensus_patterns) < 2:
                recommendations.append("Few consensus patterns detected. More pipeline executions may strengthen findings.")
            if not recommendations:
                recommendations.append("Knowledge synthesis is well-rounded. Continue iterating for deeper insights.")

            return {
                "domain": domain,
                "insight_count": len(domain_insights),
                "summary": " | ".join(summary_parts) if summary_parts else "No summary available.",
                "ranked_insights": [i.to_dict() for i in top_insights],
                "knowledge_gaps": knowledge_gaps,
                "consensus_patterns": consensus_patterns,
                "coverage_assessment": coverage,
                "avg_confidence": round(avg_confidence, 3),
                "recommendations": recommendations,
                "unique_pipelines": len({i.pipeline_id for i in domain_insights}),
                "total_quality_score": round(sum(i.quality_score() for i in domain_insights), 3),
                "synthesized_at": _time_module.time(),
            }

    def compare_pipeline_insights(
        self,
        pipeline_ids: List[str],
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare insight quality across multiple pipelines.

        Provides a side-by-side comparison of insight depth, confidence
        distribution, and domain coverage for the specified pipelines.

        Args:
            pipeline_ids: List of pipeline IDs to compare.
            domain: Optional domain filter.

        Returns:
            Comparison dictionary with per-pipeline metrics and rankings.
        """
        with self._lock:
            entries: List[Dict[str, Any]] = []
            for pid in pipeline_ids:
                pipeline = self._pipelines.get(pid)
                if pipeline is None:
                    entries.append({
                        "pipeline_id": pid,
                        "found": False,
                    })
                    continue

                insights = pipeline.insight_nodes
                if domain:
                    insights = [i for i in insights if i.domain == domain]

                if insights:
                    avg_conf = sum(i.confidence for i in insights) / len(insights)
                    avg_quality = sum(i.quality_score() for i in insights) / len(insights)
                else:
                    avg_conf = 0.0
                    avg_quality = 0.0

                type_distribution: Dict[str, int] = defaultdict(int)
                for i in insights:
                    type_distribution[i.insight_type] += 1

                entries.append({
                    "pipeline_id": pid,
                    "found": True,
                    "name": pipeline.name,
                    "status": pipeline.status,
                    "insight_count": len(insights),
                    "avg_confidence": round(avg_conf, 3),
                    "avg_quality": round(avg_quality, 3),
                    "type_distribution": dict(type_distribution),
                    "stages_completed": pipeline.total_stages_completed,
                })

            entries.sort(key=lambda e: e.get("avg_quality", 0.0), reverse=True)
            best_pipeline = entries[0]["pipeline_id"] if entries else None

            return {
                "pipeline_count": len(entries),
                "pipelines": entries,
                "best_pipeline": best_pipeline,
                "summary": (
                    f"Compared {len(entries)} pipelines. "
                    f"Best: {best_pipeline} with "
                    f"{entries[0].get('insight_count', 0)} insights."
                ) if entries else "No pipelines found for comparison.",
            }


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------


def get_intelligence_orchestrator() -> IntelligenceOrchestrator:
    """Return the singleton IntelligenceOrchestrator instance."""
    return IntelligenceOrchestrator.get_instance()