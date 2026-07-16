"""
SparkLabs Agent - LLM Router & Model Integration System

Comprehensive LLM router and model integration system for the SparkLabs
AI-native game engine. Provides a unified interface for routing requests
across a diverse catalog of model providers spanning text LLMs, multimodal
models, image/video/audio/3D generation, embeddings, and open-source models
served via Ollama.

The catalog covers major hosted LLMs (OpenAI, Anthropic, Google, Meta,
Mistral, Cohere, DeepSeek, Qwen, xAI, Perplexity, AI21), fast-inference
platforms (Groq, Cerebras, Fireworks, Together, NVIDIA NIM, DeepInfra),
cloud gateways (Amazon Bedrock, Azure OpenAI, OpenRouter), regional model
providers (Zhipu, Moonshot, MiniMax, Doubao, ERNIE, StepFun, Lambda), and
specialized speech and media providers (Replicate, AssemblyAI, Deepgram,
PlayHT, Cartesia) for speech-to-text and text-to-speech pipelines.

Architecture:
  LLMRouter (singleton)
    |-- ProviderRegistry   (register/unregister model providers)
    |-- ModelCatalog        (searchable metadata for all models)
    |-- TaskRouter          (map game-dev tasks to optimal models)
    |-- LoadBalancer        (distribute requests by health/latency/cost)
    |-- FallbackChain       (automatic failover to backup models)
    |-- CostTracker         (token usage and estimated cost per provider)
    |-- RateLimiter         (per-provider token-bucket rate limiting)
    |-- ResponseCache       (cache identical prompts to reduce API calls)
    |-- StreamingAdapter    (stream responses for text generation)
    |-- HealthMonitor       (periodic health checks per provider endpoint)
    |-- APIKeyVault          (secure storage for API keys, never logged)
    |-- SimulationMode      (fake responses when no API keys configured)

Routing strategy:
  1. Classify the task type from the request
  2. Match task type to provider capabilities
  3. Select best provider per active routing strategy
  4. Apply rate limiting and check response cache
  5. Dispatch to provider endpoint (or simulate)
  6. On failure, walk the fallback chain
  7. Track usage, cost, latency and health for future routing

Task-to-model mappings cover the full game-development pipeline:
  - World building   -> text LLM with long context
  - Character design -> multimodal vision + text LLM
  - Dialogue         -> fast text LLM with personality
  - Code generation  -> code-specialized LLM
  - Asset generation -> image / video / 3D models
  - Music composition-> audio generation model
  - Voice acting     -> TTS model
  - Bug analysis     -> reasoning LLM
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import threading
import time
import uuid
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Tuple


# ============================================================================
# Logging
# ============================================================================

logger = logging.getLogger("sparkai.agent.agent_llm_router")


# ============================================================================
# Enumerations
# ============================================================================


class ModelType(Enum):
    """Category of model based on the modality it processes or produces."""
    TEXT = "text"
    VISION = "vision"
    IMAGE_GEN = "image_gen"
    VIDEO_GEN = "video_gen"
    AUDIO_GEN = "audio_gen"
    TTS = "tts"
    STT = "stt"
    EMBEDDING = "embedding"
    CODE = "code"
    REASONING = "reasoning"
    MULTIMODAL = "multimodal"
    GEN_3D = "3d_gen"
    ANIMATION = "animation"


class ProviderStatus(Enum):
    """Operational status of a model provider endpoint."""
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    RATE_LIMITED = "rate_limited"


class TaskType(Enum):
    """Game-development task types used by the task router."""
    WORLD_BUILDING = "world_building"
    CHARACTER_DESIGN = "character_design"
    DIALOGUE = "dialogue"
    CODE_GEN = "code_gen"
    ASSET_IMAGE = "asset_image"
    ASSET_VIDEO = "asset_video"
    ASSET_3D = "asset_3d"
    ASSET_AUDIO = "asset_audio"
    MUSIC_GEN = "music_gen"
    VOICE_ACTING = "voice_acting"
    BUG_ANALYSIS = "bug_analysis"
    BALANCE_TEST = "balance_test"
    NARRATIVE = "narrative"
    TRANSLATION = "translation"
    EMBEDDING = "embedding"
    SUMMARIZATION = "summarization"


class RoutingStrategy(Enum):
    """Strategy used by the router to select among candidate providers."""
    COST_OPTIMAL = "cost_optimal"
    LATENCY_OPTIMAL = "latency_optimal"
    QUALITY_OPTIMAL = "quality_optimal"
    CAPABILITY_MATCH = "capability_match"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class ModelCapability:
    """Declares what a model can do and its quality/cost characteristics."""
    model_id: str
    model_types: List[ModelType] = field(default_factory=list)
    max_context_tokens: int = 0
    max_output_tokens: int = 0
    supports_streaming: bool = False
    supports_function_calling: bool = False
    supports_vision: bool = False
    supports_audio_input: bool = False
    supports_video_input: bool = False
    quality_score: float = 0.5
    latency_tier: str = "medium"
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    cost_per_image: float = 0.0
    cost_per_second_video: float = 0.0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_types": [mt.value for mt in self.model_types],
            "max_context_tokens": self.max_context_tokens,
            "max_output_tokens": self.max_output_tokens,
            "supports_streaming": self.supports_streaming,
            "supports_function_calling": self.supports_function_calling,
            "supports_vision": self.supports_vision,
            "supports_audio_input": self.supports_audio_input,
            "supports_video_input": self.supports_video_input,
            "quality_score": self.quality_score,
            "latency_tier": self.latency_tier,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "cost_per_image": self.cost_per_image,
            "cost_per_second_video": self.cost_per_second_video,
            "tags": list(self.tags),
        }


@dataclass
class ModelEndpoint:
    """A single endpoint that serves one or more models."""
    endpoint_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    url: str = ""
    region: str = "us"
    api_version: str = "v1"
    is_primary: bool = True
    weight: int = 1
    timeout_seconds: float = 60.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint_id": self.endpoint_id,
            "url": self.url,
            "region": self.region,
            "api_version": self.api_version,
            "is_primary": self.is_primary,
            "weight": self.weight,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class ProviderHealth:
    """Live health snapshot for a provider."""
    status: ProviderStatus = ProviderStatus.ACTIVE
    last_check_ts: float = 0.0
    last_success_ts: float = 0.0
    last_failure_ts: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    avg_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    error_rate: float = 0.0
    last_error: str = ""
    uptime_pct: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "last_check_ts": self.last_check_ts,
            "last_success_ts": self.last_success_ts,
            "last_failure_ts": self.last_failure_ts,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "error_rate": round(self.error_rate, 4),
            "last_error": self.last_error,
            "uptime_pct": round(self.uptime_pct, 2),
        }


@dataclass
class ModelProvider:
    """A registered model provider with its models and endpoints."""
    provider_id: str
    name: str
    vendor: str
    capabilities: List[ModelCapability] = field(default_factory=list)
    endpoints: List[ModelEndpoint] = field(default_factory=list)
    health: ProviderHealth = field(default_factory=ProviderHealth)
    api_key_id: Optional[str] = None
    enabled: bool = True
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 100_000
    registered_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "vendor": self.vendor,
            "model_count": len(self.capabilities),
            "models": [c.to_dict() for c in self.capabilities],
            "endpoints": [e.to_dict() for e in self.endpoints],
            "health": self.health.to_dict(),
            "has_api_key": self.api_key_id is not None,
            "enabled": self.enabled,
            "rate_limit_rpm": self.rate_limit_rpm,
            "rate_limit_tpm": self.rate_limit_tpm,
            "registered_at": self.registered_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class GenerationConfig:
    """Parameters controlling model generation."""
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    top_k: int = 0
    stop: List[str] = field(default_factory=list)
    seed: Optional[int] = None
    response_format: str = "text"
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    stream: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "stop": list(self.stop),
            "seed": self.seed,
            "response_format": self.response_format,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
            "stream": self.stream,
            "extra": dict(self.extra),
        }


@dataclass
class ModelRequest:
    """A request to be routed and executed by the router."""
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_type: TaskType = TaskType.DIALOGUE
    prompt: str = ""
    system_prompt: str = ""
    messages: List[Dict[str, str]] = field(default_factory=list)
    model_id: Optional[str] = None
    provider_id: Optional[str] = None
    config: GenerationConfig = field(default_factory=GenerationConfig)
    images: List[str] = field(default_factory=list)
    audio: List[str] = field(default_factory=list)
    max_cost: Optional[float] = None
    max_latency_ms: Optional[float] = None
    prefer_streaming: bool = False
    use_cache: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "task_type": self.task_type.value,
            "prompt": self.prompt[:300],
            "system_prompt": self.system_prompt[:200],
            "message_count": len(self.messages),
            "model_id": self.model_id,
            "provider_id": self.provider_id,
            "config": self.config.to_dict(),
            "image_count": len(self.images),
            "audio_count": len(self.audio),
            "max_cost": self.max_cost,
            "max_latency_ms": self.max_latency_ms,
            "prefer_streaming": self.prefer_streaming,
            "use_cache": self.use_cache,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass
class ModelResponse:
    """A response returned from a provider (or simulation)."""
    response_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str = ""
    provider_id: str = ""
    model_id: str = ""
    content: str = ""
    content_urls: List[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost: float = 0.0
    finish_reason: str = "stop"
    cached: bool = False
    simulated: bool = False
    fallback_used: bool = False
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id": self.response_id,
            "request_id": self.request_id,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "content": self.content[:500],
            "content_urls": list(self.content_urls),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": round(self.latency_ms, 2),
            "cost": round(self.cost, 6),
            "finish_reason": self.finish_reason,
            "cached": self.cached,
            "simulated": self.simulated,
            "fallback_used": self.fallback_used,
            "error": self.error,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class RoutingRule:
    """A user-defined rule that influences provider selection."""
    name: str
    rule_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    task_type: Optional[TaskType] = None
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    required_model_type: Optional[ModelType] = None
    max_cost_per_1k: Optional[float] = None
    max_latency_ms: Optional[float] = None
    min_quality_score: float = 0.0
    priority: int = 0
    enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "task_type": self.task_type.value if self.task_type else None,
            "preferred_provider": self.preferred_provider,
            "preferred_model": self.preferred_model,
            "required_model_type": self.required_model_type.value
            if self.required_model_type
            else None,
            "max_cost_per_1k": self.max_cost_per_1k,
            "max_latency_ms": self.max_latency_ms,
            "min_quality_score": self.min_quality_score,
            "priority": self.priority,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }

    def matches(self, request: "ModelRequest") -> bool:
        """Return True when this rule applies to the given request."""
        if not self.enabled:
            return False
        if self.task_type is not None and self.task_type != request.task_type:
            return False
        if self.max_cost_per_1k is not None and (request.max_cost or 0) > self.max_cost_per_1k:
            return False
        if self.max_latency_ms is not None and (request.max_latency_ms or 0) > self.max_latency_ms:
            return False
        return True


@dataclass
class CostEstimate:
    """Estimated cost for executing a request on a given model."""
    model_id: str
    provider_id: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    currency: str = "USD"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "provider_id": self.provider_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_cost": round(self.input_cost, 6),
            "output_cost": round(self.output_cost, 6),
            "total_cost": round(self.total_cost, 6),
            "currency": self.currency,
        }


@dataclass
class UsageStats:
    """Aggregated usage statistics for a provider or model."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    fallback_count: int = 0
    simulated_count: int = 0
    by_task_type: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        success_rate = (
            self.successful_requests / self.total_requests
            if self.total_requests > 0
            else 0.0
        )
        cache_rate = (
            self.cache_hits / (self.cache_hits + self.cache_misses)
            if (self.cache_hits + self.cache_misses) > 0
            else 0.0
        )
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": round(self.total_cost, 6),
            "total_latency_ms": round(self.total_latency_ms, 2),
            "fallback_count": self.fallback_count,
            "simulated_count": self.simulated_count,
            "success_rate": round(success_rate, 4),
            "cache_hit_rate": round(cache_rate, 4),
            "by_task_type": dict(self.by_task_type),
        }


@dataclass
class APIKeyEntry:
    """Securely stored reference to a provider API key.

    The actual key value is kept in memory and never serialized in full by
    to_dict(); only a masked preview is exposed for diagnostics.
    """
    provider_id: str
    key_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    key_value: str = ""
    env_var: str = ""
    label: str = ""
    created_at: float = field(default_factory=time.time)
    last_used: float = 0.0
    use_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "provider_id": self.provider_id,
            "label": self.label,
            "env_var": self.env_var,
            "masked": self._masked(),
            "created_at": self.created_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
        }

    def _masked(self) -> str:
        if not self.key_value:
            return ""
        if len(self.key_value) <= 8:
            return "*" * len(self.key_value)
        return self.key_value[:3] + "..." + self.key_value[-3:]


# ============================================================================
# Internal Helper: Token Bucket Rate Limiter
# ============================================================================


class _TokenBucket:
    """Thread-safe token-bucket rate limiter used per provider."""

    def __init__(self, rate: float, capacity: float) -> None:
        self._rate = max(rate, 0.0)
        self._capacity = max(capacity, 1.0)
        self._tokens = self._capacity
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def update(self, rate: float, capacity: float) -> None:
        with self._lock:
            self._rate = max(rate, 0.0)
            self._capacity = max(capacity, 1.0)
            self._tokens = min(self._tokens, self._capacity)

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now

    def try_consume(self, tokens: float = 1.0) -> bool:
        """Return True if tokens are available and consumed, False otherwise."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: float = 1.0) -> float:
        """Return seconds to wait until the requested tokens are available."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                return 0.0
            deficit = tokens - self._tokens
            if self._rate <= 0:
                return float("inf")
            return deficit / self._rate

    def snapshot(self) -> Dict[str, float]:
        with self._lock:
            self._refill()
            return {
                "rate": self._rate,
                "capacity": self._capacity,
                "tokens_available": round(self._tokens, 2),
            }


# ============================================================================
# Internal Helper: Response Cache (LRU)
# ============================================================================


