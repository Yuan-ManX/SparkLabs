"""
SparkAI Agent - Context Manager

Orthogonal context management with two distinct operations:
- compress(): Shrink context when over budget (summarization)
- select_context(): Per-turn context selection before generation

This separation avoids conflating permanent transcript compression
with per-turn retrieval. Budget parameters control which messages
are protected during compaction.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ContextMessage:
    """A single message in the context window."""
    role: str  # "system", "user", "agent", "tool"
    content: str
    timestamp: float = field(default_factory=time.time)
    token_estimate: int = 0
    protected: bool = False
    compressed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def estimate_tokens(self) -> int:
        if self.token_estimate > 0:
            return self.token_estimate
        # Rough estimate: ~4 chars per token
        self.token_estimate = max(1, len(self.content) // 4)
        return self.token_estimate


@dataclass
class ContextBudget:
    """Budget parameters for context management."""
    max_tokens: int = 8000
    threshold_percent: float = 0.75  # Compress when usage exceeds 75%
    protect_first_n: int = 3  # Always preserve first N messages
    protect_last_n: int = 6  # Always preserve last N messages
    tool_result_max_tokens: int = 500  # Max tokens per tool result


class ContextManager:
    """
    Manages agent context with orthogonal compress vs. select operations.

    Compression permanently shrinks the transcript when over budget.
    Selection retrieves relevant context per-turn without modifying
    the persisted transcript.
    """

    def __init__(self, budget: Optional[ContextBudget] = None):
        self._messages: List[ContextMessage] = []
        self._budget = budget or ContextBudget()
        self._summary: Optional[str] = None
        self._compression_count: int = 0

    @property
    def messages(self) -> List[ContextMessage]:
        return list(self._messages)

    @property
    def token_usage(self) -> int:
        return sum(m.estimate_tokens() for m in self._messages)

    @property
    def token_budget(self) -> int:
        return self._budget.max_tokens

    @property
    def usage_percent(self) -> float:
        if self._budget.max_tokens == 0:
            return 0.0
        return self.token_usage / self._budget.max_tokens

    def add_message(
        self,
        role: str,
        content: str,
        protected: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextMessage:
        """Add a message to the context."""
        msg = ContextMessage(
            role=role,
            content=content,
            protected=protected,
            metadata=metadata or {},
        )
        self._messages.append(msg)

        # Check if compression is needed
        if self.usage_percent > self._budget.threshold_percent:
            self.compress()
        return msg

    def compress(self) -> int:
        """
        Compress the context by summarizing older messages.

        Protects the first N and last N messages. Tool results are
        deterministically trimmed without an LLM call. Returns the
        number of tokens saved.
        """
        if len(self._messages) <= self._budget.protect_first_n + self._budget.protect_last_n:
            return 0

        tokens_before = self.token_usage

        # Step 1: Deterministic tool result pruning
        self._prune_tool_results()

        # Step 2: Compress unprotected middle messages into a summary
        first_n = self._budget.protect_first_n
        last_n = self._budget.protect_last_n
        middle = self._messages[first_n:-last_n] if last_n > 0 else self._messages[first_n:]

        if middle:
            # Build summary from middle messages
            summary_parts = []
            for msg in middle:
                if not msg.compressed:
                    summary_parts.append(f"[{msg.role}] {msg.content[:200]}")

            if summary_parts:
                new_summary = " | ".join(summary_parts[:10])
                if self._summary:
                    self._summary = f"{self._summary} -> {new_summary}"
                else:
                    self._summary = new_summary

                # Mark middle messages as compressed
                for msg in middle:
                    msg.compressed = True
                    msg.content = "[compressed]"
                    msg.token_estimate = 1

            self._compression_count += 1

        tokens_after = self.token_usage
        saved = tokens_before - tokens_after
        logger.debug(
            "Context compressed: %d -> %d tokens (saved %d, compression #%d)",
            tokens_before, tokens_after, saved, self._compression_count,
        )
        return saved

    def _prune_tool_results(self) -> None:
        """Deterministically trim old tool results without an LLM call."""
        max_tokens = self._budget.tool_result_max_tokens
        for msg in self._messages:
            if msg.role == "tool" and not msg.protected:
                if msg.estimate_tokens() > max_tokens:
                    msg.content = msg.content[:max_tokens * 4] + "... [pruned]"
                    msg.token_estimate = 0  # Force re-estimate

    def select_context(
        self,
        query: str,
        max_tokens: Optional[int] = None,
    ) -> List[ContextMessage]:
        """
        Per-turn context selection without modifying the transcript.

        Returns a subset of messages relevant to the query, plus
        protected messages. This runs before every LLM call.
        """
        budget = max_tokens or int(self._budget.max_tokens * 0.6)

        # Always include system messages and protected messages
        selected: List[ContextMessage] = []
        remaining: List[ContextMessage] = []

        for msg in self._messages:
            if msg.role == "system" or msg.protected:
                selected.append(msg)
            else:
                remaining.append(msg)

        # Include summary if available
        if self._summary:
            summary_msg = ContextMessage(
                role="system",
                content=f"[Previous context summary]: {self._summary[:500]}",
                protected=True,
            )
            selected.append(summary_msg)

        # Add most recent messages (recency bias)
        remaining.sort(key=lambda m: m.timestamp, reverse=True)

        current_tokens = sum(m.estimate_tokens() for m in selected)
        for msg in remaining:
            msg_tokens = msg.estimate_tokens()
            if current_tokens + msg_tokens <= budget:
                selected.append(msg)
                current_tokens += msg_tokens

        # Sort by timestamp for coherent ordering
        selected.sort(key=lambda m: m.timestamp)
        return selected

    def should_compress_preflight(self) -> bool:
        """Cheap check if compression should run before next LLM call."""
        return self.usage_percent > self._budget.threshold_percent

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_messages": len(self._messages),
            "token_usage": self.token_usage,
            "token_budget": self._budget.max_tokens,
            "usage_percent": round(self.usage_percent, 3),
            "compression_count": self._compression_count,
            "has_summary": self._summary is not None,
            "protected_count": sum(1 for m in self._messages if m.protected),
        }

    def clear(self) -> None:
        self._messages.clear()
        self._summary = None
        self._compression_count = 0
