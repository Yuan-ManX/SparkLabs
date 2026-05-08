"""
SparkLabs Agent - Platform Bridge

Multi-platform communication adapter for the AI agent.
Provides a unified interface for the agent to communicate
across different channels: Web UI, CLI terminal, REST API,
WebSocket, and messaging platforms. Ensures the agent's
responses are properly routed and formatted for each platform.

Architecture:
  PlatformBridge
    |-- PlatformAdapter (per-platform: web, cli, api, ws)
    |-- MessageRouter (direct messages to correct platform)
    |-- FormatTransformer (platform-specific message formatting)
    |-- StreamManager (SSE, WebSocket streaming per platform)
    |-- PlatformAuth (per-platform credential resolution)

Platforms:
  - WEB: browser-based editor interface
  - CLI: terminal-based interactive session
  - API: REST API for programmatic access
  - WS: WebSocket for real-time bidirectional communication
  - HOOK: webhook-based integration pipeline
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class PlatformType(Enum):
    WEB = "web"
    CLI = "cli"
    API = "api"
    WS = "ws"
    HOOK = "hook"


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class MessageFormat(Enum):
    PLAIN = "plain"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


@dataclass
class PlatformMessage:
    message_id: str
    platform: PlatformType
    role: MessageRole
    content: str
    format: MessageFormat = MessageFormat.MARKDOWN
    timestamp: float = field(default_factory=time.time)
    reply_to: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "format": self.format.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class PlatformConfig:
    platform: PlatformType
    enabled: bool = True
    default_format: MessageFormat = MessageFormat.MARKDOWN
    max_message_length: int = 8000
    rate_limit_per_minute: int = 60
    streaming: bool = False
    auth_required: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class PlatformBridge:
    """
    Multi-platform communication bridge for AI agents.

    Game development involves multiple interfaces: the
    web editor, CLI tools, REST APIs, and WebSocket
    connections. This bridge provides a unified message
    routing layer so the AI agent can communicate across
    all platforms through a single consistent interface.
    """

    _instance: Optional["PlatformBridge"] = None

    def __init__(self):
        self._configs: Dict[PlatformType, PlatformConfig] = {}
        self._message_queue: List[PlatformMessage] = []
        self._handlers: Dict[PlatformType, List[Callable]] = {
            p: [] for p in PlatformType
        }
        self._on_send: List[Callable] = []
        self._lock = threading.Lock()
        self._next_id: int = 0
        self._MAX_QUEUE = 200
        self._init_defaults()

    @classmethod
    def get_instance(cls) -> "PlatformBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def configure(self, platform: PlatformType, **kwargs) -> PlatformConfig:
        config = PlatformConfig(platform=platform, **kwargs)
        self._configs[platform] = config
        return config

    def get_config(self, platform: PlatformType) -> PlatformConfig:
        return self._configs.get(platform, PlatformConfig(platform=platform))

    def send(
        self,
        content: str,
        platform: PlatformType,
        role: MessageRole = MessageRole.ASSISTANT,
        format: Optional[MessageFormat] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlatformMessage:
        config = self._configs.get(platform, PlatformConfig(platform=platform))
        fmt = format or config.default_format

        if len(content) > config.max_message_length:
            content = content[: config.max_message_length] + "..."

        with self._lock:
            self._next_id += 1
            message = PlatformMessage(
                message_id=f"msg-{self._next_id:06d}",
                platform=platform,
                role=role,
                content=content,
                format=fmt,
                reply_to=reply_to,
                metadata=metadata or {},
            )
            self._message_queue.append(message)
            if len(self._message_queue) > self._MAX_QUEUE:
                self._message_queue = self._message_queue[-self._MAX_QUEUE:]

            for handler in self._handlers.get(platform, []):
                try:
                    handler(message)
                except Exception:
                    pass

            for cb in self._on_send:
                try:
                    cb(message)
                except Exception:
                    pass

            return message

    def send_to_all(
        self,
        content: str,
        exclude: Optional[List[PlatformType]] = None,
        **kwargs,
    ) -> List[PlatformMessage]:
        exclude = exclude or []
        messages = []
        for platform in PlatformType:
            if platform in exclude:
                continue
            if self._configs.get(platform, PlatformConfig(platform=platform)).enabled:
                messages.append(self.send(content, platform, **kwargs))
        return messages

    def register_handler(
        self, platform: PlatformType, handler: Callable[[PlatformMessage], None]
    ) -> None:
        self._handlers[platform].append(handler)

    def on_message(self, callback: Callable[[PlatformMessage], None]) -> None:
        self._on_send.append(callback)

    def get_messages(
        self, platform: Optional[PlatformType] = None, limit: int = 50
    ) -> List[PlatformMessage]:
        queue = list(self._message_queue)
        if platform:
            queue = [m for m in queue if m.platform == platform]
        return queue[-limit:]

    def format_for_platform(
        self, content: str, platform: PlatformType
    ) -> str:
        config = self._configs.get(platform, PlatformConfig(platform=platform))
        if config.default_format == MessageFormat.HTML:
            content = content.replace("\n", "<br>")
        elif config.default_format == MessageFormat.JSON:
            content = json.dumps({"content": content})
        return content

    def enable(self, platform: PlatformType) -> None:
        if platform in self._configs:
            self._configs[platform].enabled = True

    def disable(self, platform: PlatformType) -> None:
        if platform in self._configs:
            self._configs[platform].enabled = False

    def is_enabled(self, platform: PlatformType) -> bool:
        config = self._configs.get(platform)
        return config.enabled if config else False

    def get_enabled_platforms(self) -> List[PlatformType]:
        return [p for p, c in self._configs.items() if c.enabled]

    def _init_defaults(self) -> None:
        self._configs[PlatformType.WEB] = PlatformConfig(
            platform=PlatformType.WEB,
            default_format=MessageFormat.HTML,
            streaming=True,
        )
        self._configs[PlatformType.CLI] = PlatformConfig(
            platform=PlatformType.CLI,
            default_format=MessageFormat.PLAIN,
            max_message_length=4000,
        )
        self._configs[PlatformType.API] = PlatformConfig(
            platform=PlatformType.API,
            default_format=MessageFormat.JSON,
            streaming=False,
        )
        self._configs[PlatformType.WS] = PlatformConfig(
            platform=PlatformType.WS,
            default_format=MessageFormat.JSON,
            streaming=True,
            rate_limit_per_minute=120,
        )
        self._configs[PlatformType.HOOK] = PlatformConfig(
            platform=PlatformType.HOOK,
            default_format=MessageFormat.JSON,
            auth_required=True,
        )

    def get_stats(self) -> dict:
        with self._lock:
            platform_stats = {}
            for pt, cfg in self._configs.items():
                platform_stats[pt.value] = {
                    "enabled": cfg.enabled,
                    "streaming": cfg.streaming,
                    "format": cfg.default_format.value,
                }
            return {
                "platforms": platform_stats,
                "queued_messages": len(self._message_queue),
                "next_id": self._next_id,
                "active_handlers": sum(len(h) for h in self._handlers.values()),
            }

    def reset(self) -> None:
        with self._lock:
            self._message_queue.clear()
            self._configs.clear()
            self._handlers = {p: [] for p in PlatformType}
            self._on_send.clear()
            self._init_defaults()
            self._next_id = 0


def get_platform_bridge() -> PlatformBridge:
    return PlatformBridge.get_instance()
