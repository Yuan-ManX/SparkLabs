"""
SparkAI Agent - LLM Router

Intelligent routing of LLM requests based on task type, provider
capability, cost, and latency requirements. The router selects the
optimal LLM provider for each request, enabling multi-model strategies.

Routing strategy:
  1. Classify the task type from the prompt
  2. Match task type to provider capabilities
  3. Select the best available provider (cost/latency/quality)
  4. Fall back to next provider on failure
  5. Track routing decisions for optimization

Task types and their optimal providers:
  - Code generation: High-capability models (GPT-4, Claude)
  - Creative writing: Creative-tuned models
  - Analysis: Fast models with good reasoning
  - Quick decisions: Low-latency models
  - Embedding: Specialized embedding models
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from sparkai.agent.llm import LLMConfig, LLMProvider


class TaskType(Enum):
    CODE_GENERATION = "code_generation"
    CREATIVE_WRITING = "creative_writing"
    ANALYSIS = "analysis"
    QUICK_DECISION = "quick_decision"
    EMBEDDING = "embedding"
    CHAT = "chat"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    GAME_DESIGN = "game_design"
    NARRATIVE = "narrative"
    DEBUGGING = "debugging"
    REVIEW = "review"


class ProviderCapability(Enum):
    HIGH_REASONING = "high_reasoning"
    CREATIVE = "creative"
    FAST = "fast"
    CODE_SPECIALIST = "code_specialist"
    EMBEDDING = "embedding"
    MULTI_MODAL = "multi_modal"
    LONG_CONTEXT = "long_context"


@dataclass
class ProviderProfile:
    """Profile of an LLM provider's capabilities and characteristics."""
    name: str
    provider_type: str
    capabilities: List[ProviderCapability] = field(default_factory=list)
    cost_per_1k_tokens: float = 0.0
    avg_latency_ms: float = 0.0
    max_context_tokens: int = 4096
    quality_score: float = 0.5
    reliability: float = 0.99
    config: Optional[LLMConfig] = None
    _provider: Optional[LLMProvider] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "provider_type": self.provider_type,
            "capabilities": [c.value for c in self.capabilities],
            "cost_per_1k_tokens": self.cost_per_1k_tokens,
            "avg_latency_ms": self.avg_latency_ms,
            "max_context_tokens": self.max_context_tokens,
            "quality_score": self.quality_score,
            "reliability": self.reliability,
        }


