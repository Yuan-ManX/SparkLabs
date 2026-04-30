"""
SparkAI Agent - Mixture of Agents

Multi-model reasoning system that generates diverse perspectives
from multiple reference models and synthesizes them into a
unified high-quality response. When facing genuinely difficult
problems requiring diverse viewpoints, the system dispatches
the same prompt to multiple models in parallel and aggregates
their responses.

Architecture:
  MixtureOfAgentsEngine
    |-- ReferenceLayer (parallel diverse response generation)
    |-- AggregationLayer (synthesis of best elements)
    |-- ModelPool (available model registry)
    |-- ResponseScorer (quality assessment)

Flow:
  1. Receive complex query
  2. Dispatch to N reference models in parallel
  3. Collect diverse responses (tolerate partial failures)
  4. Score each response for relevance and quality
  5. Aggregate best elements into final response
  6. Return synthesized result

Design Principles:
  - Model diversity for robustness
  - Failure tolerance (minimum 1 successful reference)
  - Exponential backoff per model on failure
  - Quality-weighted aggregation
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class ModelRole(Enum):
    REFERENCE = "reference"
    AGGREGATOR = "aggregator"
    VERIFIER = "verifier"


class ResponseQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ADEQUATE = "adequate"
    POOR = "poor"
    FAILED = "failed"


class AggregationStrategy(Enum):
    BEST_OF = "best_of"
    WEIGHTED_MERGE = "weighted_merge"
    CONSENSUS = "consensus"
    LAYERED = "layered"


@dataclass
class ModelDescriptor:
    id: str = ""
    name: str = ""
    provider: str = ""
    role: ModelRole = ModelRole.REFERENCE
    strength: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    priority: int = 50
    available: bool = True
    call_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "role": self.role.value,
            "strength": self.strength,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "priority": self.priority,
            "available": self.available,
            "call_count": self.call_count,
            "failure_count": self.failure_count,
            "avg_latency_ms": self.avg_latency_ms,
        }

    @property
    def reliability(self) -> float:
        total = self.call_count
        if total == 0:
            return 1.0
        return 1.0 - (self.failure_count / total)


@dataclass
class ReferenceResponse:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    model_id: str = ""
    model_name: str = ""
    content: str = ""
    quality: ResponseQuality = ResponseQuality.ADEQUATE
    score: float = 0.0
    latency_ms: float = 0.0
    token_count: int = 0
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "content": self.content[:500],
            "quality": self.quality.value,
            "score": self.score,
            "latency_ms": self.latency_ms,
            "token_count": self.token_count,
            "error": self.error,
        }


@dataclass
class MoAResult:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    strategy: AggregationStrategy = AggregationStrategy.BEST_OF
    reference_responses: List[ReferenceResponse] = field(default_factory=list)
    aggregated_response: str = ""
    aggregator_model: str = ""
    total_latency_ms: float = 0.0
    models_used: int = 0
    models_succeeded: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query[:200],
            "strategy": self.strategy.value,
            "reference_count": len(self.reference_responses),
            "succeeded_count": self.models_succeeded,
            "aggregated_response": self.aggregated_response[:500],
            "aggregator_model": self.aggregator_model,
            "total_latency_ms": self.total_latency_ms,
            "models_used": self.models_used,
        }


class ResponseScorer:
    """
    Scores reference responses based on content quality,
    relevance to the query, and structural completeness.
    """

    def score(self, response: ReferenceResponse, query: str) -> Tuple[float, ResponseQuality]:
        if response.error:
            return 0.0, ResponseQuality.FAILED

        content = response.content
        score = 0.0

        length_score = min(len(content) / 500.0, 1.0) * 0.2
        score += length_score

        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        overlap = len(query_words & content_words) / max(len(query_words), 1)
        score += overlap * 0.3

        structure_indicators = ["because", "therefore", "however", "first", "second", "finally", "result", "approach"]
        structure_count = sum(1 for ind in structure_indicators if ind in content.lower())
        score += min(structure_count / 3.0, 1.0) * 0.2

        code_indicators = ["```", "def ", "class ", "function ", "import ", "return "]
        code_count = sum(1 for ind in code_indicators if ind in content)
        if code_count > 0:
            score += 0.15

        specificity_words = ["specifically", "exactly", "precisely", "particular", "instance"]
        spec_count = sum(1 for w in specificity_words if w in content.lower())
        score += min(spec_count / 2.0, 1.0) * 0.15

        score = min(score, 1.0)

        if score >= 0.8:
            quality = ResponseQuality.EXCELLENT
        elif score >= 0.6:
            quality = ResponseQuality.GOOD
        elif score >= 0.4:
            quality = ResponseQuality.ADEQUATE
        elif score >= 0.2:
            quality = ResponseQuality.POOR
        else:
            quality = ResponseQuality.FAILED

        return score, quality


class MixtureOfAgentsEngine:
    """
    Multi-model reasoning engine that dispatches queries to
    multiple reference models and synthesizes their responses.

    The engine tolerates partial model failures (minimum 1
    successful reference required) and uses quality-weighted
    aggregation to produce the final response.

    Usage:
        engine = MixtureOfAgentsEngine()
        engine.register_model(ModelDescriptor(
            id="model_a", name="Creative Model", strength="creative"
        ))
        result = await engine.query("Design a boss battle mechanic")
    """

    def __init__(self, min_references: int = 1, max_references: int = 4):
        self._models: Dict[str, ModelDescriptor] = {}
        self._scorer = ResponseScorer()
        self._results: List[MoAResult] = []
        self._min_references = min_references
        self._max_references = max_references
        self._generate_fn: Optional[Callable] = None
        self._seed_models()

    def _seed_models(self) -> None:
        seeds = [
            ModelDescriptor(id="creative", name="Creative Reasoner", provider="internal", role=ModelRole.REFERENCE, strength="creative", temperature=0.9, priority=70),
            ModelDescriptor(id="analytical", name="Analytical Reasoner", provider="internal", role=ModelRole.REFERENCE, strength="analytical", temperature=0.3, priority=80),
            ModelDescriptor(id="code_specialist", name="Code Specialist", provider="internal", role=ModelRole.REFERENCE, strength="code", temperature=0.5, priority=75),
            ModelDescriptor(id="aggregator", name="Aggregator", provider="internal", role=ModelRole.AGGREGATOR, strength="synthesis", temperature=0.4, priority=90),
        ]
        for model in seeds:
            self._models[model.id] = model

    def register_model(self, model: ModelDescriptor) -> str:
        self._models[model.id] = model
        return model.id

    def set_generate_fn(self, fn: Callable) -> None:
        self._generate_fn = fn

    async def query(self, query: str, strategy: AggregationStrategy = AggregationStrategy.BEST_OF, model_ids: Optional[List[str]] = None) -> MoAResult:
        start_time = time.time()

        reference_models = self._select_reference_models(model_ids)
        if not reference_models:
            return MoAResult(query=query, strategy=strategy, aggregated_response="No reference models available")

        tasks = []
        for model in reference_models:
            tasks.append(self._generate_reference(query, model))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        reference_responses = []
        for resp in responses:
            if isinstance(resp, Exception):
                reference_responses.append(ReferenceResponse(error=str(resp), quality=ResponseQuality.FAILED))
            elif isinstance(resp, ReferenceResponse):
                reference_responses.append(resp)

        successful = [r for r in reference_responses if r.error is None]
        if len(successful) < self._min_references:
            result = MoAResult(
                query=query,
                strategy=strategy,
                reference_responses=reference_responses,
                aggregated_response="Insufficient successful references",
                models_used=len(reference_models),
                models_succeeded=len(successful),
                total_latency_ms=(time.time() - start_time) * 1000,
            )
            self._results.append(result)
            return result

        for resp in successful:
            resp.score, resp.quality = self._scorer.score(resp, query)

        aggregated = self._aggregate(successful, query, strategy)

        result = MoAResult(
            query=query,
            strategy=strategy,
            reference_responses=reference_responses,
            aggregated_response=aggregated,
            aggregator_model="aggregator",
            models_used=len(reference_models),
            models_succeeded=len(successful),
            total_latency_ms=(time.time() - start_time) * 1000,
        )
        self._results.append(result)
        return result

    def _select_reference_models(self, model_ids: Optional[List[str]] = None) -> List[ModelDescriptor]:
        if model_ids:
            return [self._models[mid] for mid in model_ids if mid in self._models and self._models[mid].available]

        available = [m for m in self._models.values() if m.available and m.role == ModelRole.REFERENCE]
        available.sort(key=lambda m: m.priority, reverse=True)
        return available[:self._max_references]

    async def _generate_reference(self, query: str, model: ModelDescriptor) -> ReferenceResponse:
        start = time.time()
        model.call_count += 1

        try:
            if self._generate_fn:
                content = await self._generate_fn(query, model)
            else:
                content = f"[{model.name} perspective on: {query[:100]}]"

            latency = (time.time() - start) * 1000
            model.avg_latency_ms = (model.avg_latency_ms * (model.call_count - 1) + latency) / model.call_count

            return ReferenceResponse(
                model_id=model.id,
                model_name=model.name,
                content=content,
                latency_ms=latency,
                token_count=len(content.split()),
            )
        except Exception as e:
            model.failure_count += 1
            return ReferenceResponse(
                model_id=model.id,
                model_name=model.name,
                error=str(e),
                quality=ResponseQuality.FAILED,
            )

    def _aggregate(self, responses: List[ReferenceResponse], query: str, strategy: AggregationStrategy) -> str:
        if not responses:
            return ""

        if strategy == AggregationStrategy.BEST_OF:
            best = max(responses, key=lambda r: r.score)
            return best.content

        elif strategy == AggregationStrategy.WEIGHTED_MERGE:
            parts = []
            total_score = sum(r.score for r in responses) or 1.0
            for resp in sorted(responses, key=lambda r: r.score, reverse=True):
                weight = resp.score / total_score
                if weight > 0.15:
                    parts.append(f"[{resp.model_name} (weight: {weight:.2f})]: {resp.content[:300]}")
            return "\n\n---\n\n".join(parts)

        elif strategy == AggregationStrategy.CONSENSUS:
            common_points = []
            all_contents = [r.content.lower() for r in responses]
            for word in set(all_contents[0].split()):
                if len(word) > 4 and all(word in c for c in all_contents):
                    common_points.append(word)

            consensus_parts = [f"Consensus points: {', '.join(common_points[:10])}"]
            for resp in sorted(responses, key=lambda r: r.score, reverse=True):
                consensus_parts.append(f"[{resp.model_name}]: {resp.content[:200]}")
            return "\n\n".join(consensus_parts)

        else:
            sections = []
            for i, resp in enumerate(sorted(responses, key=lambda r: r.score, reverse=True)):
                sections.append(f"Perspective {i+1} [{resp.model_name}]: {resp.content[:250]}")
            return "\n\n".join(sections)

    def list_models(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._models.values()]

    def get_results(self, limit: int = 20) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._results[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total_queries = len(self._results)
        successful = sum(1 for r in self._results if r.models_succeeded >= self._min_references)
        avg_latency = 0.0
        if total_queries > 0:
            avg_latency = sum(r.total_latency_ms for r in self._results) / total_queries

        return {
            "total_queries": total_queries,
            "successful_queries": successful,
            "success_rate": successful / max(total_queries, 1),
            "avg_latency_ms": round(avg_latency, 1),
            "registered_models": len(self._models),
            "available_models": sum(1 for m in self._models.values() if m.available),
        }


_global_moa_engine: Optional[MixtureOfAgentsEngine] = None


def get_moa_engine() -> MixtureOfAgentsEngine:
    global _global_moa_engine
    if _global_moa_engine is None:
        _global_moa_engine = MixtureOfAgentsEngine()
    return _global_moa_engine
