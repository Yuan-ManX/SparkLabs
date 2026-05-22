"""
SparkLabs Agent - Provider Switch

Dynamic LLM provider and model management system with automatic
failover, cost optimization, usage tracking, and intelligent model
selection. Routes agent requests to the most suitable model based
on task requirements, budget constraints, and real-time performance.

Architecture:
  ProviderSwitch
    |-- ProviderConfig (connection details and authentication)
    |-- ModelProfile (capability matrix, pricing, performance tiers)
    |-- SwitchRule (condition-action rules for model routing)
    |-- FailoverEvent (historical record of failover actions)
    |-- UsageStats (accumulated token and cost tracking per model)

Provider Types:
  - OPENAI: OpenAI API models (GPT-4o, GPT-4o-mini, etc.)
  - ANTHROPIC: Anthropic Claude models (Sonnet, Opus, etc.)
  - LOCAL: On-premise models via Ollama, vLLM, etc.
  - CLOUD: Cloud-hosted inference endpoints (AWS Bedrock, GCP Vertex)
  - CUSTOM: Any HTTP-compatible LLM endpoint

Failover Strategies:
  - ROUND_ROBIN: sequential cycling through available models
  - LOWEST_COST: route to the cheapest capable model
  - HIGHEST_PERFORMANCE: route to the highest-scoring capable model
  - CUSTOM: user-defined routing function

Usage:
    ps = get_provider_switch()
    ps.register_provider("openai", ProviderType.OPENAI, "https://api.openai.com", "OPENAI_KEY")
    ps.configure_model("gpt-4o", "openai", capabilities=[ModelCapability.CODE, ModelCapability.VISION])
    model = ps.auto_select_model("Generate game code", requirements={"code": True})
"""
from __future__ import annotations

import random
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ProviderType(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    CLOUD = "cloud"
    CUSTOM = "custom"


class ModelCapability(Enum):
    TEXT = "text"
    CODE = "code"
    VISION = "vision"
    TOOL_USE = "tool_use"
    STREAMING = "streaming"


class FailoverStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LOWEST_COST = "lowest_cost"
    HIGHEST_PERFORMANCE = "highest_performance"
    CUSTOM = "custom"


class ConnectionStatus(Enum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    RATE_LIMITED = "rate_limited"


class TaskCategory(Enum):
    CODE_GENERATION = "code_generation"
    GAME_DESIGN = "game_design"
    ASSET_CREATION = "asset_creation"
    NARRATIVE = "narrative"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    CONVERSATION = "conversation"


@dataclass
class ProviderConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    provider_type: ProviderType = ProviderType.CUSTOM
    base_url: str = ""
    api_key_ref: str = ""
    timeout_seconds: float = 60.0
    max_retries: int = 3
    rate_limit_rpm: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    status: ConnectionStatus = ConnectionStatus.UNKNOWN
    registered_at: float = field(default_factory=time.time)
    last_health_check: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider_type": self.provider_type.value,
            "base_url": self.base_url,
            "api_key_ref": self.api_key_ref,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "rate_limit_rpm": self.rate_limit_rpm,
            "headers": {k: "***" for k in self.headers},
            "status": self.status.value,
            "registered_at": self.registered_at,
            "last_health_check": self.last_health_check,
            "metadata": self.metadata,
        }


@dataclass
class ModelProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    model_id: str = ""
    provider_id: str = ""
    display_name: str = ""
    capabilities: List[ModelCapability] = field(default_factory=list)
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    performance_score: float = 0.0
    context_window: int = 4096
    max_output_tokens: int = 4096
    latency_class: str = "standard"
    is_default: bool = False
    is_enabled: bool = True
    task_affinity: List[TaskCategory] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "capabilities": [c.value for c in self.capabilities],
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "performance_score": self.performance_score,
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "latency_class": self.latency_class,
            "is_default": self.is_default,
            "is_enabled": self.is_enabled,
            "task_affinity": [t.value for t in self.task_affinity],
            "created_at": self.created_at,
        }

    def has_capability(self, capability: ModelCapability) -> bool:
        return capability in self.capabilities

    def cost_for_tokens(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1000.0) * self.cost_per_1k_input
        output_cost = (output_tokens / 1000.0) * self.cost_per_1k_output
        return input_cost + output_cost