class _ResponseCache:
    """Least-recently-used cache keyed by a hash of the request signature."""

    def __init__(self, max_entries: int = 500, ttl_seconds: float = 3600.0) -> None:
        self._max_entries = max_entries
        self._ttl = ttl_seconds
        self._store: "OrderedDict[str, Tuple[float, ModelResponse]]" = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._lock = threading.RLock()
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    @staticmethod
    def compute_key(request: "ModelRequest") -> str:
        payload = json.dumps(
            {
                "task_type": request.task_type.value,
                "prompt": request.prompt,
                "system_prompt": request.system_prompt,
                "messages": request.messages,
                "model_id": request.model_id,
                "config": request.config.to_dict(),
                "images": request.images,
                "audio": request.audio,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[ModelResponse]:
        with self._lock:
            if not self._enabled:
                self._misses += 1
                return None
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            ts, response = entry
            if time.time() - ts > self._ttl:
                self._store.pop(key, None)
                self._misses += 1
                return None
            self._store.move_to_end(key)
            self._hits += 1
            cached = ModelResponse(
                request_id=response.request_id,
                provider_id=response.provider_id,
                model_id=response.model_id,
                content=response.content,
                content_urls=list(response.content_urls),
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
                cost=response.cost,
                finish_reason=response.finish_reason,
                cached=True,
                simulated=response.simulated,
                metadata=dict(response.metadata),
            )
            return cached

    def put(self, key: str, response: ModelResponse) -> None:
        with self._lock:
            if not self._enabled:
                return
            self._store[key] = (time.time(), response)
            self._store.move_to_end(key)
            while len(self._store) > self._max_entries:
                self._store.popitem(last=False)

    def clear(self) -> int:
        with self._lock:
            count = len(self._store)
            self._store.clear()
            self._hits = 0
            self._misses = 0
            return count

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "enabled": self._enabled,
                "entries": len(self._store),
                "max_entries": self._max_entries,
                "ttl_seconds": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
            }


# ============================================================================
# Task Classification Maps
# ============================================================================

# Keyword-based task classification used when the caller does not specify a
# task type explicitly. Each task maps to the keywords that strongly indicate
# the task.
_TASK_KEYWORDS: Dict[TaskType, List[str]] = {
    TaskType.WORLD_BUILDING: [
        "world", "biome", "terrain", "continent", "geography", "lore",
        "kingdom", "region", "map", "environment",
    ],
    TaskType.CHARACTER_DESIGN: [
        "character", "hero", "villain", "npc", "protagonist", "portrait",
        "avatar", "concept art", "appearance",
    ],
    TaskType.DIALOGUE: [
        "dialogue", "conversation", "speak", "say", "talk", "voice line",
        "chitchat", "reply",
    ],
    TaskType.CODE_GEN: [
        "code", "function", "class", "script", "implement", "compile",
        "debug code", "refactor", "program", "api",
    ],
    TaskType.ASSET_IMAGE: [
        "image", "texture", "sprite", "icon", "art", "illustration",
        "concept", "render image", "draw",
    ],
    TaskType.ASSET_VIDEO: [
        "video", "cutscene", "cinematic", "animation clip", "footage",
        "trailer",
    ],
    TaskType.ASSET_3D: [
        "3d", "mesh", "model", "rig", "skeleton", "voxel", "prefab",
        "low-poly", "high-poly",
    ],
    TaskType.ASSET_AUDIO: [
        "sound effect", "sfx", "ambient", "foley", "audio clip",
    ],
    TaskType.MUSIC_GEN: [
        "music", "soundtrack", "song", "melody", "score", "compose music",
    ],
    TaskType.VOICE_ACTING: [
        "voice acting", "narration", "tts", "voiceover", "speech",
    ],
    TaskType.BUG_ANALYSIS: [
        "bug", "crash", "error", "stacktrace", "exception", "defect",
        "regression",
    ],
    TaskType.BALANCE_TEST: [
        "balance", "tuning", "difficulty", "stats tuning", "playtest",
        "economy balance",
    ],
    TaskType.NARRATIVE: [
        "narrative", "story", "plot", "quest", "arc", "scene", "chapter",
    ],
    TaskType.TRANSLATION: [
        "translate", "translation", "localize", "localization", "i18n",
    ],
    TaskType.EMBEDDING: [
        "embed", "embedding", "vector", "semantic search", "similarity",
    ],
    TaskType.SUMMARIZATION: [
        "summarize", "summary", "tldr", "condense", "brief",
    ],
}


# ============================================================================
# LLM Router Singleton
# ============================================================================


class LLMRouter:
    """
    Singleton LLM router and model integration system.

    Provides a unified interface for routing requests across a diverse
    catalog of model providers. The router selects the optimal model based
    on the active routing strategy, applies rate limiting and caching,
    executes the request (or simulates it), and tracks usage, cost, and
    health for every provider.

    Thread safety:
        All public mutating operations are guarded by a re-entrant lock.
        Read operations that return snapshots acquire the lock briefly to
        avoid torn reads.

    Usage:
        router = LLMRouter.get_instance()
        response = router.execute_request(ModelRequest(
            task_type=TaskType.CODE_GEN,
            prompt="Implement a coroutine-based game loop",
        ))
    """

    _instance: Optional["LLMRouter"] = None
    _lock = threading.RLock()

    # -- Tunable defaults ------------------------------------------------
    _DEFAULT_CACHE_ENTRIES: int = 500
    _DEFAULT_CACHE_TTL: float = 3600.0
    _DEFAULT_HEALTH_INTERVAL: float = 60.0
    _MAX_HEALTH_LATENCY_SAMPLES: int = 100
    _DEGRADED_FAILURE_THRESHOLD: int = 3
    _OFFLINE_FAILURE_THRESHOLD: int = 6
    _SIMULATED_LATENCY_BASE: float = 80.0
    _SIMULATED_LATENCY_JITTER: float = 60.0

    def __init__(self) -> None:
        self._providers: Dict[str, ModelProvider] = {}
        self._models: Dict[str, Tuple[str, ModelCapability]] = {}
        self._routing_rules: Dict[str, RoutingRule] = {}
        self._task_model_map: Dict[TaskType, str] = {}
        self._fallback_chains: Dict[str, List[str]] = {}
        self._api_keys: Dict[str, APIKeyEntry] = {}
        self._rate_limiters: Dict[str, _TokenBucket] = {}
        self._cache = _ResponseCache(
            max_entries=self._DEFAULT_CACHE_ENTRIES,
            ttl_seconds=self._DEFAULT_CACHE_TTL,
        )
        self._usage_stats: Dict[str, UsageStats] = {}
        self._global_stats: UsageStats = UsageStats()
        self._routing_strategy: RoutingStrategy = RoutingStrategy.CAPABILITY_MATCH
        self._simulation_mode: bool = False
        self._health_thread: Optional[threading.Thread] = None
        self._health_running: bool = False
        self._health_stop_event = threading.Event()
        self._latency_samples: Dict[str, deque] = {}
        self._seeded: bool = False
        # Seed the catalog with the default providers and task mappings.
        self._seed_default_data()

    @classmethod
    def get_instance(cls) -> "LLMRouter":
        """Return the singleton LLMRouter instance, creating it on first call."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Provider Management
    # ------------------------------------------------------------------

    def register_provider(
        self,
        provider_id: str,
        name: str,
        vendor: str,
        endpoints: Optional[List[ModelEndpoint]] = None,
        api_key: str = "",
        api_key_env: str = "",
        rate_limit_rpm: int = 60,
        rate_limit_tpm: int = 100_000,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModelProvider:
        """Register a new model provider and return the resulting object."""
        with self._lock:
            provider = ModelProvider(
                provider_id=provider_id,
                name=name,
                vendor=vendor,
                endpoints=endpoints or [ModelEndpoint()],
                rate_limit_rpm=rate_limit_rpm,
                rate_limit_tpm=rate_limit_tpm,
                enabled=enabled,
                metadata=metadata or {},
            )
            if api_key or api_key_env:
                entry = APIKeyEntry(
                    provider_id=provider_id,
                    key_value=api_key,
                    env_var=api_key_env,
                    label=f"{vendor} API key",
                )
                self._api_keys[entry.key_id] = entry
                provider.api_key_id = entry.key_id
                if api_key:
                    self._simulation_mode = False
            self._providers[provider_id] = provider
            self._usage_stats[provider_id] = UsageStats()
            self._latency_samples[provider_id] = deque(
                maxlen=self._MAX_HEALTH_LATENCY_SAMPLES
            )
            self._rate_limiters[provider_id] = _TokenBucket(
                rate=rate_limit_rpm / 60.0,
                capacity=float(rate_limit_rpm),
            )
            logger.info("Registered provider %s (%s)", provider_id, vendor)
            return provider

    def unregister_provider(self, provider_id: str) -> bool:
        """Remove a provider and all its models from the catalog."""
        with self._lock:
            if provider_id not in self._providers:
                return False
            for model_id in [
                m_id
                for m_id, (pid, _) in self._models.items()
                if pid == provider_id
            ]:
                self._models.pop(model_id, None)
            self._providers.pop(provider_id, None)
            self._rate_limiters.pop(provider_id, None)
            self._usage_stats.pop(provider_id, None)
            self._latency_samples.pop(provider_id, None)
            self._fallback_chains.pop(provider_id, None)
            # Remove any API keys bound to this provider.
            for kid, entry in list(self._api_keys.items()):
                if entry.provider_id == provider_id:
                    self._api_keys.pop(kid, None)
            logger.info("Unregistered provider %s", provider_id)
            return True

    def get_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Return a snapshot dict for a provider, or None if not found."""
        with self._lock:
            provider = self._providers.get(provider_id)
            return provider.to_dict() if provider else None

    def list_providers(self) -> List[Dict[str, Any]]:
        """Return snapshot dicts for all registered providers."""
        with self._lock:
            return [p.to_dict() for p in self._providers.values()]

    # ------------------------------------------------------------------
    # Model Management
    # ------------------------------------------------------------------

    def register_model(
        self,
        provider_id: str,
        capability: ModelCapability,
    ) -> bool:
        """Register a model under an existing provider. Returns success."""
        with self._lock:
            provider = self._providers.get(provider_id)
            if provider is None:
                logger.warning(
                    "Cannot register model %s: provider %s not found",
                    capability.model_id,
                    provider_id,
                )
                return False
            provider.capabilities.append(capability)
            self._models[capability.model_id] = (provider_id, capability)
            logger.info(
                "Registered model %s under provider %s",
                capability.model_id,
                provider_id,
            )
            return True

    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Return a snapshot dict for a model, including its provider id."""
        with self._lock:
            entry = self._models.get(model_id)
            if entry is None:
                return None
            provider_id, capability = entry
            snapshot = capability.to_dict()
            snapshot["provider_id"] = provider_id
            return snapshot

    def list_models(self) -> List[Dict[str, Any]]:
        """Return snapshot dicts for all registered models."""
        with self._lock:
            results: List[Dict[str, Any]] = []
            for model_id, (provider_id, capability) in self._models.items():
                snapshot = capability.to_dict()
                snapshot["provider_id"] = provider_id
                results.append(snapshot)
            return results

    def search_models(
        self,
        model_type: Optional[ModelType] = None,
        provider_id: Optional[str] = None,
        min_quality: float = 0.0,
        max_cost_per_1k: Optional[float] = None,
        supports_streaming: Optional[bool] = None,
        supports_vision: Optional[bool] = None,
        supports_function_calling: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search the model catalog by capability and metadata filters."""
        with self._lock:
            results: List[Dict[str, Any]] = []
            tag_set = set(tags) if tags else None
            for model_id, (pid, cap) in self._models.items():
                if model_type is not None and model_type not in cap.model_types:
                    continue
                if provider_id is not None and pid != provider_id:
                    continue
                if cap.quality_score < min_quality:
                    continue
                if max_cost_per_1k is not None:
                    blended = (cap.cost_per_1k_input + cap.cost_per_1k_output) / 2.0
                    if blended > max_cost_per_1k:
                        continue
                if supports_streaming is not None and cap.supports_streaming != supports_streaming:
                    continue
                if supports_vision is not None and cap.supports_vision != supports_vision:
                    continue
                if (
                    supports_function_calling is not None
                    and cap.supports_function_calling != supports_function_calling
                ):
                    continue
                if tag_set is not None and not tag_set.intersection(cap.tags):
                    continue
                snapshot = cap.to_dict()
                snapshot["provider_id"] = pid
                results.append(snapshot)
                if len(results) >= limit:
                    break
            return results

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def set_routing_strategy(self, strategy: RoutingStrategy) -> None:
        """Set the active routing strategy used for provider selection."""
        with self._lock:
            self._routing_strategy = strategy
            logger.info("Routing strategy set to %s", strategy.value)

    def get_routing_strategy(self) -> RoutingStrategy:
        """Return the currently active routing strategy."""
        with self._lock:
            return self._routing_strategy

    def add_routing_rule(self, rule: RoutingRule) -> str:
        """Add a routing rule and return its id."""
        with self._lock:
            self._routing_rules[rule.rule_id] = rule
            logger.info("Added routing rule %s (%s)", rule.rule_id, rule.name)
            return rule.rule_id

    def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove a routing rule by id."""
        with self._lock:
            if rule_id not in self._routing_rules:
                return False
            self._routing_rules.pop(rule_id, None)
            return True

    def list_routing_rules(self) -> List[Dict[str, Any]]:
        """Return snapshot dicts for all routing rules, sorted by priority."""
        with self._lock:
            rules = sorted(
                self._routing_rules.values(),
                key=lambda r: r.priority,
                reverse=True,
            )
            return [r.to_dict() for r in rules]

    def route_request(self, request: ModelRequest) -> Tuple[str, str]:
        """
        Determine the optimal provider and model for a request without
        executing it. Returns a (provider_id, model_id) tuple.

        Selection order:
          1. Explicit provider/model on the request
          2. Matching routing rules
          3. Task-to-model mapping
          4. Strategy-based scoring of all candidate models
        """
        with self._lock:
            # Step 1: explicit overrides
            if request.provider_id and request.model_id:
                if self._is_available(request.provider_id, request.model_id):
                    return request.provider_id, request.model_id
            if request.model_id and request.model_id in self._models:
                pid, _ = self._models[request.model_id]
                if self._is_available(pid, request.model_id):
                    return pid, request.model_id

            # Step 2: routing rules
            for rule in sorted(
                self._routing_rules.values(),
                key=lambda r: r.priority,
                reverse=True,
            ):
                if not rule.matches(request):
                    continue
                if rule.preferred_model and rule.preferred_model in self._models:
                    pid, _ = self._models[rule.preferred_model]
                    if self._is_available(pid, rule.preferred_model):
                        return pid, rule.preferred_model
                if rule.preferred_provider and rule.preferred_provider in self._providers:
                    provider = self._providers[rule.preferred_provider]
                    if provider.enabled and provider.health.status != ProviderStatus.OFFLINE:
                        model_id = self._pick_model_in_provider(
                            provider, request.task_type
                        )
                        if model_id:
                            return provider.provider_id, model_id

            # Step 3: task-to-model mapping
            mapped = self._task_model_map.get(request.task_type)
            if mapped and mapped in self._models:
                pid, _ = self._models[mapped]
                if self._is_available(pid, mapped):
                    return pid, mapped

            # Step 4: strategy-based scoring
            candidates = self._collect_candidates(request)
            if not candidates:
                return "", ""
            scored = self._score_candidates(candidates, request)
            return scored[0][0], scored[0][1]

    def _is_available(self, provider_id: str, model_id: str) -> bool:
        """Check that a provider is enabled, healthy, and hosts the model."""
        provider = self._providers.get(provider_id)
        if provider is None or not provider.enabled:
            return False
        if provider.health.status == ProviderStatus.OFFLINE:
            return False
        return model_id in self._models and self._models[model_id][0] == provider_id

    def _pick_model_in_provider(
        self, provider: ModelProvider, task_type: TaskType
    ) -> Optional[str]:
        """Pick the best model within a single provider for a task."""
        desired_type = self._task_to_model_type(task_type)
        best: Optional[Tuple[str, float]] = None
        for cap in provider.capabilities:
            if desired_type is not None and desired_type not in cap.model_types:
                continue
            score = cap.quality_score
            if best is None or score > best[1]:
                best = (cap.model_id, score)
        if best is not None:
            return best[0]
        # Fall back to the first model the provider exposes.
        return provider.capabilities[0].model_id if provider.capabilities else None

    def _collect_candidates(
        self, request: ModelRequest
    ) -> List[Tuple[str, str, ModelCapability]]:
        """Collect all (provider_id, model_id, capability) tuples that could
        serve the request based on task type and active filters."""
        desired_type = self._task_to_model_type(request.task_type)
        candidates: List[Tuple[str, str, ModelCapability]] = []
        for model_id, (pid, cap) in self._models.items():
            provider = self._providers.get(pid)
            if provider is None or not provider.enabled:
                continue
            if provider.health.status == ProviderStatus.OFFLINE:
                continue
            if desired_type is not None and desired_type not in cap.model_types:
                continue
            if request.max_cost is not None:
                blended = (cap.cost_per_1k_input + cap.cost_per_1k_output) / 2.0
                if blended > request.max_cost:
                    continue
            if (
                request.max_latency_ms is not None
                and cap.latency_tier == "high"
                and request.max_latency_ms < 500
            ):
                continue
            candidates.append((pid, model_id, cap))
        return candidates

    def _score_candidates(
        self,
        candidates: List[Tuple[str, str, ModelCapability]],
        request: ModelRequest,
    ) -> List[Tuple[str, str]]:
        """Score and sort candidates according to the active strategy."""
        strategy = self._routing_strategy
        scored: List[Tuple[str, str, float]] = []
        for pid, mid, cap in candidates:
            provider = self._providers.get(pid)
            if provider is None:
                continue
            if strategy == RoutingStrategy.COST_OPTIMAL:
                blended_cost = (cap.cost_per_1k_input + cap.cost_per_1k_output) / 2.0
                score = -blended_cost
            elif strategy == RoutingStrategy.LATENCY_OPTIMAL:
                latency_penalty = {"low": 0.0, "medium": 0.3, "high": 0.6}.get(
                    cap.latency_tier, 0.3
                )
                score = -latency_penalty - provider.health.avg_latency_ms / 10_000.0
            elif strategy == RoutingStrategy.QUALITY_OPTIMAL:
                score = cap.quality_score
            else:  # CAPABILITY_MATCH
                blended_cost = (cap.cost_per_1k_input + cap.cost_per_1k_output) / 2.0
                score = (
                    cap.quality_score * 5.0
                    + (1.0 if provider.health.status == ProviderStatus.ACTIVE else 0.0)
                    - blended_cost * 2.0
                    - {"low": 0.0, "medium": 0.2, "high": 0.5}.get(cap.latency_tier, 0.2)
                )
            scored.append((pid, mid, score))
        scored.sort(key=lambda x: x[2], reverse=True)
        return [(pid, mid) for pid, mid, _ in scored]

    @staticmethod
    def _task_to_model_type(task_type: TaskType) -> Optional[ModelType]:
        """Map a game-dev task type to the most relevant model type."""
        mapping = {
            TaskType.WORLD_BUILDING: ModelType.TEXT,
            TaskType.CHARACTER_DESIGN: ModelType.IMAGE_GEN,
            TaskType.DIALOGUE: ModelType.TEXT,
            TaskType.CODE_GEN: ModelType.CODE,
            TaskType.ASSET_IMAGE: ModelType.IMAGE_GEN,
            TaskType.ASSET_VIDEO: ModelType.VIDEO_GEN,
            TaskType.ASSET_3D: ModelType.GEN_3D,
            TaskType.ASSET_AUDIO: ModelType.AUDIO_GEN,
            TaskType.MUSIC_GEN: ModelType.AUDIO_GEN,
            TaskType.VOICE_ACTING: ModelType.TTS,
            TaskType.BUG_ANALYSIS: ModelType.REASONING,
            TaskType.BALANCE_TEST: ModelType.REASONING,
            TaskType.NARRATIVE: ModelType.TEXT,
            TaskType.TRANSLATION: ModelType.TEXT,
            TaskType.EMBEDDING: ModelType.EMBEDDING,
            TaskType.SUMMARIZATION: ModelType.TEXT,
        }
        return mapping.get(task_type)

    def classify_task(self, prompt: str) -> TaskType:
        """Classify a free-text prompt into a task type by keyword matching."""
        prompt_lower = prompt.lower()
        best_type = TaskType.DIALOGUE
        best_score = 0
        for task_type, keywords in _TASK_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > best_score:
                best_score = score
                best_type = task_type
        return best_type

    # ------------------------------------------------------------------
    # Execution & Streaming
    # ------------------------------------------------------------------

    def execute_request(self, request: ModelRequest) -> ModelResponse:
        """
        Route and execute a model request end-to-end.

        Applies caching, rate limiting, fallback, health tracking, and cost
        accounting. Returns a ModelResponse (simulated when no API keys are
        configured or simulation mode is enabled).
        """
        with self._lock:
            simulation_mode = self._simulation_mode or not self._has_any_api_key()
            strategy = self._routing_strategy

        # Cache lookup
        if request.use_cache and self._cache.enabled:
            cache_key = self._cache.compute_key(request)
            cached = self._cache.get(cache_key)
            if cached is not None:
                cached.request_id = request.request_id
                self._record_cache_hit(request)
                logger.debug("Cache hit for request %s", request.request_id)
                return cached

        # Determine provider/model
        provider_id, model_id = self.route_request(request)
        if not provider_id or not model_id:
            return self._error_response(
                request,
                "No suitable provider/model available for task "
                f"{request.task_type.value}",
            )

        # Build fallback chain
        chain = self._build_execution_chain(provider_id, model_id, request)

        last_error: Optional[str] = None
        for idx, (pid, mid) in enumerate(chain):
            fallback_used = idx > 0
            # Rate limit
            limiter = self._rate_limiters.get(pid)
            if limiter is not None:
                wait = limiter.wait_time(1.0)
                if wait > 0 and wait < 5.0:
                    time.sleep(wait)
                if not limiter.try_consume(1.0):
                    self._mark_rate_limited(pid)
                    last_error = f"Rate limited on {pid}"
                    continue

            start = time.time()
            try:
                if simulation_mode:
                    response = self._simulate_response(
                        request, pid, mid, fallback_used
                    )
                else:
                    response = self._dispatch_to_provider(
                        request, pid, mid, fallback_used
                    )
                elapsed = (time.time() - start) * 1000.0
                response.latency_ms = elapsed
                self._record_success(pid, mid, request, response, elapsed, fallback_used)
                if request.use_cache and self._cache.enabled and not fallback_used:
                    self._cache.put(cache_key, response)
                return response
            except Exception as exc:  # noqa: BLE001 - broad catch for fallback
                elapsed = (time.time() - start) * 1000.0
                last_error = str(exc)
                self._record_failure(pid, mid, request, elapsed, exc)
                logger.warning(
                    "Provider %s/%s failed: %s (trying fallback)", pid, mid, exc
                )
                continue

        return self._error_response(
            request,
            f"All providers failed. Last error: {last_error}",
        )

    def stream_request(self, request: ModelRequest) -> Generator[str, None, None]:
        """
        Stream a text response in chunks. Falls back to a single chunk when
        the selected provider does not support streaming or when simulating.
        """
        with self._lock:
            simulation_mode = self._simulation_mode or not self._has_any_api_key()

        provider_id, model_id = self.route_request(request)
        if not provider_id or not model_id:
            yield "[LLMRouter] No provider available for streaming"
            return

        if simulation_mode:
            full = self._simulate_content(request, provider_id, model_id)
            yield from self._chunk_text(full)
            return

        with self._lock:
            cap = self._models.get(model_id, (None, None))[1]
        supports = cap.supports_streaming if cap else False
        if not supports:
            response = self.execute_request(request)
            yield from self._chunk_text(response.content)
            return

        full = self._simulate_content(request, provider_id, model_id)
        yield from self._chunk_text(full)

    @staticmethod
    def _chunk_text(text: str) -> Generator[str, None, None]:
        """Yield text in word-grouped chunks suitable for streaming."""
        words = text.split()
        if not words:
            return
        chunk_size = max(1, len(words) // 10) if len(words) >= 10 else 1
        for i in range(0, len(words), chunk_size):
            yield " ".join(words[i: i + chunk_size]) + " "

    def _build_execution_chain(
        self, primary_pid: str, primary_mid: str, request: ModelRequest
    ) -> List[Tuple[str, str]]:
        """Build the ordered list of (provider, model) pairs to try."""
        chain: List[Tuple[str, str]] = [(primary_pid, primary_mid)]
        # Explicit fallback chain for the primary provider
        fb_models = self._fallback_chains.get(primary_pid, [])
        for mid in fb_models:
            if mid == primary_mid:
                continue
            if mid in self._models:
                pid, _ = self._models[mid]
                chain.append((pid, mid))
        # Strategy-based alternates
        candidates = self._collect_candidates(request)
        scored = self._score_candidates(candidates, request)
        for pid, mid in scored:
            if (pid, mid) not in chain:
                chain.append((pid, mid))
        return chain

    def _dispatch_to_provider(
        self,
        request: ModelRequest,
        provider_id: str,
        model_id: str,
        fallback_used: bool,
    ) -> ModelResponse:
        """Dispatch a request to the real provider endpoint.

        Uses the provider_dispatcher module to make actual API calls.
        Falls back to simulation when the dispatcher cannot fulfill the request.
        """
        key_entry = self._get_api_key_for_provider(provider_id)
        if key_entry is None or not key_entry.key_value:
            if provider_id not in ("ollama",):
                # Fall back to simulation when no API key is configured
                # so that multimodal endpoints always return a usable response
                return self._simulate_response(
                    request, provider_id, model_id, fallback_used
                )
            key_value = ""
        else:
            key_value = key_entry.key_value
            key_entry.use_count += 1
            key_entry.last_used = time.time()

        # Resolve base URL for the provider
        base_url = self._get_base_url_for_provider(provider_id)

        # Determine task type string
        task_type_str = request.task_type.value if hasattr(request.task_type, 'value') else str(request.task_type)

        try:
            from sparkai.agent.provider_dispatcher import dispatch as _dispatch
            result = _dispatch(
                provider_id=provider_id,
                model_id=model_id,
                api_key=key_value,
                base_url=base_url,
                prompt=request.prompt,
                task_type=task_type_str,
                images=getattr(request, 'images', None),
                system_prompt=getattr(request, 'system_prompt', None),
                temperature=getattr(request, 'temperature', 0.7),
                max_tokens=getattr(request, 'max_tokens', 2048),
            )
        except Exception as exc:
            logger.warning("Dispatcher error for %s/%s: %s", provider_id, model_id, exc)
            return self._simulate_response(request, provider_id, model_id, fallback_used)

        if not result.get("success", False):
            logger.warning("Dispatch failed for %s/%s: %s", provider_id, model_id, result.get("error"))
            raise RuntimeError(result.get("error", "Unknown dispatch error"))

        # Convert dict to ModelResponse
        response = ModelResponse(
            request_id=result.get("request_id", request.request_id),
            provider_id=provider_id,
            model_id=model_id,
            content=result.get("content", ""),
            content_urls=result.get("content_urls", []),
            latency_ms=result.get("latency_ms", 0.0),
            fallback_used=fallback_used,
            error=None,
            simulated=False,
            metadata={
                "content_type": result.get("content_type", "text"),
                "usage": result.get("usage", {}),
            },
        )
        return response

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def set_simulation_mode(self, enabled: bool) -> None:
        """Enable or disable simulation mode."""
        with self._lock:
            self._simulation_mode = enabled
            logger.info("Simulation mode %s", "enabled" if enabled else "disabled")

    def get_simulation_mode(self) -> bool:
        """Return True if simulation mode is active."""
        with self._lock:
            return self._simulation_mode

    def simulate_request(self, request: ModelRequest) -> ModelResponse:
        """Force a simulated response regardless of API key configuration."""
        provider_id, model_id = self.route_request(request)
        if not provider_id or not model_id:
            provider_id = "simulation"
            model_id = "simulated-model"
        return self._simulate_response(request, provider_id, model_id, False)

    def _simulate_response(
        self,
        request: ModelRequest,
        provider_id: str,
        model_id: str,
        fallback_used: bool,
    ) -> ModelResponse:
        """Build a deterministic, fake response for development use."""
        content = self._simulate_content(request, provider_id, model_id)
        input_tokens = self._estimate_tokens(request.prompt)
        output_tokens = self._estimate_tokens(content)
        latency = (
            self._SIMULATED_LATENCY_BASE
            + random.random() * self._SIMULATED_LATENCY_JITTER
        )
        cap = self._models.get(model_id, (None, None))[1]
        cost = self._compute_cost(cap, input_tokens, output_tokens, request) if cap else 0.0

        # Extract content URLs for multimodal task types so the frontend
        # can display simulated images, audio, video, and 3D results.
        content_urls: List[str] = []
        if request.task_type in (
            TaskType.ASSET_IMAGE,
            TaskType.ASSET_VIDEO,
            TaskType.ASSET_3D,
            TaskType.ASSET_AUDIO,
            TaskType.MUSIC_GEN,
            TaskType.VOICE_ACTING,
        ):
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped.startswith("url:"):
                    url = stripped[4:].strip()
                    if url:
                        content_urls.append(url)

        return ModelResponse(
            request_id=request.request_id,
            provider_id=provider_id,
            model_id=model_id,
            content=content,
            content_urls=content_urls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency, 2),
            cost=cost,
            finish_reason="stop",
            simulated=True,
            fallback_used=fallback_used,
            metadata={"task_type": request.task_type.value},
        )

    def _simulate_content(
        self, request: ModelRequest, provider_id: str, model_id: str
    ) -> str:
        """Generate plausible simulated content based on task type."""
        task = request.task_type
        prompt_preview = request.prompt[:160]
        if task == TaskType.CODE_GEN:
            return (
                f"// Simulated code from {provider_id}/{model_id}\n"
                f"// Request: {prompt_preview}\n"
                "def generated_solution():\n"
                "    # TODO: implement with real provider\n"
                "    pass\n"
            )
        if task == TaskType.ASSET_IMAGE:
            return (
                f"[SIMULATED IMAGE] provider={provider_id} model={model_id}\n"
                f"Prompt: {prompt_preview}\n"
                "url: https://simulated.cdn/sparklabs/image_placeholder.png"
            )
        if task == TaskType.ASSET_VIDEO:
            return (
                f"[SIMULATED VIDEO] provider={provider_id} model={model_id}\n"
                f"Prompt: {prompt_preview}\n"
                "url: https://simulated.cdn/sparklabs/video_placeholder.mp4"
            )
        if task == TaskType.ASSET_3D:
            return (
                f"[SIMULATED 3D MESH] provider={provider_id} model={model_id}\n"
                f"Prompt: {prompt_preview}\n"
                "url: https://simulated.cdn/sparklabs/asset_placeholder.glb"
            )
        if task == TaskType.MUSIC_GEN:
            return (
                f"[SIMULATED MUSIC] provider={provider_id} model={model_id}\n"
                f"Prompt: {prompt_preview}\n"
                "url: https://simulated.cdn/sparklabs/music_placeholder.wav"
            )
        if task == TaskType.VOICE_ACTING:
            return (
                f"[SIMULATED TTS] provider={provider_id} model={model_id}\n"
                f"Prompt: {prompt_preview}\n"
                "url: https://simulated.cdn/sparklabs/voice_placeholder.mp3"
            )
        if task == TaskType.EMBEDDING:
            dims = 128
            embedding = [
                round(((hash(request.prompt) + i) % 1000) / 1000.0 - 0.5, 6)
                for i in range(dims)
            ]
            return json.dumps({"embedding": embedding, "model": model_id})
        if task == TaskType.BUG_ANALYSIS:
            return (
                f"[SIMULATED BUG ANALYSIS] provider={provider_id} model={model_id}\n"
                f"Investigated: {prompt_preview}\n"
                "Likely root cause: simulated hypothesis. "
                "Suggested fix: review stack trace and reproduction steps."
            )
        # Default text response
        return (
            f"[SIMULATED] {provider_id}/{model_id} -> {prompt_preview}"
            f"{'...' if len(request.prompt) > 160 else ''}"
        )

    # ------------------------------------------------------------------
    # API Key Vault
    # ------------------------------------------------------------------

    def set_api_key(
        self,
        provider_id: str,
        api_key: str,
        env_var: str = "",
        label: str = "",
    ) -> str:
        """Securely store an API key for a provider. Returns the key id."""
        with self._lock:
            provider = self._providers.get(provider_id)
            if provider is None:
                logger.warning(
                    "Cannot set API key for unknown provider %s", provider_id
                )
                return ""
            # Remove any previous key for this provider
            for kid, entry in list(self._api_keys.items()):
                if entry.provider_id == provider_id:
                    self._api_keys.pop(kid, None)
            entry = APIKeyEntry(
                provider_id=provider_id,
                key_value=api_key,
                env_var=env_var,
                label=label or f"{provider.vendor} API key",
            )
            self._api_keys[entry.key_id] = entry
            provider.api_key_id = entry.key_id
            if api_key:
                self._simulation_mode = False
            logger.info("API key stored for provider %s", provider_id)
            return entry.key_id

    def set_provider_base_url(self, provider_id: str, base_url: str) -> bool:
        """Update the base URL for a provider. Returns True on success."""
        with self._lock:
            provider = self._providers.get(provider_id)
            if provider is None:
                logger.warning(
                    "Cannot set base URL for unknown provider %s", provider_id
                )
                return False
            if provider.endpoints:
                provider.endpoints[0].url = base_url
            else:
                provider.endpoints.append(ModelEndpoint(url=base_url))
            logger.info("Base URL updated for provider %s: %s", provider_id, base_url)
            return True

    def get_api_key_status(self, provider_id: str) -> Dict[str, Any]:
        """Return masked status of the API key for a provider."""
        with self._lock:
            entry = self._get_api_key_for_provider(provider_id)
            if entry is None:
                return {
                    "provider_id": provider_id,
                    "configured": False,
                    "masked": "",
                }
            snapshot = entry.to_dict()
            snapshot["configured"] = bool(entry.key_value)
            return snapshot

    def remove_api_key(self, provider_id: str) -> bool:
        """Remove the API key associated with a provider."""
        with self._lock:
            entry = self._get_api_key_for_provider(provider_id)
            if entry is None:
                return False
            self._api_keys.pop(entry.key_id, None)
            provider = self._providers.get(provider_id)
            if provider is not None:
                provider.api_key_id = None
            return True

    def list_api_keys(self) -> List[Dict[str, Any]]:
        """Return masked snapshots of all stored API keys."""
        with self._lock:
            return [e.to_dict() for e in self._api_keys.values()]

    def _get_api_key_for_provider(self, provider_id: str) -> Optional[APIKeyEntry]:
        """Return the APIKeyEntry for a provider, or None."""
        for entry in self._api_keys.values():
            if entry.provider_id == provider_id:
                return entry
        return None

    def _get_base_url_for_provider(self, provider_id: str) -> str:
        """Return the configured base URL for a provider, or a sensible default."""
        with self._lock:
            provider = self._providers.get(provider_id)
            if provider and provider.endpoints and provider.endpoints[0].url:
                return provider.endpoints[0].url
        # Fallback defaults for well-known providers
        defaults = {
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "google": "https://generativelanguage.googleapis.com/v1beta",
            "huggingface": "https://api-inference.huggingface.co",
            "ollama": "http://localhost:11434",
            "together": "https://api.together.xyz/v1",
            "groq": "https://api.groq.com/openai/v1",
            "stability": "https://api.stability.ai/v1",
            "elevenlabs": "https://api.elevenlabs.io/v1",
            "replicate": "https://api.replicate.com/v1",
            "mistral": "https://api.mistral.ai/v1",
            "cohere": "https://api.cohere.ai/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "qwen": "https://dashscope.aliyuncs.com/api/v1",
            "fireworks": "https://api.fireworks.ai/inference/v1",
            "xai": "https://api.x.ai/v1",
            "perplexity": "https://api.perplexity.ai",
            "ai21": "https://api.ai21.com/studio/v1",
            "fal": "https://fal.run",
            "deepinfra": "https://api.deepinfra.com/v1/openai",
            "nvidia": "https://integrate.api.nvidia.com/v1",
            "cerebras": "https://api.cerebras.ai/v1",
            "bedrock": "https://bedrock-runtime.us-east-1.amazonaws.com",
            "azure": "https://{resource}.openai.azure.com",
            "openrouter": "https://openrouter.ai/api/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
            "moonshot": "https://api.moonshot.cn/v1",
            "minimax": "https://api.minimax.chat/v1",
            "doubao": "https://ark.cn-beijing.volces.com/api/v3",
            "ernie": "https://qianfan.baidubce.com/v2",
            "stepfun": "https://api.stepfun.com/v1",
            "lambda": "https://api.lambdalabs.com/v1",
            "assemblyai": "https://api.assemblyai.com/v2",
            "deepgram": "https://api.deepgram.com/v1",
            "playht": "https://api.play.ht/api/v2",
            "cartesia": "https://api.cartesia.ai/v1",
            "rodin": "https://api.rodin.ai/v1",
            "sloyd": "https://api.sloyd.ai/v1",
            "polycam": "https://api.polycam.ai/v1",
            "animatediff": "https://api.animatediff.com/v1",
            "deforum": "https://api.deforum.com/v1",
            "genmo": "https://api.genmo.ai/v1",
            "stable-audio": "https://api.stability.ai/v2/audio",
            "mubert": "https://api.mubert.com/v3",
            "audioldm": "http://localhost:5002",
            "voyage": "https://api.voyageai.com/v1",
            "nomic": "https://api.nomic.ai/v1",
            "jina": "https://api.jina.ai/v1",
            "mixedbread": "https://api.mixedbread.ai/v1",
            "haiper": "https://api.haiper.ai/v1",
            "domika": "https://api.domika.ai/v1",
            "yi": "https://api.01.ai/v1",
            "baichuan": "https://api.baichuan-ai.com/v1",
            "siliconflow": "https://api.siliconflow.cn/v1",
            "modelscope": "https://api.modelscope.cn/v1",
            "predibase": "https://api.predibase.com/v1",
            "octoai": "https://api.octoai.cloud/v1",
            "leonardo": "https://cloud.leonardo.ai/api/rest/v1",
            "morph": "https://api.morphstudio.com/v1",
            "viggle": "https://api.viggle.ai/v1",
            "did": "https://api.d-id.com/v1",
            "heygen": "https://api.heygen.com/v1",
            "synthesia": "https://api.synthesia.io/v2",
            "tabnine": "https://api.tabnine.com/v1",
            "codeium": "https://api.codeium.com/v1",
        }
        return defaults.get(provider_id, "https://api.example.com/v1")

    def _has_any_api_key(self) -> bool:
        """Return True if at least one provider has a real API key set."""
        return any(
            bool(e.key_value) for e in self._api_keys.values()
        )

    # ------------------------------------------------------------------
    # Health Monitoring
    # ------------------------------------------------------------------

    def get_health_status(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Return the health snapshot for a provider."""
        with self._lock:
            provider = self._providers.get(provider_id)
            return provider.health.to_dict() if provider else None

    def ping_provider(self, provider_id: str) -> Dict[str, Any]:
        """Perform a synchronous ping of a provider and update its health."""
        with self._lock:
            provider = self._providers.get(provider_id)
            if provider is None:
                return {"provider_id": provider_id, "error": "not found"}
            start = time.time()
            # In simulation, a ping always succeeds quickly.
            ok = True
            error = ""
            if not self._simulation_mode and self._has_any_api_key():
                key = self._get_api_key_for_provider(provider_id)
                if key is None or not key.key_value:
                    ok = False
                    error = "no API key configured"
            elapsed = (time.time() - start) * 1000.0
            self._apply_health_result(provider, ok, elapsed, error)
            return {
                "provider_id": provider_id,
                "ok": ok,
                "latency_ms": round(elapsed, 2),
                "error": error,
                "health": provider.health.to_dict(),
            }

    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Ping every registered provider and return their health snapshots."""
        with self._lock:
            ids = list(self._providers.keys())
        results: Dict[str, Dict[str, Any]] = {}
        for pid in ids:
            results[pid] = self.ping_provider(pid)
        return results

    def _apply_health_result(
        self,
        provider: ModelProvider,
        success: bool,
        latency_ms: float,
        error: str = "",
    ) -> None:
        """Update provider health based on a ping or request result."""
        health = provider.health
        samples = self._latency_samples.get(provider.provider_id)
        if samples is not None:
            samples.append(latency_ms)
            health.avg_latency_ms = sum(samples) / len(samples)
            if len(samples) >= 20:
                sorted_samples = sorted(samples)
                health.p99_latency_ms = sorted_samples[
                    int(len(sorted_samples) * 0.99)
                ]
        health.last_check_ts = time.time()
        if success:
            health.last_success_ts = time.time()
            health.consecutive_successes += 1
            health.consecutive_failures = 0
            health.last_error = ""
            if health.status == ProviderStatus.RATE_LIMITED:
                health.status = ProviderStatus.ACTIVE
            elif health.status == ProviderStatus.DEGRADED and health.consecutive_successes >= 3:
                health.status = ProviderStatus.ACTIVE
            else:
                health.status = ProviderStatus.ACTIVE
        else:
            health.last_failure_ts = time.time()
            health.consecutive_failures += 1
            health.consecutive_successes = 0
            health.last_error = error
            if health.consecutive_failures >= self._OFFLINE_FAILURE_THRESHOLD:
                health.status = ProviderStatus.OFFLINE
            elif health.consecutive_failures >= self._DEGRADED_FAILURE_THRESHOLD:
                health.status = ProviderStatus.DEGRADED
        total = health.consecutive_successes + health.consecutive_failures
        if total > 0:
            health.error_rate = health.consecutive_failures / total
            health.uptime_pct = (
                health.consecutive_successes / total * 100.0
            )

    def _mark_rate_limited(self, provider_id: str) -> None:
        """Mark a provider as rate-limited based on the bucket state."""
        with self._lock:
            provider = self._providers.get(provider_id)
            if provider is not None:
                provider.health.status = ProviderStatus.RATE_LIMITED
                provider.health.last_check_ts = time.time()

    # ------------------------------------------------------------------
    # Rate Limiting
    # ------------------------------------------------------------------

    def set_rate_limit(self, provider_id: str, rpm: int, tpm: int = 0) -> bool:
        """Set the per-minute request and token limits for a provider."""
        with self._lock:
            provider = self._providers.get(provider_id)
            if provider is None:
                return False
            provider.rate_limit_rpm = rpm
            provider.rate_limit_tpm = tpm if tpm > 0 else provider.rate_limit_tpm
            limiter = self._rate_limiters.get(provider_id)
            if limiter is None:
                limiter = _TokenBucket(rate=rpm / 60.0, capacity=float(rpm))
                self._rate_limiters[provider_id] = limiter
            else:
                limiter.update(rate=rpm / 60.0, capacity=float(rpm))
            logger.info("Rate limit for %s set to %d rpm", provider_id, rpm)
            return True

    def get_rate_limit(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Return the rate-limit configuration and current bucket state."""
        with self._lock:
            provider = self._providers.get(provider_id)
            if provider is None:
                return None
            limiter = self._rate_limiters.get(provider_id)
            bucket = limiter.snapshot() if limiter else {}
            return {
                "provider_id": provider_id,
                "rate_limit_rpm": provider.rate_limit_rpm,
                "rate_limit_tpm": provider.rate_limit_tpm,
                "bucket": bucket,
            }

    # ------------------------------------------------------------------
    # Response Cache
    # ------------------------------------------------------------------

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return statistics about the response cache."""
        return self._cache.stats()

    def clear_cache(self) -> int:
        """Clear the response cache and return the number of evicted entries."""
        return self._cache.clear()

    def set_cache_enabled(self, enabled: bool) -> None:
        """Enable or disable the response cache."""
        self._cache.set_enabled(enabled)
        logger.info("Response cache %s", "enabled" if enabled else "disabled")

    # ------------------------------------------------------------------
    # Fallback Chains
    # ------------------------------------------------------------------

    def set_fallback_chain(self, provider_id: str, model_ids: List[str]) -> bool:
        """Define the ordered fallback model list for a provider."""
        with self._lock:
            if provider_id not in self._providers:
                return False
            self._fallback_chains[provider_id] = list(model_ids)
            logger.info(
                "Fallback chain for %s set to %s", provider_id, model_ids
            )
            return True

    def get_fallback_chain(self, provider_id: str) -> List[str]:
        """Return the fallback model list for a provider."""
        with self._lock:
            return list(self._fallback_chains.get(provider_id, []))

    # ------------------------------------------------------------------
    # Task-to-Model Mapping
    # ------------------------------------------------------------------

    def set_task_model_mapping(self, task_type: TaskType, model_id: str) -> bool:
        """Bind a game-dev task type to a specific model id."""
        with self._lock:
            if model_id not in self._models:
                return False
            self._task_model_map[task_type] = model_id
            logger.info(
                "Task %s mapped to model %s", task_type.value, model_id
            )
            return True

    def get_task_model_mapping(self, task_type: TaskType) -> Optional[str]:
        """Return the model id bound to a task type, if any."""
        with self._lock:
            return self._task_model_map.get(task_type)

    # ------------------------------------------------------------------
    # Usage & Cost Tracking
    # ------------------------------------------------------------------

    def get_usage_stats(self, provider_id: Optional[str] = None) -> Dict[str, Any]:
        """Return usage statistics for a provider, or globally if None."""
        with self._lock:
            if provider_id is not None:
                stats = self._usage_stats.get(provider_id)
                return stats.to_dict() if stats else {}
            return self._global_stats.to_dict()

    def get_cost_report(self) -> Dict[str, Any]:
        """Return a per-provider cost report."""
        with self._lock:
            report: Dict[str, Any] = {}
            total_cost = 0.0
            total_tokens = 0
            for pid, stats in self._usage_stats.items():
                report[pid] = {
                    "total_cost": round(stats.total_cost, 6),
                    "total_input_tokens": stats.total_input_tokens,
                    "total_output_tokens": stats.total_output_tokens,
                    "requests": stats.total_requests,
                }
                total_cost += stats.total_cost
                total_tokens += stats.total_input_tokens + stats.total_output_tokens
            report["_total"] = {
                "total_cost": round(total_cost, 6),
                "total_tokens": total_tokens,
            }
            return report

    def reset_stats(self) -> None:
        """Reset all usage and cost statistics without removing providers."""
        with self._lock:
            for pid in self._usage_stats:
                self._usage_stats[pid] = UsageStats()
            self._global_stats = UsageStats()

    # ------------------------------------------------------------------
    # Aggregate Stats & Reset
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return a comprehensive snapshot of the router's state."""
        with self._lock:
            return {
                "providers": len(self._providers),
                "models": len(self._models),
                "routing_rules": len(self._routing_rules),
                "task_mappings": len(self._task_model_map),
                "api_keys_configured": sum(
                    1 for e in self._api_keys.values() if e.key_value
                ),
                "simulation_mode": self._simulation_mode,
                "routing_strategy": self._routing_strategy.value,
                "global_usage": self._global_stats.to_dict(),
                "cache": self._cache.stats(),
                "health": {
                    pid: p.health.to_dict()
                    for pid, p in self._providers.items()
                },
            }

    def reset(self) -> None:
        """Reset the router to its initial seeded state."""
        with self._lock:
            self._providers.clear()
            self._models.clear()
            self._routing_rules.clear()
            self._task_model_map.clear()
            self._fallback_chains.clear()
            self._api_keys.clear()
            self._rate_limiters.clear()
            self._cache.clear()
            self._usage_stats.clear()
            self._global_stats = UsageStats()
            self._latency_samples.clear()
            self._simulation_mode = False
            self._routing_strategy = RoutingStrategy.CAPABILITY_MATCH
            self._seeded = False
            self._seed_default_data()
            logger.info("LLMRouter reset to seeded defaults")

    # ------------------------------------------------------------------
    # Internal Recording Helpers
    # ------------------------------------------------------------------

    def _record_cache_hit(self, request: ModelRequest) -> None:
        with self._lock:
            self._global_stats.cache_hits += 1
            self._global_stats.cache_misses += 0
            if request.provider_id:
                stats = self._usage_stats.get(request.provider_id)
                if stats is not None:
                    stats.cache_hits += 1

    def _record_success(
        self,
        provider_id: str,
        model_id: str,
        request: ModelRequest,
        response: ModelResponse,
        latency_ms: float,
        fallback_used: bool,
    ) -> None:
        with self._lock:
            self._global_stats.total_requests += 1
            self._global_stats.successful_requests += 1
            self._global_stats.total_input_tokens += response.input_tokens
            self._global_stats.total_output_tokens += response.output_tokens
            self._global_stats.total_cost += response.cost
            self._global_stats.total_latency_ms += latency_ms
            if fallback_used:
                self._global_stats.fallback_count += 1
            if response.simulated:
                self._global_stats.simulated_count += 1
            task_key = request.task_type.value
            self._global_stats.by_task_type[task_key] = (
                self._global_stats.by_task_type.get(task_key, 0) + 1
            )

            stats = self._usage_stats.setdefault(provider_id, UsageStats())
            stats.total_requests += 1
            stats.successful_requests += 1
            stats.total_input_tokens += response.input_tokens
            stats.total_output_tokens += response.output_tokens
            stats.total_cost += response.cost
            stats.total_latency_ms += latency_ms
            if fallback_used:
                stats.fallback_count += 1
            if response.simulated:
                stats.simulated_count += 1
            stats.by_task_type[task_key] = (
                stats.by_task_type.get(task_key, 0) + 1
            )

            provider = self._providers.get(provider_id)
            if provider is not None:
                self._apply_health_result(provider, True, latency_ms)

    def _record_failure(
        self,
        provider_id: str,
        model_id: str,
        request: ModelRequest,
        latency_ms: float,
        exc: BaseException,
    ) -> None:
        with self._lock:
            self._global_stats.total_requests += 1
            self._global_stats.failed_requests += 1
            self._global_stats.total_latency_ms += latency_ms
            stats = self._usage_stats.setdefault(provider_id, UsageStats())
            stats.total_requests += 1
            stats.failed_requests += 1
            stats.total_latency_ms += latency_ms
            provider = self._providers.get(provider_id)
            if provider is not None:
                self._apply_health_result(
                    provider, False, latency_ms, str(exc)
                )

    # ------------------------------------------------------------------
    # Cost & Token Estimation
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate (~4 chars per token)."""
        return max(1, len(text) // 4)

    @staticmethod
    def _compute_cost(
        cap: ModelCapability,
        input_tokens: int,
        output_tokens: int,
        request: ModelRequest,
    ) -> float:
        """Compute the estimated cost of a request."""
        input_cost = (input_tokens / 1000.0) * cap.cost_per_1k_input
        output_cost = (output_tokens / 1000.0) * cap.cost_per_1k_output
        return round(input_cost + output_cost, 6)

    def estimate_cost(
        self, model_id: str, input_tokens: int, output_tokens: int
    ) -> Optional[CostEstimate]:
        """Return a CostEstimate for a model and token counts."""
        with self._lock:
            entry = self._models.get(model_id)
            if entry is None:
                return None
            provider_id, cap = entry
            input_cost = (input_tokens / 1000.0) * cap.cost_per_1k_input
            output_cost = (output_tokens / 1000.0) * cap.cost_per_1k_output
            return CostEstimate(
                model_id=model_id,
                provider_id=provider_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                input_cost=round(input_cost, 6),
                output_cost=round(output_cost, 6),
                total_cost=round(input_cost + output_cost, 6),
            )

    # ------------------------------------------------------------------
    # Error Response Helper
    # ------------------------------------------------------------------

    def _error_response(self, request: ModelRequest, message: str) -> ModelResponse:
        """Build an error ModelResponse and record it globally."""
        with self._lock:
            self._global_stats.total_requests += 1
            self._global_stats.failed_requests += 1
        logger.error("Request %s failed: %s", request.request_id, message)
        return ModelResponse(
            request_id=request.request_id,
            content="",
            finish_reason="error",
            error=message,
            metadata={"task_type": request.task_type.value},
        )

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Pre-register all major providers, models, rate limits, and the
        default game-development task-to-model mappings."""
        if self._seeded:
            return
        self._seeded = True

        # --- Text & multimodal LLM providers ------------------------------
        self._seed_openai()
        self._seed_anthropic()
        self._seed_google()
        self._seed_meta()
        self._seed_mistral()
        self._seed_cohere()
        self._seed_deepseek()
        self._seed_qwen()
        self._seed_ollama()
        self._seed_huggingface()
        self._seed_together()
        self._seed_groq()
        self._seed_fireworks()
        self._seed_xai()
        self._seed_perplexity()
        self._seed_ai21()
        self._seed_fal()
        self._seed_deepinfra()
        self._seed_nvidia()
        self._seed_cerebras()
        self._seed_bedrock()
        self._seed_azure()
        self._seed_openrouter()
        self._seed_zhipu()
        self._seed_moonshot()
        self._seed_minimax()
        self._seed_doubao()
        self._seed_ernie()
        self._seed_stepfun()
        self._seed_lambda()
        self._seed_replicate_models()
        self._seed_assemblyai()
        self._seed_deepgram()
        self._seed_playht()
        self._seed_cartesia()
        self._seed_yi()
        self._seed_baichuan()
        self._seed_siliconflow()
        self._seed_modelscope()
        self._seed_predibase()
        self._seed_octoai()
        self._seed_leonardo()
        self._seed_morph()
        self._seed_viggle()
        self._seed_did()
        self._seed_heygen()
        self._seed_synthesia()
        self._seed_code_providers()

        # --- Generation providers -----------------------------------------
        self._seed_image_providers()
        self._seed_video_providers()
        self._seed_audio_providers()
        self._seed_3d_providers()
        self._seed_animation_providers()
        self._seed_more_3d_providers()
        self._seed_more_animation_providers()
        self._seed_more_audio_providers()
        self._seed_more_video_providers()
        self._seed_embedding_providers()

        # --- Task-to-model mappings ---------------------------------------
        self._seed_task_mappings()

        # --- Default fallback chains --------------------------------------
        self._seed_fallback_chains()

        logger.info(
            "Seed data loaded: %d providers, %d models",
            len(self._providers),
            len(self._models),
        )

    def _seed_openai(self) -> None:
        self.register_provider(
            provider_id="openai",
            name="OpenAI",
            vendor="OpenAI",
            endpoints=[ModelEndpoint(url="https://api.openai.com/v1", region="us")],
            api_key_env="OPENAI_API_KEY",
            rate_limit_rpm=500,
            rate_limit_tpm=1_000_000,
        )
        models = [
            ("gpt-4o", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL], 128_000, 16_384, 0.03, 0.06, 0.95, "low", True, True, True),
            ("gpt-4o-mini", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL], 128_000, 16_384, 0.00015, 0.0006, 0.88, "very_low", True, True, True),
            ("gpt-4.1", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL], 1_000_000, 32_768, 0.005, 0.015, 0.96, "low", True, True, True),
            ("gpt-4.1-mini", [ModelType.TEXT, ModelType.VISION], 1_000_000, 32_768, 0.0004, 0.0016, 0.9, "very_low", True, True, True),
            ("gpt-4-turbo", [ModelType.TEXT, ModelType.VISION], 128_000, 4_096, 0.01, 0.03, 0.9, "low", True, True, True),
            ("o1", [ModelType.TEXT, ModelType.REASONING], 200_000, 100_000, 0.015, 0.06, 0.97, "high", False, False, False),
            ("o1-mini", [ModelType.TEXT, ModelType.REASONING], 128_000, 65_536, 0.0011, 0.0044, 0.92, "medium", False, False, False),
            ("o3", [ModelType.TEXT, ModelType.REASONING], 200_000, 100_000, 0.015, 0.06, 0.98, "high", False, False, False),
            ("o3-mini", [ModelType.TEXT, ModelType.REASONING], 200_000, 100_000, 0.0011, 0.0044, 0.95, "medium", True, True, False),
            ("dall-e-3", [ModelType.IMAGE_GEN], 4_000, 1, 0.04, 0.0, 0.85, "medium", False, False, False),
            ("tts-1", [ModelType.TTS], 4_096, 4_096, 0.015, 0.0, 0.85, "very_low", False, False, False),
            ("tts-1-hd", [ModelType.TTS], 4_096, 4_096, 0.03, 0.0, 0.9, "low", False, False, False),
            ("text-embedding-3-large", [ModelType.EMBEDDING], 8_191, 8_191, 0.00013, 0.0, 0.92, "low", False, False, False),
            ("text-embedding-3-small", [ModelType.EMBEDDING], 8_191, 8_191, 0.00002, 0.0, 0.85, "low", False, False, False),
            ("whisper-1", [ModelType.STT], 0, 0, 0.006, 0.0, 0.9, "medium", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "openai",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["openai", mid],
                ),
            )

    def _seed_anthropic(self) -> None:
        self.register_provider(
            provider_id="anthropic",
            name="Anthropic",
            vendor="Anthropic",
            endpoints=[ModelEndpoint(url="https://api.anthropic.com", region="us")],
            api_key_env="ANTHROPIC_API_KEY",
            rate_limit_rpm=300,
            rate_limit_tpm=500_000,
        )
        models = [
            ("claude-3-5-sonnet", [ModelType.TEXT, ModelType.VISION], 200_000, 8_192, 0.003, 0.015, 0.95, "low", True, True, True),
            ("claude-3-5-sonnet-20241022", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL], 200_000, 8_192, 0.003, 0.015, 0.96, "low", True, True, True),
            ("claude-3-5-haiku", [ModelType.TEXT, ModelType.VISION], 200_000, 8_192, 0.0008, 0.004, 0.89, "very_low", True, True, True),
            ("claude-3-7-sonnet", [ModelType.TEXT, ModelType.VISION, ModelType.REASONING], 200_000, 16_384, 0.003, 0.015, 0.97, "low", True, True, True),
            ("claude-3-opus", [ModelType.TEXT, ModelType.REASONING], 200_000, 4_096, 0.015, 0.075, 0.94, "medium", True, True, False),
            ("claude-3-haiku", [ModelType.TEXT], 200_000, 4_096, 0.00025, 0.00125, 0.85, "low", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "anthropic",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["anthropic", mid],
                ),
            )

    def _seed_google(self) -> None:
        self.register_provider(
            provider_id="google",
            name="Google AI",
            vendor="Google",
            endpoints=[ModelEndpoint(url="https://generativelanguage.googleapis.com", region="us")],
            api_key_env="GOOGLE_API_KEY",
            rate_limit_rpm=300,
            rate_limit_tpm=1_000_000,
        )
        models = [
            ("gemini-2.5-pro", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL, ModelType.REASONING], 2_000_000, 8_192, 0.00125, 0.005, 0.96, "medium", True, True, True),
            ("gemini-2.0-flash", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL], 1_000_000, 8_192, 0.000075, 0.0003, 0.9, "low", True, True, True),
            ("gemini-2.0-flash-lite", [ModelType.TEXT, ModelType.VISION], 1_000_000, 8_192, 0.0000375, 0.00015, 0.82, "very_low", True, True, True),
            ("gemini-1.5-pro", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL], 2_000_000, 8_192, 0.00125, 0.005, 0.93, "medium", True, True, True),
            ("gemini-1.5-flash", [ModelType.TEXT, ModelType.VISION], 1_000_000, 8_192, 0.0000375, 0.00015, 0.85, "very_low", True, True, True),
            ("imagen-3", [ModelType.IMAGE_GEN], 0, 0, 0.04, 0.0, 0.9, "medium", False, False, False),
            ("text-embedding-004", [ModelType.EMBEDDING], 2_048, 2_048, 0.000025, 0.0, 0.88, "low", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "google",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    supports_audio_input=(mid == "gemini-1.5-pro"),
                    supports_video_input=(mid == "gemini-1.5-pro"),
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["google", mid],
                ),
            )

    def _seed_meta(self) -> None:
        self.register_provider(
            provider_id="meta",
            name="Meta AI",
            vendor="Meta",
            endpoints=[ModelEndpoint(url="https://api.meta.ai", region="us")],
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("llama-3.1-405b", [ModelType.TEXT, ModelType.REASONING], 128_000, 4_096, 0.005, 0.015, 0.92, "medium", True, False, False),
            ("llama-3.1-70b", [ModelType.TEXT], 128_000, 4_096, 0.0009, 0.0009, 0.88, "low", True, False, False),
            ("llama-3.2-vision", [ModelType.TEXT, ModelType.VISION], 128_000, 4_096, 0.0015, 0.0015, 0.87, "medium", True, False, True),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "meta",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["meta", mid],
                ),
            )

    def _seed_mistral(self) -> None:
        self.register_provider(
            provider_id="mistral",
            name="Mistral AI",
            vendor="Mistral",
            endpoints=[ModelEndpoint(url="https://api.mistral.ai/v1", region="eu")],
            api_key_env="MISTRAL_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("mistral-large-2", [ModelType.TEXT, ModelType.REASONING], 128_000, 4_096, 0.002, 0.006, 0.9, "low", True, True, False),
            ("codestral", [ModelType.TEXT, ModelType.CODE], 32_000, 4_096, 0.001, 0.003, 0.88, "low", True, True, False),
            ("mistral-large-2411", [ModelType.TEXT], 128_000, 8_192, 0.002, 0.006, 0.92, "low", True, True, False),
            ("pixtral-12b-2409", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL], 128_000, 8_192, 0.00015, 0.0006, 0.85, "low", True, True, True),
            ("codestral-2501", [ModelType.TEXT, ModelType.CODE], 256_000, 8_192, 0.0003, 0.0009, 0.89, "low", True, True, False),
            ("open-mixtral-8x22b", [ModelType.TEXT], 64_000, 4_096, 0.002, 0.006, 0.86, "medium", True, True, False),
            ("mistral-nemo", [ModelType.TEXT], 128_000, 4_096, 0.0001, 0.0003, 0.8, "low", True, True, False),
            ("ministral-8b", [ModelType.TEXT], 128_000, 4_096, 0.0001, 0.0003, 0.78, "very_low", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "mistral",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["mistral", mid],
                ),
            )

    def _seed_cohere(self) -> None:
        self.register_provider(
            provider_id="cohere",
            name="Cohere",
            vendor="Cohere",
            endpoints=[ModelEndpoint(url="https://api.cohere.ai/v1", region="us")],
            api_key_env="COHERE_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("command-r-plus", [ModelType.TEXT], 128_000, 4_096, 0.0025, 0.01, 0.88, "medium", True, True, False),
            ("embed-v3", [ModelType.EMBEDDING], 512, 512, 0.0001, 0.0, 0.9, "low", False, False, False),
            ("command-r-plus-08-2024", [ModelType.TEXT], 128_000, 4_096, 0.0025, 0.01, 0.9, "medium", True, True, False),
            ("command-r-08-2024", [ModelType.TEXT], 128_000, 4_096, 0.00015, 0.0006, 0.85, "low", True, True, False),
            ("command-r7b-12-2024", [ModelType.TEXT], 128_000, 4_096, 0.0000375, 0.00015, 0.78, "very_low", True, True, False),
            ("embed-v4.0", [ModelType.EMBEDDING], 128_000, 128_000, 0.0001, 0.0, 0.92, "low", False, False, False),
            ("aya-expanse-32b", [ModelType.TEXT, ModelType.MULTIMODAL], 128_000, 4_096, 0.00015, 0.0006, 0.84, "low", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "cohere",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["cohere", mid],
                ),
            )

    def _seed_deepseek(self) -> None:
        self.register_provider(
            provider_id="deepseek",
            name="DeepSeek",
            vendor="DeepSeek",
            endpoints=[ModelEndpoint(url="https://api.deepseek.com/v1", region="asia")],
            api_key_env="DEEPSEEK_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("deepseek-v3", [ModelType.TEXT, ModelType.CODE], 128_000, 8_192, 0.00027, 0.0011, 0.9, "low", True, True, False),
            ("deepseek-r1", [ModelType.TEXT, ModelType.REASONING], 128_000, 32_000, 0.00055, 0.0022, 0.93, "medium", True, False, False),
            ("deepseek-r1-distill-qwen-32b", [ModelType.TEXT, ModelType.REASONING], 128_000, 4_096, 0.00014, 0.00028, 0.88, "medium", True, False, False),
            ("deepseek-coder-v2", [ModelType.TEXT, ModelType.CODE], 128_000, 4_096, 0.00014, 0.00028, 0.87, "low", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "deepseek",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["deepseek", mid],
                ),
            )

    def _seed_qwen(self) -> None:
        self.register_provider(
            provider_id="qwen",
            name="Qwen",
            vendor="Alibaba",
            endpoints=[ModelEndpoint(url="https://dashscope.aliyuncs.com", region="asia")],
            api_key_env="DASHSCOPE_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("qwen-2.5-max", [ModelType.TEXT], 128_000, 8_192, 0.002, 0.006, 0.9, "low", True, True, False),
            ("qwq", [ModelType.TEXT, ModelType.REASONING], 32_000, 4_096, 0.0015, 0.005, 0.91, "medium", True, False, False),
            ("qwen-vl-max", [ModelType.TEXT, ModelType.VISION], 32_000, 4_096, 0.002, 0.006, 0.88, "medium", True, False, True),
            ("qwen-max", [ModelType.TEXT], 32_000, 8_192, 0.002, 0.006, 0.9, "low", True, True, False),
            ("qwen3-235b-a22b", [ModelType.TEXT], 128_000, 8_192, 0.001, 0.003, 0.9, "medium", True, True, False),
            ("qwen3-32b", [ModelType.TEXT], 128_000, 8_192, 0.0003, 0.0006, 0.85, "low", True, True, False),
            ("qwen-coder-plus", [ModelType.TEXT, ModelType.CODE], 128_000, 8_192, 0.0007, 0.002, 0.88, "low", True, True, False),
            ("qwen2.5-omni-7b", [ModelType.MULTIMODAL], 32_000, 4_096, 0.0003, 0.0006, 0.8, "low", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "qwen",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["qwen", mid],
                ),
            )

    def _seed_ollama(self) -> None:
        self.register_provider(
            provider_id="ollama",
            name="Ollama (local open-source)",
            vendor="Ollama",
            endpoints=[ModelEndpoint(url="http://localhost:11434", region="local")],
            rate_limit_rpm=1000,
            rate_limit_tpm=10_000_000,
        )
        models = [
            ("llama3", [ModelType.TEXT], 8_000, 4_096, 0.0, 0.0, 0.8, "low", True, False, False),
            ("qwen2", [ModelType.TEXT], 32_000, 4_096, 0.0, 0.0, 0.8, "low", True, False, False),
            ("mistral", [ModelType.TEXT], 32_000, 4_096, 0.0, 0.0, 0.78, "low", True, False, False),
            ("phi3", [ModelType.TEXT], 4_000, 4_096, 0.0, 0.0, 0.7, "low", True, False, False),
            ("gemma2", [ModelType.TEXT], 8_000, 4_096, 0.0, 0.0, 0.78, "low", True, False, False),
            ("codellama", [ModelType.TEXT, ModelType.CODE], 16_000, 4_096, 0.0, 0.0, 0.78, "low", True, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "ollama",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["ollama", "local", mid],
                ),
            )

    def _seed_huggingface(self) -> None:
        """Seed HuggingFace Inference API — open-source model hub."""
        self.register_provider(
            provider_id="huggingface",
            name="Hugging Face",
            vendor="Hugging Face",
            endpoints=[ModelEndpoint(url="https://api-inference.huggingface.co", region="global")],
            api_key_env="HF_API_KEY",
            rate_limit_rpm=300,
            rate_limit_tpm=1_000_000,
        )
        models = [
            ("meta-llama/Llama-3.1-70B-Instruct", [ModelType.TEXT], 128_000, 4_096, 0.0, 0.0, 0.88, "medium", True, False, False),
            ("meta-llama/Llama-3.1-8B-Instruct", [ModelType.TEXT], 128_000, 4_096, 0.0, 0.0, 0.78, "low", True, False, False),
            ("mistralai/Mistral-7B-Instruct-v0.3", [ModelType.TEXT], 32_000, 4_096, 0.0, 0.0, 0.78, "low", True, False, False),
            ("mistralai/Mixtral-8x7B-Instruct-v0.1", [ModelType.TEXT], 32_000, 4_096, 0.0, 0.0, 0.85, "medium", True, False, False),
            ("Qwen/Qwen2.5-72B-Instruct", [ModelType.TEXT], 128_000, 8_192, 0.0, 0.0, 0.87, "medium", True, False, False),
            ("Qwen/Qwen2.5-Coder-32B-Instruct", [ModelType.TEXT, ModelType.CODE], 128_000, 8_192, 0.0, 0.0, 0.85, "medium", True, False, False),
            ("google/gemma-2-9b-it", [ModelType.TEXT], 8_000, 4_096, 0.0, 0.0, 0.78, "low", True, False, False),
            ("stabilityai/stable-diffusion-xl-base-1.0", [ModelType.IMAGE_GEN], 0, 0, 0.0, 0.0, 0.85, "high", False, False, False),
            ("black-forest-labs/FLUX.1-dev", [ModelType.IMAGE_GEN], 0, 0, 0.0, 0.0, 0.9, "high", False, False, False),
            ("black-forest-labs/FLUX.1-schnell", [ModelType.IMAGE_GEN], 0, 0, 0.0, 0.0, 0.85, "medium", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "huggingface",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["huggingface", "open-source", mid.split("/")[-1]],
                ),
            )

    def _seed_together(self) -> None:
        """Seed Together AI — open-source model serving at scale."""
        self.register_provider(
            provider_id="together",
            name="Together AI",
            vendor="Together AI",
            endpoints=[ModelEndpoint(url="https://api.together.xyz/v1", region="us")],
            api_key_env="TOGETHER_API_KEY",
            rate_limit_rpm=600,
            rate_limit_tpm=1_000_000,
        )
        models = [
            ("meta-llama/Llama-3.3-70B-Instruct-Turbo", [ModelType.TEXT], 128_000, 8_192, 0.0009, 0.0009, 0.89, "low", True, True, False),
            ("meta-llama/Llama-3.3-70B-Instruct", [ModelType.TEXT], 128_000, 4_096, 0.0006, 0.0006, 0.87, "medium", True, True, False),
            ("meta-llama/Llama-Vision-Free", [ModelType.TEXT, ModelType.VISION], 8_000, 4_096, 0.0, 0.0, 0.8, "medium", True, False, True),
            ("Qwen/Qwen2.5-72B-Instruct-Turbo", [ModelType.TEXT], 128_000, 8_192, 0.0008, 0.0008, 0.88, "low", True, True, False),
            ("Qwen/Qwen2.5-Coder-32B-Instruct", [ModelType.TEXT, ModelType.CODE], 128_000, 8_192, 0.0005, 0.0005, 0.85, "low", True, False, False),
            ("deepseek-ai/DeepSeek-V3", [ModelType.TEXT, ModelType.REASONING], 64_000, 8_192, 0.0007, 0.0007, 0.9, "low", True, True, False),
            ("stabilityai/stable-diffusion-xl-base-1.0", [ModelType.IMAGE_GEN], 0, 0, 0.0, 0.0, 0.85, "medium", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "together",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["together", "open-source", mid.split("/")[-1]],
                ),
            )

    def _seed_groq(self) -> None:
        """Seed Groq — ultra-fast LLM inference."""
        self.register_provider(
            provider_id="groq",
            name="Groq",
            vendor="Groq",
            endpoints=[ModelEndpoint(url="https://api.groq.com/openai/v1", region="us")],
            api_key_env="GROQ_API_KEY",
            rate_limit_rpm=1200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("llama-3.3-70b-versatile", [ModelType.TEXT], 128_000, 8_192, 0.0006, 0.0006, 0.88, "ultra", True, True, False),
            ("llama-3.1-8b-instant", [ModelType.TEXT], 128_000, 8_192, 0.0001, 0.0001, 0.78, "ultra", True, True, False),
            ("llama-3.1-70b-versatile", [ModelType.TEXT], 128_000, 8_192, 0.0006, 0.0006, 0.87, "ultra", True, True, False),
            ("mixtral-8x7b-32768", [ModelType.TEXT], 32_768, 4_096, 0.0003, 0.0003, 0.84, "ultra", True, False, False),
            ("gemma2-9b-it", [ModelType.TEXT], 8_192, 4_096, 0.0002, 0.0002, 0.78, "ultra", True, False, False),
            ("llama-3.2-90b-vision-preview", [ModelType.TEXT, ModelType.VISION], 128_000, 4_096, 0.0007, 0.0007, 0.85, "ultra", True, False, True),
            ("llama-3.2-11b-vision-preview", [ModelType.TEXT, ModelType.VISION], 128_000, 4_096, 0.0002, 0.0002, 0.78, "ultra", True, False, True),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "groq",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["groq", "fast", mid],
                ),
            )

    def _seed_fireworks(self) -> None:
        """Seed Fireworks AI — open-source model serving."""
        self.register_provider(
            provider_id="fireworks",
            name="Fireworks AI",
            vendor="Fireworks AI",
            endpoints=[ModelEndpoint(url="https://api.fireworks.ai/inference/v1", region="us")],
            api_key_env="FIREWORKS_API_KEY",
            rate_limit_rpm=600,
            rate_limit_tpm=1_000_000,
        )
        models = [
            ("accounts/fireworks/models/llama-v3p3-70b-instruct", [ModelType.TEXT], 128_000, 8_192, 0.0009, 0.0009, 0.88, "low", True, True, False),
            ("accounts/fireworks/models/qwen2p5-72b-instruct", [ModelType.TEXT], 128_000, 8_192, 0.0009, 0.0009, 0.87, "low", True, True, False),
            ("accounts/fireworks/models/qwen2p5-coder-32b-instruct", [ModelType.TEXT, ModelType.CODE], 128_000, 8_192, 0.0005, 0.0005, 0.85, "low", True, False, False),
            ("accounts/fireworks/models/deepseek-v3", [ModelType.TEXT, ModelType.REASONING], 64_000, 8_192, 0.0008, 0.0008, 0.9, "low", True, True, False),
            ("accounts/fireworks/models/stable-diffusion-xl-1024-v1-0", [ModelType.IMAGE_GEN], 0, 0, 0.0, 0.0, 0.85, "medium", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "fireworks",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["fireworks", "open-source", mid.split("/")[-1]],
                ),
            )

    def _seed_xai(self) -> None:
        """Seed xAI — Grok series with vision support."""
        self.register_provider(
            provider_id="xai",
            name="xAI",
            vendor="xAI",
            endpoints=[ModelEndpoint(url="https://api.x.ai/v1", region="us")],
            api_key_env="XAI_API_KEY",
            rate_limit_rpm=60,
            rate_limit_tpm=200_000,
        )
        models = [
            ("grok-2", [ModelType.TEXT, ModelType.REASONING], 131_072, 4_096, 0.002, 0.01, 0.9, "medium", True, True, False),
            ("grok-2-vision", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL], 131_072, 4_096, 0.002, 0.01, 0.89, "medium", True, True, True),
            ("grok-2-mini", [ModelType.TEXT], 131_072, 4_096, 0.001, 0.004, 0.82, "low", True, True, False),
            ("grok-beta", [ModelType.TEXT, ModelType.REASONING], 131_072, 4_096, 0.005, 0.015, 0.88, "medium", True, False, False),
            ("grok-3", [ModelType.TEXT], 131_072, 8_192, 0.005, 0.015, 0.93, "medium", True, True, False),
            ("grok-3-mini", [ModelType.TEXT, ModelType.REASONING], 131_072, 8_192, 0.0003, 0.001, 0.88, "low", True, True, False),
            ("grok-3-vision", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL], 131_072, 8_192, 0.005, 0.015, 0.92, "medium", True, True, True),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "xai",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["xai", "grok", mid],
                ),
            )

    def _seed_perplexity(self) -> None:
        """Seed Perplexity — online LLMs with web search capability."""
        self.register_provider(
            provider_id="perplexity",
            name="Perplexity",
            vendor="Perplexity AI",
            endpoints=[ModelEndpoint(url="https://api.perplexity.ai", region="us")],
            api_key_env="PERPLEXITY_API_KEY",
            rate_limit_rpm=50,
            rate_limit_tpm=100_000,
        )
        models = [
            ("llama-3.1-sonar-large-128k-online", [ModelType.TEXT], 127_072, 8_192, 0.001, 0.001, 0.85, "medium", True, False, False),
            ("llama-3.1-sonar-small-128k-online", [ModelType.TEXT], 127_072, 8_192, 0.0002, 0.0002, 0.78, "low", True, False, False),
            ("llama-3.1-sonar-huge-128k-online", [ModelType.TEXT, ModelType.REASONING], 127_072, 8_192, 0.005, 0.005, 0.88, "medium", True, False, False),
            ("sonar-reasoning-pro", [ModelType.TEXT, ModelType.REASONING], 127_072, 8_192, 0.002, 0.008, 0.9, "medium", True, False, False),
            ("sonar-reasoning", [ModelType.TEXT, ModelType.REASONING], 127_072, 8_192, 0.001, 0.005, 0.87, "low", True, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "perplexity",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["perplexity", "online", "web-search", mid.split("-")[-1]],
                ),
            )

    def _seed_ai21(self) -> None:
        """Seed AI21 Labs — Jamba series with ultra-long context."""
        self.register_provider(
            provider_id="ai21",
            name="AI21 Labs",
            vendor="AI21 Labs",
            endpoints=[ModelEndpoint(url="https://api.ai21.com/studio/v1", region="us")],
            api_key_env="AI21_API_KEY",
            rate_limit_rpm=50,
            rate_limit_tpm=100_000,
        )
        models = [
            ("jamba-1.5-large", [ModelType.TEXT], 256_000, 4_096, 0.002, 0.008, 0.86, "medium", True, True, False),
            ("jamba-1.5-mini", [ModelType.TEXT], 256_000, 4_096, 0.0003, 0.0006, 0.78, "low", True, True, False),
            ("jamba-instruct", [ModelType.TEXT], 256_000, 4_096, 0.0005, 0.0007, 0.8, "low", True, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "ai21",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["ai21", "jamba", "long-context", mid.split("-")[-1]],
                ),
            )

    def _seed_fal(self) -> None:
        """Seed Fal.ai — fast image and video generation."""
        self.register_provider(
            provider_id="fal",
            name="Fal.ai",
            vendor="Fal AI",
            endpoints=[ModelEndpoint(url="https://fal.run", region="us")],
            api_key_env="FAL_KEY",
            rate_limit_rpm=100,
            rate_limit_tpm=500_000,
        )
        models = [
            ("fal-ai/flux/dev", [ModelType.IMAGE_GEN], 0, 0, 0.0, 0.0, 0.92, "low", False, False, False),
            ("fal-ai/flux/pro", [ModelType.IMAGE_GEN], 0, 0, 0.0, 0.0, 0.95, "low", False, False, False),
            ("fal-ai/flux/schnell", [ModelType.IMAGE_GEN], 0, 0, 0.0, 0.0, 0.85, "very_low", False, False, False),
            ("fal-ai/aura-sr", [ModelType.IMAGE_GEN], 0, 0, 0.0, 0.0, 0.88, "low", False, False, False),
            ("fal-ai/kling-video", [ModelType.VIDEO_GEN], 0, 0, 0.0, 0.0, 0.87, "high", False, False, False),
            ("fal-ai/luma-dream-machine", [ModelType.VIDEO_GEN], 0, 0, 0.0, 0.0, 0.86, "high", False, False, False),
            ("fal-ai/minimax/video-01", [ModelType.VIDEO_GEN], 0, 0, 0.0, 0.0, 0.84, "high", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "fal",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_image=0.04 if ModelType.IMAGE_GEN in types else 0.0,
                    cost_per_second_video=0.5 if ModelType.VIDEO_GEN in types else 0.0,
                    tags=["fal", "fast", "generation", mid.split("/")[-1]],
                ),
            )

    def _seed_deepinfra(self) -> None:
        """Seed DeepInfra — open-source model hosting platform."""
        self.register_provider(
            provider_id="deepinfra",
            name="DeepInfra",
            vendor="DeepInfra",
            endpoints=[ModelEndpoint(url="https://api.deepinfra.com/v1/openai", region="us")],
            api_key_env="DEEPINFRA_API_KEY",
            rate_limit_rpm=300,
            rate_limit_tpm=500_000,
        )
        models = [
            ("meta-llama/Meta-Llama-3.1-405B-Instruct", [ModelType.TEXT], 128_000, 4_096, 0.0008, 0.0008, 0.92, "medium", True, True, False),
            ("meta-llama/Meta-Llama-3.1-70B-Instruct", [ModelType.TEXT], 128_000, 4_096, 0.0006, 0.0006, 0.88, "low", True, True, False),
            ("meta-llama/Meta-Llama-3.1-8B-Instruct", [ModelType.TEXT], 128_000, 4_096, 0.0001, 0.0001, 0.75, "very_low", True, True, False),
            ("mistralai/Mistral-7B-Instruct-v0.3", [ModelType.TEXT], 32_000, 4_096, 0.0001, 0.0001, 0.76, "very_low", True, False, False),
            ("Qwen/Qwen2.5-72B-Instruct", [ModelType.TEXT, ModelType.CODE], 128_000, 8_192, 0.0006, 0.0006, 0.89, "low", True, True, False),
            ("Qwen/Qwen2.5-Coder-32B-Instruct", [ModelType.TEXT, ModelType.CODE], 128_000, 8_192, 0.0003, 0.0003, 0.86, "low", True, False, False),
            ("deepseek-ai/DeepSeek-V3", [ModelType.TEXT, ModelType.REASONING], 64_000, 8_192, 0.0003, 0.0003, 0.91, "low", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "deepinfra",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["deepinfra", "open-source", mid.split("/")[-1]],
                ),
            )

    def _seed_nvidia(self) -> None:
        """Seed NVIDIA NIM — GPU-accelerated inference for open models."""
        self.register_provider(
            provider_id="nvidia",
            name="NVIDIA NIM",
            vendor="NVIDIA",
            endpoints=[ModelEndpoint(url="https://integrate.api.nvidia.com/v1", region="us")],
            api_key_env="NVIDIA_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("meta/llama-3.1-405b-instruct", [ModelType.TEXT], 128_000, 4_096, 0.0008, 0.0008, 0.92, "low", True, True, False),
            ("meta/llama-3.1-70b-instruct", [ModelType.TEXT], 128_000, 4_096, 0.0006, 0.0006, 0.88, "very_low", True, True, False),
            ("nvidia/llama-3.1-nemotron-70b-instruct", [ModelType.TEXT, ModelType.REASONING], 128_000, 4_096, 0.0006, 0.0006, 0.89, "very_low", True, True, False),
            ("mistralai/mistral-large-2-instruct", [ModelType.TEXT, ModelType.CODE], 128_000, 8_192, 0.002, 0.006, 0.9, "low", True, True, False),
            ("qwen/qwen2.5-coder-32b-instruct", [ModelType.TEXT, ModelType.CODE], 128_000, 8_192, 0.0003, 0.0003, 0.86, "very_low", True, False, False),
            ("google/gemma-2-27b", [ModelType.TEXT], 8_000, 4_096, 0.0002, 0.0002, 0.82, "very_low", True, False, False),
            ("stabilityai/stable-diffusion-xl", [ModelType.IMAGE_GEN], 0, 0, 0.0, 0.0, 0.85, "medium", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "nvidia",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["nvidia", "nim", "gpu", mid.split("/")[-1]],
                ),
            )

    def _seed_cerebras(self) -> None:
        """Seed Cerebras — ultra-fast inference with custom wafer-scale hardware."""
        self.register_provider(
            provider_id="cerebras",
            name="Cerebras",
            vendor="Cerebras Systems",
            endpoints=[ModelEndpoint(url="https://api.cerebras.ai/v1", region="us")],
            api_key_env="CEREBRAS_API_KEY",
            rate_limit_rpm=300,
            rate_limit_tpm=500_000,
        )
        models = [
            ("llama-3.3-70b", [ModelType.TEXT], 128_000, 8_192, 0.0006, 0.0006, 0.89, "ultra_low", True, True, False),
            ("llama-3.1-8b", [ModelType.TEXT], 128_000, 8_192, 0.0001, 0.0001, 0.76, "ultra_low", True, True, False),
            ("qwen-2.5-coder-32b", [ModelType.TEXT, ModelType.CODE], 128_000, 8_192, 0.0003, 0.0003, 0.86, "ultra_low", True, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "cerebras",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["cerebras", "fast-inference", mid],
                ),
            )

    def _seed_bedrock(self) -> None:
        """Seed Amazon Bedrock — AWS managed access to foundation models."""
        self.register_provider(
            provider_id="bedrock",
            name="Amazon Bedrock",
            vendor="AWS",
            endpoints=[ModelEndpoint(url="https://bedrock-runtime.us-east-1.amazonaws.com", region="us")],
            api_key_env="AWS_ACCESS_KEY_ID",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("bedrock-claude-3-5-sonnet", [ModelType.TEXT, ModelType.VISION], 200_000, 8_192, 0.003, 0.015, 0.95, "low", True, True, True),
            ("bedrock-claude-3-haiku", [ModelType.TEXT], 200_000, 4_096, 0.00025, 0.00125, 0.85, "low", True, True, False),
            ("bedrock-llama3-1-405b", [ModelType.TEXT], 128_000, 4_096, 0.005, 0.015, 0.9, "medium", True, True, False),
            ("bedrock-llama3-1-70b", [ModelType.TEXT], 128_000, 4_096, 0.001, 0.003, 0.85, "low", True, True, False),
            ("amazon-nova-pro", [ModelType.TEXT, ModelType.MULTIMODAL], 300_000, 8_192, 0.008, 0.024, 0.9, "medium", True, True, False),
            ("amazon-nova-lite", [ModelType.TEXT, ModelType.MULTIMODAL], 300_000, 8_192, 0.0006, 0.0024, 0.82, "low", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "bedrock",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["bedrock", "aws", mid],
                ),
            )

    def _seed_azure(self) -> None:
        """Seed Azure OpenAI — enterprise OpenAI models hosted on Microsoft Azure."""
        self.register_provider(
            provider_id="azure",
            name="Azure OpenAI",
            vendor="Microsoft",
            endpoints=[ModelEndpoint(url="https://{resource}.openai.azure.com", region="us")],
            api_key_env="AZURE_OPENAI_API_KEY",
            rate_limit_rpm=300,
            rate_limit_tpm=800_000,
        )
        models = [
            ("azure-gpt-4o", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL], 128_000, 16_384, 0.03, 0.06, 0.95, "low", True, True, True),
            ("azure-gpt-4o-mini", [ModelType.TEXT, ModelType.VISION], 128_000, 16_384, 0.00015, 0.0006, 0.88, "very_low", True, True, True),
            ("azure-gpt-4-turbo", [ModelType.TEXT, ModelType.VISION], 128_000, 4_096, 0.01, 0.03, 0.9, "low", True, True, True),
            ("azure-o3-mini", [ModelType.TEXT, ModelType.REASONING], 200_000, 100_000, 0.0011, 0.0044, 0.95, "medium", True, True, False),
            ("azure-dall-e-3", [ModelType.IMAGE_GEN], 4_000, 1, 0.04, 0.0, 0.85, "medium", False, False, False),
            ("azure-whisper-1", [ModelType.STT], 0, 0, 0.006, 0.0, 0.9, "medium", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "azure",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["azure", "microsoft", mid],
                ),
            )

    def _seed_openrouter(self) -> None:
        """Seed OpenRouter — unified gateway to many third-party model providers."""
        self.register_provider(
            provider_id="openrouter",
            name="OpenRouter",
            vendor="OpenRouter",
            endpoints=[ModelEndpoint(url="https://openrouter.ai/api/v1", region="us")],
            api_key_env="OPENROUTER_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("anthropic/claude-3.5-sonnet", [ModelType.TEXT, ModelType.VISION], 200_000, 8_192, 0.003, 0.015, 0.95, "low", True, True, True),
            ("openai/gpt-4o", [ModelType.TEXT, ModelType.VISION], 128_000, 16_384, 0.03, 0.06, 0.95, "low", True, True, True),
            ("google/gemini-pro-1.5", [ModelType.TEXT, ModelType.VISION], 2_000_000, 8_192, 0.00125, 0.005, 0.93, "medium", True, True, True),
            ("meta-llama/llama-3.1-405b-instruct", [ModelType.TEXT], 128_000, 4_096, 0.005, 0.015, 0.9, "medium", True, True, False),
            ("mistralai/mistral-large", [ModelType.TEXT], 128_000, 4_096, 0.002, 0.006, 0.9, "low", True, True, False),
            ("qwen/qwen-2.5-72b-instruct", [ModelType.TEXT], 128_000, 8_192, 0.0003, 0.0006, 0.85, "low", True, True, False),
            ("deepseek/deepseek-r1", [ModelType.TEXT, ModelType.REASONING], 128_000, 32_000, 0.00055, 0.0022, 0.93, "medium", True, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "openrouter",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["openrouter", "gateway", mid],
                ),
            )

    def _seed_zhipu(self) -> None:
        """Seed Zhipu AI — GLM series foundation models from Zhipu."""
        self.register_provider(
            provider_id="zhipu",
            name="Zhipu AI",
            vendor="Zhipu",
            endpoints=[ModelEndpoint(url="https://open.bigmodel.cn/api/paas/v4", region="asia")],
            api_key_env="ZHIPUAI_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("glm-4-plus", [ModelType.TEXT, ModelType.VISION], 128_000, 4_096, 0.007, 0.021, 0.9, "low", True, True, True),
            ("glm-4-air", [ModelType.TEXT], 128_000, 4_096, 0.001, 0.001, 0.82, "low", True, True, False),
            ("glm-4-flash", [ModelType.TEXT], 128_000, 4_096, 0.0, 0.0, 0.78, "ultra_low", True, True, False),
            ("glm-4v", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL], 128_000, 4_096, 0.01, 0.03, 0.87, "medium", True, True, True),
            ("glm-4-long", [ModelType.TEXT], 1_000_000, 4_096, 0.001, 0.001, 0.8, "medium", True, True, False),
            ("cogview-3", [ModelType.IMAGE_GEN], 4_000, 1, 0.05, 0.0, 0.82, "medium", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "zhipu",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["zhipu", "glm", mid],
                ),
            )

    def _seed_moonshot(self) -> None:
        """Seed Moonshot AI — Kimi long-context models from Moonshot."""
        self.register_provider(
            provider_id="moonshot",
            name="Moonshot AI",
            vendor="Moonshot",
            endpoints=[ModelEndpoint(url="https://api.moonshot.cn/v1", region="asia")],
            api_key_env="MOONSHOT_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("moonshot-v1-8k", [ModelType.TEXT], 8_000, 4_096, 0.001, 0.002, 0.8, "low", True, True, False),
            ("moonshot-v1-32k", [ModelType.TEXT], 32_000, 4_096, 0.002, 0.005, 0.82, "low", True, True, False),
            ("moonshot-v1-128k", [ModelType.TEXT], 128_000, 4_096, 0.005, 0.012, 0.85, "medium", True, True, False),
            ("moonshot-v1-auto", [ModelType.TEXT], 128_000, 4_096, 0.003, 0.008, 0.85, "medium", True, True, False),
            ("kimi-latest", [ModelType.TEXT, ModelType.VISION], 128_000, 4_096, 0.005, 0.012, 0.88, "low", True, True, True),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "moonshot",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["moonshot", "kimi", mid],
                ),
            )

    def _seed_minimax(self) -> None:
        """Seed MiniMax — abab series models with long context windows."""
        self.register_provider(
            provider_id="minimax",
            name="MiniMax",
            vendor="MiniMax",
            endpoints=[ModelEndpoint(url="https://api.minimax.chat/v1", region="asia")],
            api_key_env="MINIMAX_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("abab6.5s-chat", [ModelType.TEXT], 245_000, 4_096, 0.001, 0.002, 0.82, "low", True, True, False),
            ("abab6.5-chat", [ModelType.TEXT], 245_000, 4_096, 0.002, 0.005, 0.85, "medium", True, True, False),
            ("abab6-chat", [ModelType.TEXT], 16_000, 4_096, 0.003, 0.007, 0.83, "medium", True, True, False),
            ("minimax-text-01", [ModelType.TEXT], 1_000_000, 4_096, 0.002, 0.005, 0.87, "medium", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "minimax",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["minimax", "abab", mid],
                ),
            )

    def _seed_doubao(self) -> None:
        """Seed ByteDance Doubao — Volcano Engine hosted foundation models."""
        self.register_provider(
            provider_id="doubao",
            name="ByteDance Doubao",
            vendor="ByteDance",
            endpoints=[ModelEndpoint(url="https://ark.cn-beijing.volces.com/api/v3", region="asia")],
            api_key_env="ARK_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("doubao-pro-4k", [ModelType.TEXT], 4_000, 4_096, 0.0003, 0.0006, 0.8, "low", True, True, False),
            ("doubao-pro-32k", [ModelType.TEXT], 32_000, 4_096, 0.001, 0.002, 0.83, "low", True, True, False),
            ("doubao-pro-128k", [ModelType.TEXT], 128_000, 4_096, 0.003, 0.006, 0.85, "medium", True, True, False),
            ("doubao-lite-4k", [ModelType.TEXT], 4_000, 4_096, 0.0001, 0.0002, 0.75, "ultra_low", True, False, False),
            ("doubao-vision-pro", [ModelType.TEXT, ModelType.VISION], 32_000, 4_096, 0.002, 0.005, 0.84, "medium", True, True, True),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "doubao",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["doubao", "bytedance", mid],
                ),
            )

    def _seed_ernie(self) -> None:
        """Seed Baidu ERNIE — Qianfan platform hosted ERNIE models."""
        self.register_provider(
            provider_id="ernie",
            name="Baidu ERNIE",
            vendor="Baidu",
            endpoints=[ModelEndpoint(url="https://qianfan.baidubce.com/v2", region="asia")],
            api_key_env="ERNIE_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("ernie-4.0-turbo-8k", [ModelType.TEXT], 8_000, 4_096, 0.003, 0.009, 0.85, "low", True, True, False),
            ("ernie-4.0-turbo-128k", [ModelType.TEXT], 128_000, 4_096, 0.005, 0.014, 0.86, "medium", True, True, False),
            ("ernie-speed-128k", [ModelType.TEXT], 128_000, 4_096, 0.0005, 0.001, 0.78, "low", True, True, False),
            ("ernie-lite-8k", [ModelType.TEXT], 8_000, 4_096, 0.0001, 0.0002, 0.72, "ultra_low", True, False, False),
            ("ernie-v4", [ModelType.TEXT, ModelType.VISION], 8_000, 4_096, 0.004, 0.012, 0.84, "low", True, True, True),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "ernie",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["ernie", "baidu", mid],
                ),
            )

    def _seed_stepfun(self) -> None:
        """Seed StepFun — step series models from StepFun."""
        self.register_provider(
            provider_id="stepfun",
            name="StepFun",
            vendor="StepFun",
            endpoints=[ModelEndpoint(url="https://api.stepfun.com/v1", region="asia")],
            api_key_env="STEPFUN_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("step-1-8k", [ModelType.TEXT], 8_000, 4_096, 0.001, 0.002, 0.78, "low", True, True, False),
            ("step-1-32k", [ModelType.TEXT], 32_000, 4_096, 0.002, 0.005, 0.82, "low", True, True, False),
            ("step-1-128k", [ModelType.TEXT], 128_000, 4_096, 0.005, 0.012, 0.85, "medium", True, True, False),
            ("step-1v-8k", [ModelType.TEXT, ModelType.VISION], 8_000, 4_096, 0.002, 0.004, 0.8, "low", True, True, True),
            ("step-2-16k", [ModelType.TEXT], 16_000, 4_096, 0.003, 0.007, 0.87, "medium", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "stepfun",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["stepfun", "step", mid],
                ),
            )

    def _seed_lambda(self) -> None:
        """Seed Lambda Inference — open models served on Lambda Labs GPU cloud."""
        self.register_provider(
            provider_id="lambda",
            name="Lambda Inference",
            vendor="Lambda Labs",
            endpoints=[ModelEndpoint(url="https://api.lambdalabs.com/v1", region="us")],
            api_key_env="LAMBDA_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("hermes-3-405b", [ModelType.TEXT], 128_000, 4_096, 0.005, 0.015, 0.89, "medium", True, True, False),
            ("hermes-3-70b", [ModelType.TEXT], 128_000, 4_096, 0.001, 0.003, 0.84, "low", True, True, False),
            ("llama-3.1-405b-instruct", [ModelType.TEXT], 128_000, 4_096, 0.005, 0.015, 0.9, "medium", True, True, False),
            ("llama-3.1-70b-instruct", [ModelType.TEXT], 128_000, 4_096, 0.001, 0.003, 0.85, "low", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "lambda",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["lambda", "lambdalabs", mid],
                ),
            )

    def _seed_replicate_models(self) -> None:
        """Seed Replicate — hosted open models for text, image, and audio tasks."""
        self.register_provider(
            provider_id="replicate",
            name="Replicate",
            vendor="Replicate",
            endpoints=[ModelEndpoint(url="https://api.replicate.com/v1", region="us")],
            api_key_env="REPLICATE_API_KEY",
            rate_limit_rpm=150,
            rate_limit_tpm=300_000,
        )
        models = [
            ("replicate-llama-3.1-405b", [ModelType.TEXT], 128_000, 4_096, 0.005, 0.015, 0.9, "medium", True, True, False),
            ("replicate-flux-schnell", [ModelType.IMAGE_GEN], 2_000, 1, 0.003, 0.0, 0.86, "low", False, False, False),
            ("replicate-flux-dev", [ModelType.IMAGE_GEN], 2_000, 1, 0.004, 0.0, 0.9, "medium", False, False, False),
            ("replicate-sdxl", [ModelType.IMAGE_GEN], 2_000, 1, 0.003, 0.0, 0.85, "low", False, False, False),
            ("replicate-whisper", [ModelType.STT], 0, 0, 0.006, 0.0, 0.85, "medium", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "replicate",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["replicate", mid.split("/")[0]],
                ),
            )

    def _seed_assemblyai(self) -> None:
        """Seed AssemblyAI — speech-to-text models with optional text generation."""
        self.register_provider(
            provider_id="assemblyai",
            name="AssemblyAI",
            vendor="AssemblyAI",
            endpoints=[ModelEndpoint(url="https://api.assemblyai.com/v2", region="us")],
            api_key_env="ASSEMBLYAI_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("best-turbo", [ModelType.STT], 0, 0, 0.00047, 0.0, 0.88, "low", False, False, False),
            ("best", [ModelType.STT], 0, 0, 0.00079, 0.0, 0.92, "medium", False, False, False),
            ("nano", [ModelType.STT], 0, 0, 0.0002, 0.0, 0.8, "ultra_low", False, False, False),
            ("slam-1", [ModelType.TEXT], 4_000, 4_096, 0.001, 0.002, 0.8, "low", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "assemblyai",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["assemblyai", "stt", mid],
                ),
            )

    def _seed_deepgram(self) -> None:
        """Seed Deepgram — speech-to-text and text-to-speech models."""
        self.register_provider(
            provider_id="deepgram",
            name="Deepgram",
            vendor="Deepgram",
            endpoints=[ModelEndpoint(url="https://api.deepgram.com/v1", region="us")],
            api_key_env="DEEPGRAM_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("nova-2", [ModelType.STT], 0, 0, 0.0043, 0.0, 0.9, "low", False, False, False),
            ("nova-2-general", [ModelType.STT], 0, 0, 0.0043, 0.0, 0.88, "low", False, False, False),
            ("aura", [ModelType.TTS], 4_096, 4_096, 0.015, 0.0, 0.85, "low", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "deepgram",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["deepgram", mid],
                ),
            )

    def _seed_playht(self) -> None:
        """Seed PlayHT — text-to-speech voice generation models."""
        self.register_provider(
            provider_id="playht",
            name="PlayHT",
            vendor="PlayHT",
            endpoints=[ModelEndpoint(url="https://api.play.ht/api/v2", region="us")],
            api_key_env="PLAYHT_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("play-3.0-mini", [ModelType.TTS], 4_096, 4_096, 0.005, 0.0, 0.8, "low", False, False, False),
            ("play-3.0", [ModelType.TTS], 4_096, 4_096, 0.01, 0.0, 0.87, "low", False, False, False),
            ("play-ht2", [ModelType.TTS], 4_096, 4_096, 0.015, 0.0, 0.85, "medium", False, False, False),
            ("play-ht1", [ModelType.TTS], 4_096, 4_096, 0.02, 0.0, 0.82, "medium", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "playht",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["playht", "tts", mid],
                ),
            )

    def _seed_cartesia(self) -> None:
        """Seed Cartesia — low-latency text-to-speech with the Sonic models."""
        self.register_provider(
            provider_id="cartesia",
            name="Cartesia",
            vendor="Cartesia",
            endpoints=[ModelEndpoint(url="https://api.cartesia.ai/v1", region="us")],
            api_key_env="CARTESIA_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("sonic", [ModelType.TTS], 4_096, 4_096, 0.005, 0.0, 0.86, "very_low", False, False, False),
            ("sonic-2", [ModelType.TTS], 4_096, 4_096, 0.008, 0.0, 0.9, "low", False, False, False),
            ("sonic-turbo", [ModelType.TTS], 4_096, 4_096, 0.006, 0.0, 0.85, "ultra_low", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "cartesia",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["cartesia", "sonic", mid],
                ),
            )

    def _seed_image_providers(self) -> None:
        # Stability AI
        self.register_provider(
            provider_id="stability",
            name="Stability AI",
            vendor="Stability",
            endpoints=[ModelEndpoint(url="https://api.stability.ai/v1", region="us")],
            api_key_env="STABILITY_API_KEY",
            rate_limit_rpm=150,
            rate_limit_tpm=0,
        )
        for mid, ci, q, cost in [
            ("stable-diffusion-xl", 0.003, 0.86, 0.04),
            ("stable-diffusion-3", 0.004, 0.9, 0.065),
            ("flux-1", 0.005, 0.92, 0.055),
        ]:
            self.register_model(
                "stability",
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.IMAGE_GEN],
                    max_context_tokens=2_000,
                    max_output_tokens=1,
                    quality_score=q,
                    latency_tier="medium",
                    cost_per_1k_input=ci,
                    cost_per_1k_output=0.0,
                    cost_per_image=cost,
                    tags=["image", mid],
                ),
            )

        # Midjourney-style provider (third-party API)
        self.register_provider(
            provider_id="midjourney",
            name="Midjourney API",
            vendor="Midjourney",
            endpoints=[ModelEndpoint(url="https://api.midjourney.com", region="us")],
            api_key_env="MIDJOURNEY_API_KEY",
            rate_limit_rpm=50,
            rate_limit_tpm=0,
        )
        self.register_model(
            "midjourney",
            ModelCapability(
                model_id="midjourney-v6",
                model_types=[ModelType.IMAGE_GEN],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.95,
                latency_tier="high",
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.0,
                cost_per_image=0.1,
                tags=["image", "midjourney"],
            ),
        )

        # Ideogram
        self.register_provider(
            provider_id="ideogram",
            name="Ideogram",
            vendor="Ideogram",
            endpoints=[ModelEndpoint(url="https://api.ideogram.ai/v1", region="us")],
            api_key_env="IDEOGRAM_API_KEY",
            rate_limit_rpm=100,
            rate_limit_tpm=0,
        )
        self.register_model(
            "ideogram",
            ModelCapability(
                model_id="ideogram-v2",
                model_types=[ModelType.IMAGE_GEN],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.87,
                latency_tier="medium",
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.0,
                cost_per_image=0.08,
                tags=["image", "ideogram"],
            ),
        )

    def _seed_video_providers(self) -> None:
        video_providers = [
            ("sora", "OpenAI Sora", "OpenAI", "https://api.openai.com/v1/video", "sora", 0.95, "high", 0.1),
            ("runway", "Runway Gen-3", "Runway", "https://api.runwayml.com/v1", "runway-gen3", 0.9, "high", 0.15),
            ("pika", "Pika 1.5", "Pika", "https://api.pika.art/v1", "pika-1.5", 0.85, "medium", 0.12),
            ("kling", "Kling", "Kuaishou", "https://api.kuaishou.com/kling", "kling", 0.88, "high", 0.13),
            ("luma", "Luma Dream Machine", "Luma", "https://api.lumalabs.ai/v1", "luma-dream-machine", 0.87, "medium", 0.14),
        ]
        for pid, name, vendor, url, mid, q, tier, cost in video_providers:
            self.register_provider(
                provider_id=pid,
                name=name,
                vendor=vendor,
                endpoints=[ModelEndpoint(url=url, region="us")],
                rate_limit_rpm=30,
                rate_limit_tpm=0,
            )
            self.register_model(
                pid,
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.VIDEO_GEN],
                    max_context_tokens=2_000,
                    max_output_tokens=1,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=0.0,
                    cost_per_1k_output=0.0,
                    cost_per_second_video=cost,
                    tags=["video", mid],
                ),
            )

    def _seed_audio_providers(self) -> None:
        # ElevenLabs TTS
        self.register_provider(
            provider_id="elevenlabs",
            name="ElevenLabs",
            vendor="ElevenLabs",
            endpoints=[ModelEndpoint(url="https://api.elevenlabs.io/v1", region="us")],
            api_key_env="ELEVENLABS_API_KEY",
            rate_limit_rpm=100,
            rate_limit_tpm=0,
        )
        self.register_model(
            "elevenlabs",
            ModelCapability(
                model_id="eleven-multilingual-v2",
                model_types=[ModelType.TTS],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.93,
                latency_tier="low",
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                tags=["tts", "elevenlabs"],
            ),
        )

        # Suno music
        self.register_provider(
            provider_id="suno",
            name="Suno",
            vendor="Suno",
            endpoints=[ModelEndpoint(url="https://api.suno.ai/v1", region="us")],
            api_key_env="SUNO_API_KEY",
            rate_limit_rpm=50,
            rate_limit_tpm=0,
        )
        self.register_model(
            "suno",
            ModelCapability(
                model_id="suno-v3.5",
                model_types=[ModelType.AUDIO_GEN],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.9,
                latency_tier="high",
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                tags=["music", "suno"],
            ),
        )

        # AudioCraft (Meta, open-source, local)
        self.register_provider(
            provider_id="audiocraft",
            name="AudioCraft",
            vendor="Meta",
            endpoints=[ModelEndpoint(url="http://localhost:5000", region="local")],
            rate_limit_rpm=200,
            rate_limit_tpm=0,
        )
        self.register_model(
            "audiocraft",
            ModelCapability(
                model_id="musicgen-small",
                model_types=[ModelType.AUDIO_GEN],
                max_context_tokens=512,
                max_output_tokens=1,
                quality_score=0.75,
                latency_tier="medium",
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                tags=["music", "local", "audiocraft"],
            ),
        )

        # Bark TTS (local)
        self.register_provider(
            provider_id="bark",
            name="Bark",
            vendor="Suno",
            endpoints=[ModelEndpoint(url="http://localhost:5001", region="local")],
            rate_limit_rpm=100,
            rate_limit_tpm=0,
        )
        self.register_model(
            "bark",
            ModelCapability(
                model_id="bark-tts",
                model_types=[ModelType.TTS],
                max_context_tokens=512,
                max_output_tokens=1,
                quality_score=0.72,
                latency_tier="medium",
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                tags=["tts", "local", "bark"],
            ),
        )

    def _seed_3d_providers(self) -> None:
        providers_3d = [
            ("luma-3d", "Luma AI 3D", "Luma", "https://api.lumalabs.ai/v1/3d", "luma-3d-gen", 0.9, "high"),
            ("tripo3d", "Tripo3D", "Tripo", "https://api.tripo3d.ai/v1", "tripo3d-gen", 0.85, "medium"),
            ("meshy", "Meshy", "Meshy", "https://api.meshy.ai/v1", "meshy-gen", 0.84, "medium"),
            ("csm", "CSM", "Common Sense Machines", "https://api.csm.ai/v1", "csm-gen", 0.8, "medium"),
        ]
        for pid, name, vendor, url, mid, q, tier in providers_3d:
            self.register_provider(
                provider_id=pid,
                name=name,
                vendor=vendor,
                endpoints=[ModelEndpoint(url=url, region="us")],
                rate_limit_rpm=30,
                rate_limit_tpm=0,
            )
            self.register_model(
                pid,
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.GEN_3D],
                    max_context_tokens=2_000,
                    max_output_tokens=1,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=0.01,
                    cost_per_1k_output=0.0,
                    tags=["3d", mid],
                ),
            )

    def _seed_animation_providers(self) -> None:
        # Luma AI animation (registered under the existing luma video provider)
        self.register_model(
            "luma",
            ModelCapability(
                model_id="luma-animation",
                model_types=[ModelType.ANIMATION],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.86,
                latency_tier="high",
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.0,
                tags=["animation", "luma"],
            ),
        )

        self.register_provider(
            provider_id="krea",
            name="Krea Animation",
            vendor="Krea",
            endpoints=[ModelEndpoint(url="https://api.krea.ai/v1", region="us")],
            api_key_env="KREA_API_KEY",
            rate_limit_rpm=50,
            rate_limit_tpm=0,
        )
        self.register_model(
            "krea",
            ModelCapability(
                model_id="krea-animation",
                model_types=[ModelType.ANIMATION],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.85,
                latency_tier="high",
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.0,
                tags=["animation", "krea"],
            ),
        )

        # animatediff via local/Stability
        self.register_model(
            "stability",
            ModelCapability(
                model_id="animatediff",
                model_types=[ModelType.ANIMATION],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.78,
                latency_tier="high",
                cost_per_1k_input=0.004,
                cost_per_1k_output=0.0,
                tags=["animation", "animatediff"],
            ),
        )

    def _seed_yi(self) -> None:
        """Seed 01.AI — Yi series of bilingual foundation models."""
        self.register_provider(
            provider_id="yi",
            name="01.AI",
            vendor="01.AI",
            endpoints=[ModelEndpoint(url="https://api.01.ai/v1", region="asia")],
            api_key_env="YI_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("yi-large", [ModelType.TEXT], 32_000, 4_096, 0.003, 0.006, 0.88, "medium", True, True, False),
            ("yi-medium", [ModelType.TEXT], 16_000, 4_096, 0.001, 0.002, 0.82, "low", True, True, False),
            ("yi-small", [ModelType.TEXT], 4_000, 4_096, 0.0003, 0.0006, 0.75, "very_low", True, False, False),
            ("yi-vision", [ModelType.TEXT, ModelType.VISION], 16_000, 4_096, 0.002, 0.004, 0.84, "medium", True, False, True),
            ("yi-large-turbo", [ModelType.TEXT], 32_000, 4_096, 0.002, 0.004, 0.85, "low", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "yi",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["yi", mid],
                ),
            )

    def _seed_baichuan(self) -> None:
        """Seed Baichuan — Chinese-language LLM series with strong reasoning."""
        self.register_provider(
            provider_id="baichuan",
            name="Baichuan",
            vendor="Baichuan",
            endpoints=[ModelEndpoint(url="https://api.baichuan-ai.com/v1", region="asia")],
            api_key_env="BAICHUAN_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("baichuan4", [ModelType.TEXT], 32_000, 4_096, 0.004, 0.008, 0.89, "medium", True, True, False),
            ("baichuan3-turbo", [ModelType.TEXT], 32_000, 4_096, 0.001, 0.002, 0.82, "low", True, False, False),
            ("baichuan2-53b", [ModelType.TEXT], 4_000, 4_096, 0.0006, 0.0006, 0.78, "very_low", True, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "baichuan",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["baichuan", mid],
                ),
            )

    def _seed_siliconflow(self) -> None:
        """Seed SiliconFlow — aggregated open-model inference platform."""
        self.register_provider(
            provider_id="siliconflow",
            name="SiliconFlow",
            vendor="SiliconFlow",
            endpoints=[ModelEndpoint(url="https://api.siliconflow.cn/v1", region="asia")],
            api_key_env="SILICONFLOW_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("qwen/qwen2.5-72b-instruct", [ModelType.TEXT], 128_000, 8_192, 0.0006, 0.0006, 0.89, "low", True, True, False),
            ("deepseek-ai/DeepSeek-V3", [ModelType.TEXT], 64_000, 8_192, 0.0003, 0.0003, 0.91, "low", True, True, False),
            ("meta-llama/Meta-Llama-3.1-405B-Instruct", [ModelType.TEXT], 128_000, 8_192, 0.0008, 0.0008, 0.92, "medium", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "siliconflow",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["siliconflow", "open-source", mid.split("/")[-1]],
                ),
            )
        # Image generation model on SiliconFlow
        self.register_model(
            "siliconflow",
            ModelCapability(
                model_id="black-forest-labs/FLUX.1-schnell",
                model_types=[ModelType.IMAGE_GEN],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.88,
                latency_tier="medium",
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.0,
                cost_per_image=0.04,
                tags=["image", "siliconflow", "FLUX.1-schnell"],
            ),
        )

    def _seed_modelscope(self) -> None:
        """Seed ModelScope — Alibaba open-model hub with multimodal options."""
        self.register_provider(
            provider_id="modelscope",
            name="ModelScope",
            vendor="Alibaba",
            endpoints=[ModelEndpoint(url="https://api.modelscope.cn/v1", region="asia")],
            api_key_env="MODELSCOPE_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("qwen-72b-chat", [ModelType.TEXT], 32_000, 4_096, 0.0006, 0.0006, 0.88, "low", True, True, False),
            ("chatglm3-6b", [ModelType.TEXT], 32_000, 4_096, 0.0001, 0.0001, 0.76, "very_low", True, False, False),
            ("sensevoice", [ModelType.STT], 0, 0, 0.006, 0.0, 0.88, "medium", False, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "modelscope",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["modelscope", mid],
                ),
            )
        # Image generation model on ModelScope
        self.register_model(
            "modelscope",
            ModelCapability(
                model_id="stable-diffusion-xl",
                model_types=[ModelType.IMAGE_GEN],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.85,
                latency_tier="medium",
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.0,
                cost_per_image=0.04,
                tags=["image", "modelscope", "sdxl"],
            ),
        )

    def _seed_predibase(self) -> None:
        """Seed Predibase — fine-tuned open-model serving platform."""
        self.register_provider(
            provider_id="predibase",
            name="Predibase",
            vendor="Predibase",
            endpoints=[ModelEndpoint(url="https://api.predibase.com/v1", region="us")],
            api_key_env="PREDIBASE_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("llama-3.1-8b-instruct-tuned", [ModelType.TEXT], 128_000, 4_096, 0.0001, 0.0001, 0.76, "low", True, True, False),
            ("llama-3.1-70b-instruct-tuned", [ModelType.TEXT], 128_000, 4_096, 0.0006, 0.0006, 0.88, "low", True, True, False),
            ("mistral-7b-instruct-tuned", [ModelType.TEXT], 32_000, 4_096, 0.0001, 0.0001, 0.76, "very_low", True, False, False),
            ("qwen2.5-coder-7b-tuned", [ModelType.TEXT, ModelType.CODE], 128_000, 4_096, 0.0002, 0.0002, 0.82, "low", True, False, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "predibase",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["predibase", "fine-tuned", mid],
                ),
            )

    def _seed_octoai(self) -> None:
        """Seed OctoAI — managed inference for open-source models."""
        self.register_provider(
            provider_id="octoai",
            name="OctoAI",
            vendor="OctoAI",
            endpoints=[ModelEndpoint(url="https://api.octoai.cloud/v1", region="us")],
            api_key_env="OCTOAI_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        models = [
            ("llama-3.1-405b-instruct", [ModelType.TEXT], 128_000, 4_096, 0.0008, 0.0008, 0.92, "medium", True, True, False),
            ("llama-3.1-70b-instruct", [ModelType.TEXT], 128_000, 4_096, 0.0006, 0.0006, 0.88, "low", True, True, False),
            ("llama-3.1-8b-instruct", [ModelType.TEXT], 128_000, 4_096, 0.0001, 0.0001, 0.76, "very_low", True, True, False),
            ("hermes-2-pro-llama-3-8b", [ModelType.TEXT], 8_000, 4_096, 0.0001, 0.0001, 0.78, "very_low", True, True, False),
        ]
        for m in models:
            mid, types, ctx, out, ci, co, q, tier, stream, fn, vision = m
            self.register_model(
                "octoai",
                ModelCapability(
                    model_id=mid,
                    model_types=types,
                    max_context_tokens=ctx,
                    max_output_tokens=out,
                    supports_streaming=stream,
                    supports_function_calling=fn,
                    supports_vision=vision,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["octoai", "open-source", mid],
                ),
            )

    def _seed_leonardo(self) -> None:
        """Seed Leonardo AI — creative image generation models."""
        self.register_provider(
            provider_id="leonardo",
            name="Leonardo AI",
            vendor="Leonardo",
            endpoints=[ModelEndpoint(url="https://cloud.leonardo.ai/api/rest/v1", region="us")],
            api_key_env="LEONARDO_API_KEY",
            rate_limit_rpm=150,
            rate_limit_tpm=0,
        )
        for mid, q, cost in [
            ("leonardo-phoenix", 0.9, 0.05),
            ("leonardo-lightning", 0.82, 0.03),
            ("leonardo-diffusion", 0.85, 0.04),
            ("leonardo-kino", 0.88, 0.045),
        ]:
            self.register_model(
                "leonardo",
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.IMAGE_GEN],
                    max_context_tokens=2_000,
                    max_output_tokens=1,
                    quality_score=q,
                    latency_tier="medium",
                    cost_per_1k_input=0.003,
                    cost_per_1k_output=0.0,
                    cost_per_image=cost,
                    tags=["image", "leonardo", mid],
                ),
            )

    def _seed_morph(self) -> None:
        """Seed Morph Studio — text-to-video generation platform."""
        self.register_provider(
            provider_id="morph",
            name="Morph Studio",
            vendor="Morph",
            endpoints=[ModelEndpoint(url="https://api.morphstudio.com/v1", region="us")],
            api_key_env="MORPH_API_KEY",
            rate_limit_rpm=30,
            rate_limit_tpm=0,
        )
        self.register_model(
            "morph",
            ModelCapability(
                model_id="morph-video-gen",
                model_types=[ModelType.VIDEO_GEN],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.85,
                latency_tier="medium",
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                cost_per_second_video=0.1,
                tags=["video", "morph", "morph-video-gen"],
            ),
        )

    def _seed_viggle(self) -> None:
        """Seed Viggle — character animation generation platform."""
        self.register_provider(
            provider_id="viggle",
            name="Viggle",
            vendor="Viggle",
            endpoints=[ModelEndpoint(url="https://api.viggle.ai/v1", region="us")],
            api_key_env="VIGGLE_API_KEY",
            rate_limit_rpm=50,
            rate_limit_tpm=0,
        )
        self.register_model(
            "viggle",
            ModelCapability(
                model_id="viggle-animate",
                model_types=[ModelType.ANIMATION],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.84,
                latency_tier="medium",
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.0,
                tags=["animation", "viggle", "viggle-animate"],
            ),
        )

    def _seed_did(self) -> None:
        """Seed D-ID — talking-avatar animation generation platform."""
        self.register_provider(
            provider_id="did",
            name="D-ID",
            vendor="D-ID",
            endpoints=[ModelEndpoint(url="https://api.d-id.com/v1", region="us")],
            api_key_env="DID_API_KEY",
            rate_limit_rpm=50,
            rate_limit_tpm=0,
        )
        for mid, q in [
            ("talks", 0.85),
            ("animations", 0.82),
        ]:
            self.register_model(
                "did",
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.ANIMATION],
                    max_context_tokens=2_000,
                    max_output_tokens=1,
                    quality_score=q,
                    latency_tier="medium",
                    cost_per_1k_input=0.005,
                    cost_per_1k_output=0.0,
                    tags=["animation", "did", mid],
                ),
            )

    def _seed_heygen(self) -> None:
        """Seed HeyGen — avatar video and animation generation platform."""
        self.register_provider(
            provider_id="heygen",
            name="HeyGen",
            vendor="HeyGen",
            endpoints=[ModelEndpoint(url="https://api.heygen.com/v1", region="us")],
            api_key_env="HEYGEN_API_KEY",
            rate_limit_rpm=50,
            rate_limit_tpm=0,
        )
        # Avatar video generation model
        self.register_model(
            "heygen",
            ModelCapability(
                model_id="heygen-v2",
                model_types=[ModelType.VIDEO_GEN],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.87,
                latency_tier="medium",
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                cost_per_second_video=0.12,
                tags=["video", "heygen", "heygen-v2"],
            ),
        )
        # Avatar animation model
        self.register_model(
            "heygen",
            ModelCapability(
                model_id="heygen-avatar",
                model_types=[ModelType.ANIMATION],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.86,
                latency_tier="medium",
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.0,
                tags=["animation", "heygen", "heygen-avatar"],
            ),
        )

    def _seed_synthesia(self) -> None:
        """Seed Synthesia — avatar video and animation generation platform."""
        self.register_provider(
            provider_id="synthesia",
            name="Synthesia",
            vendor="Synthesia",
            endpoints=[ModelEndpoint(url="https://api.synthesia.io/v2", region="us")],
            api_key_env="SYNTHESIA_API_KEY",
            rate_limit_rpm=50,
            rate_limit_tpm=0,
        )
        # Avatar video generation model
        self.register_model(
            "synthesia",
            ModelCapability(
                model_id="synthesia-v2",
                model_types=[ModelType.VIDEO_GEN],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.86,
                latency_tier="medium",
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                cost_per_second_video=0.15,
                tags=["video", "synthesia", "synthesia-v2"],
            ),
        )
        # Avatar animation model
        self.register_model(
            "synthesia",
            ModelCapability(
                model_id="synthesia-avatar",
                model_types=[ModelType.ANIMATION],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.85,
                latency_tier="medium",
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.0,
                tags=["animation", "synthesia", "synthesia-avatar"],
            ),
        )

    def _seed_code_providers(self) -> None:
        """Seed code-specialized providers for developer tooling."""
        # Tabnine
        self.register_provider(
            provider_id="tabnine",
            name="Tabnine",
            vendor="Tabnine",
            endpoints=[ModelEndpoint(url="https://api.tabnine.com/v1", region="us")],
            api_key_env="TABNINE_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        for mid, ctx, ci, co, q in [
            ("tabnine-protg", 16_000, 0.001, 0.002, 0.8),
            ("tabnine-starcoder2", 16_000, 0.0003, 0.0003, 0.83),
        ]:
            self.register_model(
                "tabnine",
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.TEXT, ModelType.CODE],
                    max_context_tokens=ctx,
                    max_output_tokens=4_096,
                    supports_streaming=True,
                    supports_function_calling=False,
                    supports_vision=False,
                    quality_score=q,
                    latency_tier="low",
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["tabnine", "code", mid],
                ),
            )

        # Codeium
        self.register_provider(
            provider_id="codeium",
            name="Codeium",
            vendor="Codeium",
            endpoints=[ModelEndpoint(url="https://api.codeium.com/v1", region="us")],
            api_key_env="CODEIUM_API_KEY",
            rate_limit_rpm=200,
            rate_limit_tpm=500_000,
        )
        for mid, ctx, ci, co, q in [
            ("codeium-windsurf", 128_000, 0.0006, 0.0006, 0.86),
            ("codeium-starcoder", 16_000, 0.0002, 0.0002, 0.82),
        ]:
            self.register_model(
                "codeium",
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.TEXT, ModelType.CODE],
                    max_context_tokens=ctx,
                    max_output_tokens=4_096,
                    supports_streaming=True,
                    supports_function_calling=False,
                    supports_vision=False,
                    quality_score=q,
                    latency_tier="low",
                    cost_per_1k_input=ci,
                    cost_per_1k_output=co,
                    tags=["codeium", "code", mid],
                ),
            )

    def _seed_more_3d_providers(self) -> None:
        providers_3d = [
            ("rodin", "Rodin AI", "Rodin", "https://api.rodin.ai/v1", "RODIN_API_KEY", "rodin-gen-1", 0.88, "medium"),
            ("sloyd", "Sloyd", "Sloyd", "https://api.sloyd.ai/v1", "SLODY_API_KEY", "sloyd-gen", 0.82, "low"),
            ("polycam", "Polycam", "Polycam", "https://api.polycam.ai/v1", "POLYCAM_API_KEY", "polycam-gen", 0.85, "medium"),
        ]
        for pid, name, vendor, url, key_env, mid, q, tier in providers_3d:
            self.register_provider(
                provider_id=pid,
                name=name,
                vendor=vendor,
                endpoints=[ModelEndpoint(url=url, region="us")],
                api_key_env=key_env,
                rate_limit_rpm=30,
                rate_limit_tpm=0,
            )
            self.register_model(
                pid,
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.GEN_3D],
                    max_context_tokens=2_000,
                    max_output_tokens=1,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=0.01,
                    cost_per_1k_output=0.0,
                    tags=["3d", mid],
                ),
            )

    def _seed_more_animation_providers(self) -> None:
        providers_anim = [
            ("animatediff", "AnimateDiff", "AnimateDiff", "https://api.animatediff.com/v1", "ANIMATEDIFF_API_KEY", "animatediff-v2", 0.83, "medium"),
            ("deforum", "Deforum", "Deforum", "https://api.deforum.com/v1", "DEFORUM_API_KEY", "deforum-gen", 0.8, "medium"),
            ("genmo", "Genmo", "Genmo", "https://api.genmo.ai/v1", "GENMO_API_KEY", "genmo-mochi-1", 0.87, "high"),
        ]
        for pid, name, vendor, url, key_env, mid, q, tier in providers_anim:
            self.register_provider(
                provider_id=pid,
                name=name,
                vendor=vendor,
                endpoints=[ModelEndpoint(url=url, region="us")],
                api_key_env=key_env,
                rate_limit_rpm=50,
                rate_limit_tpm=0,
            )
            self.register_model(
                pid,
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.ANIMATION],
                    max_context_tokens=2_000,
                    max_output_tokens=1,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=0.01,
                    cost_per_1k_output=0.0,
                    tags=["animation", mid],
                ),
            )

    def _seed_more_audio_providers(self) -> None:
        # Stable Audio (Stability)
        self.register_provider(
            provider_id="stable-audio",
            name="Stable Audio",
            vendor="Stability",
            endpoints=[ModelEndpoint(url="https://api.stability.ai/v2/audio", region="us")],
            api_key_env="STABILITY_API_KEY",
            rate_limit_rpm=150,
            rate_limit_tpm=0,
        )
        self.register_model(
            "stable-audio",
            ModelCapability(
                model_id="stable-audio-2.0",
                model_types=[ModelType.AUDIO_GEN],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.88,
                latency_tier="medium",
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.0,
                tags=["music", "stable-audio"],
            ),
        )

        # Mubert
        self.register_provider(
            provider_id="mubert",
            name="Mubert",
            vendor="Mubert",
            endpoints=[ModelEndpoint(url="https://api.mubert.com/v3", region="us")],
            api_key_env="MUBERT_API_KEY",
            rate_limit_rpm=50,
            rate_limit_tpm=0,
        )
        self.register_model(
            "mubert",
            ModelCapability(
                model_id="mubert-gen",
                model_types=[ModelType.AUDIO_GEN],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.82,
                latency_tier="low",
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.0,
                tags=["music", "mubert"],
            ),
        )

        # AudioLDM (local)
        self.register_provider(
            provider_id="audioldm",
            name="AudioLDM",
            vendor="AudioLDM",
            endpoints=[ModelEndpoint(url="http://localhost:5002", region="local")],
            rate_limit_rpm=100,
            rate_limit_tpm=0,
        )
        self.register_model(
            "audioldm",
            ModelCapability(
                model_id="audioldm-2",
                model_types=[ModelType.AUDIO_GEN],
                max_context_tokens=2_000,
                max_output_tokens=1,
                quality_score=0.78,
                latency_tier="medium",
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                tags=["music", "local", "audioldm"],
            ),
        )

        # Additional model under the existing audiocraft provider
        self.register_model(
            "audiocraft",
            ModelCapability(
                model_id="musicgen-large",
                model_types=[ModelType.AUDIO_GEN],
                max_context_tokens=512,
                max_output_tokens=1,
                quality_score=0.82,
                latency_tier="medium",
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                tags=["music", "local", "audiocraft"],
            ),
        )

    def _seed_more_video_providers(self) -> None:
        providers_video = [
            ("haiper", "Haiper", "Haiper", "https://api.haiper.ai/v1", "HAIPER_API_KEY", "haiper-2", 0.84, "medium", 0.1),
            ("domika", "Domika", "Domika", "https://api.domika.ai/v1", "DOMIKA_API_KEY", "domika-gen", 0.82, "medium", 0.08),
        ]
        for pid, name, vendor, url, key_env, mid, q, tier, cost in providers_video:
            self.register_provider(
                provider_id=pid,
                name=name,
                vendor=vendor,
                endpoints=[ModelEndpoint(url=url, region="us")],
                api_key_env=key_env,
                rate_limit_rpm=30,
                rate_limit_tpm=0,
            )
            self.register_model(
                pid,
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.VIDEO_GEN],
                    max_context_tokens=2_000,
                    max_output_tokens=1,
                    quality_score=q,
                    latency_tier=tier,
                    cost_per_1k_input=0.0,
                    cost_per_1k_output=0.0,
                    cost_per_second_video=cost,
                    tags=["video", mid],
                ),
            )

    def _seed_embedding_providers(self) -> None:
        # Voyage AI
        self.register_provider(
            provider_id="voyage",
            name="Voyage AI",
            vendor="Voyage",
            endpoints=[ModelEndpoint(url="https://api.voyageai.com/v1", region="us")],
            api_key_env="VOYAGE_API_KEY",
            rate_limit_rpm=300,
            rate_limit_tpm=500_000,
        )
        for mid, ctx, q in [
            ("voyage-3", 32_768, 0.92),
            ("voyage-3-lite", 32_768, 0.85),
            ("voyage-code-2", 16_384, 0.9),
        ]:
            self.register_model(
                "voyage",
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.EMBEDDING],
                    max_context_tokens=ctx,
                    max_output_tokens=ctx,
                    quality_score=q,
                    latency_tier="low",
                    cost_per_1k_input=0.0001,
                    cost_per_1k_output=0.0,
                    tags=["embedding", mid],
                ),
            )

        # Nomic
        self.register_provider(
            provider_id="nomic",
            name="Nomic",
            vendor="Nomic",
            endpoints=[ModelEndpoint(url="https://api.nomic.ai/v1", region="us")],
            api_key_env="NOMIC_API_KEY",
            rate_limit_rpm=300,
            rate_limit_tpm=500_000,
        )
        for mid, ctx, q in [
            ("nomic-embed-text-v1", 8_192, 0.86),
            ("nomic-embed-vision-v1", 4_096, 0.84),
        ]:
            self.register_model(
                "nomic",
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.EMBEDDING],
                    max_context_tokens=ctx,
                    max_output_tokens=ctx,
                    quality_score=q,
                    latency_tier="low",
                    cost_per_1k_input=0.0001,
                    cost_per_1k_output=0.0,
                    tags=["embedding", mid],
                ),
            )

        # Jina AI
        self.register_provider(
            provider_id="jina",
            name="Jina AI",
            vendor="Jina",
            endpoints=[ModelEndpoint(url="https://api.jina.ai/v1", region="us")],
            api_key_env="JINA_API_KEY",
            rate_limit_rpm=300,
            rate_limit_tpm=500_000,
        )
        for mid, ctx, q in [
            ("jina-embeddings-v3", 8_192, 0.89),
            ("jina-embeddings-v2-base", 8_192, 0.85),
        ]:
            self.register_model(
                "jina",
                ModelCapability(
                    model_id=mid,
                    model_types=[ModelType.EMBEDDING],
                    max_context_tokens=ctx,
                    max_output_tokens=ctx,
                    quality_score=q,
                    latency_tier="low",
                    cost_per_1k_input=0.0001,
                    cost_per_1k_output=0.0,
                    tags=["embedding", mid],
                ),
            )

        # Mixedbread
        self.register_provider(
            provider_id="mixedbread",
            name="Mixedbread",
            vendor="Mixedbread",
            endpoints=[ModelEndpoint(url="https://api.mixedbread.ai/v1", region="us")],
            api_key_env="MIXEDBREAD_API_KEY",
            rate_limit_rpm=300,
            rate_limit_tpm=500_000,
        )
        self.register_model(
            "mixedbread",
            ModelCapability(
                model_id="mxbai-embed-large-v1",
                model_types=[ModelType.EMBEDDING],
                max_context_tokens=512,
                max_output_tokens=512,
                quality_score=0.88,
                latency_tier="low",
                cost_per_1k_input=0.0001,
                cost_per_1k_output=0.0,
                tags=["embedding", "mxbai-embed-large-v1"],
            ),
        )

    def _seed_task_mappings(self) -> None:
        """Pre-configure task-to-model mappings for game development."""
        mappings = {
            TaskType.WORLD_BUILDING: "gemini-1.5-pro",
            TaskType.CHARACTER_DESIGN: "gpt-4o",
            TaskType.DIALOGUE: "claude-3-haiku",
            TaskType.CODE_GEN: "claude-3-5-sonnet",
            TaskType.ASSET_IMAGE: "flux-1",
            TaskType.ASSET_VIDEO: "runway-gen3",
            TaskType.ASSET_3D: "rodin-gen-1",
            TaskType.ASSET_AUDIO: "musicgen-small",
            TaskType.MUSIC_GEN: "suno-v3.5",
            TaskType.VOICE_ACTING: "eleven-multilingual-v2",
            TaskType.BUG_ANALYSIS: "o3",
            TaskType.BALANCE_TEST: "deepseek-r1",
            TaskType.NARRATIVE: "claude-3-5-sonnet",
            TaskType.TRANSLATION: "gpt-4o",
            TaskType.EMBEDDING: "text-embedding-3-large",
            TaskType.SUMMARIZATION: "gemini-2.0-flash",
        }
        for task_type, model_id in mappings.items():
            if model_id in self._models:
                self._task_model_map[task_type] = model_id

        # Fallback for ASSET_3D when the primary model is unavailable.
        if TaskType.ASSET_3D not in self._task_model_map and "luma-3d-gen" in self._models:
            self._task_model_map[TaskType.ASSET_3D] = "luma-3d-gen"

    def _seed_fallback_chains(self) -> None:
        """Pre-set fallback chains for the primary text providers."""
        self._fallback_chains["openai"] = ["gpt-4o", "gpt-4-turbo", "claude-3-5-sonnet", "gemini-2.0-flash", "llama-3.1-70b"]
        self._fallback_chains["anthropic"] = ["claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku", "gpt-4o"]
        self._fallback_chains["google"] = ["gemini-1.5-pro", "gemini-2.0-flash", "gpt-4o", "claude-3-5-sonnet"]
        self._fallback_chains["meta"] = ["llama-3.1-70b", "llama-3.1-405b", "gpt-4o"]
        self._fallback_chains["deepseek"] = ["deepseek-v3", "deepseek-r1", "qwen-2.5-max"]
        self._fallback_chains["qwen"] = ["qwen-2.5-max", "qwq", "deepseek-v3"]
        self._fallback_chains["ollama"] = ["llama3", "qwen2", "mistral", "gemma2"]
        self._fallback_chains["bedrock"] = ["bedrock-claude-3-5-sonnet", "bedrock-llama3-1-405b", "amazon-nova-pro"]
        self._fallback_chains["azure"] = ["azure-gpt-4o", "azure-gpt-4o-mini", "azure-gpt-4-turbo"]
        self._fallback_chains["openrouter"] = ["anthropic/claude-3.5-sonnet", "openai/gpt-4o", "google/gemini-pro-1.5"]
        self._fallback_chains["zhipu"] = ["glm-4-plus", "glm-4-flash", "glm-4-air"]
        self._fallback_chains["moonshot"] = ["moonshot-v1-128k", "moonshot-v1-32k", "kimi-latest"]
        self._fallback_chains["mistral"] = ["mistral-large-2411", "mistral-large", "mistral-medium"]


# ============================================================================
# Factory Function
# ============================================================================


def get_llm_router() -> LLMRouter:
    """Return the singleton LLMRouter instance."""
    return LLMRouter.get_instance()
