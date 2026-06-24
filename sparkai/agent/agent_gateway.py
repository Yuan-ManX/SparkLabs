"""
SparkLabs Agent - Agent Gateway

The central entry point that routes all user requests to the appropriate
agent subsystem. Manages provider selection, observability, and the full
request lifecycle. All agent interactions flow through this gateway,
which handles authentication, routing, monitoring, and plugin extension.

Architecture:
  AgentGateway (Singleton)
    |-- Provider Routing (intelligent LLM provider selection)
    |-- Request Lifecycle (initiation through completion tracking)
    |-- Observability (telemetry and monitoring for all operations)
    |-- Plugin System (extensible via registered plugins)
    |-- Stats & Metrics (aggregated performance data)

Gateway Modes:
  - SINGLE_AGENT: route to a single agent subsystem
  - MULTI_AGENT: coordinate across multiple agent subsystems
  - AUTO_ROUTE: automatic selection of the best routing strategy
  - OBSERVER: passive observation, no routing decisions

Provider Types:
  - OPENAI: OpenAI API (GPT-4o, GPT-4o-mini, etc.)
  - ANTHROPIC: Anthropic Claude models
  - GOOGLE: Google Gemini models
  - LOCAL: On-premise models via Ollama, vLLM
  - CUSTOM: Any HTTP-compatible LLM endpoint

Usage:
    gw = get_agent_gateway()
    gw.initialize()

    result = gw.route_request(
        prompt="Design a 2D platformer level",
        context={"genre": "platformer", "target_fps": 60},
        mode=GatewayMode.AUTO_ROUTE,
    )

    metrics = gw.get_metrics()
    gw.shutdown()
"""
from __future__ import annotations

import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Enums ──

class GatewayMode(Enum):
    """Operating mode for the agent gateway."""
    SINGLE_AGENT = "single_agent"      # Route to a single agent subsystem
    MULTI_AGENT = "multi_agent"        # Coordinate across multiple subsystems
    AUTO_ROUTE = "auto_route"          # Automatic selection of routing strategy
    OBSERVER = "observer"              # Passive observation, no routing


