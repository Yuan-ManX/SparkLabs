"""
SparkAI Configuration
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class EngineMode(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class SparkAIConfig:
    engine_mode: EngineMode = EngineMode.DEVELOPMENT
    log_level: str = "INFO"
    max_agents: int = 100
    max_workflows: int = 50
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4"
    memory_capacity_short: int = 10
    memory_capacity_long: int = 1000
    memory_capacity_episodic: int = 500
    memory_capacity_semantic: int = 2000
    websocket_host: str = "0.0.0.0"
    websocket_port: int = 8090
    api_host: str = "0.0.0.0"
    api_port: int = 8090
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    llm_configs: Dict[str, Dict] = field(default_factory=dict)
    enable_onnx: bool = True
    enable_gpu: bool = True
    onnx_model_path: str = "models/"
    asset_output_path: str = "output/"

    @classmethod
    def from_dict(cls, data: Dict) -> "SparkAIConfig":
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                if key == "engine_mode":
                    value = EngineMode(value)
                setattr(config, key, value)
        return config

    def to_dict(self) -> Dict:
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            else:
                result[key] = value
        return result
