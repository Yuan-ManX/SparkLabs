"""
SparkLabs Agent - Memory Consolidator

Cross-session memory consolidation system
L1-L4 memory layers with FTS5 semantic search. Bridges ephemeral
session memory into durable, searchable knowledge fragments that
persist across agent sessions and inform future decision-making.

Architecture:
  MemoryConsolidator (thread-safe singleton)
    |-- MemoryFragment    (atomic knowledge unit with embedding hint)
    |-- ConsolidationResult (post-consolidation statistics)
    |-- FragmentType      (taxonomy of memory fragment kinds)
    |-- ConsolidationStrategy (how fragments are merged/compressed)
    |-- SemanticIndex     (TF-IDF vector space for similarity search)
    |-- RetentionRanker   (importance-weighted fragment prioritization)
    |-- SessionDigester   (cross-session summary generation)

Memory Layers (L1-L4):
  L1 - Working fragments: active session context, high churn
  L2 - Episodic fragments: recent session snapshots, medium retention
  L3 - Semantic fragments: consolidated knowledge, low churn
  L4 - Archival fragments: compressed long-term memory, read-optimized

Consolidation Flow:
  1. New fragments enter L1 (working memory)
  2. Similarity search groups related fragments
  3. Configurable strategy merges/compresses L1 → L2 → L3
  4. Importance-driven retention ranking manages capacity
  5. Session digest generation for cross-session context transfer
"""

from __future__ import annotations

import math
import re
import threading
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class FragmentType(Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    DECISION = "decision"
    PATTERN = "pattern"
    WORKFLOW = "workflow"
    INSIGHT = "insight"
    CONVENTION = "convention"


class ConsolidationStrategy(Enum):
    SUMMARIZE = "summarize"
    MERGE = "merge"
    PRIORITIZE = "prioritize"
    COMPRESS = "compress"
    ARCHIVE = "archive"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class MemoryFragment:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    content: str = ""
    fragment_type: FragmentType = FragmentType.FACT
    source_session: str = ""
    embedding_hint: List[float] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    importance_score: float = 0.5
    access_count: int = 0
    created_at: float = field(default_factory=_time_module.time)
    last_accessed: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "fragment_type": self.fragment_type.value,
            "source_session": self.source_session,
            "embedding_hint": list(self.embedding_hint),
            "keywords": list(self.keywords),
            "importance_score": self.importance_score,
            "access_count": self.access_count,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
        }

    def age_seconds(self) -> float:
        return max(0.0, _time_module.time() - self.created_at)

    def staleness_seconds(self) -> float:
        return max(0.0, _time_module.time() - self.last_accessed)


@dataclass
class ConsolidationResult:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    fragments_count: int = 0
    merged_count: int = 0
    summary: str = ""
    compact_ratio: float = 0.0
    duration_ms: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "fragments_count": self.fragments_count,
            "merged_count": self.merged_count,
            "summary": self.summary,
            "compact_ratio": round(self.compact_ratio, 4),
            "duration_ms": self.duration_ms,
            "created_at": self.created_at,
        }


# ------------------------------------------------------------------
# Internal: TF-IDF Semantic Index
# ------------------------------------------------------------------


