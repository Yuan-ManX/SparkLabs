"""
SparkLabs Agent - Cognitive Synthesis Engine

A unified cognitive pipeline that orchestrates reasoning, memory retrieval,
learning, and creative synthesis into a single intelligence framework. The
Cognitive Synthesis Engine is the central intelligence hub that coordinates
all agent subsystems through a structured multi-phase synthesis pipeline.

Architecture:
  CognitiveSynthesisEngine (Singleton)
    |-- ContextBuilder (raw input enrichment, goal extraction, domain alignment)
    |-- MemoryRetriever (multi-mode memory access with relevance ranking)
    |-- ReasoningEngine (multi-step reasoning with depth control and fallback)
    |-- CreativeSynthesizer (constrained creative variation generation)
    |-- SynthesisValidator (output validation against constraints and quality metrics)

Core Capabilities:
  - synthesize: Full pipeline execution from input to validated output
  - step_synthesis: Single-phase granular execution for fine control
  - retrieve_memories: Multi-mode memory retrieval with relevance scoring
  - reason: Multi-step reasoning chain construction with fallback plans
  - create_variations: Creative synthesis with constraint-aware generation
  - validate: Output quality assessment against constraints and metrics
  - get_synthesis_history: Full execution history for audit and analysis
  - get_performance_metrics: Real-time engine performance snapshot

Usage:
    engine = get_cognitive_synthesis()
    report = engine.synthesize(
        input_text="Design a stealth mechanics system for an open-world game",
        goal="Generate a complete game design document section",
        constraints={"format": "markdown", "max_sections": 5, "tone": "professional"},
        depth=ReasoningDepth.DEEP,
    )
    memories = engine.retrieve_memories(
        query="stealth mechanics game design",
        mode=MemoryAccessMode.SEMANTIC,
        limit=10,
    )
    chain = engine.reason(
        problem="How to balance stealth difficulty with player skill progression?",
        depth=ReasoningDepth.DEEP,
        context=report.context,
    )
"""

from __future__ import annotations

import json
import math
import random
import threading
import time as _time_module
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SynthesisPhase(Enum):
    """Ordered phases of the cognitive synthesis pipeline."""
    INPUT_PARSING = "input_parsing"
    CONTEXT_ASSEMBLY = "context_assembly"
    MEMORY_RETRIEVAL = "memory_retrieval"
    REASONING = "reasoning"
    CREATIVE_SYNTHESIS = "creative_synthesis"
    RESPONSE_GENERATION = "response_generation"
    VALIDATION = "validation"
    REFINEMENT = "refinement"

    @classmethod
    def ordered_phases(cls) -> List["SynthesisPhase"]:
        return [
            cls.INPUT_PARSING,
            cls.CONTEXT_ASSEMBLY,
            cls.MEMORY_RETRIEVAL,
            cls.REASONING,
            cls.CREATIVE_SYNTHESIS,
            cls.RESPONSE_GENERATION,
            cls.VALIDATION,
            cls.REFINEMENT,
        ]


class MemoryAccessMode(Enum):
    """Access modes for the memory retrieval subsystem."""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"
    LONG_TERM = "long_term"


class ReasoningDepth(Enum):
    """Depth levels for multi-step reasoning."""
    SHALLOW = "shallow"
    STANDARD = "standard"
    DEEP = "deep"
    EXHAUSTIVE = "exhaustive"

    def max_steps(self) -> int:
        return {
            ReasoningDepth.SHALLOW: 2,
            ReasoningDepth.STANDARD: 5,
            ReasoningDepth.DEEP: 10,
            ReasoningDepth.EXHAUSTIVE: 20,
        }[self]

    def fallback_branches(self) -> int:
        return {
            ReasoningDepth.SHALLOW: 0,
            ReasoningDepth.STANDARD: 1,
            ReasoningDepth.DEEP: 2,
            ReasoningDepth.EXHAUSTIVE: 4,
        }[self]


class CreativeConstraint(Enum):
    """Constraints that guide creative synthesis."""
    FIDELITY = "fidelity"
    NOVELTY = "novelty"
    COHERENCE = "coherence"
    UTILITY = "utility"


class SynthesisConfidence(Enum):
    """Confidence levels for synthesis outputs."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CERTAIN = "certain"

    def to_float(self) -> float:
        return {
            SynthesisConfidence.LOW: 0.25,
            SynthesisConfidence.MEDIUM: 0.55,
            SynthesisConfidence.HIGH: 0.80,
            SynthesisConfidence.CERTAIN: 0.95,
        }[self]

    @classmethod
    def from_float(cls, value: float) -> "SynthesisConfidence":
        if value >= 0.90:
            return cls.CERTAIN
        if value >= 0.70:
            return cls.HIGH
        if value >= 0.40:
            return cls.MEDIUM
        return cls.LOW


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CognitiveContext:
    """Enriched context assembled from raw input for the synthesis pipeline."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    domain_knowledge: Dict[str, Any] = field(default_factory=dict)
    active_focus: List[str] = field(default_factory=list)
    mood_tone: str = "neutral"
    priority_weight: float = 0.5
    parsed_entities: List[str] = field(default_factory=list)
    detected_intent: str = ""
    suggested_approach: str = ""
    complexity_estimate: float = 0.5
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "goal": self.goal,
            "constraints": dict(self.constraints),
            "domain_knowledge": dict(self.domain_knowledge),
            "active_focus": list(self.active_focus),
            "mood_tone": self.mood_tone,
            "priority_weight": round(self.priority_weight, 4),
            "parsed_entities": list(self.parsed_entities),
            "detected_intent": self.detected_intent,
            "suggested_approach": self.suggested_approach,
            "complexity_estimate": round(self.complexity_estimate, 4),
        }


@dataclass
class MemoryPacket:
    """A retrieved memory entry with relevance scoring and decay modeling."""
    mem_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    content: str = ""
    source: str = ""
    timestamp: float = field(default_factory=_time_module.time)
    relevance_score: float = 0.0
    access_count: int = 0
    decay_rate: float = 0.01
    access_mode: str = "semantic"
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.5
    linked_memories: List[str] = field(default_factory=list)

    def effective_relevance(self, current_time: float = None) -> float:
        """Compute relevance after decay."""
        if current_time is None:
            current_time = _time_module.time()
        age = current_time - self.timestamp
        decay = math.exp(-self.decay_rate * max(0.0, age) / 3600.0)
        recency_boost = math.log(1 + self.access_count) * 0.1
        return self.relevance_score * decay + recency_boost

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mem_id": self.mem_id,
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp,
            "relevance_score": round(self.relevance_score, 4),
            "access_count": self.access_count,
            "decay_rate": round(self.decay_rate, 4),
            "access_mode": self.access_mode,
            "tags": list(self.tags),
            "confidence": round(self.confidence, 4),
        }


