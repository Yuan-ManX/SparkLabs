"""
SparkLabs Agent - Conversation Memory Engine

Persistent multi-turn dialogue management with context threading for AI
agents within the game engine. Tracks conversation threads across sessions,
supports summarization strategies, semantic search over historical turns,
thread merging, archival, and context assembly for downstream reasoning.

Architecture:
  ConversationMemoryEngine (Singleton)
    |-- ConversationTurn (individual dialogue turn with role and metadata)
    |-- ConversationThread (dialogue session with ordered turns)
    |-- ThreadContext (assembled context window for a thread)
    |-- MemoryIndex (keyword and thread-level lookup structures)

Context Strategies:
  SLIDING_WINDOW - most recent N turns
  SUMMARY - compressed natural language summary of the thread
  RELEVANCE - turns ranked by keyword overlap with the current query
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class TurnRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ThreadState(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ContextStrategy(Enum):
    SLIDING_WINDOW = "sliding_window"
    SUMMARY = "summary"
    RELEVANCE = "relevance"


@dataclass
class ConversationTurn:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    thread_id: str = ""
    role: TurnRole = TurnRole.USER
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    turn_index: int = 0
    created_at: float = field(default_factory=time.time)
    embedding_sim: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "role": self.role.value,
            "content": self.content,
            "metadata": self.metadata,
            "token_count": self.token_count,
            "turn_index": self.turn_index,
            "created_at": self.created_at,
            "embedding_sim": round(self.embedding_sim, 4),
        }


@dataclass
class ConversationThread:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    title: str = ""
    system_prompt: str = ""
    state: ThreadState = ThreadState.ACTIVE
    turn_ids: List[str] = field(default_factory=list)
    context_summary: str = ""
    summary_strategy: str = "summary"
    token_budget: int = 0
    created_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "title": self.title,
            "system_prompt": self.system_prompt,
            "state": self.state.value,
            "turn_count": len(self.turn_ids),
            "context_summary": self.context_summary,
            "summary_strategy": self.summary_strategy,
            "token_budget": self.token_budget,
            "created_at": self.created_at,
            "last_activity_at": self.last_activity_at,
        }


@dataclass
class ThreadContext:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    thread_id: str = ""
    recent_turns: List[str] = field(default_factory=list)
    summary: str = ""
    active_topics: List[str] = field(default_factory=list)
    context_window_size: int = 10
    strategy: ContextStrategy = ContextStrategy.SLIDING_WINDOW
    total_token_estimate: int = 0
    assembled_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "recent_turn_count": len(self.recent_turns),
            "summary": self.summary,
            "active_topics": self.active_topics,
            "context_window_size": self.context_window_size,
            "strategy": self.strategy.value,
            "total_token_estimate": self.total_token_estimate,
            "assembled_at": self.assembled_at,
        }


@dataclass
class MemoryIndex:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    keyword_index: Dict[str, Set[str]] = field(default_factory=dict)
    thread_index: Dict[str, List[str]] = field(default_factory=dict)
    agent_index: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "unique_keywords": len(self.keyword_index),
            "indexed_threads": len(self.thread_index),
            "indexed_agents": len(self.agent_index),
        }


class ConversationMemoryEngine:
    """Persistent multi-turn dialogue management with context threading."""

    _instance: Optional["ConversationMemoryEngine"] = None
    _lock = threading.RLock()

    _DEFAULT_CONTEXT_WINDOW = 10
    _MAX_SEARCH_RESULTS = 50
    _SUMMARY_TRUNCATION_LENGTH = 500
    _TOKEN_ESTIMATE_CHARS_PER_TOKEN = 4
    _TOPIC_EXTRACTION_MIN_TOKENS = 3
    _TOPIC_EXTRACTION_MAX_CANDIDATES = 10
    _SLIDING_WINDOW_OVERLAP_TURNS = 2
    _RELEVANCE_SCORE_THRESHOLD = 0.10

    def __init__(self) -> None:
        self._threads: Dict[str, ConversationThread] = {}
        self._turns: Dict[str, ConversationTurn] = {}
        self._index: MemoryIndex = MemoryIndex()
        self._search_cache: Dict[str, List[str]] = {}
        self._thread_count: int = 0
        self._turn_count: int = 0
        self._archive_count: int = 0
        self._merge_events: List[Dict[str, Any]] = []
        self._summaries_generated: int = 0

    @classmethod
    def get_instance(cls) -> "ConversationMemoryEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Thread Lifecycle ----

    def start_thread(
        self,
        agent_id: str,
        title: str = "",
        system_prompt: str = "",
    ) -> ConversationThread:
        with self._lock:
            thread = ConversationThread(
                agent_id=agent_id,
                title=title or self._generate_title(agent_id),
                system_prompt=system_prompt,
                token_budget=self._estimate_tokens(system_prompt),
            )
            self._threads[thread.id] = thread
            self._thread_count += 1
            self._index_thread(thread)
            return thread

    def add_turn(
        self,
        thread_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ConversationTurn]:
        thread = self._threads.get(thread_id)
        if thread is None:
            return None
        if thread.state == ThreadState.ARCHIVED:
            return None
        try:
            turn_role = TurnRole(role.lower())
        except ValueError:
            turn_role = TurnRole.USER
        with self._lock:
            turn = ConversationTurn(
                thread_id=thread_id,
                role=turn_role,
                content=content,
                metadata=metadata or {},
                token_count=self._estimate_tokens(content),
                turn_index=len(thread.turn_ids),
                embedding_sim=self._compute_turn_embedding_sim(content),
            )
            self._turns[turn.id] = turn
            self._turn_count += 1
            thread.turn_ids.append(turn.id)
            thread.last_activity_at = time.time()
            thread.token_budget += turn.token_count
            self._index_turn(turn)
            self._invalidate_search_cache(thread_id)
            return turn

    # ---- Summarization ----

    def summarize_thread(self, thread_id: str, strategy: str = "summary") -> str:
        thread = self._threads.get(thread_id)
        if thread is None:
            return ""
        turns = self._get_thread_turns(thread_id)
        if not turns:
            return "No conversation turns to summarize."
        with self._lock:
            summary = self._build_summary(turns, strategy)
            thread.context_summary = summary
            thread.summary_strategy = strategy
            self._summaries_generated += 1
            return summary

    # ---- Search ----

    def search_conversations(
        self,
        query: str,
        limit: int = 20,
    ) -> List[ConversationTurn]:
        if not query.strip():
            return []
        actual_limit = max(1, min(limit, self._MAX_SEARCH_RESULTS))
        cache_key = f"{query}:{actual_limit}"
        with self._lock:
            if cache_key in self._search_cache:
                cached_ids = self._search_cache[cache_key]
                return [self._turns[tid] for tid in cached_ids if tid in self._turns]
            scored: List[Tuple[ConversationTurn, float]] = []
            query_tokens = set(self._tokenize(query))
            for turn in self._turns.values():
                thread = self._threads.get(turn.thread_id)
                if thread is None or thread.state == ThreadState.ARCHIVED:
                    continue
                score = self._score_turn_relevance(turn, query, query_tokens)
                if score >= self._RELEVANCE_SCORE_THRESHOLD:
                    scored.append((turn, score))
            scored.sort(key=lambda t: t[1], reverse=True)
            result = [turn for turn, _ in scored[:actual_limit]]
            self._search_cache[cache_key] = [t.id for t in result]
            return result

    # ---- Context Assembly ----

    def get_thread_context(self, thread_id: str) -> Optional[ThreadContext]:
        thread = self._threads.get(thread_id)
        if thread is None:
            return None
        turns = self._get_thread_turns(thread_id)
        with self._lock:
            window_size = self._DEFAULT_CONTEXT_WINDOW
            recent = [t.id for t in turns[-window_size:]]
            topics = self._extract_topics(turns, self._TOPIC_EXTRACTION_MAX_CANDIDATES)
            strategy = ContextStrategy.SLIDING_WINDOW
            if thread.context_summary:
                strategy = ContextStrategy.SUMMARY
            elif len(turns) > window_size * 2:
                strategy = ContextStrategy.RELEVANCE
            total_tokens = sum(t.token_count for t in turns[-window_size:])
            ctx = ThreadContext(
                thread_id=thread_id,
                recent_turns=recent,
                summary=thread.context_summary,
                active_topics=topics,
                context_window_size=window_size,
                strategy=strategy,
                total_token_estimate=total_tokens,
            )
            return ctx

    # ---- Thread Merge ----

    def merge_threads(self, source_ids: List[str], target_id: str) -> bool:
        target = self._threads.get(target_id)
        if target is None:
            return False
        if target.state == ThreadState.ARCHIVED:
            return False
        if not source_ids:
            return False
        with self._lock:
            merged_turns: List[ConversationTurn] = []
            for sid in source_ids:
                source = self._threads.get(sid)
                if source is None or source.id == target_id:
                    continue
                source_turns = self._get_thread_turns(sid)
                for turn in source_turns:
                    turn.thread_id = target_id
                    turn.turn_index = len(target.turn_ids) + len(merged_turns)
                    merged_turns.append(turn)
                self._reindex_thread_turns(source, target)
                source.state = ThreadState.ARCHIVED
                source.turn_ids.clear()
                self._archive_count += 1
            for turn in merged_turns:
                target.turn_ids.append(turn.id)
                target.token_budget += turn.token_count
            target.last_activity_at = time.time()
            self._merge_events.append({
                "source_ids": list(source_ids),
                "target_id": target_id,
                "merged_turn_count": len(merged_turns),
                "timestamp": time.time(),
            })
            if merged_turns:
                self._invalidate_search_cache(target_id)
            return True

    # ---- Archive ----

    def archive_thread(self, thread_id: str) -> bool:
        thread = self._threads.get(thread_id)
        if thread is None:
            return False
        if thread.state == ThreadState.ARCHIVED:
            return True
        with self._lock:
            thread.state = ThreadState.ARCHIVED
            self._archive_count += 1
            self._invalidate_search_cache(thread_id)
            return True

    # ---- Export ----

    def export_thread(self, thread_id: str, format: str = "json") -> Optional[Dict[str, Any]]:
        thread = self._threads.get(thread_id)
        if thread is None:
            return None
        turns = self._get_thread_turns(thread_id)
        with self._lock:
            export_data: Dict[str, Any] = {
                "thread": thread.to_dict(),
                "turns": [t.to_dict() for t in turns],
                "turn_count": len(turns),
                "total_tokens": sum(t.token_count for t in turns),
                "export_format": format,
                "exported_at": time.time(),
            }
            if format == "compact":
                export_data["turns"] = [
                    {"role": t.role.value, "content": t.content[:200]}
                    for t in turns
                ]
            elif format == "timeline":
                role_groups: Dict[str, List[Dict[str, Any]]] = {}
                for t in turns:
                    role_groups.setdefault(t.role.value, []).append({
                        "content": t.content,
                        "turn_index": t.turn_index,
                        "created_at": t.created_at,
                    })
                export_data["timeline"] = role_groups
            return export_data

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            role_distribution: Dict[str, int] = {}
            state_distribution: Dict[str, int] = {}
            agent_thread_counts: Dict[str, int] = {}
            total_tokens = 0
            total_content_length = 0

            for turn in self._turns.values():
                role_distribution[turn.role.value] = (
                    role_distribution.get(turn.role.value, 0) + 1
                )
                total_tokens += turn.token_count
                total_content_length += len(turn.content)

            for thread in self._threads.values():
                state_distribution[thread.state.value] = (
                    state_distribution.get(thread.state.value, 0) + 1
                )
                agent_thread_counts[thread.agent_id] = (
                    agent_thread_counts.get(thread.agent_id, 0) + 1
                )

            total_threads = len(self._threads)
            total_turns_count = len(self._turns)
            avg_turns_per_thread = (
                round(total_turns_count / max(1, total_threads), 2)
            )
            avg_tokens_per_turn = (
                round(total_tokens / max(1, total_turns_count), 1)
            )
            avg_content_length = (
                round(total_content_length / max(1, total_turns_count), 1)
            )

            return {
                "total_threads": total_threads,
                "total_turns": total_turns_count,
                "thread_count": self._thread_count,
                "turn_count": self._turn_count,
                "archive_count": self._archive_count,
                "merge_count": len(self._merge_events),
                "summaries_generated": self._summaries_generated,
                "avg_turns_per_thread": avg_turns_per_thread,
                "avg_tokens_per_turn": avg_tokens_per_turn,
                "avg_content_length": avg_content_length,
                "role_distribution": role_distribution,
                "state_distribution": state_distribution,
                "agent_threads": agent_thread_counts,
                "index_keywords": len(self._index.keyword_index),
                "indexed_threads": len(self._index.thread_index),
                "indexed_agents": len(self._index.agent_index),
                "search_cache_entries": len(self._search_cache),
            }

    # ---- Reset ----

    def reset(self) -> None:
        with self._lock:
            self._threads.clear()
            self._turns.clear()
            self._index = MemoryIndex()
            self._search_cache.clear()
            self._thread_count = 0
            self._turn_count = 0
            self._archive_count = 0
            self._merge_events.clear()
            self._summaries_generated = 0

    # ---- Thread Query Helpers ----

    def get_thread(self, thread_id: str) -> Optional[ConversationThread]:
        return self._threads.get(thread_id)

    def list_threads(
        self,
        agent_id: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 50,
    ) -> List[ConversationThread]:
        threads = list(self._threads.values())
        if agent_id:
            threads = [t for t in threads if t.agent_id == agent_id]
        if state:
            try:
                filter_state = ThreadState(state.lower())
                threads = [t for t in threads if t.state == filter_state]
            except ValueError:
                pass
        threads.sort(key=lambda t: t.last_activity_at, reverse=True)
        return threads[:limit]

    def get_turn(self, turn_id: str) -> Optional[ConversationTurn]:
        return self._turns.get(turn_id)

    def list_turns(
        self,
        thread_id: str,
        limit: int = 100,
    ) -> List[ConversationTurn]:
        turns = self._get_thread_turns(thread_id)
        return turns[-limit:]

    def pause_thread(self, thread_id: str) -> bool:
        thread = self._threads.get(thread_id)
        if thread is None or thread.state != ThreadState.ACTIVE:
            return False
        with self._lock:
            thread.state = ThreadState.PAUSED
            return True

    def resume_thread(self, thread_id: str) -> bool:
        thread = self._threads.get(thread_id)
        if thread is None or thread.state != ThreadState.PAUSED:
            return False
        with self._lock:
            thread.state = ThreadState.ACTIVE
            thread.last_activity_at = time.time()
            return True

    def update_title(self, thread_id: str, title: str) -> bool:
        thread = self._threads.get(thread_id)
        if thread is None:
            return False
        with self._lock:
            thread.title = title
            return True

    # ---- Internal: Indexing ----

    def _index_thread(self, thread: ConversationThread) -> None:
        if thread.agent_id:
            self._index.agent_index.setdefault(thread.agent_id, []).append(thread.id)
        self._index.thread_index.setdefault(thread.id, [])

    def _index_turn(self, turn: ConversationTurn) -> None:
        tokens = self._tokenize(turn.content)
        for token in tokens:
            if token not in self._index.keyword_index:
                self._index.keyword_index[token] = set()
            self._index.keyword_index[token].add(turn.id)
        self._index.thread_index.setdefault(turn.thread_id, []).append(turn.id)

    def _reindex_thread_turns(
        self, source: ConversationThread, target: ConversationThread
    ) -> None:
        if source.id in self._index.thread_index:
            old_turn_ids = self._index.thread_index.pop(source.id, [])
            self._index.thread_index.setdefault(target.id, []).extend(old_turn_ids)

    # ---- Internal: Token & Similarity ----

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        cleaned = "".join(
            c.lower() if c.isalnum() or c.isspace() else " " for c in text
        )
        tokens = cleaned.split()
        return [t for t in tokens if len(t) >= 2]

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, len(text) // ConversationMemoryEngine._TOKEN_ESTIMATE_CHARS_PER_TOKEN)

    @staticmethod
    def _compute_turn_embedding_sim(content: str) -> float:
        if not content:
            return 0.0
        chars = list(content.lower()[:256])
        seed = sum(ord(c) * (i + 1) for i, c in enumerate(chars))
        val = math.sin(seed * 0.01) * 0.5 + 0.5
        return round(max(0.0, min(1.0, val)), 4)

    @staticmethod
    def _token_overlap(a_tokens: Set[str], b_tokens: Set[str]) -> float:
        if not a_tokens or not b_tokens:
            return 0.0
        return len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))

    # ---- Internal: Thread Helpers ----

    def _get_thread_turns(self, thread_id: str) -> List[ConversationTurn]:
        turn_ids = self._index.thread_index.get(thread_id, [])
        turns = [self._turns[tid] for tid in turn_ids if tid in self._turns]
        turns.sort(key=lambda t: t.turn_index)
        return turns

    def _invalidate_search_cache(self, thread_id: str) -> None:
        keys_to_remove = []
        for key in self._search_cache:
            cached_ids = self._search_cache[key]
            has_thread_turns = any(
                tid in self._turns and self._turns[tid].thread_id == thread_id
                for tid in cached_ids
            )
            if has_thread_turns:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._search_cache[key]

    # ---- Internal: Summarization ----

    def _build_summary(
        self, turns: List[ConversationTurn], strategy: str
    ) -> str:
        if not turns:
            return ""

        parts: List[str] = []
        total_turns = len(turns)
        role_counts: Dict[str, int] = {}
        for turn in turns:
            role_counts[turn.role.value] = role_counts.get(turn.role.value, 0) + 1

        parts.append(
            f"Conversation with {total_turns} turns across "
            f"{len(role_counts)} roles."
        )

        if strategy == "concise":
            for turn in turns:
                preview = turn.content[:120].replace("\n", " ")
                parts.append(f"[{turn.role.value}] {preview}")
            return "\n".join(parts)

        if strategy == "overview":
            role_summary = ", ".join(
                f"{role}: {count}" for role, count in role_counts.items()
            )
            parts.append(f"Role breakdown: {role_summary}.")
            first = turns[0]
            last = turns[-1]
            parts.append(
                f"Opens with: {first.content[:120].replace(chr(10), ' ')}..."
            )
            parts.append(
                f"Closes with: {last.content[:120].replace(chr(10), ' ')}..."
            )
            if len(turns) > 2:
                mid = turns[len(turns) // 2]
                parts.append(
                    f"Midpoint: {mid.content[:120].replace(chr(10), ' ')}..."
                )
            return "\n".join(parts)

        # default "summary" strategy
        for i, turn in enumerate(turns):
            preview = turn.content[:self._SUMMARY_TRUNCATION_LENGTH].replace("\n", " ")
            parts.append(f"[Turn {i + 1}/{total_turns} | {turn.role.value}] {preview}")

        result = "\n\n".join(parts)
        total_tokens = self._estimate_tokens(result)
        if total_tokens > 2000:
            reduced: List[str] = []
            step = max(1, len(turns) // 20)
            for i, turn in enumerate(turns):
                if i % step == 0 or i == len(turns) - 1:
                    preview = turn.content[:150].replace("\n", " ")
                    reduced.append(
                        f"[Turn {i + 1} | {turn.role.value}] {preview}"
                    )
            result = "\n\n".join(reduced)

        return result

    # ---- Internal: Topic Extraction ----

    @staticmethod
    def _extract_topics(
        turns: List[ConversationTurn], max_candidates: int = 10
    ) -> List[str]:
        frequency: Dict[str, int] = {}
        for turn in turns:
            tokens = ConversationMemoryEngine._tokenize(turn.content)
            for token in tokens:
                if len(token) >= ConversationMemoryEngine._TOPIC_EXTRACTION_MIN_TOKENS:
                    frequency[token] = frequency.get(token, 0) + 1
        stopwords = {
            "the", "and", "for", "that", "with", "this", "from", "have",
            "are", "was", "not", "but", "all", "can", "will", "just",
            "like", "what", "when", "where", "which", "how", "they",
            "them", "then", "than", "been", "has", "had", "did", "does",
            "were", "into", "more", "some", "such", "only", "other",
            "also", "about", "over", "after", "very", "your", "its",
        }
        filtered = [(w, c) for w, c in frequency.items() if w not in stopwords]
        filtered.sort(key=lambda x: x[1], reverse=True)
        return [word for word, _ in filtered[:max_candidates]]

    # ---- Internal: Search Scoring ----

    def _score_turn_relevance(
        self,
        turn: ConversationTurn,
        query: str,
        query_tokens: Set[str],
    ) -> float:
        turn_tokens = set(self._tokenize(turn.content))
        if not query_tokens or not turn_tokens:
            return 0.0
        exact_bonus = 1.0 if query.lower() in turn.content.lower() else 0.0
        overlap = self._token_overlap(query_tokens, turn_tokens)
        text_score = overlap * 0.70 + exact_bonus * 0.30
        if text_score == 0.0:
            return 0.0
        recency = 1.0 / (1.0 + (time.time() - turn.created_at) / 86400.0)
        role_weight = 0.05
        if turn.role == TurnRole.SYSTEM:
            role_weight = 0.15
        elif turn.role == TurnRole.USER:
            role_weight = 0.10
        signal = recency * 0.40 + turn.embedding_sim * 0.40 + role_weight * 0.20
        score = text_score * 0.70 + signal * 0.30
        thread = self._threads.get(turn.thread_id)
        if thread is not None and thread.state == ThreadState.ACTIVE:
            score *= 1.05
        return round(min(1.0, score), 4)

    # ---- Internal: Title Generation ----

    @staticmethod
    def _generate_title(agent_id: str) -> str:
        short_id = agent_id[:8] if len(agent_id) >= 8 else agent_id
        return f"Conversation-{short_id}-{int(time.time())}"


def get_conversation_memory() -> ConversationMemoryEngine:
    return ConversationMemoryEngine.get_instance()