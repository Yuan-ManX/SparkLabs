"""
AI Integration Module
======================

Provides Python-based AI integration with the C++ SparkLabs Engine.
This module demonstrates how to connect external AI services, APIs,
and machine learning models to the engine.
"""

import sys
import json
import asyncio
from typing import Dict, List, Any, Optional, Callable
from abc import ABC, abstractmethod


class AIService(ABC):
    """Abstract base class for AI service integrations."""

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the AI service."""
        pass

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return AI-generated output."""
        pass

    @abstractmethod
    def shutdown(self):
        """Shutdown the AI service."""
        pass


class OpenAIService(AIService):
    """Integration with OpenAI API for text generation."""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        self.client = None

    async def initialize(self) -> bool:
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
            print(f"[OpenAI] Initialized with model: {self.model}")
            return True
        except ImportError:
            print("[OpenAI] Error: openai package not installed")
            return False
        except Exception as e:
            print(f"[OpenAI] Initialization error: {e}")
            return False

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.client:
            return {"error": "Service not initialized"}

        try:
            prompt = input_data.get("prompt", "")
            max_tokens = input_data.get("max_tokens", 100)
            temperature = input_data.get("temperature", 0.7)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )

            return {
                "text": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            return {"error": str(e)}

    def shutdown(self):
        self.client = None


class HuggingFaceService(AIService):
    """Integration with Hugging Face models."""

    def __init__(self, model_name: str = "gpt2"):
        self.model_name = model_name
        self.pipeline = None

    async def initialize(self) -> bool:
        try:
            from transformers import pipeline
            self.pipeline = pipeline("text-generation", model=self.model_name)
            print(f"[HuggingFace] Initialized with model: {self.model_name}")
            return True
        except ImportError:
            print("[HuggingFace] Error: transformers package not installed")
            return False
        except Exception as e:
            print(f"[HuggingFace] Initialization error: {e}")
            return False

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.pipeline:
            return {"error": "Service not initialized"}

        try:
            prompt = input_data.get("prompt", "")
            max_length = input_data.get("max_length", 100)

            results = self.pipeline(
                prompt,
                max_length=max_length,
                num_return_sequences=1
            )

            return {
                "text": results[0]["generated_text"]
            }
        except Exception as e:
            return {"error": str(e)}

    def shutdown(self):
        self.pipeline = None


class LocalModelService(AIService):
    """Integration with local ONNX models."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.session = None

    async def initialize(self) -> bool:
        try:
            import onnxruntime as ort
            self.session = ort.InferenceSession(self.model_path)
            print(f"[LocalModel] Loaded model from: {self.model_path}")
            return True
        except ImportError:
            print("[LocalModel] Error: onnxruntime package not installed")
            return False
        except Exception as e:
            print(f"[LocalModel] Initialization error: {e}")
            return False

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.session:
            return {"error": "Service not initialized"}

        try:
            inputs = input_data.get("inputs", {})
            outputs = self.session.run(None, inputs)
            return {"outputs": outputs}
        except Exception as e:
            return {"error": str(e)}

    def shutdown(self):
        self.session = None


class AIServiceManager:
    """Manages multiple AI services and provides a unified interface."""

    def __init__(self):
        self.services: Dict[str, AIService] = {}
        self._running = False

    async def register_service(self, name: str, service: AIService) -> bool:
        """Register an AI service with the manager."""
        if await service.initialize():
            self.services[name] = service
            return True
        return False

    def get_service(self, name: str) -> Optional[AIService]:
        """Get a registered AI service by name."""
        return self.services.get(name)

    async def process(self, service_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input using a specific AI service."""
        service = self.get_service(service_name)
        if not service:
            return {"error": f"Service not found: {service_name}"}
        return await service.process(input_data)

    def shutdown_all(self):
        """Shutdown all registered AI services."""
        for service in self.services.values():
            service.shutdown()
        self.services.clear()


# Global AI service manager
_ai_manager: Optional[AIServiceManager] = None


def get_ai_manager() -> AIServiceManager:
    """Get or create the global AI service manager."""
    global _ai_manager
    if _ai_manager is None:
        _ai_manager = AIServiceManager()
    return _ai_manager


async def setup_ai_services(config: Dict[str, Any]) -> bool:
    """
    Set up AI services from a configuration dictionary.

    Example config:
    {
        "openai": {
            "api_key": "sk-...",
            "model": "gpt-4"
        },
        "huggingface": {
            "model_name": "gpt2"
        }
    }
    """
    manager = get_ai_manager()
    success = True

    if "openai" in config:
        cfg = config["openai"]
        service = OpenAIService(api_key=cfg["api_key"], model=cfg.get("model", "gpt-4"))
        if not await manager.register_service("openai", service):
            success = False

    if "huggingface" in config:
        cfg = config["huggingface"]
        service = HuggingFaceService(model_name=cfg.get("model_name", "gpt2"))
        if not await manager.register_service("huggingface", service):
            success = False

    if "local_model" in config:
        cfg = config["local_model"]
        service = LocalModelService(model_path=cfg["model_path"])
        if not await manager.register_service("local_model", service):
            success = False

    return success


def shutdown_ai_services():
    """Shutdown all AI services."""
    global _ai_manager
    if _ai_manager:
        _ai_manager.shutdown_all()
        _ai_manager = None