@dataclass
class ReasoningChain:
    """A complete multi-step reasoning chain with fallback plans."""
    chain_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    premise: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.5
    fallback_plan: Optional[Dict[str, Any]] = None
    depth_used: str = "standard"
    step_count: int = 0
    total_time_ms: float = 0.0
    branches_explored: int = 0
    dead_ends_hit: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "premise": self.premise,
            "steps": [dict(s) for s in self.steps],
            "conclusion": self.conclusion,
            "confidence": round(self.confidence, 4),
            "fallback_plan": dict(self.fallback_plan) if self.fallback_plan else None,
            "depth_used": self.depth_used,
            "step_count": self.step_count,
            "total_time_ms": round(self.total_time_ms, 2),
            "branches_explored": self.branches_explored,
            "dead_ends_hit": self.dead_ends_hit,
        }


@dataclass
class CreativeSynthesis:
    """Result of creative variation generation under constraints."""
    synthesis_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    idea_seed: str = ""
    variations: List[Dict[str, Any]] = field(default_factory=list)
    constraints_applied: List[str] = field(default_factory=list)
    novelty_score: float = 0.0
    coherence_score: float = 0.0
    utility_score: float = 0.0
    composite_score: float = 0.0
    generation_method: str = "divergent"
    iteration_count: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "idea_seed": self.idea_seed,
            "variations": [dict(v) for v in self.variations],
            "constraints_applied": list(self.constraints_applied),
            "novelty_score": round(self.novelty_score, 4),
            "coherence_score": round(self.coherence_score, 4),
            "utility_score": round(self.utility_score, 4),
            "composite_score": round(self.composite_score, 4),
            "generation_method": self.generation_method,
            "iteration_count": self.iteration_count,
        }


@dataclass
class SynthesisReport:
    """Complete report of a synthesis pipeline execution."""
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    phase_timings: Dict[str, float] = field(default_factory=dict)
    memory_accesses: int = 0
    reasoning_depth_used: str = "standard"
    creative_variations: int = 0
    final_output: str = ""
    confidence_distribution: Dict[str, float] = field(default_factory=dict)
    iteration_count: int = 0
    context: Optional[CognitiveContext] = None
    refinement_rounds: int = 0
    total_time_ms: float = 0.0
    success: bool = False
    error_details: Optional[str] = None
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "phase_timings": {k: round(v, 4) for k, v in self.phase_timings.items()},
            "memory_accesses": self.memory_accesses,
            "reasoning_depth_used": self.reasoning_depth_used,
            "creative_variations": self.creative_variations,
            "final_output": self.final_output,
            "confidence_distribution": {k: round(v, 4) for k, v in self.confidence_distribution.items()},
            "iteration_count": self.iteration_count,
            "refinement_rounds": self.refinement_rounds,
            "total_time_ms": round(self.total_time_ms, 2),
            "success": self.success,
            "error_details": self.error_details,
        }


# ---------------------------------------------------------------------------
# Subsystem: ContextBuilder
# ---------------------------------------------------------------------------

class ContextBuilder:
    """Builds and enriches cognitive context from raw input text."""

    _INTENT_PATTERNS: Dict[str, List[str]] = {
        "design": ["design", "create", "build", "architect", "craft"],
        "analyze": ["analyze", "evaluate", "assess", "review", "examine"],
        "optimize": ["optimize", "improve", "enhance", "refine", "tune"],
        "explain": ["explain", "describe", "elaborate", "clarify", "define"],
        "generate": ["generate", "produce", "synthesize", "compose", "write"],
        "debug": ["debug", "fix", "resolve", "troubleshoot", "repair"],
    }

    _TONE_INDICATORS: Dict[str, List[str]] = {
        "professional": ["professional", "formal", "technical", "academic"],
        "creative": ["creative", "innovative", "imaginative", "artistic"],
        "critical": ["critical", "analytical", "rigorous", "precise"],
        "neutral": ["neutral", "balanced", "objective", "unbiased"],
        "enthusiastic": ["enthusiastic", "energetic", "passionate", "exciting"],
    }

    def __init__(self):
        self._build_count: int = 0

    def build(
        self,
        input_text: str,
        goal: str = "",
        constraints: Optional[Dict[str, Any]] = None,
        domain_knowledge: Optional[Dict[str, Any]] = None,
    ) -> CognitiveContext:
        """Parse raw input and assemble an enriched CognitiveContext."""
        if constraints is None:
            constraints = {}
        if domain_knowledge is None:
            domain_knowledge = {}

        context = CognitiveContext(goal=goal, constraints=constraints)

        # Parse entities from input
        context.parsed_entities = self._extract_entities(input_text)

        # Detect intent
        context.detected_intent = self._detect_intent(input_text)

        # Infer mood/tone
        context.mood_tone = self._infer_tone(input_text, constraints)

        # Determine active focus areas
        context.active_focus = self._extract_focus(input_text, goal)

        # Compute complexity estimate
        context.complexity_estimate = self._estimate_complexity(input_text, constraints)

        # Suggest approach
        context.suggested_approach = self._suggest_approach(context)

        # Merge provided domain knowledge
        if domain_knowledge:
            context.domain_knowledge.update(domain_knowledge)

        # Set priority weight based on constraint urgency
        context.priority_weight = self._compute_priority(constraints)

        self._build_count += 1
        return context

    def _extract_entities(self, text: str) -> List[str]:
        """Extract key entities from input text."""
        entities: List[str] = []
        words = text.lower().split()
        significant = [
            w.strip(".,;:!?()[]{}") for w in words
            if len(w.strip(".,;:!?()[]{}")) > 3
        ]
        # Deduplicate while preserving order
        seen: set = set()
        for w in significant:
            if w not in seen:
                seen.add(w)
                entities.append(w)
        return entities[:20]

    def _detect_intent(self, text: str) -> str:
        """Detect the primary intent from input text."""
        text_lower = text.lower()
        scores: Dict[str, int] = {}
        for intent, keywords in self._INTENT_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[intent] = score
        if not scores:
            return "analyze"
        return max(scores, key=lambda k: scores[k])

    def _infer_tone(self, text: str, constraints: Dict[str, Any]) -> str:
        """Infer the desired tone from text and constraints."""
        if "tone" in constraints:
            tone_val = str(constraints["tone"]).lower()
            for tone, indicators in self._TONE_INDICATORS.items():
                if tone_val in indicators or tone == tone_val:
                    return tone
        text_lower = text.lower()
        for tone, indicators in self._TONE_INDICATORS.items():
            if any(ind in text_lower for ind in indicators):
                return tone
        return "neutral"

    def _extract_focus(self, text: str, goal: str) -> List[str]:
        """Extract key focus areas from text and goal."""
        combined = f"{text} {goal}".lower()
        focus_keywords = [
            "performance", "security", "usability", "scalability",
            "reliability", "maintainability", "efficiency", "quality",
            "innovation", "simplicity", "robustness", "flexibility",
        ]
        focus: List[str] = []
        for kw in focus_keywords:
            if kw in combined:
                focus.append(kw)
        return focus if focus else ["quality", "efficiency"]

    def _estimate_complexity(
        self, text: str, constraints: Dict[str, Any]
    ) -> float:
        """Estimate input complexity on a 0-1 scale."""
        word_count = len(text.split())
        constraint_count = len(constraints)
        complexity = min(1.0, (word_count / 200.0) * 0.6 + (constraint_count / 10.0) * 0.4)
        return max(0.1, complexity)

    def _suggest_approach(self, context: CognitiveContext) -> str:
        """Suggest an approach based on detected intent and complexity."""
        if context.complexity_estimate > 0.7:
            base = "decompose-and-iterate"
        elif context.detected_intent == "design":
            base = "divergent-convergent"
        elif context.detected_intent == "analyze":
            base = "systematic-decomposition"
        elif context.detected_intent == "optimize":
            base = "iterative-refinement"
        else:
            base = "direct-generation"
        return base

    def _compute_priority(self, constraints: Dict[str, Any]) -> float:
        """Compute priority weight from constraints."""
        urgency = float(constraints.get("urgency", constraints.get("priority", 0.5)))
        return max(0.1, min(1.0, urgency))


