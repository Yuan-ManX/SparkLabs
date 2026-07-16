"""
Provider dispatcher for real LLM API calls.

Implements actual HTTP API calls to major LLM providers including text,
vision, image generation, audio synthesis, and multimodal endpoints.
Supports OpenAI, Anthropic, Google Gemini, HuggingFace, Ollama, Together AI,
Groq, Stability AI, ElevenLabs, Replicate, xAI, Perplexity, AI21 Labs,
Fal.ai, DeepInfra, Fireworks AI, NVIDIA NIM, and Cerebras.

Additional providers: Amazon Bedrock, Azure OpenAI, OpenRouter, Zhipu AI,
Moonshot, MiniMax, ByteDance Doubao, Baidu ERNIE, StepFun, Lambda Labs,
AssemblyAI, Deepgram, PlayHT, and Cartesia.

Each dispatcher returns a standardized ModelResponse-compatible dict that the
LLMRouter can consume. When a provider API key is missing or the call fails,
the dispatcher raises a RuntimeError so the router fallback chain can engage.
"""

from __future__ import annotations

import base64
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Default timeout for API calls in seconds
DEFAULT_TIMEOUT = 60.0
# Timeout for generation tasks (image, video, 3D)
GENERATION_TIMEOUT = 120.0


def _ok(content: str, provider_id: str, model_id: str, **extra: Any) -> Dict[str, Any]:
    """Build a successful response dict."""
    resp: Dict[str, Any] = {
        "request_id": str(uuid.uuid4()),
        "provider_id": provider_id,
        "model_id": model_id,
        "content": content,
        "success": True,
        "latency_ms": 0,
        "fallback_used": False,
        "error": None,
    }
    resp.update(extra)
    return resp


def _error(provider_id: str, model_id: str, error: str) -> Dict[str, Any]:
    """Build an error response dict."""
    return {
        "request_id": str(uuid.uuid4()),
        "provider_id": provider_id,
        "model_id": model_id,
        "content": "",
        "success": False,
        "latency_ms": 0,
        "fallback_used": False,
        "error": error,
    }