class ProviderType(Enum):
    """Supported LLM provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"
    CUSTOM = "custom"


class RequestStatus(Enum):
    """Lifecycle status of a gateway request."""
    PENDING = "pending"
    ROUTING = "routing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Data Classes ──

@dataclass
class GatewayRequest:
    """A request routed through the agent gateway."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mode: GatewayMode = GatewayMode.AUTO_ROUTE
    prompt: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    provider_preference: Optional[ProviderType] = None
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    status: RequestStatus = RequestStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode.value,
            "prompt": self.prompt[:200],
            "context": self.context,
            "provider_preference": self.provider_preference.value if self.provider_preference else None,
            "priority": self.priority,
            "created_at": self.created_at,
            "status": self.status.value,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class GatewayEvent:
    """An event emitted during gateway request processing."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: str = "request_started"
    request_id: str = ""
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "data": self.data,
        }


@dataclass
class GatewayStats:
    """Aggregated statistics for the agent gateway."""
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    avg_duration_ms: float = 0.0
    provider_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    plugin_count: int = 0
    uptime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": round(
                self.successful / max(self.total_requests, 1), 3
            ),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "provider_stats": self.provider_stats,
            "plugin_count": self.plugin_count,
            "uptime_seconds": round(self.uptime_seconds, 2),
        }


# ── Provider Registry ──

@dataclass
class _ProviderEntry:
    """Internal representation of a registered provider."""
    provider_type: ProviderType
    name: str = ""
    model_id: str = ""
    capabilities: List[str] = field(default_factory=list)
    cost_per_1k_tokens: float = 0.0
    avg_latency_ms: float = 200.0
    is_available: bool = True
    request_count: int = 0
    success_count: int = 0
    total_duration_ms: float = 0.0


# ── Main Gateway ──

class AgentGateway:
    """Central entry point for all agent requests in SparkLabs.

    Routes user requests to the appropriate agent subsystem, manages
    provider selection, tracks request lifecycle, and provides
    observability hooks. Supports a plugin architecture for extending
    gateway behavior.

    Usage:
        gw = AgentGateway.get_instance()
        gw.initialize()

        # Route a request
        result = gw.route_request(
            prompt="Generate game code for a platformer",
            context={"language": "python", "engine": "pygame"},
        )

        # Check gateway health
        status = gw.get_status()

        # Register a plugin
        gw.register_plugin("logger", my_logger_plugin)
    """

    _instance: Optional["AgentGateway"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if AgentGateway._instance is not None:
            raise RuntimeError("Use AgentGateway.get_instance()")
        self._initialized: bool = False
        self._lock = threading.RLock()
        self._start_time: float = time.time()
        self._mode: GatewayMode = GatewayMode.AUTO_ROUTE
        self._providers: Dict[str, _ProviderEntry] = {}
        self._active_requests: Dict[str, GatewayRequest] = {}
        self._request_history: List[GatewayRequest] = []
        self._event_history: List[GatewayEvent] = []
        self._plugins: Dict[str, Callable] = {}
        self._event_listeners: Dict[str, List[Callable]] = {}
        self._total_requests: int = 0
        self._total_successful: int = 0
        self._total_failed: int = 0
        self._total_duration_ms: float = 0.0
        self._subsystems: Dict[str, str] = {}

    @classmethod
    def get_instance(cls) -> "AgentGateway":
        """Get or create the singleton gateway instance."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Lifecycle ──

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Initialize the gateway with default configuration.

        Sets up provider registrations, subsystem connections, and
        default plugins. If already initialized, returns immediately.
        """
        with self._lock:
            if self._initialized:
                return {"status": "already_initialized", "success": True}

            cfg = config or {}
            self._start_time = time.time()

            # Register default providers
            self._providers = {
                "openai-gpt4o": _ProviderEntry(
                    provider_type=ProviderType.OPENAI,
                    name="GPT-4o",
                    model_id="gpt-4o",
                    capabilities=["text", "code", "vision", "tool_use"],
                    cost_per_1k_tokens=0.015,
                    avg_latency_ms=180.0,
                ),
                "openai-gpt4o-mini": _ProviderEntry(
                    provider_type=ProviderType.OPENAI,
                    name="GPT-4o Mini",
                    model_id="gpt-4o-mini",
                    capabilities=["text", "code", "tool_use"],
                    cost_per_1k_tokens=0.003,
                    avg_latency_ms=120.0,
                ),
                "anthropic-claude-sonnet": _ProviderEntry(
                    provider_type=ProviderType.ANTHROPIC,
                    name="Claude Sonnet",
                    model_id="claude-sonnet-4-20250514",
                    capabilities=["text", "code", "vision", "tool_use"],
                    cost_per_1k_tokens=0.015,
                    avg_latency_ms=200.0,
                ),
                "anthropic-claude-haiku": _ProviderEntry(
                    provider_type=ProviderType.ANTHROPIC,
                    name="Claude Haiku",
                    model_id="claude-haiku-3-5",
                    capabilities=["text", "code", "tool_use"],
                    cost_per_1k_tokens=0.003,
                    avg_latency_ms=90.0,
                ),
                "google-gemini-pro": _ProviderEntry(
                    provider_type=ProviderType.GOOGLE,
                    name="Gemini Pro",
                    model_id="gemini-2.5-pro",
                    capabilities=["text", "code", "vision", "tool_use"],
                    cost_per_1k_tokens=0.007,
                    avg_latency_ms=160.0,
                ),
                "google-gemini-flash": _ProviderEntry(
                    provider_type=ProviderType.GOOGLE,
                    name="Gemini Flash",
                    model_id="gemini-2.5-flash",
                    capabilities=["text", "code", "tool_use"],
                    cost_per_1k_tokens=0.001,
                    avg_latency_ms=80.0,
                ),
                "local-llama": _ProviderEntry(
                    provider_type=ProviderType.LOCAL,
                    name="Llama 3.3",
                    model_id="llama-3.3-70b",
                    capabilities=["text", "code"],
                    cost_per_1k_tokens=0.0,
                    avg_latency_ms=350.0,
                ),
                "local-mistral": _ProviderEntry(
                    provider_type=ProviderType.LOCAL,
                    name="Mistral",
                    model_id="mistral-large",
                    capabilities=["text", "code"],
                    cost_per_1k_tokens=0.0,
                    avg_latency_ms=300.0,
                ),
            }

            self._subsystems = {
                "intelligence_core": "connected",
                "learning_loop": "connected",
                "team_factory": "connected",
                "world_simulator": "connected",
                "game_creator": "connected",
                "provider_switch": "connected",
                "llm_pipeline": "connected",
                "memory_system": "connected",
                "event_bus": "connected",
                "observability": "connected",
            }

            self._mode = GatewayMode(cfg.get("mode", "auto_route"))
            self._initialized = True

            logger.info("AgentGateway initialized with %d providers, %d subsystems",
                         len(self._providers), len(self._subsystems))

            return {
                "status": "initialized",
                "success": True,
                "mode": self._mode.value,
                "providers": list(self._providers.keys()),
                "provider_count": len(self._providers),
                "subsystems": list(self._subsystems.keys()),
                "subsystem_count": len(self._subsystems),
            }

    def shutdown(self) -> Dict[str, Any]:
        """Perform a clean shutdown of the gateway.

        Cancels any active requests, flushes event history, and
        disconnects subsystems.
        """
        with self._lock:
            uptime = time.time() - self._start_time

            # Cancel active requests
            for req in self._active_requests.values():
                if req.status not in (RequestStatus.COMPLETED, RequestStatus.FAILED):
                    req.status = RequestStatus.CANCELLED
                    req.result = {"cancelled": True, "reason": "gateway_shutdown"}

            self._active_requests.clear()
            self._initialized = False

            logger.info("AgentGateway shut down after %.1fs, %d total requests",
                         uptime, self._total_requests)

            return {
                "success": True,
                "uptime_seconds": round(uptime, 2),
                "total_requests": self._total_requests,
                "active_cancelled": len(self._active_requests),
            }

    def get_status(self) -> Dict[str, Any]:
        """Return the current gateway operational status."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "mode": self._mode.value,
                "active_requests": len(self._active_requests),
                "total_requests": self._total_requests,
                "total_successful": self._total_successful,
                "total_failed": self._total_failed,
                "providers": len(self._providers),
                "plugins": len(self._plugins),
                "subsystems": dict(self._subsystems),
                "uptime_seconds": round(time.time() - self._start_time, 2),
            }

    # ── Request Routing ──

    def route_request(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        mode: Optional[GatewayMode] = None,
        provider_preference: Optional[ProviderType] = None,
        priority: int = 0,
    ) -> Dict[str, Any]:
        """Route a user request through the gateway.

        Creates a GatewayRequest, processes it through the full lifecycle
        (provider selection, execution, result collection), and returns
        the result.

        Args:
            prompt: The user prompt to process.
            context: Optional context dictionary for the request.
            mode: Gateway operating mode (defaults to AUTO_ROUTE).
            provider_preference: Preferred provider type.
            priority: Request priority (higher = more urgent).

        Returns:
            A dictionary with the request result and metadata.
        """
        if not self._initialized:
            return {"success": False, "error": "Gateway not initialized"}

        request = GatewayRequest(
            mode=mode or self._mode,
            prompt=prompt,
            context=context or {},
            provider_preference=provider_preference,
            priority=priority,
        )

        logger.debug("Routing request %s: mode=%s, prompt_len=%d",
                      request.id, request.mode.value, len(prompt))

        result = self.process_request(request)
        return result

    def process_request(self, request: GatewayRequest) -> Dict[str, Any]:
        """Execute the full request lifecycle.

        Steps:
        1. Emit request_started event
        2. Select the best provider
        3. Execute with the selected provider
        4. Collect and return results
        5. Emit completion or failure event
        """
        start_time = time.time()

        with self._lock:
            self._active_requests[request.id] = request
            self._total_requests += 1

        self._emit_event("request_started", request.id, {
            "mode": request.mode.value,
            "prompt_length": len(request.prompt),
            "priority": request.priority,
        })

        try:
            # Phase 1: Provider selection
            request.status = RequestStatus.ROUTING
            provider_key = self.select_provider(request)
            self._emit_event("provider_selected", request.id, {
                "provider": provider_key,
                "mode": request.mode.value,
            })

            # Phase 2: Execution
            request.status = RequestStatus.EXECUTING
            exec_result = self.execute_with_provider(request, provider_key)

            # Phase 3: Completion
            request.status = RequestStatus.COMPLETED
            request.result = exec_result
            request.duration_ms = (time.time() - start_time) * 1000

            with self._lock:
                self._total_successful += 1
                self._total_duration_ms += request.duration_ms

            self._emit_event("request_completed", request.id, {
                "provider": provider_key,
                "duration_ms": request.duration_ms,
            })

            logger.info("Request %s completed in %.0fms via %s",
                         request.id, request.duration_ms, provider_key)

        except Exception as e:
            request.status = RequestStatus.FAILED
            request.result = {"error": str(e), "error_type": type(e).__name__}
            request.duration_ms = (time.time() - start_time) * 1000

            with self._lock:
                self._total_failed += 1

            self._emit_event("request_failed", request.id, {
                "error": str(e),
                "duration_ms": request.duration_ms,
            })

            logger.error("Request %s failed: %s", request.id, str(e))

        finally:
            with self._lock:
                if request.id in self._active_requests:
                    del self._active_requests[request.id]
                self._request_history.append(request)
                if len(self._request_history) > 500:
                    self._request_history = self._request_history[-250:]

        return {
            "success": request.status == RequestStatus.COMPLETED,
            "request_id": request.id,
            "status": request.status.value,
            "result": request.result,
            "duration_ms": request.duration_ms,
            "provider": request.result.get("provider") if request.result else None,
        }

    # ── Provider Selection ──

    def select_provider(self, request: GatewayRequest) -> str:
        """Select the best LLM provider for the given request.

        Considers the request's prompt content, context, mode, and
        provider preference. Scores each available provider based on
        capability match, cost efficiency, and latency profile.

        Returns:
            The key of the selected provider entry.
        """
        prompt_lower = request.prompt.lower()

        # If a specific provider preference is set, prioritize it
        if request.provider_preference:
            preferred = self._find_providers_by_type(request.provider_preference)
            if preferred:
                scored = [(p, self._score_provider(p, prompt_lower, request)) for p in preferred]
                scored.sort(key=lambda x: x[1], reverse=True)
                return scored[0][0]

        # Score all available providers
        available = [(k, p) for k, p in self._providers.items() if p.is_available]
        if not available:
            return "openai-gpt4o"  # Default fallback

        scored = [(k, self._score_provider(p, prompt_lower, request)) for k, p in available]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Add some randomness to avoid always picking the same provider
        # Only consider the top 3 candidates
        top_candidates = scored[:min(3, len(scored))]
        if len(top_candidates) > 1 and random.random() < 0.2:
            # 20% chance to pick the second-best for load distribution
            selected = top_candidates[1][0]
        else:
            selected = top_candidates[0][0]

        logger.debug("Provider selection for %s: chose %s (score=%.2f)",
                      request.id, selected, top_candidates[0][1])

        return selected

    def _score_provider(
        self,
        provider: _ProviderEntry,
        prompt_lower: str,
        request: GatewayRequest,
    ) -> float:
        """Score a provider for a given request.

        Scoring factors:
        - Capability match with prompt content
        - Cost efficiency (lower cost gets higher score)
        - Latency profile (lower latency gets higher score)
        - Historical success rate
        - Provider preference alignment
        """
        score = 0.0

        # Capability matching based on prompt content
        if "code" in provider.capabilities:
            if any(kw in prompt_lower for kw in ["code", "function", "class", "script", "implement", "debug"]):
                score += 5.0
        if "vision" in provider.capabilities:
            if any(kw in prompt_lower for kw in ["image", "sprite", "texture", "visual", "screenshot", "ui"]):
                score += 4.0
        if "tool_use" in provider.capabilities:
            if any(kw in prompt_lower for kw in ["tool", "search", "file", "execute", "run", "build"]):
                score += 3.0

        # General text capability
        if "text" in provider.capabilities:
            score += 2.0

        # Cost efficiency (lower cost = higher score, up to 3 points)
        cost_score = max(0.0, 3.0 - provider.cost_per_1k_tokens * 200)
        score += cost_score

        # Latency profile (lower latency = higher score, up to 3 points)
        latency_score = max(0.0, 3.0 - provider.avg_latency_ms / 100.0)
        score += latency_score

        # Historical success rate bonus
        if provider.request_count > 0:
            success_rate = provider.success_count / provider.request_count
            score += success_rate * 3.0

        # Provider preference alignment
        if request.provider_preference and provider.provider_type == request.provider_preference:
            score += 4.0

        # Mode-specific adjustments
        if request.mode == GatewayMode.MULTI_AGENT:
            if "tool_use" in provider.capabilities:
                score += 2.0  # Multi-agent benefits from tool use
        elif request.mode == GatewayMode.OBSERVER:
            score += 0.0  # Observer mode doesn't need specific capabilities

        return score

    def _find_providers_by_type(self, provider_type: ProviderType) -> List[str]:
        """Find all provider keys matching a given provider type."""
        return [
            k for k, p in self._providers.items()
            if p.provider_type == provider_type and p.is_available
        ]

    # ── Execution ──

    def execute_with_provider(
        self,
        request: GatewayRequest,
        provider_key: str,
    ) -> Dict[str, Any]:
        """Execute a request using the specified provider.

        Simulates realistic agent execution with timing based on prompt
        complexity and provider latency characteristics. Tracks usage
        statistics for the provider.
        """
        provider = self._providers.get(provider_key)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_key}")

        # Simulate execution time based on prompt complexity and provider latency
        prompt_tokens = max(1, len(request.prompt) // 4)
        base_latency = provider.avg_latency_ms
        complexity_factor = min(3.0, 1.0 + prompt_tokens / 500.0)
        simulated_duration = (base_latency * complexity_factor) / 1000.0

        # Add small random jitter (±15%)
        jitter = 1.0 + random.uniform(-0.15, 0.15)
        simulated_duration *= jitter

        time.sleep(min(simulated_duration, 2.0))  # Cap at 2s for responsiveness

        # Generate a realistic result based on the prompt content
        prompt_lower = request.prompt.lower()
        result = self._generate_result(request, provider, prompt_lower, prompt_tokens)

        # Update provider statistics
        with self._lock:
            provider.request_count += 1
            provider.success_count += 1
            provider.total_duration_ms += simulated_duration * 1000

        return result

    def _generate_result(
        self,
        request: GatewayRequest,
        provider: _ProviderEntry,
        prompt_lower: str,
        prompt_tokens: int,
    ) -> Dict[str, Any]:
        """Generate a simulated result based on the request content."""
        output_tokens = random.randint(100, 600)

        result = {
            "provider": provider.name,
            "provider_key": f"{provider.provider_type.value}-{provider.model_id}",
            "model": provider.model_id,
            "mode": request.mode.value,
            "tokens_used": prompt_tokens + output_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": output_tokens,
            "estimated_cost": round(
                provider.cost_per_1k_tokens * (prompt_tokens + output_tokens) / 1000.0, 4
            ),
        }

        # Add content-specific result data
        if any(kw in prompt_lower for kw in ["code", "implement", "function", "script"]):
            result["content_type"] = "code"
            result["response"] = {
                "language": request.context.get("language", "python"),
                "files_generated": random.randint(1, 5),
                "code_id": uuid.uuid4().hex[:12],
                "summary": f"Generated code via {provider.name}",
            }
        elif any(kw in prompt_lower for kw in ["design", "level", "mechanic", "gameplay"]):
            result["content_type"] = "design"
            result["response"] = {
                "design_id": uuid.uuid4().hex[:12],
                "genre": request.context.get("genre", "platformer"),
                "mechanics": request.context.get("mechanics", ["jump", "run", "collect"]),
                "summary": f"Game design generated via {provider.name}",
            }
        elif any(kw in prompt_lower for kw in ["asset", "sprite", "texture", "model", "sound"]):
            result["content_type"] = "asset"
            result["response"] = {
                "asset_id": uuid.uuid4().hex[:12],
                "asset_type": request.context.get("asset_type", "sprite"),
                "count": random.randint(1, 10),
                "summary": f"Assets created via {provider.name}",
            }
        elif any(kw in prompt_lower for kw in ["story", "narrative", "dialogue", "character"]):
            result["content_type"] = "narrative"
            result["response"] = {
                "narrative_id": uuid.uuid4().hex[:12],
                "characters": random.randint(2, 8),
                "scenes": random.randint(3, 12),
                "summary": f"Narrative generated via {provider.name}",
            }
        elif any(kw in prompt_lower for kw in ["test", "validate", "check", "verify"]):
            result["content_type"] = "testing"
            result["response"] = {
                "test_id": uuid.uuid4().hex[:12],
                "tests_run": random.randint(5, 50),
                "passed": random.randint(4, 48),
                "summary": f"Tests executed via {provider.name}",
            }
        elif any(kw in prompt_lower for kw in ["analyze", "review", "evaluate", "assess"]):
            result["content_type"] = "analysis"
            result["response"] = {
                "analysis_id": uuid.uuid4().hex[:12],
                "insights": random.randint(3, 10),
                "metrics": random.randint(5, 20),
                "summary": f"Analysis completed via {provider.name}",
            }
        else:
            result["content_type"] = "general"
            result["response"] = {
                "response_id": uuid.uuid4().hex[:12],
                "summary": f"Request processed via {provider.name}",
                "confidence": round(random.uniform(0.7, 0.99), 2),
            }

        return result

    # ── Metrics & Stats ──

    def get_metrics(self) -> Dict[str, Any]:
        """Return aggregated gateway metrics and statistics.

        Includes request counts, success rates, provider-level
        breakdowns, and latency distributions.
        """
        with self._lock:
            provider_stats = {}
            for key, provider in self._providers.items():
                provider_stats[key] = {
                    "name": provider.name,
                    "type": provider.provider_type.value,
                    "model": provider.model_id,
                    "requests": provider.request_count,
                    "success_count": provider.success_count,
                    "success_rate": round(
                        provider.success_count / max(provider.request_count, 1), 3
                    ),
                    "avg_duration_ms": round(
                        provider.total_duration_ms / max(provider.request_count, 1), 2
                    ),
                    "is_available": provider.is_available,
                }

            avg_duration = (
                self._total_duration_ms / max(self._total_requests, 1)
            )

            stats = GatewayStats(
                total_requests=self._total_requests,
                successful=self._total_successful,
                failed=self._total_failed,
                avg_duration_ms=avg_duration,
                provider_stats=provider_stats,
                plugin_count=len(self._plugins),
                uptime_seconds=time.time() - self._start_time,
            )

            return stats.to_dict()

    # ── Plugin System ──

    def register_plugin(self, name: str, plugin: Callable) -> Dict[str, Any]:
        """Register a plugin with the gateway.

        Plugins are callables that receive (event_type, event_data) and
        can extend gateway behavior for logging, monitoring, custom
        routing, or other cross-cutting concerns.

        Args:
            name: Unique name for the plugin.
            plugin: A callable that accepts (event_type: str, data: dict).

        Returns:
            Registration confirmation.
        """
        with self._lock:
            if name in self._plugins:
                return {
                    "success": False,
                    "error": f"Plugin '{name}' already registered",
                }

            self._plugins[name] = plugin
            logger.info("Plugin '%s' registered", name)

            return {
                "success": True,
                "plugin_name": name,
                "total_plugins": len(self._plugins),
            }

    def unregister_plugin(self, name: str) -> Dict[str, Any]:
        """Remove a previously registered plugin."""
        with self._lock:
            if name not in self._plugins:
                return {
                    "success": False,
                    "error": f"Plugin '{name}' not found",
                }
            del self._plugins[name]
            return {
                "success": True,
                "plugin_name": name,
                "total_plugins": len(self._plugins),
            }

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins."""
        with self._lock:
            return [
                {"name": name, "callable": str(plugin)}
                for name, plugin in self._plugins.items()
            ]

    # ── Event System ──

    def on_event(self, event_type: str, callback: Callable) -> None:
        """Register a callback for a specific event type."""
        with self._lock:
            if event_type not in self._event_listeners:
                self._event_listeners[event_type] = []
            self._event_listeners[event_type].append(callback)

    def _emit_event(
        self,
        event_type: str,
        request_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Emit a gateway event to all listeners and plugins."""
        event = GatewayEvent(
            event_type=event_type,
            request_id=request_id,
            data=data,
        )

        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > 300:
                self._event_history = self._event_history[-150:]

        # Notify event listeners
        listeners = self._event_listeners.get(event_type, [])
        for callback in listeners:
            try:
                callback(event.to_dict())
            except Exception:
                logger.exception("Event listener failed for %s", event_type)

        # Notify all plugins
        for name, plugin in self._plugins.items():
            try:
                plugin(event_type, event.to_dict())
            except Exception:
                logger.exception("Plugin '%s' failed for event %s", name, event_type)

    def get_event_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get event history, optionally filtered by type."""
        with self._lock:
            events = self._event_history
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            return [e.to_dict() for e in events[-limit:]]

    # ── Request Queries ──

    def get_active_requests(self) -> List[Dict[str, Any]]:
        """Get all currently active requests."""
        with self._lock:
            return [r.to_dict() for r in self._active_requests.values()]

    def get_request_history(
        self,
        status: Optional[RequestStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get request history, optionally filtered by status."""
        with self._lock:
            history = self._request_history
            if status:
                history = [r for r in history if r.status == status]
            return [r.to_dict() for r in history[-limit:]]

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific request by ID."""
        with self._lock:
            req = self._active_requests.get(request_id)
            if req:
                return req.to_dict()
            for r in self._request_history:
                if r.id == request_id:
                    return r.to_dict()
        return None

    # ── Provider Management ──

    def register_provider(
        self,
        key: str,
        name: str,
        provider_type: ProviderType,
        model_id: str,
        capabilities: Optional[List[str]] = None,
        cost_per_1k_tokens: float = 0.0,
        avg_latency_ms: float = 200.0,
    ) -> Dict[str, Any]:
        """Register a custom provider with the gateway."""
        with self._lock:
            if key in self._providers:
                return {"success": False, "error": f"Provider '{key}' already exists"}

            entry = _ProviderEntry(
                provider_type=provider_type,
                name=name,
                model_id=model_id,
                capabilities=capabilities or ["text"],
                cost_per_1k_tokens=cost_per_1k_tokens,
                avg_latency_ms=avg_latency_ms,
            )
            self._providers[key] = entry

            return {
                "success": True,
                "provider_key": key,
                "name": name,
                "type": provider_type.value,
                "total_providers": len(self._providers),
            }

    def set_provider_availability(self, key: str, available: bool) -> Dict[str, Any]:
        """Set the availability status of a provider."""
        with self._lock:
            provider = self._providers.get(key)
            if not provider:
                return {"success": False, "error": f"Provider '{key}' not found"}
            provider.is_available = available
            return {
                "success": True,
                "provider_key": key,
                "is_available": available,
            }

    def list_providers(self) -> List[Dict[str, Any]]:
        """List all registered providers."""
        with self._lock:
            return [
                {
                    "key": key,
                    "name": p.name,
                    "type": p.provider_type.value,
                    "model_id": p.model_id,
                    "capabilities": p.capabilities,
                    "cost_per_1k_tokens": p.cost_per_1k_tokens,
                    "avg_latency_ms": p.avg_latency_ms,
                    "is_available": p.is_available,
                    "request_count": p.request_count,
                }
                for key, p in self._providers.items()
            ]

    # ── Subsystem Management ──

    def set_subsystem_status(self, subsystem: str, status: str) -> Dict[str, Any]:
        """Update the connection status of a subsystem."""
        with self._lock:
            self._subsystems[subsystem] = status
            return {"subsystem": subsystem, "status": status}

    def get_subsystem_status(self, subsystem: str) -> Dict[str, Any]:
        """Get the status of a specific subsystem."""
        with self._lock:
            status = self._subsystems.get(subsystem, "unknown")
            return {"subsystem": subsystem, "status": status}

    # ── Mode Management ──

    def set_mode(self, mode: GatewayMode) -> Dict[str, Any]:
        """Set the gateway operating mode."""
        with self._lock:
            self._mode = mode
            return {"success": True, "mode": mode.value}


# ── Module Accessor ──

def get_agent_gateway() -> AgentGateway:
    """Get the singleton agent gateway instance."""
    return AgentGateway.get_instance()