# ---------------------------------------------------------------------------
# Subsystem: MemoryRetriever
# ---------------------------------------------------------------------------

class MemoryRetriever:
    """Accesses and retrieves from memory subsystems with relevance ranking."""

    def __init__(self):
        self._memory_store: Dict[str, Dict[str, List[MemoryPacket]]] = {
            mode.value: defaultdict(list) for mode in MemoryAccessMode
        }
        self._total_retrievals: int = 0
        self._cache: Dict[str, List[MemoryPacket]] = {}
        self._populate_default_memories()

    def _populate_default_memories(self):
        """Seed memory stores with default knowledge across modes."""
        defaults = {
            "episodic": [
                ("User previously requested a stealth system design with emphasis on player agency.", 0.7),
                ("The last game design session focused on open-world traversal mechanics.", 0.6),
                ("Prior iteration on stealth mechanics revealed preference for environmental interaction.", 0.8),
            ],
            "semantic": [
                ("Stealth mechanics include: line-of-sight, sound propagation, cover systems, and alert states.", 0.9),
                ("Game design principles: flow, challenge-reward balance, player feedback loops.", 0.85),
                ("Open-world design patterns: emergent gameplay, systemic interaction, spatial storytelling.", 0.8),
            ],
            "procedural": [
                ("Step 1: Define core stealth verbs (hide, distract, bypass). Step 2: Design detection systems.", 0.75),
                ("Procedure for balancing: establish baseline difficulty, test with playtesters, iterate.", 0.7),
                ("Method: create a state machine for AI guard behaviors (patrol, investigate, alert, chase).", 0.8),
            ],
            "working": [
                ("Current focus: stealth mechanics system design for open-world game.", 0.95),
                ("Active constraints: markdown format, max 5 sections, professional tone.", 0.9),
            ],
            "long_term": [
                ("Fundamental principle: player agency is paramount in stealth game design.", 0.9),
                ("Historical reference: Thief series pioneered light-based stealth in 3D environments.", 0.85),
                ("Established pattern: detection meter UI provides clear feedback to player.", 0.8),
            ],
        }
        now = _time_module.time()
        for mode_str, entries in defaults.items():
            for content, relevance in entries:
                packet = MemoryPacket(
                    content=content,
                    source=f"default_{mode_str}",
                    timestamp=now - random.uniform(0, 3600),
                    relevance_score=relevance,
                    access_mode=mode_str,
                    tags=[mode_str, "default"],
                    confidence=0.7 + random.uniform(0, 0.2),
                )
                self._memory_store[mode_str]["default"].append(packet)

    def retrieve(
        self,
        query: str,
        mode: MemoryAccessMode,
        limit: int = 10,
    ) -> List[MemoryPacket]:
        """Retrieve memories matching the query in the specified access mode."""
        mode_key = mode.value
        if mode_key not in self._memory_store:
            return []

        all_packets: List[MemoryPacket] = []
        for category_packets in self._memory_store[mode_key].values():
            all_packets.extend(category_packets)

        if not all_packets:
            return []

        # Score each packet against the query
        query_terms = set(query.lower().split())
        scored: List[Tuple[MemoryPacket, float]] = []
        for packet in all_packets:
            content_lower = packet.content.lower()
            term_matches = sum(1 for t in query_terms if t in content_lower)
            semantic_score = term_matches / max(1, len(query_terms))
            effective_rel = packet.effective_relevance()
            combined_score = 0.5 * semantic_score + 0.3 * effective_rel + 0.2 * packet.confidence
            scored.append((packet, combined_score))

        # Sort by combined score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for packet, score in scored[:limit]:
            packet.access_count += 1
            packet.relevance_score = max(packet.relevance_score, score)
            results.append(packet)

        self._total_retrievals += 1
        return results

    def store(
        self,
        content: str,
        mode: MemoryAccessMode,
        source: str = "runtime",
        relevance_score: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> MemoryPacket:
        """Store a new memory packet in the specified mode."""
        packet = MemoryPacket(
            content=content,
            source=source,
            access_mode=mode.value,
            relevance_score=relevance_score,
            tags=tags or [],
        )
        self._memory_store[mode.value][source].append(packet)
        return packet

    def get_stats(self) -> Dict[str, Any]:
        """Return retrieval statistics."""
        stats = {}
        for mode_key, categories in self._memory_store.items():
            total = sum(len(pkts) for pkts in categories.values())
            stats[mode_key] = total
        return {
            "total_packets": sum(stats.values()),
            "by_mode": stats,
            "total_retrievals": self._total_retrievals,
        }


# ---------------------------------------------------------------------------
# Subsystem: ReasoningEngine
# ---------------------------------------------------------------------------

class ReasoningEngine:
    """Performs multi-step reasoning with depth control and fallback."""

    def __init__(self):
        self._chain_count: int = 0
        self._reasoning_templates: Dict[str, List[str]] = {
            "design": [
                "Identify core requirements and constraints",
                "Analyze existing solutions and patterns",
                "Generate alternative approaches",
                "Evaluate trade-offs between alternatives",
                "Synthesize recommended solution with rationale",
            ],
            "analyze": [
                "Decompose the problem into constituent parts",
                "Examine relationships between components",
                "Identify root causes and dependencies",
                "Assess implications and edge cases",
                "Formulate conclusions with evidence",
            ],
            "optimize": [
                "Establish baseline metrics",
                "Identify bottlenecks and inefficiencies",
                "Propose targeted improvements",
                "Evaluate improvement impact",
                "Recommend priority order for implementation",
            ],
            "general": [
                "Clarify the problem statement",
                "Gather relevant information",
                "Formulate hypotheses",
                "Test hypotheses against constraints",
                "Draw conclusions with confidence assessment",
            ],
        }

    def reason(
        self,
        problem: str,
        depth: ReasoningDepth,
        context: Optional[CognitiveContext] = None,
    ) -> ReasoningChain:
        """Execute multi-step reasoning on the given problem."""
        start_time = _time_module.time()
        max_steps = depth.max_steps()
        fallback_branches = depth.fallback_branches()

        # Select reasoning template
        intent = "general"
        if context and context.detected_intent:
            intent = context.detected_intent
        template = self._reasoning_templates.get(
            intent, self._reasoning_templates["general"]
        )

        # Build reasoning steps
        steps: List[Dict[str, Any]] = []
        step_count = min(max_steps, len(template))

        for i in range(step_count):
            step = self._execute_reasoning_step(
                template[i], problem, i, step_count, context
            )
            steps.append(step)

            # Check for early termination
            if step.get("is_terminal", False):
                break

        # Generate conclusion
        conclusion = self._synthesize_conclusion(steps, problem, depth)

        # Build fallback plan if configured
        fallback = None
        if fallback_branches > 0:
            fallback = self._build_fallback_plan(problem, steps, fallback_branches)

        # Compute confidence
        confidence = self._compute_chain_confidence(steps, depth)

        elapsed = (_time_module.time() - start_time) * 1000.0

        chain = ReasoningChain(
            premise=problem,
            steps=steps,
            conclusion=conclusion,
            confidence=confidence,
            fallback_plan=fallback,
            depth_used=depth.value,
            step_count=len(steps),
            total_time_ms=elapsed,
            branches_explored=fallback_branches,
            dead_ends_hit=random.randint(0, max(0, fallback_branches - 1)),
        )

        self._chain_count += 1
        return chain

    def _execute_reasoning_step(
        self,
        step_template: str,
        problem: str,
        step_index: int,
        total_steps: int,
        context: Optional[CognitiveContext],
    ) -> Dict[str, Any]:
        """Execute a single reasoning step, returning a structured result."""
        # Simulate reasoning with structured output
        outputs = {
            "Identify core requirements": "Key requirements identified: functional scope, performance targets, user experience goals.",
            "Analyze existing solutions": "Analysis of existing solutions: pattern matching reveals 3 relevant approaches with varying trade-offs.",
            "Generate alternative approaches": "Generated 3 alternative approaches: conservative, innovative, and hybrid strategies.",
            "Evaluate trade-offs": "Trade-off evaluation: approach A (best performance), approach B (best flexibility), approach C (best balance).",
            "Synthesize recommended solution": "Recommended solution: hybrid approach combining the strengths of approaches A and B.",
            "Decompose the problem": "Problem decomposition: identified 4 sub-problems with clear dependencies.",
            "Examine relationships": "Relationship analysis: strong coupling between components 1-2, weak coupling between 2-3.",
            "Identify root causes": "Root cause analysis: primary factor is resource contention, secondary is configuration drift.",
            "Assess implications": "Implications assessment: 3 high-impact areas, 2 moderate, 1 low with mitigation plan.",
            "Formulate conclusions": "Conclusions formulated with supporting evidence from all prior analysis steps.",
            "Establish baseline metrics": "Baseline established: current performance at 60% of target, with 3 key metrics identified.",
            "Identify bottlenecks": "Bottleneck identification: 2 critical bottlenecks found in data pipeline and rendering layer.",
            "Propose targeted improvements": "Improvement proposals: 5 targeted changes with estimated impact ranges.",
            "Evaluate improvement impact": "Impact evaluation: projected 25-40% improvement with proposed changes.",
            "Recommend priority order": "Priority order: changes 1 and 3 first (highest ROI), then 2, 4, and 5.",
            "Clarify the problem statement": "Problem clarified: scope defined, edge cases identified, success criteria established.",
            "Gather relevant information": "Information gathered: 4 relevant sources identified with key insights extracted.",
            "Formulate hypotheses": "Hypotheses formulated: 3 testable hypotheses with prediction criteria.",
            "Test hypotheses": "Hypothesis testing: 2 of 3 hypotheses confirmed, 1 requires further investigation.",
            "Draw conclusions": "Conclusions drawn with confidence assessment and remaining uncertainties noted.",
        }

        result_text = outputs.get(step_template, f"Step {step_index + 1} completed: {step_template}")

        # Add some variation based on context
        if context and context.complexity_estimate > 0.6:
            result_text += " (high complexity: additional edge cases considered)"

        return {
            "step_index": step_index,
            "step_label": step_template,
            "result": result_text,
            "confidence": 0.7 + random.uniform(-0.2, 0.2),
            "is_terminal": step_index >= total_steps - 1,
            "time_ms": 10.0 + random.uniform(0, 30.0),
        }

    def _synthesize_conclusion(
        self,
        steps: List[Dict[str, Any]],
        problem: str,
        depth: ReasoningDepth,
    ) -> str:
        """Synthesize a conclusion from reasoning steps."""
        if not steps:
            return "Unable to reach a conclusion: insufficient reasoning steps."

        key_points = [s["result"] for s in steps[-3:]]
        depth_qualifier = {
            ReasoningDepth.SHALLOW: "Based on initial analysis",
            ReasoningDepth.STANDARD: "After thorough reasoning",
            ReasoningDepth.DEEP: "Following deep multi-step analysis",
            ReasoningDepth.EXHAUSTIVE: "After exhaustive examination of all factors",
        }

        conclusion = (
            f"{depth_qualifier[depth]}, the following conclusion is reached: "
            f"{' '.join(key_points)} "
            f"Overall recommendation addresses the core problem: {problem[:100]}..."
        )
        return conclusion

    def _build_fallback_plan(
        self,
        problem: str,
        primary_steps: List[Dict[str, Any]],
        num_branches: int,
    ) -> Dict[str, Any]:
        """Build fallback reasoning branches."""
        alternatives = []
        for i in range(num_branches):
            alt = {
                "branch_id": f"fallback_{i + 1}",
                "approach": f"Alternative approach {i + 1}",
                "trigger_condition": f"Primary step {max(1, len(primary_steps) - 2)} confidence below threshold",
                "estimated_confidence": 0.5 + random.uniform(0, 0.3),
            }
            alternatives.append(alt)
        return {
            "problem": problem,
            "alternatives": alternatives,
            "trigger_threshold": 0.4,
        }

    def _compute_chain_confidence(
        self,
        steps: List[Dict[str, Any]],
        depth: ReasoningDepth,
    ) -> float:
        """Compute overall confidence for the reasoning chain."""
        if not steps:
            return 0.1

        avg_step_confidence = sum(s.get("confidence", 0.5) for s in steps) / len(steps)
        depth_factor = {
            ReasoningDepth.SHALLOW: 0.7,
            ReasoningDepth.STANDARD: 0.85,
            ReasoningDepth.DEEP: 0.93,
            ReasoningDepth.EXHAUSTIVE: 0.98,
        }
        chain_confidence = avg_step_confidence * depth_factor[depth]
        return max(0.1, min(0.99, chain_confidence))


# ---------------------------------------------------------------------------
# Subsystem: CreativeSynthesizer
# ---------------------------------------------------------------------------

class CreativeSynthesizer:
    """Generates creative variations within defined constraints."""

    _VARIATION_PREFIXES: List[str] = [
        "A conventional approach:",
        "An innovative twist:",
        "A hybrid solution:",
        "A minimalist interpretation:",
        "A maximalist design:",
        "A player-centric view:",
        "A systems-driven design:",
        "A narrative-integrated approach:",
        "A data-driven method:",
        "An emergent design:",
    ]

    def __init__(self):
        self._synthesis_count: int = 0

    def create_variations(
        self,
        seed: str,
        constraints: List[CreativeConstraint],
        count: int = 3,
    ) -> CreativeSynthesis:
        """Generate creative variations from a seed idea under constraints."""
        variations: List[Dict[str, Any]] = []
        constraint_names = [c.value for c in constraints]

        for i in range(min(count, len(self._VARIATION_PREFIXES))):
            variation = self._generate_variation(seed, i, constraints)
            variations.append(variation)

        # Compute quality scores
        novelty = self._compute_novelty(variations, seed)
        coherence = self._compute_coherence(variations, seed)
        utility = self._compute_utility(variations, constraints)

        composite = (
            0.35 * novelty
            + 0.35 * coherence
            + 0.30 * utility
        )

        synthesis = CreativeSynthesis(
            idea_seed=seed,
            variations=variations,
            constraints_applied=constraint_names,
            novelty_score=novelty,
            coherence_score=coherence,
            utility_score=utility,
            composite_score=composite,
            generation_method="divergent" if count > 1 else "convergent",
            iteration_count=count,
        )

        self._synthesis_count += 1
        return synthesis

    def _generate_variation(
        self,
        seed: str,
        index: int,
        constraints: List[CreativeConstraint],
    ) -> Dict[str, Any]:
        """Generate a single variation with constraint-aware content."""
        # Simulate constraint weights
        fidelity_weight = 1.0 if CreativeConstraint.FIDELITY in constraints else 0.3
        novelty_weight = 1.0 if CreativeConstraint.NOVELTY in constraints else 0.3
        coherence_weight = 1.0 if CreativeConstraint.COHERENCE in constraints else 0.3
        utility_weight = 1.0 if CreativeConstraint.UTILITY in constraints else 0.3

        prefix = self._VARIATION_PREFIXES[index % len(self._VARIATION_PREFIXES)]
        content = self._generate_content_for_variation(seed, index)

        return {
            "variation_id": uuid.uuid4().hex,
            "label": f"Variation {index + 1}: {prefix}",
            "content": content,
            "scores": {
                "fidelity": round(0.6 + random.uniform(0, 0.4) * fidelity_weight, 4),
                "novelty": round(0.3 + random.uniform(0, 0.7) * novelty_weight, 4),
                "coherence": round(0.5 + random.uniform(0, 0.5) * coherence_weight, 4),
                "utility": round(0.4 + random.uniform(0, 0.6) * utility_weight, 4),
            },
            "seed_reference": seed[:80],
            "generation_index": index,
        }

    def _generate_content_for_variation(self, seed: str, index: int) -> str:
        """Generate content for a variation based on the seed and index."""
        suffixes = [
            "Focusing on core mechanics and traditional design patterns.",
            "Introducing novel mechanics that challenge established conventions.",
            "Blending multiple approaches for a balanced and flexible solution.",
            "Stripping down to essential elements for maximum clarity.",
            "Expanding scope to include rich, interconnected systems.",
            "Prioritizing player experience and intuitive interaction design.",
            "Emphasizing emergent properties through systemic interactions.",
            "Weaving narrative elements into the mechanical design.",
            "Using quantitative metrics to drive design decisions.",
            "Allowing complexity to emerge from simple, composable rules.",
        ]
        return f"{seed[:50]}... {suffixes[index % len(suffixes)]}"

    def _compute_novelty(
        self, variations: List[Dict[str, Any]], seed: str
    ) -> float:
        """Compute overall novelty score across variations."""
        if not variations:
            return 0.0
        novelty_scores = [v["scores"]["novelty"] for v in variations]
        return sum(novelty_scores) / len(novelty_scores)

    def _compute_coherence(
        self, variations: List[Dict[str, Any]], seed: str
    ) -> float:
        """Compute overall coherence score across variations."""
        if not variations:
            return 0.0
        coherence_scores = [v["scores"]["coherence"] for v in variations]
        return sum(coherence_scores) / len(coherence_scores)

    def _compute_utility(
        self,
        variations: List[Dict[str, Any]],
        constraints: List[CreativeConstraint],
    ) -> float:
        """Compute overall utility score across variations."""
        if not variations:
            return 0.0
        utility_scores = [v["scores"]["utility"] for v in variations]
        base = sum(utility_scores) / len(utility_scores)
        # Boost if utility constraint is active
        if CreativeConstraint.UTILITY in constraints:
            base = min(1.0, base + 0.1)
        return base


# ---------------------------------------------------------------------------
# Subsystem: SynthesisValidator
# ---------------------------------------------------------------------------

class SynthesisValidator:
    """Validates outputs against constraints and quality metrics."""

    _QUALITY_DIMENSIONS: List[str] = [
        "completeness", "accuracy", "relevance", "clarity",
        "consistency", "actionability", "depth", "originality",
    ]

    def __init__(self):
        self._validation_count: int = 0

    def validate(
        self,
        output: str,
        constraints: Dict[str, Any],
        context: Optional[CognitiveContext] = None,
    ) -> Dict[str, Any]:
        """Validate synthesis output against constraints and quality metrics."""
        results: Dict[str, Any] = {
            "passed": True,
            "overall_score": 0.0,
            "dimension_scores": {},
            "constraint_checks": {},
            "issues": [],
            "warnings": [],
            "suggestions": [],
        }

        # Evaluate each quality dimension
        for dim in self._QUALITY_DIMENSIONS:
            score = self._evaluate_dimension(output, dim, constraints, context)
            results["dimension_scores"][dim] = round(score, 4)

        # Check each constraint
        for key, value in constraints.items():
            check = self._check_constraint(output, key, value)
            results["constraint_checks"][key] = check
            if not check.get("passed", True):
                results["passed"] = False
                results["issues"].append(f"Constraint '{key}' failed: {check.get('reason', 'unknown')}")

        # Compute overall score
        if results["dimension_scores"]:
            results["overall_score"] = round(
                sum(results["dimension_scores"].values()) / len(results["dimension_scores"]), 4
            )

        # Generate suggestions if needed
        if results["overall_score"] < 0.6:
            results["suggestions"] = self._generate_suggestions(results)

        # Add warnings for borderline cases
        for dim, score in results["dimension_scores"].items():
            if 0.4 <= score < 0.6:
                results["warnings"].append(f"Dimension '{dim}' is borderline (score: {score:.2f})")

        self._validation_count += 1
        return results

    def _evaluate_dimension(
        self,
        output: str,
        dimension: str,
        constraints: Dict[str, Any],
        context: Optional[CognitiveContext],
    ) -> float:
        """Evaluate a single quality dimension."""
        word_count = len(output.split())
        sentence_count = output.count(".") + output.count("!") + output.count("?")

        # Heuristic scoring per dimension
        if dimension == "completeness":
            return min(1.0, word_count / 200.0)
        elif dimension == "accuracy":
            # Check for hedging language as a proxy
            hedging = sum(1 for w in ["might", "could", "maybe", "perhaps", "possibly"]
                          if w in output.lower())
            return max(0.3, 1.0 - hedging * 0.15)
        elif dimension == "relevance":
            return 0.7 + random.uniform(-0.1, 0.2)
        elif dimension == "clarity":
            if sentence_count == 0:
                return 0.3
            avg_words_per_sentence = word_count / max(1, sentence_count)
            # Prefer sentences between 10-30 words
            if 10 <= avg_words_per_sentence <= 30:
                return 0.85 + random.uniform(-0.1, 0.15)
            return 0.5 + random.uniform(-0.1, 0.2)
        elif dimension == "consistency":
            return 0.75 + random.uniform(-0.15, 0.15)
        elif dimension == "actionability":
            action_words = sum(1 for w in ["should", "must", "recommend", "implement", "apply",
                                            "create", "build", "execute", "follow"]
                              if w in output.lower())
            return min(1.0, 0.3 + action_words * 0.1)
        elif dimension == "depth":
            return min(1.0, word_count / 300.0)
        elif dimension == "originality":
            return 0.6 + random.uniform(-0.2, 0.3)
        return 0.5

    def _check_constraint(
        self, output: str, key: str, value: Any
    ) -> Dict[str, Any]:
        """Check a single constraint against the output."""
        result = {"passed": True, "constraint": key, "expected": str(value)}

        if key == "max_sections":
            sections = output.count("\n##") + output.count("\n#")
            if sections > int(value):
                result["passed"] = False
                result["reason"] = f"Expected max {value} sections, found {sections}"
        elif key == "format":
            if str(value).lower() == "markdown":
                has_md = any(marker in output for marker in ["#", "**", "- ", "```"])
                if not has_md:
                    result["passed"] = False
                    result["reason"] = "Output does not contain markdown formatting"
        elif key == "min_length":
            if len(output.split()) < int(value):
                result["passed"] = False
                result["reason"] = f"Output too short: {len(output.split())} words, minimum {value}"
        elif key == "max_length":
            if len(output.split()) > int(value):
                result["passed"] = False
                result["reason"] = f"Output too long: {len(output.split())} words, maximum {value}"
        elif key == "tone":
            # Simple tone check
            tone_indicators = {
                "professional": ["professional", "formal", "analysis", "recommend", "accordingly"],
                "creative": ["creative", "innovative", "imagine", "explore", "novel"],
            }
            expected = tone_indicators.get(str(value).lower(), [])
            if expected:
                matches = sum(1 for w in expected if w in output.lower())
                if matches == 0:
                    result["passed"] = False
                    result["reason"] = f"Output does not match expected tone: {value}"

        return result

    def _generate_suggestions(self, results: Dict[str, Any]) -> List[str]:
        """Generate improvement suggestions based on validation results."""
        suggestions = []
        for dim, score in results["dimension_scores"].items():
            if score < 0.4:
                suggestions.append(f"Improve {dim}: current score is {score:.2f}")
            elif score < 0.6:
                suggestions.append(f"Consider enhancing {dim}: score is {score:.2f}")
        return suggestions


# ---------------------------------------------------------------------------
# CognitiveSynthesisEngine - Singleton
# ---------------------------------------------------------------------------

class CognitiveSynthesisEngine:
    """Central intelligence hub that orchestrates all cognitive synthesis subsystems.

    The CognitiveSynthesisEngine coordinates ContextBuilder, MemoryRetriever,
    ReasoningEngine, CreativeSynthesizer, and SynthesisValidator through a
    unified multi-phase synthesis pipeline. It is the primary entry point for
    all agent intelligence operations.
    """

    _instance: Optional["CognitiveSynthesisEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_HISTORY_SIZE: int = 500
    MAX_MEMORIES_PER_STORE: int = 1000

    def __new__(cls) -> "CognitiveSynthesisEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "CognitiveSynthesisEngine":
        """Get or create the singleton CognitiveSynthesisEngine instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._context_builder = ContextBuilder()
            self._memory_retriever = MemoryRetriever()
            self._reasoning_engine = ReasoningEngine()
            self._creative_synthesizer = CreativeSynthesizer()
            self._validator = SynthesisValidator()
            self._history: deque = deque(maxlen=self.MAX_HISTORY_SIZE)
            self._total_syntheses: int = 0
            self._total_errors: int = 0
            self._phase_timing_accumulator: Dict[str, List[float]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Full Pipeline: synthesize
    # ------------------------------------------------------------------

    def synthesize(
        self,
        input_text: str,
        goal: str = "",
        constraints: Optional[Dict[str, Any]] = None,
        depth: ReasoningDepth = ReasoningDepth.STANDARD,
    ) -> SynthesisReport:
        """Execute the full cognitive synthesis pipeline.

        Args:
            input_text: The raw input to synthesize.
            goal: Optional high-level goal for the synthesis.
            constraints: Optional constraints dict (e.g., format, max_sections, tone).
            depth: Reasoning depth for the analysis.

        Returns:
            A SynthesisReport containing the complete results and metadata.
        """
        if constraints is None:
            constraints = {}

        pipeline_start = _time_module.time()
        report = SynthesisReport(reasoning_depth_used=depth.value)
        phase_timings: Dict[str, float] = {}

        try:
            # Phase 1: INPUT_PARSING — build context
            p_start = _time_module.time()
            context = self._context_builder.build(
                input_text=input_text,
                goal=goal,
                constraints=constraints,
            )
            phase_timings[SynthesisPhase.INPUT_PARSING.value] = (
                _time_module.time() - p_start
            ) * 1000.0
            report.context = context

            # Phase 2: CONTEXT_ASSEMBLY — enrich with goal
            p_start = _time_module.time()
            context = self._enrich_context(context, input_text)
            phase_timings[SynthesisPhase.CONTEXT_ASSEMBLY.value] = (
                _time_module.time() - p_start
            ) * 1000.0

            # Phase 3: MEMORY_RETRIEVAL — retrieve relevant memories
            p_start = _time_module.time()
            memories = self._memory_retriever.retrieve(
                query=input_text,
                mode=MemoryAccessMode.SEMANTIC,
                limit=10,
            )
            report.memory_accesses = len(memories)
            phase_timings[SynthesisPhase.MEMORY_RETRIEVAL.value] = (
                _time_module.time() - p_start
            ) * 1000.0

            # Phase 4: REASONING — multi-step reasoning
            p_start = _time_module.time()
            reasoning_chain = self._reasoning_engine.reason(
                problem=input_text,
                depth=depth,
                context=context,
            )
            phase_timings[SynthesisPhase.REASONING.value] = (
                _time_module.time() - p_start
            ) * 1000.0

            # Phase 5: CREATIVE_SYNTHESIS — generate variations
            p_start = _time_module.time()
            creative_constraints = [
                CreativeConstraint.COHERENCE,
                CreativeConstraint.UTILITY,
            ]
            if constraints.get("creative", False):
                creative_constraints.append(CreativeConstraint.NOVELTY)
            if constraints.get("faithful", True):
                creative_constraints.append(CreativeConstraint.FIDELITY)

            creative = self._creative_synthesizer.create_variations(
                seed=reasoning_chain.conclusion,
                constraints=creative_constraints,
                count=3,
            )
            report.creative_variations = len(creative.variations)
            phase_timings[SynthesisPhase.CREATIVE_SYNTHESIS.value] = (
                _time_module.time() - p_start
            ) * 1000.0

            # Phase 6: RESPONSE_GENERATION — compose final output
            p_start = _time_module.time()
            final_output = self._generate_response(
                context=context,
                reasoning_chain=reasoning_chain,
                creative=creative,
                memories=memories,
                constraints=constraints,
            )
            report.final_output = final_output
            phase_timings[SynthesisPhase.RESPONSE_GENERATION.value] = (
                _time_module.time() - p_start
            ) * 1000.0

            # Phase 7: VALIDATION — validate output
            p_start = _time_module.time()
            validation = self._validator.validate(
                output=final_output,
                constraints=constraints,
                context=context,
            )
            phase_timings[SynthesisPhase.VALIDATION.value] = (
                _time_module.time() - p_start
            ) * 1000.0

            # Phase 8: REFINEMENT — refine if needed
            p_start = _time_module.time()
            if not validation["passed"] or validation["overall_score"] < 0.6:
                final_output = self._refine_output(
                    final_output=final_output,
                    validation=validation,
                    context=context,
                )
                report.final_output = final_output
                report.refinement_rounds = 1
                # Re-validate
                validation = self._validator.validate(
                    output=final_output,
                    constraints=constraints,
                    context=context,
                )
            phase_timings[SynthesisPhase.REFINEMENT.value] = (
                _time_module.time() - p_start
            ) * 1000.0

            # Finalize report
            report.phase_timings = phase_timings
            report.total_time_ms = (_time_module.time() - pipeline_start) * 1000.0
            report.confidence_distribution = {
                "reasoning": round(reasoning_chain.confidence, 4),
                "creative_novelty": round(creative.novelty_score, 4),
                "creative_coherence": round(creative.coherence_score, 4),
                "creative_utility": round(creative.utility_score, 4),
                "validation": round(validation["overall_score"], 4),
            }
            report.iteration_count = 1
            report.success = validation["passed"]

            self._total_syntheses += 1
            self._history.append(report)

            # Accumulate phase timings for metrics
            for phase, timing in phase_timings.items():
                self._phase_timing_accumulator[phase].append(timing)

        except Exception as e:
            report.error_details = str(e)
            report.success = False
            report.total_time_ms = (_time_module.time() - pipeline_start) * 1000.0
            self._total_errors += 1

        return report

    # ------------------------------------------------------------------
    # Step Synthesis
    # ------------------------------------------------------------------

    def step_synthesis(
        self,
        phase: SynthesisPhase,
        context: CognitiveContext,
    ) -> Dict[str, Any]:
        """Execute a single phase of the synthesis pipeline in isolation.

        Args:
            phase: The specific synthesis phase to execute.
            context: The current cognitive context.

        Returns:
            A dict with phase-specific results and metadata.
        """
        try:
            if phase == SynthesisPhase.INPUT_PARSING:
                return {"phase": phase.value, "context": context.to_dict()}
            elif phase == SynthesisPhase.CONTEXT_ASSEMBLY:
                enriched = self._enrich_context(context, context.goal)
                return {"phase": phase.value, "context": enriched.to_dict()}
            elif phase == SynthesisPhase.MEMORY_RETRIEVAL:
                memories = self._memory_retriever.retrieve(
                    query=context.goal,
                    mode=MemoryAccessMode.SEMANTIC,
                    limit=10,
                )
                return {
                    "phase": phase.value,
                    "memories": [m.to_dict() for m in memories],
                    "count": len(memories),
                }
            elif phase == SynthesisPhase.REASONING:
                chain = self._reasoning_engine.reason(
                    problem=context.goal,
                    depth=ReasoningDepth.STANDARD,
                    context=context,
                )
                return {"phase": phase.value, "reasoning": chain.to_dict()}
            elif phase == SynthesisPhase.CREATIVE_SYNTHESIS:
                creative = self._creative_synthesizer.create_variations(
                    seed=context.goal,
                    constraints=[CreativeConstraint.COHERENCE, CreativeConstraint.UTILITY],
                    count=3,
                )
                return {"phase": phase.value, "creative": creative.to_dict()}
            elif phase == SynthesisPhase.RESPONSE_GENERATION:
                return {"phase": phase.value, "output": "Response generated successfully."}
            elif phase == SynthesisPhase.VALIDATION:
                validation = self._validator.validate(
                    output=context.goal or "",
                    constraints=context.constraints,
                    context=context,
                )
                return {"phase": phase.value, "validation": validation}
            elif phase == SynthesisPhase.REFINEMENT:
                return {"phase": phase.value, "refined": True, "rounds": 1}
            else:
                return {"phase": phase.value, "error": "Unknown phase"}
        except Exception as e:
            return {"phase": phase.value, "error": str(e)}

    # ------------------------------------------------------------------
    # Memory Retrieval
    # ------------------------------------------------------------------

    def retrieve_memories(
        self,
        query: str,
        mode: MemoryAccessMode,
        limit: int = 10,
    ) -> List[MemoryPacket]:
        """Retrieve memories from the specified access mode.

        Args:
            query: The search query for memory retrieval.
            mode: Which memory subsystem to access.
            limit: Maximum number of results to return.

        Returns:
            A list of MemoryPacket objects ranked by relevance.
        """
        try:
            return self._memory_retriever.retrieve(
                query=query,
                mode=mode,
                limit=limit,
            )
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Reasoning
    # ------------------------------------------------------------------

    def reason(
        self,
        problem: str,
        depth: ReasoningDepth,
        context: CognitiveContext,
    ) -> ReasoningChain:
        """Perform multi-step reasoning with depth control.

        Args:
            problem: The problem statement to reason about.
            depth: The reasoning depth level.
            context: The cognitive context for the reasoning.

        Returns:
            A ReasoningChain with steps, conclusion, and confidence.
        """
        try:
            return self._reasoning_engine.reason(
                problem=problem,
                depth=depth,
                context=context,
            )
        except Exception as e:
            return ReasoningChain(
                premise=problem,
                conclusion=f"Reasoning failed: {e}",
                confidence=0.1,
                depth_used=depth.value,
            )

    # ------------------------------------------------------------------
    # Creative Variations
    # ------------------------------------------------------------------

    def create_variations(
        self,
        seed: str,
        constraints: List[CreativeConstraint],
        count: int = 3,
    ) -> CreativeSynthesis:
        """Generate creative variations from a seed idea.

        Args:
            seed: The seed idea to generate variations from.
            constraints: List of creative constraints to apply.
            count: Number of variations to generate.

        Returns:
            A CreativeSynthesis with generated variations and quality scores.
        """
        try:
            return self._creative_synthesizer.create_variations(
                seed=seed,
                constraints=constraints,
                count=count,
            )
        except Exception as e:
            return CreativeSynthesis(
                idea_seed=seed,
                constraints_applied=[c.value for c in constraints],
                novelty_score=0.0,
                coherence_score=0.0,
                utility_score=0.0,
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(
        self,
        output: str,
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate output against constraints and quality metrics.

        Args:
            output: The output text to validate.
            constraints: Dict of constraints to check against.

        Returns:
            A dict with validation results including scores and issues.
        """
        try:
            return self._validator.validate(output=output, constraints=constraints)
        except Exception as e:
            return {"passed": False, "error": str(e)}

    # ------------------------------------------------------------------
    # History and Metrics
    # ------------------------------------------------------------------

    def get_synthesis_history(self) -> List[SynthesisReport]:
        """Return the complete synthesis execution history.

        Returns:
            A list of SynthesisReport objects, newest first.
        """
        return list(reversed(self._history))

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Return real-time performance metrics for the engine.

        Returns:
            A dict with aggregated performance statistics.
        """
        avg_timings = {}
        for phase, timings in self._phase_timing_accumulator.items():
            if timings:
                avg_timings[phase] = {
                    "avg_ms": round(sum(timings) / len(timings), 2),
                    "min_ms": round(min(timings), 2),
                    "max_ms": round(max(timings), 2),
                    "count": len(timings),
                }

        memory_stats = self._memory_retriever.get_stats()

        return {
            "total_syntheses": self._total_syntheses,
            "total_errors": self._total_errors,
            "error_rate": round(
                self._total_errors / max(1, self._total_syntheses), 4
            ),
            "history_size": len(self._history),
            "average_phase_timings_ms": avg_timings,
            "memory_stats": memory_stats,
            "reasoning_chains": self._reasoning_engine._chain_count,
            "creative_syntheses": self._creative_synthesizer._synthesis_count,
            "validations": self._validator._validation_count,
        }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _enrich_context(
        self, context: CognitiveContext, input_text: str
    ) -> CognitiveContext:
        """Enrich the cognitive context with additional derived information."""
        # Add domain knowledge from input
        domain_terms = [
            "game", "design", "mechanics", "system", "player",
            "level", "ui", "physics", "ai", "rendering",
            "stealth", "combat", "puzzle", "narrative", "simulation",
        ]
        for term in domain_terms:
            if term in input_text.lower():
                context.domain_knowledge[term] = True

        # Adjust complexity based on goal length
        if context.goal:
            context.complexity_estimate = min(
                1.0, context.complexity_estimate + len(context.goal.split()) * 0.02
            )

        return context

    def _generate_response(
        self,
        context: CognitiveContext,
        reasoning_chain: ReasoningChain,
        creative: CreativeSynthesis,
        memories: List[MemoryPacket],
        constraints: Dict[str, Any],
    ) -> str:
        """Compose the final synthesis output from all pipeline results."""
        parts: List[str] = []

        # Header
        if constraints.get("format", "").lower() == "markdown":
            parts.append(f"# Synthesis: {context.goal or 'Analysis'}\n")
        else:
            parts.append(f"Synthesis: {context.goal or 'Analysis'}\n")

        # Reasoning summary
        parts.append(f"## Reasoning Analysis\n")
        parts.append(f"**Premise**: {reasoning_chain.premise}\n")
        parts.append(f"**Steps**: {len(reasoning_chain.steps)} reasoning steps executed\n")
        for step in reasoning_chain.steps:
            parts.append(f"- {step['step_label']}: {step['result']}\n")
        parts.append(f"\n**Conclusion**: {reasoning_chain.conclusion}\n")
        parts.append(f"**Confidence**: {reasoning_chain.confidence:.2%}\n")

        # Creative variations
        parts.append(f"\n## Creative Variations\n")
        for var in creative.variations:
            parts.append(f"- **{var['label']}**\n")
            parts.append(f"  {var['content']}\n")

        # Memory integration
        if memories:
            parts.append(f"\n## Related Knowledge\n")
            for mem in memories[:5]:
                parts.append(f"- {mem.content}\n")

        # Fallback plan
        if reasoning_chain.fallback_plan:
            parts.append(f"\n## Contingency Plan\n")
            alternatives = reasoning_chain.fallback_plan.get("alternatives", [])
            for alt in alternatives:
                parts.append(f"- {alt.get('approach', 'Alternative')}: {alt.get('trigger_condition', '')}\n")

        return "\n".join(parts)

    def _refine_output(
        self,
        final_output: str,
        validation: Dict[str, Any],
        context: CognitiveContext,
    ) -> str:
        """Refine output based on validation feedback."""
        refined = final_output

        # Apply suggestions
        for suggestion in validation.get("suggestions", []):
            refined += f"\n\n*[Refinement: {suggestion}]*\n"

        # Add any missing sections
        if "completeness" in validation.get("dimension_scores", {}):
            score = validation["dimension_scores"]["completeness"]
            if score < 0.5:
                refined += "\n\n## Additional Considerations\n\n"
                refined += "Further analysis suggests additional factors to explore:\n"
                refined += "- Edge cases and boundary conditions\n"
                refined += "- Long-term implications and sustainability\n"
                refined += "- Integration with existing systems\n"

        return refined


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_cognitive_synthesis() -> CognitiveSynthesisEngine:
    """Get or create the global CognitiveSynthesisEngine singleton."""
    return CognitiveSynthesisEngine.get_instance()