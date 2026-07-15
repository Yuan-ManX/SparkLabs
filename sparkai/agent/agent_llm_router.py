"""
SparkLabs Agent - LLM Router & Model Integration System

Comprehensive LLM router and model integration system for the SparkLabs
AI-native game engine. Provides a unified interface for routing requests
across a diverse catalog of model providers spanning text LLMs, multimodal
models, image/video/audio/3D generation, embeddings, and open-source models
served via Ollama.

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

        This is a thin integration layer. In production it would delegate to
        the provider's SDK; here it raises NotImplementedError when no SDK
        adapter is wired so the caller can fall back to simulation.
        """
        key_entry = self._get_api_key_for_provider(provider_id)
        if key_entry is None or not key_entry.key_value:
            raise RuntimeError(
                f"No API key configured for provider {provider_id}; "
                "enable simulation mode or configure a key"
            )
        # Mark key usage
        key_entry.use_count += 1
        key_entry.last_used = time.time()
        # When a real SDK adapter is available, dispatch here. For now we
        # fall through to a simulated response so the router is usable
        # end-to-end during development.
        return self._simulate_response(request, provider_id, model_id, fallback_used)

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
        return ModelResponse(
            request_id=request.request_id,
            provider_id=provider_id,
            model_id=model_id,
            content=content,
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

        # --- Generation providers -----------------------------------------
        self._seed_image_providers()
        self._seed_video_providers()
        self._seed_audio_providers()
        self._seed_3d_providers()
        self._seed_animation_providers()
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
            ("gpt-4-turbo", [ModelType.TEXT, ModelType.VISION], 128_000, 4_096, 0.01, 0.03, 0.9, "low", True, True, True),
            ("o1", [ModelType.TEXT, ModelType.REASONING], 200_000, 100_000, 0.015, 0.06, 0.97, "high", False, False, False),
            ("o3", [ModelType.TEXT, ModelType.REASONING], 200_000, 100_000, 0.015, 0.06, 0.98, "high", False, False, False),
            ("dall-e-3", [ModelType.IMAGE_GEN], 4_000, 1, 0.04, 0.0, 0.85, "medium", False, False, False),
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
            ("gemini-1.5-pro", [ModelType.TEXT, ModelType.VISION, ModelType.MULTIMODAL], 2_000_000, 8_192, 0.00125, 0.005, 0.93, "medium", True, True, True),
            ("gemini-2.0-flash", [ModelType.TEXT, ModelType.VISION], 1_000_000, 8_192, 0.000075, 0.0003, 0.88, "low", True, True, True),
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

    def _seed_embedding_providers(self) -> None:
        # OpenAI embeddings already registered above; add Cohere reference.
        # text-embedding-3-large/small and Cohere embed-v3 are registered in
        # their respective provider seeders. This method is a placeholder for
        # future embedding-specific providers.
        pass

    def _seed_task_mappings(self) -> None:
        """Pre-configure task-to-model mappings for game development."""
        mappings = {
            TaskType.WORLD_BUILDING: "gemini-1.5-pro",
            TaskType.CHARACTER_DESIGN: "gpt-4o",
            TaskType.DIALOGUE: "claude-3-haiku",
            TaskType.CODE_GEN: "claude-3-5-sonnet",
            TaskType.ASSET_IMAGE: "flux-1",
            TaskType.ASSET_VIDEO: "runway-gen3",
            TaskType.ASSET_3D: "luma-3d-gen",
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

    def _seed_fallback_chains(self) -> None:
        """Pre-set fallback chains for the primary text providers."""
        self._fallback_chains["openai"] = ["gpt-4o", "gpt-4-turbo", "claude-3-5-sonnet", "gemini-2.0-flash", "llama-3.1-70b"]
        self._fallback_chains["anthropic"] = ["claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku", "gpt-4o"]
        self._fallback_chains["google"] = ["gemini-1.5-pro", "gemini-2.0-flash", "gpt-4o", "claude-3-5-sonnet"]
        self._fallback_chains["meta"] = ["llama-3.1-70b", "llama-3.1-405b", "gpt-4o"]
        self._fallback_chains["deepseek"] = ["deepseek-v3", "deepseek-r1", "qwen-2.5-max"]
        self._fallback_chains["qwen"] = ["qwen-2.5-max", "qwq", "deepseek-v3"]
        self._fallback_chains["ollama"] = ["llama3", "qwen2", "mistral", "gemma2"]


# ============================================================================
# Factory Function
# ============================================================================


def get_llm_router() -> LLMRouter:
    """Return the singleton LLMRouter instance."""
    return LLMRouter.get_instance()