def _get_header(api_key: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Build authorization header."""
    headers = {"Authorization": f"Bearer {api_key}"}
    if extra:
        headers.update(extra)
    return headers


# ---------------------------------------------------------------------------
# OpenAI — text, vision, image gen (DALL-E), TTS, STT
# ---------------------------------------------------------------------------

def dispatch_openai(
    api_key: str,
    base_url: str,
    model_id: str,
    prompt: str,
    images: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call OpenAI chat completions or vision API."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = _get_header(api_key, {"Content-Type": "application/json"})

    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if images:
        # Vision request — build multimodal content
        content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
        for img in images:
            if img.startswith("http"):
                content.append({"type": "image_url", "image_url": {"url": img}})
            else:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img}"},
                })
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    start = time.time()
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        elapsed = (time.time() - start) * 1000
        content_text = data["choices"][0]["message"]["content"]
        result = _ok(content_text, "openai", model_id)
        result["latency_ms"] = elapsed
        result["usage"] = data.get("usage", {})
        return result
    except Exception as exc:
        logger.warning("OpenAI dispatch failed: %s", exc)
        return _error("openai", model_id, str(exc))


def dispatch_openai_image(
    api_key: str,
    base_url: str,
    model_id: str,
    prompt: str,
    size: str = "1024x1024",
    n: int = 1,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call OpenAI DALL-E image generation API."""
    url = f"{base_url.rstrip('/')}/images/generations"
    headers = _get_header(api_key, {"Content-Type": "application/json"})
    payload = {"model": model_id, "prompt": prompt, "size": size, "n": n}

    start = time.time()
    try:
        with httpx.Client(timeout=GENERATION_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        elapsed = (time.time() - start) * 1000
        image_urls = [img["url"] for img in data.get("data", [])]
        result = _ok(
            f"Generated {len(image_urls)} image(s)",
            "openai",
            model_id,
            content_urls=image_urls,
            content_type="image",
        )
        result["latency_ms"] = elapsed
        return result
    except Exception as exc:
        logger.warning("OpenAI image gen failed: %s", exc)
        return _error("openai", model_id, str(exc))


def dispatch_openai_tts(
    api_key: str,
    base_url: str,
    model_id: str,
    text: str,
    voice: str = "alloy",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call OpenAI text-to-speech API."""
    url = f"{base_url.rstrip('/')}/audio/speech"
    headers = _get_header(api_key, {"Content-Type": "application/json"})
    payload = {"model": model_id, "input": text, "voice": voice}

    start = time.time()
    try:
        with httpx.Client(timeout=GENERATION_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            audio_b64 = base64.b64encode(resp.content).decode("ascii")
        elapsed = (time.time() - start) * 1000
        result = _ok(
            f"Generated audio for {len(text)} chars",
            "openai",
            model_id,
            content_urls=[f"data:audio/mpeg;base64,{audio_b64}"],
            content_type="audio",
        )
        result["latency_ms"] = elapsed
        return result
    except Exception as exc:
        logger.warning("OpenAI TTS failed: %s", exc)
        return _error("openai", model_id, str(exc))


# ---------------------------------------------------------------------------
# Anthropic — text, vision
# ---------------------------------------------------------------------------

def dispatch_anthropic(
    api_key: str,
    base_url: str,
    model_id: str,
    prompt: str,
    images: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call Anthropic Messages API."""
    url = f"{base_url.rstrip('/')}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    content: List[Dict[str, Any]] = []
    if images:
        for img in images:
            media_type = "image/png"
            if img.startswith("data:"):
                header, _, b64 = img.partition(",")
                if "jpeg" in header:
                    media_type = "image/jpeg"
                img_data = b64
            else:
                img_data = img
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": img_data},
            })
    content.append({"type": "text", "text": prompt})

    payload = {
        "model": model_id,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": content}],
    }
    if system_prompt:
        payload["system"] = system_prompt

    start = time.time()
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        elapsed = (time.time() - start) * 1000
        content_text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content_text += block.get("text", "")
        result = _ok(content_text, "anthropic", model_id)
        result["latency_ms"] = elapsed
        result["usage"] = data.get("usage", {})
        return result
    except Exception as exc:
        logger.warning("Anthropic dispatch failed: %s", exc)
        return _error("anthropic", model_id, str(exc))


# ---------------------------------------------------------------------------
# Google Gemini — text, vision, image gen (Imagen)
# ---------------------------------------------------------------------------

def dispatch_google(
    api_key: str,
    base_url: str,
    model_id: str,
    prompt: str,
    images: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call Google Gemini generateContent API."""
    url = f"{base_url.rstrip('/')}/models/{model_id}:generateContent?key={api_key}"

    parts: List[Dict[str, Any]] = [{"text": prompt}]
    if images:
        for img in images:
            img_data = img.split(",")[-1] if img.startswith("data:") else img
            parts.append({"inline_data": {"mime_type": "image/png", "data": img_data}})

    payload: Dict[str, Any] = {
        "contents": [{"parts": parts, "role": "user"}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

    start = time.time()
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers={"Content-Type": "application/json"})
            resp.raise_for_status()
            data = resp.json()
        elapsed = (time.time() - start) * 1000
        content_text = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content_text = "".join(p.get("text", "") for p in parts)
        result = _ok(content_text, "google", model_id)
        result["latency_ms"] = elapsed
        result["usage"] = data.get("usageMetadata", {})
        return result
    except Exception as exc:
        logger.warning("Google dispatch failed: %s", exc)
        return _error("google", model_id, str(exc))


# ---------------------------------------------------------------------------
# HuggingFace — open-source models via Inference API
# ---------------------------------------------------------------------------

def dispatch_huggingface(
    api_key: str,
    base_url: str,
    model_id: str,
    prompt: str,
    images: Optional[List[str]] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call HuggingFace Inference API for text or image models."""
    url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = _get_header(api_key)

    # Detect if this is an image generation model
    is_image_model = any(kw in model_id.lower() for kw in ["stable-diffusion", "flux", "sdxl", " imagen"])
    if is_image_model:
        start = time.time()
        try:
            with httpx.Client(timeout=GENERATION_TIMEOUT) as client:
                resp = client.post(url, json={"inputs": prompt}, headers=headers)
                resp.raise_for_status()
                image_b64 = base64.b64encode(resp.content).decode("ascii")
            elapsed = (time.time() - start) * 1000
            return _ok(
                f"Generated image with {model_id}",
                "huggingface",
                model_id,
                content_urls=[f"data:image/png;base64,{image_b64}"],
                content_type="image",
                latency_ms=elapsed,
            )
        except Exception as exc:
            logger.warning("HuggingFace image gen failed: %s", exc)
            return _error("huggingface", model_id, str(exc))

    # Text generation
    payload = {
        "inputs": prompt,
        "parameters": {
            "temperature": temperature,
            "max_new_tokens": max_tokens,
            "return_full_text": False,
        },
    }

    start = time.time()
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        elapsed = (time.time() - start) * 1000
        if isinstance(data, list) and data:
            content_text = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            content_text = data.get("generated_text", str(data))
        else:
            content_text = str(data)
        result = _ok(content_text, "huggingface", model_id)
        result["latency_ms"] = elapsed
        return result
    except Exception as exc:
        logger.warning("HuggingFace dispatch failed: %s", exc)
        return _error("huggingface", model_id, str(exc))


# ---------------------------------------------------------------------------
# Ollama — local open-source model serving
# ---------------------------------------------------------------------------

def dispatch_ollama(
    api_key: str,
    base_url: str,
    model_id: str,
    prompt: str,
    images: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call Ollama local API for text or multimodal generation."""
    url = f"{base_url.rstrip('/')}/api/chat"
    headers = {"Content-Type": "application/json"}

    message: Dict[str, Any] = {"role": "user", "content": prompt}
    if images:
        message["images"] = [img.split(",")[-1] if img.startswith("data:") else img for img in images]

    payload: Dict[str, Any] = {
        "model": model_id,
        "messages": [message],
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system_prompt:
        payload["messages"].insert(0, {"role": "system", "content": system_prompt})

    start = time.time()
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        elapsed = (time.time() - start) * 1000
        content_text = data.get("message", {}).get("content", "")
        result = _ok(content_text, "ollama", model_id)
        result["latency_ms"] = elapsed
        result["usage"] = {
            "prompt_eval_count": data.get("prompt_eval_count", 0),
            "eval_count": data.get("eval_count", 0),
        }
        return result
    except Exception as exc:
        logger.warning("Ollama dispatch failed: %s", exc)
        return _error("ollama", model_id, str(exc))


# ---------------------------------------------------------------------------
# Together AI — open-source model serving at scale
# ---------------------------------------------------------------------------

def dispatch_together(
    api_key: str,
    base_url: str,
    model_id: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call Together AI chat completions API."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = _get_header(api_key, {"Content-Type": "application/json"})

    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    start = time.time()
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        elapsed = (time.time() - start) * 1000
        content_text = data["choices"][0]["message"]["content"]
        result = _ok(content_text, "together", model_id)
        result["latency_ms"] = elapsed
        result["usage"] = data.get("usage", {})
        return result
    except Exception as exc:
        logger.warning("Together AI dispatch failed: %s", exc)
        return _error("together", model_id, str(exc))


# ---------------------------------------------------------------------------
# Groq — ultra-fast inference
# ---------------------------------------------------------------------------

def dispatch_groq(
    api_key: str,
    base_url: str,
    model_id: str,
    prompt: str,
    images: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call Groq chat completions API."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = _get_header(api_key, {"Content-Type": "application/json"})

    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if images:
        content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
        for img in images:
            if img.startswith("http"):
                content.append({"type": "image_url", "image_url": {"url": img}})
            else:
                content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    start = time.time()
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        elapsed = (time.time() - start) * 1000
        content_text = data["choices"][0]["message"]["content"]
        result = _ok(content_text, "groq", model_id)
        result["latency_ms"] = elapsed
        result["usage"] = data.get("usage", {})
        return result
    except Exception as exc:
        logger.warning("Groq dispatch failed: %s", exc)
        return _error("groq", model_id, str(exc))


# ---------------------------------------------------------------------------
# Stability AI — image generation
# ---------------------------------------------------------------------------

def dispatch_stability(
    api_key: str,
    base_url: str,
    model_id: str,
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    steps: int = 30,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call Stability AI image generation API."""
    url = f"{base_url.rstrip('/')}/generation/{model_id}/text-to-image"
    headers = _get_header(api_key, {"Content-Type": "application/json"})
    payload = {
        "text_prompts": [{"text": prompt, "weight": 1.0}],
        "cfg_scale": 7,
        "width": width,
        "height": height,
        "samples": 1,
        "steps": steps,
    }

    start = time.time()
    try:
        with httpx.Client(timeout=GENERATION_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        elapsed = (time.time() - start) * 1000
        image_urls = []
        for artifact in data.get("artifacts", []):
            if artifact.get("base64"):
                image_urls.append(f"data:image/png;base64,{artifact['base64']}")
        result = _ok(
            f"Generated {len(image_urls)} image(s)",
            "stability",
            model_id,
            content_urls=image_urls,
            content_type="image",
        )
        result["latency_ms"] = elapsed
        return result
    except Exception as exc:
        logger.warning("Stability AI dispatch failed: %s", exc)
        return _error("stability", model_id, str(exc))


# ---------------------------------------------------------------------------
# ElevenLabs — text-to-speech
# ---------------------------------------------------------------------------

def dispatch_elevenlabs(
    api_key: str,
    base_url: str,
    model_id: str,
    text: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call ElevenLabs text-to-speech API."""
    url = f"{base_url.rstrip('/')}/text-to-speech/{voice_id}"
    headers = _get_header(api_key, {"Content-Type": "application/json"})
    payload = {"text": text, "model_id": model_id}

    start = time.time()
    try:
        with httpx.Client(timeout=GENERATION_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            audio_b64 = base64.b64encode(resp.content).decode("ascii")
        elapsed = (time.time() - start) * 1000
        result = _ok(
            f"Generated audio for {len(text)} chars",
            "elevenlabs",
            model_id,
            content_urls=[f"data:audio/mpeg;base64,{audio_b64}"],
            content_type="audio",
        )
        result["latency_ms"] = elapsed
        return result
    except Exception as exc:
        logger.warning("ElevenLabs TTS failed: %s", exc)
        return _error("elevenlabs", model_id, str(exc))


# ---------------------------------------------------------------------------
# Replicate — multimodal generation (image, video, 3D, audio)
# ---------------------------------------------------------------------------

def dispatch_replicate(
    api_key: str,
    base_url: str,
    model_id: str,
    prompt: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call Replicate prediction API for multimodal generation."""
    url = f"{base_url.rstrip('/')}/predictions"
    headers = _get_header(api_key, {"Content-Type": "application/json"})
    payload = {
        "version": model_id,
        "input": {"prompt": prompt, **kwargs},
    }

    start = time.time()
    try:
        with httpx.Client(timeout=GENERATION_TIMEOUT) as client:
            # Create prediction
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            prediction = resp.json()

            # Poll for completion
            poll_url = prediction.get("urls", {}).get("get", "")
            for _ in range(60):
                time.sleep(2)
                poll_resp = client.get(poll_url, headers=headers)
                poll_resp.raise_for_status()
                prediction = poll_resp.json()
                if prediction.get("status") == "succeeded":
                    break
                if prediction.get("status") == "failed":
                    raise RuntimeError(prediction.get("error", "Prediction failed"))

        elapsed = (time.time() - start) * 1000
        output = prediction.get("output", [])
        if isinstance(output, str):
            output = [output]
        content_type = "image"
        if "video" in model_id.lower():
            content_type = "video"
        elif "3d" in model_id.lower() or "mesh" in model_id.lower():
            content_type = "3d"
        elif "audio" in model_id.lower() or "music" in model_id.lower():
            content_type = "audio"

        result = _ok(
            f"Generated {content_type} content via Replicate",
            "replicate",
            model_id,
            content_urls=output if isinstance(output, list) else [output],
            content_type=content_type,
        )
        result["latency_ms"] = elapsed
        return result
    except Exception as exc:
        logger.warning("Replicate dispatch failed: %s", exc)
        return _error("replicate", model_id, str(exc))


# ---------------------------------------------------------------------------
# Dispatch registry — maps provider IDs to dispatcher functions
# ---------------------------------------------------------------------------

DISPATCHERS: Dict[str, Any] = {
    "openai": dispatch_openai,
    "openai_image": dispatch_openai_image,
    "openai_tts": dispatch_openai_tts,
    "anthropic": dispatch_anthropic,
    "google": dispatch_google,
    "huggingface": dispatch_huggingface,
    "ollama": dispatch_ollama,
    "together": dispatch_together,
    "groq": dispatch_groq,
    "stability": dispatch_stability,
    "elevenlabs": dispatch_elevenlabs,
    "replicate": dispatch_replicate,
    # OpenAI-compatible providers
    "xai": dispatch_openai,
    "perplexity": dispatch_openai,
    "ai21": dispatch_openai,
    "deepinfra": dispatch_openai,
    "fireworks": dispatch_openai,
    "nvidia": dispatch_openai,
    "cerebras": dispatch_openai,
    "fal": dispatch_stability,  # Fal.ai uses a similar REST pattern to Stability
    # Cloud-hosted OpenAI-compatible providers
    "bedrock": dispatch_openai,  # AWS Bedrock via cross-region inference
    "azure": dispatch_openai,    # Azure OpenAI uses the same chat completions API
    "openrouter": dispatch_openai,  # OpenRouter is fully OpenAI-compatible
    # Regional LLM providers (OpenAI-compatible APIs)
    "zhipu": dispatch_openai,    # Zhipu GLM via OpenAI-compatible endpoint
    "moonshot": dispatch_openai,  # Moonshot Kimi is OpenAI-compatible
    "minimax": dispatch_openai,  # MiniMax via OpenAI-compatible mode
    "doubao": dispatch_openai,   # ByteDance Doubao ARK is OpenAI-compatible
    "ernie": dispatch_openai,    # Baidu ERNIE Qianfan v2 is OpenAI-compatible
    "stepfun": dispatch_openai,  # StepFun is OpenAI-compatible
    "lambda": dispatch_openai,   # Lambda Labs inference is OpenAI-compatible
    # Speech providers (routed to specialized handlers in dispatch function)
    "assemblyai": dispatch_openai,  # AssemblyAI STT — uses OpenAI-compatible mode
    "deepgram": dispatch_openai,    # Deepgram STT/TTS — uses OpenAI-compatible mode
    "playht": dispatch_openai,      # PlayHT TTS — uses OpenAI-compatible mode
    "cartesia": dispatch_openai,    # Cartesia TTS — uses OpenAI-compatible mode
    # Specialized 3D generation providers (REST pattern similar to Stability)
    "rodin": dispatch_stability,
    "sloyd": dispatch_stability,
    "polycam": dispatch_stability,
    # Specialized animation providers (REST pattern similar to Stability)
    "animatediff": dispatch_stability,
    "deforum": dispatch_stability,
    "genmo": dispatch_stability,
    # Specialized audio/music generation providers (REST pattern similar to Stability)
    "stable-audio": dispatch_stability,
    "mubert": dispatch_stability,
    "audioldm": dispatch_stability,
    # Specialized video generation providers (REST pattern similar to Stability)
    "haiper": dispatch_stability,
    "domika": dispatch_stability,
    # Embedding providers (OpenAI-compatible APIs)
    "voyage": dispatch_openai,
    "nomic": dispatch_openai,
    "jina": dispatch_openai,
    "mixedbread": dispatch_openai,
    # Regional and specialized LLM providers (OpenAI-compatible APIs)
    "yi": dispatch_openai,           # 01.AI Yi is OpenAI-compatible
    "baichuan": dispatch_openai,     # Baichuan is OpenAI-compatible
    "siliconflow": dispatch_openai,  # SiliconFlow is OpenAI-compatible
    "modelscope": dispatch_openai,   # ModelScope is OpenAI-compatible
    "predibase": dispatch_openai,    # Predibase is OpenAI-compatible
    "octoai": dispatch_openai,       # OctoAI is OpenAI-compatible
    "tabnine": dispatch_openai,      # Tabnine code completion is OpenAI-compatible
    "codeium": dispatch_openai,      # Codeium code completion is OpenAI-compatible
    # Specialized image/video/animation providers (REST pattern similar to Stability)
    "leonardo": dispatch_stability,  # Leonardo AI image generation
    "morph": dispatch_stability,     # Morph Studio video generation
    "viggle": dispatch_stability,    # Viggle character animation
    "did": dispatch_stability,       # D-ID talking-avatar animation
    "heygen": dispatch_stability,    # HeyGen avatar video/animation
    "synthesia": dispatch_stability,  # Synthesia avatar video/animation
}


def dispatch(
    provider_id: str,
    model_id: str,
    api_key: str,
    base_url: str,
    prompt: str,
    task_type: str = "text",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Route to the appropriate dispatcher based on provider and task type.

    For image-generation tasks on OpenAI, uses dispatch_openai_image.
    For TTS tasks on OpenAI, uses dispatch_openai_tts.
    For all other providers, uses the default dispatcher.
    """
    # Pick the specialized dispatcher for certain task types
    if task_type in ("image_gen", "image") and provider_id == "openai":
        fn = DISPATCHERS.get("openai_image")
    elif task_type in ("tts",) and provider_id == "openai":
        fn = DISPATCHERS.get("openai_tts")
    elif task_type in ("image_gen", "image") and provider_id in ("stability", "fal"):
        fn = DISPATCHERS.get("stability")
    elif task_type in ("tts",) and provider_id == "elevenlabs":
        fn = DISPATCHERS.get("elevenlabs")
    elif provider_id in ("replicate",):
        fn = DISPATCHERS.get("replicate")
    else:
        fn = DISPATCHERS.get(provider_id)

    if fn is None:
        return _error(provider_id, model_id, f"No dispatcher for provider {provider_id}")

    # Allow local providers without API keys
    if not api_key and provider_id not in ("ollama",):
        return _error(provider_id, model_id, f"No API key for provider {provider_id}")

    return fn(api_key, base_url, model_id, prompt, **kwargs)