@dataclass
class RoutingDecision:
    """Record of a routing decision for analytics."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType = TaskType.CHAT
    selected_provider: str = ""
    fallback_used: bool = False
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0
    success: bool = True
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "selected_provider": self.selected_provider,
            "fallback_used": self.fallback_used,
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
            "success": self.success,
            "timestamp": self.timestamp,
        }


# Task type to required capabilities mapping
_TASK_CAPABILITY_MAP: Dict[TaskType, List[ProviderCapability]] = {
    TaskType.CODE_GENERATION: [ProviderCapability.CODE_SPECIALIST, ProviderCapability.HIGH_REASONING],
    TaskType.CREATIVE_WRITING: [ProviderCapability.CREATIVE],
    TaskType.ANALYSIS: [ProviderCapability.HIGH_REASONING],
    TaskType.QUICK_DECISION: [ProviderCapability.FAST],
    TaskType.EMBEDDING: [ProviderCapability.EMBEDDING],
    TaskType.CHAT: [],
    TaskType.SUMMARIZATION: [ProviderCapability.LONG_CONTEXT],
    TaskType.TRANSLATION: [],
    TaskType.GAME_DESIGN: [ProviderCapability.CREATIVE, ProviderCapability.HIGH_REASONING],
    TaskType.NARRATIVE: [ProviderCapability.CREATIVE, ProviderCapability.LONG_CONTEXT],
    TaskType.DEBUGGING: [ProviderCapability.CODE_SPECIALIST, ProviderCapability.HIGH_REASONING],
    TaskType.REVIEW: [ProviderCapability.HIGH_REASONING],
}

# Keyword-based task classification
_TASK_KEYWORDS: Dict[TaskType, List[str]] = {
    TaskType.CODE_GENERATION: ["code", "implement", "function", "class", "module", "api", "script", "program"],
    TaskType.CREATIVE_WRITING: ["write", "story", "creative", "imagine", "invent", "compose"],
    TaskType.ANALYSIS: ["analyze", "evaluate", "assess", "compare", "investigate", "examine"],
    TaskType.QUICK_DECISION: ["choose", "pick", "select", "decide", "which", "yes or no"],
    TaskType.GAME_DESIGN: ["game", "mechanic", "level", "player", "gameplay", "balance", "design"],
    TaskType.NARRATIVE: ["narrative", "dialogue", "quest", "plot", "character", "story arc"],
    TaskType.DEBUGGING: ["debug", "fix", "error", "bug", "issue", "trace", "diagnose"],
    TaskType.REVIEW: ["review", "check", "validate", "verify", "inspect", "audit"],
    TaskType.SUMMARIZATION: ["summarize", "condense", "brief", "overview", "tldr"],
}


class LLMRouter:
    """
    Intelligent LLM request router for the SparkLabs AI-Native Game Engine.

    Routes LLM requests to the optimal provider based on task type,
    provider capabilities, cost, and latency. Supports fallback chains
    and tracks routing decisions for optimization.

    Usage:
        router = LLMRouter()
        router.register_provider("gpt4", profile)
        result = await router.route("Generate game code", TaskType.CODE_GENERATION)
    """

    def __init__(self):
        self._providers: Dict[str, ProviderProfile] = {}
        self._default_provider: Optional[str] = None
        self._routing_history: List[RoutingDecision] = []
        self._max_history: int = 1000
        self._provider_stats: Dict[str, Dict[str, Any]] = {}

    def register_provider(
        self,
        name: str,
        config: LLMConfig,
        capabilities: Optional[List[ProviderCapability]] = None,
        cost_per_1k: float = 0.0,
        avg_latency_ms: float = 0.0,
        quality_score: float = 0.5,
    ) -> ProviderProfile:
        """Register an LLM provider with its capabilities."""
        profile = ProviderProfile(
            name=name,
            provider_type=config.provider,
            capabilities=capabilities or [],
            cost_per_1k_tokens=cost_per_1k,
            avg_latency_ms=avg_latency_ms,
            max_context_tokens=config.max_tokens,
            quality_score=quality_score,
            config=config,
            _provider=LLMProvider(config),
        )
        self._providers[name] = profile
        self._provider_stats[name] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_latency_ms": 0.0,
        }
        if self._default_provider is None:
            self._default_provider = name
        return profile

    def set_default_provider(self, name: str) -> bool:
        if name in self._providers:
            self._default_provider = name
            return True
        return False

    def classify_task(self, prompt: str) -> TaskType:
        """Classify a prompt into a task type based on keywords."""
        prompt_lower = prompt.lower()
        best_type = TaskType.CHAT
        best_score = 0

        for task_type, keywords in _TASK_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > best_score:
                best_score = score
                best_type = task_type

        return best_type

    def select_provider(
        self,
        task_type: TaskType,
        prefer_provider: Optional[str] = None,
    ) -> Optional[str]:
        """Select the best provider for a given task type."""
        if prefer_provider and prefer_provider in self._providers:
            return prefer_provider

        required_caps = _TASK_CAPABILITY_MAP.get(task_type, [])
        if not required_caps:
            return self._default_provider

        candidates = []
        for name, profile in self._providers.items():
            cap_match = sum(
                1 for cap in required_caps if cap in profile.capabilities
            )
            if cap_match > 0:
                score = (
                    cap_match * 10
                    + profile.quality_score * 5
                    + profile.reliability * 3
                    - profile.cost_per_1k_tokens
                    - profile.avg_latency_ms / 1000
                )
                candidates.append((name, score))

        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return self._default_provider

    async def route(
        self,
        prompt: str,
        task_type: Optional[TaskType] = None,
        prefer_provider: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Route a prompt to the optimal LLM provider and generate a response.
        Falls back to the next best provider on failure.
        """
        if task_type is None:
            task_type = self.classify_task(prompt)

        selected = self.select_provider(task_type, prefer_provider)

        if not selected or selected not in self._providers:
            return "[LLMRouter] No providers available"

        decision = RoutingDecision(task_type=task_type, selected_provider=selected)
        start_time = time.time()

        tried_providers = {selected}
        provider_order = self._get_fallback_order(selected, task_type)

        for provider_name in provider_order:
            profile = self._providers.get(provider_name)
            if not profile or not profile._provider:
                continue

            try:
                response = await profile._provider.generate(prompt, **kwargs)
                decision.latency_ms = (time.time() - start_time) * 1000
                decision.success = True
                decision.fallback_used = (provider_name != selected)
                decision.selected_provider = provider_name
                self._record_decision(decision)
                self._update_provider_stats(provider_name, decision)
                return response

            except Exception:
                tried_providers.add(provider_name)
                base_delay = 2.0
                jitter = random.uniform(0, base_delay * 0.5)
                await asyncio.sleep(base_delay + jitter)
                continue

        decision.latency_ms = (time.time() - start_time) * 1000
        decision.success = False
        self._record_decision(decision)
        return "[LLMRouter] All providers failed"

    def _get_fallback_order(self, primary: str, task_type: TaskType) -> List[str]:
        """Get ordered list of providers to try, starting with primary."""
        order = [primary]
        required_caps = _TASK_CAPABILITY_MAP.get(task_type, [])

        scored = []
        for name, profile in self._providers.items():
            if name == primary:
                continue
            cap_match = sum(1 for cap in required_caps if cap in profile.capabilities)
            score = cap_match * 10 + profile.reliability * 5
            scored.append((name, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        order.extend(name for name, _ in scored)
        return order

    def _record_decision(self, decision: RoutingDecision) -> None:
        self._routing_history.append(decision)
        if len(self._routing_history) > self._max_history:
            self._routing_history = self._routing_history[-self._max_history:]

    def _update_provider_stats(self, provider_name: str, decision: RoutingDecision) -> None:
        if provider_name not in self._provider_stats:
            self._provider_stats[provider_name] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_latency_ms": 0.0,
            }
        stats = self._provider_stats[provider_name]
        stats["total_requests"] += 1
        if decision.success:
            stats["successful_requests"] += 1
        else:
            stats["failed_requests"] += 1
        n = stats["total_requests"]
        stats["avg_latency_ms"] = (
            (stats["avg_latency_ms"] * (n - 1) + decision.latency_ms) / n
        )

    def get_routing_stats(self) -> Dict[str, Any]:
        return {
            "total_routed": len(self._routing_history),
            "successful": sum(1 for d in self._routing_history if d.success),
            "fallbacks": sum(1 for d in self._routing_history if d.fallback_used),
            "providers": self._provider_stats,
            "by_task_type": self._get_task_type_stats(),
        }

    def _get_task_type_stats(self) -> Dict[str, int]:
        stats: Dict[str, int] = {}
        for decision in self._routing_history:
            key = decision.task_type.value
            stats[key] = stats.get(key, 0) + 1
        return stats

    def list_providers(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._providers.values()]

    def get_provider(self, name: str) -> Optional[Dict[str, Any]]:
        profile = self._providers.get(name)
        return profile.to_dict() if profile else None
