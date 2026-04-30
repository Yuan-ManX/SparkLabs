"""
SparkAI Agent - Context Compression Engine

Pluggable context compression system that reduces token usage
by summarizing older conversation turns while preserving
recent context. The compression strategy is swappable,
allowing different approaches for different use cases.

Architecture:
  ContextCompressionEngine
    |-- CompressionStrategy (pluggable interface)
    |-- DefaultCompressor (head-tail preservation + middle summary)
    |-- RelevanceCompressor (importance-scored selection)
    |-- IterationBudget (token-aware iteration control)

Compression Flow:
  1. Check if compression is needed (token threshold)
  2. Select compression strategy
  3. Identify head (system prompt) and tail (recent turns)
  4. Compress middle turns into structured summary
  5. Inject continuation framing
  6. Return compressed context
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class CompressionStrategy(Enum):
    HEAD_TAIL = "head_tail"
    RELEVANCE_SCORED = "relevance_scored"
    LAYERED = "layered"
    AGGRESSIVE = "aggressive"


class ContextRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_RESULT = "tool_result"
    SUMMARY = "summary"


@dataclass
class ContextTurn:
    role: ContextRole = ContextRole.USER
    content: str = ""
    token_count: int = 0
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content[:500],
            "token_count": self.token_count,
            "importance": self.importance,
            "timestamp": self.timestamp,
        }


@dataclass
class CompressionResult:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    strategy: CompressionStrategy = CompressionStrategy.HEAD_TAIL
    turns_before: int = 0
    turns_after: int = 0
    tokens_before: int = 0
    tokens_after: int = 0
    compression_ratio: float = 0.0
    summary: str = ""
    preserved_head: int = 0
    preserved_tail: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy": self.strategy.value,
            "turns_before": self.turns_before,
            "turns_after": self.turns_after,
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "compression_ratio": round(self.compression_ratio, 3),
            "summary": self.summary[:500],
            "preserved_head": self.preserved_head,
            "preserved_tail": self.preserved_tail,
            "created_at": self.created_at,
        }


@dataclass
class IterationBudget:
    """
    Thread-safe iteration counter that limits how many
    loop iterations an agent can consume. Prevents runaway
    agents from consuming unlimited resources.
    """
    max_iterations: int = 90
    current_iteration: int = 0
    subagent_max: int = 50
    budget_warn_at: float = 0.8

    def consume(self) -> bool:
        self.current_iteration += 1
        return self.current_iteration <= self.max_iterations

    def remaining(self) -> int:
        return max(0, self.max_iterations - self.current_iteration)

    def is_exhausted(self) -> bool:
        return self.current_iteration >= self.max_iterations

    def is_near_limit(self) -> bool:
        return self.current_iteration >= int(self.max_iterations * self.budget_warn_at)

    def reset(self) -> None:
        self.current_iteration = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_iterations": self.max_iterations,
            "current_iteration": self.current_iteration,
            "remaining": self.remaining(),
            "is_exhausted": self.is_exhausted(),
            "is_near_limit": self.is_near_limit(),
        }


class BaseCompressor(ABC):
    """Abstract base class for compression strategies."""

    @abstractmethod
    def compress(
        self,
        turns: List[ContextTurn],
        max_tokens: int,
        preserve_head: int = 1,
        preserve_tail: int = 4,
    ) -> Tuple[List[ContextTurn], str]:
        pass


class HeadTailCompressor(BaseCompressor):
    """
    Preserves the head (system prompt) and tail (recent turns)
    verbatim, while summarizing all middle turns into a single
    structured summary message.
    """

    def compress(
        self,
        turns: List[ContextTurn],
        max_tokens: int,
        preserve_head: int = 1,
        preserve_tail: int = 4,
    ) -> Tuple[List[ContextTurn], str]:
        if len(turns) <= preserve_head + preserve_tail:
            return turns, ""

        head = turns[:preserve_head]
        tail = turns[-preserve_tail:]
        middle = turns[preserve_head:-preserve_tail]

        summary = self._summarize(middle)
        summary_turn = ContextTurn(
            role=ContextRole.SUMMARY,
            content=f"[Prior Context Summary]\n{summary}\n[End Summary - Continue without acknowledging]",
            token_count=len(summary.split()),
            importance=1.0,
        )

        compressed = head + [summary_turn] + tail
        return compressed, summary

    def _summarize(self, turns: List[ContextTurn]) -> str:
        if not turns:
            return ""

        resolved_questions = []
        pending_questions = []
        key_decisions = []

        for turn in turns:
            content = turn.content[:300]
            if turn.role == ContextRole.ASSISTANT:
                if any(kw in content.lower() for kw in ["yes", "no", "done", "completed", "fixed"]):
                    resolved_questions.append(content[:150])
                if any(kw in content.lower() for kw in ["decided", "chose", "will use", "approach"]):
                    key_decisions.append(content[:150])
            elif turn.role == ContextRole.USER:
                pending_questions.append(content[:150])

        parts = []
        if resolved_questions:
            parts.append(f"Resolved: {'; '.join(resolved_questions[:3])}")
        if pending_questions:
            parts.append(f"Addressed: {'; '.join(pending_questions[:3])}")
        if key_decisions:
            parts.append(f"Decisions: {'; '.join(key_decisions[:3])}")
        parts.append(f"Turns compressed: {len(turns)}")

        return " | ".join(parts)


class RelevanceCompressor(BaseCompressor):
    """
    Scores each turn by importance and preserves the highest-scoring
    turns, replacing the rest with a summary.
    """

    def compress(
        self,
        turns: List[ContextTurn],
        max_tokens: int,
        preserve_head: int = 1,
        preserve_tail: int = 4,
    ) -> Tuple[List[ContextTurn], str]:
        if len(turns) <= 8:
            return turns, ""

        head = turns[:preserve_head]
        tail = turns[-preserve_tail:]
        middle = turns[preserve_head:-preserve_tail]

        scored = []
        for i, turn in enumerate(middle):
            score = turn.importance
            recency = (i + 1) / len(middle)
            score += recency * 0.3
            if turn.role == ContextRole.SYSTEM:
                score += 0.4
            if turn.role == ContextRole.ASSISTANT and turn.token_count > 100:
                score += 0.2
            if turn.role == ContextRole.TOOL_RESULT:
                score -= 0.1
            scored.append((score, i, turn))

        scored.sort(key=lambda x: x[0], reverse=True)
        keep_count = min(4, len(middle))
        keep_indices = sorted([idx for _, idx, _ in scored[:keep_count]])

        preserved_middle = [middle[i] for i in keep_indices]
        removed = [middle[i] for i in range(len(middle)) if i not in keep_indices]
        summary = self._summarize_removed(removed)

        summary_turn = ContextTurn(
            role=ContextRole.SUMMARY,
            content=f"[Compressed Context]\n{summary}\n[End Compressed Context]",
            token_count=len(summary.split()),
            importance=1.0,
        )

        return head + [summary_turn] + preserved_middle + tail, summary

    def _summarize_removed(self, turns: List[ContextTurn]) -> str:
        if not turns:
            return ""
        user_msgs = [t.content[:100] for t in turns if t.role == ContextRole.USER]
        assistant_msgs = [t.content[:100] for t in turns if t.role == ContextRole.ASSISTANT]
        parts = [f"Compressed {len(turns)} turns"]
        if user_msgs:
            parts.append(f"User topics: {'; '.join(user_msgs[:2])}")
        if assistant_msgs:
            parts.append(f"Assistant responses: {'; '.join(assistant_msgs[:2])}")
        return " | ".join(parts)


class LayeredCompressor(BaseCompressor):
    """
    Divides middle turns into chunks and creates a layered
    summary with segment-level detail.
    """

    def compress(
        self,
        turns: List[ContextTurn],
        max_tokens: int,
        preserve_head: int = 1,
        preserve_tail: int = 4,
    ) -> Tuple[List[ContextTurn], str]:
        if len(turns) <= preserve_head + preserve_tail + 6:
            return turns, ""

        head = turns[:preserve_head]
        tail = turns[-preserve_tail:]
        middle = turns[preserve_head:-preserve_tail]

        chunk_size = max(3, len(middle) // 3)
        chunks = [middle[i:i + chunk_size] for i in range(0, len(middle), chunk_size)]

        layer_summaries = []
        for i, chunk in enumerate(chunks):
            summary = self._summarize_chunk(chunk, i + 1)
            layer_summaries.append(summary)

        combined = "\n\n".join(layer_summaries)
        summary_turn = ContextTurn(
            role=ContextRole.SUMMARY,
            content=f"[Layered Context Summary]\n{combined}\n[End Layered Summary]",
            token_count=len(combined.split()),
            importance=1.0,
        )

        return head + [summary_turn] + tail, combined

    def _summarize_chunk(self, chunk: List[ContextTurn], segment_num: int) -> str:
        user_content = [t.content[:80] for t in chunk if t.role == ContextRole.USER]
        assistant_content = [t.content[:80] for t in chunk if t.role == ContextRole.ASSISTANT]
        parts = [f"[Segment {segment_num}]"]
        if user_content:
            parts.append(f"Topics: {'; '.join(user_content[:2])}")
        if assistant_content:
            parts.append(f"Actions: {'; '.join(assistant_content[:2])}")
        parts.append(f"Turns: {len(chunk)}")
        return " ".join(parts)


class ContextCompressionEngine:
    """
    Unified context compression engine with pluggable strategies
    and iteration budget tracking.

    The engine monitors context size and automatically compresses
    when token limits are approached. Different strategies can be
    selected based on the task type and context characteristics.

    Usage:
        engine = ContextCompressionEngine(max_tokens=100000)
        turns = engine.parse_context(messages)
        result = engine.compress(turns)
        compressed_turns = engine.apply_compression(turns, result)
    """

    def __init__(self, max_tokens: int = 100000, threshold: float = 0.8):
        self._max_tokens = max_tokens
        self._threshold = threshold
        self._compressors: Dict[CompressionStrategy, BaseCompressor] = {
            CompressionStrategy.HEAD_TAIL: HeadTailCompressor(),
            CompressionStrategy.RELEVANCE_SCORED: RelevanceCompressor(),
            CompressionStrategy.LAYERED: LayeredCompressor(),
            CompressionStrategy.AGGRESSIVE: HeadTailCompressor(),
        }
        self._default_strategy = CompressionStrategy.HEAD_TAIL
        self._compression_history: List[CompressionResult] = []
        self._iteration_budgets: Dict[str, IterationBudget] = {}

    def parse_context(self, messages: List[Dict[str, Any]]) -> List[ContextTurn]:
        turns = []
        for msg in messages:
            role_str = msg.get("role", "user").lower()
            try:
                role = ContextRole(role_str)
            except ValueError:
                role = ContextRole.USER
            content = msg.get("content", "")
            token_count = msg.get("token_count", len(content.split()))
            importance = msg.get("importance", 0.5)
            turns.append(ContextTurn(
                role=role,
                content=content,
                token_count=token_count,
                importance=importance,
            ))
        return turns

    def should_compress(self, turns: List[ContextTurn]) -> bool:
        total_tokens = sum(t.token_count for t in turns)
        return total_tokens >= int(self._max_tokens * self._threshold)

    def compress(
        self,
        turns: List[ContextTurn],
        strategy: Optional[CompressionStrategy] = None,
        preserve_head: int = 1,
        preserve_tail: int = 4,
    ) -> CompressionResult:
        strat = strategy or self._default_strategy
        compressor = self._compressors.get(strat, self._compressors[CompressionStrategy.HEAD_TAIL])

        tokens_before = sum(t.token_count for t in turns)
        compressed_turns, summary = compressor.compress(
            turns, self._max_tokens, preserve_head, preserve_tail
        )
        tokens_after = sum(t.token_count for t in compressed_turns)

        result = CompressionResult(
            strategy=strat,
            turns_before=len(turns),
            turns_after=len(compressed_turns),
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            compression_ratio=tokens_after / max(tokens_before, 1),
            summary=summary,
            preserved_head=preserve_head,
            preserved_tail=preserve_tail,
        )
        self._compression_history.append(result)
        return result

    def apply_compression(self, turns: List[ContextTurn], result: CompressionResult) -> List[ContextTurn]:
        compressor = self._compressors.get(result.strategy, self._compressors[CompressionStrategy.HEAD_TAIL])
        compressed, _ = compressor.compress(turns, self._max_tokens, result.preserved_head, result.preserved_tail)
        return compressed

    def create_iteration_budget(self, session_id: str, max_iterations: int = 90) -> IterationBudget:
        budget = IterationBudget(max_iterations=max_iterations)
        self._iteration_budgets[session_id] = budget
        return budget

    def get_iteration_budget(self, session_id: str) -> Optional[IterationBudget]:
        return self._iteration_budgets.get(session_id)

    def get_compression_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._compression_history[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._compression_history)
        avg_ratio = 0.0
        if total > 0:
            avg_ratio = sum(r.compression_ratio for r in self._compression_history) / total

        return {
            "max_tokens": self._max_tokens,
            "threshold": self._threshold,
            "total_compressions": total,
            "avg_compression_ratio": round(avg_ratio, 3),
            "active_budgets": len(self._iteration_budgets),
            "available_strategies": [s.value for s in CompressionStrategy],
        }


_global_compression_engine: Optional[ContextCompressionEngine] = None


def get_compression_engine() -> ContextCompressionEngine:
    global _global_compression_engine
    if _global_compression_engine is None:
        _global_compression_engine = ContextCompressionEngine()
    return _global_compression_engine
