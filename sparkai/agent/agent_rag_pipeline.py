"""
SparkLabs Agent - RAG (Retrieval Augmented Generation) Pipeline

A retrieval augmented generation system for the AI-native game engine.
Ingests game development knowledge documents, chunks content using
configurable strategies, builds keyword and vector indexes, and
retrieves context for augmenting LLM prompts at generation time.

Architecture:
  RAGPipeline
    |-- Document (ingested game dev knowledge)
    |-- DocumentChunk (sub-document retrieval unit)
    |-- SearchResult (scored retrieval hit)
    |-- InvertedIndex (keyword-based BM25-like search)
    |-- EmbeddingStore (cosine-similarity vector search)
    |-- HybridRanker (combined keyword + vector scoring)
"""

import math
import re
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ChunkStrategy(Enum):
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"
    PARAGRAPH = "paragraph"


class SearchMode(Enum):
    KEYWORD = "keyword"
    VECTOR = "vector"
    HYBRID = "hybrid"


class RAGDomain(Enum):
    GAME_DESIGN = "game_design"
    CODE_PATTERNS = "code_patterns"
    ASSET_GUIDELINES = "asset_guidelines"
    LEVEL_DESIGN = "level_design"
    NARRATIVE = "narrative"
    MECHANICS = "mechanics"
    PERFORMANCE = "performance"
    UI_UX = "ui_ux"
    AUDIO = "audio"
    PUBLISHING = "publishing"


@dataclass
class DocumentChunk:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    document_id: str = ""
    content: str = ""
    embedding: List[float] = field(default_factory=list)
    chunk_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "content_preview": self.content[:200],
            "embedding_dim": len(self.embedding),
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
            "token_count": self.token_count,
            "created_at": self.created_at,
        }


@dataclass
class Document:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    source: str = ""
    content: str = ""
    chunks: List[DocumentChunk] = field(default_factory=list)
    domain: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "content_preview": self.content[:300],
            "chunk_count": len(self.chunks),
            "domain": self.domain,
            "tags": self.tags,
            "created_at": self.created_at,
        }


@dataclass
class SearchResult:
    chunk_id: str = ""
    document_id: str = ""
    score: float = 0.0
    content_preview: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "score": round(self.score, 4),
            "content_preview": self.content_preview[:200],
            "metadata": self.metadata,
        }


