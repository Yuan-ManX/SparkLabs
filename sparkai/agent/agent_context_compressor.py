"""
SparkLabs Agent - Context Compressor

Smart context window management that summarizes conversation history,
prioritizes relevant information, compresses tool outputs, and maintains
coherent agent state within token limits.

Architecture:
  AgentContextCompressor (singleton)
    |-- ContentChunk registry (all tracked content pieces)
    |-- CompressionPolicy engine (strategy-driven compression rules)
    |-- TokenBudget monitor (real-time token usage tracking)
    |-- CompressionResult ledger (historical compression outcomes)

Compression Strategies:
  - SUMMARIZE: condense content into concise summaries via abstractive compression
  - TRUNCATE: keep the first N tokens, discarding the remainder
  - EXTRACT_KEY: isolate and retain only high-priority excerpts
  - PRUNE_OLD: remove chunks older than a configured time threshold
  - PRIORITY_FILTER: keep critical/high-priority chunks, drop lower tiers
  - HYBRID: combine multiple strategies adaptively based on content profile
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CompressionStrategy(Enum):
    SUMMARIZE = "summarize"
    TRUNCATE = "truncate"
    EXTRACT_KEY = "extract_key"
    PRUNE_OLD = "prune_old"
    PRIORITY_FILTER = "priority_filter"
    HYBRID = "hybrid"


class ContentPriority(Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    DISPOSABLE = 1


class ContentType(Enum):
    SYSTEM_PROMPT = "system_prompt"
    TOOL_OUTPUT = "tool_output"
    USER_MESSAGE = "user_message"
    AGENT_THOUGHT = "agent_thought"
    MEMORY_SNIPPET = "memory_snippet"
    CODE_BLOCK = "code_block"


class CompressionTrigger(Enum):
    TOKEN_THRESHOLD = "token_threshold"
    TURN_COUNT = "turn_count"
    TIME_ELAPSED = "time_elapsed"
    MANUAL = "manual"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class ContentChunk:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    content: str = ""
    content_type: ContentType = ContentType.USER_MESSAGE
    priority: ContentPriority = ContentPriority.MEDIUM
    token_estimate: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    compression_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "content_type": self.content_type.value,
            "priority": self.priority.value,
            "token_estimate": self.token_estimate,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "compression_count": self.compression_count,
        }


@dataclass
class CompressionResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    policy_id: str = ""
    strategy: CompressionStrategy = CompressionStrategy.SUMMARIZE
    original_chunks: List[ContentChunk] = field(default_factory=list)
    compressed_chunks: List[ContentChunk] = field(default_factory=list)
    original_token_count: int = 0
    compressed_token_count: int = 0
    savings_pct: float = 0.0
    duration_ms: float = 0.0
    compressed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "strategy": self.strategy.value,
            "original_chunks": [c.to_dict() for c in self.original_chunks],
            "compressed_chunks": [c.to_dict() for c in self.compressed_chunks],
            "original_token_count": self.original_token_count,
            "compressed_token_count": self.compressed_token_count,
            "savings_pct": round(self.savings_pct, 1),
            "duration_ms": round(self.duration_ms, 2),
            "compressed_at": self.compressed_at,
        }


@dataclass
class TokenBudget:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    total_allocated: int = 0
    total_used: int = 0
    available: int = 0
    usage_pct: float = 0.0
    chunk_count: int = 0
    critical_reserved: int = 0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "total_allocated": self.total_allocated,
            "total_used": self.total_used,
            "available": self.available,
            "usage_pct": round(self.usage_pct, 1),
            "chunk_count": self.chunk_count,
            "critical_reserved": self.critical_reserved,
            "last_updated": self.last_updated,
        }


@dataclass
class CompressionPolicy:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    strategy: CompressionStrategy = CompressionStrategy.SUMMARIZE
    trigger_threshold_token: int = 8000
    target_token_count: int = 4000
    preserve_critical: bool = True
    max_chunk_age_seconds: float = 3600.0
    min_priority: ContentPriority = ContentPriority.LOW
    enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "strategy": self.strategy.value,
            "trigger_threshold_token": self.trigger_threshold_token,
            "target_token_count": self.target_token_count,
            "preserve_critical": self.preserve_critical,
            "max_chunk_age_seconds": self.max_chunk_age_seconds,
            "min_priority": self.min_priority.value,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


class AgentContextCompressor:
    """Smart context window manager for the SparkLabs agent runtime."""

    _instance: Optional["AgentContextCompressor"] = None
    _lock = threading.RLock()

    _DEFAULT_TOKEN_ESTIMATE_RATIO: float = 0.75
    _SUMMARY_TOKEN_BUDGET: int = 256
    _KEY_EXTRACT_SENTENCE_THRESHOLD: int = 3

    def __init__(self) -> None:
        self._chunks: Dict[str, ContentChunk] = {}
        self._policies: Dict[str, CompressionPolicy] = {}
        self._compression_history: List[CompressionResult] = []

    @classmethod
    def get_instance(cls) -> "AgentContextCompressor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Chunk Management ----

    def register_chunk(self,
                       content: str,
                       content_type: ContentType = ContentType.USER_MESSAGE,
                       priority: ContentPriority = ContentPriority.MEDIUM,
                       token_estimate: int = 0,
                       metadata: Optional[Dict[str, Any]] = None) -> ContentChunk:
        if token_estimate <= 0:
            token_estimate = self.estimate_tokens(content)
        chunk = ContentChunk(
            content=content,
            content_type=content_type,
            priority=priority,
            token_estimate=token_estimate,
            metadata=metadata or {},
        )
        self._chunks[chunk.id] = chunk
        return chunk

    # ---- Policy Management ----

    def create_policy(self,
                      name: str,
                      strategy: CompressionStrategy = CompressionStrategy.SUMMARIZE,
                      trigger_threshold_token: int = 8000,
                      target_token_count: int = 4000,
                      preserve_critical: bool = True) -> CompressionPolicy:
        policy = CompressionPolicy(
            name=name,
            strategy=strategy,
            trigger_threshold_token=trigger_threshold_token,
            target_token_count=target_token_count,
            preserve_critical=preserve_critical,
        )
        self._policies[policy.id] = policy
        return policy

    # ---- Compression Engine ----

    def compress(self,
                 policy_id: str,
                 chunks: Optional[List[ContentChunk]] = None) -> CompressionResult:
        policy = self._policies.get(policy_id)
        if policy is None:
            policy = CompressionPolicy(strategy=CompressionStrategy.TRUNCATE)

        source = chunks if chunks is not None else list(self._chunks.values())
        if not source:
            return CompressionResult(
                policy_id=policy_id,
                strategy=policy.strategy,
                original_token_count=0,
                compressed_token_count=0,
                savings_pct=0.0,
            )

        start_time = time.time()
        original_total = sum(ch.token_estimate for ch in source)
        result_chunks: List[ContentChunk] = []

        if policy.strategy == CompressionStrategy.SUMMARIZE:
            result_chunks = self._compress_summarize(source, policy)
        elif policy.strategy == CompressionStrategy.TRUNCATE:
            result_chunks = self._compress_truncate(source, policy)
        elif policy.strategy == CompressionStrategy.EXTRACT_KEY:
            result_chunks = self._compress_extract_key(source, policy)
        elif policy.strategy == CompressionStrategy.PRUNE_OLD:
            result_chunks = self._compress_prune_old(source, policy)
        elif policy.strategy == CompressionStrategy.PRIORITY_FILTER:
            result_chunks = self._compress_priority_filter(source, policy)
        elif policy.strategy == CompressionStrategy.HYBRID:
            result_chunks = self._compress_hybrid(source, policy)

        compressed_total = sum(ch.token_estimate for ch in result_chunks)

        for ch in source:
            if ch.id in self._chunks:
                self._chunks[ch.id].compression_count += 1

        savings_pct = 0.0
        if original_total > 0:
            savings_pct = ((original_total - compressed_total) / original_total) * 100.0

        duration_ms = (time.time() - start_time) * 1000.0

        result = CompressionResult(
            policy_id=policy_id,
            strategy=policy.strategy,
            original_chunks=list(source),
            compressed_chunks=result_chunks,
            original_token_count=original_total,
            compressed_token_count=compressed_total,
            savings_pct=savings_pct,
            duration_ms=duration_ms,
        )
        self._compression_history.append(result)
        return result

    def _compress_summarize(self,
                            chunks: List[ContentChunk],
                            policy: CompressionPolicy) -> List[ContentChunk]:
        combined = ""
        for ch in self._sort_by_priority(chunks):
            combined += ch.content + "\n"
        summary = self._generate_summary(combined)
        summary_chunk = ContentChunk(
            content=summary,
            content_type=ContentType.AGENT_THOUGHT,
            priority=ContentPriority.HIGH,
            token_estimate=self.estimate_tokens(summary),
        )
        return [summary_chunk]

    def _compress_truncate(self,
                           chunks: List[ContentChunk],
                           policy: CompressionPolicy) -> List[ContentChunk]:
        ordered = self._sort_by_priority(chunks)
        accumulated = 0
        kept: List[ContentChunk] = []
        for ch in ordered:
            if accumulated + ch.token_estimate <= policy.target_token_count:
                kept.append(ch)
                accumulated += ch.token_estimate
            else:
                break
        return kept

    def _compress_extract_key(self,
                              chunks: List[ContentChunk],
                              policy: CompressionPolicy) -> List[ContentChunk]:
        result: List[ContentChunk] = []
        target = max(policy.target_token_count, 1)
        per_chunk_budget = max(target // max(len(chunks), 1), 16)
        for ch in self._sort_by_priority(chunks):
            extracted = self._extract_key_sentences(ch.content)
            extract_chunk = ContentChunk(
                content=extracted,
                content_type=ch.content_type,
                priority=ch.priority,
                token_estimate=min(self.estimate_tokens(extracted), per_chunk_budget),
                metadata={"source_chunk_id": ch.id},
            )
            result.append(extract_chunk)
        return result

    def _compress_prune_old(self,
                            chunks: List[ContentChunk],
                            policy: CompressionPolicy) -> List[ContentChunk]:
        now = time.time()
        threshold = now - policy.max_chunk_age_seconds
        kept: List[ContentChunk] = []
        for ch in chunks:
            if ch.created_at >= threshold:
                kept.append(ch)
            elif policy.preserve_critical and ch.priority == ContentPriority.CRITICAL:
                kept.append(ch)
        return kept

    def _compress_priority_filter(self,
                                  chunks: List[ContentChunk],
                                  policy: CompressionPolicy) -> List[ContentChunk]:
        result: List[ContentChunk] = []
        accumulated = 0
        for ch in self._sort_by_priority(chunks):
            if ch.priority.value < policy.min_priority.value:
                continue
            if policy.preserve_critical and ch.priority == ContentPriority.CRITICAL:
                result.append(ch)
                accumulated += ch.token_estimate
                continue
            if accumulated + ch.token_estimate <= policy.target_token_count:
                result.append(ch)
                accumulated += ch.token_estimate
            else:
                break
        return result

    def _compress_hybrid(self,
                         chunks: List[ContentChunk],
                         policy: CompressionPolicy) -> List[ContentChunk]:
        old_filtered = self._compress_prune_old(chunks, policy)
        priority_filtered = self._compress_priority_filter(old_filtered, policy)
        if sum(ch.token_estimate for ch in priority_filtered) > policy.target_token_count:
            return self._compress_truncate(priority_filtered, policy)
        return priority_filtered

    # ---- Token Estimation ----

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        char_count = len(text)
        word_count = len(text.split())
        estimated = max(
            int(char_count * self._DEFAULT_TOKEN_ESTIMATE_RATIO),
            int(word_count * 1.3),
            1,
        )
        return estimated

    # ---- Budget Tracking ----

    def get_current_budget(self) -> TokenBudget:
        total_used = sum(ch.token_estimate for ch in self._chunks.values())
        critical_used = sum(
            ch.token_estimate
            for ch in self._chunks.values()
            if ch.priority == ContentPriority.CRITICAL
        )
        total_allocated = 0
        for policy in self._policies.values():
            total_allocated = max(total_allocated, policy.trigger_threshold_token)
        if total_allocated == 0:
            total_allocated = total_used * 2
        available = max(total_allocated - total_used, 0)
        usage_pct = 0.0
        if total_allocated > 0:
            usage_pct = (total_used / total_allocated) * 100.0
        return TokenBudget(
            total_allocated=total_allocated,
            total_used=total_used,
            available=available,
            usage_pct=usage_pct,
            chunk_count=len(self._chunks),
            critical_reserved=critical_used,
        )

    # ---- Relevance Selection ----

    def select_relevant(self,
                        query: str,
                        chunks: Optional[List[ContentChunk]] = None,
                        max_tokens: int = 2000) -> List[ContentChunk]:
        source = chunks if chunks is not None else list(self._chunks.values())
        if not source:
            return []
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        scored: List[Tuple[ContentChunk, float]] = []
        for ch in source:
            score = self._compute_relevance_score(ch, query_lower, query_terms)
            scored.append((ch, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        selected: List[ContentChunk] = []
        accumulated = 0
        for ch, _score in scored:
            if accumulated + ch.token_estimate <= max_tokens:
                selected.append(ch)
                accumulated += ch.token_estimate
            else:
                break
        return selected

    # ---- History Retrieval ----

    def get_compression_history(self, limit: int = 20) -> List[CompressionResult]:
        if limit <= 0:
            return list(self._compression_history)
        return self._compression_history[-limit:]

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        total_original = sum(r.original_token_count for r in self._compression_history)
        total_compressed = sum(r.compressed_token_count for r in self._compression_history)
        overall_savings_pct = 0.0
        if total_original > 0:
            overall_savings_pct = ((total_original - total_compressed) / total_original) * 100.0
        strategy_counts: Dict[str, int] = {}
        for r in self._compression_history:
            key = r.strategy.value
            strategy_counts[key] = strategy_counts.get(key, 0) + 1
        priority_distribution: Dict[int, int] = {}
        for ch in self._chunks.values():
            pv = ch.priority.value
            priority_distribution[pv] = priority_distribution.get(pv, 0) + 1
        type_distribution: Dict[str, int] = {}
        for ch in self._chunks.values():
            key = ch.content_type.value
            type_distribution[key] = type_distribution.get(key, 0) + 1
        return {
            "total_chunks": len(self._chunks),
            "total_policies": len(self._policies),
            "total_compressions": len(self._compression_history),
            "total_tokens_original": total_original,
            "total_tokens_saved": total_original - total_compressed,
            "overall_savings_pct": round(overall_savings_pct, 1),
            "strategy_usage": strategy_counts,
            "priority_distribution": priority_distribution,
            "content_type_distribution": type_distribution,
        }

    # ---- Internal Helpers ----

    @staticmethod
    def _sort_by_priority(chunks: List[ContentChunk]) -> List[ContentChunk]:
        return sorted(chunks, key=lambda ch: ch.priority.value, reverse=True)

    @staticmethod
    def _generate_summary(text: str) -> str:
        lines = text.strip().split("\n")
        if not lines:
            return ""
        key_lines: List[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if len(stripped) < 20:
                continue
            key_lines.append(stripped)
        if len(key_lines) <= 3:
            return " | ".join(key_lines)
        first_few = key_lines[:3]
        remaining_count = len(key_lines) - 3
        summary = " | ".join(first_few)
        if remaining_count > 0:
            summary += f" ... ({remaining_count} more segments)"
        return summary

    @staticmethod
    def _extract_key_sentences(text: str) -> str:
        sentences = text.replace("\n", ". ").split(". ")
        meaningful: List[str] = []
        for sentence in sentences:
            stripped = sentence.strip()
            if len(stripped) > 15 and any(kw in stripped.lower() for kw in
                                          ["result", "error", "output", "return",
                                           "status", "value", "data", "key", "critical"]):
                meaningful.append(stripped)
        if not meaningful:
            meaningful = [s.strip() for s in sentences if len(s.strip()) > 15]
        selected = meaningful[:AgentContextCompressor._KEY_EXTRACT_SENTENCE_THRESHOLD]
        return ". ".join(selected) + "." if selected else text[:200]

    @staticmethod
    def _compute_relevance_score(chunk: ContentChunk,
                                 query_lower: str,
                                 query_terms: set) -> float:
        score = 0.0
        content_lower = chunk.content.lower()
        for term in query_terms:
            if term in content_lower:
                score += 1.0
        if chunk.content_type in (ContentType.SYSTEM_PROMPT, ContentType.TOOL_OUTPUT):
            score *= 0.8
        elif chunk.content_type == ContentType.USER_MESSAGE:
            score *= 1.2
        if chunk.priority == ContentPriority.CRITICAL:
            score *= 1.5
        elif chunk.priority == ContentPriority.HIGH:
            score *= 1.2
        score += chunk.token_estimate * 0.0001
        return score


def get_context_compressor() -> AgentContextCompressor:
    return AgentContextCompressor.get_instance()