class _SemanticIndex:
    """Pure-Python TF-IDF vector index for fragment similarity search.

    Uses a bag-of-words term-frequency model with inverse document
    frequency weighting. Operates in O(N * V) where N is the number
    of indexed fragments and V is the average vocabulary size per
    fragment. No external dependencies required.
    """

    def __init__(self) -> None:
        self._fragments: Dict[str, MemoryFragment] = {}
        self._term_index: Dict[str, Dict[str, float]] = {}
        self._document_frequency: Counter = Counter()
        self._total_documents: int = 0
        self._stop_words: set = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "is", "are",
            "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "could", "should",
            "may", "might", "shall", "can", "this", "that", "these",
            "those", "it", "its", "not", "no", "nor", "so", "if",
            "then", "than", "too", "very", "just", "about", "into",
            "over", "also", "up", "out", "when", "who", "how", "what",
            "which", "where", "why", "all", "each", "every", "both",
            "few", "more", "most", "other", "some", "such", "only",
        }

    def index(self, fragment: MemoryFragment) -> None:
        self._fragments[fragment.id] = fragment
        tokens = self._tokenize(fragment.content)
        if not tokens:
            return
        self._total_documents += 1
        unique_tokens = set(tokens)
        for token in unique_tokens:
            self._document_frequency[token] += 1
        token_counts = Counter(tokens)
        total_terms = len(tokens)
        tf_vector: Dict[str, float] = {}
        for token, count in token_counts.items():
            tf_vector[token] = count / total_terms
        self._term_index[fragment.id] = tf_vector

    def remove(self, fragment_id: str) -> None:
        if fragment_id not in self._fragments:
            return
        tokens = self._tokenize(self._fragments[fragment_id].content)
        unique_tokens = set(tokens)
        for token in unique_tokens:
            if self._document_frequency[token] > 0:
                self._document_frequency[token] -= 1
                if self._document_frequency[token] == 0:
                    del self._document_frequency[token]
        self._total_documents = max(0, self._total_documents - 1)
        self._term_index.pop(fragment_id, None)
        self._fragments.pop(fragment_id, None)

    def search(self, query_text: str, top_k: int = 10, min_score: float = 0.05) -> List[Tuple[MemoryFragment, float]]:
        if not self._fragments:
            return []
        query_tokens = self._tokenize(query_text)
        if not query_tokens:
            return []
        query_vector = self._compute_query_tfidf(query_tokens)
        results: List[Tuple[MemoryFragment, float]] = []
        for fragment_id, fragment in self._fragments.items():
            doc_vector = self._term_index.get(fragment_id, {})
            score = self._cosine_similarity(query_vector, doc_vector)
            if score >= min_score:
                results.append((fragment, score))
        results.sort(key=lambda pair: pair[1], reverse=True)
        return results[:top_k]

    def pairwise_similarity(self, fragment_id_a: str, fragment_id_b: str) -> float:
        vec_a = self._term_index.get(fragment_id_a, {})
        vec_b = self._term_index.get(fragment_id_b, {})
        return self._cosine_similarity(vec_a, vec_b)

    def _tokenize(self, text: str) -> List[str]:
        raw_tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        return [t for t in raw_tokens if len(t) > 1 and t not in self._stop_words]

    def _idf(self, term: str) -> float:
        doc_count = self._document_frequency.get(term, 0)
        return math.log((self._total_documents + 1) / (doc_count + 1)) + 1.0

    def _compute_query_tfidf(self, tokens: List[str]) -> Dict[str, float]:
        token_counts = Counter(tokens)
        total_terms = len(tokens)
        tfidf: Dict[str, float] = {}
        for token, count in token_counts.items():
            tf = count / total_terms
            tfidf[token] = tf * self._idf(token)
        return tfidf

    def _cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        dot_product = sum(vec_a.get(k, 0.0) * vec_b.get(k, 0.0) for k in vec_a)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        similarity = dot_product / (norm_a * norm_b)
        return similarity

    @property
    def document_count(self) -> int:
        return len(self._fragments)


# ------------------------------------------------------------------
# Internal: Retention Ranker
# ------------------------------------------------------------------