@dataclass
class SwitchRule:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    model_id: str = ""
    condition: str = ""
    strategy: FailoverStrategy = FailoverStrategy.ROUND_ROBIN
    target_models: List[str] = field(default_factory=list)
    max_consecutive_failures: int = 3
    cooldown_seconds: float = 60.0
    is_active: bool = True
    priority: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "model_id": self.model_id,
            "condition": self.condition,
            "strategy": self.strategy.value,
            "target_models": self.target_models,
            "max_consecutive_failures": self.max_consecutive_failures,
            "cooldown_seconds": self.cooldown_seconds,
            "is_active": self.is_active,
            "priority": self.priority,
            "created_at": self.created_at,
        }


@dataclass
class FailoverEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    failed_model_id: str = ""
    switched_to_model_id: str = ""
    strategy_used: FailoverStrategy = FailoverStrategy.ROUND_ROBIN
    reason: str = ""
    request_id: str = ""
    occurred_at: float = field(default_factory=time.time)
    recovery_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "failed_model_id": self.failed_model_id,
            "switched_to_model_id": self.switched_to_model_id,
            "strategy_used": self.strategy_used.value,
            "reason": self.reason,
            "request_id": self.request_id,
            "occurred_at": self.occurred_at,
            "recovery_time_ms": self.recovery_time_ms,
            "metadata": self.metadata,
        }


@dataclass
class UsageStats:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    model_id: str = ""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    total_duration_ms: float = 0.0
    first_request_at: float = 0.0
    last_request_at: float = 0.0
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": round(self.total_cost, 4),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "avg_duration_ms": round(
                self.total_duration_ms / max(self.total_requests, 1), 2
            ),
            "success_rate": round(
                self.successful_requests / max(self.total_requests, 1), 3
            ),
            "first_request_at": self.first_request_at,
            "last_request_at": self.last_request_at,
        }

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests


TASK_MODEL_AFFINITY: Dict[TaskCategory, List[ModelCapability]] = {
    TaskCategory.CODE_GENERATION: [ModelCapability.CODE, ModelCapability.TOOL_USE],
    TaskCategory.GAME_DESIGN: [ModelCapability.TEXT],
    TaskCategory.ASSET_CREATION: [ModelCapability.VISION, ModelCapability.TEXT],
    TaskCategory.NARRATIVE: [ModelCapability.TEXT, ModelCapability.STREAMING],
    TaskCategory.ANALYSIS: [ModelCapability.TEXT, ModelCapability.CODE],
    TaskCategory.PLANNING: [ModelCapability.TEXT, ModelCapability.TOOL_USE],
    TaskCategory.CONVERSATION: [ModelCapability.TEXT, ModelCapability.STREAMING],
}