class RAGPipeline:
    """
    Retrieval Augmented Generation pipeline for game development knowledge.

    Ingests documents, chunks them with configurable strategies, indexes
    content for keyword and vector search, and produces context strings
    for augmenting LLM prompts.
    """

    _instance: Optional["RAGPipeline"] = None
    _lock: threading.RLock = threading.RLock()

    FIXED_CHUNK_SIZE = 512
    EMBEDDING_DIM = 384
    MIN_CHUNK_TOKENS = 10

    def __init__(self) -> None:
        self._documents: Dict[str, Document] = {}
        self._chunk_index: Dict[str, Dict[str, Any]] = {}
        self._inverted_index: Dict[str, Set[str]] = defaultdict(set)
        self._document_count: int = 0
        self._chunk_count: int = 0
        self._document_frequencies: Dict[str, Dict[str, int]] = {}
        self._total_token_count: int = 0
        self._initialize_knowledge_base()

    @classmethod
    def get_instance(cls) -> "RAGPipeline":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _generate_embedding(self, text: str) -> List[float]:
        normalized = text.lower().strip()[:1024]
        chars = list(normalized)
        seed = sum(ord(c) * (i + 1) for i, c in enumerate(chars))
        dim = self.EMBEDDING_DIM
        embedding: List[float] = []
        for i in range(dim):
            val = math.sin(seed * 0.01 + i * 0.1) * 0.5 + 0.5
            val += math.cos(seed * 0.007 + i * 0.13) * 0.3
            val += math.sin(seed * 0.003 + i * 0.17) * 0.2
            val = max(-1.0, min(1.0, val))
            embedding.append(round(val, 6))
        return embedding

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        min_len = min(len(a), len(b))
        dot = sum(a[i] * b[i] for i in range(min_len))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0
        return dot / (mag_a * mag_b)

    def _tokenize(self, text: str) -> List[str]:
        lowered = text.lower()
        tokens = re.findall(r"[a-z0-9]{2,}", lowered)
        return tokens

    def _compute_tf(self, term: str, tokens: List[str]) -> float:
        if not tokens:
            return 0.0
        count = tokens.count(term)
        return count / len(tokens)

    def _compute_idf(self, term: str) -> float:
        df = len(self._inverted_index.get(term, set()))
        if df == 0:
            return 0.0
        total_docs = max(1, len(self._documents))
        return math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)

    def chunk_content(self, content: str, strategy: ChunkStrategy) -> List[str]:
        if not content.strip():
            return []

        if strategy == ChunkStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(content)
        elif strategy == ChunkStrategy.PARAGRAPH:
            return self._chunk_paragraph(content)
        elif strategy == ChunkStrategy.SEMANTIC:
            return self._chunk_semantic(content)
        elif strategy == ChunkStrategy.RECURSIVE:
            return self._chunk_recursive(content)
        else:
            return self._chunk_fixed_size(content)

    def _chunk_fixed_size(self, content: str) -> List[str]:
        words = content.split()
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for word in words:
            word_len = len(word) + 1
            if current_len + word_len > self.FIXED_CHUNK_SIZE and current:
                chunks.append(" ".join(current))
                current = []
                current_len = 0
            current.append(word)
            current_len += word_len

        if current:
            chunks.append(" ".join(current))
        return chunks

    def _chunk_paragraph(self, content: str) -> List[str]:
        paragraphs = re.split(r"\n\s*\n", content)
        chunks: List[str] = []
        for para in paragraphs:
            stripped = para.strip()
            if stripped and self._estimate_tokens(stripped) >= self.MIN_CHUNK_TOKENS:
                chunks.append(stripped)
        if not chunks:
            return self._chunk_fixed_size(content)
        return chunks

    def _chunk_semantic(self, content: str) -> List[str]:
        sections = re.split(r"\n\s*\n", content)
        chunks: List[str] = []
        buffer: List[str] = []
        buffer_tokens = 0

        for section in sections:
            stripped = section.strip()
            if not stripped:
                continue
            section_tokens = self._estimate_tokens(stripped)

            if buffer_tokens + section_tokens > self.FIXED_CHUNK_SIZE * 2 and buffer:
                chunks.append("\n\n".join(buffer))
                buffer = []
                buffer_tokens = 0

            buffer.append(stripped)
            buffer_tokens += section_tokens

        if buffer:
            chunks.append("\n\n".join(buffer))

        if not chunks:
            return self._chunk_fixed_size(content)
        return chunks

    def _chunk_recursive(self, content: str) -> List[str]:
        header_pattern = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
        headers = list(header_pattern.finditer(content))

        if not headers:
            return self._chunk_semantic(content)

        chunks: List[str] = []
        for i, match in enumerate(headers):
            start = match.start()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
            section = content[start:end].strip()
            if section and self._estimate_tokens(section) >= self.MIN_CHUNK_TOKENS:
                chunks.append(section)

        large_chunks: List[str] = []
        for chunk in chunks:
            if self._estimate_tokens(chunk) > self.FIXED_CHUNK_SIZE * 2:
                sub_chunks = self._chunk_paragraph(chunk)
                large_chunks.extend(sub_chunks)
            else:
                large_chunks.append(chunk)

        if not large_chunks:
            return self._chunk_fixed_size(content)
        return large_chunks

    def ingest_document(
        self,
        title: str,
        source: str,
        content: str,
        domain: str,
        tags: List[str],
        chunk_strategy: ChunkStrategy = ChunkStrategy.SEMANTIC,
    ) -> str:
        with self._lock:
            doc = Document(
                title=title,
                source=source,
                content=content,
                domain=domain,
                tags=tags,
            )

            chunk_texts = self.chunk_content(content, chunk_strategy)
            doc.chunks = []
            for idx, chunk_text in enumerate(chunk_texts):
                chunk = DocumentChunk(
                    document_id=doc.id,
                    content=chunk_text,
                    embedding=self._generate_embedding(chunk_text),
                    chunk_index=idx,
                    metadata={
                        "title": title,
                        "domain": domain,
                        "tags": tags,
                        "source": source,
                    },
                    token_count=self._estimate_tokens(chunk_text),
                )
                doc.chunks.append(chunk)
                self._chunk_index[chunk.id] = {
                    "document_id": doc.id,
                    "domain": domain,
                    "chunk_index": idx,
                    "token_count": chunk.token_count,
                }
                self._chunk_count += 1

            self._documents[doc.id] = doc
            self._document_count += 1

            tokens = self._tokenize(content)
            self._document_frequencies[doc.id] = {}
            for token in set(tokens):
                self._document_frequencies[doc.id][token] = tokens.count(token)

            for chunk in doc.chunks:
                chunk_tokens = self._tokenize(chunk.content)
                for token in set(chunk_tokens):
                    self._inverted_index[token].add(chunk.id)

            self._total_token_count += sum(
                ch.token_count for ch in doc.chunks
            )
            return doc.id

    def build_inverted_index(self) -> None:
        with self._lock:
            self._inverted_index.clear()
            self._document_frequencies.clear()

            for doc in self._documents.values():
                tokens = self._tokenize(doc.content)
                self._document_frequencies[doc.id] = {}
                for token in set(tokens):
                    self._document_frequencies[doc.id][token] = tokens.count(token)

            for doc in self._documents.values():
                for chunk in doc.chunks:
                    chunk_tokens = self._tokenize(chunk.content)
                    for token in set(chunk_tokens):
                        self._inverted_index[token].add(chunk.id)

    def keyword_search(
        self,
        query: str,
        domain_filter: Optional[str] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        chunk_scores: Dict[str, float] = defaultdict(float)

        for token in query_tokens:
            matching_chunks = self._inverted_index.get(token, set())
            idf = self._compute_idf(token)

            for chunk_id in matching_chunks:
                chunk_info = self._chunk_index.get(chunk_id)
                if chunk_info is None:
                    continue
                if domain_filter and chunk_info.get("domain") != domain_filter:
                    continue

                chunk_content = ""
                doc = self._documents.get(chunk_info.get("document_id", ""))
                if doc:
                    for ch in doc.chunks:
                        if ch.id == chunk_id:
                            chunk_content = ch.content
                            break

                chunk_token_list = self._tokenize(chunk_content)
                tf = self._compute_tf(token, chunk_token_list)
                chunk_scores[chunk_id] += tf * idf

        avg_dl = max(1.0, self._total_token_count / max(1, self._chunk_count))
        k1 = 1.5
        b = 0.75

        for chunk_id in list(chunk_scores.keys()):
            chunk_info = self._chunk_index.get(chunk_id)
            if chunk_info is None:
                del chunk_scores[chunk_id]
                continue
            dl = chunk_info.get("token_count", 1)
            norm = 1.0 - b + b * (dl / avg_dl)
            chunk_scores[chunk_id] = chunk_scores[chunk_id] / norm * (k1 + 1.0)

        sorted_chunks = sorted(chunk_scores.items(), key=lambda x: -x[1])
        results: List[SearchResult] = []
        for chunk_id, score in sorted_chunks[:top_k]:
            chunk_info = self._chunk_index.get(chunk_id, {})
            doc_id = chunk_info.get("document_id", "")
            doc = self._documents.get(doc_id)
            content_preview = ""
            if doc:
                for ch in doc.chunks:
                    if ch.id == chunk_id:
                        content_preview = ch.content[:200]
                        break

            results.append(SearchResult(
                chunk_id=chunk_id,
                document_id=doc_id,
                score=round(score, 4),
                content_preview=content_preview,
                metadata={
                    "domain": chunk_info.get("domain", ""),
                    "chunk_index": chunk_info.get("chunk_index", 0),
                    "search_mode": SearchMode.KEYWORD.value,
                },
            ))

        return results

    def semantic_search(
        self,
        query: str,
        domain_filter: Optional[str] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        query_embedding = self._generate_embedding(query)
        scored: List[Tuple[str, float]] = []

        for chunk_id, chunk_info in self._chunk_index.items():
            if domain_filter and chunk_info.get("domain") != domain_filter:
                continue

            doc = self._documents.get(chunk_info.get("document_id", ""))
            if doc is None:
                continue

            chunk_emb = None
            for ch in doc.chunks:
                if ch.id == chunk_id:
                    chunk_emb = ch.embedding
                    break

            if chunk_emb is None:
                continue

            sim = self._cosine_similarity(query_embedding, chunk_emb)
            if sim > 0.0:
                scored.append((chunk_id, sim))

        if not scored:
            return self.keyword_search(query, domain_filter, top_k)

        scored.sort(key=lambda x: -x[1])
        results: List[SearchResult] = []
        for chunk_id, score in scored[:top_k]:
            chunk_info = self._chunk_index.get(chunk_id, {})
            doc_id = chunk_info.get("document_id", "")
            doc = self._documents.get(doc_id)
            content_preview = ""
            if doc:
                for ch in doc.chunks:
                    if ch.id == chunk_id:
                        content_preview = ch.content[:200]
                        break

            results.append(SearchResult(
                chunk_id=chunk_id,
                document_id=doc_id,
                score=round(score, 4),
                content_preview=content_preview,
                metadata={
                    "domain": chunk_info.get("domain", ""),
                    "chunk_index": chunk_info.get("chunk_index", 0),
                    "search_mode": SearchMode.VECTOR.value,
                },
            ))

        return results

    def hybrid_search(
        self,
        query: str,
        domain_filter: Optional[str] = None,
        top_k: int = 10,
        keyword_weight: float = 0.3,
    ) -> List[SearchResult]:
        keyword_results = self.keyword_search(query, domain_filter, top_k * 2)
        semantic_results = self.semantic_search(query, domain_filter, top_k * 2)

        keyword_scores: Dict[str, float] = {}
        for r in keyword_results:
            keyword_scores[r.chunk_id] = r.score

        semantic_scores: Dict[str, float] = {}
        for r in semantic_results:
            semantic_scores[r.chunk_id] = r.score

        max_kw = max(keyword_scores.values()) if keyword_scores else 1.0
        max_sem = max(semantic_scores.values()) if semantic_scores else 1.0

        combined: Dict[str, float] = {}
        all_chunk_ids = set(keyword_scores.keys()) | set(semantic_scores.keys())

        for chunk_id in all_chunk_ids:
            kw_norm = keyword_scores.get(chunk_id, 0.0) / max(0.001, max_kw)
            sem_norm = semantic_scores.get(chunk_id, 0.0) / max(0.001, max_sem)
            combined[chunk_id] = keyword_weight * kw_norm + (1.0 - keyword_weight) * sem_norm

        sorted_chunks = sorted(combined.items(), key=lambda x: -x[1])
        results: List[SearchResult] = []
        for chunk_id, score in sorted_chunks[:top_k]:
            chunk_info = self._chunk_index.get(chunk_id, {})
            doc_id = chunk_info.get("document_id", "")
            doc = self._documents.get(doc_id)
            content_preview = ""
            if doc:
                for ch in doc.chunks:
                    if ch.id == chunk_id:
                        content_preview = ch.content[:200]
                        break

            results.append(SearchResult(
                chunk_id=chunk_id,
                document_id=doc_id,
                score=round(score, 4),
                content_preview=content_preview,
                metadata={
                    "domain": chunk_info.get("domain", ""),
                    "chunk_index": chunk_info.get("chunk_index", 0),
                    "search_mode": SearchMode.HYBRID.value,
                    "keyword_weight": keyword_weight,
                },
            ))

        return results

    def generate_context(
        self,
        query: str,
        domain_filter: Optional[str] = None,
        max_tokens: int = 2048,
        top_k: int = 5,
    ) -> str:
        search_results = self.hybrid_search(query, domain_filter, top_k)

        seen_chunks: Set[str] = set()
        context_parts: List[str] = []
        token_budget = max_tokens

        for result in search_results:
            if token_budget <= 0:
                break
            if result.chunk_id in seen_chunks:
                continue
            seen_chunks.add(result.chunk_id)

            doc = self._documents.get(result.document_id)
            if doc is None:
                continue

            chunk_content = ""
            for ch in doc.chunks:
                if ch.id == result.chunk_id:
                    chunk_content = ch.content
                    break

            if not chunk_content:
                continue

            chunk_tokens = self._estimate_tokens(chunk_content)
            if chunk_tokens <= token_budget:
                header = f"[{doc.title}] (relevance: {result.score:.3f})"
                context_parts.append(f"{header}\n{chunk_content}")
                token_budget -= chunk_tokens
            else:
                truncated = chunk_content[:token_budget * 4]
                header = f"[{doc.title}] (relevance: {result.score:.3f}, truncated)"
                context_parts.append(f"{header}\n{truncated}")
                token_budget = 0

        if not context_parts:
            return ""

        return "\n\n---\n\n".join(context_parts)

    def augment_prompt(
        self,
        base_prompt: str,
        query: str,
        domain_filter: Optional[str] = None,
        max_context_tokens: int = 2048,
    ) -> str:
        context = self.generate_context(query, domain_filter, max_context_tokens)

        if not context:
            return base_prompt

        augmented = (
            "You are a game development assistant with access to the following "
            "retrieved knowledge. Use this context to inform your response.\n\n"
            "=== RETRIEVED CONTEXT ===\n"
            f"{context}\n"
            "=== END OF CONTEXT ===\n\n"
            "=== USER PROMPT ===\n"
            f"{base_prompt}\n"
            "=== END OF PROMPT ===\n\n"
            "Provide your response based on the context above. If the context "
            "does not contain relevant information, answer from your own knowledge "
            "but note that limitation."
        )
        return augmented

    def remove_document(self, doc_id: str) -> bool:
        with self._lock:
            doc = self._documents.get(doc_id)
            if doc is None:
                return False

            for chunk in doc.chunks:
                chunk_tokens = self._tokenize(chunk.content)
                for token in set(chunk_tokens):
                    index_entry = self._inverted_index.get(token)
                    if index_entry is not None:
                        index_entry.discard(chunk.id)
                        if not index_entry:
                            del self._inverted_index[token]

                if chunk.id in self._chunk_index:
                    del self._chunk_index[chunk.id]
                    self._chunk_count -= 1

            if doc_id in self._document_frequencies:
                del self._document_frequencies[doc_id]

            del self._documents[doc_id]
            self._document_count -= 1
            return True

    def get_documents_by_domain(self, domain: str) -> List[Document]:
        return [
            doc for doc in self._documents.values()
            if doc.domain == domain
        ]

    def get_stats(self) -> Dict[str, Any]:
        domain_breakdown: Dict[str, int] = defaultdict(int)
        for doc in self._documents.values():
            domain_breakdown[doc.domain] += 1

        return {
            "document_count": self._document_count,
            "chunk_count": self._chunk_count,
            "index_size": len(self._inverted_index),
            "total_tokens": self._total_token_count,
            "domain_breakdown": dict(domain_breakdown),
        }

    def _initialize_knowledge_base(self) -> None:
        seed_entries = [
            {
                "title": "Entity-Component-System Architecture",
                "source": "sparklabs_core",
                "content": (
                    "The Entity-Component-System (ECS) pattern is fundamental to modern "
                    "game engine architecture. Entities are simple unique identifiers with "
                    "no behavior of their own. Components are plain data containers attached "
                    "to entities, representing attributes like position, velocity, health, "
                    "or renderable mesh. Systems contain the logic that operates on entities "
                    "with specific component sets.\n\n"
                    "Benefits of ECS include cache-friendly memory layout through "
                    "contiguous component arrays, automatic parallelization when systems "
                    "operate on disjoint component sets, and runtime composition of entity "
                    "behavior without deep inheritance hierarchies.\n\n"
                    "Common pitfalls: over-fragmenting components leads to system bloat; "
                    "under-fragmenting creates god-components that defeat the purpose. "
                    "Aim for components that represent a single concern.\n\n"
                    "When to use: any game with more than a handful of entity types, "
                    "especially when entity behavior changes dynamically at runtime. "
                    "For simple games, a basic inheritance hierarchy may suffice."
                ),
                "domain": RAGDomain.GAME_DESIGN.value,
                "tags": ["ecs", "architecture", "entities", "components", "systems"],
            },
            {
                "title": "Game Loop and Delta Time Patterns",
                "source": "sparklabs_core",
                "content": (
                    "The game loop is the heartbeat of any real-time game. It follows "
                    "a three-phase pattern: process input, update game state, render "
                    "output. For frame-rate independence, always multiply movement and "
                    "physics calculations by delta time, the elapsed seconds since the "
                    "previous frame.\n\n"
                    "Fixed timestep loops decouple the update rate from the render rate. "
                    "Accumulate delta time and step the simulation at fixed intervals "
                    "(commonly 60 Hz). This ensures deterministic physics simulation "
                    "regardless of frame rate, critical for networked games and replays.\n\n"
                    "Variable timestep loops are simpler to implement but can cause "
                    "physics instability at very low or very high frame rates. Use "
                    "interpolation for smooth rendering when the simulation rate differs "
                    "from the display rate.\n\n"
                    "Anti-pattern: tying game speed to frame rate without delta time, "
                    "causing inconsistent gameplay across devices."
                ),
                "domain": RAGDomain.GAME_DESIGN.value,
                "tags": ["game_loop", "delta_time", "frame_rate", "timestep"],
            },
            {
                "title": "Observer Pattern for Game Events",
                "source": "sparklabs_core",
                "content": (
                    "The Observer pattern decouples event producers from event consumers "
                    "in game systems. A central event bus or message queue allows systems "
                    "to communicate without direct references. This is essential for "
                    "achievement systems, UI updates, audio triggers, and gameplay "
                    "scripting.\n\n"
                    "Implementation approaches: simple callback registration, signal-slot "
                    "connections, or a full publish-subscribe message bus. Each has "
                    "tradeoffs in type safety, performance overhead, and debugging "
                    "visibility.\n\n"
                    "For performance-critical paths like collision callbacks, prefer "
                    "direct function calls over event bus dispatch. Reserve the event "
                    "bus for cross-system communication where loose coupling adds value.\n\n"
                    "Event payload design: use small, immutable data structures. Avoid "
                    "passing mutable game state through events to prevent unintended "
                    "side effects and race conditions in multi-threaded environments."
                ),
                "domain": RAGDomain.CODE_PATTERNS.value,
                "tags": ["observer", "events", "pub_sub", "decoupling", "messaging"],
            },
            {
                "title": "Object Pooling for Performance",
                "source": "sparklabs_core",
                "content": (
                    "Object pooling pre-allocates a fixed number of reusable objects "
                    "to avoid runtime allocation and garbage collection pauses. This is "
                    "especially important for frequently created and destroyed objects "
                    "like projectiles, particles, enemies, and UI elements.\n\n"
                    "A pool maintains two lists: available objects (inactive) and active "
                    "objects. When a new object is needed, retrieve from available; when "
                    "done, return to the pool by resetting its state rather than "
                    "destroying it. If the pool is exhausted, either grow the pool or "
                    "reuse the oldest active object.\n\n"
                    "Reset protocol: every pooled object must implement a reset method "
                    "that returns it to a clean initial state. Failing to reset properly "
                    "is the most common source of pool-related bugs, leading to stale "
                    "state bleeding between uses.\n\n"
                    "Pool sizing: profile your game to determine peak active object "
                    "counts. Size pools slightly above the observed maximum to handle "
                    "edge cases. Too-large pools waste memory; too-small pools cause "
                    "allocation at runtime."
                ),
                "domain": RAGDomain.PERFORMANCE.value,
                "tags": ["object_pool", "memory", "performance", "garbage_collection"],
            },
            {
                "title": "Level Design Spatial Partitioning",
                "source": "sparklabs_core",
                "content": (
                    "Spatial partitioning divides the game world into manageable regions "
                    "for efficient collision detection, rendering culling, and AI spatial "
                    "queries. Common approaches include grid-based partitioning, quad-trees "
                    "for 2D, and octrees for 3D.\n\n"
                    "Grid partitioning divides space into uniform cells. Objects are "
                    "assigned to the cells they overlap. Querying is O(1) per cell, "
                    "making it ideal for games with uniformly distributed objects. Tuning "
                    "cell size is critical: too large and you check too many objects; "
                    "too small and objects span many cells.\n\n"
                    "Quad-trees and octrees recursively subdivide space when cell density "
                    "exceeds a threshold. They adapt to non-uniform object distributions "
                    "but add tree traversal overhead. Use them when object density varies "
                    "significantly across the world.\n\n"
                    "Spatial hashing maps continuous coordinates to discrete hash buckets, "
                    "providing O(1) neighbor lookups. This technique works well for "
                    "particle systems and dynamic environments where rebuilding trees "
                    "each frame is too expensive."
                ),
                "domain": RAGDomain.LEVEL_DESIGN.value,
                "tags": ["spatial", "partitioning", "collision", "quadtree", "octree"],
            },
            {
                "title": "Finite State Machines for Game AI",
                "source": "sparklabs_core",
                "content": (
                    "Finite State Machines (FSMs) model agent behavior as discrete states "
                    "with well-defined transitions. Each state encapsulates behavior for "
                    "that mode; transitions define when and why the agent switches states. "
                    "Common in-game states include: Idle, Patrol, Chase, Attack, Flee, "
                    "and Dead.\n\n"
                    "A simple FSM uses a switch statement or state pattern with an "
                    "update method per state. Transitions are evaluated at the end of "
                    "each state's update cycle. More sophisticated implementations use "
                    "transition tables or hierarchical state machines.\n\n"
                    "Hierarchical State Machines (HSMs) allow states to contain sub-states, "
                    "reducing transition explosion. For example, an Attack state might "
                    "contain sub-states for Approach, Strafe, and Fire. The parent state "
                    "handles common transitions like taking damage to switch to Flee.\n\n"
                    "Behavior Trees offer an alternative to FSMs for complex AI. They "
                    "compose behaviors from reusable nodes and handle conditional logic "
                    "more naturally than flat or hierarchical state machines. Choose FSMs "
                    "for predictability; choose behavior trees for modularity."
                ),
                "domain": RAGDomain.MECHANICS.value,
                "tags": ["fsm", "state_machine", "ai", "behavior", "hfsm"],
            },
        ]

        for i, entry in enumerate(seed_entries):
            strategy = ChunkStrategy.SEMANTIC if i % 2 == 0 else ChunkStrategy.PARAGRAPH
            self.ingest_document(
                title=entry["title"],
                source=entry["source"],
                content=entry["content"],
                domain=entry["domain"],
                tags=entry["tags"],
                chunk_strategy=strategy,
            )


def get_rag_pipeline() -> RAGPipeline:
    return RAGPipeline.get_instance()