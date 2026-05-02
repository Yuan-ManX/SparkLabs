"""
Context Engine - Intelligent context window management for lengthy agent sessions.

Architecture:
    ContextEngine/
    |-- ContextStrategy (management strategy enumeration)
    |-- ContextWindow (bounded message buffer dataclass)
    |-- MessageSegment (token-aware message slice dataclass)
    |-- ContextSummary (compressed context snapshot dataclass)
    |-- ContextEngine (global context orchestration)

Manages the context window passed to LLMs during game development sessions.
Supports message pruning, summarization, importance scoring, and token counting
to keep agent conversations within model limits while preserving relevant context.
"""

from __future__ import annotations

import time
import uuid
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


class ContextStrategy(Enum):
    SLIDING_WINDOW = auto()
    SUMMARIZE = auto()
    IMPORTANCE_SCORE = auto()
    HYBRID = auto()


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class MessageSegment:
    segment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole = MessageRole.USER
    content: str = ""
    token_estimate: int = 0
    importance: float = 0.5
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content[:200],
            "tokens": self.token_estimate,
            "importance": self.importance,
        }


@dataclass
class ContextWindow:
    window_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    messages: List[MessageSegment] = field(default_factory=list)
    max_tokens: int = 8000
    current_tokens: int = 0
    strategy: ContextStrategy = ContextStrategy.HYBRID
    system_prompt: str = ""
    keep_last_n: int = 4
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_id": self.window_id,
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "max_tokens": self.max_tokens,
            "current_tokens": self.current_tokens,
            "strategy": self.strategy.name,
        }


@dataclass
class ContextSummary:
    summary_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    token_estimate: int = 0
    message_range: Tuple[int, int] = (0, 0)
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "text": self.text[:200],
            "tokens": self.token_estimate,
            "message_range": list(self.message_range),
        }


class ContextEngine:
    _instance: Optional["ContextEngine"] = None

    def __init__(self):
        self._windows: Dict[str, ContextWindow] = {}
        self._summaries: Dict[str, List[ContextSummary]] = {}
        self._default_max_tokens: int = 8000
        self._default_strategy: ContextStrategy = ContextStrategy.HYBRID

    @classmethod
    def get_instance(cls) -> "ContextEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_window(self, session_id: str, max_tokens: Optional[int] = None,
                      strategy: Optional[ContextStrategy] = None,
                      system_prompt: str = "") -> ContextWindow:
        window = ContextWindow(
            session_id=session_id,
            max_tokens=max_tokens or self._default_max_tokens,
            strategy=strategy or self._default_strategy,
            system_prompt=system_prompt,
        )
        if system_prompt:
            sys_msg = MessageSegment(
                role=MessageRole.SYSTEM,
                content=system_prompt,
                token_estimate=self._estimate_tokens(system_prompt),
            )
            window.messages.append(sys_msg)
            window.current_tokens = sys_msg.token_estimate

        self._windows[window.window_id] = window
        return window

    def get_window(self, window_id: str) -> Optional[ContextWindow]:
        return self._windows.get(window_id)

    def add_message(self, window_id: str, role: MessageRole, content: str,
                    importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> Optional[MessageSegment]:
        window = self._windows.get(window_id)
        if not window:
            return None

        tokens = self._estimate_tokens(content)
        segment = MessageSegment(
            role=role,
            content=content,
            token_estimate=tokens,
            importance=importance,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        window.messages.append(segment)
        window.current_tokens += tokens

        if window.current_tokens > window.max_tokens:
            self._compact(window_id)

        return segment

    def get_messages_for_llm(self, window_id: str) -> List[Dict[str, str]]:
        window = self._windows.get(window_id)
        if not window:
            return []

        if window.current_tokens <= window.max_tokens:
            return [{"role": m.role.value, "content": m.content} for m in window.messages]

        self._compact(window_id)
        return [{"role": m.role.value, "content": m.content} for m in window.messages]

    def summarize_window(self, window_id: str) -> str:
        window = self._windows.get(window_id)
        if not window:
            return ""

        if len(window.messages) <= window.keep_last_n:
            return ""

        to_summarize = window.messages[:-window.keep_last_n]
        parts = []
        for msg in to_summarize:
            role = msg.role.value
            preview = msg.content[:100]
            parts.append(f"[{role}] {preview}")

        summary_text = f"Previous conversation: {' | '.join(parts)}"
        window.summary = summary_text
        return summary_text

    def _compact(self, window_id: str) -> None:
        window = self._windows.get(window_id)
        if not window:
            return

        if window.strategy == ContextStrategy.SLIDING_WINDOW:
            self._compact_sliding(window)
        elif window.strategy == ContextStrategy.IMPORTANCE_SCORE:
            self._compact_importance(window)
        elif window.strategy == ContextStrategy.SUMMARIZE:
            self._compact_summarize(window)
        else:
            self._compact_hybrid(window)

    def _compact_sliding(self, window: ContextWindow) -> None:
        while window.current_tokens > window.max_tokens and len(window.messages) > window.keep_last_n + 1:
            removed = window.messages.pop(1)
            window.current_tokens -= removed.token_estimate

    def _compact_importance(self, window: ContextWindow) -> None:
        system_msg = window.messages[0] if window.messages and window.messages[0].role == MessageRole.SYSTEM else None
        content_msgs = window.messages[1:] if system_msg else window.messages
        keep_last = content_msgs[-window.keep_last_n:]
        middle = content_msgs[:-window.keep_last_n]
        middle.sort(key=lambda m: m.importance)
        while window.current_tokens > window.max_tokens and middle:
            removed = middle.pop(0)
            window.current_tokens -= removed.token_estimate
        window.messages = ([system_msg] if system_msg else []) + middle + keep_last

    def _compact_summarize(self, window: ContextWindow) -> None:
        if len(window.messages) <= window.keep_last_n + 2:
            self._compact_sliding(window)
            return

        summary_text = self.summarize_window(window.window_id)
        keep_last = window.messages[-window.keep_last_n:]
        tokens_removed = window.current_tokens - sum(m.token_estimate for m in keep_last)
        summary_msg = MessageSegment(
            role=MessageRole.SYSTEM,
            content=f"[Conversation summary] {summary_text}",
            token_estimate=self._estimate_tokens(summary_text),
            importance=0.8,
            timestamp=time.time(),
        )
        system_msg = window.messages[0] if window.messages[0].role == MessageRole.SYSTEM else None
        window.messages = ([system_msg] if system_msg else []) + [summary_msg] + keep_last
        window.current_tokens = sum(m.token_estimate for m in window.messages)

    def _compact_hybrid(self, window: ContextWindow) -> None:
        if len(window.messages) <= window.keep_last_n + 4:
            self._compact_importance(window)
        else:
            self._compact_summarize(window)

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        word_count = len(text.split())
        char_count = len(text)
        return max(word_count, char_count // 4)

    def remove_window(self, window_id: str) -> bool:
        if window_id in self._windows:
            del self._windows[window_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        total_messages = sum(len(w.messages) for w in self._windows.values())
        total_tokens = sum(w.current_tokens for w in self._windows.values())
        return {
            "window_count": len(self._windows),
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "avg_tokens_per_window": total_tokens / max(len(self._windows), 1),
            "strategies": {
                strategy.name: sum(1 for w in self._windows.values() if w.strategy == strategy)
                for strategy in ContextStrategy
            },
        }


def get_context_engine() -> ContextEngine:
    return ContextEngine.get_instance()