class ProviderSwitch:
    """
    Dynamic LLM provider and model management for SparkLabs agents.

    Routes agent requests across multiple LLM providers with automatic
    failover, cost optimization, and intelligent model selection. Tracks
    per-model usage statistics for cost analysis and performance tuning.

    Usage:
        ps = ProviderSwitch()
        ps.register_provider("openai", ProviderType.OPENAI, "https://api.openai.com", "KEY_REF")
        ps.configure_model("gpt-4o", "openai", [ModelCapability.CODE, ModelCapability.VISION],
                           cost_per_1k_input=0.005, cost_per_1k_output=0.015)
        model_id = ps.auto_select_model("Generate code", requirements={"code": True})
    """

    _instance: Optional["ProviderSwitch"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._providers: Dict[str, ProviderConfig] = {}
        self._models: Dict[str, ModelProfile] = {}
        self._switch_rules: Dict[str, SwitchRule] = {}
        self._failover_events: List[FailoverEvent] = []
        self._usage: Dict[str, UsageStats] = {}
        self._failover_counts: Dict[str, int] = defaultdict(int)
        self._custom_routing_fn: Optional[Callable[[List[ModelProfile], Dict[str, Any]], Optional[str]]] = None
        self._provider_count: int = 0
        self._model_count: int = 0
        self._rule_count: int = 0
        self._total_failovers: int = 0

    @classmethod
    def get_instance(cls) -> "ProviderSwitch":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register_provider(
        self,
        name: str,
        provider_type: ProviderType,
        base_url: str,
        api_key_ref: str,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
        rate_limit_rpm: int = 0,
        headers: Optional[Dict[str, str]] = None,
    ) -> ProviderConfig:
        config = ProviderConfig(
            name=name,
            provider_type=provider_type,
            base_url=base_url,
            api_key_ref=api_key_ref,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            rate_limit_rpm=rate_limit_rpm,
            headers=headers or {},
        )
        self._providers[config.id] = config
        self._provider_count += 1
        return config

    def configure_model(
        self,
        model_id: str,
        provider_id: str,
        capabilities: Optional[List[ModelCapability]] = None,
        cost_per_1k_input: float = 0.0,
        cost_per_1k_output: float = 0.0,
        performance_score: float = 0.0,
        context_window: int = 4096,
        max_output_tokens: int = 4096,
        latency_class: str = "standard",
        is_default: bool = False,
        task_affinity: Optional[List[TaskCategory]] = None,
    ) -> ModelProfile:
        profile = ModelProfile(
            model_id=model_id,
            provider_id=provider_id,
            display_name=model_id,
            capabilities=capabilities or [],
            cost_per_1k_input=cost_per_1k_input,
            cost_per_1k_output=cost_per_1k_output,
            performance_score=performance_score,
            context_window=context_window,
            max_output_tokens=max_output_tokens,
            latency_class=latency_class,
            is_default=is_default,
            task_affinity=task_affinity or [],
        )
        self._models[profile.id] = profile
        self._model_count += 1
        return profile

    def set_switch_rule(
        self,
        rule_id: str,
        model_id: str,
        condition: str,
        strategy: FailoverStrategy = FailoverStrategy.ROUND_ROBIN,
        target_models: Optional[List[str]] = None,
        max_consecutive_failures: int = 3,
        cooldown_seconds: float = 60.0,
    ) -> Optional[SwitchRule]:
        potential = self._switch_rules.get(rule_id)
        if potential is not None:
            potential.model_id = model_id
            potential.condition = condition
            potential.strategy = strategy
            potential.target_models = target_models or []
            potential.max_consecutive_failures = max_consecutive_failures
            potential.cooldown_seconds = cooldown_seconds
            return potential

        model = self._find_model_by_id(model_id)
        if model is None:
            return None

        rule = SwitchRule(
            id=rule_id or uuid.uuid4().hex,
            name=f"Rule for {model_id}",
            model_id=model.id,
            condition=condition,
            strategy=strategy,
            target_models=target_models or [],
            max_consecutive_failures=max_consecutive_failures,
            cooldown_seconds=cooldown_seconds,
        )
        self._switch_rules[rule.id] = rule
        self._rule_count += 1
        return rule

    def auto_select_model(
        self,
        task_description: str,
        requirements: Optional[Dict[str, Any]] = None,
        budget: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        requirements = requirements or {}
        candidates = list(self._models.values())

        if not candidates:
            return None

        task_category = self._classify_task(task_description)

        scored: List[Tuple[ModelProfile, float]] = []
        for profile in candidates:
            if not profile.is_enabled:
                continue

            provider = self._providers.get(profile.provider_id)
            if provider and provider.status == ConnectionStatus.OFFLINE:
                continue

            score = 0.0

            for task_cap in TASK_MODEL_AFFINITY.get(task_category, []):
                if task_cap in profile.capabilities:
                    score += 2.0

            required_caps = requirements.get("capabilities", [])
            for cap_name in required_caps:
                try:
                    cap = ModelCapability(cap_name)
                    if cap in profile.capabilities:
                        score += 3.0
                except ValueError:
                    pass

            score += profile.performance_score * 2.0

            if profile.task_affinity and task_category in profile.task_affinity:
                score += 5.0

            if requirements.get("code"):
                if ModelCapability.CODE in profile.capabilities:
                    score += 4.0
            if requirements.get("vision"):
                if ModelCapability.VISION in profile.capabilities:
                    score += 4.0

            if budget is not None:
                effective_cost = profile.cost_per_1k_input + profile.cost_per_1k_output
                if effective_cost > 0:
                    cost_score = max(0.0, 1.0 - effective_cost / budget)
                    score += cost_score * 3.0

            usage = self._usage.get(profile.id)
            if usage and usage.success_rate < 0.8:
                score -= 2.0

            scored.append((profile, score))

        if not scored:
            return None

        scored.sort(key=lambda x: x[1], reverse=True)
        best = scored[0][0]

        return {
            "model_profile_id": best.id,
            "model_id": best.model_id,
            "provider_id": best.provider_id,
            "display_name": best.display_name,
            "score": round(scored[0][1], 2),
            "alternatives": [
                {"model_profile_id": p.id, "model_id": p.model_id, "score": round(s, 2)}
                for p, s in scored[1:4]
            ],
        }

    def handle_failover(
        self,
        failed_model_id: str,
        request_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        failed_profile = self._find_model_by_id(failed_model_id)
        if failed_profile is None:
            return None

        self._failover_counts[failed_model_id] += 1

        rules = [
            r for r in self._switch_rules.values()
            if r.model_id == failed_profile.id and r.is_active
        ]
        rules.sort(key=lambda r: r.priority, reverse=True)

        rule = rules[0] if rules else None
        strategy = rule.strategy if rule else FailoverStrategy.ROUND_ROBIN
        target_model_ids = rule.target_models if rule else []

        candidates = self._resolve_failover_candidates(target_model_ids, failed_profile)
        if not candidates:
            return None

        fallback = self._apply_failover_strategy(candidates, strategy)
        if fallback is None:
            return None

        event = FailoverEvent(
            failed_model_id=failed_profile.id,
            switched_to_model_id=fallback.id,
            strategy_used=strategy,
            reason=f"Failover from {failed_profile.model_id} after {self._failover_counts[failed_model_id]} failures",
            request_id=request_id,
        )
        self._failover_events.append(event)
        self._total_failovers += 1

        return {
            "failover_event_id": event.id,
            "switched_to": fallback.model_id,
            "model_profile_id": fallback.id,
            "provider_id": fallback.provider_id,
            "strategy": strategy.value,
            "occurred_at": event.occurred_at,
        }

    def record_usage(
        self,
        model_id: str,
        tokens_in: int,
        tokens_out: int,
        duration: float,
        success: bool = True,
    ) -> Optional[UsageStats]:
        profile = self._find_model_by_id(model_id)
        if profile is None:
            return None

        usage = self._usage.get(profile.id)
        if usage is None:
            usage = UsageStats(model_id=profile.id)
            usage.first_request_at = time.time()
            self._usage[profile.id] = usage

        usage.total_requests += 1
        if success:
            usage.successful_requests += 1
        else:
            usage.failed_requests += 1

        usage.total_input_tokens += tokens_in
        usage.total_output_tokens += tokens_out
        usage.total_cost += profile.cost_for_tokens(tokens_in, tokens_out)
        usage.total_duration_ms += duration
        usage.last_request_at = time.time()
        usage.updated_at = time.time()

        return usage

    def get_model_stats(self, model_id: str) -> Optional[Dict[str, Any]]:
        profile = self._find_model_by_id(model_id)
        if profile is None:
            return None
        usage = self._usage.get(profile.id)
        if usage is None:
            return {"model_id": profile.model_id, "requests": 0, "message": "No usage data"}
        return usage.to_dict()

    def list_providers(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._providers.values()]

    def list_models(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._models.values()]

    def test_connectivity(self, provider_id: str) -> Dict[str, Any]:
        provider = self._providers.get(provider_id)
        if provider is None:
            return {"provider_id": provider_id, "status": "unknown", "error": "Provider not found"}

        provider.last_health_check = time.time()
        connected = bool(provider.base_url)
        if connected:
            provider.status = ConnectionStatus.ONLINE
        else:
            provider.status = ConnectionStatus.OFFLINE

        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "status": provider.status.value,
            "base_url": provider.base_url,
            "checked_at": provider.last_health_check,
        }

    def get_optimal_model(self, task_category: str) -> Optional[Dict[str, Any]]:
        try:
            category = TaskCategory(task_category)
        except ValueError:
            return None

        result = self.auto_select_model(
            task_description=task_category,
            requirements={},
        )
        return result

    def set_provider_status(self, provider_id: str, status: ConnectionStatus) -> bool:
        provider = self._providers.get(provider_id)
        if provider is None:
            return False
        provider.status = status
        return True

    def set_custom_routing(self, fn: Callable[[List[ModelProfile], Dict[str, Any]], Optional[str]]) -> None:
        self._custom_routing_fn = fn

    def get_failover_history(self, model_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        events = self._failover_events
        if model_id:
            profile = self._find_model_by_id(model_id)
            if profile:
                events = [e for e in events if e.failed_model_id == profile.id]
            else:
                events = []
        return [e.to_dict() for e in events[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total_cost_all = sum(u.total_cost for u in self._usage.values())
        total_requests_all = sum(u.total_requests for u in self._usage.values())
        total_tokens = sum(u.total_input_tokens + u.total_output_tokens for u in self._usage.values())

        model_breakdown = {}
        for profile in self._models.values():
            usage = self._usage.get(profile.id)
            if usage and usage.total_requests > 0:
                model_breakdown[profile.model_id] = {
                    "requests": usage.total_requests,
                    "success_rate": round(usage.success_rate, 3),
                    "total_tokens": usage.total_input_tokens + usage.total_output_tokens,
                    "total_cost": round(usage.total_cost, 4),
                }

        return {
            "total_providers": self._provider_count,
            "total_models": self._model_count,
            "total_rules": self._rule_count,
            "total_failovers": self._total_failovers,
            "total_requests": total_requests_all,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost_all, 4),
            "models_with_usage": len(self._usage),
            "model_breakdown": model_breakdown,
        }

    def clear(self) -> None:
        self._providers.clear()
        self._models.clear()
        self._switch_rules.clear()
        self._failover_events.clear()
        self._usage.clear()
        self._failover_counts.clear()
        self._custom_routing_fn = None
        self._provider_count = 0
        self._model_count = 0
        self._rule_count = 0
        self._total_failovers = 0

    def _find_model_by_id(self, model_id: str) -> Optional[ModelProfile]:
        for profile in self._models.values():
            if profile.model_id == model_id or profile.id == model_id:
                return profile
        return None

    @staticmethod
    def _classify_task(description: str) -> TaskCategory:
        desc = description.lower()
        if any(kw in desc for kw in ["code", "implement", "function", "class", "script"]):
            return TaskCategory.CODE_GENERATION
        if any(kw in desc for kw in ["design", "mechanic", "gameplay", "level"]):
            return TaskCategory.GAME_DESIGN
        if any(kw in desc for kw in ["asset", "sprite", "texture", "model", "sound"]):
            return TaskCategory.ASSET_CREATION
        if any(kw in desc for kw in ["story", "narrative", "dialogue", "character"]):
            return TaskCategory.NARRATIVE
        if any(kw in desc for kw in ["analyze", "review", "evaluate", "assess"]):
            return TaskCategory.ANALYSIS
        if any(kw in desc for kw in ["plan", "roadmap", "milestone", "schedule"]):
            return TaskCategory.PLANNING
        return TaskCategory.CONVERSATION

    def _resolve_failover_candidates(
        self,
        target_model_ids: List[str],
        failed_profile: ModelProfile,
    ) -> List[ModelProfile]:
        if target_model_ids:
            candidates: List[ModelProfile] = []
            for mid in target_model_ids:
                profile = self._find_model_by_id(mid)
                if profile and profile.id != failed_profile.id and profile.is_enabled:
                    provider = self._providers.get(profile.provider_id)
                    if provider and provider.status != ConnectionStatus.OFFLINE:
                        candidates.append(profile)
            if candidates:
                return candidates

        fallback_profiles: List[ModelProfile] = []
        for profile in self._models.values():
            if profile.id == failed_profile.id:
                continue
            if not profile.is_enabled:
                continue
            provider = self._providers.get(profile.provider_id)
            if provider and provider.status == ConnectionStatus.OFFLINE:
                continue
            overlap = set(failed_profile.capabilities) & set(profile.capabilities)
            if overlap:
                fallback_profiles.append(profile)

        return fallback_profiles

    def _apply_failover_strategy(
        self,
        candidates: List[ModelProfile],
        strategy: FailoverStrategy,
    ) -> Optional[ModelProfile]:
        if not candidates:
            return None

        if strategy == FailoverStrategy.ROUND_ROBIN:
            idx = random.randint(0, len(candidates) - 1)
            return candidates[idx]

        if strategy == FailoverStrategy.LOWEST_COST:
            return min(
                candidates,
                key=lambda p: p.cost_per_1k_input + p.cost_per_1k_output,
            )

        if strategy == FailoverStrategy.HIGHEST_PERFORMANCE:
            return max(candidates, key=lambda p: p.performance_score)

        if strategy == FailoverStrategy.CUSTOM and self._custom_routing_fn:
            result = self._custom_routing_fn(candidates, {})
            if result:
                for candidate in candidates:
                    if candidate.id == result or candidate.model_id == result:
                        return candidate

        return candidates[0]


def get_provider_switch() -> ProviderSwitch:
    return ProviderSwitch.get_instance()