"""
SparkLabs Agent - LLM Orchestrator

Central LLM orchestration engine that provides a unified interface for all
agent modules to call AI APIs for reasoning, generation, and analysis.
Handles provider management, prompt templating, token tracking, rate
limiting, streaming, caching, and fallback chains.

Architecture:
  LLMOrchestratorEngine
    |-- ProviderRegistry (OpenAI, Anthropic, local, custom)
    |-- PromptTemplateLibrary (templated prompts with context injection)
    |-- TokenTracker (usage stats and cost management)
    |-- RateLimiter (throttling and retry logic)
    |-- ResponseCache (keyed cache for repeated queries)
    |-- StreamingAdapter (chunked response delivery)
    |-- FallbackChain (primary -> secondary provider cascade)

Provider Flow:
  Request arrives -> check cache -> resolve template -> select provider
  -> apply rate limit -> dispatch to API -> parse response -> track tokens
  -> cache result -> return LLMResponse
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generator, List, Optional


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    CUSTOM = "custom"


class LLMRequestType(Enum):
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    FUNCTION_CALL = "function_call"


@dataclass
class PromptTemplate:
    name: str
    template: str
    variables: Dict[str, Any] = field(default_factory=dict)
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "template_id": self.template_id,
            "template": self.template[:200],
            "variable_count": len(self.variables),
            "variable_names": list(self.variables.keys()),
            "system_prompt": self.system_prompt[:200],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "created_at": self.created_at,
            "usage_count": self.usage_count,
        }

    def render(self, variables: Optional[Dict[str, Any]] = None) -> str:
        merged = {**self.variables, **(variables or {})}
        result = self.template
        for key, value in merged.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value))
        return result


@dataclass
class LLMResponse:
    content: str
    provider: LLMProvider
    model: str
    tokens_used: int
    latency_ms: float
    finish_reason: str
    function_calls: Optional[List[Dict[str, Any]]] = None
    response_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id": self.response_id,
            "content": self.content[:500],
            "provider": self.provider.value,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "finish_reason": self.finish_reason,
            "has_function_calls": self.function_calls is not None,
            "function_call_count": len(self.function_calls) if self.function_calls else 0,
            "created_at": self.created_at,
        }


class LLMOrchestratorEngine:
    """
    Central LLM orchestration engine for the SparkLabs AI-native game engine.

    Provides a unified interface for all agent modules to interact with AI
    APIs. Manages multiple providers, prompt templates, response caching,
    token tracking, rate limiting, streaming, and fallback chains.
    """

    _instance: Optional["LLMOrchestratorEngine"] = None
    _lock = threading.RLock()

    _MAX_CACHE_ENTRIES: int = 500
    _DEFAULT_TEMPERATURE: float = 0.7
    _DEFAULT_MAX_TOKENS: int = 2048
    _DEFAULT_RETRY_COUNT: int = 3
    _DEFAULT_RETRY_DELAY: float = 1.0
    _DEFAULT_RATE_LIMIT_RPM: int = 60
    _FALLBACK_MODELS: Dict[str, str] = {
        "gpt-4": "gpt-3.5-turbo",
        "gpt-4-turbo": "gpt-3.5-turbo",
        "claude-3-opus": "claude-3-sonnet",
        "claude-3-5-sonnet": "claude-3-haiku",
    }

    def __init__(self) -> None:
        self._providers: Dict[str, Dict[str, Any]] = {}
        self._templates: Dict[str, PromptTemplate] = {}
        self._cache: Dict[str, LLMResponse] = {}
        self._cache_keys: List[str] = []
        self._usage_stats: Dict[str, Any] = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_latency_ms": 0.0,
            "by_provider": {},
            "by_model": {},
            "by_request_type": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
        }
        self._rate_limit_timestamps: Dict[str, List[float]] = {}
        self._retry_count: int = self._DEFAULT_RETRY_COUNT
        self._retry_delay: float = self._DEFAULT_RETRY_DELAY
        self._rate_limit_rpm: int = self._DEFAULT_RATE_LIMIT_RPM
        self._fallback_enabled: bool = True

    @classmethod
    def get_instance(cls) -> "LLMOrchestratorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Provider Configuration
    # ------------------------------------------------------------------

    def configure_provider(
        self,
        provider: LLMProvider,
        api_key: str = "",
        model: str = "",
        base_url: str = "",
        **kwargs: Any,
    ) -> bool:
        with self._lock:
            key = provider.value
            config: Dict[str, Any] = {
                "provider": provider,
                "api_key": api_key,
                "model": model,
                "base_url": base_url,
                "configured_at": time.time(),
                **kwargs,
            }

            if key not in self._providers:
                self._providers[key] = config
            else:
                self._providers[key].update(config)

            if key not in self._usage_stats["by_provider"]:
                self._usage_stats["by_provider"][key] = {
                    "requests": 0,
                    "tokens": 0,
                    "latency_ms": 0.0,
                }

            return True

    def get_provider_config(self, provider: LLMProvider) -> Optional[Dict[str, Any]]:
        return self._providers.get(provider.value)

    def list_providers(self) -> List[Dict[str, Any]]:
        return [
            {
                "provider": cfg["provider"].value,
                "model": cfg.get("model", ""),
                "base_url": cfg.get("base_url", ""),
                "has_api_key": bool(cfg.get("api_key", "")),
                "configured_at": cfg.get("configured_at", 0),
            }
            for cfg in self._providers.values()
        ]

    # ------------------------------------------------------------------
    # Template Management
    # ------------------------------------------------------------------

    def register_template(
        self,
        name: str,
        template: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> PromptTemplate:
        with self._lock:
            pt = PromptTemplate(
                name=name,
                template=template,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self._templates[name] = pt
            return pt

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        return self._templates.get(name)

    def list_templates(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._templates.values()]

    def remove_template(self, name: str) -> bool:
        with self._lock:
            if name in self._templates:
                del self._templates[name]
                return True
            return False

    # ------------------------------------------------------------------
    # Core Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        request_type: LLMRequestType,
        template_name: str = "",
        messages: Optional[List[Dict[str, str]]] = None,
        prompt: str = "",
        variables: Optional[Dict[str, Any]] = None,
        provider: Optional[LLMProvider] = None,
    ) -> LLMResponse:
        resolved_prompt = prompt
        system_prompt = ""
        temperature = self._DEFAULT_TEMPERATURE
        max_tokens = self._DEFAULT_MAX_TOKENS

        if template_name:
            tmpl = self._templates.get(template_name)
            if tmpl is not None:
                resolved_prompt = tmpl.render(variables)
                system_prompt = tmpl.system_prompt
                temperature = tmpl.temperature
                max_tokens = tmpl.max_tokens
                tmpl.usage_count += 1
            elif not resolved_prompt:
                resolved_prompt = template_name

        cache_key = self._compute_cache_key(
            request_type=request_type,
            template_name=template_name,
            messages=messages,
            prompt=resolved_prompt,
            variables=variables,
            provider=provider,
        )

        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        selected_provider = self._resolve_provider(provider)
        if selected_provider is None:
            return self._error_response(
                "No provider configured. Call configure_provider() first.",
                provider or LLMProvider.LOCAL,
            )

        self._check_rate_limit(selected_provider.value)

        start_time = time.time()
        result_text = self._simulate_api_call(
            provider=selected_provider,
            request_type=request_type,
            prompt=resolved_prompt,
            system_prompt=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        elapsed_ms = (time.time() - start_time) * 1000.0

        model = self._providers[selected_provider.value].get("model", "default")
        tokens_used = self._estimate_tokens(resolved_prompt, result_text)

        response = LLMResponse(
            content=result_text,
            provider=selected_provider,
            model=model,
            tokens_used=tokens_used,
            latency_ms=round(elapsed_ms, 2),
            finish_reason="stop",
        )

        self._record_timestamps(selected_provider.value)
        self._update_usage_stats(
            provider=selected_provider,
            model=model,
            request_type=request_type,
            tokens_used=tokens_used,
            latency_ms=elapsed_ms,
        )
        self._put_in_cache(cache_key, response)

        return response

    def generate_stream(
        self,
        request_type: LLMRequestType,
        template_name: str = "",
        messages: Optional[List[Dict[str, str]]] = None,
        prompt: str = "",
        variables: Optional[Dict[str, Any]] = None,
        provider: Optional[LLMProvider] = None,
    ) -> Generator[str, None, None]:
        resolved_prompt = prompt
        system_prompt = ""
        temperature = self._DEFAULT_TEMPERATURE
        max_tokens = self._DEFAULT_MAX_TOKENS

        if template_name:
            tmpl = self._templates.get(template_name)
            if tmpl is not None:
                resolved_prompt = tmpl.render(variables)
                system_prompt = tmpl.system_prompt
                temperature = tmpl.temperature
                max_tokens = tmpl.max_tokens
                tmpl.usage_count += 1
            elif not resolved_prompt:
                resolved_prompt = template_name

        selected_provider = self._resolve_provider(provider)
        if selected_provider is None:
            yield "[ERROR] No provider configured."
            return

        full_response = self._simulate_api_call(
            provider=selected_provider,
            request_type=request_type,
            prompt=resolved_prompt,
            system_prompt=system_prompt,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        words = full_response.split()
        chunk_size = max(1, len(words) // 10) if len(words) >= 10 else 1
        for i in range(0, len(words), chunk_size):
            yield " ".join(words[i : i + chunk_size]) + " "

    # ------------------------------------------------------------------
    # Specialized Generation Methods
    # ------------------------------------------------------------------

    def reason_about(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        enhanced_prompt = prompt
        if context:
            context_str = json.dumps(context, indent=2)
            enhanced_prompt = (
                f"Context:\n{context_str}\n\nBased on the above context, {prompt}"
            )
        return self.generate(
            request_type=LLMRequestType.CHAT,
            prompt=enhanced_prompt,
        )

    def analyze_game_state(
        self, state: Dict[str, Any], analysis_type: str = "general"
    ) -> LLMResponse:
        state_json = json.dumps(state, indent=2)
        prompt = (
            f"Analyze the following game state ({analysis_type} analysis):\n\n"
            f"{state_json}\n\n"
            f"Provide a detailed analysis of the game state, including:\n"
            f"- Key observations about the current state\n"
            f"- Potential issues or imbalances\n"
            f"- Suggestions for improvement\n"
            f"- Notable patterns or trends"
        )
        return self.generate(
            request_type=LLMRequestType.CHAT,
            prompt=prompt,
        )

    def generate_dialogue(
        self,
        characters: List[Dict[str, Any]],
        context: str = "",
        style: str = "natural",
    ) -> LLMResponse:
        char_descriptions = "\n".join(
            f"- {c.get('name', 'Unknown')}: {c.get('description', 'No description')}"
            for c in characters
        )
        prompt = (
            f"Generate dialogue in {style} style.\n\n"
            f"Characters:\n{char_descriptions}\n\n"
            f"Context: {context or 'General conversation'}\n\n"
            f"Generate a natural conversation between these characters."
        )
        return self.generate(
            request_type=LLMRequestType.CHAT,
            prompt=prompt,
        )

    def evaluate_action(
        self,
        action: str,
        game_state: Dict[str, Any],
        criteria: Optional[List[str]] = None,
    ) -> LLMResponse:
        state_json = json.dumps(game_state, indent=2)
        criteria_str = ", ".join(criteria) if criteria else "general impact"
        prompt = (
            f"Evaluate the following action in the context of the current game state.\n\n"
            f"Action: {action}\n\n"
            f"Game State:\n{state_json}\n\n"
            f"Evaluation Criteria: {criteria_str}\n\n"
            f"Provide an evaluation including:\n"
            f"- Expected outcome of the action\n"
            f"- Risks and potential side effects\n"
            f"- Alignment with the evaluation criteria\n"
            f"- Confidence level in the assessment"
        )
        return self.generate(
            request_type=LLMRequestType.CHAT,
            prompt=prompt,
        )

    def get_embedding(self, text: str) -> List[float]:
        if not text:
            return [0.0] * 128

        hash_val = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
        embedding: List[float] = []
        for i in range(128):
            seed = (hash_val + i * 2654435761) & 0xFFFFFFFF
            val = ((seed * 1103515245 + 12345) & 0x7FFFFFFF) / 0x7FFFFFFF
            embedding.append(round(val * 2.0 - 1.0, 6))
        return embedding

    # ------------------------------------------------------------------
    # Cache Management
    # ------------------------------------------------------------------

    def clear_cache(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._cache_keys.clear()
            return count

    def get_cache_size(self) -> int:
        return len(self._cache)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_usage_stats(self) -> Dict[str, Any]:
        with self._lock:
            stats = dict(self._usage_stats)
            if stats["total_requests"] > 0:
                stats["cache_hit_rate"] = round(
                    stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"]), 4
                )
            else:
                stats["cache_hit_rate"] = 0.0
            stats["configured_providers"] = list(self._providers.keys())
            stats["template_count"] = len(self._templates)
            stats["cache_size"] = len(self._cache)
            return stats

    def get_stats(self) -> Dict[str, Any]:
        return self.get_usage_stats()

    def reset(self) -> None:
        with self._lock:
            self._providers.clear()
            self._templates.clear()
            self._cache.clear()
            self._cache_keys.clear()
            self._rate_limit_timestamps.clear()
            self._usage_stats = {
                "total_requests": 0,
                "total_tokens": 0,
                "total_latency_ms": 0.0,
                "by_provider": {},
                "by_model": {},
                "by_request_type": {},
                "cache_hits": 0,
                "cache_misses": 0,
                "errors": 0,
            }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _resolve_provider(
        self, preferred: Optional[LLMProvider] = None
    ) -> Optional[LLMProvider]:
        if preferred is not None and preferred.value in self._providers:
            return preferred

        for provider in LLMProvider:
            if provider.value in self._providers:
                return provider

        return None

    def _compute_cache_key(
        self,
        request_type: LLMRequestType,
        template_name: str,
        messages: Optional[List[Dict[str, str]]],
        prompt: str,
        variables: Optional[Dict[str, Any]],
        provider: Optional[LLMProvider],
    ) -> str:
        raw = json.dumps(
            {
                "type": request_type.value,
                "template": template_name,
                "messages": messages,
                "prompt": prompt,
                "variables": variables,
                "provider": provider.value if provider else "auto",
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[LLMResponse]:
        with self._lock:
            if cache_key in self._cache:
                self._usage_stats["cache_hits"] += 1
                return self._cache[cache_key]
            self._usage_stats["cache_misses"] += 1
            return None

    def _put_in_cache(self, cache_key: str, response: LLMResponse) -> None:
        with self._lock:
            if cache_key in self._cache:
                return
            self._cache[cache_key] = response
            self._cache_keys.append(cache_key)
            if len(self._cache_keys) > self._MAX_CACHE_ENTRIES:
                evict = self._cache_keys.pop(0)
                self._cache.pop(evict, None)

    def _simulate_api_call(
        self,
        provider: LLMProvider,
        request_type: LLMRequestType,
        prompt: str,
        system_prompt: str,
        messages: Optional[List[Dict[str, str]]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        if request_type == LLMRequestType.EMBEDDING:
            return f"[EMBEDDING] provider={provider.value} dims=128"

        if request_type == LLMRequestType.FUNCTION_CALL:
            return json.dumps({
                "function": "simulated_function",
                "arguments": {"prompt_length": len(prompt)},
            })

        combined = prompt
        if messages:
            combined = "\n".join(
                f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                for m in messages
            )

        provider_name = provider.value
        model = self._providers.get(provider_name, {}).get("model", "default")

        return (
            f"[{provider_name}/{model}] Response to: "
            f"{combined[:200]}{'...' if len(combined) > 200 else ''}"
        )

    def _estimate_tokens(self, prompt: str, response: str) -> int:
        prompt_chars = len(prompt)
        response_chars = len(response)
        return (prompt_chars // 4) + (response_chars // 4)

    def _check_rate_limit(self, provider_key: str) -> None:
        now = time.time()
        window = 60.0
        if provider_key not in self._rate_limit_timestamps:
            self._rate_limit_timestamps[provider_key] = []
        timestamps = self._rate_limit_timestamps[provider_key]
        timestamps[:] = [ts for ts in timestamps if now - ts < window]
        if len(timestamps) >= self._rate_limit_rpm:
            oldest = timestamps[0]
            wait = window - (now - oldest) + 0.1
            if wait > 0:
                time.sleep(wait)

    def _record_timestamps(self, provider_key: str) -> None:
        if provider_key not in self._rate_limit_timestamps:
            self._rate_limit_timestamps[provider_key] = []
        self._rate_limit_timestamps[provider_key].append(time.time())

    def _update_usage_stats(
        self,
        provider: LLMProvider,
        model: str,
        request_type: LLMRequestType,
        tokens_used: int,
        latency_ms: float,
    ) -> None:
        with self._lock:
            self._usage_stats["total_requests"] += 1
            self._usage_stats["total_tokens"] += tokens_used
            self._usage_stats["total_latency_ms"] += latency_ms

            pkey = provider.value
            if pkey in self._usage_stats["by_provider"]:
                self._usage_stats["by_provider"][pkey]["requests"] += 1
                self._usage_stats["by_provider"][pkey]["tokens"] += tokens_used
                self._usage_stats["by_provider"][pkey]["latency_ms"] += latency_ms

            if model not in self._usage_stats["by_model"]:
                self._usage_stats["by_model"][model] = {"requests": 0, "tokens": 0}
            self._usage_stats["by_model"][model]["requests"] += 1
            self._usage_stats["by_model"][model]["tokens"] += tokens_used

            rt = request_type.value
            self._usage_stats["by_request_type"][rt] = (
                self._usage_stats["by_request_type"].get(rt, 0) + 1
            )

    def _error_response(
        self, message: str, provider: LLMProvider
    ) -> LLMResponse:
        with self._lock:
            self._usage_stats["errors"] += 1
        return LLMResponse(
            content=f"[ERROR] {message}",
            provider=provider,
            model="none",
            tokens_used=0,
            latency_ms=0.0,
            finish_reason="error",
        )


def get_llm_orchestrator() -> LLMOrchestratorEngine:
    return LLMOrchestratorEngine.get_instance()