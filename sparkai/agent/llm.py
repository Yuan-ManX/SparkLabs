"""
SparkAI Agent - LLM Provider Integration
"""

from __future__ import annotations

import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    timeout: float = 60.0
    extra_params: Dict[str, Any] = field(default_factory=dict)


class LLMProvider:
    """
    Multi-provider LLM integration supporting OpenAI, Anthropic,
    local models, and custom endpoints.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client: Any = None
        self._initialized = False

    async def initialize(self) -> bool:
        try:
            provider = self.config.provider.lower()
            if provider == "openai":
                return await self._init_openai()
            elif provider == "anthropic":
                return await self._init_anthropic()
            elif provider == "deepseek":
                return await self._init_deepseek()
            elif provider == "local":
                return await self._init_local()
            elif provider == "ollama":
                return await self._init_ollama()
            else:
                return await self._init_custom()
        except Exception as e:
            print(f"[LLMProvider] Initialization error: {e}")
            return False

    async def generate(self, prompt: str, **kwargs) -> str:
        if not self._initialized:
            await self.initialize()

        provider = self.config.provider.lower()
        try:
            if provider == "openai":
                return await self._generate_openai(prompt, **kwargs)
            elif provider == "anthropic":
                return await self._generate_anthropic(prompt, **kwargs)
            elif provider == "deepseek":
                return await self._generate_deepseek(prompt, **kwargs)
            elif provider == "local":
                return await self._generate_local(prompt, **kwargs)
            elif provider == "ollama":
                return await self._generate_ollama(prompt, **kwargs)
            else:
                return await self._generate_custom(prompt, **kwargs)
        except Exception as e:
            return f"LLM generation error: {str(e)}"

    async def generate_chat(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> str:
        if not self._initialized:
            await self.initialize()

        provider = self.config.provider.lower()
        try:
            if provider == "openai":
                return await self._chat_openai(messages, **kwargs)
            elif provider == "anthropic":
                return await self._chat_anthropic(messages, **kwargs)
            else:
                return await self._chat_openai(messages, **kwargs)
        except Exception as e:
            return f"LLM chat error: {str(e)}"

    async def _init_openai(self) -> bool:
        try:
            import openai
            kwargs = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = openai.AsyncOpenAI(**kwargs)
            self._initialized = True
            return True
        except ImportError:
            print("[LLMProvider] openai package not installed")
            return False

    async def _init_anthropic(self) -> bool:
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self.config.api_key)
            self._initialized = True
            return True
        except ImportError:
            print("[LLMProvider] anthropic package not installed")
            return False

    async def _init_deepseek(self) -> bool:
        try:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url or "https://api.deepseek.com/v1",
            )
            self._initialized = True
            return True
        except ImportError:
            print("[LLMProvider] openai package not installed for deepseek")
            return False

    async def _init_ollama(self) -> bool:
        base = self.config.base_url or "http://localhost:11434"
        self._client = {"base_url": base}
        self._initialized = True
        return True

    async def _init_local(self) -> bool:
        self._client = {"type": "local"}
        self._initialized = True
        return True

    async def _init_custom(self) -> bool:
        self._client = {"type": "custom", "base_url": self.config.base_url}
        self._initialized = True
        return True

    async def _generate_openai(self, prompt: str, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self._chat_openai(messages, **kwargs)

    async def _chat_openai(self, messages: List[Dict], **kwargs) -> str:
        response = await self._client.chat.completions.create(
            model=kwargs.get("model", self.config.model),
            messages=messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            top_p=kwargs.get("top_p", self.config.top_p),
        )
        return response.choices[0].message.content

    async def _generate_anthropic(self, prompt: str, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self._chat_anthropic(messages, **kwargs)

    async def _chat_anthropic(self, messages: List[Dict], **kwargs) -> str:
        response = await self._client.messages.create(
            model=kwargs.get("model", self.config.model),
            messages=messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
        )
        return response.content[0].text

    async def _generate_deepseek(self, prompt: str, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self._chat_openai(messages, **kwargs)

    async def _generate_ollama(self, prompt: str, **kwargs) -> str:
        import aiohttp
        base_url = self._client.get("base_url", "http://localhost:11434")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/generate",
                json={
                    "model": kwargs.get("model", self.config.model),
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                    },
                },
            ) as resp:
                data = await resp.json()
                return data.get("response", "")

    async def _generate_local(self, prompt: str, **kwargs) -> str:
        return f"[Local Model] Processed: {prompt[:100]}..."

    async def _generate_custom(self, prompt: str, **kwargs) -> str:
        import aiohttp
        base_url = self._client.get("base_url", "")
        if not base_url:
            return "[Custom] No base URL configured"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": kwargs.get("model", self.config.model),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                },
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            ) as resp:
                data = await resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def shutdown(self) -> None:
        self._client = None
        self._initialized = False