class _RetentionRanker:
    """Scores fragments by composite importance for retention decisions.

    Factors in: base importance_score, access frequency, recency of
    last access, fragment type weight, and keyword richness. Produces
    a normalized ranking that drives pruning and consolidation
    priority.
    """

    _type_weights: Dict[FragmentType, float] = {
        FragmentType.FACT: 0.7,
        FragmentType.PREFERENCE: 0.9,
        FragmentType.DECISION: 0.85,
        FragmentType.PATTERN: 0.8,
        FragmentType.WORKFLOW: 0.75,
        FragmentType.INSIGHT: 0.95,
        FragmentType.CONVENTION: 0.8,
    }

    def rank(self, fragments: List[MemoryFragment]) -> List[Tuple[MemoryFragment, float]]:
        if not fragments:
            return []
        scored: List[Tuple[MemoryFragment, float]] = []
        now = _time_module.time()
        for fragment in fragments:
            score = self._compute_retention_score(fragment, now)
            scored.append((fragment, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored

    def _compute_retention_score(self, fragment: MemoryFragment, now: float) -> float:
        base = fragment.importance_score
        access_bonus = min(0.25, fragment.access_count * 0.03)
        recency = max(0.0, now - fragment.last_accessed)
        recency_decay = 1.0 / (1.0 + recency / 86400.0)
        type_weight = self._type_weights.get(fragment.fragment_type, 0.7)
        keyword_bonus = min(0.1, len(fragment.keywords) * 0.02)
        score = (base * 0.4 + type_weight * 0.3 + access_bonus * 0.15 + keyword_bonus * 0.15) * recency_decay
        return min(1.0, max(0.0, score))


# ------------------------------------------------------------------
# Internal: Session Digest Builder
# ------------------------------------------------------------------


class _SessionDigester:
    """Builds human-readable session summaries from fragment clusters."""

    def digest(self, session_id: str, fragments: List[MemoryFragment]) -> str:
        if not fragments:
            return f"Session {session_id}: no fragments recorded."
        type_groups: Dict[FragmentType, List[MemoryFragment]] = defaultdict(list)
        for fragment in fragments:
            type_groups[fragment.fragment_type].append(fragment)
        parts: List[str] = []
        parts.append(f"Session: {session_id}")
        parts.append(f"Total fragments: {len(fragments)}")
        for frag_type, group in sorted(type_groups.items(), key=lambda x: x[0].value):
            parts.append(f"  [{frag_type.value}] {len(group)} fragments")
            top_fragments = sorted(group, key=lambda f: f.importance_score, reverse=True)[:3]
            for fragment in top_fragments:
                snippet = fragment.content[:120].replace("\n", " ")
                parts.append(f"    - {snippet}")
        parts.append(f"---")
        return "\n".join(parts)

    def summarize(
        self, fragments: List[MemoryFragment], max_length: int = 500
    ) -> str:
        if not fragments:
            return ""
        sorted_fragments = sorted(fragments, key=lambda f: f.importance_score, reverse=True)
        combined_parts: List[str] = []
        total_chars = 0
        for fragment in sorted_fragments:
            snippet = fragment.content[:150].strip()
            if total_chars + len(snippet) > max_length:
                remaining = max_length - total_chars
                if remaining > 20:
                    combined_parts.append(snippet[:remaining] + "...")
                break
            combined_parts.append(snippet)
            total_chars += len(snippet)
        return " | ".join(combined_parts)


# ------------------------------------------------------------------
# Thread-Safe Singleton
# ------------------------------------------------------------------


DEFAULT_MAX_WORKING_FRAGMENTS: int = 200
DEFAULT_SIMILARITY_THRESHOLD: float = 0.3
DEFAULT_RETENTION_LIMIT: int = 1000
DEFAULT_MERGE_SIMILARITY: float = 0.6


class MemoryConsolidator:
    """Cross-session memory consolidation system with semantic search.

    Maintains L1-L4 memory layers for durable knowledge retention
    across agent sessions. Supports TF-IDF semantic search over
    fragment content, configurable consolidation strategies, and
    importance-driven retention ranking.

    Thread-safe singleton usable concurrently from multiple sessions.

    Usage:
        consolidator = get_memory_consolidator()
        consolidator.add_fragment(
            content="User prefers dark theme in code editors",
            fragment_type=FragmentType.PREFERENCE,
            source_session="session_abc",
        )
        results = consolidator.semantic_search("dark theme preference")
        consolidator.consolidate(ConsolidationStrategy.MERGE)
    """

    _instance: Optional[MemoryConsolidator] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> MemoryConsolidator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> MemoryConsolidator:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._working: Dict[str, MemoryFragment] = {}
        self._episodic: Dict[str, MemoryFragment] = {}
        self._semantic_store: Dict[str, MemoryFragment] = {}
        self._archival: Dict[str, MemoryFragment] = {}
        self._index: _SemanticIndex = _SemanticIndex()
        self._ranker: _RetentionRanker = _RetentionRanker()
        self._digester: _SessionDigester = _SessionDigester()
        self._consolidation_history: List[ConsolidationResult] = []
        self._total_consolidations: int = 0
        self._max_working: int = DEFAULT_MAX_WORKING_FRAGMENTS
        self._similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
        self._retention_limit: int = DEFAULT_RETENTION_LIMIT
        self._merge_similarity: float = DEFAULT_MERGE_SIMILARITY

    # --- Public API ---

    def add_fragment(
        self,
        content: str,
        fragment_type: str = "fact",
        source_session: str = "",
        embedding_hint: Optional[List[float]] = None,
        keywords: Optional[List[str]] = None,
        importance_score: float = 0.5,
    ) -> MemoryFragment:
        frag_type = FragmentType(fragment_type)
        fragment = MemoryFragment(
            content=content,
            fragment_type=frag_type,
            source_session=source_session,
            embedding_hint=embedding_hint if embedding_hint is not None else [],
            keywords=keywords if keywords is not None else self._extract_keywords(content),
            importance_score=max(0.0, min(1.0, importance_score)),
        )
        with self._lock:
            self._working[fragment.id] = fragment
            self._index.index(fragment)
            self._enforce_working_limit()
        return fragment

    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.05,
        fragment_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            results = self._index.search(query, top_k=top_k, min_score=min_score)
        filtered: List[Tuple[MemoryFragment, float]] = []
        for fragment, score in results:
            if fragment_type is not None and fragment.fragment_type.value != fragment_type:
                continue
            fragment.last_accessed = _time_module.time()
            fragment.access_count += 1
            filtered.append((fragment, score))
        return [
            {**fragment.to_dict(), "similarity_score": round(score, 4)}
            for fragment, score in filtered
        ]

    def consolidate(
        self,
        strategy: str = "merge",
        source_session: Optional[str] = None,
    ) -> ConsolidationResult:
        start_time = _time_module.time()
        strat = ConsolidationStrategy(strategy)
        with self._lock:
            if source_session is not None:
                candidates = {
                    fid: frag
                    for fid, frag in self._working.items()
                    if frag.source_session == source_session
                }
            else:
                candidates = dict(self._working)
            before_count = len(candidates)
            if strat == ConsolidationStrategy.MERGE:
                merged = self._execute_merge(candidates)
            elif strat == ConsolidationStrategy.SUMMARIZE:
                merged = self._execute_summarize(candidates)
            elif strat == ConsolidationStrategy.PRIORITIZE:
                merged = self._execute_prioritize(candidates)
            elif strat == ConsolidationStrategy.COMPRESS:
                merged = self._execute_compress(candidates)
            elif strat == ConsolidationStrategy.ARCHIVE:
                merged = self._execute_archive(candidates)
            else:
                merged = self._execute_merge(candidates)
            for fragment_id in candidates:
                self._working.pop(fragment_id, None)
            summary = self._digester.summarize(list(self._semantic_store.values())[-10:])
            duration_ms = (_time_module.time() - start_time) * 1000
            after_count = len(self._working)
            compact_ratio = after_count / max(before_count, 1)
            result = ConsolidationResult(
                fragments_count=before_count,
                merged_count=merged,
                summary=summary,
                compact_ratio=compact_ratio,
                duration_ms=round(duration_ms, 2),
            )
            self._consolidation_history.append(result)
            self._total_consolidations += 1
            if len(self._consolidation_history) > 100:
                self._consolidation_history = self._consolidation_history[-100:]
            self._enforce_retention_limit()
        return result

    def generate_context(
        self,
        session_id: str = "",
        max_fragments: int = 15,
        include_archival: bool = False,
    ) -> Dict[str, Any]:
        with self._lock:
            relevant: List[MemoryFragment] = []
            for store in [self._working, self._episodic, self._semantic_store]:
                for fragment in store.values():
                    if not session_id or fragment.source_session == session_id:
                        relevant.append(fragment)
                        fragment.last_accessed = _time_module.time()
                        fragment.access_count += 1
            if include_archival:
                for fragment in self._archival.values():
                    if not session_id or fragment.source_session == session_id:
                        relevant.append(fragment)
            ranked = self._ranker.rank(relevant)
            top_fragments = [fragment for fragment, _ in ranked[:max_fragments]]
            context_text = self._digester.summarize(top_fragments, max_length=2000)
            return {
                "session_id": session_id,
                "fragments_included": len(top_fragments),
                "total_candidates": len(relevant),
                "context": context_text,
                "fragments": [f.to_dict() for f in top_fragments],
            }

    def summarize_sessions(self, session_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        with self._lock:
            all_fragments = (
                list(self._working.values())
                + list(self._episodic.values())
                + list(self._semantic_store.values())
                + list(self._archival.values())
            )
        sessions: Dict[str, List[MemoryFragment]] = defaultdict(list)
        for fragment in all_fragments:
            if session_ids is None or fragment.source_session in session_ids:
                sessions[fragment.source_session].append(fragment)
        results: List[Dict[str, Any]] = []
        for sid, fragments in sorted(sessions.items()):
            digest_text = self._digester.digest(sid, fragments)
            type_counts: Dict[str, int] = {}
            for fragment in fragments:
                type_counts[fragment.fragment_type.value] = (
                    type_counts.get(fragment.fragment_type.value, 0) + 1
                )
            avg_importance = 0.0
            if fragments:
                avg_importance = sum(f.importance_score for f in fragments) / len(fragments)
            results.append({
                "session_id": sid,
                "fragment_count": len(fragments),
                "type_distribution": type_counts,
                "average_importance": round(avg_importance, 4),
                "digest": digest_text,
            })
        return results

    def prioritize_retention(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        effective_limit = limit or self._retention_limit
        with self._lock:
            all_fragments = (
                list(self._working.values())
                + list(self._episodic.values())
                + list(self._semantic_store.values())
                + list(self._archival.values())
            )
        ranked = self._ranker.rank(all_fragments)
        retained = ranked[:effective_limit]
        pruned = ranked[effective_limit:]
        return [
            {
                "retained": [fragment.to_dict() for fragment, score in retained],
                "retained_scores": [round(score, 4) for _, score in retained],
                "pruned_count": len(pruned),
                "total_ranked": len(ranked),
                "retention_limit": effective_limit,
            }
        ]

    def get_memory_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_fragments = (
                len(self._working)
                + len(self._episodic)
                + len(self._semantic_store)
                + len(self._archival)
            )
            type_distribution: Dict[str, int] = {}
            for store in [self._working, self._episodic, self._semantic_store, self._archival]:
                for fragment in store.values():
                    type_distribution[fragment.fragment_type.value] = (
                        type_distribution.get(fragment.fragment_type.value, 0) + 1
                    )
            avg_importance_working = self._avg_importance(self._working)
            avg_importance_episodic = self._avg_importance(self._episodic)
            avg_importance_semantic = self._avg_importance(self._semantic_store)
            avg_importance_archival = self._avg_importance(self._archival)
            recent_consolidations = [
                r.to_dict() for r in self._consolidation_history[-5:]
            ]
            return {
                "total_fragments": total_fragments,
                "working_count": len(self._working),
                "episodic_count": len(self._episodic),
                "semantic_count": len(self._semantic_store),
                "archival_count": len(self._archival),
                "indexed_documents": self._index.document_count,
                "type_distribution": type_distribution,
                "avg_importance_working": round(avg_importance_working, 4),
                "avg_importance_episodic": round(avg_importance_episodic, 4),
                "avg_importance_semantic": round(avg_importance_semantic, 4),
                "avg_importance_archival": round(avg_importance_archival, 4),
                "total_consolidations": self._total_consolidations,
                "retention_limit": self._retention_limit,
                "similarity_threshold": self._similarity_threshold,
                "max_working": self._max_working,
                "merge_similarity": self._merge_similarity,
                "recent_consolidations": recent_consolidations,
            }

    # --- Consolidation Strategy Implementations ---

    def _execute_merge(self, candidates: Dict[str, MemoryFragment]) -> int:
        merged = 0
        fragment_list = list(candidates.items())
        grouped: Dict[str, List[str]] = defaultdict(list)
        processed: set = set()
        for i, (fid_a, frag_a) in enumerate(fragment_list):
            if fid_a in processed:
                continue
            for j, (fid_b, frag_b) in enumerate(fragment_list):
                if j <= i or fid_b in processed:
                    continue
                similarity = self._index.pairwise_similarity(fid_a, fid_b)
                if similarity >= self._merge_similarity:
                    grouped[fid_a].append(fid_b)
                    processed.add(fid_b)
            if grouped.get(fid_a):
                processed.add(fid_a)
        for primary_id, secondary_ids in grouped.items():
            primary = candidates.get(primary_id)
            if primary is None:
                continue
            secondaries = [candidates[sid] for sid in secondary_ids if sid in candidates]
            if not secondaries:
                continue
            merged_content = self._merge_fragment_content(primary, secondaries)
            merged_keywords = list(set(primary.keywords))
            for sec in secondaries:
                merged_keywords.extend(sec.keywords)
            merged_keywords = list(set(merged_keywords))
            merged_importance = max(
                primary.importance_score,
                max((s.importance_score for s in secondaries), default=primary.importance_score),
            )
            merged_fragment = MemoryFragment(
                content=merged_content,
                fragment_type=primary.fragment_type,
                source_session=primary.source_session,
                keywords=merged_keywords[:20],
                importance_score=merged_importance,
            )
            self._semantic_store[merged_fragment.id] = merged_fragment
            self._index.index(merged_fragment)
            for sid in secondary_ids:
                self._index.remove(sid)
            self._index.remove(primary_id)
            self._index.index(merged_fragment)
            merged += len(secondary_ids)
        return merged

    def _execute_summarize(self, candidates: Dict[str, MemoryFragment]) -> int:
        if not candidates:
            return 0
        fragments = sorted(
            candidates.values(), key=lambda f: f.importance_score, reverse=True
        )
        group_size = max(1, len(fragments) // 4)
        summarized = 0
        for i in range(0, len(fragments), group_size):
            group = fragments[i : i + group_size]
            if len(group) <= 1:
                for fragment in group:
                    self._semantic_store[fragment.id] = fragment
                continue
            summary_content = self._digester.summarize(group, max_length=300)
            merged_fragment = MemoryFragment(
                content=summary_content,
                fragment_type=FragmentType.INSIGHT,
                source_session=group[0].source_session,
                keywords=self._extract_keywords(summary_content),
                importance_score=sum(f.importance_score for f in group) / len(group),
            )
            self._semantic_store[merged_fragment.id] = merged_fragment
            self._index.index(merged_fragment)
            summarized += len(group) - 1
        return summarized

    def _execute_prioritize(self, candidates: Dict[str, MemoryFragment]) -> int:
        ranked = self._ranker.rank(list(candidates.values()))
        retained_ids = {fragment.id for fragment, score in ranked[:self._retention_limit]}
        moved = 0
        for fragment_id, fragment in candidates.items():
            if fragment_id in retained_ids:
                self._episodic[fragment_id] = fragment
            else:
                self._semantic_store[fragment_id] = fragment
                moved += 1
        return moved

    def _execute_compress(self, candidates: Dict[str, MemoryFragment]) -> int:
        if not candidates:
            return 0
        fragments = list(candidates.values())
        session_groups: Dict[str, List[MemoryFragment]] = defaultdict(list)
        for frag in fragments:
            session_groups[frag.source_session].append(frag)
        compressed = 0
        for session_id, group in session_groups.items():
            if len(group) <= 3:
                for fragment in group:
                    self._episodic[fragment.id] = fragment
                continue
            sorted_group = sorted(group, key=lambda f: f.importance_score, reverse=True)
            top = sorted_group[:2]
            rest = sorted_group[2:]
            for fragment in top:
                self._episodic[fragment.id] = fragment
            if rest:
                compressed_content = self._digester.summarize(rest, max_length=400)
                compressed_fragment = MemoryFragment(
                    content=compressed_content,
                    fragment_type=FragmentType.INSIGHT,
                    source_session=session_id,
                    keywords=self._extract_keywords(compressed_content),
                    importance_score=sum(f.importance_score for f in rest) / len(rest),
                )
                self._semantic_store[compressed_fragment.id] = compressed_fragment
                self._index.index(compressed_fragment)
                compressed += len(rest)
        return compressed

    def _execute_archive(self, candidates: Dict[str, MemoryFragment]) -> int:
        archived = 0
        for fragment_id, fragment in candidates.items():
            if fragment.importance_score >= 0.6:
                self._semantic_store[fragment_id] = fragment
            else:
                self._archival[fragment_id] = fragment
                archived += 1
        return archived

    # --- Helpers ---

    def _enforce_working_limit(self) -> None:
        while len(self._working) > self._max_working:
            ranked = self._ranker.rank(list(self._working.values()))
            if not ranked:
                break
            lowest_fragment, _ = ranked[-1]
            self._working.pop(lowest_fragment.id, None)

    def _enforce_retention_limit(self) -> None:
        all_fragments = (
            list(self._working.values())
            + list(self._episodic.values())
            + list(self._semantic_store.values())
            + list(self._archival.values())
        )
        if len(all_fragments) <= self._retention_limit:
            return
        ranked = self._ranker.rank(all_fragments)
        retained_ids = {
            fragment.id for fragment, _ in ranked[:self._retention_limit]
        }
        for store in [self._working, self._episodic, self._semantic_store, self._archival]:
            for fragment_id in list(store.keys()):
                if fragment_id not in retained_ids:
                    self._index.remove(fragment_id)
                    store.pop(fragment_id, None)

    def _extract_keywords(self, content: str) -> List[str]:
        tokens = re.findall(r"[a-zA-Z0-9_]{3,}", content.lower())
        stop_words = {
            "the", "and", "for", "that", "this", "with", "from",
            "are", "was", "has", "not", "but", "have", "been",
            "will", "can", "all", "its", "when", "into", "over",
        }
        filtered = [t for t in tokens if t not in stop_words]
        counter = Counter(filtered)
        return [word for word, _ in counter.most_common(10)]

    def _merge_fragment_content(
        self, primary: MemoryFragment, secondaries: List[MemoryFragment]
    ) -> str:
        parts = [primary.content]
        for secondary in secondaries[:5]:
            if secondary.content not in parts:
                parts.append(secondary.content)
        return " | ".join(parts)

    @staticmethod
    def _avg_importance(store: Dict[str, MemoryFragment]) -> float:
        if not store:
            return 0.0
        return sum(f.importance_score for f in store.values()) / len(store)

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive MemoryConsolidator subsystem statistics."""
        all_fragments = {
            **{f"working_{k}": v for k, v in self._working.items()},
            **{f"episodic_{k}": v for k, v in self._episodic.items()},
            **{f"semantic_{k}": v for k, v in self._semantic_store.items()},
            **{f"archival_{k}": v for k, v in self._archival.items()},
        }
        return {
            "total_fragments": len(all_fragments),
            "working_count": len(self._working),
            "episodic_count": len(self._episodic),
            "semantic_count": len(self._semantic_store),
            "archival_count": len(self._archival),
            "total_consolidations": self._total_consolidations,
            "consolidation_history_size": len(self._consolidation_history),
        }


def get_memory_consolidator() -> MemoryConsolidator:
    return MemoryConsolidator.get_instance()