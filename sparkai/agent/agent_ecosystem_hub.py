"""
SparkLabs Agent - Ecosystem Hub

Unified connectivity layer that links SparkLabs agents to external AI
services, model providers, and third-party tools through a single API.
Manages API key references, service endpoints, rate limits, call
recording, and usage metrics for all external interactions.

Architecture:
  EcosystemHub
    |-- ServiceConnection (registered service with auth and rate limits)
    |-- ServiceCall (immutable record of each external API call)
    |-- ServiceMetric (time-windowed usage statistics per service)
    |-- ServiceDiscovery (catalog of available service templates)

Service Types:
  - LLM_PROVIDER: text generation, chat completion, embeddings
  - IMAGE_GENERATION: diffusion models, style transfer, upscaling
  - AUDIO_GENERATION: TTS, voice cloning, music composition
  - CODE_EXECUTION: sandboxed code runtime, REPL environments
  - VECTOR_DATABASE: embedding storage and similarity search
  - ANALYTICS: usage dashboards, cost tracking, performance reports
  - STORAGE: cloud file storage, dataset hosting, artifact management
  - CUSTOM: user-defined service via configurable endpoint

Auth Methods:
  - API_KEY: bearer token or header-based key authentication
  - OAUTH: OAuth 2.0 three-legged or client-credentials flow
  - JWT: JSON Web Token with automatic refresh support
  - NONE: public endpoint requiring no authentication

Usage:
    hub = get_ecosystem_hub()
    service = hub.register_service(
        "OpenAI GPT-4o", ServiceType.LLM_PROVIDER,
        "https://api.openai.com/v1", AuthMethod.API_KEY,
        "OPENAI_API_KEY", rate_limit_rpm=500, rate_limit_tpm=100000,
    )
    ok = hub.check_rate_limit(service.id)
    call = hub.record_call(service.id, "POST", "/chat/completions",
                           {"model": "gpt-4o"}, {"choices": [...]}, 200, 350.2, 512)
    metrics = hub.get_usage_metrics(service.id, hours=1)
    stats = hub.get_stats()
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


_time_module = time


class ServiceType(Enum):
    LLM_PROVIDER = "llm_provider"
    IMAGE_GENERATION = "image_generation"
    AUDIO_GENERATION = "audio_generation"
    CODE_EXECUTION = "code_execution"
    VECTOR_DATABASE = "vector_database"
    ANALYTICS = "analytics"
    STORAGE = "storage"
    CUSTOM = "custom"


class ServiceStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class AuthMethod(Enum):
    API_KEY = "api_key"
    OAUTH = "oauth"
    JWT = "jwt"
    NONE = "none"


class ConnectionProtocol(Enum):
    REST = "rest"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    GRAPHQL = "graphql"


@dataclass
class ServiceConnection:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    service_type: ServiceType = ServiceType.CUSTOM
    endpoint_url: str = ""
    auth_method: AuthMethod = AuthMethod.NONE
    api_key_ref: str = ""
    protocol: ConnectionProtocol = ConnectionProtocol.REST
    status: ServiceStatus = ServiceStatus.DISCONNECTED
    rate_limit_rpm: int = 0
    rate_limit_tpm: int = 0
    current_rpm: int = 0
    current_tpm: int = 0
    last_used_at: float = 0.0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "service_type": self.service_type.value,
            "endpoint_url": self.endpoint_url,
            "auth_method": self.auth_method.value,
            "api_key_ref": self.api_key_ref,
            "protocol": self.protocol.value,
            "status": self.status.value,
            "rate_limit_rpm": self.rate_limit_rpm,
            "rate_limit_tpm": self.rate_limit_tpm,
            "current_rpm": self.current_rpm,
            "current_tpm": self.current_tpm,
            "last_used_at": self.last_used_at,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class ServiceCall:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    connection_id: str = ""
    method: str = "GET"
    path: str = "/"
    request_data: Dict[str, Any] = field(default_factory=dict)
    response_data: Dict[str, Any] = field(default_factory=dict)
    status_code: int = 0
    latency_ms: float = 0.0
    tokens_used: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "connection_id": self.connection_id,
            "method": self.method,
            "path": self.path,
            "request_data": self.request_data,
            "response_data": self.response_data,
            "status_code": self.status_code,
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at,
        }


@dataclass
class ServiceMetric:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    connection_id: str = ""
    timestamp: float = field(default_factory=time.time)
    rpm: int = 0
    tpm: int = 0
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    error_count: int = 0
    total_requests: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "connection_id": self.connection_id,
            "timestamp": self.timestamp,
            "rpm": self.rpm,
            "tpm": self.tpm,
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "error_count": self.error_count,
            "total_requests": self.total_requests,
        }


SERVICE_TEMPLATES: List[Dict[str, Any]] = [
    {
        "name": "OpenAI API",
        "service_type": ServiceType.LLM_PROVIDER,
        "protocol": ConnectionProtocol.REST,
        "description": "GPT-4o, GPT-4o-mini, embeddings, and moderation",
        "default_endpoint": "https://api.openai.com/v1",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "usage",
        "rate_limit_rpm": 500,
        "rate_limit_tpm": 100000,
    },
    {
        "name": "Anthropic API",
        "service_type": ServiceType.LLM_PROVIDER,
        "protocol": ConnectionProtocol.REST,
        "description": "Claude Sonnet, Opus, and Haiku models",
        "default_endpoint": "https://api.anthropic.com/v1",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "usage",
        "rate_limit_rpm": 400,
        "rate_limit_tpm": 80000,
    },
    {
        "name": "Google AI Studio",
        "service_type": ServiceType.LLM_PROVIDER,
        "protocol": ConnectionProtocol.REST,
        "description": "Gemini Pro, Flash, and Nano model access",
        "default_endpoint": "https://generativelanguage.googleapis.com/v1beta",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "free_tier",
        "rate_limit_rpm": 60,
        "rate_limit_tpm": 30000,
    },
    {
        "name": "Groq Cloud",
        "service_type": ServiceType.LLM_PROVIDER,
        "protocol": ConnectionProtocol.REST,
        "description": "Ultra-fast inference for Llama, Mixtral, Gemma",
        "default_endpoint": "https://api.groq.com/openai/v1",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "usage",
        "rate_limit_rpm": 300,
        "rate_limit_tpm": 60000,
    },
    {
        "name": "Together AI",
        "service_type": ServiceType.LLM_PROVIDER,
        "protocol": ConnectionProtocol.REST,
        "description": "Open-source model hosting with fine-tuning",
        "default_endpoint": "https://api.together.xyz/v1",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "usage",
        "rate_limit_rpm": 300,
        "rate_limit_tpm": 60000,
    },
    {
        "name": "Azure OpenAI Service",
        "service_type": ServiceType.LLM_PROVIDER,
        "protocol": ConnectionProtocol.REST,
        "description": "Enterprise OpenAI models on Azure infrastructure",
        "default_endpoint": "https://{resource}.openai.azure.com",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "enterprise",
        "rate_limit_rpm": 1000,
        "rate_limit_tpm": 200000,
    },
    {
        "name": "Hugging Face Inference",
        "service_type": ServiceType.LLM_PROVIDER,
        "protocol": ConnectionProtocol.REST,
        "description": "Serverless inference for thousands of open models",
        "default_endpoint": "https://api-inference.huggingface.co",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "usage",
        "rate_limit_rpm": 200,
        "rate_limit_tpm": 40000,
    },
    {
        "name": "Ollama Local",
        "service_type": ServiceType.LLM_PROVIDER,
        "protocol": ConnectionProtocol.REST,
        "description": "Local LLM runtime for self-hosted inference",
        "default_endpoint": "http://localhost:11434/api",
        "auth_method": AuthMethod.NONE,
        "pricing_tier": "free",
        "rate_limit_rpm": 0,
        "rate_limit_tpm": 0,
    },
    {
        "name": "DALL-E 3",
        "service_type": ServiceType.IMAGE_GENERATION,
        "protocol": ConnectionProtocol.REST,
        "description": "OpenAI image generation with prompt following",
        "default_endpoint": "https://api.openai.com/v1/images/generations",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "usage",
        "rate_limit_rpm": 50,
        "rate_limit_tpm": 0,
    },
    {
        "name": "Midjourney API",
        "service_type": ServiceType.IMAGE_GENERATION,
        "protocol": ConnectionProtocol.REST,
        "description": "Artistic image generation via Midjourney service",
        "default_endpoint": "https://api.midjourney.com/v1",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "subscription",
        "rate_limit_rpm": 20,
        "rate_limit_tpm": 0,
    },
    {
        "name": "Stability AI",
        "service_type": ServiceType.IMAGE_GENERATION,
        "protocol": ConnectionProtocol.REST,
        "description": "Stable Diffusion models for image generation",
        "default_endpoint": "https://api.stability.ai/v1",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "usage",
        "rate_limit_rpm": 100,
        "rate_limit_tpm": 0,
    },
    {
        "name": "ElevenLabs TTS",
        "service_type": ServiceType.AUDIO_GENERATION,
        "protocol": ConnectionProtocol.REST,
        "description": "Text-to-speech with voice cloning and dubbing",
        "default_endpoint": "https://api.elevenlabs.io/v1",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "usage",
        "rate_limit_rpm": 100,
        "rate_limit_tpm": 0,
    },
    {
        "name": "Pinecone",
        "service_type": ServiceType.VECTOR_DATABASE,
        "protocol": ConnectionProtocol.REST,
        "description": "Managed vector database for semantic search",
        "default_endpoint": "https://api.pinecone.io",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "usage",
        "rate_limit_rpm": 300,
        "rate_limit_tpm": 0,
    },
    {
        "name": "Weaviate Cloud",
        "service_type": ServiceType.VECTOR_DATABASE,
        "protocol": ConnectionProtocol.GRAPHQL,
        "description": "AI-native vector database with GraphQL interface",
        "default_endpoint": "https://{cluster}.weaviate.network",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "usage",
        "rate_limit_rpm": 200,
        "rate_limit_tpm": 0,
    },
    {
        "name": "E2B Sandbox",
        "service_type": ServiceType.CODE_EXECUTION,
        "protocol": ConnectionProtocol.WEBSOCKET,
        "description": "Cloud sandbox for secure code execution",
        "default_endpoint": "https://api.e2b.dev",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "usage",
        "rate_limit_rpm": 60,
        "rate_limit_tpm": 0,
    },
    {
        "name": "Datadog Analytics",
        "service_type": ServiceType.ANALYTICS,
        "protocol": ConnectionProtocol.REST,
        "description": "Monitoring, metrics, and observability platform",
        "default_endpoint": "https://api.datadoghq.com/api/v1",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "enterprise",
        "rate_limit_rpm": 400,
        "rate_limit_tpm": 0,
    },
    {
        "name": "AWS S3 Storage",
        "service_type": ServiceType.STORAGE,
        "protocol": ConnectionProtocol.REST,
        "description": "Scalable cloud object storage for datasets and artifacts",
        "default_endpoint": "https://s3.amazonaws.com",
        "auth_method": AuthMethod.API_KEY,
        "pricing_tier": "usage",
        "rate_limit_rpm": 200,
        "rate_limit_tpm": 0,
    },
]


BUDGET_TIERS: Dict[str, Dict[str, Any]] = {
    "free": {
        "label": "Free Tier",
        "max_monthly_cost": 0.0,
        "preferred_service_types": [
            ServiceType.LLM_PROVIDER,
        ],
        "priority_services": ["Ollama Local", "Google AI Studio"],
    },
    "low": {
        "label": "Budget ($0-$50/mo)",
        "max_monthly_cost": 50.0,
        "preferred_service_types": [
            ServiceType.LLM_PROVIDER,
            ServiceType.VECTOR_DATABASE,
        ],
        "priority_services": ["Together AI", "Groq Cloud", "Weaviate Cloud"],
    },
    "medium": {
        "label": "Standard ($50-$500/mo)",
        "max_monthly_cost": 500.0,
        "preferred_service_types": [
            ServiceType.LLM_PROVIDER,
            ServiceType.IMAGE_GENERATION,
            ServiceType.AUDIO_GENERATION,
            ServiceType.VECTOR_DATABASE,
            ServiceType.CODE_EXECUTION,
        ],
        "priority_services": [
            "Anthropic API", "OpenAI API", "DALL-E 3",
            "ElevenLabs TTS", "Pinecone", "E2B Sandbox",
        ],
    },
    "high": {
        "label": "Professional ($500-$2000/mo)",
        "max_monthly_cost": 2000.0,
        "preferred_service_types": [
            ServiceType.LLM_PROVIDER,
            ServiceType.IMAGE_GENERATION,
            ServiceType.AUDIO_GENERATION,
            ServiceType.VECTOR_DATABASE,
            ServiceType.CODE_EXECUTION,
            ServiceType.ANALYTICS,
            ServiceType.STORAGE,
        ],
        "priority_services": [
            "Azure OpenAI Service", "Anthropic API",
            "Stability AI", "Midjourney API", "Datadog Analytics",
            "AWS S3 Storage",
        ],
    },
    "unlimited": {
        "label": "Enterprise (Unlimited)",
        "max_monthly_cost": float("inf"),
        "preferred_service_types": list(ServiceType),
        "priority_services": [],
    },
}


class EcosystemHub:
    """
    Unified connectivity layer for SparkLabs external AI services.

    Centralizes service registration, API key reference management,
    rate limit enforcement, call recording, and usage metrics across
    all third-party AI integrations. Provides service discovery and
    budget-aware recommendations for selecting the right provider.

    Usage:
        hub = EcosystemHub.get_instance()
        conn = hub.register_service("My LLM", ServiceType.LLM_PROVIDER,
                                     "https://api.example.com", AuthMethod.API_KEY,
                                     "MY_KEY", rate_limit_rpm=100)
        hub.check_rate_limit(conn.id)
    """

    _instance: Optional["EcosystemHub"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._connections: Dict[str, ServiceConnection] = {}
        self._calls: Dict[str, List[ServiceCall]] = {}
        self._metrics: Dict[str, List[ServiceMetric]] = {}

    @classmethod
    def get_instance(cls) -> "EcosystemHub":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register_service(
        self,
        name: str,
        service_type: ServiceType,
        endpoint_url: str,
        auth_method: AuthMethod,
        api_key_ref: str,
        protocol: ConnectionProtocol = ConnectionProtocol.REST,
        rate_limit_rpm: int = 0,
        rate_limit_tpm: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ServiceConnection:
        connection = ServiceConnection(
            name=name,
            service_type=service_type,
            endpoint_url=endpoint_url,
            auth_method=auth_method,
            api_key_ref=api_key_ref,
            protocol=protocol,
            rate_limit_rpm=rate_limit_rpm,
            rate_limit_tpm=rate_limit_tpm,
            metadata=metadata or {},
            headers=headers or {},
        )
        self._connections[connection.id] = connection
        self._calls.setdefault(connection.id, [])
        self._metrics.setdefault(connection.id, [])
        return connection

    def update_service(
        self,
        connection_id: str,
        **updates: Any,
    ) -> Optional[ServiceConnection]:
        connection = self._connections.get(connection_id)
        if connection is None:
            return None

        allowed_fields = {
            "name", "service_type", "endpoint_url", "auth_method",
            "api_key_ref", "protocol", "status", "rate_limit_rpm",
            "rate_limit_tpm", "current_rpm", "current_tpm",
            "last_used_at", "metadata", "headers",
        }

        for key, value in updates.items():
            if key in allowed_fields and hasattr(connection, key):
                if key == "service_type" and isinstance(value, ServiceType):
                    setattr(connection, key, value)
                elif key == "auth_method" and isinstance(value, AuthMethod):
                    setattr(connection, key, value)
                elif key == "protocol" and isinstance(value, ConnectionProtocol):
                    setattr(connection, key, value)
                elif key == "status" and isinstance(value, ServiceStatus):
                    setattr(connection, key, value)
                else:
                    setattr(connection, key, value)

        return connection

    def remove_service(self, connection_id: str) -> bool:
        connection = self._connections.pop(connection_id, None)
        if connection is None:
            return False
        self._calls.pop(connection_id, None)
        self._metrics.pop(connection_id, None)
        return True

    def get_service(self, connection_id: str) -> Optional[ServiceConnection]:
        return self._connections.get(connection_id)

    def list_services(
        self,
        service_type: Optional[ServiceType] = None,
        status: Optional[ServiceStatus] = None,
    ) -> List[ServiceConnection]:
        results = list(self._connections.values())
        if service_type is not None:
            results = [c for c in results if c.service_type == service_type]
        if status is not None:
            results = [c for c in results if c.status == status]
        return results

    def record_call(
        self,
        connection_id: str,
        method: str,
        path: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        status_code: int,
        latency_ms: float,
        tokens_used: int,
    ) -> ServiceCall:
        now = _time_module.time()
        call = ServiceCall(
            connection_id=connection_id,
            method=method,
            path=path,
            request_data=request_data,
            response_data=response_data,
            status_code=status_code,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            created_at=now,
        )

        self._calls.setdefault(connection_id, [])
        self._calls[connection_id].append(call)

        connection = self._connections.get(connection_id)
        if connection is not None:
            connection.last_used_at = now
            connection.current_rpm += 1
            connection.current_tpm += tokens_used

            if status_code >= 400:
                if connection.status != ServiceStatus.MAINTENANCE:
                    connection.status = ServiceStatus.ERROR

        return call

    def check_rate_limit(self, connection_id: str) -> bool:
        connection = self._connections.get(connection_id)
        if connection is None:
            return False

        if connection.status == ServiceStatus.MAINTENANCE:
            return False

        if connection.rate_limit_rpm > 0 and connection.current_rpm >= connection.rate_limit_rpm:
            connection.status = ServiceStatus.RATE_LIMITED
            return False

        if connection.rate_limit_tpm > 0 and connection.current_tpm >= connection.rate_limit_tpm:
            connection.status = ServiceStatus.RATE_LIMITED
            return False

        if connection.status == ServiceStatus.RATE_LIMITED:
            if connection.rate_limit_rpm == 0 or connection.current_rpm < connection.rate_limit_rpm:
                if connection.rate_limit_tpm == 0 or connection.current_tpm < connection.rate_limit_tpm:
                    connection.status = ServiceStatus.CONNECTED

        return True

    def reset_rate_limits(self, connection_id: str) -> bool:
        connection = self._connections.get(connection_id)
        if connection is None:
            return False
        connection.current_rpm = 0
        connection.current_tpm = 0
        if connection.status == ServiceStatus.RATE_LIMITED:
            connection.status = ServiceStatus.CONNECTED
        return True

    def get_usage_metrics(
        self,
        connection_id: str,
        hours: int = 24,
    ) -> List[ServiceMetric]:
        all_metrics = self._metrics.get(connection_id, [])
        if not all_metrics:
            return []

        now = _time_module.time()
        cutoff = now - (hours * 3600)
        return [m for m in all_metrics if m.timestamp >= cutoff]

    def compute_and_store_metric(self, connection_id: str) -> Optional[ServiceMetric]:
        connection = self._connections.get(connection_id)
        if connection is None:
            return None

        calls = self._calls.get(connection_id, [])
        now = _time_module.time()
        window_start = now - 60.0

        window_calls = [c for c in calls if c.created_at >= window_start]
        rpm = len(window_calls)
        tpm = sum(c.tokens_used for c in window_calls)

        successful = [c for c in window_calls if 200 <= c.status_code < 300]
        total = len(window_calls)
        success_rate = len(successful) / total if total > 0 else 1.0

        avg_latency = sum(c.latency_ms for c in window_calls) / total if total > 0 else 0.0
        error_count = sum(1 for c in window_calls if c.status_code >= 400)

        metric = ServiceMetric(
            connection_id=connection_id,
            timestamp=now,
            rpm=rpm,
            tpm=tpm,
            success_rate=round(success_rate, 4),
            avg_latency_ms=round(avg_latency, 2),
            error_count=error_count,
            total_requests=total,
        )

        self._metrics.setdefault(connection_id, [])
        self._metrics[connection_id].append(metric)
        return metric

    def get_aggregate_metrics(self) -> Dict[str, Any]:
        all_calls: List[ServiceCall] = []
        for call_list in self._calls.values():
            all_calls.extend(call_list)

        if not all_calls:
            return {
                "total_services": len(self._connections),
                "total_calls": 0,
                "active_services": 0,
                "services": {},
            }

        total_tokens = sum(c.tokens_used for c in all_calls)
        total_errors = sum(1 for c in all_calls if c.status_code >= 400)
        successful = [c for c in all_calls if 200 <= c.status_code < 300]
        overall_success_rate = len(successful) / len(all_calls) if all_calls else 1.0
        total_latency = sum(c.latency_ms for c in all_calls)
        avg_latency = total_latency / len(all_calls) if all_calls else 0.0

        service_summaries: Dict[str, Any] = {}
        for conn_id, conn in self._connections.items():
            conn_calls = self._calls.get(conn_id, [])
            conn_errors = sum(1 for c in conn_calls if c.status_code >= 400)
            conn_successful = [c for c in conn_calls if 200 <= c.status_code < 300]
            conn_success_rate = len(conn_successful) / len(conn_calls) if conn_calls else 1.0
            conn_tokens = sum(c.tokens_used for c in conn_calls)
            conn_latency = sum(c.latency_ms for c in conn_calls)
            conn_avg_latency = conn_latency / len(conn_calls) if conn_calls else 0.0

            service_summaries[conn_id] = {
                "name": conn.name,
                "service_type": conn.service_type.value,
                "status": conn.status.value,
                "total_calls": len(conn_calls),
                "error_count": conn_errors,
                "success_rate": round(conn_success_rate, 4),
                "total_tokens": conn_tokens,
                "avg_latency_ms": round(conn_avg_latency, 2),
                "current_rpm": conn.current_rpm,
                "current_tpm": conn.current_tpm,
            }

        return {
            "total_services": len(self._connections),
            "total_calls": len(all_calls),
            "total_tokens": total_tokens,
            "total_errors": total_errors,
            "overall_success_rate": round(overall_success_rate, 4),
            "overall_avg_latency_ms": round(avg_latency, 2),
            "active_services": sum(
                1 for c in self._connections.values()
                if c.status == ServiceStatus.CONNECTED
            ),
            "services": service_summaries,
        }

    def discover_services(
        self,
        service_type: Optional[ServiceType] = None,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for template in SERVICE_TEMPLATES:
            if service_type is not None and template["service_type"] != service_type:
                continue
            entry: Dict[str, Any] = {
                "name": template["name"],
                "service_type": template["service_type"].value,
                "protocol": template["protocol"].value,
                "description": template["description"],
                "default_endpoint": template["default_endpoint"],
                "auth_method": template["auth_method"].value,
                "pricing_tier": template["pricing_tier"],
                "rate_limit_rpm": template["rate_limit_rpm"],
                "rate_limit_tpm": template["rate_limit_tpm"],
            }
            results.append(entry)
        return results

    def get_recommended_service(
        self,
        service_type: ServiceType,
        budget: Optional[str] = None,
    ) -> Optional[ServiceConnection]:
        budget_key = budget if budget and budget in BUDGET_TIERS else "medium"
        tier = BUDGET_TIERS.get(budget_key, BUDGET_TIERS["medium"])

        for conn in self._connections.values():
            if conn.service_type == service_type:
                for priority_name in tier.get("priority_services", []):
                    if conn.name == priority_name and conn.status == ServiceStatus.CONNECTED:
                        return conn

        for conn in self._connections.values():
            if conn.service_type == service_type and conn.status == ServiceStatus.CONNECTED:
                return conn

        for template in SERVICE_TEMPLATES:
            if template["service_type"] == service_type:
                for priority_name in tier.get("priority_services", []):
                    if template["name"] == priority_name:
                        return self.register_service(
                            name=template["name"],
                            service_type=template["service_type"],
                            endpoint_url=template["default_endpoint"],
                            auth_method=template["auth_method"],
                            api_key_ref=f"{template['name'].upper().replace(' ', '_')}_KEY",
                            protocol=template["protocol"],
                            rate_limit_rpm=template["rate_limit_rpm"],
                            rate_limit_tpm=template["rate_limit_tpm"],
                        )

        return None

    def set_service_status(
        self,
        connection_id: str,
        status: ServiceStatus,
    ) -> bool:
        connection = self._connections.get(connection_id)
        if connection is None:
            return False
        connection.status = status
        return True

    def get_service_calls(
        self,
        connection_id: str,
        limit: int = 100,
    ) -> List[ServiceCall]:
        calls = self._calls.get(connection_id, [])
        return calls[-limit:] if calls else []

    def get_connection_for_request(
        self,
        service_type: ServiceType,
        preferred_name: Optional[str] = None,
    ) -> Optional[ServiceConnection]:
        candidates = [
            c for c in self._connections.values()
            if c.service_type == service_type and c.status == ServiceStatus.CONNECTED
        ]

        if not candidates:
            candidates = [
                c for c in self._connections.values()
                if c.service_type == service_type and c.status != ServiceStatus.MAINTENANCE
            ]

        if not candidates:
            return None

        if preferred_name:
            for conn in candidates:
                if conn.name == preferred_name:
                    return conn

        best_candidate = None
        best_score = float("inf")
        for conn in candidates:
            rpm_score = conn.current_rpm / max(conn.rate_limit_rpm, 1)
            best_candidate = best_candidate or conn
            if rpm_score < best_score:
                best_score = rpm_score
                best_candidate = conn

        return best_candidate

    def get_stats(self) -> Dict[str, Any]:
        total_services = len(self._connections)

        all_calls_count = sum(len(c) for c in self._calls.values())
        all_tokens = 0
        for conn_calls in self._calls.values():
            all_tokens += sum(c.tokens_used for c in conn_calls)

        type_counts: Dict[str, int] = {}
        for conn in self._connections.values():
            key = conn.service_type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        status_counts: Dict[str, int] = {}
        for conn in self._connections.values():
            key = conn.status.value
            status_counts[key] = status_counts.get(key, 0) + 1

        rate_limited_ids: List[str] = [
            conn.id for conn in self._connections.values()
            if conn.status == ServiceStatus.RATE_LIMITED
        ]

        error_ids: List[str] = [
            conn.id for conn in self._connections.values()
            if conn.status == ServiceStatus.ERROR
        ]

        total_metrics = sum(len(m) for m in self._metrics.values())

        top_services: List[Dict[str, Any]] = []
        for conn in self._connections.values():
            calls = self._calls.get(conn.id, [])
            if calls:
                top_services.append({
                    "id": conn.id,
                    "name": conn.name,
                    "type": conn.service_type.value,
                    "total_calls": len(calls),
                    "total_tokens": sum(c.tokens_used for c in calls),
                    "avg_latency_ms": round(
                        sum(c.latency_ms for c in calls) / len(calls), 2
                    ),
                })

        top_services.sort(key=lambda s: s["total_calls"], reverse=True)
        top_services = top_services[:10]

        return {
            "total_services": total_services,
            "total_calls_recorded": all_calls_count,
            "total_tokens_consumed": all_tokens,
            "total_metrics_snapshots": total_metrics,
            "services_by_type": type_counts,
            "services_by_status": status_counts,
            "rate_limited_services": len(rate_limited_ids),
            "error_services": len(error_ids),
            "rate_limited_ids": rate_limited_ids[:20],
            "error_ids": error_ids[:20],
            "top_services_by_calls": top_services,
            "connected_service_count": sum(
                1 for c in self._connections.values()
                if c.status == ServiceStatus.CONNECTED
            ),
            "registered_protocols": list(
                set(c.protocol.value for c in self._connections.values())
            ),
            "registered_auth_methods": list(
                set(c.auth_method.value for c in self._connections.values())
            ),
            "discoverable_service_count": len(SERVICE_TEMPLATES),
            "budget_tiers_available": list(BUDGET_TIERS.keys()),
        }

    def clear(self) -> None:
        self._connections.clear()
        self._calls.clear()
        self._metrics.clear()


def get_ecosystem_hub() -> EcosystemHub:
    return EcosystemHub.get_instance()